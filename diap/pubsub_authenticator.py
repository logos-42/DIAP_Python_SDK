import asyncio
import json
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .types.errors import AgentAuthError
from .utils.crypto import sha256_hash, generate_random_bytes
from .utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PubSubMessage:
    topic: str
    sender_did: str
    content: bytes
    timestamp: str
    sequence: int
    signature: Optional[bytes] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PubSubTopic:
    name: str
    owner_did: str
    authorized_dids: List[str] = field(default_factory=list)
    is_public: bool = False
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class PubSubAuthenticator:
    def __init__(self, key_manager=None):
        self.key_manager = key_manager
        self._topics: Dict[str, PubSubTopic] = {}
        self._subscriptions: Dict[str, List[str]] = {}
        self._message_log: Dict[str, List[PubSubMessage]] = {}
        self._sequence_counters: Dict[str, int] = {}
        self._handlers: Dict[str, List[Callable]] = {}
        self._running = False

    async def create_topic(
        self,
        name: str,
        owner_did: str,
        authorized_dids: Optional[List[str]] = None,
        is_public: bool = False,
    ) -> PubSubTopic:
        topic = PubSubTopic(
            name=name,
            owner_did=owner_did,
            authorized_dids=authorized_dids or [],
            is_public=is_public,
        )

        self._topics[name] = topic
        self._subscriptions[name] = []
        self._message_log[name] = []

        logger.info(f"Created pubsub topic: {name} (owner: {owner_did})")
        return topic

    async def subscribe(
        self,
        topic: str,
        subscriber_did: str,
    ) -> bool:
        if topic not in self._topics:
            logger.warning(f"Topic not found: {topic}")
            return False

        topic_obj = self._topics[topic]

        if not topic_obj.is_public:
            if subscriber_did != topic_obj.owner_did:
                if subscriber_did not in topic_obj.authorized_dids:
                    logger.warning(f"Subscriber not authorized: {subscriber_did}")
                    return False

        if topic not in self._subscriptions:
            self._subscriptions[topic] = []

        if subscriber_did not in self._subscriptions[topic]:
            self._subscriptions[topic].append(subscriber_did)

        logger.debug(f"Subscribed {subscriber_did} to topic {topic}")
        return True

    async def unsubscribe(
        self,
        topic: str,
        subscriber_did: str,
    ) -> bool:
        if topic in self._subscriptions:
            if subscriber_did in self._subscriptions[topic]:
                self._subscriptions[topic].remove(subscriber_did)
                logger.debug(f"Unsubscribed {subscriber_did} from topic {topic}")
                return True

        return False

    async def publish(
        self,
        topic: str,
        sender_did: str,
        content: bytes,
        sign: bool = True,
    ) -> PubSubMessage:
        if topic not in self._topics:
            raise AgentAuthError(f"Topic not found: {topic}")

        topic_obj = self._topics[topic]

        if sender_did != topic_obj.owner_did:
            if sender_did not in topic_obj.authorized_dids:
                raise AgentAuthError(f"Publisher not authorized: {sender_did}")

        if topic not in self._sequence_counters:
            self._sequence_counters[topic] = 0

        self._sequence_counters[topic] += 1
        sequence = self._sequence_counters[topic]

        signature = None
        if sign and self.key_manager:
            key_pair = self.key_manager._key_cache.get(sender_did)
            if key_pair:
                message = self._build_signable_message(
                    topic, sender_did, content, sequence
                )
                signature = self.key_manager.sign(key_pair, message)

        message = PubSubMessage(
            topic=topic,
            sender_did=sender_did,
            content=content,
            timestamp=datetime.utcnow().isoformat() + "Z",
            sequence=sequence,
            signature=signature,
        )

        self._message_log.setdefault(topic, []).append(message)

        await self._deliver_message(message)

        logger.debug(f"Published message to {topic} from {sender_did}")
        return message

    async def verify_message(
        self,
        message: PubSubMessage,
        verify_signature: bool = True,
    ) -> bool:
        if verify_signature and message.signature:
            if not self.key_manager:
                logger.warning("No key manager to verify signature")
                return False

            key_pair = self.key_manager._key_cache.get(message.sender_did)
            if not key_pair:
                logger.warning(f"Key pair not found for {message.sender_did}")
                return False

            signable = self._build_signable_message(
                message.topic,
                message.sender_did,
                message.content,
                message.sequence,
            )

            is_valid = self.key_manager.verify(
                key_pair,
                signable,
                message.signature,
            )

            if not is_valid:
                logger.warning(
                    f"Invalid signature on message from {message.sender_did}"
                )
                return False

        return True

    def add_message_handler(
        self,
        topic: str,
        handler: Callable[[PubSubMessage], None],
    ):
        if topic not in self._handlers:
            self._handlers[topic] = []
        self._handlers[topic].append(handler)

    def remove_message_handler(
        self,
        topic: str,
        handler: Callable[[PubSubMessage], None],
    ):
        if topic in self._handlers:
            self._handlers[topic].remove(handler)

    async def get_topic_messages(
        self,
        topic: str,
        limit: int = 100,
    ) -> List[PubSubMessage]:
        messages = self._message_log.get(topic, [])
        return messages[-limit:]

    def get_topic_info(self, topic: str) -> Optional[Dict[str, Any]]:
        if topic not in self._topics:
            return None

        topic_obj = self._topics[topic]
        return {
            "name": topic_obj.name,
            "owner_did": topic_obj.owner_did,
            "authorized_dids": topic_obj.authorized_dids,
            "is_public": topic_obj.is_public,
            "subscriber_count": len(self._subscriptions.get(topic, [])),
            "message_count": len(self._message_log.get(topic, [])),
            "created_at": topic_obj.created_at,
        }

    def list_topics(self) -> List[str]:
        return list(self._topics.keys())

    def get_subscribers(self, topic: str) -> List[str]:
        return self._subscriptions.get(topic, [])

    async def _deliver_message(self, message: PubSubMessage):
        handlers = self._handlers.get(message.topic, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(message)
                else:
                    handler(message)
            except Exception as e:
                logger.error(f"Handler error: {e}")

    def _build_signable_message(
        self,
        topic: str,
        sender_did: str,
        content: bytes,
        sequence: int,
    ) -> bytes:
        parts = [
            topic,
            sender_did,
            content.decode() if isinstance(content, bytes) else content,
            str(sequence),
        ]
        return "|".join(parts).encode()
