import os
import signal
import subprocess
import time
from typing import Optional, List, Dict, Any
from pathlib import Path

from .types.errors import IPFSError
from .utils.logger import get_logger

logger = get_logger(__name__)


class IPFSNodeManager:
    DEFAULT_NODE_PATH = os.path.join("~", ".diap", "ipfs")
    DEFAULT_API_PORT = 5001
    DEFAULT_GATEWAY_PORT = 8080
    DEFAULT_SWARM_PORT = 4001

    def __init__(
        self,
        node_path: Optional[str] = None,
        api_port: int = 5001,
        gateway_port: int = 8080,
        swarm_port: int = 4001,
    ):
        self.node_path = os.path.expanduser(node_path or self.DEFAULT_NODE_PATH)
        self.api_port = api_port
        self.gateway_port = gateway_port
        self.swarm_port = swarm_port
        self._process: Optional[subprocess.Popen] = None
        self._initialized = False

    def initialize(self, force: bool = False) -> bool:
        if self._initialized and not force:
            return True

        os.makedirs(self.node_path, exist_ok=True)

        repo_path = os.path.join(self.node_path, "repo")
        os.makedirs(repo_path, exist_ok=True)

        if not self._check_repo_initialized():
            logger.info("Initializing IPFS repository...")
            self._init_repo()

        self._initialized = True
        return True

    def _check_repo_initialized(self) -> bool:
        repo_lock = os.path.join(self.node_path, "repo", "repo.lock")
        return os.path.exists(repo_lock)

    def _init_repo(self):
        try:
            result = subprocess.run(
                ["ipfs", "init"],
                cwd=self.node_path,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if (
                result.returncode != 0
                and "already initialized" not in result.stderr.lower()
            ):
                logger.warning(f"IPFS init warning: {result.stderr}")

        except FileNotFoundError:
            raise IPFSError("IPFS not found. Please install Kubo/IPFS.")

    def start(
        self,
        bootstrap: bool = True,
        witness_cid: Optional[str] = None,
    ) -> bool:
        if self._process is not None:
            logger.warning("IPFS node already running")
            return True

        self.initialize()

        cmd = self._build_start_command(bootstrap, witness_cid)

        try:
            self._process = subprocess.Popen(
                cmd,
                cwd=self.node_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            if self._wait_for_api():
                logger.info("IPFS node started successfully")
                return True
            else:
                logger.error("IPFS node failed to start")
                self._process = None
                return False

        except Exception as e:
            raise IPFSError(f"Failed to start IPFS node: {e}")

    def _build_start_command(
        self, bootstrap: bool, witness_cid: Optional[str]
    ) -> List[str]:
        cmd = [
            "ipfs",
            "daemon",
            "--api",
            f"/ip4/127.0.0.1/tcp/{self.api_port}",
            "--gateway",
            f"/ip4/0.0.0.0/tcp/{self.gateway_port}",
            "--offline" if not bootstrap else "",
        ]

        if not bootstrap:
            cmd.append("--offline")

        if witness_cid:
            cmd.extend(["--witness", witness_cid])

        return [c for c in cmd if c]

    def _wait_for_api(self, timeout: int = 30) -> bool:
        import urllib.request
        import json

        endpoint = f"http://localhost:{self.api_port}/api/v0/id"

        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                req = urllib.request.Request(endpoint, method="POST")
                response = urllib.request.urlopen(req, timeout=2)
                if response.status == 200:
                    return True
            except:
                pass
            time.sleep(0.5)

        return False

    def stop(self) -> bool:
        if self._process is None:
            return True

        try:
            self._process.send_signal(signal.SIGINT)

            try:
                self._process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait()

            self._process = None
            logger.info("IPFS node stopped")
            return True

        except Exception as e:
            logger.error(f"Error stopping IPFS node: {e}")
            return False

    def restart(self, bootstrap: bool = True) -> bool:
        self.stop()
        time.sleep(1)
        return self.start(bootstrap=bootstrap)

    def is_running(self) -> bool:
        if self._process is None:
            return False

        return self._process.poll() is None

    def get_status(self) -> Dict[str, Any]:
        status = {
            "running": self.is_running(),
            "node_path": self.node_path,
            "api_port": self.api_port,
            "gateway_port": self.gateway_port,
            "swarm_port": self.swarm_port,
        }

        if status["running"]:
            try:
                import urllib.request
                import json

                endpoint = f"http://localhost:{self.api_port}/api/v0/id"
                req = urllib.request.Request(endpoint, method="POST")
                response = urllib.request.urlopen(req, timeout=2)

                if response.status == 200:
                    data = json.loads(response.read())
                    status["peer_id"] = data.get("ID")
                    status["addresses"] = data.get("Addresses", [])

            except:
                pass

        return status

    def get_config(self, key: Optional[str] = None) -> Dict[str, Any]:
        try:
            result = subprocess.run(
                ["ipfs", "config", key] if key else ["ipfs", "config", "show"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                import json

                try:
                    return json.loads(result.stdout)
                except:
                    return {"value": result.stdout.strip()}

            return {}

        except Exception as e:
            logger.error(f"Failed to get config: {e}")
            return {}

    def set_config(self, key: str, value: Any) -> bool:
        try:
            str_value = str(value)
            result = subprocess.run(
                ["ipfs", "config", key, str_value],
                capture_output=True,
                text=True,
                timeout=10,
            )

            return result.returncode == 0

        except Exception as e:
            logger.error(f"Failed to set config: {e}")
            return False

    def update_bootstrap_config(self, peers: List[str]) -> bool:
        current = self.get_config("Bootstrap")
        if isinstance(current, str):
            try:
                current = json.loads(current)
            except:
                current = []

        current = list(set(current + peers))
        return self.set_config("Bootstrap", json.dumps(current))

    def clear_bootstrap_config(self) -> bool:
        return self.set_config("Bootstrap", "[]")
