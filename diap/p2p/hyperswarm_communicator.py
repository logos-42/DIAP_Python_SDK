from enum import Enum
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
import hashlib
import os

from ..utils.logger import get_logger

logger = get_logger(__name__)


class P2PMessageType(Enum):
    AUTH_REQUEST = "auth_request"
    AUTH_RESPONSE = "auth_response"
    DATA = "data"
    HEARTBEAT = "heartbeat"
    CUSTOM = "custom"


@dataclass
class P2PConnection:
    id: str
    public_key: str
    is_inbound: bool
    connected_at: int
    last_activity: int
    bytes_sent: int = 0
    bytes_received: int = 0


@dataclass
class P2PNodeAddr:
    public_key: str
    topics: List[str]
    relay_addresses: Optional[List[str]] = None


@dataclass
class P2PMessage:
    id: str
    type: P2PMessageType
    from_public_key: str
    to_public_key: Optional[str] = None
    content: bytes = b""
    timestamp: int = 0
    signature: Optional[bytes] = None


class HyperswarmCommunicator:
    def __init__(
        self,
        server: bool = True,
        client: bool = True,
        auto_connect: bool = True,
        max_connections: int = 100,
        seed: Optional[List[bytes]] = None,
        multiplex: bool = True,
    ):
        self.config = {
            "server": server,
            "client": client,
            "autoConnect": auto_connect,
            "maxConnections": max_connections,
            "seed": seed or [],
            "multiplex": multiplex,
        }
        self._swarm = None
        self._connections: Dict[str, P2PConnection] = {}
        self._topics: set = set()
        self._is_running = False
        self._event_handlers: Dict[str, set] = {}
        self._local_public_key: Optional[str] = None

        logger.info("Hyperswarm P2P communicator created")
        logger.info(f"  Server mode: {server}")
        logger.info(f"  Client mode: {client}")
        logger.info(f"  Max connections: {max_connections}")

    async def start(self) -> None:
        if self._is_running:
            logger.warning("P2P network already running")
            return

        try:
            logger.info("Starting Hyperswarm P2P network...")

            self._is_running = True

            logger.info("Hyperswarm P2P network started")
        except Exception as error:
            logger.error(f"Failed to start P2P network: {error}")
            raise error

    async def stop(self) -> None:
        if not self._is_running:
            return

        try:
            logger.info("Stopping Hyperswarm P2P network...")

            for connection_id in list(self._connections.keys()):
                await self.close_connection(connection_id)

            self._connections.clear()
            self._topics.clear()
            self._is_running = False

            logger.info("Hyperswarm P2P network stopped")
        except Exception as error:
            logger.error(f"Failed to stop P2P network: {error}")
            raise error

    async def join_topic(self, topic: bytes | str) -> None:
        if not self._is_running:
            raise RuntimeError("P2P network not started")

        topic_hex = topic.hex() if isinstance(topic, bytes) else topic

        if topic_hex in self._topics:
            logger.warning(f"Already joined topic: {topic_hex[:8]}...")
            return

        try:
            logger.info(f"Joining topic: {topic_hex[:8]}...")

            topic_buffer = self._create_topic_buffer(topic)
            self._topics.add(topic_hex)

            self._emit("topic", topic_buffer)

            logger.info(f"Joined topic: {topic_hex[:8]}...")
        except Exception as error:
            logger.error(f"Failed to join topic: {error}")
            raise error

    async def leave_topic(self, topic: bytes | str) -> None:
        if not self._is_running:
            return

        topic_hex = topic.hex() if isinstance(topic, bytes) else topic

        if topic_hex not in self._topics:
            return

        try:
            topic_buffer = self._create_topic_buffer(topic)

            self._topics.remove(topic_hex)

            logger.info(f"Left topic: {topic_hex[:8]}...")
        except Exception as error:
            logger.error(f"Failed to leave topic: {error}")

    async def connect(self, public_key: bytes | str) -> P2PConnection:
        if not self._is_running:
            raise RuntimeError("P2P network not started")

        key_hex = public_key.hex() if isinstance(public_key, bytes) else public_key

        existing = self._connections.get(key_hex)
        if existing:
            return existing

        try:
            logger.info(f"Connecting to node: {key_hex[:8]}...")

            connection = P2PConnection(
                id=self._generate_id(),
                public_key=key_hex,
                is_inbound=False,
                connected_at=int(datetime.utcnow().timestamp() * 1000),
                last_activity=int(datetime.utcnow().timestamp() * 1000),
                bytes_sent=0,
                bytes_received=0,
            )

            self._connections[key_hex] = connection

            logger.info(f"Connected to node: {key_hex[:8]}...")

            return connection
        except Exception as error:
            logger.error(f"Failed to connect: {error}")
            raise error

    async def close_connection(self, connection_id: str) -> None:
        conn = self._connections.get(connection_id)
        if not conn:
            return

        try:
            self._connections.pop(connection_id, None)
            logger.info(f"Closed connection: {connection_id[:8]}...")
        except Exception as error:
            logger.error(f"Failed to close connection: {error}")

    async def send_to_connection(self, connection_id: str, data: bytes | str) -> None:
        conn = self._connections.get(connection_id)
        if not conn:
            raise RuntimeError("Connection not found")

        data_buffer = data if isinstance(data, bytes) else data.encode()

        try:
            conn.bytes_sent += len(data_buffer)
            conn.last_activity = int(datetime.utcnow().timestamp() * 1000)

            logger.debug(f"Sending data to {connection_id[:8]}...: {len(data_buffer)} bytes")
        except Exception as error:
            logger.error(f"Failed to send data: {error}")
            raise error

    async def broadcast(self, data: bytes | str) -> None:
        promises = []

        for connection_id in self._connections:
            promises.append(self.send_to_connection(connection_id, data))

        await asyncio.gather(*promises, return_exceptions=True)
        logger.info(f"Broadcast to {len(self._connections)} connections")

    def get_connections(self) -> List[P2PConnection]:
        return list(self._connections.values())

    def get_connection_count(self) -> int:
        return len(self._connections)

    def get_local_public_key(self) -> Optional[str]:
        return self._local_public_key

    def is_active(self) -> bool:
        return self._is_running

    def get_config(self) -> Dict[str, Any]:
        return {**self.config}

    def on(self, event: str, handler: Callable) -> None:
        if event not in self._event_handlers:
            self._event_handlers[event] = set()
        self._event_handlers[event].add(handler)

    def off(self, event: str, handler: Callable) -> None:
        handlers = self._event_handlers.get(event)
        if handlers:
            handlers.discard(handler)

    def _emit(self, event: str, *args) -> None:
        handlers = self._event_handlers.get(event)
        if handlers:
            for handler in handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        asyncio.create_task(handler(*args))
                    else:
                        handler(*args)
                except Exception as error:
                    logger.error(f"Event handler error: {error}")

    def _create_topic_buffer(self, topic: bytes | str) -> bytes:
        if isinstance(topic, str):
            if all(c in "0123456789abcdefABCDEF" for c in topic):
                return bytes.fromhex(topic.ljust(64, "0")[:64])
            return topic.encode()[:32].ljust(32, b"\x00")
        return topic[:32].ljust(32, b"\x00")

    def _generate_id(self) -> str:
        return os.urandom(16).hex()

    async def sign_message(self, content: bytes, private_key: bytes) -> bytes:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        key = private_key[:32]
        private_key_obj = Ed25519PrivateKey.from_private_bytes(key)
        return private_key_obj.sign(content)

    async def verify_message_signature(
        self,
        content: bytes,
        signature: bytes,
        public_key: bytes,
    ) -> bool:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

        try:
            public_key_obj = Ed25519PublicKey.from_public_bytes(public_key[:32])
            public_key_obj.verify(signature, content)
            return True
        except Exception:
            return False

    async def create_signed_message(
        self,
        msg_type: P2PMessageType,
        content: bytes,
        from_public_key: str,
        to_public_key: Optional[str],
        private_key: bytes,
    ) -> P2PMessage:
        message = P2PMessage(
            id=self._generate_id(),
            type=msg_type,
            from_public_key=from_public_key,
            to_public_key=to_public_key,
            content=content,
            timestamp=int(datetime.utcnow().timestamp() * 1000),
            signature=None,
        )

        signature = await self.sign_message(content, private_key)
        message.signature = signature

        return message

    async def verify_signed_message(
        self,
        message: P2PMessage,
        sender_public_key: bytes,
    ) -> bool:
        if not message.signature:
            logger.warning("Message missing signature")
            return False

        return await self.verify_message_signature(
            message.content,
            message.signature,
            sender_public_key,
        )


def create_hyperswarm_communicator(
    config: Optional[Dict[str, Any]] = None,
) -> HyperswarmCommunicator:
    return HyperswarmCommunicator(**(config or {}))


def create_topic(topic: str) -> bytes:
    if all(c in "0123456789abcdefABCDEF" for c in topic):
        return bytes.fromhex(topic.ljust(64, "0")[:64])

    buf = bytearray(32)
    data = topic.encode()
    buf[: len(data)] = data[:32]
    return bytes(buf)
