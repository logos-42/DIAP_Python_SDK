from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime

from ..types.zkp_types import NoirProverInputs, NoirProofResult, ProofResult
from ..types.errors import ZKPError
from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ZKPManagerConfig:
    backend: str = "snarkjs"
    proving_key_path: Optional[str] = None
    verification_key_path: Optional[str] = None
    wasm_path: Optional[str] = None
    circuit_id: str = "did_binding"


class NoirZKPManager:
    def __init__(self, config: Optional[ZKPManagerConfig] = None):
        self.config = config or ZKPManagerConfig()
        self._backend = None
        self._init_backend()

    def _init_backend(self):
        if self.config.backend == "snarkjs":
            try:
                from .snarkjs_backend import SnarkJSBackend

                self._backend = SnarkJSBackend(
                    wasm_path=self.config.wasm_path,
                    proving_key_path=self.config.proving_key_path,
                    verification_key_path=self.config.verification_key_path,
                )
                logger.info("Initialized SnarkJS ZKP backend")
            except ImportError as e:
                logger.error(f"Failed to import SnarkJS backend: {e}")
                raise ZKPError("SnarkJS backend not available")
        else:
            raise ZKPError(f"Unsupported ZKP backend: {self.config.backend}")

    def generate_did_binding_proof(
        self,
        expected_did_hash: List[int],
        public_key_hash: int,
        nonce_hash: int,
        secret_key: List[int],
        did_document_hash: List[int],
        nonce: List[int],
    ) -> NoirProofResult:
        inputs = NoirProverInputs(
            expected_did_hash=expected_did_hash,
            public_key_hash=public_key_hash,
            nonce_hash=nonce_hash,
            secret_key=secret_key,
            did_document_hash=did_document_hash,
            nonce=nonce,
        )

        return self._backend.generate_proof(inputs.to_dict())

    def verify_did_binding_proof(
        self,
        proof: bytes,
        public_inputs: bytes,
    ) -> bool:
        return self._backend.verify_proof(proof, public_inputs)

    def generate_proof(self, inputs: Dict[str, Any]) -> ProofResult:
        start_time = datetime.utcnow()

        result = self._backend.generate_proof(inputs)

        generation_time_ms = int(
            (datetime.utcnow() - start_time).total_seconds() * 1000
        )

        return ProofResult(
            proof=result.proof,
            public_inputs=result.public_inputs,
            circuit_hash=self._compute_circuit_hash(),
            timestamp=datetime.utcnow().isoformat() + "Z",
        )

    def verify_proof(self, proof_result: ProofResult) -> bool:
        return self._backend.verify_proof(
            proof_result.proof,
            proof_result.public_inputs,
        )

    def _compute_circuit_hash(self) -> str:
        if self.config.proving_key_path:
            import hashlib

            with open(self.config.proving_key_path, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()[:16]
        return "unknown"

    def load_verification_key(self, path: str) -> Dict[str, Any]:
        import json

        with open(path, "r") as f:
            return json.load(f)

    def load_proving_key(self, path: str) -> bytes:
        with open(path, "rb") as f:
            return f.read()
