import os
import json
from pathlib import Path
from typing import Optional, Any, Dict
from dataclasses import dataclass, field, asdict
from datetime import datetime

from .types.errors import ConfigError
from .utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SDKConfig:
    ipfs_host: str = "localhost"
    ipfs_port: int = 5001
    ipfs_protocol: str = "http"
    ipns_publish_interval: int = 3600
    did_cache_ttl: int = 3600
    max_cache_size: int = 1000
    log_level: str = "INFO"
    keystore_path: Optional[str] = None
    network_timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    enable_pubsub: bool = True
    p2p_listen_addresses: list = field(default_factory=list)
    agent_verification_timeout: int = 60


@dataclass
class IPFSConfig:
    host: str = "localhost"
    port: int = 5001
    protocol: str = "http"
    gateway: str = "localhost"
    gateway_port: int = 8080
    gateway_protocol: str = "http"


@dataclass
class P2PConfig:
    enabled: bool = True
    listen_addresses: list = field(default_factory=list)
    bootstrap_nodes: list = field(default_factory=list)
    relay_enabled: bool = True
    nat_enabled: bool = True


@dataclass
class ZKPConfig:
    backend: str = "snarkjs"
    proving_key_path: Optional[str] = None
    verification_key_path: Optional[str] = None
    wasm_path: Optional[str] = None
    circuit_id: str = "did_binding"


class ConfigManager:
    DEFAULT_CONFIG_PATH = os.path.join("~", ".diap", "config.json")

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = os.path.expanduser(config_path or self.DEFAULT_CONFIG_PATH)
        self._config: Optional[SDKConfig] = None
        self._ipfs_config: Optional[IPFSConfig] = None
        self._p2p_config: Optional[P2PConfig] = None
        self._zkp_config: Optional[ZKPConfig] = None

    def load(self) -> SDKConfig:
        if self._config is not None:
            return self._config

        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    data = json.load(f)
                self._config = SDKConfig(**data.get("sdk", {}))
                self._ipfs_config = IPFSConfig(**data.get("ipfs", {}))
                self._p2p_config = P2PConfig(**data.get("p2p", {}))
                self._zkp_config = ZKPConfig(**data.get("zkp", {}))
                logger.info(f"Loaded configuration from {self.config_path}")
            except Exception as e:
                logger.warning(f"Failed to load config: {e}, using defaults")
                self._set_defaults()
        else:
            self._set_defaults()

        return self._config

    def _set_defaults(self):
        self._config = SDKConfig()
        self._ipfs_config = IPFSConfig()
        self._p2p_config = P2PConfig()
        self._zkp_config = ZKPConfig()

    def save(self, config: Optional[SDKConfig] = None):
        if config:
            self._config = config

        config_data = {
            "sdk": asdict(self._config) if self._config else asdict(SDKConfig()),
            "ipfs": asdict(self._ipfs_config)
            if self._ipfs_config
            else asdict(IPFSConfig()),
            "p2p": asdict(self._p2p_config)
            if self._p2p_config
            else asdict(P2PConfig()),
            "zkp": asdict(self._zkp_config)
            if self._zkp_config
            else asdict(ZKPConfig()),
        }

        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, "w") as f:
            json.dump(config_data, f, indent=2)

        logger.info(f"Saved configuration to {self.config_path}")

    def get_sdk_config(self) -> SDKConfig:
        if self._config is None:
            self.load()
        return self._config

    def get_ipfs_config(self) -> IPFSConfig:
        if self._ipfs_config is None:
            self.load()
        return self._ipfs_config

    def get_p2p_config(self) -> P2PConfig:
        if self._p2p_config is None:
            self.load()
        return self._p2p_config

    def get_zkp_config(self) -> ZKPConfig:
        if self._zkp_config is None:
            self.load()
        return self._zkp_config

    def update(self, updates: Dict[str, Any]):
        if self._config is None:
            self.load()

        for key, value in updates.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)

    def update_ipfs(self, updates: Dict[str, Any]):
        if self._ipfs_config is None:
            self.load()

        for key, value in updates.items():
            if hasattr(self._ipfs_config, key):
                setattr(self._ipfs_config, key, value)

    def reset(self):
        self._set_defaults()
        if os.path.exists(self.config_path):
            os.remove(self.config_path)
        logger.info("Reset configuration to defaults")


def asdict(obj):
    if hasattr(obj, "__dataclass_fields__"):
        result = {}
        for key, field in obj.__dataclass_fields__.items():
            value = getattr(obj, key)
            if hasattr(value, "__dataclass_fields__"):
                result[key] = asdict(value)
            elif (
                isinstance(value, list)
                and value
                and hasattr(value[0], "__dataclass_fields__")
            ):
                result[key] = [asdict(v) for v in value]
            else:
                result[key] = value
        return result
    return obj
