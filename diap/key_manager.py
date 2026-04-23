import os
import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

from .types.key_types import KeyPair, KeyBackup, KeyStoreConfig
from .types.errors import KeyManagerError
from .utils.crypto import (
    generate_random_bytes,
    sha256_hash,
    aes_gcm_encrypt,
    aes_gcm_decrypt,
    base58_encode,
    base58_decode,
)
from .utils.encoding import bytes_to_multibase, encode_hex, decode_hex
from .utils.logger import get_logger

logger = get_logger(__name__)

MULTICODEC_ED25519_PREFIX = bytes([0xED, 0x01])


class KeyManager:
    DEFAULT_KEY_TYPE = "Ed25519"

    @staticmethod
    def generate() -> KeyPair:
        try:
            private_key_obj = Ed25519PrivateKey.generate()
            private_bytes = private_key_obj.private_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PrivateFormat.Raw,
                encryption_algorithm=serialization.NoEncryption(),
            )

            public_key_obj = private_key_obj.public_key()
            public_bytes = public_key_obj.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            )

            did = KeyManager._derive_did_key(public_bytes)

            key_pair = KeyPair(
                private_key=private_bytes,
                public_key=public_bytes,
                did=did,
                key_type=KeyManager.DEFAULT_KEY_TYPE,
            )

            logger.debug(f"Generated new Ed25519 keypair: {did}")
            return key_pair
        except Exception as e:
            raise KeyManagerError(f"Failed to generate keypair: {e}")

    @staticmethod
    def from_private_key(private_key: bytes) -> KeyPair:
        if len(private_key) != 32:
            raise KeyManagerError("Private key must be 32 bytes")

        try:
            private_key_obj = Ed25519PrivateKey.from_private_bytes(private_key)
            public_key_obj = private_key_obj.public_key()
            public_bytes = public_key_obj.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            )

            did = KeyManager._derive_did_key(public_bytes)

            return KeyPair(
                private_key=private_key,
                public_key=public_bytes,
                did=did,
                key_type=KeyManager.DEFAULT_KEY_TYPE,
            )
        except Exception as e:
            raise KeyManagerError(f"Failed to load keypair from private key: {e}")

    @staticmethod
    async def from_file(path: str) -> KeyPair:
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            key_file = json.loads(content)

            private_key_bytes = decode_hex(key_file["privateKey"])
            if len(private_key_bytes) != 32:
                raise KeyManagerError("Invalid private key length in file")

            return KeyManager.from_private_key(private_key_bytes)
        except KeyManagerError:
            raise
        except Exception as e:
            raise KeyManagerError(f"Failed to load keypair from file: {path}", original_error=e)

    @staticmethod
    async def save_to_file(keypair: KeyPair, path: str) -> None:
        try:
            key_file = {
                "keyType": "Ed25519",
                "privateKey": encode_hex(keypair.private_key),
                "publicKey": encode_hex(keypair.public_key),
                "did": keypair.did,
                "createdAt": datetime.utcnow().isoformat() + "Z",
                "version": "2.0",
            }

            content = json.dumps(key_file, indent=2)

            dir_path = os.path.dirname(path)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)

            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
                os.chmod(path, 0o600)

            logger.debug(f"Saved keypair to file: {path}")
        except Exception as e:
            raise KeyManagerError(f"Failed to save keypair to file: {path}", original_error=e)

    @staticmethod
    def export_backup(keypair: KeyPair, password: Optional[str] = None) -> KeyBackup:
        try:
            key_file = {
                "keyType": "Ed25519",
                "privateKey": encode_hex(keypair.private_key),
                "publicKey": encode_hex(keypair.public_key),
                "did": keypair.did,
                "createdAt": datetime.utcnow().isoformat() + "Z",
                "version": "2.0",
            }

            json_data = json.dumps(key_file)

            if password:
                salt = generate_random_bytes(16)
                key = KeyManager._derive_key(password, salt)
                nonce = generate_random_bytes(12)
                encrypted, _, _ = aes_gcm_encrypt(key, json_data.encode(), nonce)

                combined = salt + nonce + encrypted
                encrypted_data = base58_encode(combined)
            else:
                encrypted_data = base58_encode(json_data.encode())

            return KeyBackup(
                encrypted_data=encrypted_data,
                exported_at=datetime.utcnow().isoformat() + "Z",
            )
        except Exception as e:
            raise KeyManagerError(f"Failed to export key backup: {e}")

    @staticmethod
    def import_from_backup(backup: KeyBackup, password: Optional[str] = None) -> KeyPair:
        try:
            encrypted_buffer = base58_decode(backup.encrypted_data)

            if password:
                salt = encrypted_buffer[:16]
                nonce = encrypted_buffer[16:28]
                ciphertext = encrypted_buffer[28:]

                key = KeyManager._derive_key(password, salt)
                decrypted = aes_gcm_decrypt(ciphertext, key, nonce)
                json_data = decrypted.decode("utf-8")
            else:
                json_data = encrypted_buffer.decode("utf-8")

            key_file = json.loads(json_data)
            private_key_bytes = decode_hex(key_file["privateKey"])

            if len(private_key_bytes) != 32:
                raise KeyManagerError("Invalid private key length in backup")

            return KeyManager.from_private_key(private_key_bytes)
        except KeyManagerError:
            raise
        except Exception as e:
            raise KeyManagerError(f"Failed to import key from backup: {e}")

    @staticmethod
    def sign(keypair: KeyPair, data: bytes) -> bytes:
        try:
            private_key_obj = Ed25519PrivateKey.from_private_bytes(keypair.private_key)
            signature = private_key_obj.sign(data)
            return signature
        except Exception as e:
            raise KeyManagerError(f"Failed to sign data: {e}")

    @staticmethod
    def verify(keypair: KeyPair, data: bytes, signature: bytes) -> bool:
        try:
            public_key_obj = Ed25519PublicKey.from_public_bytes(keypair.public_key)
            public_key_obj.verify(signature, data)
            return True
        except Exception as e:
            logger.warning(f"Signature verification failed: {e}")
            return False

    @staticmethod
    def _derive_did_key(public_key: bytes) -> str:
        if len(public_key) != 32:
            raise KeyManagerError("Public key must be 32 bytes for Ed25519")

        combined = MULTICODEC_ED25519_PREFIX + public_key
        encoded = bytes_to_multibase(combined)
        return f"did:key:{encoded}"

    @staticmethod
    def _derive_key(password: str, salt: bytes) -> bytes:
        import hashlib

        info = b"DIAP_KEY_V2"
        combined = password.encode() + salt + info
        return hashlib.sha256(combined).digest()


