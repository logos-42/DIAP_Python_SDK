import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from .types.errors import VerificationError
from .utils.crypto import sha256_hash, generate_random_bytes
from .utils.encoding import bytes_to_hex, hex_to_bytes
from .utils.logger import get_logger

logger = get_logger(__name__)


class BidirectionalVerificationError(Exception):
    pass


@dataclass
class VerificationChallenge:
    challenge_id: str
    challenge: str
    created_at: str
    expires_at: str
    used: bool = False


@dataclass
class VerificationResult:
    is_valid: bool
    node_id: str
    timestamp: str
    method: str
    details: Optional[Dict[str, Any]] = None


class IPFSBidirectionalVerifier:
    def __init__(
        self,
        ipfs_client,
        node_id: str,
        private_key: bytes,
    ):
        self.ipfs_client = ipfs_client
        self.node_id = node_id
        self.private_key = private_key
        self._challenges: Dict[str, VerificationChallenge] = {}
        self._verification_log: List[VerificationResult] = []

    async def initiate_verification(
        self,
        peer_id: str,
        peer_addr: Optional[str] = None,
        ttl: int = 300,
    ) -> str:
        challenge_id = generate_random_bytes(16).hex()
        challenge = generate_random_bytes(32).hex()

        created_at = datetime.utcnow()
        expires_at = created_at + timedelta(seconds=ttl)

        verification_challenge = VerificationChallenge(
            challenge_id=challenge_id,
            challenge=challenge,
            created_at=created_at.isoformat() + "Z",
            expires_at=expires_at.isoformat() + "Z",
        )

        self._challenges[challenge_id] = verification_challenge

        logger.info(f"Initiated verification with peer: {peer_id}")
        return challenge_id

    async def respond_to_verification(
        self,
        challenge_id: str,
        peer_id: str,
        response: str,
    ) -> bool:
        if challenge_id not in self._challenges:
            logger.warning(f"Unknown challenge: {challenge_id}")
            return False

        challenge = self._challenges[challenge_id]

        expires = datetime.fromisoformat(challenge.expires_at.replace("Z", "+00:00"))
        if datetime.utcnow() > expires.replace(tzinfo=None):
            logger.warning(f"Challenge expired: {challenge_id}")
            del self._challenges[challenge_id]
            return False

        expected_response = self._compute_response(peer_id, challenge.challenge)

        if response != expected_response:
            logger.warning("Invalid verification response")
            return False

        challenge.used = True

        result = VerificationResult(
            is_valid=True,
            node_id=peer_id,
            timestamp=datetime.utcnow().isoformat() + "Z",
            method="bidirectional_challenge",
            details={"challenge_id": challenge_id},
        )

        self._verification_log.append(result)
        logger.info(f"Verification successful for peer: {peer_id}")
        return True

    async def verify_peer(
        self,
        peer_id: str,
        peer_challenge: str,
        peer_response: str,
        peer_signature: bytes,
    ) -> VerificationResult:
        try:
            expected = self._compute_response(self.node_id, peer_challenge)

            if peer_response != expected:
                result = VerificationResult(
                    is_valid=False,
                    node_id=peer_id,
                    timestamp=datetime.utcnow().isoformat() + "Z",
                    method="bidirectional_verification",
                    details={"error": "Response mismatch"},
                )
                self._verification_log.append(result)
                return result

            from cryptography.hazmat.primitives.asymmetric.ed25519 import (
                Ed25519PublicKey,
            )

            public_key_bytes = hex_to_bytes(peer_id[:64])
            public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)

            message = f"{peer_id}:{peer_challenge}".encode()
            public_key.verify(peer_signature, message)

            result = VerificationResult(
                is_valid=True,
                node_id=peer_id,
                timestamp=datetime.utcnow().isoformat() + "Z",
                method="bidirectional_verification",
                details={"verified": True},
            )

            self._verification_log.append(result)
            logger.info(f"Peer verification successful: {peer_id}")
            return result

        except Exception as e:
            logger.error(f"Peer verification error: {e}")
            result = VerificationResult(
                is_valid=False,
                node_id=peer_id,
                timestamp=datetime.utcnow().isoformat() + "Z",
                method="bidirectional_verification",
                details={"error": str(e)},
            )
            self._verification_log.append(result)
            return result

    async def verify_content(
        self,
        cid: str,
        expected_hash: str,
    ) -> VerificationResult:
        try:
            content = await self.ipfs_client.get_raw(cid)

            if not content:
                return VerificationResult(
                    is_valid=False,
                    node_id=self.node_id,
                    timestamp=datetime.utcnow().isoformat() + "Z",
                    method="content_verification",
                    details={"error": "Content not found"},
                )

            actual_hash = sha256_hash(content).hex()

            is_valid = actual_hash == expected_hash

            result = VerificationResult(
                is_valid=is_valid,
                node_id=self.node_id,
                timestamp=datetime.utcnow().isoformat() + "Z",
                method="content_verification",
                details={
                    "cid": cid,
                    "expected_hash": expected_hash,
                    "actual_hash": actual_hash,
                    "match": is_valid,
                },
            )

            self._verification_log.append(result)
            return result

        except Exception as e:
            logger.error(f"Content verification error: {e}")
            return VerificationResult(
                is_valid=False,
                node_id=self.node_id,
                timestamp=datetime.utcnow().isoformat() + "Z",
                method="content_verification",
                details={"error": str(e)},
            )

    def _compute_response(self, node_id: str, challenge: str) -> str:
        message = f"{node_id}:{challenge}".encode()
        return sha256_hash(message).hex()

    def get_verification_history(
        self,
        peer_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[VerificationResult]:
        if peer_id:
            return [r for r in self._verification_log if r.node_id == peer_id][:limit]
        return self._verification_log[:limit]

    def clear_history(self):
        self._verification_log.clear()

    async def cleanup_expired_challenges(self) -> int:
        now = datetime.utcnow()
        expired = [
            cid
            for cid, c in self._challenges.items()
            if datetime.fromisoformat(c.expires_at.replace("Z", "+00:00")).replace(
                tzinfo=None
            )
            < now
        ]

        for cid in expired:
            del self._challenges[cid]

        if expired:
            logger.debug(f"Cleaned up {len(expired)} expired challenges")

        return len(expired)
