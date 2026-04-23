from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime

from .types.did_types import DIDDocument
from .types.zkp_types import ProofResult
from .types.errors import VerificationError
from .utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class VerificationRequest:
    did: str
    challenge: str
    timestamp: str
    nonce: str
    expires_at: Optional[str] = None


@dataclass
class VerificationResult:
    is_valid: bool
    did: str
    timestamp: str
    method: str
    details: Optional[Dict[str, Any]] = None


class AgentVerificationManager:
    def __init__(
        self,
        identity_manager=None,
        zkp_manager=None,
        nonce_manager=None,
    ):
        self.identity_manager = identity_manager
        self.zkp_manager = zkp_manager
        self.nonce_manager = nonce_manager
        self._verification_log: List[VerificationResult] = []

    async def verify_agent_identity(
        self,
        did: str,
        proof: ProofResult,
        ipfs_client=None,
    ) -> VerificationResult:
        start_time = datetime.utcnow()

        try:
            if self.identity_manager:
                identity = self.identity_manager.resolve_identity(did, ipfs_client)
                if not identity:
                    return VerificationResult(
                        is_valid=False,
                        did=did,
                        timestamp=start_time.isoformat() + "Z",
                        method="identity_resolution",
                        details={"error": "Identity not found"},
                    )

            if self.zkp_manager:
                is_valid = self.zkp_manager.verify_proof(proof)
                if not is_valid:
                    return VerificationResult(
                        is_valid=False,
                        did=did,
                        timestamp=datetime.utcnow().isoformat() + "Z",
                        method="zkp_verification",
                        details={"error": "ZKP proof invalid"},
                    )

            result = VerificationResult(
                is_valid=True,
                did=did,
                timestamp=datetime.utcnow().isoformat() + "Z",
                method="full_verification",
                details={"verification_time_ms": self._elapsed_ms(start_time)},
            )

            self._verification_log.append(result)
            logger.info(f"Agent verification successful: {did}")
            return result

        except Exception as e:
            logger.error(f"Verification error for {did}: {e}")
            return VerificationResult(
                is_valid=False,
                did=did,
                timestamp=datetime.utcnow().isoformat() + "Z",
                method="error",
                details={"error": str(e)},
            )

    async def verify_binding_proof(
        self,
        did: str,
        proof: bytes,
        public_inputs: bytes,
    ) -> VerificationResult:
        try:
            if self.zkp_manager:
                is_valid = self.zkp_manager.verify_proof(
                    ProofResult(
                        proof=proof,
                        public_inputs=public_inputs,
                        circuit_hash="",
                        timestamp="",
                    )
                )

                return VerificationResult(
                    is_valid=is_valid,
                    did=did,
                    timestamp=datetime.utcnow().isoformat() + "Z",
                    method="binding_proof",
                    details={"verified": is_valid},
                )

            return VerificationResult(
                is_valid=False,
                did=did,
                timestamp=datetime.utcnow().isoformat() + "Z",
                method="binding_proof",
                details={"error": "ZKP manager not available"},
            )

        except Exception as e:
            logger.error(f"Binding proof verification error: {e}")
            return VerificationResult(
                is_valid=False,
                did=did,
                timestamp=datetime.utcnow().isoformat() + "Z",
                method="binding_proof",
                details={"error": str(e)},
            )

    async def verify_did_document(
        self,
        document: DIDDocument,
        ipfs_client=None,
    ) -> VerificationResult:
        try:
            doc_json = document.to_dict()
            computed_hash = self._hash_document(document)

            stored_hash = doc_json.get("_hash")
            if stored_hash and stored_hash != computed_hash:
                return VerificationResult(
                    is_valid=False,
                    did=document.id,
                    timestamp=datetime.utcnow().isoformat() + "Z",
                    method="document_integrity",
                    details={"error": "Hash mismatch"},
                )

            if ipfs_client and self.identity_manager:
                registration = self.identity_manager.get_registration(document.id)
                if registration:
                    stored_doc = await ipfs_client.get(registration.cid)
                    if stored_doc:
                        stored_hash = stored_doc.get("_hash")
                        if stored_hash and stored_hash != computed_hash:
                            return VerificationResult(
                                is_valid=False,
                                did=document.id,
                                timestamp=datetime.utcnow().isoformat() + "Z",
                                method="document_persistence",
                                details={"error": "IPFS hash mismatch"},
                            )

            return VerificationResult(
                is_valid=True,
                did=document.id,
                timestamp=datetime.utcnow().isoformat() + "Z",
                method="document_verification",
                details={"verified": True},
            )

        except Exception as e:
            logger.error(f"DID document verification error: {e}")
            return VerificationResult(
                is_valid=False,
                did=document.id if document else "unknown",
                timestamp=datetime.utcnow().isoformat() + "Z",
                method="document_verification",
                details={"error": str(e)},
            )

    async def verify_pubsub_message(
        self,
        sender_did: str,
        message: bytes,
        signature: bytes,
        public_key: bytes,
    ) -> VerificationResult:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

        try:
            public_key_obj = Ed25519PublicKey.from_public_bytes(public_key)
            public_key_obj.verify(signature, message)

            return VerificationResult(
                is_valid=True,
                did=sender_did,
                timestamp=datetime.utcnow().isoformat() + "Z",
                method="pubsub_signature",
                details={"verified": True},
            )

        except Exception as e:
            logger.warning(f"Pubsub verification failed: {e}")
            return VerificationResult(
                is_valid=False,
                did=sender_did,
                timestamp=datetime.utcnow().isoformat() + "Z",
                method="pubsub_signature",
                details={"error": str(e)},
            )

    def get_verification_history(
        self,
        did: Optional[str] = None,
        limit: int = 100,
    ) -> List[VerificationResult]:
        if did:
            return [r for r in self._verification_log if r.did == did][:limit]
        return self._verification_log[:limit]

    def clear_history(self):
        self._verification_log.clear()

    def _hash_document(self, document: DIDDocument) -> str:
        import json
        from .utils.crypto import sha256_hash

        canonical = json.dumps(
            document.to_dict(), sort_keys=True, separators=(",", ":")
        )
        return sha256_hash(canonical.encode()).hex()

    def _elapsed_ms(self, start: datetime) -> int:
        return int((datetime.utcnow() - start).total_seconds() * 1000)
