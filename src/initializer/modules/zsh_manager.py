"""Zsh Manager Module."""

import asyncio
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional

from ..utils.logger import get_logger

logger = get_logger("zsh_manager")


@dataclass
class ZshInfo:
    """Zsh installation information."""

    installed: bool
    version: Optional[str] = None
    path: Optional[str] = None


@dataclass
class OhMyZshInfo:
    """Oh-my-zsh installation information."""

    installed: bool
    version: Optional[str] = None
    config_path: Optional[str] = None
    plugins_installed: List[str] = None

    def __post_init__(self):
        if self.plugins_installed is None:
            self.plugins_installed = []


@dataclass
class PluginInfo:
    """Oh-my-zsh plugin information."""

    name: str
    installed: bool
    repo_url: str
    install_path: str
    description: str = ""
    install_method: str = "git"


class ZshManager:
    """Manager for Zsh and Oh-my-zsh installation and configuration."""

    def __init__(self):
        """Initialize ZshManager."""
        pass

    @staticmethod
    async def detect_zsh() -> ZshInfo:
        """
        检测 Zsh 的安装状态和版本。

        Returns:
            ZshInfo: Zsh 安装信息
        """
        try:
            # 检查 zsh 是否存在
            result = subprocess.run(
                ["which", "zsh"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode != 0:
                logger.debug("Zsh not found in PATH")
                return ZshInfo(installed=False)

            zsh_path = result.stdout.strip()
            logger.debug(f"Zsh found at: {zsh_path}")

            # 获取版本信息
            version_result = subprocess.run(
                ["zsh", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            version = None
            if version_result.returncode == 0:
                # 解析版本号 (格式: "zsh 5.8.1 (x86_64-ubuntu-linux-gnu)")
                output = version_result.stdout.strip()
                parts = output.split()
                if len(parts) >= 2:
                    version = parts[1]

            logger.info(f"Detected Zsh: version={version}, path={zsh_path}")
            return ZshInfo(installed=True, version=version, path=zsh_path)

        except subprocess.TimeoutExpired:
            logger.error("Zsh detection timed out")
            return ZshInfo(installed=False)
        except Exception as exc:
            logger.error(f"Failed to detect Zsh: {exc}", exc_info=True)
            return ZshInfo(installed=False)

    @staticmethod
    async def detect_ohmyzsh() -> OhMyZshInfo:
        """
        检测 Oh-my-zsh 的安装状态和版本。

        Returns:
            OhMyZshInfo: Oh-my-zsh 安装信息
        """
        try:
            # 检查 Oh-my-zsh 目录
            ohmyzsh_path = Path.home() / ".oh-my-zsh"
            if not ohmyzsh_path.exists():
                logger.debug("Oh-my-zsh directory not found")
                return OhMyZshInfo(installed=False)

            logger.debug(f"Oh-my-zsh found at: {ohmyzsh_path}")

            # 尝试获取版本信息（从 git）
            version = None
            git_dir = ohmyzsh_path / ".git"
            if git_dir.exists():
                try:
                    result = subprocess.run(
                        ["git", "-C", str(ohmyzsh_path), "describe", "--tags"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    if result.returncode == 0:
                        version = result.stdout.strip()
                except Exception as exc:
                    logger.debug(f"Failed to get Oh-my-zsh version: {exc}")

            # 扫描已安装的插件
            plugins_installed = []
            custom_plugins_dir = ohmyzsh_path / "custom" / "plugins"
            if custom_plugins_dir.exists():
                try:
                    plugins_installed = [
                        p.name
                        for p in custom_plugins_dir.iterdir()
                        if p.is_dir() and not p.name.startswith(".")
                    ]
                except Exception as exc:
                    logger.debug(f"Failed to scan plugins: {exc}")

            logger.info(
                f"Detected Oh-my-zsh: version={version}, plugins={len(plugins_installed)}"
            )
            return OhMyZshInfo(
                installed=True,
                version=version,
                config_path=str(ohmyzsh_path),
                plugins_installed=plugins_installed,
            )

        except Exception as exc:
            logger.error(f"Failed to detect Oh-my-zsh: {exc}", exc_info=True)
            return OhMyZshInfo(installed=False)

    @staticmethod
    async def get_current_shell() -> str:
        """
        获取当前用户的默认 shell。

        Returns:
            str: 当前默认 shell 的完整路径
        """
        try:
            # 优先从 /etc/passwd 获取（chsh 修改后立即生效）
            import pwd

            user_info = pwd.getpwuid(os.getuid())
            shell = user_info.pw_shell
            logger.debug(f"Current shell from /etc/passwd: {shell}")
            return shell

        except Exception as exc:
            logger.error(f"Failed to get current shell from /etc/passwd: {exc}", exc_info=True)

            # 降级到环境变量
            shell = os.environ.get("SHELL", "/bin/bash")
            logger.debug(f"Fallback to $SHELL: {shell}")
            return shell

    @staticmethod
    async def get_available_shells() -> List[str]:
        """
        获取系统中可用的 shell 列表。

        Returns:
            List[str]: 可用 shell 的完整路径列表
        """
        try:
            shells_file = Path("/etc/shells")
            if not shells_file.exists():
                logger.warning("/etc/shells not found")
                return []

            with open(shells_file, "r") as f:
                shells = [
                    line.strip()
                    for line in f
                    if line.strip() and not line.strip().startswith("#")
                ]

            logger.debug(f"Available shells: {shells}")
            return shells

        except Exception as exc:
            logger.error(f"Failed to read /etc/shells: {exc}", exc_info=True)
            return []

    @staticmethod
    async def check_dependencies() -> dict:
        """
        检查必需的依赖工具是否安装。

        Returns:
            dict: 依赖检查结果 {"git": bool, "curl": bool, "wget": bool}
        """
        deps = {}
        for tool in ["git", "curl", "wget"]:
            try:
                result = subprocess.run(
                    ["which", tool],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                deps[tool] = result.returncode == 0
            except Exception:
                deps[tool] = False

        logger.debug(f"Dependencies check: {deps}")
        return deps

    async def get_plugin_status(self, plugins: List[dict]) -> List[PluginInfo]:
        """
        检查插件列表的安装状态。

        Args:
            plugins: 插件配置列表

        Returns:
            List[PluginInfo]: 插件信息列表
        """
        plugin_infos = []
        ohmyzsh_path = Path.home() / ".oh-my-zsh"

        for plugin in plugins:
            name = plugin.get("name", "")
            repo_url = plugin.get("repo_url", "")
            install_method = plugin.get("install_method", "git")
            description = plugin.get("description", "")

            if install_method == "package_manager":
                # 检查系统包管理器是否安装了该工具
                try:
                    result = subprocess.run(
                        ["which", name],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    installed = result.returncode == 0
                    install_path = result.stdout.strip() if installed else ""
                except Exception:
                    installed = False
                    install_path = ""
            else:
                # 检查 Oh-my-zsh custom/plugins 目录
                install_path = str(ohmyzsh_path / "custom" / "plugins" / name)
                installed = Path(install_path).exists()

            plugin_infos.append(
                PluginInfo(
                    name=name,
                    installed=installed,
                    repo_url=repo_url,
                    install_path=install_path,
                    description=description,
                    install_method=install_method,
                )
            )

        return plugin_infos

    async def change_default_shell(
        self, shell_path: str, progress_callback: Callable[[str], None]
    ) -> dict:
        """
        更改当前用户的默认 shell。

        Args:
            shell_path: 目标 shell 的完整路径
            progress_callback: 进度回调函数

        Returns:
            dict: {"success": bool, "error": str, "output": str}
        """
        try:
            logger.info(f"Changing default shell to: {shell_path}")
            progress_callback(f"Changing default shell to {shell_path}...")

            # 使用 chsh 命令更改 shell
            process = subprocess.Popen(
                ["chsh", "-s", shell_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            output_lines = []
            # 读取输出
            while True:
                line = process.stdout.readline()
                if not line:
                    break
                line = line.strip()
                if line:
                    output_lines.append(line)
                    progress_callback(line)

            # 等待进程完成
            process.wait(timeout=30)

            # 读取错误输出
            stderr = process.stderr.read()

            if process.returncode == 0:
                logger.info("Shell changed successfully")
                progress_callback("Shell changed successfully!")
                return {
                    "success": True,
                    "error": "",
                    "output": "\n".join(output_lines),
                }
            else:
                logger.error(f"Failed to change shell: {stderr}")
                return {
                    "success": False,
                    "error": stderr or "Unknown error",
                    "output": "\n".join(output_lines),
                }

        except subprocess.TimeoutExpired:
            logger.error("Shell change timed out")
            return {"success": False, "error": "Operation timed out", "output": ""}
        except Exception as exc:
            logger.error(f"Failed to change shell: {exc}", exc_info=True)
            return {"success": False, "error": str(exc), "output": ""}

    async def install_zsh(
        self, pm_name: str, progress_callback: Callable[[str], None]
    ) -> dict:
        """
        使用包管理器安装 Zsh。

        Args:
            pm_name: 包管理器名称 (apt, yum, dnf, brew)
            progress_callback: 进度回调函数

        Returns:
            dict: {"success": bool, "error": str, "output": str}
        """
        try:
            logger.info(f"Installing Zsh via {pm_name}")
            progress_callback(f"Installing Zsh using {pm_name}...")

            # 构建安装命令
            if pm_name == "apt":
                cmd = ["sudo", "apt", "install", "-y", "zsh"]
            elif pm_name in ["yum", "dnf"]:
                cmd = ["sudo", pm_name, "install", "-y", "zsh"]
            elif pm_name == "brew":
                cmd = ["brew", "install", "zsh"]
            else:
                return {
                    "success": False,
                    "error": f"Unsupported package manager: {pm_name}",
                    "output": "",
                }

            return await self._run_command(cmd, progress_callback)

        except Exception as exc:
            logger.error(f"Failed to install Zsh: {exc}", exc_info=True)
            return {"success": False, "error": str(exc), "output": ""}

    async def uninstall_zsh(
        self, pm_name: str, progress_callback: Callable[[str], None]
    ) -> dict:
        """
        使用包管理器卸载 Zsh。

        Args:
            pm_name: 包管理器名称
            progress_callback: 进度回调函数

        Returns:
            dict: {"success": bool, "error": str, "output": str}
        """
        try:
            logger.info(f"Uninstalling Zsh via {pm_name}")
            progress_callback(f"Uninstalling Zsh using {pm_name}...")

            # 构建卸载命令
            if pm_name == "apt":
                cmd = ["sudo", "apt", "remove", "-y", "zsh"]
            elif pm_name in ["yum", "dnf"]:
                cmd = ["sudo", pm_name, "remove", "-y", "zsh"]
            elif pm_name == "brew":
                cmd = ["brew", "uninstall", "zsh"]
            else:
                return {
                    "success": False,
                    "error": f"Unsupported package manager: {pm_name}",
                    "output": "",
                }

            return await self._run_command(cmd, progress_callback)

        except Exception as exc:
            logger.error(f"Failed to uninstall Zsh: {exc}", exc_info=True)
            return {"success": False, "error": str(exc), "output": ""}

    async def install_ohmyzsh(
        self, install_url: str, progress_callback: Callable[[str], None]
    ) -> dict:
        """
        安装 Oh-my-zsh。

        Args:
            install_url: 安装脚本 URL
            progress_callback: 进度回调函数

        Returns:
            dict: {"success": bool, "error": str, "output": str}
        """
        try:
            logger.info(f"Installing Oh-my-zsh from {install_url}")
            progress_callback("Downloading Oh-my-zsh installation script...")

            # 使用 curl 下载并执行安装脚本
            cmd = [
                "sh",
                "-c",
                f'$(curl -fsSL {install_url}) "" --unattended',
            ]

            return await self._run_command(cmd, progress_callback, timeout=300)

        except Exception as exc:
            logger.error(f"Failed to install Oh-my-zsh: {exc}", exc_info=True)
            return {"success": False, "error": str(exc), "output": ""}

    async def uninstall_ohmyzsh(
        self, progress_callback: Callable[[str], None]
    ) -> dict:
        """
        卸载 Oh-my-zsh。

        Args:
            progress_callback: 进度回调函数

        Returns:
            dict: {"success": bool, "error": str, "output": str}
        """
        try:
            logger.info("Uninstalling Oh-my-zsh")
            progress_callback("Uninstalling Oh-my-zsh...")

            ohmyzsh_path = Path.home() / ".oh-my-zsh"
            if not ohmyzsh_path.exists():
                return {
                    "success": True,
                    "error": "",
                    "output": "Oh-my-zsh not installed",
                }

            # 重命名目录而不是删除（安全备份）
            import time

            timestamp = int(time.time())
            backup_path = Path.home() / f".oh-my-zsh.removed.{timestamp}"

            progress_callback(f"Moving {ohmyzsh_path} to {backup_path}...")
            ohmyzsh_path.rename(backup_path)

            # 备份 .zshrc
            zshrc_path = Path.home() / ".zshrc"
            if zshrc_path.exists():
                zshrc_backup = Path.home() / f".zshrc.backup.{timestamp}"
                progress_callback(f"Backing up .zshrc to {zshrc_backup}...")
                zshrc_path.rename(zshrc_backup)

            logger.info("Oh-my-zsh uninstalled successfully")
            progress_callback("Oh-my-zsh uninstalled successfully!")
            return {"success": True, "error": "", "output": "Uninstalled successfully"}

        except Exception as exc:
            logger.error(f"Failed to uninstall Oh-my-zsh: {exc}", exc_info=True)
            return {"success": False, "error": str(exc), "output": ""}

    async def install_plugin(
        self, plugin: dict, progress_callback: Callable[[str], None]
    ) -> dict:
        """
        安装 Oh-my-zsh 插件。

        Args:
            plugin: 插件配置字典
            progress_callback: 进度回调函数

        Returns:
            dict: {"success": bool, "error": str, "output": str}
        """
        try:
            name = plugin.get("name", "")
            repo_url = plugin.get("repo_url", "")
            install_method = plugin.get("install_method", "git")

            logger.info(f"Installing plugin: {name}")
            progress_callback(f"Installing plugin: {name}...")

            if install_method == "package_manager":
                # 使用包管理器安装
                progress_callback(f"Installing {name} via package manager...")
                # 这里需要根据实际情况选择包管理器
                cmd = ["sudo", "apt", "install", "-y", name]
                return await self._run_command(cmd, progress_callback)
            else:
                # 使用 git clone 安装
                ohmyzsh_path = Path.home() / ".oh-my-zsh"
                plugins_dir = ohmyzsh_path / "custom" / "plugins"
                plugin_path = plugins_dir / name

                if plugin_path.exists():
                    return {
                        "success": True,
                        "error": "",
                        "output": f"Plugin {name} already installed",
                    }

                # 确保 plugins 目录存在
                plugins_dir.mkdir(parents=True, exist_ok=True)

                progress_callback(f"Cloning {repo_url}...")
                cmd = ["git", "clone", repo_url, str(plugin_path)]
                return await self._run_command(cmd, progress_callback)

        except Exception as exc:
            logger.error(f"Failed to install plugin: {exc}", exc_info=True)
            return {"success": False, "error": str(exc), "output": ""}

    async def uninstall_plugin(
        self, plugin: dict, progress_callback: Callable[[str], None]
    ) -> dict:
        """
        卸载 Oh-my-zsh 插件。

        Args:
            plugin: 插件配置字典
            progress_callback: 进度回调函数

        Returns:
            dict: {"success": bool, "error": str, "output": str}
        """
        try:
            name = plugin.get("name", "")
            install_method = plugin.get("install_method", "git")

            logger.info(f"Uninstalling plugin: {name}")
            progress_callback(f"Uninstalling plugin: {name}...")

            if install_method == "package_manager":
                # 使用包管理器卸载
                cmd = ["sudo", "apt", "remove", "-y", name]
                return await self._run_command(cmd, progress_callback)
            else:
                # 删除插件目录
                ohmyzsh_path = Path.home() / ".oh-my-zsh"
                plugin_path = ohmyzsh_path / "custom" / "plugins" / name

                if not plugin_path.exists():
                    return {
                        "success": True,
                        "error": "",
                        "output": f"Plugin {name} not installed",
                    }

                import shutil

                progress_callback(f"Removing {plugin_path}...")
                shutil.rmtree(plugin_path)

                logger.info(f"Plugin {name} uninstalled successfully")
                progress_callback("Plugin uninstalled successfully!")
                return {
                    "success": True,
                    "error": "",
                    "output": "Uninstalled successfully",
                }

        except Exception as exc:
            logger.error(f"Failed to uninstall plugin: {exc}", exc_info=True)
            return {"success": False, "error": str(exc), "output": ""}

    async def _run_command(
        self,
        cmd: List[str],
        progress_callback: Callable[[str], None],
        timeout: int = 120,
    ) -> dict:
        """
        执行命令并实时输出到回调函数。

        Args:
            cmd: 命令列表
            progress_callback: 进度回调函数
            timeout: 超时时间（秒）

        Returns:
            dict: {"success": bool, "error": str, "output": str}
        """
        try:
            logger.debug(f"Running command: {' '.join(cmd)}")
            progress_callback(f"Executing: {' '.join(cmd)}")

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            output_lines = []

            # 实时读取输出
            while True:
                line = process.stdout.readline()
                if not line:
                    break
                line = line.rstrip()
                if line:
                    output_lines.append(line)
                    progress_callback(line)

            # 等待进程完成
            process.wait(timeout=timeout)

            output = "\n".join(output_lines)

            if process.returncode == 0:
                logger.info("Command executed successfully")
                progress_callback("Command completed successfully!")
                return {"success": True, "error": "", "output": output}
            else:
                logger.error(f"Command failed with code {process.returncode}")
                return {
                    "success": False,
                    "error": f"Command failed with exit code {process.returncode}",
                    "output": output,
                }

        except subprocess.TimeoutExpired:
            logger.error("Command timed out")
            process.kill()
            return {"success": False, "error": "Operation timed out", "output": ""}
        except Exception as exc:
            logger.error(f"Command execution failed: {exc}", exc_info=True)
            return {"success": False, "error": str(exc), "output": ""}
