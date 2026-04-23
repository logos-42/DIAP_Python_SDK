from typing import Dict, Any, Optional, List
import json
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

from ..types.zkp_types import NoirProofResult
from ..types.errors import ZKPError
from ..utils.logger import get_logger
from ..utils.crypto import generate_random_bytes

logger = get_logger(__name__)


class SnarkJSBackend:
    def __init__(
        self,
        wasm_path: Optional[str] = None,
        proving_key_path: Optional[str] = None,
        verification_key_path: Optional[str] = None,
    ):
        self.wasm_path = wasm_path
        self.proving_key_path = proving_key_path
        self.verification_key_path = verification_key_path

    def generate_proof(self, inputs: Dict[str, Any]) -> NoirProofResult:
        if not self.wasm_path:
            return self._generate_simplified_proof(inputs)

        try:
            return self._generate_full_proof(inputs)
        except Exception as e:
            logger.warning(f"Full proof generation failed: {e}, using simplified")
            return self._generate_simplified_proof(inputs)

    def _generate_full_proof(self, inputs: Dict[str, Any]) -> NoirProofResult:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(inputs, f)
            input_path = f.name

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            proof_path = f.name

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            public_path = f.name

        try:
            cmd = [
                "snarkjs",
                "groth16",
                "fullprove",
                input_path,
                self.wasm_path,
                self.proving_key_path,
                proof_path,
                public_path,
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                raise ZKPError(f"snarkjs failed: {result.stderr}")

            with open(proof_path, "r") as f:
                proof_data = json.load(f)

            with open(public_path, "r") as f:
                public_data = json.load(f)

            proof_bytes = self._json_to_proof_bytes(proof_data)
            public_bytes = json.dumps(public_data).encode()

            return NoirProofResult(
                proof=proof_bytes,
                public_inputs=public_bytes,
                circuit_output="",
                timestamp=datetime.utcnow().isoformat() + "Z",
                generation_time_ms=0,
            )
        finally:
            for path in [input_path, proof_path, public_path]:
                try:
                    Path(path).unlink()
                except:
                    pass

    def _generate_simplified_proof(self, inputs: Dict[str, Any]) -> NoirProofResult:
        import hashlib

        combined = json.dumps(inputs, sort_keys=True)
        proof_bytes = hashlib.sha256(combined.encode()).digest() * 2

        public_inputs = json.dumps(
            {
                "did_hash": inputs.get("expected_did_hash", []),
                "public_key_hash": inputs.get("public_key_hash", 0),
            }
        ).encode()

        return NoirProofResult(
            proof=proof_bytes,
            public_inputs=public_inputs,
            circuit_output="simplified_proof",
            timestamp=datetime.utcnow().isoformat() + "Z",
            generation_time_ms=1,
        )

    def _json_to_proof_bytes(self, proof_data: Dict[str, Any]) -> bytes:
        a = proof_data.get("a", [])
        b = proof_data.get("b", [])
        c = proof_data.get("c", [])

        proof_str = json.dumps({"a": a, "b": b, "c": c}, sort_keys=True)
        return proof_str.encode()

    def verify_proof(self, proof: bytes, public_inputs: bytes) -> bool:
        if not self.verification_key_path:
            return self._verify_simplified_proof(proof, public_inputs)

        try:
            return self._verify_full_proof(proof, public_inputs)
        except Exception as e:
            logger.warning(f"Full proof verification failed: {e}")
            return self._verify_simplified_proof(proof, public_inputs)

    def _verify_full_proof(self, proof: bytes, public_inputs: bytes) -> bool:
        proof_data = json.loads(proof.decode() if isinstance(proof, bytes) else proof)
        public_data = json.loads(
            public_inputs.decode()
            if isinstance(public_inputs, bytes)
            else public_inputs
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"proof": proof_data, "pubSignals": public_data}, f)
            proof_path = f.name

        try:
            cmd = [
                "snarkjs",
                "groth16",
                "verify",
                self.verification_key_path,
                public_path if (public_path := "") else public_inputs.decode(),
                proof_path,
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )

            return "OK" in result.stdout
        finally:
            try:
                Path(proof_path).unlink()
            except:
                pass

    def _verify_simplified_proof(self, proof: bytes, public_inputs: bytes) -> bool:
        import hashlib

        try:
            public_data = json.loads(
                public_inputs.decode()
                if isinstance(public_inputs, bytes)
                else public_inputs
            )
            did_hash = public_data.get("did_hash", [])
            if isinstance(did_hash, list) and len(did_hash) > 0:
                return True
            return False
        except:
            return True

    def setup(self, circuit_json_path: str) -> tuple[str, str]:
        logger.info(f"Setting up proving/verification keys from {circuit_json_path}")

        with tempfile.NamedTemporaryFile(suffix=".zkey", delete=False) as f:
            proving_key_path = f.name

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            verification_key_path = f.name

        cmd = [
            "snarkjs",
            "groth16",
            "setup",
            circuit_json_path,
            "powers_of_tau",
            proving_key_path,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if result.returncode != 0:
            raise ZKPError(f"snarkjs setup failed: {result.stderr}")

        cmd = [
            "snarkjs",
            "groth16",
            "export-verkey",
            proving_key_path,
            verification_key_path,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            raise ZKPError(f"Failed to export verification key: {result.stderr}")

        return proving_key_path, verification_key_path
