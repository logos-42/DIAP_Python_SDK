"""
内存 IPFS 客户端
用于开发/测试场景，无需外部 IPFS 节点或 Pinata 凭据
DID 文档存储在内存 Map 中，CID 基于 SHA256 生成
"""

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Optional

from .ipfs_client import IPFSClient
from .utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class IpfsUploadResult:
    """IPFS 上传结果"""
    cid: str
    size: int
    uploaded_at: str
    provider: str


class MemoryIpfsClient(IPFSClient):
    """内存 IPFS 客户端
    所有上传内容存储在内存中，生成确定性 CID
    读取优先查内存，查不到再回退到公共网关
    """

    # 静态内存存储: CID → content
    _store: Dict[str, str] = {}

    def __init__(self):
        super().__init__()
        logger.info("📦 使用内存 IPFS 客户端（不上传到外部网络）")

    @staticmethod
    async def new_memory() -> "MemoryIpfsClient":
        """创建内存模式客户端"""
        return MemoryIpfsClient()

    @staticmethod
    def compute_cid(content: str) -> str:
        """从内容计算确定性 CID
        格式: mem-<sha256-hex[:32]>
        不生成真实 IPFS CID，但在本进程内可解析
        """
        hash_bytes = hashlib.sha256(content.encode()).digest()
        hex_str = hash_bytes.hex()
        return f"mem-{hex_str[:32]}"

    async def upload(self, content: str, name: str = "data") -> IpfsUploadResult:
        """上传内容到内存存储"""
        cid = MemoryIpfsClient.compute_cid(content)
        MemoryIpfsClient._store[cid] = content
        logger.info(f"📦 内存上传成功: {cid} ({len(content)}B, name={name})")
        return IpfsUploadResult(
            cid=cid,
            size=len(content),
            uploaded_at=datetime.now(timezone.utc).isoformat(),
            provider="memory",
        )

    async def get(self, cid: str) -> Optional[str]:
        """从内存获取内容，查不到再回退到公共网关"""
        content = MemoryIpfsClient._store.get(cid)
        if content:
            logger.info(f"📦 内存命中: {cid}")
            return content
        logger.info(f"📦 内存未命中 {cid}，回退到公共网关")
        return await super().get(cid)

    def has(self, cid: str) -> bool:
        """检查内容是否存在"""
        return cid in MemoryIpfsClient._store

    @staticmethod
    def get_store_size() -> int:
        """获取存储大小"""
        return len(MemoryIpfsClient._store)

    @staticmethod
    def clear_store() -> None:
        """清空存储（用于测试清理）"""
        MemoryIpfsClient._store.clear()