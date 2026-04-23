import json
import hashlib
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

from .types.did_types import DIDDocument
from .types.key_types import KeyPair
from .types.zkp_types import ProofResult
from .types.errors import AgentAuthError
from .utils.crypto import sha256_hash, generate_random_bytes, hmac_sha256
from .utils.encoding import bytes_to_hex, base58_encode
from .utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Agent:
    did: str
    name: str
    public_key: bytes
    created_at: str
    last_authenticated: Optional[str] = None
    auth_count: int = 0


@dataclass
class AgentCredentials:
    agent_id: str
    challenge: str
    response: Optional[str] = None
    verified: bool = False
    expires_at: Optional[str] = None


class AgentAuthManager:
    def __init__(
        self,
        key_manager=None,
        identity_manager=None,
        nonce_manager=None,
    ):
        self.key_manager = key_manager
        self.identity_manager = identity_manager
        self.nonce_manager = nonce_manager
        self._agents: Dict[str, Agent] = {}
        self._credentials: Dict[str, AgentCredentials] = {}
        self._challenge_expiry = 300

    def create_agent(
        self,
        name: str,
        key_pair: KeyPair,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Agent:
        if key_pair.did in self._agents:
            raise AgentAuthError(f"Agent already exists: {key_pair.did}")

        agent = Agent(
            did=key_pair.did,
            name=name,
            public_key=key_pair.public_key,
            created_at=datetime.utcnow().isoformat() + "Z",
        )

        self._agents[key_pair.did] = agent

        logger.info(f"Created agent: {name} ({key_pair.did})")
        return agent

    def register_agent(
        self,
        agent: Agent,
        ipfs_client,
        ipns_manager=None,
    ) -> str:
        agent_data = asdict(agent)
        agent_json = json.dumps(agent_data)

        cid = ipfs_client.add(agent_json)

        if ipns_manager:
            try:
                ipns_name, ipns_value = ipns_manager.publish(cid)
                return ipns_name
            except Exception as e:
                logger.warning(f"Failed to publish agent to IPNS: {e}")

        return cid

    def generate_challenge(self, agent_id: str) -> str:
        if agent_id not in self._agents:
            raise AgentAuthError(f"Agent not found: {agent_id}")

        challenge = base58_encode(generate_random_bytes(32))

        expires_at = datetime.utcnow() + timedelta(seconds=self._challenge_expiry)

        credentials = AgentCredentials(
            agent_id=agent_id,
            challenge=challenge,
            expires_at=expires_at.isoformat() + "Z",
        )

        self._credentials[challenge] = credentials

        logger.debug(f"Generated challenge for agent: {agent_id}")
        return challenge

    def verify_challenge(
        self,
        challenge: str,
        response: str,
    ) -> bool:
        if challenge not in self._credentials:
            logger.warning(f"Unknown challenge: {challenge[:16]}...")
            return False

        credentials = self._credentials[challenge]

        if credentials.expires_at:
            expires = datetime.fromisoformat(
                credentials.expires_at.replace("Z", "+00:00")
            )
            if datetime.utcnow() > expires.replace(tzinfo=None):
                logger.warning("Challenge expired")
                return False

        agent = self._agents.get(credentials.agent_id)
        if not agent:
            return False

        expected_response = self._compute_response(agent, challenge)

        if response != expected_response:
            logger.warning("Invalid challenge response")
            return False

        credentials.response = response
        credentials.verified = True

        agent.last_authenticated = datetime.utcnow().isoformat() + "Z"
        agent.auth_count += 1

        logger.info(f"Agent authenticated: {agent.did}")
        return True

    def _compute_response(self, agent: Agent, challenge: str) -> str:
        message = f"{agent.did}:{challenge}".encode()
        signature = self.key_manager.sign(
            KeyPair(
                private_key=self.key_manager._key_cache.get(agent.did).private_key
                if self.key_manager
                else agent.public_key,
                public_key=agent.public_key,
                did=agent.did,
            ),
            message,
        )
        return base58_encode(signature)

    def generate_proof(
        self,
        agent_id: str,
        zkp_manager,
    ) -> ProofResult:
        if agent_id not in self._agents:
            raise AgentAuthError(f"Agent not found: {agent_id}")

        agent = self._agents[agent_id]

        if self.key_manager is None:
            raise AgentAuthError("Key manager not available")

        key_pair = self.key_manager._key_cache.get(agent_id)
        if not key_pair:
            raise AgentAuthError("Agent key pair not found")

        nonce = generate_random_bytes(32)
        nonce_hash = sha256_hash(nonce)

        public_key_hash = sha256_hash(key_pair.public_key)

        inputs = {
            "expected_did_hash": self._bytes_to_field_elements(key_pair.did.encode()),
            "public_key_hash": int.from_bytes(public_key_hash[:8], "little"),
            "nonce_hash": int.from_bytes(nonce_hash[:8], "little"),
            "secret_key": self._bytes_to_field_elements(key_pair.private_key),
            "did_document_hash": self._bytes_to_field_elements(key_pair.did.encode()),
            "nonce": self._bytes_to_field_elements(nonce),
        }

        proof = zkp_manager.generate_proof(inputs)

        logger.info(f"Generated auth proof for agent: {agent_id}")
        return proof

    def verify_identity(
        self,
        agent_id: str,
        proof: ProofResult,
        zkp_manager,
    ) -> bool:
        if agent_id not in self._agents:
            raise AgentAuthError(f"Agent not found: {agent_id}")

        is_valid = zkp_manager.verify_proof(proof)

        if is_valid:
            agent = self._agents[agent_id]
            agent.last_authenticated = datetime.utcnow().isoformat() + "Z"
            agent.auth_count += 1
            logger.info(f"Agent identity verified: {agent_id}")
        else:
            logger.warning(f"Agent identity verification failed: {agent_id}")

        return is_valid

    def revoke_agent(self, agent_id: str) -> bool:
        if agent_id in self._agents:
            del self._agents[agent_id]

        active_creds = [c for c in self._credentials.values() if c.agent_id == agent_id]
        for c in active_creds:
            del self._credentials[c.challenge]

        logger.info(f"Revoked agent: {agent_id}")
        return True

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        return self._agents.get(agent_id)

    def list_agents(self) -> List[str]:
        return list(self._agents.keys())

    def get_auth_stats(self, agent_id: str) -> Dict[str, Any]:
        agent = self._agents.get(agent_id)
        if not agent:
            return {}

        return {
            "did": agent.did,
            "name": agent.name,
            "created_at": agent.created_at,
            "last_authenticated": agent.last_authenticated,
            "auth_count": agent.auth_count,
        }

    def _bytes_to_field_elements(self, data: bytes) -> List[int]:
        result = []
        for i in range(0, len(data), 8):
            chunk = data[i : i + 8]
            if len(chunk) < 8:
                chunk = chunk + b"\x00" * (8 - len(chunk))
            result.append(int.from_bytes(chunk, "little"))
        return result[:4]
