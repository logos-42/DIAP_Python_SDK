import os
import hashlib
import hmac
import secrets
from typing import Tuple, Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.asymmetric.ec import (
    SECP256K1,
    ECDH,
    generate_private_key,
)
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend


def generate_random_bytes(length: int) -> bytes:
    return secrets.token_bytes(length)


def sha256_hash(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def keccak_hash(data: bytes) -> bytes:
    from Crypto.Hash import keccak

    hasher = keccak.new(digest_bits=256)
    hasher.update(data)
    return hasher.digest()


def hmac_sha256(key: bytes, data: bytes) -> bytes:
    return hmac.new(key, data, hashlib.sha256).digest()


def aes_gcm_encrypt(
    key: bytes, plaintext: bytes, nonce: Optional[bytes] = None
) -> Tuple[bytes, bytes, bytes]:
    if nonce is None:
        nonce = generate_random_bytes(12)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    return ciphertext, nonce, ciphertext[-16:]


def aes_gcm_decrypt(key: bytes, ciphertext: bytes, nonce: bytes) -> bytes:
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None)


def ecies_encrypt(public_key_bytes: bytes, plaintext: bytes) -> Tuple[bytes, bytes, bytes, bytes]:
    private_key = generate_private_key(SECP256K1())
    public_key = private_key.public_key()

    ephemeral_public_key_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint,
    )

    shared_key = private_key.exchange(ECDH(), public_key)

    key_hash = sha256_hash(shared_key)
    encryption_key = key_hash[:16]
    mac_key = key_hash[16:32]

    aesgcm = AESGCM(encryption_key)
    nonce = generate_random_bytes(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)

    mac = hmac_sha256(mac_key, ciphertext)

    return ciphertext, nonce, mac, ephemeral_public_key_bytes


def ecies_decrypt(
    private_key_bytes: bytes,
    ciphertext: bytes,
    nonce: bytes,
    mac: bytes,
    ephemeral_public_key_bytes: bytes,
) -> bytes:
    private_key = serialization.load_der_private_key(
        private_key_bytes, password=None, backend=default_backend()
    )

    from cryptography.hazmat.primitives.asymmetric.ec import (
        EllipticCurvePublicKey,
        SECP256K1,
    )
    from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature

    if len(ephemeral_public_key_bytes) == 65 and ephemeral_public_key_bytes[0] == 0x04:
        x = int.from_bytes(ephemeral_public_key_bytes[1:33], "big")
        y = int.from_bytes(ephemeral_public_key_bytes[33:65], "big")
        from cryptography.hazmat.primitives.asymmetric.ec import EllipticCurvePublicNumbers

        public_numbers = EllipticCurvePublicNumbers(x, y, SECP256K1())
        ephemeral_public_key = public_numbers.public_key(default_backend())
    else:
        raise ValueError("Invalid public key format")

    shared_key = private_key.exchange(ECDH(), ephemeral_public_key)

    key_hash = sha256_hash(shared_key)
    encryption_key = key_hash[:16]
    mac_key = key_hash[16:32]

    expected_mac = hmac_sha256(mac_key, ciphertext)
    if not hmac.compare_digest(mac, expected_mac):
        raise ValueError("MAC verification failed")

    aesgcm = AESGCM(encryption_key)
    return aesgcm.decrypt(nonce, ciphertext, None)


def base58_encode(data: bytes) -> str:
    import base58

    return base58.b58encode(data).decode()


def base58_decode(data: str) -> bytes:
    import base58

    return base58.b58decode(data)


# ============================================================================
# Ed25519 签名（pynacl，对应 TS @noble/ed25519）
# ============================================================================


def ed25519_sign(private_key_seed: bytes, data: bytes) -> bytes:
    """Ed25519 签名（pynacl 实现，与 @noble/ed25519 兼容）

    private_key_seed: 32 字节私钥种子（与 cryptography Raw 格式一致）
    返回 64 字节签名
    """
    import nacl.signing

    signing_key = nacl.signing.SigningKey(private_key_seed)
    return signing_key.sign(data).signature


def ed25519_verify(public_key: bytes, data: bytes, signature: bytes) -> bool:
    """Ed25519 验签（pynacl 实现）

    public_key: 32 字节公钥（与 cryptography Raw 格式一致）
    """
    import nacl.signing

    try:
        verify_key = nacl.signing.VerifyKey(public_key)
        verify_key.verify(data, signature)
        return True
    except Exception:
        return False


def ed25519_keypair_from_seed(seed: bytes) -> Tuple[bytes, bytes]:
    """从 32 字节种子派生 Ed25519 公私钥对（pynacl）"""
    import nacl.signing

    signing_key = nacl.signing.SigningKey(seed)
    public_key = bytes(signing_key.verify_key)
    return seed, public_key
