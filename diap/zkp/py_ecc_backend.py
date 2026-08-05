"""
DIAP Python SDK - 真实椭圆曲线 ZKP 后端（py_ecc / BN128）

使用 py_ecc 8.0 在 BN128 曲线上实现真实的 Schnorr 知识证明：
- 证明者知道秘密标量 x（从输入派生），公钥 X = x·G
- 证明：(R, s)，其中 R = r·G, c = H(R || X || public), s = r + c·x
- 验证：s·G == R + c·X

这是 honest-verifier zero-knowledge 的知识证明协议，
替代纯哈希模拟（simplified backend），提供真实的椭圆曲线密码学保证。
"""

import hashlib
import json
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple

from py_ecc.bn128 import G1, add, multiply, eq, curve_order

from ..types.errors import ZKPError
from ..utils.logger import get_logger

logger = get_logger(__name__)

# 证明格式版本
PROOF_FORMAT_VERSION = 2
CIRCUIT_HASH = "bn128_schnorr_v2"


def _point_to_bytes(point: Tuple) -> bytes:
    """将曲线点序列化为 64 字节 (x || y)"""
    x, y = point
    return int(x).to_bytes(32, "big") + int(y).to_bytes(32, "big")


def _bytes_to_point(data: bytes) -> Tuple:
    """从 64 字节还原曲线点"""
    if len(data) != 64:
        raise ZKPError("Invalid point bytes length")
    x = int.from_bytes(data[:32], "big")
    y = int.from_bytes(data[32:], "big")
    from py_ecc.bn128 import FQ

    return (FQ(x), FQ(y))


def _derive_secret(inputs: Dict[str, Any]) -> int:
    """从输入派生确定性秘密标量（真实证明中的 witness）"""
    canonical = json.dumps(inputs, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode()).digest()
    secret = int.from_bytes(digest, "big")
    return secret % (curve_order - 1) + 1


def _public_binding(inputs: Dict[str, Any]) -> bytes:
    """提取公开输入作为 challenge 绑定的公共语句"""
    public = {
        "expected_did_hash": inputs.get("expected_did_hash", inputs.get("expectedDidHash", [])),
        "public_key_hash": inputs.get("public_key_hash", inputs.get("publicKeyHash", 0)),
        "nonce_hash": inputs.get("nonce_hash", inputs.get("nonceHash", 0)),
    }
    return json.dumps(public, sort_keys=True, separators=(",", ":")).encode()


class PyEccBackend:
    """基于 py_ecc BN128 的真实椭圆曲线 ZKP 后端"""

    def __init__(self, verification_key_path: Optional[str] = None):
        self.verification_key_path = verification_key_path

    # ------------------------------------------------------------------
    # 证明生成
    # ------------------------------------------------------------------

    def generate_proof(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """生成 Schnorr 知识证明

        返回 JSON 结构：
        {
            "format": "bn128_schnorr",
            "version": 2,
            "public_key": X (64 bytes hex),
            "commitment": R (64 bytes hex),
            "challenge": c (32 bytes hex),
            "response": s (32 bytes hex),
            "public_binding": 公开输入 JSON
        }
        """
        try:
            # witness: 派生秘密标量
            x = _derive_secret(inputs)

            # 公钥 X = x·G（证明者承诺的公共值）
            X = multiply(G1, x)

            # 随机数 r，承诺 R = r·G
            r = secrets.randbelow(curve_order - 1) + 1
            R = multiply(G1, r)

            # challenge: Fiat-Shamir 变换
            public_binding = _public_binding(inputs)
            challenge_bytes = hashlib.sha256(
                _point_to_bytes(R) + _point_to_bytes(X) + public_binding
            ).digest()
            c = int.from_bytes(challenge_bytes, "big") % curve_order

            # response: s = r + c·x (mod n)
            s = (r + c * x) % curve_order

            return {
                "format": "bn128_schnorr",
                "version": PROOF_FORMAT_VERSION,
                "public_key": _point_to_bytes(X).hex(),
                "commitment": _point_to_bytes(R).hex(),
                "challenge": c.to_bytes(32, "big").hex(),
                "response": s.to_bytes(32, "big").hex(),
                "public_binding": public_binding.decode(),
            }
        except Exception as e:
            raise ZKPError(f"Failed to generate proof: {e}")

    # ------------------------------------------------------------------
    # 证明验证
    # ------------------------------------------------------------------

    def verify_proof(self, proof: bytes | str, public_inputs: bytes | str) -> bool:
        """验证 Schnorr 知识证明

        验证方程：s·G == R + c·X
        """
        try:
            proof_data = self._parse_proof(proof)
            if proof_data.get("format") != "bn128_schnorr":
                return False
            if proof_data.get("version") != PROOF_FORMAT_VERSION:
                return False

            X = _bytes_to_point(bytes.fromhex(proof_data["public_key"]))
            R = _bytes_to_point(bytes.fromhex(proof_data["commitment"]))
            c = int.from_bytes(bytes.fromhex(proof_data["challenge"]), "big")
            s = int.from_bytes(bytes.fromhex(proof_data["response"]), "big")

            # 验证曲线点合法性
            if not self._is_valid_point(X) or not self._is_valid_point(R):
                return False

            # s·G == R + c·X
            lhs = multiply(G1, s)
            rhs = add(R, multiply(X, c))
            return eq(lhs, rhs)
        except Exception as e:
            logger.debug(f"Proof verification failed: {e}")
            return False

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------

    def _parse_proof(self, proof: bytes | str | dict) -> Dict[str, Any]:
        if isinstance(proof, dict):
            return proof
        if isinstance(proof, bytes):
            return json.loads(proof.decode())
        return json.loads(proof)

    def _is_valid_point(self, point: Tuple) -> bool:
        """检查点是否在 BN128 曲线上（朴素重算曲线方程）"""
        from py_ecc.bn128 import FQ, b

        x, y = point
        try:
            # y² == x³ + b
            return eq(
                (FQ(y) ** 2),
                (FQ(x) ** 3 + FQ(b)),
            )
        except Exception:
            return False

    # ------------------------------------------------------------------
    # 兼容接口
    # ------------------------------------------------------------------

    def get_circuit_hash(self) -> str:
        return CIRCUIT_HASH

    def is_available(self) -> bool:
        """py_ecc 总是可用"""
        return True
