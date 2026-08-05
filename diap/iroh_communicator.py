"""
DIAP Python SDK - Iroh P2P 通信器（真实 iroh 实现）

基于官方 iroh Python 绑定（iroh==0.31.0），使用 gossip 协议实现
与 TypeScript 版本相同的 API 设计。

- 节点身份：iroh 原生 node_id（Ed25519 派生）
- 消息路由：gossip topic 订阅/广播（32 字节 topic）
- 节点发现：add_node_addr + bootstrap（base32 node id）
"""

import asyncio
import base64
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable

import iroh
from iroh.iroh_ffi import uniffi_set_event_loop

from .types.errors import NetworkError
from .utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_TOPIC = b"diap-agent-network-v1" + b"\x00" * 10  # 32 字节


@dataclass
class IrohMessage:
    from_node: str
    to_node: str
    payload: bytes
    timestamp: str
    message_type: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IrohNodeInfo:
    node_id: str
    addr: str
    public_key: bytes
    is_connected: bool = False
    last_seen: Optional[str] = None


def _hex_to_base32(node_id_hex: str) -> str:
    """将 64 位 hex node_id 转为 iroh 使用的 base32 表示（无 padding）"""
    return base64.b32encode(bytes.fromhex(node_id_hex)).decode().rstrip("=")


def _make_topic(topic: str | bytes) -> bytes:
    """将任意主题字符串哈希为 32 字节 gossip topic"""
    import hashlib

    if isinstance(topic, bytes) and len(topic) == 32:
        return topic
    data = topic if isinstance(topic, bytes) else topic.encode()
    return hashlib.sha256(data).digest()


