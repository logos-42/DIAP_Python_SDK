import os
import hashlib
import hmac
import secrets
from typing import Tuple, Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.asymmetric.ec import (
    SECP256K1,
    ECDH,
)
from cryptography.hazmat.primitives.asymmetric.ec import (
    generate_private_key,
    derive_public_key,
)
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend


def generate_random_bytes(length: int) -> bytes:
    return secrets.token_bytes(length)


def sha256_hash(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def keccak_hash(data: bytes) -> bytes:
    import pysha3

    return pysha3.keccak_256(data).digest()


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


def ecies_encrypt(
    public_key_bytes: bytes, plaintext: bytes
) -> Tuple[bytes, bytes, bytes, bytes]:
    private_key = generate_private_key(SECP256K1(), default_backend())
    public_key = derive_public_key(private_key.public_key())

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
    private_key = serialization.load_pem_private_key(
        private_key_bytes, password=None, backend=default_backend()
    )

    ephemeral_public_key = type(private_key.public_key()).from_encoded_point(
        SECP256K1(), ephemeral_public_key_bytes
    )

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
