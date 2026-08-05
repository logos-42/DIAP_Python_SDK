"""
IPFS (Kubo) 本地节点——全自动安装配置

三步自动搞定：
  1. 检测是否已安装
  2. 未安装 → 自动下载安装
  3. 初始化 + 启动守护进程

用户零操作，程序全自动。
"""

import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import time
import urllib.request
import zipfile
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

from .utils.logger import get_logger

logger = get_logger(__name__)

# 默认 Kubo 版本（可以覆盖）
DEFAULT_KUBO_VERSION = "v0.28.0"


@dataclass
class KuboSetupResult:
    """Kubo 设置结果"""
    ready: bool
    binary_found: bool
    daemon_running: bool
    version: Optional[str] = None
    api_url: Optional[str] = None
    gateway_url: Optional[str] = None
    install_path: Optional[str] = None
    message: Optional[str] = None


# ============================================================================
# 平台检测
# ============================================================================

def _detect_platform() -> str:
    p = platform.system().lower()
    if p == "darwin":
        return "darwin"
    if p == "windows":
        return "windows"
    return "linux"


def _detect_arch() -> str:
    a = platform.machine().lower()
    if a in ("arm64", "aarch64"):
        return "arm64"
    if a in ("x86_64", "amd64"):
        return "amd64"
    if a == "arm":
        return "arm"
    return "amd64"


def _get_install_dir() -> str:
    home = os.path.expanduser("~")
    return os.path.join(home, ".diap", "kubo")


# ============================================================================
# 检查二进制
# ============================================================================

