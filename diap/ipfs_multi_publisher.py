"""
IPFS Multi-Node Publisher
多节点 IPNS 发布器，支持本地 IPFS 节点和多个远程节点并行发布
"""

import base64
import json
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

import aiohttp

from .types.errors import IPFSError
from .utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class MultiNodePublishResult:
    success: bool
    cid: str
    ipns_name: Optional[str] = None
    published_nodes: List[str] = field(default_factory=list)
    failed_nodes: List[str] = field(default_factory=list)
    total_time_ms: int = 0


@dataclass
class IpfsNodeConfig:
    api_url: str
    gateway_url: Optional[str] = None
    is_local: bool = False
    headers: Optional[Dict[str, str]] = None


@dataclass
class GatewayCredentials:
    pinata: Optional[Dict[str, str]] = None
    infura: Optional[Dict[str, str]] = None
    web3_storage: Optional[Dict[str, str]] = None


def _build_auth_header(credentials: GatewayCredentials) -> Optional[Dict[str, str]]:
    """构建认证头"""
    if credentials.pinata:
        token = base64.b64encode(
            f"{credentials.pinata['apiKey']}:{credentials.pinata['secretKey']}".encode()
        ).decode()
        return {"Authorization": f"Basic {token}"}
    if credentials.infura:
        token = base64.b64encode(
            f"{credentials.infura['projectId']}:{credentials.infura['projectSecret']}".encode()
        ).decode()
        return {"Authorization": f"Basic {token}"}
    if credentials.web3_storage:
        return {"Authorization": f"Bearer {credentials.web3_storage['token']}"}
    return None


