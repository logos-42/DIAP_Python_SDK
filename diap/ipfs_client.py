import json
import aiohttp
import ipfshttpclient
from typing import Optional, Dict, Any, Union
from pathlib import Path

from .types.errors import IPFSError
from .utils.logger import get_logger

logger = get_logger(__name__)


class IPFSClient:
    def __init__(
        self,
        host: str = "localhost",
        port: int = 5001,
        protocol: str = "http",
        gateway_host: str = "localhost",
        gateway_port: int = 8080,
        gateway_protocol: str = "http",
    ):
        self.host = host
        self.port = port
        self.protocol = protocol
        self.gateway_host = gateway_host
        self.gateway_port = gateway_port
        self.gateway_protocol = gateway_protocol
        self._client: Optional[ipfshttpclient.Client] = None

    def _get_client(self) -> ipfshttpclient.Client:
        if self._client is None:
            try:
                addr = f"{self.protocol}://{self.host}:{self.port}"
                self._client = ipfshttpclient.Client(addr)
            except Exception as e:
                raise IPFSError(f"Failed to connect to IPFS: {e}")
        return self._client

    async def add(
        self, data: Union[str, bytes], content_type: Optional[str] = None
    ) -> str:
        if isinstance(data, str):
            data = data.encode()

        try:
            client = self._get_client()
            result = client.add_bytes(data)
            logger.debug(f"Added data to IPFS, CID: {result}")
            return result
        except Exception as e:
            raise IPFSError(f"Failed to add data: {e}")

    async def add_file(self, filepath: str) -> str:
        try:
            client = self._get_client()
            with open(filepath, "rb") as f:
                result = client.add_bytes(f.read())
            logger.debug(f"Added file to IPFS, CID: {result}")
            return result
        except Exception as e:
            raise IPFSError(f"Failed to add file: {e}")

    async def get(self, cid: str) -> Optional[Dict[str, Any]]:
        try:
            client = self._get_client()
            data = client.cat(cid)
            if isinstance(data, bytes):
                data = data.decode()
            result = json.loads(data)
            logger.debug(f"Retrieved data from IPFS, CID: {cid}")
            return result
        except json.JSONDecodeError:
            return data
        except Exception as e:
            raise IPFSError(f"Failed to get data: {e}")

    async def get_raw(self, cid: str) -> bytes:
        try:
            client = self._get_client()
            return client.cat(cid)
        except Exception as e:
            raise IPFSError(f"Failed to get raw data: {e}")

    async def pin_add(self, cid: str) -> bool:
        try:
            client = self._get_client()
            client.pin.add(cid)
            logger.debug(f"Pinned CID: {cid}")
            return True
        except Exception as e:
            raise IPFSError(f"Failed to pin: {e}")

    async def pin_remove(self, cid: str) -> bool:
        try:
            client = self._get_client()
            client.pin.rm(cid)
            logger.debug(f"Unpinned CID: {cid}")
            return True
        except Exception as e:
            raise IPFSError(f"Failed to unpin: {e}")

    async def pin_list(self) -> list:
        try:
            client = self._get_client()
            pins = client.pin.ls()
            return list(pins)
        except Exception as e:
            raise IPFSError(f"Failed to list pins: {e}")

    async def refs(self, cid: str) -> list:
        try:
            client = self._get_client()
            refs = client.refs(cid)
            return list(refs)
        except Exception as e:
            raise IPFSError(f"Failed to get refs: {e}")

    async def dag_put(self, data: Dict[str, Any]) -> str:
        try:
            client = self._get_client()
            result = client.dag.put(data)
            logger.debug(f"Put DAG, CID: {result}")
            return str(result)
        except Exception as e:
            raise IPFSError(f"Failed to put DAG: {e}")

    async def dag_get(self, cid: str) -> Optional[Dict[str, Any]]:
        try:
            client = self._get_client()
            result = client.dag.get(cid)
            return result
        except Exception as e:
            raise IPFSError(f"Failed to get DAG: {e}")

    def get_gateway_url(self, cid: str, path: Optional[str] = None) -> str:
        base = f"{self.gateway_protocol}://{self.gateway_host}:{self.gateway_port}/ipfs/{cid}"
        if path:
            return f"{base}/{path}"
        return base

    async def resolve(self, name: str) -> Optional[str]:
        try:
            client = self._get_client()
            result = client.name.resolve(name)
            return result
        except Exception as e:
            logger.warning(f"Failed to resolve name: {e}")
            return None

    async def id(self) -> Dict[str, Any]:
        try:
            client = self._get_client()
            return client.id()
        except Exception as e:
            raise IPFSError(f"Failed to get ID: {e}")

    async def swarm_peers(self) -> list:
        try:
            client = self._get_client()
            return list(client.swarm.peers())
        except Exception as e:
            raise IPFSError(f"Failed to get swarm peers: {e}")

    async def stats_repo(self) -> Dict[str, Any]:
        try:
            client = self._get_client()
            return client.repo.stat()
        except Exception as e:
            raise IPFSError(f"Failed to get repo stats: {e}")

    def close(self):
        if self._client is not None:
            try:
                self._client.close()
            except:
                pass
            self._client = None


class MultiAddrIPFSClient(IPFSClient):
    def __init__(self, multiaddr: str, **kwargs):
        super().__init__(**kwargs)
        self.multiaddr = multiaddr
        self._client: Optional[ipfshttpclient.Client] = None

    def _get_client(self) -> ipfshttpclient.Client:
        if self._client is None:
            try:
                self._client = ipfshttpclient.Client(self.multiaddr)
            except Exception as e:
                raise IPFSError(f"Failed to connect to IPFS: {e}")
        return self._client
