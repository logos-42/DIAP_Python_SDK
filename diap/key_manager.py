import os
import json
import hashlib
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass, asdict

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

from .types.key_types import KeyPair, KeyBackup, KeyStoreConfig
from .types.errors import KeyManagerError, CryptoError
from .utils.crypto import (
    generate_random_bytes,
    sha256_hash,
    aes_gcm_encrypt,
    aes_gcm_decrypt,
    base58_encode,
    base58_decode,
)
from .utils.encoding import bytes_to_multibase
from .utils.logger import get_logger

logger = get_logger(__name__)


class KeyManager:
    DEFAULT_KEY_TYPE = "Ed25519"

    def __init__(self, store_path: Optional[str] = None):
        self.store_path = store_path or self._default_store_path()
        self._key_cache: dict[str, KeyPair] = {}

    def _default_store_path(self) -> str:
        home = os.path.expanduser("~")
        return os.path.join(home, ".diap", "keys")

    def generate_key_pair(self, key_type: str = "Ed25519") -> KeyPair:
        if key_type != "Ed25519":
            raise KeyManagerError(f"Unsupported key type: {key_type}")

        private_key_obj = Ed25519PrivateKey.generate()
        private_bytes = private_key_obj.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )

        public_key_obj = private_key_obj.public_key()
        public_bytes = public_key_obj.public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
        )

        did = self._derive_did_key(public_bytes)

        key_pair = KeyPair(
            private_key=private_bytes,
            public_key=public_bytes,
            did=did,
            key_type=key_type,
        )

        logger.info(f"Generated new key pair with DID: {did}")
        return key_pair

    def _derive_did_key(self, public_key: bytes) -> str:
        from .utils.crypto import sha256_hash

        key_hash = sha256_hash(public_key)
        multicodec_prefix = bytes([0xED, 0x01])
        prefixed_key = multicodec_prefix + key_hash[:32]
        did_key = f"did:key:{bytes_to_multibase(prefixed_key)}"
        return did_key

    def load_or_generate(
        self, key_id: str = "default", store: Optional[KeyStoreConfig] = None
    ) -> KeyPair:
        if key_id in self._key_cache:
            return self._key_cache[key_id]

        store_config = store or KeyStoreConfig(path=self._get_key_path(key_id))
        key_path = store_config.path or self._get_key_path(key_id)

        if os.path.exists(key_path):
            try:
                key_pair = self._load_from_file(key_path, store_config.password)
                self._key_cache[key_id] = key_pair
                logger.info(f"Loaded existing key pair for: {key_id}")
                return key_pair
            except Exception as e:
                logger.warning(f"Failed to load key pair: {e}, generating new one")

        key_pair = self.generate_key_pair()
        self._save_to_file(key_path, key_pair, store_config.password)
        self._key_cache[key_id] = key_pair
        logger.info(f"Generated and saved new key pair for: {key_id}")
        return key_pair

    def _get_key_path(self, key_id: str) -> str:
        return os.path.join(self.store_path, f"{key_id}.json")

    def _load_from_file(self, path: str, password: Optional[str] = None) -> KeyPair:
        with open(path, "r") as f:
            data = json.load(f)

        if password:
            encrypted_data = base58_decode(data["encrypted_key"])
            key = sha256_hash(password.encode())
            nonce = base58_decode(data["nonce"])
            decrypted = aes_gcm_decrypt(key, encrypted_data, nonce)
            private_key = decrypted[:32]
        else:
            private_key = base58_decode(data["private_key"])

        public_key = base58_decode(data["public_key"])

        return KeyPair(
            private_key=private_key,
            public_key=public_key,
            did=data["did"],
            key_type=data.get("key_type", self.DEFAULT_KEY_TYPE),
        )

    def _save_to_file(
        self, path: str, key_pair: KeyPair, password: Optional[str] = None
    ):
        os.makedirs(os.path.dirname(path), exist_ok=True)

        if password:
            key = sha256_hash(password.encode())
            nonce = generate_random_bytes(12)
            encrypted, _, _ = aes_gcm_encrypt(key, key_pair.private_key, nonce)
            data = {
                "encrypted_key": base58_encode(encrypted).encode().decode(),
                "nonce": base58_encode(nonce).encode().decode(),
                "did": key_pair.did,
                "key_type": key_pair.key_type,
            }
        else:
            data = {
                "private_key": base58_encode(key_pair.private_key).encode().decode(),
                "public_key": base58_encode(key_pair.public_key).encode().decode(),
                "did": key_pair.did,
                "key_type": key_pair.key_type,
            }

        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def sign(self, key_pair: KeyPair, message: bytes) -> bytes:
        private_key_obj = Ed25519PrivateKey.from_private_bytes(key_pair.private_key)
        signature = private_key_obj.sign(message)
        return signature

    def verify(self, key_pair: KeyPair, message: bytes, signature: bytes) -> bool:
        public_key_obj = Ed25519PublicKey.from_public_bytes(key_pair.public_key)
        try:
            public_key_obj.verify(signature, message)
            return True
        except Exception:
            return False

    def export_key_pair(
        self, key_pair: KeyPair, password: Optional[str] = None
    ) -> KeyBackup:
        if password:
            key = sha256_hash(password.encode())
            nonce = generate_random_bytes(12)
            encrypted, _, _ = aes_gcm_encrypt(key, key_pair.private_key, nonce)
            encrypted_data = base58_encode(encrypted)
        else:
            encrypted_data = base58_encode(key_pair.private_key)

        return KeyBackup(
            encrypted_data=encrypted_data,
            mnemonic=None,
            exported_at=datetime.now().isoformat(),
        )

    def import_key_pair(
        self, backup: KeyBackup, password: Optional[str] = None
    ) -> KeyPair:
        encrypted_data = base58_decode(backup.encrypted_data)

        if password:
            key = sha256_hash(password.encode())
            nonce = encrypted_data[-12:]
            ciphertext = encrypted_data[:-12]
            private_key = aes_gcm_decrypt(key, ciphertext, nonce)
        else:
            private_key = encrypted_data

        private_key_obj = Ed25519PrivateKey.from_private_bytes(private_key[:32])
        public_bytes = private_key_obj.public_key().public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
        )

        did = self._derive_did_key(public_bytes)

        return KeyPair(
            private_key=private_key[:32],
            public_key=public_bytes,
            did=did,
            key_type=self.DEFAULT_KEY_TYPE,
        )

    def delete_key(self, key_id: str):
        if key_id in self._key_cache:
            del self._key_cache[key_id]

        key_path = self._get_key_path(key_id)
        if os.path.exists(key_path):
            os.remove(key_path)
            logger.info(f"Deleted key: {key_id}")

    def list_keys(self) -> list[str]:
        if not os.path.exists(self.store_path):
            return []
        return [
            f.replace(".json", "")
            for f in os.listdir(self.store_path)
            if f.endswith(".json")
        ]


from datetime import datetime
