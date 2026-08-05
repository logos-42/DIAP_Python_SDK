"""
DIAP Python SDK - Iroh 节点（真实 iroh 实现）

基于官方 iroh Python 绑定（iroh==0.31.0）的真实节点管理：
- 内存节点：Iroh.memory()
- 持久化节点：Iroh.persistent(path)
- 节点发现：add_node_addr + remote_info_list
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any

import iroh
from iroh.iroh_ffi import uniffi_set_event_loop

from .types.errors import NetworkError
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
        self._iroh_node: Optional[iroh.Iroh] = None
        self._node_id: Optional[str] = None
        self._listen_addresses: List[str] = []
        self._running = False
        self._peer_ids: List[str] = []
        self._started_at: Optional[str] = None

    async def start(self) -> IrohNodeStatus:
        if self._running:
            return self.get_status()

        # iroh 0.31 uniffi callback 需要全局 event loop
        uniffi_set_event_loop(asyncio.get_running_loop())

        try:
            if self.config.storage_path:
                self._iroh_node = await iroh.Iroh.persistent(self.config.storage_path)
            else:
                self._iroh_node = await iroh.Iroh.memory()

            net = self._iroh_node.net()
            self._node_id = await net.node_id()
            self._running = True
            self._started_at = datetime.utcnow().isoformat() + "Z"

            # 获取本机地址信息
            try:
                addr = await net.node_addr()
                self._listen_addresses = addr.direct_addresses()
            except Exception:
                self._listen_addresses = []

            if self.config.relay_enabled and self.config.relay_servers:
                for relay in self.config.relay_servers:
                    logger.info(f"Relay server configured: {relay}")

            if self.config.bootstrap_nodes:
                await self._bootstrap()

            logger.info(f"Iroh node started: {self._node_id[:16]}...")
            return self.get_status()
        except Exception as e:
            raise NetworkError(f"Failed to start Iroh node: {e}")

    async def stop(self):
        if not self._running:
            return

        self._running = False
        # iroh 0.31 无 shutdown API（进程退出时自动回收）
        self._iroh_node = None
        self._peer_ids.clear()
        self._started_at = None
        logger.info(f"Iroh node stopped: {self._node_id[:16]}..." if self._node_id else "Iroh node stopped")

    async def _bootstrap(self):
        if not self._iroh_node:
            return
        net = self._iroh_node.net()
        for node_addr in self.config.bootstrap_nodes:
            try:
                # 支持 node_id 或 node_id@relay 格式
                parts = node_addr.split("@")
                node_id_hex = parts[0]
                relay = parts[1] if len(parts) > 1 else None
                pub_key = iroh.PublicKey.from_string(node_id_hex)
                await net.add_node_addr(
                    iroh.NodeAddr(pub_key, relay, [])
                )
                if node_id_hex not in self._peer_ids:
                    self._peer_ids.append(node_id_hex)
                logger.info(f"Bootstrapped node: {node_id_hex[:16]}...")
            except Exception as e:
                logger.warning(f"Bootstrap failed for {node_addr}: {e}")

    async def connect_peer(
        self,
        peer_addr: str,
        timeout: float = 30.0,
    ) -> bool:
        if not self._running or not self._iroh_node:
            raise NetworkError("Node not running")

        try:
            parts = peer_addr.split("@")
            node_id_hex = parts[0]
            relay = parts[1] if len(parts) > 1 else None
            pub_key = iroh.PublicKey.from_string(node_id_hex)

            net = self._iroh_node.net()
            direct: List[str] = []
            remote = None
            try:
                remote = await net.remote_info(pub_key)
            except Exception:
                remote = None
            if remote is not None:
                try:
                    relay = relay or remote.relay_url
                except Exception:
                    pass
                try:
                    direct = [str(a) for a in remote.addrs]
                except Exception:
                    direct = []
            if relay is None:
                try:
                    relay = await net.home_relay()
                except Exception:
                    relay = None

            await net.add_node_addr(iroh.NodeAddr(pub_key, relay, direct))
            if node_id_hex not in self._peer_ids:
                self._peer_ids.append(node_id_hex)
            logger.info(f"Connected to peer: {node_id_hex[:16]}...")
            return True
        except Exception as e:
            logger.error(f"Connect peer failed: {e}")
            return False

    async def disconnect_peer(self, peer_id: str) -> bool:
        if peer_id in self._peer_ids:
            self._peer_ids.remove(peer_id)
            logger.info(f"Disconnected from peer: {peer_id[:16]}...")
            return True
        return False

    def get_status(self) -> IrohNodeStatus:
        return IrohNodeStatus(
            node_id=self._node_id or "",
            listen_addresses=self._listen_addresses,
            is_running=self._running,
            peer_count=len(self._peer_ids),
            started_at=self._started_at,
        )

    async def get_peers(self) -> List[str]:
        if not self._iroh_node:
            return list(self._peer_ids)
        try:
            remotes = await self._iroh_node.net().remote_info_list()
            for r in remotes:
                try:
                    nid = str(r.node_id)
                    if nid not in self._peer_ids:
                        self._peer_ids.append(nid)
                except Exception:
                    pass
        except Exception:
            pass
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
