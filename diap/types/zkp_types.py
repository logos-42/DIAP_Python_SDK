from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class NoirProverInputs:
    expected_did_hash: List[int]
    public_key_hash: int
    nonce_hash: int
    secret_key: List[int]
    did_document_hash: List[int]
    nonce: List[int]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "expected_did_hash": self.expected_did_hash,
            "public_key_hash": self.public_key_hash,
            "nonce_hash": self.nonce_hash,
            "secret_key": self.secret_key,
            "did_document_hash": self.did_document_hash,
            "nonce": self.nonce,
        }


@dataclass
class NoirProofResult:
    proof: bytes
    public_inputs: bytes
    circuit_output: str
    timestamp: str
    generation_time_ms: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proof": self.proof.hex(),
            "public_inputs": self.public_inputs.hex(),
            "circuit_output": self.circuit_output,
            "timestamp": self.timestamp,
            "generation_time_ms": self.generation_time_ms,
        }


@dataclass
class ProofInputs:
    did_hash: List[int]
    public_key_hash: int
    nonce_hash: int
    secret_key: List[int]
    document_hash: List[int]
    nonce: List[int]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "did_hash": self.did_hash,
            "public_key_hash": self.public_key_hash,
            "nonce_hash": self.nonce_hash,
            "secret_key": self.secret_key,
            "document_hash": self.document_hash,
            "nonce": self.nonce,
        }


@dataclass
class ProofResult:
    proof: bytes
    public_inputs: bytes
    circuit_hash: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proof": self.proof.hex() if isinstance(self.proof, bytes) else self.proof,
            "public_inputs": self.public_inputs.hex()
            if isinstance(self.public_inputs, bytes)
            else self.public_inputs,
            "circuit_hash": self.circuit_hash,
            "timestamp": self.timestamp,
        }


@dataclass
class VerificationKey:
    vk_hash: str
    circuit_id: str
    proving_key_path: Optional[str] = None
    verification_key_path: Optional[str] = None
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "vk_hash": self.vk_hash,
            "circuit_id": self.circuit_id,
            "proving_key_path": self.proving_key_path,
            "verification_key_path": self.verification_key_path,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VerificationKey":
        return cls(
            vk_hash=data["vk_hash"],
            circuit_id=data["circuit_id"],
            proving_key_path=data.get("proving_key_path"),
            verification_key_path=data.get("verification_key_path"),
            created_at=data.get("created_at"),
        )


@dataclass
class ZKPProof:
    proof: str
    public_inputs: List[str]
    circuit_id: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proof": self.proof,
            "public_inputs": self.public_inputs,
            "circuit_id": self.circuit_id,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ZKPProof":
        return cls(
            proof=data["proof"],
            public_inputs=data["public_inputs"],
            circuit_id=data["circuit_id"],
            timestamp=data["timestamp"],
        )
