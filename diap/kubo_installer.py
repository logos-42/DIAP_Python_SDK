import os
import platform
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Optional
from urllib.request import urlretrieve

from .types.errors import IPFSError
from .utils.logger import get_logger

logger = get_logger(__name__)


class KuboInstaller:
    KUBO_VERSION = "0.24.0"
    KUBO_DOWNLOAD_URLS = {
        "linux": f"https://dist.ipfs.tech/kubo/v{KUBO_VERSION}/kubo_v{KUBO_VERSION}_linux-amd64.tar.gz",
        "darwin": f"https://dist.ipfs.tech/kubo/v{KUBO_VERSION}/kubo_v{KUBO_VERSION}_darwin-amd64.tar.gz",
        "windows": f"https://dist.ipfs.tech/kubo/v{KUBO_VERSION}/kubo_v{KUBO_VERSION}_windows-amd64.zip",
    }

    def __init__(
        self,
        install_path: Optional[str] = None,
        bin_path: Optional[str] = None,
    ):
        self.install_path = os.path.expanduser(
            install_path or os.path.join("~", ".diap", "kubo")
        )
        self.bin_path = os.path.expanduser(
            bin_path or os.path.join("~", ".local", "bin")
        )
        self._system = platform.system().lower()

    def is_installed(self) -> bool:
        try:
            result = subprocess.run(
                ["ipfs", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except:
            return False

    def get_installed_version(self) -> Optional[str]:
        try:
            result = subprocess.run(
                ["ipfs", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return result.stdout.strip().replace("ipfs version: ", "")
            return None
        except:
            return None

    def install(self, force: bool = False) -> bool:
        if self.is_installed() and not force:
            logger.info("IPFS already installed")
            return True

        if self._system == "windows":
            return self._install_windows()
        elif self._system == "darwin":
            return self._install_mac()
        elif self._system == "linux":
            return self._install_linux()
        else:
            raise IPFSError(f"Unsupported platform: {self._system}")

    def _install_windows(self) -> bool:
        logger.info("Installing Kubo for Windows...")

        url = self.KUBO_DOWNLOAD_URLS["windows"]

        try:
            with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
                zip_path = f.name
                logger.info(f"Downloading {url}...")
                urlretrieve(url, zip_path)

            with tempfile.TemporaryDirectory() as temp_dir:
                with zipfile.ZipFile(zip_path, "r") as zip_ref:
                    zip_ref.extractall(temp_dir)

                os.makedirs(self.install_path, exist_ok=True)
                os.makedirs(self.bin_path, exist_ok=True)

                extract_path = Path(temp_dir)
                for file in extract_path.rglob("*.exe"):
                    dest = os.path.join(self.bin_path, file.name)
                    if not os.path.exists(dest) or file.name == "ipfs.exe":
                        import shutil

                        shutil.copy2(file, dest)

                for file in extract_path.rglob("*.cmd"):
                    dest = os.path.join(self.bin_path, file.name)
                    if not os.path.exists(dest):
                        import shutil

                        shutil.copy2(file, dest)

            os.unlink(zip_path)

            self._add_to_path()
            logger.info("Kubo installed successfully")
            return True

        except Exception as e:
            raise IPFSError(f"Failed to install Kubo: {e}")

    def _install_mac(self) -> bool:
        logger.info("Installing Kubo for macOS...")

        url = self.KUBO_DOWNLOAD_URLS["darwin"]

        try:
            with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as f:
                tar_path = f.name
                logger.info(f"Downloading {url}...")
                urlretrieve(url, tar_path)

            with tempfile.TemporaryDirectory() as temp_dir:
                import tarfile

                with tarfile.open(tar_path, "r:gz") as tar_ref:
                    tar_ref.extractall(temp_dir)

                os.makedirs(self.install_path, exist_ok=True)
                os.makedirs(self.bin_path, exist_ok=True)

                extract_path = Path(temp_dir)
                for file in extract_path.rglob("ipfs*"):
                    dest = os.path.join(self.bin_path, file.name)
                    if not os.path.exists(dest):
                        import shutil

                        shutil.copy2(file, dest)
                        os.chmod(dest, 0o755)

            os.unlink(tar_path)

            self._add_to_path()
            logger.info("Kubo installed successfully")
            return True

        except Exception as e:
            raise IPFSError(f"Failed to install Kubo: {e}")

    def _install_linux(self) -> bool:
        return self._install_mac()

    def _add_to_path(self):
        shell_config = ""
        if self._system == "darwin":
            shell_config = os.path.expanduser("~/.zshrc")
        elif self._system == "linux":
            shell_config = os.path.expanduser("~/.bashrc")
        elif self._system == "windows":
            import winreg

            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Environment",
                0,
                winreg.KEY_SET_VALUE,
            )
            current_path = winreg.QueryValueEx(key, "Path")[0]
            if self.bin_path not in current_path:
                winreg.SetValueEx(
                    key,
                    "Path",
                    0,
                    winreg.REG_EXPAND_SZ,
                    f"{current_path};{self.bin_path}",
                )
            winreg.CloseKey(key)
            return

        if shell_config and os.path.exists(shell_config):
            with open(shell_config, "a") as f:
                f.write(f'\nexport PATH="$PATH:{self.bin_path}"\n')

    def uninstall(self) -> bool:
        try:
            if os.path.exists(self.install_path):
                import shutil

                shutil.rmtree(self.install_path)

            for file in ["ipfs", "ipfs.exe"]:
                path = os.path.join(self.bin_path, file)
                if os.path.exists(path):
                    os.remove(path)

            logger.info("Kubo uninstalled")
            return True

        except Exception as e:
            logger.error(f"Failed to uninstall: {e}")
            return False

    def verify_installation(self) -> bool:
        if not self.is_installed():
            return False

        try:
            result = subprocess.run(
                ["ipfs", "version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except:
            return False