class KeyManagerInstance:
    def __init__(self, store_path: Optional[str] = None):
        self.store_path = store_path or self._default_store_path()
        self._key_cache: Dict[str, KeyPair] = {}

    def _default_store_path(self) -> str:
        home = os.path.expanduser("~")
        return os.path.join(home, ".diap", "keys")

    def generate(self) -> KeyPair:
        return KeyManager.generate()

    def from_private_key(self, private_key: bytes) -> KeyPair:
        return KeyManager.from_private_key(private_key)

    async def from_file(self, path: str) -> KeyPair:
        return await KeyManager.from_file(path)

    async def save_to_file(self, keypair: KeyPair, path: str) -> None:
        return await KeyManager.save_to_file(keypair, path)

    def export_backup(self, keypair: KeyPair, password: Optional[str] = None) -> KeyBackup:
        return KeyManager.export_backup(keypair, password)

    def import_from_backup(self, backup: KeyBackup, password: Optional[str] = None) -> KeyPair:
        return KeyManager.import_from_backup(backup, password)

    def sign(self, keypair: KeyPair, data: bytes) -> bytes:
        return KeyManager.sign(keypair, data)

    def verify(self, keypair: KeyPair, data: bytes, signature: bytes) -> bool:
        return KeyManager.verify(keypair, data, signature)

    def load_or_generate(
        self, key_id: str = "default", store: Optional[KeyStoreConfig] = None
    ) -> KeyPair:
        if key_id in self._key_cache:
            return self._key_cache[key_id]

        store_config = store or KeyStoreConfig(path=self._get_key_path(key_id))
        key_path = store_config.path or self._get_key_path(key_id)

        if os.path.exists(key_path):
            try:
                import asyncio

                key_pair = asyncio.run(KeyManager.from_file(key_path))
                self._key_cache[key_id] = key_pair
                logger.info(f"Loaded existing key pair for: {key_id}")
                return key_pair
            except Exception as e:
                logger.warning(f"Failed to load key pair: {e}, generating new one")

        key_pair = KeyManager.generate()
        asyncio.run(KeyManager.save_to_file(key_pair, key_path))
        self._key_cache[key_id] = key_pair
        logger.info(f"Generated and saved new key pair for: {key_id}")
        return key_pair

    def _get_key_path(self, key_id: str) -> str:
        return os.path.join(self.store_path, f"{key_id}.json")

    def delete_key(self, key_id: str):
        if key_id in self._key_cache:
            del self._key_cache[key_id]

        key_path = self._get_key_path(key_id)
        if os.path.exists(key_path):
            os.remove(key_path)
            logger.info(f"Deleted key: {key_id}")

    def list_keys(self) -> list:
        if not os.path.exists(self.store_path):
            return []
        return [f.replace(".json", "") for f in os.listdir(self.store_path) if f.endswith(".json")]
