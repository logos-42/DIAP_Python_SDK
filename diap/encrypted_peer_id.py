import hashlib
from typing import Tuple, Optional
from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .types.errors import KeyManagerError
from .utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class EncryptedPeerID:
    ciphertext: bytes
    nonce: bytes
    signature: bytes
    method: str = "AES-256-GCM-Ed25519-V3"

    def to_dict(self) -> dict:
        return {
            "ciphertext": self.ciphertext.hex(),
            "nonce": self.nonce.hex(),
            "signature": self.signature.hex(),
            "method": self.method,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EncryptedPeerID":
        return cls(
            ciphertext=bytes.fromhex(data["ciphertext"]),
            nonce=bytes.fromhex(data["nonce"]),
            signature=bytes.fromhex(data["signature"]),
            method=data.get("method", "AES-256-GCM-Ed25519-V3"),
        )


def derive_aes_key_from_ed25519(signing_key: bytes) -> bytes:
    key_material = signing_key
    info = b"DIAP_AES_KEY_V3"

    combined = bytearray(key_material) + bytearray(info)
    return hashlib.sha256(combined).digest()


def encrypt_peer_id(signing_key: bytes, peer_id: str) -> EncryptedPeerID:
    if len(signing_key) != 32:
        raise KeyManagerError("Signing key must be 32 bytes")

    aes_key = derive_aes_key_from_ed25519(signing_key)
    peer_id_bytes = peer_id.encode("utf-8")

    ciphertext, nonce = _aes_gcm_encrypt(peer_id_bytes, aes_key)

    sig_data = bytearray(ciphertext) + bytearray(nonce)
    signature = _sign_data(bytes(sig_data), signing_key)

    logger.debug("PeerID encrypted (AES-256-GCM)")
    logger.debug(f"  Original PeerID: {peer_id}")
    logger.debug(f"  Ciphertext length: {len(ciphertext)} bytes")
    logger.debug(f"  Nonce length: {len(nonce)} bytes")
    logger.debug(f"  Signature length: {len(signature)} bytes")

    return EncryptedPeerID(
        ciphertext=ciphertext,
        nonce=nonce,
        signature=signature,
        method="AES-256-GCM-Ed25519-V3",
    )


def decrypt_peer_id_with_secret(
    signing_key: bytes,
    encrypted: EncryptedPeerID,
) -> str:
    logger.info("Decrypting PeerID (holder private key)")

    if len(signing_key) != 32:
        raise KeyManagerError("Signing key must be 32 bytes")

    try:
        sig_data = bytearray(encrypted.ciphertext) + bytearray(encrypted.nonce)

        is_valid = _verify_signature(bytes(sig_data), encrypted.signature, signing_key)

        if not is_valid:
            raise KeyManagerError("Signature verification failed: data may be tampered")

        logger.debug("Signature verification passed")

        aes_key = derive_aes_key_from_ed25519(signing_key)
        plaintext = _aes_gcm_decrypt(encrypted.ciphertext, aes_key, encrypted.nonce)

        peer_id = plaintext.decode("utf-8")

        logger.info("PeerID decrypted successfully")
        logger.debug(f"  Decrypted PeerID: {peer_id}")

        return peer_id
    except KeyManagerError:
        raise
    except Exception as e:
        raise KeyManagerError(f"Failed to decrypt PeerID: {e}")


def verify_peer_id_signature(
    verifying_key: bytes,
    encrypted: EncryptedPeerID,
    claimed_peer_id: str,
) -> bool:
    logger.info("Verifying PeerID signature (public verification)")

    try:
        sig_data = bytearray(encrypted.ciphertext) + bytearray(encrypted.nonce)
        is_valid = _verify_signature(bytes(sig_data), encrypted.signature, verifying_key)

        if is_valid:
            logger.info("PeerID signature verification passed")
            return True
        else:
            logger.warning("PeerID signature verification failed")
            return False
    except Exception as e:
        logger.warning(f"PeerID signature verification failed: {e}")
        return False


def verify_encrypted_peer_id_ownership(
    verifying_key: bytes,
    encrypted: EncryptedPeerID,
    claimed_peer_id: str,
) -> bool:
    logger.info("Verifying PeerID ownership (via signature)")
    return verify_peer_id_signature(verifying_key, encrypted, claimed_peer_id)


def _aes_gcm_encrypt(plaintext: bytes, key: bytes) -> Tuple[bytes, bytes]:
    import os

    nonce = os.urandom(12)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    return ciphertext, nonce


def _aes_gcm_decrypt(ciphertext: bytes, key: bytes, nonce: bytes) -> bytes:
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None)


def _sign_data(data: bytes, signing_key: bytes) -> bytes:
    private_key_obj = Ed25519PrivateKey.from_private_bytes(signing_key)
    return private_key_obj.sign(data)


def _verify_signature(data: bytes, signature: bytes, verifying_key: bytes) -> bool:
    try:
        public_key_obj = Ed25519PublicKey.from_public_bytes(verifying_key)
        public_key_obj.verify(signature, data)
        return True
    except Exception:
        return False
