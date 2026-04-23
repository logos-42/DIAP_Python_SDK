import time
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta

from cachetools import TTLCache

from .types.did_types import DIDDocument
from .types.errors import DIDBuilderError
from .utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class CacheEntry:
    document: DIDDocument
    timestamp: float
    ttl: int


class DIDCache:
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._memory_cache: TTLCache = TTLCache(maxsize=max_size, ttl=default_ttl)
        self._hits = 0
        self._misses = 0

    def get(self, did: str) -> Optional[DIDDocument]:
        try:
            entry = self._memory_cache.get(did)
            if entry is None:
                self._misses += 1
                return None

            if self._is_expired(entry):
                self._memory_cache.pop(did, None)
                self._misses += 1
                return None

            self._hits += 1
            logger.debug(f"Cache hit for DID: {did}")
            return entry.document
        except Exception as e:
            logger.warning(f"Cache get error: {e}")
            return None

    def set(self, did: str, document: DIDDocument, ttl: Optional[int] = None):
        ttl = ttl or self.default_ttl
        try:
            entry = CacheEntry(
                document=document,
                timestamp=time.time(),
                ttl=ttl,
            )
            self._memory_cache[did] = entry
            logger.debug(f"Cached DID document for: {did}")
        except Exception as e:
            logger.warning(f"Cache set error: {e}")

    def invalidate(self, did: str):
        if did in self._memory_cache:
            self._memory_cache.pop(did)
            logger.debug(f"Invalidated cache for: {did}")

    def clear(self):
        self._memory_cache.clear()
        self._hits = 0
        self._misses = 0
        logger.info("Cache cleared")

    def _is_expired(self, entry: CacheEntry) -> bool:
        return time.time() - entry.timestamp > entry.ttl

    def get_stats(self) -> Dict[str, Any]:
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0

        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
            "size": len(self._memory_cache),
            "max_size": self.max_size,
        }

    def cleanup_expired(self):
        expired_keys = [
            did for did, entry in self._memory_cache.items() if self._is_expired(entry)
        ]
        for key in expired_keys:
            self._memory_cache.pop(key, None)

        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired entries")


class PersistentDIDCache:
    def __init__(self, cache_dir: str):
        import os
        import json
        from pathlib import Path

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.memory_cache = DIDCache()

    def get(self, did: str) -> Optional[DIDDocument]:
        cached = self.memory_cache.get(did)
        if cached:
            return cached

        filepath = self._get_cache_path(did)
        if filepath.exists():
            try:
                with open(filepath, "r") as f:
                    data = json.load(f)
                document = DIDDocument.from_dict(data)
                self.memory_cache.set(did, document)
                return document
            except Exception as e:
                logger.warning(f"Failed to load cached DID: {e}")
                return None

        return None

    def set(self, did: str, document: DIDDocument, ttl: Optional[int] = None):
        self.memory_cache.set(did, document, ttl)

        filepath = self._get_cache_path(did)
        try:
            with open(filepath, "w") as f:
                json.dump(document.to_dict(), f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to persist DID cache: {e}")

    def invalidate(self, did: str):
        self.memory_cache.invalidate(did)

        filepath = self._get_cache_path(did)
        if filepath.exists():
            filepath.unlink()

    def clear(self):
        self.memory_cache.clear()

        for filepath in self.cache_dir.glob("*.json"):
            filepath.unlink()

    def _get_cache_path(self, did: str) -> "Path":
        safe_did = did.replace(":", "_").replace("/", "_")
        return self.cache_dir / f"{safe_did}.json"
