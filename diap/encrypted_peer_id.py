import os
from typing import Optional, Tuple
from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.asymmetric.ec import (
    SECP256K1,
    ECDH,
    generate_private_key,
    derive_public_key,
)
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

from .types.errors import CryptoError
from .utils.crypto import (
    generate_random_bytes,
    sha256_hash,
    aes_gcm_encrypt,
    aes_gcm_decrypt,
    hmac_sha256,
)
from .utils.encoding import bytes_to_hex, hex_to_bytes, base58_encode, base58_decode
from .utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class EncryptedPeerID:
    encrypted_data: str
    nonce: str
    tag: str
    ephemeral_public_key: str
    version: int = 1

    def to_dict(self) -> dict:
        return {
            "encrypted_data": self.encrypted_data,
            "nonce": self.nonce,
            "tag": self.tag,
            "ephemeral_public_key": self.ephemeral_public_key,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EncryptedPeerID":
        return cls(
            encrypted_data=data["encrypted_data"],
            nonce=data["nonce"],
            tag=data["tag"],
            ephemeral_public_key=data["ephemeral_public_key"],
            version=data.get("version", 1),
        )


class EncryptedPeerIDManager:
    KEY_SIZE = 32
    NONCE_SIZE = 12
    TAG_SIZE = 16

    def __init__(self):
        self._key_cache: dict[str, bytes] = {}

    def encrypt_peer_id(
        self,
        peer_id: bytes,
        recipient_public_key: Optional[bytes] = None,
    ) -> EncryptedPeerID:
        if recipient_public_key:
            return self._ecies_encrypt(peer_id, recipient_public_key)
        else:
            return self._aes_encrypt(peer_id)

    def decrypt_peer_id(
        self,
        encrypted: EncryptedPeerID,
        private_key: Optional[bytes] = None,
        shared_key: Optional[bytes] = None,
    ) -> bytes:
        if encrypted.ephemeral_public_key:
            if not private_key:
                raise CryptoError("Private key required for ECIES decryption")
            return self._ecies_decrypt(encrypted, private_key)
        else:
            if not shared_key:
                raise CryptoError("Shared key required for AES decryption")
            return self._aes_decrypt(encrypted, shared_key)

    def _aes_encrypt(self, data: bytes) -> EncryptedPeerID:
        key = generate_random_bytes(self.KEY_SIZE)
        ciphertext, nonce, tag = aes_gcm_encrypt(key, data)

        self._key_cache[bytes_to_hex(data[:8])] = key

        return EncryptedPeerID(
            encrypted_data=bytes_to_hex(ciphertext),
            nonce=bytes_to_hex(nonce),
            tag=bytes_to_hex(tag),
            ephemeral_public_key="",
        )

    def _aes_decrypt(self, encrypted: EncryptedPeerID, key: bytes) -> bytes:
        ciphertext = hex_to_bytes(encrypted.encrypted_data)
        nonce = hex_to_bytes(encrypted.nonce)

        return aes_gcm_decrypt(key, ciphertext, nonce)

    def _ecies_encrypt(
        self, data: bytes, recipient_public_key: bytes
    ) -> EncryptedPeerID:
        ephemeral_private = generate_private_key(SECP256K1(), default_backend())
        ephemeral_public = derive_public_key(ephemeral_private.public_key())

        ephemeral_public_bytes = ephemeral_public.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint,
        )

        shared_secret = ephemeral_private.exchange(ECDH(), ephemeral_public)

        key_material = sha256_hash(shared_secret)
        encryption_key = key_material[:16]
        mac_key = key_material[16:32]

        aesgcm = AESGCM(encryption_key)
        nonce = generate_random_bytes(self.NONCE_SIZE)
        ciphertext = aesgcm.encrypt(nonce, data, None)

        mac = hmac_sha256(mac_key, ciphertext)

        return EncryptedPeerID(
            encrypted_data=bytes_to_hex(ciphertext),
            nonce=bytes_to_hex(nonce),
            tag=bytes_to_hex(mac[: self.TAG_SIZE]),
            ephemeral_public_key=bytes_to_hex(ephemeral_public_bytes),
        )

    def _ecies_decrypt(
        self, encrypted: EncryptedPeerID, private_key_bytes: bytes
    ) -> bytes:
        ephemeral_public_bytes = hex_to_bytes(encrypted.ephemeral_public_key)

        ephemeral_public = type(
            default_backend()
            .load_elliptic_curve_public_numbers(
                int.from_bytes(ephemeral_public_bytes[1:33], "big"),
                int.from_bytes(ephemeral_public_bytes[33:65], "big"),
            )
            .public_key(SECP256K1())
        )(SECP256K1(), default_backend())

        private_key = serialization.load_der_private_key(
            private_key_bytes, password=None, backend=default_backend()
        )

        shared_secret = private_key.exchange(ECDH(), ephemeral_public)

        key_material = sha256_hash(shared_secret)
        encryption_key = key_material[:16]
        mac_key = key_material[16:32]

        ciphertext = hex_to_bytes(encrypted.encrypted_data)
        nonce = hex_to_bytes(encrypted.nonce)
        expected_mac = hex_to_bytes(encrypted.tag)

        mac = hmac_sha256(mac_key, ciphertext)
        if mac[: self.TAG_SIZE] != expected_mac:
            raise CryptoError("MAC verification failed")

        aesgcm = AESGCM(encryption_key)
        return aesgcm.decrypt(nonce, ciphertext, None)

    def derive_shared_key(
        self,
        private_key: bytes,
        peer_public_key: bytes,
    ) -> bytes:
        private = serialization.load_der_private_key(
            private_key, password=None, backend=default_backend()
        )

        peer_public = serialization.load_elliptic_curve_public_bytes(
            peer_public_key, SECP256K1()
        )

        shared = private.exchange(ECDH(), peer_public)
        return sha256_hash(shared)[:32]

    def generate_peer_id_keypair(self) -> Tuple[bytes, bytes]:
        private_key = generate_private_key(SECP256K1(), default_backend())
        public_key = derive_public_key(private_key.public_key())

        private_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

        public_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint,
        )

        return private_bytes, public_bytes
