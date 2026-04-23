import json
import hashlib
from typing import Optional, List, Dict, Any
from datetime import datetime

from .types.did_types import (
    DIDDocument,
    VerificationMethod,
    Service,
    AgentProfile,
    CryptoWallets,
    AgentWallet,
    LinkedDomains,
)
from .types.key_types import KeyPair
from .types.errors import DIDBuilderError
from .utils.crypto import sha256_hash, generate_random_bytes
from .utils.encoding import (
    bytes_to_multibase,
    base58_encode,
    base58_decode,
    canonicalize,
)
from .utils.logger import get_logger

logger = get_logger(__name__)


class DIDBuilder:
    DEFAULT_CONTEXT = ["https://www.w3.org/ns/did/v1", "https://ns.did.ai/schemas/v1"]
    DEFAULT_VERIFICATION_TYPE = "Ed25519VerificationKey2020"

    def __init__(self, key_manager=None):
        self.key_manager = key_manager

    def create_did_document(
        self,
        key_pair: KeyPair,
        services: Optional[List[Service]] = None,
        agent_profile: Optional[AgentProfile] = None,
        crypto_wallets: Optional[CryptoWallets] = None,
        linked_domains: Optional[LinkedDomains] = None,
    ) -> DIDDocument:
        public_key_multibase = bytes_to_multibase(key_pair.public_key)

        verification_method = VerificationMethod(
            id=f"{key_pair.did}#key-1",
            vm_type=self.DEFAULT_VERIFICATION_TYPE,
            controller=key_pair.did,
            public_key_multibase=public_key_multibase,
        )

        authentication = [f"{key_pair.did}#key-1"]
        context = self.DEFAULT_CONTEXT.copy()

        if agent_profile or crypto_wallets or linked_domains:
            context.append("https://diap.ai/schemas/v1")

        service = services or []

        if agent_profile:
            service.append(self._create_agent_service(agent_profile, key_pair.did))
        if crypto_wallets:
            service.append(self._create_wallet_service(crypto_wallets, key_pair.did))
        if linked_domains:
            service.append(
                self._create_linked_domains_service(linked_domains, key_pair.did)
            )

        now = datetime.utcnow().isoformat() + "Z"

        did_document = DIDDocument(
            context=context,
            id=key_pair.did,
            verification_method=[verification_method],
            authentication=authentication,
            service=service if service else None,
            created=now,
            updated=now,
        )

        logger.info(f"Created DID document for: {key_pair.did}")
        return did_document

    def _create_agent_service(self, profile: AgentProfile, did: str) -> Service:
        return Service(
            id=f"{did}/agent",
            service_type="AgentProfile",
            service_endpoint={
                "avatar": profile.avatar,
                "name": profile.name,
                "description": profile.description,
                "homepage": profile.homepage,
            },
        )

    def _create_wallet_service(self, wallets: CryptoWallets, did: str) -> Service:
        return Service(
            id=f"{did}/wallets",
            service_type="CryptoWallets",
            service_endpoint=wallets.to_dict(),
        )

    def _create_linked_domains_service(
        self, domains: LinkedDomains, did: str
    ) -> Service:
        return Service(
            id=f"{did}/linked-domains",
            service_type="LinkedDomains",
            service_endpoint={"domains": domains.domains},
        )

    def add_service(
        self,
        document: DIDDocument,
        service_type: str,
        endpoint: Any,
        id: Optional[str] = None,
    ) -> DIDDocument:
        service_id = id or f"{document.id}/service/{self._generate_id()}"

        service = Service(
            id=service_id,
            service_type=service_type,
            service_endpoint=endpoint,
        )

        if document.service is None:
            document.service = []

        document.service.append(service)
        document.updated = datetime.utcnow().isoformat() + "Z"

        return document

    def add_verification_method(
        self,
        document: DIDDocument,
        key_pair: KeyPair,
        method_id: Optional[str] = None,
        vm_type: Optional[str] = None,
    ) -> DIDDocument:
        vm_id = (
            method_id or f"{document.id}#key-{len(document.verification_method) + 1}"
        )
        vm_type = vm_type or self.DEFAULT_VERIFICATION_TYPE

        verification_method = VerificationMethod(
            id=vm_id,
            vm_type=vm_type,
            controller=document.id,
            public_key_multibase=bytes_to_multibase(key_pair.public_key),
        )

        document.verification_method.append(verification_method)
        document.updated = datetime.utcnow().isoformat() + "Z"

        return document

    def add_authentication(
        self,
        document: DIDDocument,
        method_id: Optional[str] = None,
    ) -> DIDDocument:
        vm_id = method_id or f"{document.id}#key-{len(document.verification_method)}"

        if vm_id not in document.authentication:
            document.authentication.append(vm_id)
            document.updated = datetime.utcnow().isoformat() + "Z"

        return document

    def remove_service(self, document: DIDDocument, service_id: str) -> DIDDocument:
        if document.service:
            document.service = [s for s in document.service if s.id != service_id]
            document.updated = datetime.utcnow().isoformat() + "Z"

        return document

    def deactivate(self, document: DIDDocument) -> DIDDocument:
        document.verification_method = []
        document.authentication = []
        document.service = None
        document.updated = datetime.utcnow().isoformat() + "Z"

        return document

    def compute_document_hash(self, document: DIDDocument) -> str:
        canonical = canonicalize(document.to_dict())
        return sha256_hash(canonical).hex()

    def verify_document_integrity(self, document: DIDDocument) -> bool:
        expected_hash = document.to_dict().get("_hash")
        if not expected_hash:
            return True

        current_hash = self.compute_document_hash(document)
        return current_hash == expected_hash

    def _generate_id(self) -> str:
        return base58_encode(generate_random_bytes(16))[:12]

    def parse_did(self, did: str) -> Dict[str, str]:
        if not did.startswith("did:key:"):
            raise DIDBuilderError(f"Invalid did:key format: {did}")

        parts = did.split(":")
        if len(parts) < 3:
            raise DIDBuilderError(f"Invalid did format: {did}")

        return {
            "method": parts[1],
            "method_specific_id": ":".join(parts[2:]),
        }

    def resolve_did_key(self, did: str) -> Optional[bytes]:
        parsed = self.parse_did(did)
        multicodec = base58_decode(parsed["method_specific_id"])

        if multicodec[0] == 0xED and multicodec[1] == 0x01:
            return multicodec[2:]

        raise DIDBuilderError(f"Unsupported multicodec: {multicodec[:2].hex()}")

    def export_document(self, document: DIDDocument, filepath: str):
        with open(filepath, "w") as f:
            json.dump(document.to_dict(), f, indent=2)
        logger.info(f"Exported DID document to {filepath}")

    @staticmethod
    def import_document(data: Dict[str, Any]) -> DIDDocument:
        return DIDDocument.from_dict(data)
