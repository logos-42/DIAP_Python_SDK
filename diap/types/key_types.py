from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from enum import Enum


class EncryptionAlgorithm(Enum):
    ED25519 = "ed25519"
    SECP256K1 = "secp256k1"
    RSA = "rsa"


@dataclass
class KeyPair:
    private_key: bytes
    public_key: bytes
    did: str
    key_type: str = "Ed25519"

    def get_private_key_hex(self) -> str:
        return self.private_key.hex()

    def get_public_key_hex(self) -> str:
        return self.public_key.hex()

    def get_multibase_encoded(self) -> str:
        from .encoding import bytes_to_multibase

        return bytes_to_multibase(self.public_key)


@dataclass
class KeyBackup:
    encrypted_data: str
    mnemonic: Optional[str] = None
    exported_at: str = ""


@dataclass
class KeyStoreConfig:
    store_type: str = "file"
    path: Optional[str] = None
    password: Optional[str] = None
    encrypted: bool = False


@dataclass
class SignOptions:
    encoding: str = "base58"
    canonicalize: bool = True


@dataclass
class VerifyOptions:
    strict: bool = True
    allow_malleability: bool = False


@dataclass
class EncryptedData:
    ciphertext: bytes
    nonce: bytes
    tag: Optional[bytes] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ciphertext": self.ciphertext.hex(),
            "nonce": self.nonce.hex(),
            "tag": self.tag.hex() if self.tag else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EncryptedData":
        return cls(
            ciphertext=bytes.fromhex(data["ciphertext"]),
            nonce=bytes.fromhex(data["nonce"]),
            tag=bytes.fromhex(data["tag"]) if data.get("tag") else None,
        )
