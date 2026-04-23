import json
from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass, asdict

from .types.did_types import DIDDocument, Service
from .types.key_types import KeyPair
from .types.zkp_types import ProofResult
from .types.errors import IdentityError
from .did_builder import DIDBuilder
from .did_cache import DIDCache
from .utils.crypto import sha256_hash
from .utils.encoding import bytes_to_hex
from .utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ServiceInfo:
    service_type: str
    endpoint: str
    pubsub_topic: Optional[str] = None


@dataclass
class AgentInfo:
    name: str
    services: List[ServiceInfo]
    description: Optional[str] = None
    tags: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "services": [
                {
                    "serviceType": s.service_type,
                    "endpoint": s.endpoint,
                    "pubsubTopic": s.pubsub_topic,
                }
                for s in self.services
            ],
            "description": self.description,
            "tags": self.tags,
        }


@dataclass
class IdentityRegistration:
    did: str
    cid: str
    did_document: Dict[str, Any]
    encrypted_peer_id_hex: str
    pubsub_auth_topic: str
    registered_at: str
    ipns_name: Optional[str] = None
    ipns_value: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "did": self.did,
            "cid": self.cid,
            "did_document": self.did_document,
            "encrypted_peer_id_hex": self.encrypted_peer_id_hex,
            "pubsub_auth_topic": self.pubsub_auth_topic,
            "registered_at": self.registered_at,
            "ipns_name": self.ipns_name,
            "ipns_value": self.ipns_value,
        }


class IdentityManager:
    def __init__(
        self,
        did_builder: Optional[DIDBuilder] = None,
        did_cache: Optional[DIDCache] = None,
        key_manager=None,
    ):
        self.did_builder = did_builder or DIDBuilder(key_manager)
        self.did_cache = did_cache or DIDCache()
        self.key_manager = key_manager
        self._registrations: Dict[str, IdentityRegistration] = {}

    def register_identity(
        self,
        key_pair: KeyPair,
        ipfs_client,
        services: Optional[List[Service]] = None,
        agent_profile=None,
        crypto_wallets=None,
        linked_domains=None,
        ipns_manager=None,
    ) -> IdentityRegistration:
        document = self.did_builder.create_did_document(
            key_pair=key_pair,
            services=services,
            agent_profile=agent_profile,
            crypto_wallets=crypto_wallets,
            linked_domains=linked_domains,
        )

        document_json = json.dumps(document.to_dict())
        cid = ipfs_client.add(document_json)

        pubsub_topic = self._generate_pubsub_topic(key_pair.did)

        registration = IdentityRegistration(
            did=key_pair.did,
            cid=cid,
            did_document=document.to_dict(),
            encrypted_peer_id_hex="",
            pubsub_auth_topic=pubsub_topic,
            registered_at=datetime.utcnow().isoformat() + "Z",
        )

        if ipns_manager:
            try:
                ipns_name, ipns_value = ipns_manager.publish(cid)
                registration.ipns_name = ipns_name
                registration.ipns_value = ipns_value
            except Exception as e:
                logger.warning(f"Failed to publish to IPNS: {e}")

        self._registrations[key_pair.did] = registration
        self.did_cache.set(key_pair.did, document)

        logger.info(f"Registered identity: {key_pair.did}")
        return registration

    def generate_binding_proof(
        self,
        key_pair: KeyPair,
        document_cid: str,
        zkp_manager,
        nonce: bytes,
    ) -> ProofResult:
        document = self.did_cache.get(key_pair.did)
        if not document:
            raise IdentityError("DID document not found in cache")

        doc_bytes = json.dumps(document.to_dict()).encode()
        doc_hash = sha256_hash(doc_bytes)

        nonce_hash = sha256_hash(nonce)

        public_key_hash = sha256_hash(key_pair.public_key)

        secret_key = key_pair.private_key

        inputs = {
            "expected_did_hash": self._bytes_to_field_elements(doc_hash),
            "public_key_hash": self._bytes_to_field_element(public_key_hash),
            "nonce_hash": self._bytes_to_field_element(nonce_hash),
            "secret_key": self._bytes_to_field_elements(secret_key),
            "did_document_hash": self._bytes_to_field_elements(doc_hash),
            "nonce": self._bytes_to_field_elements(nonce),
        }

        proof_result = zkp_manager.generate_proof(inputs)

        logger.info(f"Generated binding proof for DID: {key_pair.did}")
        return proof_result

    def verify_identity_with_zkp(
        self,
        did: str,
        proof: ProofResult,
        zkp_manager,
    ) -> bool:
        is_valid = zkp_manager.verify_proof(proof)

        if is_valid:
            logger.info(f"ZKP identity verification successful for: {did}")
        else:
            logger.warning(f"ZKP identity verification failed for: {did}")

        return is_valid

    def resolve_identity(self, did: str, ipfs_client=None) -> Optional[DIDDocument]:
        cached = self.did_cache.get(did)
        if cached:
            return cached

        if ipfs_client:
            registration = self._registrations.get(did)
            if registration:
                doc_data = ipfs_client.get(registration.cid)
                if doc_data:
                    document = DIDDocument.from_dict(doc_data)
                    self.did_cache.set(did, document)
                    return document

        return None

    def revoke_identity(self, did: str, ipfs_client=None, ipns_manager=None) -> bool:
        if did in self._registrations:
            registration = self._registrations[did]

            if ipfs_client:
                try:
                    ipfs_client.pin_remove(registration.cid)
                except Exception as e:
                    logger.warning(f"Failed to unpin CID: {e}")

            if ipns_manager and registration.ipns_name:
                try:
                    ipns_manager.remove(registration.ipns_name)
                except Exception as e:
                    logger.warning(f"Failed to remove IPNS name: {e}")

            self._registrations.pop(did)
            self.did_cache.invalidate(did)

            logger.info(f"Revoked identity: {did}")
            return True

        return False

    def get_registration(self, did: str) -> Optional[IdentityRegistration]:
        return self._registrations.get(did)

    def list_identities(self) -> List[str]:
        return list(self._registrations.keys())

    def _generate_pubsub_topic(self, did: str) -> str:
        topic_hash = sha256_hash(did.encode())[:8]
        return f"diap.auth.{bytes_to_hex(topic_hash)}"

    def _bytes_to_field_element(self, data: bytes) -> int:
        hash_bytes = sha256_hash(data)
        return int.from_bytes(hash_bytes[:8], "little")

    def _bytes_to_field_elements(self, data: bytes) -> List[int]:
        result = []
        for i in range(0, len(data), 8):
            chunk = data[i : i + 8]
            if len(chunk) < 8:
                chunk = chunk + b"\x00" * (8 - len(chunk))
            result.append(int.from_bytes(chunk, "little"))
        return result[:4]

    def create_agent_identity(
        self,
        name: str,
        key_pair: KeyPair,
        ipfs_client,
        services: List[ServiceInfo],
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> IdentityRegistration:
        agent_info = AgentInfo(
            name=name,
            services=services,
            description=description,
            tags=tags,
        )

        agent_service = Service(
            id=f"{key_pair.did}/agent",
            service_type="Agent",
            service_endpoint=agent_info.to_dict(),
        )

        registration = self.register_identity(
            key_pair=key_pair,
            ipfs_client=ipfs_client,
            services=[agent_service],
        )

        logger.info(f"Created agent identity: {name} ({key_pair.did})")
        return registration
