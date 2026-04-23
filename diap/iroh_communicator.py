import asyncio
import json
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from datetime import datetime

from .types.errors import NetworkError
from .utils.logger import get_logger

logger = get_logger(__name__)


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


class IrohCommunicator:
    def __init__(
        self,
        node_id: Optional[str] = None,
        addr: Optional[str] = None,
        private_key: Optional[bytes] = None,
    ):
        self.node_id = node_id or self._generate_node_id()
        self.addr = addr
        self.private_key = private_key
        self._connected_nodes: Dict[str, IrohNodeInfo] = {}
        self._message_handlers: Dict[str, List[Callable]] = {}
        self._running = False
        self._listener_task: Optional[asyncio.Task] = None

    def _generate_node_id(self) -> str:
        from .utils.crypto import generate_random_bytes

        return generate_random_bytes(16).hex()

    async def start(self):
        if self._running:
            return

        self._running = True
        self._listener_task = asyncio.create_task(self._listen_loop())
        logger.info(f"Iroh communicator started: {self.node_id}")

    async def stop(self):
        self._running = False
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass

        self._connected_nodes.clear()
        logger.info("Iroh communicator stopped")

    async def connect(
        self,
        peer_addr: str,
        peer_public_key: Optional[bytes] = None,
    ) -> bool:
        node_info = IrohNodeInfo(
            node_id=self._generate_node_id(),
            addr=peer_addr,
            public_key=peer_public_key or b"",
            is_connected=True,
            last_seen=datetime.utcnow().isoformat() + "Z",
        )

        self._connected_nodes[peer_addr] = node_info
        logger.info(f"Connected to Iroh node: {peer_addr}")
        return True

    async def disconnect(self, peer_addr: str) -> bool:
        if peer_addr in self._connected_nodes:
            del self._connected_nodes[peer_addr]
            logger.info(f"Disconnected from Iroh node: {peer_addr}")
            return True
        return False

    async def send_message(
        self,
        to_node: str,
        payload: bytes,
        message_type: str = "default",
        timeout: float = 30.0,
    ) -> bool:
        if to_node not in self._connected_nodes:
            logger.warning(f"Node not connected: {to_node}")
            return False

        message = IrohMessage(
            from_node=self.node_id,
            to_node=to_node,
            payload=payload,
            timestamp=datetime.utcnow().isoformat() + "Z",
            message_type=message_type,
        )

        delivered = await self._deliver_message(message, timeout)

        if delivered:
            logger.debug(f"Message sent to {to_node}")
        else:
            logger.warning(f"Failed to send message to {to_node}")

        return delivered

    async def broadcast(
        self,
        payload: bytes,
        message_type: str = "broadcast",
    ) -> int:
        delivered_count = 0

        for node_id in self._connected_nodes:
            if await self.send_message(node_id, payload, message_type):
                delivered_count += 1

        logger.info(
            f"Broadcast delivered to {delivered_count}/{len(self._connected_nodes)} nodes"
        )
        return delivered_count

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

    async def _listen_loop(self):
        while self._running:
            try:
                await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Listen loop error: {e}")

    async def _deliver_message(
        self,
        message: IrohMessage,
        timeout: float,
    ) -> bool:
        handlers = self._message_handlers.get(message.message_type, [])
        handlers.extend(self._message_handlers.get("*", []))

        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(message)
                else:
                    handler(message)
            except Exception as e:
                logger.error(f"Handler error: {e}")

        return True

    async def ping(self, node_id: str) -> bool:
        if node_id not in self._connected_nodes:
            return False

        try:
            result = await self.send_message(
                node_id,
                b"ping",
                message_type="ping",
                timeout=5.0,
            )
            return result
        except:
            return False

    async def get_node_stats(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "connected_nodes": len(self._connected_nodes),
            "running": self._running,
            "handlers_registered": sum(len(h) for h in self._message_handlers.values()),
        }
