import json
from typing import Optional, Tuple, Dict, Any
from datetime import datetime

from .types.errors import IPNSError
from .utils.logger import get_logger

logger = get_logger(__name__)


class IPNSManager:
    def __init__(self, ipfs_client):
        self.ipfs_client = ipfs_client

    async def publish(
        self,
        cid: str,
        key: Optional[str] = None,
        lifetime: str = "48h",
        ttl: Optional[int] = None,
    ) -> Tuple[str, str]:
        try:
            client = self.ipfs_client._get_client()

            if key:
                result = client.name.publish(cid, key=key, lifetime=lifetime)
            else:
                result = client.name.publish(cid, lifetime=lifetime)

            name = result.get("Name", "")
            value = result.get("Value", "")

            logger.info(f"Published to IPNS: {name} -> {value}")
            return name, value

        except Exception as e:
            raise IPNSError(f"Failed to publish to IPNS: {e}")

    async def resolve(
        self,
        name: str,
        recursive: bool = False,
        nocache: bool = False,
    ) -> Optional[str]:
        try:
            client = self.ipfs_client._get_client()

            opts = {}
            if recursive:
                opts["recursive"] = True
            if nocache:
                opts["nocache"] = True

            result = client.name.resolve(name, **opts)
            return result

        except Exception as e:
            logger.warning(f"Failed to resolve IPNS name: {e}")
            return None

    async def revoke(self, key: str) -> bool:
        try:
            client = self.ipfs_client._get_client()
            empty_cid = "QmNLei78zWmzUdbeRB3CiUfAizWUrbeeZh5K1rhAQKChof"

            client.name.publish(empty_cid, key=key)

            logger.info(f"Revoked IPNS key: {key}")
            return True

        except Exception as e:
            raise IPNSError(f"Failed to revoke IPNS name: {e}")

    async def list_keys(self) -> list:
        try:
            client = self.ipfs_client._get_client()
            keys = client.key.list()
            return keys.get("Keys", [])
        except Exception as e:
            raise IPNSError(f"Failed to list IPNS keys: {e}")

    async def gen_key(self, name: str, type: str = "rsa", size: int = 2048) -> str:
        try:
            client = self.ipfs_client._get_client()
            result = client.key.gen(name, type=type, size=size)
            return result.get("Id", "")

        except Exception as e:
            raise IPNSError(f"Failed to generate IPNS key: {e}")

    async def rm_key(self, name: str) -> bool:
        try:
            client = self.ipfs_client._get_client()
            client.key.rm(name)
            logger.info(f"Removed IPNS key: {name}")
            return True

        except Exception as e:
            raise IPNSError(f"Failed to remove IPNS key: {e}")

    async def rename_key(self, old_name: str, new_name: str) -> Tuple[bool, str]:
        try:
            client = self.ipfs_client._get_client()
            result = client.key.rename(old_name, new_name)

            was_overwritten = result.get("WasOverwrite", False)
            return was_overwritten, new_name

        except Exception as e:
            raise IPNSError(f"Failed to rename IPNS key: {e}")

    async def export_key(self, name: str, output_path: str) -> bool:
        try:
            import subprocess

            result = subprocess.run(
                ["ipfs", "key", "export", name, "-o", output_path],
                capture_output=True,
                text=True,
            )
            return result.returncode == 0

        except Exception as e:
            raise IPNSError(f"Failed to export IPNS key: {e}")

    async def import_key(
        self,
        name: str,
        input_path: str,
    ) -> str:
        try:
            import subprocess

            result = subprocess.run(
                ["ipfs", "key", "import", name, "-o", input_path],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                return name
            raise IPNSError(f"Key import failed: {result.stderr}")

        except Exception as e:
            raise IPNSError(f"Failed to import IPNS key: {e}")

    async def get_keys_stats(self) -> Dict[str, Any]:
        try:
            client = self.ipfs_client._get_client()
            keys = await self.list_keys()

            stats = {
                "total_keys": len(keys),
                "keys": [],
            }

            for key in keys:
                stats["keys"].append(
                    {
                        "name": key.get("Name"),
                        "id": key.get("Id"),
                    }
                )

            return stats

        except Exception as e:
            raise IPNSError(f"Failed to get keys stats: {e}")