class IrohCommunicator:
    def __init__(
        self,
        node_id: Optional[str] = None,
        addr: Optional[str] = None,
        private_key: Optional[bytes] = None,
        topic: str | bytes = DEFAULT_TOPIC,
    ):
        self.node_id = node_id or ""
        self.addr = addr
        self.private_key = private_key
        self._topic = _make_topic(topic)
        self._iroh_node: Optional[iroh.Iroh] = None
        self._sender: Optional[iroh.Sender] = None
        self._connected_nodes: Dict[str, IrohNodeInfo] = {}
        self._message_handlers: Dict[str, List[Callable]] = {}
        self._running = False
        self._listener_task: Optional[asyncio.Task] = None

    async def start(self):
        if self._running:
            return

        # iroh 0.31 uniffi callback 需要全局 event loop（Rust 线程调用 Python 回调）
        uniffi_set_event_loop(asyncio.get_running_loop())

        self._iroh_node = await iroh.Iroh.memory()
        net = self._iroh_node.net()
        self.node_id = await net.node_id()
        self._running = True

        await self._resubscribe()
        self._listener_task = asyncio.create_task(self._listen_loop())
        logger.info(f"Iroh communicator started: {self.node_id[:16]}...")

    async def stop(self):
        if not self._running:
            return

        self._running = False
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        if self._sender:
            try:
                await self._sender.cancel()
            except Exception:
                pass
        # iroh 0.31 无 shutdown API（进程退出时自动回收）
        self._iroh_node = None
        self._sender = None
        self._connected_nodes.clear()
        logger.info("Iroh communicator stopped")

    async def connect(
        self,
        peer_addr: str,
        peer_public_key: Optional[bytes] = None,
    ) -> bool:
        """连接对端：注册 node addr（含 relay）并更新 gossip bootstrap"""
        if not self._running or not self._iroh_node:
            raise NetworkError("Iroh communicator not running")

        try:
            # peer_addr 可以是完整 hex node_id 或 node_id@relay_url
            parts = peer_addr.split("@")
            node_id_hex = parts[0]
            explicit_relay = parts[1] if len(parts) > 1 else None
            pub_key = iroh.PublicKey.from_string(node_id_hex)
            node_info = IrohNodeInfo(
                node_id=node_id_hex,
                addr=peer_addr,
                public_key=peer_public_key or bytes(pub_key.to_bytes()),
                is_connected=True,
                last_seen=datetime.utcnow().isoformat() + "Z",
            )
            self._connected_nodes[node_id_hex] = node_info

            # 解析对端地址：优先 remote_info，否则用显式 relay，最后用本机 home relay
            net = self._iroh_node.net()
            relay_url = explicit_relay
            direct: List[str] = []
            remote = None
            try:
                remote = await net.remote_info(pub_key)
            except Exception:
                remote = None
            if remote is not None:
                try:
                    relay_url = relay_url or remote.relay_url
                except Exception:
                    pass
                try:
                    direct = [str(a) for a in remote.addrs]
                except Exception:
                    direct = []
            if relay_url is None:
                try:
                    relay_url = await net.home_relay()
                except Exception:
                    relay_url = None

            await net.add_node_addr(
                iroh.NodeAddr(
                    pub_key,
                    relay_url,
                    direct,
                )
            )

            # 重新订阅以更新 bootstrap（gossip 发现新节点）
            await self._resubscribe()
            logger.info(f"Connected to Iroh node: {node_id_hex[:16]}...")
            return True
        except Exception as e:
            logger.error(f"Connect failed: {e}")
            return False

    async def disconnect(self, peer_addr: str) -> bool:
        node_id_hex = peer_addr.split("@")[0]
        if node_id_hex in self._connected_nodes:
            del self._connected_nodes[node_id_hex]
            logger.info(f"Disconnected from Iroh node: {node_id_hex[:16]}...")
            return True
        return False

    async def send_message(
        self,
        to_node: str,
        payload: bytes,
        message_type: str = "default",
        timeout: float = 30.0,
    ) -> bool:
        if not self._sender:
            logger.warning("Iroh communicator not started")
            return False

        message = IrohMessage(
            from_node=self.node_id,
            to_node=to_node,
            payload=payload,
            timestamp=datetime.utcnow().isoformat() + "Z",
            message_type=message_type,
        )
        envelope = json.dumps(
            {
                "from": message.from_node,
                "to": message.to_node,
                "payload": payload.hex(),
                "ts": message.timestamp,
                "type": message_type,
            }
        ).encode()
        try:
            await self._sender.broadcast(envelope)
            logger.debug(f"Message sent to {to_node[:16]}...")
            return True
        except Exception as e:
            logger.warning(f"Failed to send message: {e}")
            return False

    async def broadcast(
        self,
        payload: bytes,
        message_type: str = "broadcast",
    ) -> int:
        if not self._sender:
            logger.warning("Iroh communicator not started")
            return 0

        message = IrohMessage(
            from_node=self.node_id,
            to_node="",
            payload=payload,
            timestamp=datetime.utcnow().isoformat() + "Z",
            message_type=message_type,
        )
        envelope = json.dumps(
            {
                "from": message.from_node,
                "to": "",
                "payload": payload.hex(),
                "ts": message.timestamp,
                "type": message_type,
            }
        ).encode()
        try:
            await self._sender.broadcast(envelope)
            return len(self._connected_nodes) or 1
        except Exception as e:
            logger.warning(f"Broadcast failed: {e}")
            return 0

    def add_message_handler(
        self,
        message_type: str,
        handler: Callable[[IrohMessage], None],
    ):
        if message_type not in self._message_handlers:
            self._message_handlers[message_type] = []
        self._message_handlers[message_type].append(handler)

    def remove_message_handler(
        self,
        message_type: str,
        handler: Callable[[IrohMessage], None],
    ):
        if message_type in self._message_handlers:
            self._message_handlers[message_type].remove(handler)

    async def get_connected_nodes(self) -> List[IrohNodeInfo]:
        return list(self._connected_nodes.values())

    def is_connected(self, node_id: str) -> bool:
        for node in self._connected_nodes.values():
            if node.node_id == node_id:
                return node.is_connected
        return False

    async def ping(self, node_id: str) -> bool:
        return await self.send_message(node_id, b"ping", message_type="ping", timeout=5.0)

    async def get_node_stats(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "connected_nodes": len(self._connected_nodes),
            "running": self._running,
            "handlers_registered": sum(len(h) for h in self._message_handlers.values()),
        }

    # =========================================================================
    # 内部方法
    # =========================================================================

    async def _resubscribe(self):
        """重新订阅 gossip topic，携带最新 bootstrap 节点列表"""
        if not self._iroh_node:
            return
        bootstrap = [_hex_to_base32(n) for n in self._connected_nodes]

        class _Callback:
            def __init__(self, comm: "IrohCommunicator"):
                self.comm = comm

            async def on_message(self, msg):
                try:
                    if msg.type() is not iroh.MessageType.RECEIVED:
                        return
                    received = msg.as_received()
                    self.comm._handle_gossip_message(received.content)
                except Exception as e:
                    logger.debug(f"Gossip callback error: {e}")

        try:
            new_sender = await self._iroh_node.gossip().subscribe(
                self._topic, bootstrap, _Callback(self)
            )
            if self._sender:
                try:
                    await self._sender.cancel()
                except Exception:
                    pass
            self._sender = new_sender
        except Exception as e:
            logger.warning(f"Resubscribe failed: {e}")

    def _handle_gossip_message(self, content: bytes):
        try:
            data = json.loads(content.decode())
        except Exception:
            logger.debug("Received non-JSON gossip message, ignoring")
            return

        to_node = data.get("to", "")
        if to_node and to_node != self.node_id:
            return  # 定向消息且非本节点

        message = IrohMessage(
            from_node=data.get("from", ""),
            to_node=to_node,
            payload=bytes.fromhex(data.get("payload", "")),
            timestamp=data.get("ts", ""),
            message_type=data.get("type", "default"),
        )

        handlers = self._message_handlers.get(message.message_type, [])
        handlers.extend(self._message_handlers.get("*", []))
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    asyncio.create_task(handler(message))
                else:
                    handler(message)
            except Exception as e:
                logger.error(f"Handler error: {e}")

    async def _listen_loop(self):
        while self._running:
            try:
                await asyncio.sleep(1.0)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Listen loop error: {e}")
