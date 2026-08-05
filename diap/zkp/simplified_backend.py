"""
简化 ZKP 后端
用于测试和回退，使用哈希函数模拟 ZKP
"""

import hashlib
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from ..types.errors import ZKPError
from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class NoirProofResult:
    """Noir 证明结果"""
    proof: bytes
    public_inputs: bytes
    circuit_output: Optional[Any] = None
    timestamp: str = ""
    generation_time_ms: int = 0


@dataclass
class NoirVerificationResult:
    """Noir 验证结果"""
    is_valid: bool
    verification_time_ms: int = 0
    error_message: Optional[str] = None


class SimplifiedBackend:
    """简化后端实现"""

    async def generate_proof(self, inputs: Dict[str, Any]) -> NoirProofResult:
        """生成证明（模拟）"""
        start_time = time.time() * 1000

        try:
            logger.debug(f"Generating proof with simplified backend: {inputs}")

            # 模拟证明生成：使用哈希函数
            proof_data = json.dumps(
                {
                    "expectedDidHash": inputs.get("expectedDidHash", []),
                    "publicKeyHash": inputs.get("publicKeyHash", 0),
                    "nonceHash": inputs.get("nonceHash", 0),
                    "timestamp": int(time.time() * 1000),
                },
                sort_keys=True,
            )

            proof = hashlib.sha256(proof_data.encode()).digest()
            public_inputs = hashlib.sha256(
                json.dumps(
                    {
                        "expectedDidHash": inputs.get("expectedDidHash", []),
                        "publicKeyHash": inputs.get("publicKeyHash", 0),
                        "nonceHash": inputs.get("nonceHash", 0),
                    },
                    sort_keys=True,
                ).encode()
            ).digest()

            generation_time = int(time.time() * 1000 - start_time)

            return NoirProofResult(
                proof=proof,
                public_inputs=public_inputs,
                circuit_output=inputs.get("expectedOutput"),
                timestamp=datetime.now(timezone.utc).isoformat(),
                generation_time_ms=generation_time,
            )
        except Exception as error:
            raise ZKPError(f"Failed to generate proof with simplified backend: {error}")

    async def verify_proof(
        self,
        proof: bytes,
        public_inputs: bytes,
    ) -> NoirVerificationResult:
        """验证证明（模拟）"""
        start_time = time.time() * 1000

        try:
            # 模拟验证：检查证明和公共输入是否有效
            is_valid = len(proof) > 0 and len(public_inputs) > 0

            verification_time = int(time.time() * 1000 - start_time)

            return NoirVerificationResult(
                is_valid=is_valid,
                verification_time_ms=verification_time,
                error_message=None if is_valid else "Invalid proof format",
            )
        except Exception as error:
            return NoirVerificationResult(
                is_valid=False,
                verification_time_ms=int(time.time() * 1000 - start_time),
                error_message=f"Verification failed: {error}",
            )

    def is_available(self) -> bool:
        """检查后端是否可用"""
        return True  # 简化后端总是可用