class IpfsMultiPublisher:
    """多节点 IPNS 发布器"""

    def __init__(
        self,
        key_name: str,
        local_node: Optional[IpfsNodeConfig] = None,
        remote_nodes: Optional[List[IpfsNodeConfig]] = None,
    ):
        self.key_name = key_name
        self.local_node = local_node
        self.remote_nodes = remote_nodes or []
        self.key_ensured = False

    async def _ensure_key_exists_on_node(self, node: IpfsNodeConfig) -> bool:
        """确保密钥在指定节点上存在"""
        try:
            url_list = f"{node.api_url}/key/list"
            async with aiohttp.ClientSession() as session:
                async with session.post(url_list, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        logger.warning(f"节点 {node.api_url} 的 key/list 请求失败")
                        return False
                    v = await resp.json()
                    keys = v.get("Keys", [])
                    exists = any(k.get("Name") == self.key_name for k in keys)

                    if exists:
                        logger.info(f"密钥 {self.key_name} 在节点 {node.api_url} 已存在")
                        return True
        except Exception as e:
            logger.warning(f"检查密钥是否存在时出错 {node.api_url}: {e}")

        try:
            url_gen = f"{node.api_url}/key/gen?arg={self.key_name}&type=ed25519"
            async with aiohttp.ClientSession() as session:
                async with session.post(url_gen, timeout=aiohttp.ClientTimeout(total=30)) as resp_gen:
                    if resp_gen.status == 200:
                        logger.info(f"密钥 {self.key_name} 在节点 {node.api_url} 创建成功")
                        return True
                    else:
                        text = await resp_gen.text()
                        logger.warning(f"节点 {node.api_url} 创建密钥失败: {resp_gen.status} - {text}")
                        return False
        except Exception as e:
            logger.warning(f"创建密钥时出错 {node.api_url}: {e}")
            return False

    async def ensure_key_exists(self) -> None:
        """确保密钥在所有可用节点上存在"""
        if self.key_ensured:
            return

        nodes_to_check: List[IpfsNodeConfig] = []
        if self.local_node:
            nodes_to_check.append(self.local_node)

        logger.info(f"开始确保密钥 {self.key_name} 在 {len(nodes_to_check)} 个节点上存在")

        results = []
        for node in nodes_to_check:
            results.append(await self._ensure_key_exists_on_node(node))

        if any(results):
            self.key_ensured = True
            logger.info(f"密钥 {self.key_name} 初始化完成")
        else:
            logger.warning("所有节点的密钥初始化都失败了，发布时可能失败")

    @staticmethod
    async def check_local_node() -> bool:
        """检查本地 IPFS 节点是否可用"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "http://localhost:5001/api/v0/id",
                    timeout=aiohttp.ClientTimeout(total=3),
                ) as resp:
                    return resp.status == 200
        except Exception:
            return False

    async def publish_multi_node(self, cid: str) -> MultiNodePublishResult:
        """从多节点并行发布 IPNS"""
        start_time = time.time() * 1000
        published_nodes: List[str] = []
        failed_nodes: List[str] = []
        ipns_name: Optional[str] = None

        if not self.local_node:
            logger.info("⚠️ 没有可用的本地 IPFS 节点，跳过 IPNS 发布（仅使用 CID）")
            return MultiNodePublishResult(
                success=False,
                cid=cid,
                published_nodes=[],
                failed_nodes=[],
                total_time_ms=int(time.time() * 1000 - start_time),
            )

        logger.info("开始发布 IPNS（仅本地节点）")
        logger.info(f"  本地节点: {self.local_node.api_url}")

        try:
            result = await self._publish_to_node(self.local_node, cid)
            published_nodes.append(self.local_node.api_url)
            if result and result.get("Name"):
                ipns_name = result["Name"]
            logger.info(f"✅ 本地 IPNS 发布成功: {ipns_name or 'N/A'}")
        except Exception as e:
            failed_nodes.append(self.local_node.api_url)
            logger.warning(f"⚠️ 本地 IPNS 发布失败: {e}")

        total_time_ms = int(time.time() * 1000 - start_time)
        success = len(published_nodes) > 0

        logger.info(f"  结果: {'✅ 成功' if success else '❌ 失败'} ({total_time_ms}ms)")

        return MultiNodePublishResult(
            success=success,
            cid=cid,
            ipns_name=ipns_name,
            published_nodes=published_nodes,
            failed_nodes=failed_nodes,
            total_time_ms=total_time_ms,
        )

    async def _publish_to_node(self, node: IpfsNodeConfig, cid: str) -> Dict[str, Any]:
        """向单个节点发布"""
        arg_path = f"/ipfs/{cid}"
        url = f"{node.api_url}/name/publish?arg={arg_path}&key={self.key_name}&allow-offline=true&resolve=true"

        headers = {"User-Agent": "diap-python-sdk/0.2"}
        if node.headers:
            headers.update(node.headers)

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise IPFSError(f"{resp.status}: {text}")
                return await resp.json()

    def get_local_node(self) -> Optional[IpfsNodeConfig]:
        """获取本地节点配置"""
        return self.local_node

    def set_local_node(self, node: IpfsNodeConfig) -> None:
        """设置本地节点"""
        self.local_node = node


def is_kubo_installed() -> bool:
    """检查本地 IPFS Kubo 是否已安装"""
    try:
        result = subprocess.run(
            ["ipfs", "version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False


def start_local_kubo() -> Dict[str, Any]:
    """启动本地 IPFS 守护进程"""
    try:
        # 检查是否已运行
        try:
            subprocess.run(["ipfs", "id"], capture_output=True, timeout=5)
            logger.info("IPFS 守护进程已在运行")
            return {"success": True}
        except Exception:
            pass

        # 在后台启动 ipfs daemon
        subprocess.Popen(
            ["ipfs", "daemon", "--enable-pubsub-experiment"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

        # 等待 daemon 启动
        time.sleep(5)

        logger.info("IPFS 守护进程已启动")
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def create_multi_publisher(key_name: str) -> IpfsMultiPublisher:
    """创建多节点发布器，自动检测本地节点"""
    local_node_available = await IpfsMultiPublisher.check_local_node()

    local_node: Optional[IpfsNodeConfig] = None
    if local_node_available:
        local_node = IpfsNodeConfig(
            api_url="http://localhost:5001/api/v0",
            gateway_url="http://localhost:8080",
            is_local=True,
        )
        logger.info("✅ 检测到本地 Kubo 节点，将用于 IPNS 发布")
    else:
        logger.info("ℹ️ 本地 Kubo 节点不可用，跳过 IPNS 发布（仅使用 CID）")

    publisher = IpfsMultiPublisher(key_name, local_node)
    await publisher.ensure_key_exists()
    return publisher


async def create_pinata_publisher(
    key_name: str, api_key: str, secret_key: str
) -> IpfsMultiPublisher:
    """使用 Pinata 凭证创建发布器"""
    auth_header = _build_auth_header(
        GatewayCredentials(pinata={"apiKey": api_key, "secretKey": secret_key})
    )

    local_node_available = await IpfsMultiPublisher.check_local_node()

    nodes: List[IpfsNodeConfig] = []
    if local_node_available:
        nodes.append(
            IpfsNodeConfig(
                api_url="http://localhost:5001/api/v0",
                gateway_url="http://localhost:8080",
                is_local=True,
            )
        )
        logger.info("使用本地 IPFS 节点 + Pinata 进行发布")

    nodes.append(
        IpfsNodeConfig(
            api_url="https://api.pinata.cloud/pinning/pinFileToIPFS",
            gateway_url="https://gateway.pinata.cloud/ipfs/",
            is_local=False,
            headers=auth_header,
        )
    )

    publisher = IpfsMultiPublisher(key_name, nodes[0] if nodes else None, nodes[1:])
    await publisher.ensure_key_exists()
    return publisher


async def create_infura_publisher(
    key_name: str, project_id: str, project_secret: str
) -> IpfsMultiPublisher:
    """使用 Infura 凭证创建发布器"""
    auth_header = _build_auth_header(
        GatewayCredentials(infura={"projectId": project_id, "projectSecret": project_secret})
    )

    local_node_available = await IpfsMultiPublisher.check_local_node()

    nodes: List[IpfsNodeConfig] = []
    if local_node_available:
        nodes.append(
            IpfsNodeConfig(
                api_url="http://localhost:5001/api/v0",
                gateway_url="http://localhost:8080",
                is_local=True,
            )
        )
        logger.info("使用本地 IPFS 节点 + Infura 进行发布")

    nodes.append(
        IpfsNodeConfig(
            api_url="https://ipfs.infura.io:5001/api/v0",
            gateway_url="https://ipfs.infura.io/ipfs/",
            is_local=False,
            headers=auth_header,
        )
    )

    publisher = IpfsMultiPublisher(key_name, nodes[0] if nodes else None, nodes[1:])
    await publisher.ensure_key_exists()
    return publisher


async def create_web3_storage_publisher(
    key_name: str, token: str
) -> IpfsMultiPublisher:
    """使用 Web3.Storage 凭证创建发布器"""
    auth_header = _build_auth_header(
        GatewayCredentials(web3_storage={"token": token})
    )

    local_node_available = await IpfsMultiPublisher.check_local_node()

    nodes: List[IpfsNodeConfig] = []
    if local_node_available:
        nodes.append(
            IpfsNodeConfig(
                api_url="http://localhost:5001/api/v0",
                gateway_url="http://localhost:8080",
                is_local=True,
            )
        )
        logger.info("使用本地 IPFS 节点 + Web3.Storage 进行发布")

    nodes.append(
        IpfsNodeConfig(
            api_url="https://api.web3.storage/upload",
            gateway_url="https://w3s.link/ipfs/",
            is_local=False,
            headers=auth_header,
        )
    )

    publisher = IpfsMultiPublisher(key_name, nodes[0] if nodes else None, nodes[1:])
    await publisher.ensure_key_exists()
    return publisher


async def create_custom_publisher(
    key_name: str,
    api_url: str,
    gateway_url: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None,
) -> IpfsMultiPublisher:
    """使用自定义网关凭证创建发布器"""
    local_node_available = await IpfsMultiPublisher.check_local_node()

    nodes: List[IpfsNodeConfig] = []
    if local_node_available:
        nodes.append(
            IpfsNodeConfig(
                api_url="http://localhost:5001/api/v0",
                gateway_url="http://localhost:8080",
                is_local=True,
            )
        )
        logger.info("使用本地 IPFS 节点 + 自定义网关进行发布")

    nodes.append(
        IpfsNodeConfig(
            api_url=api_url,
            gateway_url=gateway_url,
            is_local=False,
            headers=headers,
        )
    )

    publisher = IpfsMultiPublisher(key_name, nodes[0] if nodes else None, nodes[1:])
    await publisher.ensure_key_exists()
    return publisher