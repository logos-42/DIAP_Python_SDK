import asyncio
import json
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime

from .types.errors import NetworkError
from .utils.crypto import generate_random_bytes
from .utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class IrohNodeConfig:
    listen_addr: str = "/ip4/0.0.0.0/tcp/0"
    relay_enabled: bool = True
    relay_servers: List[str] = field(default_factory=list)
    bootstrap_nodes: List[str] = field(default_factory=list)
    storage_path: Optional[str] = None


@dataclass
class IrohNodeStatus:
    node_id: str
    listen_addresses: List[str]
    is_running: bool
    peer_count: int
    started_at: Optional[str] = None


class IrohNode:
    def __init__(
        self,
        config: Optional[IrohNodeConfig] = None,
    ):
        self.config = config or IrohNodeConfig()
        self._node_id: Optional[str] = None
        self._listen_addresses: List[str] = []
        self._running = False
        self._bootstrap_task: Optional[asyncio.Task] = None
        self._peer_ids: List[str] = []

    async def start(self) -> IrohNodeStatus:
        if self._running:
            return self.get_status()

        self._node_id = generate_random_bytes(16).hex()
        self._running = True

        if self.config.relay_enabled:
            await self._setup_relay()

        if self.config.bootstrap_nodes:
            await self._bootstrap()

        logger.info(f"Iroh node started: {self._node_id}")

        return self.get_status()

    async def stop(self):
        if not self._running:
            return

        self._running = False

        if self._bootstrap_task:
            self._bootstrap_task.cancel()
            try:
                await self._bootstrap_task
            except asyncio.CancelledError:
                pass

        self._peer_ids.clear()
        logger.info(f"Iroh node stopped: {self._node_id}")

    async def _setup_relay(self):
        if self.config.relay_servers:
            logger.info(f"Relay servers configured: {len(self.config.relay_servers)}")

    async def _bootstrap(self):
        logger.info(f"Bootstrapping from {len(self.config.bootstrap_nodes)} nodes")

    async def connect_peer(
        self,
        peer_addr: str,
        timeout: float = 30.0,
    ) -> bool:
        if not self._running:
            raise NetworkError("Node not running")

        logger.info(f"Connecting to peer: {peer_addr}")
        return True

    async def disconnect_peer(self, peer_id: str) -> bool:
        if peer_id in self._peer_ids:
            self._peer_ids.remove(peer_id)
            logger.info(f"Disconnected from peer: {peer_id}")
            return True
        return False

    def get_status(self) -> IrohNodeStatus:
        return IrohNodeStatus(
            node_id=self._node_id or "",
            listen_addresses=self._listen_addresses,
            is_running=self._running,
            peer_count=len(self._peer_ids),
            started_at=datetime.utcnow().isoformat() + "Z" if self._running else None,
        )

    async def get_peers(self) -> List[str]:
        return list(self._peer_ids)

    async def add_bootstrap_node(self, addr: str):
        if addr not in self.config.bootstrap_nodes:
            self.config.bootstrap_nodes.append(addr)
            logger.info(f"Added bootstrap node: {addr}")

    async def remove_bootstrap_node(self, addr: str):
        if addr in self.config.bootstrap_nodes:
            self.config.bootstrap_nodes.remove(addr)
            logger.info(f"Removed bootstrap node: {addr}")

    async def get_stats(self) -> Dict[str, Any]:
        status = self.get_status()
        return {
            "node_id": status.node_id,
            "is_running": status.is_running,
            "peer_count": status.peer_count,
            "relay_enabled": self.config.relay_enabled,
            "bootstrap_nodes": len(self.config.bootstrap_nodes),
            "relay_servers": len(self.config.relay_servers),
            "listen_addr": self.config.listen_addr,
        }
