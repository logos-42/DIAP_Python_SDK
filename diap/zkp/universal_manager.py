from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum

from ..types.zkp_types import ProofResult, NoirProofResult
from ..types.errors import ZKPError
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ZKPBackendType(Enum):
    SNARKJS = "snarkjs"
    SIMPLIFIED = "simplified"
    NOIR = "noir"


class UniversalZKManager:
    def __init__(self, default_backend: str = "snarkjs"):
        self.default_backend = default_backend
        self._backends: Dict[str, Any] = {}
        self._current_backend = default_backend
        self._init_default_backend()

    def _init_default_backend(self):
        if self.default_backend == "snarkjs":
            try:
                from .snarkjs_backend import SnarkJSBackend

                self._backends["snarkjs"] = SnarkJSBackend()
                logger.info("Initialized SnarkJS backend")
            except ImportError as e:
                logger.warning(f"Failed to init SnarkJS: {e}, using simplified")
                self._backends["simplified"] = SimplifiedBackend()
                self._current_backend = "simplified"
        else:
            self._backends[self.default_backend] = SimplifiedBackend()

    def generate_proof(
        self,
        inputs: Dict[str, Any],
        backend: Optional[str] = None,
    ) -> ProofResult:
        backend_name = backend or self._current_backend

        if backend_name not in self._backends:
            if backend_name == "snarkjs":
                from .snarkjs_backend import SnarkJSBackend

                self._backends["snarkjs"] = SnarkJSBackend()
            else:
                raise ZKPError(f"Unknown backend: {backend_name}")

        backend_instance = self._backends[backend_name]

        if backend_name == "snarkjs":
            result = backend_instance.generate_proof(inputs)
        else:
            result = backend_instance.generate_proof(inputs)

        if isinstance(result, NoirProofResult):
            return ProofResult(
                proof=result.proof,
                public_inputs=result.public_inputs,
                circuit_hash="",
                timestamp=result.timestamp,
            )

        return result

    def verify_proof(
        self,
        proof: ProofResult,
        backend: Optional[str] = None,
    ) -> bool:
        backend_name = backend or self._current_backend

        if backend_name not in self._backends:
            logger.warning(f"Backend {backend_name} not found, using default")
            backend_name = self._current_backend

        backend_instance = self._backends[backend_name]
        return backend_instance.verify_proof(proof.proof, proof.public_inputs)

    def register_backend(self, name: str, backend: Any):
        self._backends[name] = backend
        logger.info(f"Registered ZKP backend: {name}")

    def set_default_backend(self, name: str):
        if name not in self._backends:
            raise ZKPError(f"Backend not registered: {name}")
        self._current_backend = name
        logger.info(f"Set default ZKP backend to: {name}")

    def get_available_backends(self) -> List[str]:
        return list(self._backends.keys())


class SimplifiedBackend:
    def generate_proof(self, inputs: Dict[str, Any]) -> ProofResult:
        import hashlib

        combined = json.dumps(inputs, sort_keys=True).encode()
        proof_bytes = hashlib.sha256(combined).digest() * 2

        public_inputs = json.dumps(
            {
                "did_hash": inputs.get("expected_did_hash", []),
                "public_key_hash": inputs.get("public_key_hash", 0),
            }
        ).encode()

        return ProofResult(
            proof=proof_bytes,
            public_inputs=public_inputs,
            circuit_hash="simplified_v1",
            timestamp=datetime.utcnow().isoformat() + "Z",
        )

    def verify_proof(self, proof: bytes, public_inputs: bytes) -> bool:
        return True

    def get_circuit_hash(self) -> str:
        return "simplified_v1"


import json
