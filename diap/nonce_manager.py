import time
import asyncio
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from cachetools import TTLCache

from .types.errors import AgentAuthError
from .utils.crypto import sha256_hash, generate_random_bytes
from .utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class NonceEntry:
    nonce: str
    created_at: float
    expires_at: float
    used: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class NonceManager:
    def __init__(
        self,
        max_size: int = 10000,
        default_ttl: int = 300,
        cleanup_interval: int = 60,
    ):
        self.default_ttl = default_ttl
        self.cleanup_interval = cleanup_interval
        self._nonces: Dict[str, NonceEntry] = {}
        self._cache = TTLCache(maxsize=max_size, ttl=default_ttl)
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self):
        if self._running:
            return

        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("NonceManager started")

    async def stop(self):
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("NonceManager stopped")

    async def generate(
        self,
        entity_id: Optional[str] = None,
        ttl: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        nonce = generate_random_bytes(32).hex()

        ttl = ttl or self.default_ttl
        now = time.time()

        entry = NonceEntry(
            nonce=nonce,
            created_at=now,
            expires_at=now + ttl,
            metadata=metadata or {},
        )

        if entity_id:
            entry.metadata["entity_id"] = entity_id

        async with self._lock:
            self._nonces[nonce] = entry
            self._cache[nonce] = entry

        logger.debug(f"Generated nonce: {nonce[:16]}... for entity: {entity_id}")
        return nonce

    async def verify(
        self,
        nonce: str,
        entity_id: Optional[str] = None,
        consume: bool = False,
    ) -> bool:
        async with self._lock:
            entry = self._nonces.get(nonce)

            if not entry:
                logger.warning(f"Nonce not found: {nonce[:16]}...")
                return False

            if entry.used:
                logger.warning(f"Nonce already used: {nonce[:16]}...")
                return False

            now = time.time()
            if now > entry.expires_at:
                logger.warning(f"Nonce expired: {nonce[:16]}...")
                del self._nonces[nonce]
                self._cache.pop(nonce, None)
                return False

            if entity_id:
                if entry.metadata.get("entity_id") != entity_id:
                    logger.warning(f"Entity ID mismatch for nonce: {nonce[:16]}...")
                    return False

            if consume:
                entry.used = True
                del self._nonces[nonce]
                self._cache.pop(nonce, None)
                logger.debug(f"Nonce consumed: {nonce[:16]}...")

            return True

    async def revoke(self, nonce: str) -> bool:
        async with self._lock:
            if nonce in self._nonces:
                del self._nonces[nonce]
                self._cache.pop(nonce, None)
                logger.debug(f"Revoked nonce: {nonce[:16]}...")
                return True

        return False

    async def revoke_all(self, entity_id: str) -> int:
        count = 0
        async with self._lock:
            to_remove = [
                nonce
                for nonce, entry in self._nonces.items()
                if entry.metadata.get("entity_id") == entity_id
            ]

            for nonce in to_remove:
                del self._nonces[nonce]
                self._cache.pop(nonce, None)
                count += 1

        if count > 0:
            logger.info(f"Revoked {count} nonces for entity: {entity_id}")

        return count

    async def cleanup_expired(self) -> int:
        count = 0
        now = time.time()

        async with self._lock:
            expired = [
                nonce for nonce, entry in self._nonces.items() if now > entry.expires_at
            ]

            for nonce in expired:
                del self._nonces[nonce]
                self._cache.pop(nonce, None)
                count += 1

        if count > 0:
            logger.debug(f"Cleaned up {count} expired nonces")

        return count

    async def get_stats(self) -> Dict[str, Any]:
        now = time.time()

        async with self._lock:
            total = len(self._nonces)
            active = sum(
                1 for e in self._nonces.values() if not e.used and now <= e.expires_at
            )
            expired = sum(1 for e in self._nonces.values() if now > e.expires_at)
            used = sum(1 for e in self._nonces.values() if e.used)

            return {
                "total": total,
                "active": active,
                "expired": expired,
                "used": used,
                "cache_size": len(self._cache),
            }

    async def _cleanup_loop(self):
        while self._running:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self.cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup error: {e}")


class DistributedNonceManager(NonceManager):
    def __init__(self, redis_client=None, **kwargs):
        super().__init__(**kwargs)
        self.redis_client = redis_client

    async def _get_from_store(self, nonce: str) -> Optional[NonceEntry]:
        if not self.redis_client:
            return self._nonces.get(nonce)

        try:
            import json

            key = f"nonce:{nonce}"
            data = await self.redis_client.get(key)
            if data:
                entry_dict = json.loads(data)
                return NonceEntry(**entry_dict)
        except Exception as e:
            logger.error(f"Redis get error: {e}")

        return None

    async def _store_entry(self, entry: NonceEntry):
        if not self.redis_client:
            return

        try:
            import json

            key = f"nonce:{entry.nonce}"
            ttl = int(entry.expires_at - time.time())
            if ttl > 0:
                await self.redis_client.setex(key, ttl, json.dumps(entry.__dict__))
        except Exception as e:
            logger.error(f"Redis store error: {e}")
