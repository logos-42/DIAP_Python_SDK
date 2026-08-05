"""
DIAP Python SDK - Libp2p P2P 通信器

基于 asyncio 实现的轻量级 P2P 通信器
保持与 TypeScript 版本相同的 API 设计
"""

import asyncio
import json
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Set

from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Libp2pConfig:
    """Libp2p 配置"""
    listen_addresses: List[str] = field(
        default_factory=lambda: ["/ip4/0.0.0.0/tcp/0", "/ip4/0.0.0.0/tcp/0/ws"]
    )
    bootstrap_peers: List[str] = field(default_factory=list)
    enable_nat_traversal: bool = True
    enable_relay: bool = True
    max_connections: int = 100


@dataclass
class Libp2pMessage:
    """Libp2p 消息"""
    id: str
    from_peer: str
    to_peer: Optional[str] = None
    topic: str = ""
    data: bytes = b""
    timestamp: int = 0
    signature: Optional[bytes] = None


@dataclass
class Libp2pConnection:
    """Libp2p 连接信息"""
    peer_id: str
    multiaddrs: List[str] = field(default_factory=list)
    connected_at: int = 0
    protocols: List[str] = field(default_factory=list)


class Libp2pCommunicator:
    """Libp2p P2P 通信器"""

    def __init__(self, config: Optional[Libp2pConfig] = None):
        self.config = config or Libp2pConfig()
        self._node_id: Optional[str] = None
        self._connections: Dict[str, Libp2pConnection] = {}
        self._event_handlers: Dict[str, Set[Callable]] = {}
        self._message_handlers: Dict[str, Callable] = {}
        self._is_running = False
        self._topics: Set[str] = set()

        logger.info("🔧 Libp2p P2P 通信器已创建")
        logger.info(f"  监听地址: {', '.join(self.config.listen_addresses)}")
        logger.info(f"  最大连接数: {self.config.max_connections}")

    async def start(self) -> None:
        """启动 Libp2p P2P 网络"""
        if self._is_running:
            logger.warning("⚠️ Libp2p 节点已在运行")
            return

        try:
            logger.info("🚀 启动 Libp2p P2P 网络...")

            # 生成节点 ID（模拟 libp2p PeerId）
            self._node_id = self._generate_id()
            self._is_running = True

            logger.info("✅ Libp2p P2P 网络已启动")
            logger.info(f"   节点 ID: {self._node_id[:16]}...")
        except Exception as error:
            logger.error(f"❌ 启动 Libp2p 节点失败: {error}")
            raise error

    async def stop(self) -> None:
        """停止 Libp2p P2P 网络"""
        if not self._is_running:
            return

        try:
            logger.info("🛑 停止 Libp2p P2P 网络...")

            self._connections.clear()
            self._topics.clear()
            self._is_running = False
            self._node_id = None

            logger.info("✅ Libp2p P2P 网络已停止")
        except Exception as error:
            logger.error(f"❌ 停止 Libp2p 节点失败: {error}")
            raise error

    async def subscribe(self, topic: str, handler: Callable) -> None:
        """订阅主题"""
        if not self._is_running:
            raise RuntimeError("Libp2p 节点未启动")

        self._message_handlers[topic] = handler
        self._topics.add(topic)
        logger.info(f"🔔 已订阅主题: {topic}")

    async def unsubscribe(self, topic: str) -> None:
        """取消订阅主题"""
        if not self._is_running:
            return

        self._message_handlers.pop(topic, None)
        self._topics.discard(topic)
        logger.info(f"🔕 已取消订阅主题: {topic}")

    async def publish(self, topic: str, data: bytes | str) -> None:
        """发布消息到主题"""
        if not self._is_running:
            raise RuntimeError("Libp2p 节点未启动")

        data_buffer = data if isinstance(data, bytes) else data.encode()
        message = Libp2pMessage(
            id=self._generate_id(),
            from_peer=self._node_id or "",
            topic=topic,
            data=data_buffer,
            timestamp=int(time.time() * 1000),
        )

        # 模拟发布：触发本地订阅者
        handler = self._message_handlers.get(topic)
        if handler:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(message)
                else:
                    handler(message)
            except Exception as e:
                logger.error(f"❌ 消息处理器错误: {e}")

        self._emit("message", message)
        logger.debug(f"📢 已发布消息到主题: {topic}")

    async def connect_to_peer(self, peer_addr: str) -> Libp2pConnection:
        """连接到对等节点"""
        if not self._is_running:
            raise RuntimeError("Libp2p 节点未启动")

        try:
            peer_id = self._generate_id()
            conn = Libp2pConnection(
                peer_id=peer_id,
                multiaddrs=[peer_addr],
                connected_at=int(time.time() * 1000),
                protocols=["/diap/1.0.0"],
            )

            self._connections[peer_id] = conn
            self._emit("peer:connect", conn)
            logger.info(f"🔗 已连接到节点: {peer_id[:8]}...")
            return conn
        except Exception as error:
            logger.error(f"❌ 连接节点失败: {error}")
            raise error

    def get_connections(self) -> List[Libp2pConnection]:
        """获取所有连接"""
        return list(self._connections.values())

    def get_peer_id(self) -> Optional[str]:
        """获取本地节点 ID"""
        return self._node_id

    def is_active(self) -> bool:
        """是否正在运行"""
        return self._is_running

    def on(self, event: str, handler: Callable) -> None:
        """注册事件处理器"""
        if event not in self._event_handlers:
            self._event_handlers[event] = set()
        self._event_handlers[event].add(handler)

    def off(self, event: str, handler: Callable) -> None:
        """移除事件处理器"""
        handlers = self._event_handlers.get(event)
        if handlers:
            handlers.discard(handler)

    def _emit(self, event: str, *args) -> None:
        """触发事件"""
        handlers = self._event_handlers.get(event)
        if handlers:
            for handler in handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        asyncio.create_task(handler(*args))
                    else:
                        handler(*args)
                except Exception as e:
                    logger.error(f"❌ 事件处理器错误: {e}")

    def _generate_id(self) -> str:
        """生成唯一 ID"""
        return os.urandom(16).hex()


def create_libp2p_communicator(
    config: Optional[Libp2pConfig] = None,
) -> Libp2pCommunicator:
    """创建 Libp2p P2P 通信器"""
    return Libp2pCommunicator(config)