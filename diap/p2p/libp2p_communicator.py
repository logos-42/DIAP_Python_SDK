"""
DIAP Python SDK - Libp2p P2P 通信器（真实 libp2p 组件 + asyncio 传输）

身份 / 签名 / 消息编码使用真实 libp2p 0.7 组件：
- 身份：libp2p Ed25519 KeyPair → PeerID（12D3KooW...）
- 签名：libp2p private_key.sign() / public_key.verify()
- 消息帧：JSON + 长度前缀（与 HyperswarmCommunicator 相同的传输格式）

说明：libp2p 0.7 的 BasicHost.run() 依赖 trio event loop（RunContext.runner
缺失 bug），在 asyncio 环境不可用，因此传输层使用 asyncio TCP 实现，
保持与 TypeScript 版本相同的 API 设计。
"""

import asyncio
import json
import os
import struct
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Set

from libp2p.crypto.ed25519 import create_new_key_pair, Ed25519PrivateKey, Ed25519PublicKey
from libp2p.peer.id import ID

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
    """Libp2p P2P 通信器（真实 libp2p 身份/签名 + asyncio TCP 传输）"""

    PROTOCOL_ID = "/diap/libp2p/1.0.0"

    def __init__(self, config: Optional[Libp2pConfig] = None):
        self.config = config or Libp2pConfig()
        self._key_pair = None
        self._node_id: Optional[str] = None
        self._connections: Dict[str, Libp2pConnection] = {}
        self._streams: Dict[str, asyncio.StreamWriter] = {}
        self._event_handlers: Dict[str, Set[Callable]] = {}
        self._message_handlers: Dict[str, Callable] = {}
        self._is_running = False
        self._topics: Set[str] = set()
        self._server: Optional[asyncio.Server] = None
        self._heartbeat_task: Optional[asyncio.Task] = None

        logger.info("🔧 Libp2p P2P 通信器已创建")
        logger.info(f"  监听地址: {', '.join(self.config.listen_addresses)}")
        logger.info(f"  最大连接数: {self.config.max_connections}")

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """启动 Libp2p P2P 网络"""
        if self._is_running:
            logger.warning("⚠️ Libp2p 节点已在运行")
            return

        try:
            logger.info("🚀 启动 Libp2p P2P 网络...")

            # 真实 libp2p Ed25519 身份
            self._key_pair = create_new_key_pair()
            self._node_id = str(ID.from_pubkey(self._key_pair.public_key))

            # 启动 TCP 服务器
            self._server = await asyncio.start_server(
                self._handle_client,
                host="0.0.0.0",
                port=0,
            )
            self._is_running = True

            # 心跳
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

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

            if self._heartbeat_task:
                self._heartbeat_task.cancel()
                try:
                    await self._heartbeat_task
                except asyncio.CancelledError:
                    pass
                self._heartbeat_task = None

            for connection_id in list(self._connections.keys()):
                await self.close_connection(connection_id)

            if self._server:
                self._server.close()
                await self._server.wait_closed()
                self._server = None

            self._connections.clear()
            self._streams.clear()
            self._topics.clear()
            self._is_running = False
            self._node_id = None
            self._key_pair = None

            logger.info("✅ Libp2p P2P 网络已停止")
        except Exception as error:
            logger.error(f"❌ 停止 Libp2p 节点失败: {error}")
            raise error

    # ------------------------------------------------------------------
    # 主题订阅 / 发布
    # ------------------------------------------------------------------

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
        """发布消息到主题（广播到所有连接 + 本地订阅者）"""
        if not self._is_running:
            raise RuntimeError("Libp2p 节点未启动")

        data_buffer = data if isinstance(data, bytes) else data.encode()
        message = self._create_signed_message(topic, data_buffer)

        # 本地订阅者
        handler = self._message_handlers.get(topic)
        if handler:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(message)
                else:
                    handler(message)
            except Exception as e:
                logger.error(f"❌ 消息处理器错误: {e}")

        # 广播到所有已连接节点
        frame = self._encode_frame(message)
        for connection_id in list(self._streams.keys()):
            writer = self._streams.get(connection_id)
            if writer and not writer.is_closing():
                try:
                    writer.write(struct.pack(">I", len(frame)) + frame)
                    await writer.drain()
                except Exception as e:
                    logger.debug(f"发送到 {connection_id[:8]}... 失败: {e}")

        self._emit("message", message)
        logger.debug(f"📢 已发布消息到主题: {topic}")

    # ------------------------------------------------------------------
    # 连接管理
    # ------------------------------------------------------------------

    async def connect_to_peer(self, peer_addr: str) -> Libp2pConnection:
        """连接到对等节点（peer_addr: /ip4/host/tcp/port/p2p/PeerID 或 host:port）"""
        if not self._is_running:
            raise RuntimeError("Libp2p 节点未启动")

        try:
            host, port = self._parse_peer_addr(peer_addr)
            reader, writer = await asyncio.open_connection(host, port)

            peer_id = self._generate_id()
            conn = Libp2pConnection(
                peer_id=peer_id,
                multiaddrs=[peer_addr],
                connected_at=int(time.time() * 1000),
                protocols=[self.PROTOCOL_ID],
            )

            self._connections[peer_id] = conn
            self._streams[peer_id] = writer
            self._emit("peer:connect", conn)
            logger.info(f"🔗 已连接到节点: {peer_id[:8]}...")
            return conn
        except Exception as error:
            logger.error(f"❌ 连接节点失败: {error}")
            raise error

    async def close_connection(self, connection_id: str) -> None:
        """关闭连接"""
        conn = self._connections.get(connection_id)
        if not conn:
            return

        writer = self._streams.get(connection_id)
        if writer:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
            self._streams.pop(connection_id, None)

        self._connections.pop(connection_id, None)
        logger.info(f"🔌 已关闭连接: {connection_id[:8]}...")

    def get_connections(self) -> List[Libp2pConnection]:
        """获取所有连接"""
        return list(self._connections.values())

    def get_peer_id(self) -> Optional[str]:
        """获取本地节点 ID（libp2p PeerID）"""
        return self._node_id

    def is_active(self) -> bool:
        """是否正在运行"""
        return self._is_running

    # ------------------------------------------------------------------
    # 事件系统
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # 签名（真实 libp2p Ed25519）
    # ------------------------------------------------------------------

    def sign_message(self, data: bytes) -> bytes:
        """使用 libp2p 私钥签名"""
        if not self._key_pair:
            raise RuntimeError("Libp2p 节点未启动")
        return self._key_pair.private_key.sign(data)

    def verify_signature(self, data: bytes, signature: bytes, peer_id: str) -> bool:
        """验证签名（按 peer_id 查找公钥；本地消息用本地公钥）"""
        try:
            if peer_id == self._node_id and self._key_pair:
                return self._key_pair.public_key.verify(data, signature)
            # 远端公钥需通过 peer store 获取，当前简化：仅本地验证
            return False
        except Exception:
            return False

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _create_signed_message(self, topic: str, data: bytes) -> Libp2pMessage:
        signature = self.sign_message(data)
        return Libp2pMessage(
            id=self._generate_id(),
            from_peer=self._node_id or "",
            topic=topic,
            data=data,
            timestamp=int(time.time() * 1000),
            signature=signature,
        )

    def _encode_frame(self, message: Libp2pMessage) -> bytes:
        frame = {
            "id": message.id,
            "from": message.from_peer,
            "to": message.to_peer,
            "topic": message.topic,
            "data": message.data.decode("utf-8", errors="replace"),
            "ts": message.timestamp,
            "sig": message.signature.hex() if message.signature else "",
        }
        return json.dumps(frame).encode()

    def _parse_peer_addr(self, peer_addr: str):
        """解析 peer_addr: multiaddr 或 host:port"""
        if peer_addr.startswith("/ip4/") or peer_addr.startswith("/ip6/"):
            # multiaddr 格式: /ip4/host/tcp/port/p2p/PeerID
            parts = peer_addr.split("/")
            host = parts[2]
            port = 0
            for i, p in enumerate(parts):
                if p == "tcp":
                    port = int(parts[i + 1])
                    break
            return host, port
        host, port_str = peer_addr.rsplit(":", 1)
        return host, int(port_str)

    def _generate_id(self) -> str:
        """生成唯一 ID"""
        return os.urandom(16).hex()

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

    async def _heartbeat_loop(self):
        """心跳循环"""
        while self._is_running:
            try:
                await asyncio.sleep(30)
                for connection_id in list(self._streams.keys()):
                    writer = self._streams.get(connection_id)
                    if writer and not writer.is_closing():
                        try:
                            frame = self._encode_frame(
                                Libp2pMessage(
                                    id=self._generate_id(),
                                    from_peer=self._node_id or "",
                                    topic="__heartbeat__",
                                    data=b"ping",
                                    timestamp=int(time.time() * 1000),
                                )
                            )
                            writer.write(struct.pack(">I", len(frame)) + frame)
                            await writer.drain()
                        except Exception:
                            pass
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"心跳失败: {e}")

    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ):
        """处理入站连接"""
        peer_id = self._generate_id()
        try:
            conn = Libp2pConnection(
                peer_id=peer_id,
                multiaddrs=[],
                connected_at=int(time.time() * 1000),
                protocols=[self.PROTOCOL_ID],
            )
            self._connections[peer_id] = conn
            self._streams[peer_id] = writer
            self._emit("peer:connect", conn)
            logger.info(f"🔗 入站连接: {peer_id[:8]}...")

            while True:
                length_bytes = await reader.readexactly(4)
                length = struct.unpack(">I", length_bytes)[0]
                frame_bytes = await reader.readexactly(length)
                frame = json.loads(frame_bytes.decode())
                await self._handle_frame(frame)
        except (asyncio.IncompleteReadError, ConnectionResetError):
            pass
        except Exception as e:
            logger.debug(f"连接处理错误: {e}")
        finally:
            if peer_id in self._connections:
                await self.close_connection(peer_id)

    async def _handle_frame(self, frame: dict):
        """处理收到的消息帧"""
        try:
            message = Libp2pMessage(
                id=frame.get("id", self._generate_id()),
                from_peer=frame.get("from", ""),
                to_peer=frame.get("to"),
                topic=frame.get("topic", ""),
                data=frame.get("data", "").encode(),
                timestamp=frame.get("ts", 0),
                signature=bytes.fromhex(frame["sig"]) if frame.get("sig") else None,
            )
            self._emit("message", message)
            handler = self._message_handlers.get(message.topic)
            if handler:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(message)
                    else:
                        handler(message)
                except Exception as e:
                    logger.error(f"❌ 消息处理器错误: {e}")
        except Exception as e:
            logger.debug(f"帧解析失败: {e}")


def create_libp2p_communicator(
    config: Optional[Libp2pConfig] = None,
) -> Libp2pCommunicator:
    """创建 Libp2p P2P 通信器"""
    return Libp2pCommunicator(config)