def _check_binary() -> Dict[str, Any]:
    """检查 ipfs 二进制是否可用"""
    try:
        result = subprocess.run(
            ["ipfs", "version", "--enc=json"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            parsed = json.loads(result.stdout.strip())
            version = parsed.get("Version") or parsed.get("version") or "?"
            logger.info(f"  ipfs 已在 PATH 中 (v{version})")
            return {"found": True, "version": version, "path": "ipfs"}
    except Exception:
        pass

    # 检查安装目录
    install_dir = _get_install_dir()
    bin_name = "ipfs.exe" if _detect_platform() == "windows" else "ipfs"
    bin_path = os.path.join(install_dir, bin_name)

    if os.path.exists(bin_path):
        try:
            result = subprocess.run(
                [bin_path, "version", "--enc=json"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                parsed = json.loads(result.stdout.strip())
                version = parsed.get("Version") or parsed.get("version") or "?"
                logger.info(f"  在安装目录找到 ipfs (v{version})")
                os.environ["PATH"] = f"{install_dir}:{os.environ.get('PATH', '')}"
                return {"found": True, "version": version, "path": bin_path}
        except Exception:
            pass

    return {"found": False}


# ============================================================================
# 检查守护进程
# ============================================================================

def _check_daemon() -> Dict[str, Any]:
    """检查 IPFS 守护进程是否运行"""
    api_url = "http://127.0.0.1:5001"
    gateway_url = "http://127.0.0.1:8080"

    try:
        import urllib.request

        req = urllib.request.Request(f"{api_url}/api/v0/id", method="POST")
        with urllib.request.urlopen(req, timeout=3) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode())
                node_id = data.get("ID", "")
                logger.info(f"  节点 ID: {node_id[:12]}...")
                return {"running": True, "api_url": api_url, "gateway_url": gateway_url}
    except Exception:
        pass

    return {"running": False, "api_url": api_url, "gateway_url": gateway_url}


# ============================================================================
# 自动下载安装 Kubo
# ============================================================================

def _get_kubo_version() -> str:
    """获取 Kubo 版本号（简化版：用默认版本）"""
    return DEFAULT_KUBO_VERSION


def _download_and_install(version: str) -> bool:
    """自动下载并安装 Kubo"""
    platform_name = _detect_platform()
    arch = _detect_arch()
    install_dir = _get_install_dir()

    # 创建安装目录
    os.makedirs(install_dir, exist_ok=True)

    # 确定文件名和下载 URL
    ext = ".zip" if platform_name == "windows" else ".tar.gz"
    archive_name = f"kubo_{version}_{platform_name}-{arch}{ext}"
    download_url = f"https://dist.ipfs.tech/kubo/{version}/{archive_name}"
    archive_path = os.path.join(install_dir, archive_name)

    logger.info(f"📥 下载 Kubo {version} ({platform_name}-{arch})...")
    logger.info(f"   来自: {download_url}")

    # 下载
    try:
        urllib.request.urlretrieve(download_url, archive_path)
        size_mb = os.path.getsize(archive_path) / 1024 / 1024
        logger.info(f"   已下载 {size_mb:.1f}MB")
    except Exception as e:
        logger.error(f"   下载失败: {e}")
        return False

    # 解压
    logger.info("📦 解压中...")
    try:
        if platform_name == "windows":
            with zipfile.ZipFile(archive_path, "r") as zf:
                zf.extractall(install_dir)
        else:
            with tarfile.open(archive_path, "r:gz") as tf:
                tf.extractall(install_dir)
    except Exception as e:
        logger.error(f"   解压失败: {e}")
        return False

    # 把 kubo/kubo 二进制移到安装目录根
    kubo_subdir = os.path.join(install_dir, "kubo")
    kubo_bin = "ipfs.exe" if platform_name == "windows" else "ipfs"
    src = os.path.join(kubo_subdir, kubo_bin)
    dst = os.path.join(install_dir, kubo_bin)

    if os.path.exists(src) and not os.path.exists(dst):
        shutil.move(src, dst)

    # 设置可执行权限
    try:
        os.chmod(dst, 0o755)
    except Exception:
        pass

    # 清理：删除下载的压缩包和子目录
    try:
        os.remove(archive_path)
        shutil.rmtree(kubo_subdir, ignore_errors=True)
    except Exception:
        pass

    # 把安装目录加到 PATH
    os.environ["PATH"] = f"{install_dir}:{os.environ.get('PATH', '')}"

    logger.info(f"✅ 安装完成: {dst}")
    return True


def _init_kubo_repo() -> bool:
    """初始化 Kubo 仓库（如果未初始化）"""
    try:
        result = subprocess.run(
            ["ipfs", "init", "--profile", "server"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0:
            logger.info("  ipfs 仓库已初始化")
            return True
        msg = result.stderr or result.stdout or ""
        if "already" in msg.lower():
            logger.info("  ipfs 仓库已存在（跳过初始化）")
            return True
        logger.warning(f"  ipfs init 失败: {msg[:100]}")
        return False
    except Exception as e:
        logger.warning(f"  ipfs init 失败: {e}")
        return False


def _configure_kubo() -> bool:
    """配置 Kubo API 地址（确保本地访问）"""
    try:
        subprocess.run(
            ["ipfs", "config", "Addresses.API", "/ip4/127.0.0.1/tcp/5001"],
            capture_output=True,
            timeout=10,
        )
        subprocess.run(
            ["ipfs", "config", "Addresses.Gateway", "/ip4/127.0.0.1/tcp/8080"],
            capture_output=True,
            timeout=10,
        )
        logger.info("  API 地址已配置为 127.0.0.1:5001")
        return True
    except Exception as e:
        logger.warning(f"  配置失败: {e}")
        return False


# ============================================================================
# 启动守护进程
# ============================================================================

def start_local_kubo() -> bool:
    """启动本地 Kubo 守护进程"""
    try:
        # 用 swarm peers 判断 daemon 是否真正运行
        try:
            subprocess.run(["ipfs", "swarm", "peers"], capture_output=True, timeout=3)
            logger.info("  ✅ 守护进程已在运行")
            return True
        except Exception:
            pass

        logger.info("  🚀 启动守护进程...")
        subprocess.Popen(
            ["ipfs", "daemon", "--enable-pubsub-experiment"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

        # 等待启动（最多 20s）
        for i in range(20):
            time.sleep(1)
            try:
                subprocess.run(["ipfs", "swarm", "peers"], capture_output=True, timeout=2)
                logger.info("  ✅ 守护进程已就绪")
                return True
            except Exception:
                if i % 5 == 4:
                    logger.info(f"  ⏳ 等待守护进程启动... ({i + 1}s)")

        logger.warning("  ⚠️ 守护进程启动超时，可稍后手动运行 `ipfs daemon`")
        return False
    except Exception as e:
        logger.error(f"  ❌ 启动失败: {e}")
        return False


# ============================================================================
# 一键全套
# ============================================================================

def check_kubo_setup(
    auto_install: bool = True,
    auto_start: bool = True,
) -> KuboSetupResult:
    """一键检测 + 自动安装 + 初始化 + 启动"""
    logger.info("🔍 检查 IPFS (Kubo) 本地节点...")

    # === 步骤 1: 检查二进制 ===
    binary = _check_binary()

    # === 步骤 2: 未安装 → 自动下载安装 ===
    if not binary.get("found") and auto_install:
        logger.info("  ipfs 未找到，自动安装中...")
        try:
            version = _get_kubo_version()
            installed = _download_and_install(version)
            if installed:
                binary = _check_binary()
        except Exception as e:
            return KuboSetupResult(
                ready=False,
                binary_found=False,
                daemon_running=False,
                message=f"自动安装失败: {e}",
            )

    if not binary.get("found"):
        return KuboSetupResult(
            ready=False,
            binary_found=False,
            daemon_running=False,
            message="Kubo 安装失败",
        )

    logger.info(f"  ✅ ipfs 就绪 (v{binary.get('version')})")

    # === 步骤 3: 初始化仓库 ===
    init_ok = _init_kubo_repo()

    # === 步骤 4: 配置 API 地址 ===
    if init_ok:
        _configure_kubo()

    # === 步骤 5: 检查/启动守护进程 ===
    daemon = _check_daemon()
    if not daemon.get("running") and auto_start:
        logger.info("  守护进程未运行，自动启动中...")
        started = start_local_kubo()
        if started:
            time.sleep(1)
            daemon = _check_daemon()

    if daemon.get("running"):
        logger.info("✅ Kubo 本地节点完全就绪")
        return KuboSetupResult(
            ready=True,
            binary_found=True,
            daemon_running=True,
            version=binary.get("version"),
            api_url=daemon.get("api_url"),
            gateway_url=daemon.get("gateway_url"),
            install_path=binary.get("path"),
            message="本地 Kubo 已就绪",
        )

    logger.warning("⚠️ 守护进程未运行，DID 发布将降级为仅 CID 模式")
    return KuboSetupResult(
        ready=True,
        binary_found=True,
        daemon_running=False,
        version=binary.get("version"),
        install_path=binary.get("path"),
        message="ipfs 已安装但守护进程未运行",
    )


def ensure_local_ipfs_node() -> Optional[Dict[str, str]]:
    """确保本地 Kubo 节点可用（最简接口）"""
    setup = check_kubo_setup(True, True)
    if setup.ready and setup.daemon_running and setup.api_url and setup.gateway_url:
        return {"api_url": setup.api_url, "gateway_url": setup.gateway_url}
    return None