"""Zsh Manager Module."""

import asyncio
import os
import re
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


@dataclass
class ShellConfig:
    """Shell configuration for migration."""

    tool_name: str
    config_lines: List[str]
    source_file: str
    description: str
    priority: int
    selected: bool = True


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
            List[str]: 可用 shell 的完整路径列表（已去重）
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

            # 使用 dict.fromkeys 进行去重，保持原始顺序
            unique_shells = list(dict.fromkeys(shells))

            # 记录去重信息
            if len(unique_shells) != len(shells):
                logger.debug(f"Filtered duplicate shells: {len(shells)} -> {len(unique_shells)}")
                logger.debug(f"Original: {shells}")
                logger.debug(f"Unique: {unique_shells}")

            logger.debug(f"Available shells: {unique_shells}")
            return unique_shells

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

    @staticmethod
    async def detect_shell_configs(current_shell: str) -> List[ShellConfig]:
        """
        检测原有 shell 配置文件中的开发工具配置。

        Args:
            current_shell: 当前默认 shell 的完整路径

        Returns:
            List[ShellConfig]: 检测到的配置列表，按优先级排序
        """
        configs = []

        # 确定要检查的配置文件
        shell_name = Path(current_shell).name
        config_files = []

        if shell_name == "bash":
            config_files = [
                Path.home() / ".bashrc",
                Path.home() / ".bash_profile",
                Path.home() / ".profile"
            ]
        elif shell_name == "zsh":
            config_files = [
                Path.home() / ".zshrc"
            ]
        else:
            # 其他 shell，检查通用配置文件
            config_files = [
                Path.home() / f".{shell_name}rc",
                Path.home() / ".profile"
            ]

        # 工具配置模式定义
        tool_patterns = [
            {
                "name": "uv",
                "description": "Python 包管理和项目管理工具",
                "priority": 1,
                "patterns": [
                    r'export\s+PATH=.*uv.*:?[\w/-]*',
                    r'alias\s+uv=',
                    r'source\s+.*uv',
                    r'\.?\s+.*uv/env'
                ]
            },
            {
                "name": "nvm",
                "description": "Node.js 版本管理器",
                "priority": 2,
                "patterns": [
                    r'export\s+NVM_DIR=',
                    r'source\s+.*nvm\.sh',
                    r'\[?\s*-s\s+.*nvm',
                    r'cargo\s+install\s+nvm'
                ]
            },
            {
                "name": "conda",
                "description": "Anaconda/Miniconda Python 环境",
                "priority": 3,
                "patterns": [
                    r'source\s+.*conda\.sh',
                    r'conda\s+init',
                    r'export\s+PATH=.*conda',
                    r'__conda_setup'
                ]
            },
            {
                "name": "pyenv",
                "description": "Python 版本管理器",
                "priority": 4,
                "patterns": [
                    r'export\s+PYENV_ROOT=',
                    r'eval\s+"\$\(pyenv\s+init\s-\)"',
                    r'eval\s+"\$\(pyenv\s+virtualenv-init\s-\)"',
                    r'export\s+PATH=.*pyenv'
                ]
            },
            {
                "name": "rbenv",
                "description": "Ruby 版本管理器",
                "priority": 5,
                "patterns": [
                    r'export\s+RBENV_ROOT=',
                    r'eval\s+"\$\(rbenv\s+init\s-\)"',
                    r'export\s+PATH=.*rbenv'
                ]
            },
            {
                "name": "goenv",
                "description": "Go 版本管理器",
                "priority": 6,
                "patterns": [
                    r'export\s+GOENV_ROOT=',
                    r'eval\s+"\$\(goenv\s+init\s-\)"',
                    r'export\s+PATH=.*goenv'
                ]
            },
            {
                "name": "docker",
                "description": "Docker 容器环境",
                "priority": 7,
                "patterns": [
                    r'export\s+DOCKER_',
                    r'source\s+.*docker',
                    r'alias\s+docker='
                ]
            }
        ]

        # 检查每个配置文件
        for config_file in config_files:
            if not config_file.exists():
                logger.debug(f"Config file not found: {config_file}")
                continue

            try:
                with open(config_file, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()

                logger.debug(f"Analyzing config file: {config_file}")

                # 为每个工具检查配置模式
                for tool in tool_patterns:
                    tool_config_lines = []

                    for line_num, line in enumerate(lines, 1):
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue

                        # 检查是否匹配任何模式
                        for pattern in tool["patterns"]:
                            if re.search(pattern, line, re.IGNORECASE):
                                logger.debug(f"Found {tool['name']} config in {config_file}:{line_num}: {line}")
                                tool_config_lines.append(line)
                                break

                    # 如果找到配置，创建 ShellConfig 对象
                    if tool_config_lines:
                        configs.append(ShellConfig(
                            tool_name=tool["name"],
                            config_lines=tool_config_lines,
                            source_file=str(config_file),
                            description=tool["description"],
                            priority=tool["priority"]
                        ))

            except Exception as exc:
                logger.error(f"Failed to read config file {config_file}: {exc}", exc_info=True)
                continue

        # 按优先级排序
        configs.sort(key=lambda x: x.priority)

        logger.info(f"Detected {len(configs)} shell configurations from {shell_name}")
        return configs

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

            # 使用 curl 下载并执行安装脚本（管道方式）
            cmd = [
                "bash",
                "-c",
                f"curl -fsSL {install_url} | bash -s -- --unattended",
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

    async def migrate_shell_configs(
        self,
        configs: List[ShellConfig],
        target_file: str = "~/.zshrc",
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> dict:
        """
        将检测到的配置迁移到目标 shell 配置文件。

        Args:
            configs: 要迁移的配置列表
            target_file: 目标配置文件路径
            progress_callback: 进度回调函数

        Returns:
            dict: {"success": bool, "error": str, "output": str, "backup_path": str}
        """
        try:
            from datetime import datetime
            import time

            # 默认进度回调
            if progress_callback is None:
                progress_callback = lambda msg: logger.info(msg)

            logger.info(f"Starting shell configuration migration to {target_file}")
            progress_callback("开始配置迁移...")

            # 解析目标文件路径
            target_path = Path(target_file).expanduser()
            backup_path = None

            # 过滤选中的配置
            selected_configs = [config for config in configs if config.selected]
            if not selected_configs:
                return {
                    "success": False,
                    "error": "No configurations selected for migration",
                    "output": "",
                    "backup_path": ""
                }

            progress_callback(f"准备迁移 {len(selected_configs)} 个工具配置...")

            # 备份现有的 .zshrc 文件
            if target_path.exists():
                timestamp = int(time.time())
                backup_path = target_path.parent / f"{target_path.name}.backup.{timestamp}"
                progress_callback(f"备份现有配置到 {backup_path}...")

                try:
                    import shutil
                    shutil.copy2(target_path, backup_path)
                    logger.info(f"Backup created at: {backup_path}")
                except Exception as backup_exc:
                    logger.error(f"Failed to create backup: {backup_exc}")
                    return {
                        "success": False,
                        "error": f"Failed to create backup: {backup_exc}",
                        "output": "",
                        "backup_path": ""
                    }

            # 读取现有内容（如果存在）
            existing_content = ""
            if target_path.exists():
                try:
                    with open(target_path, 'r', encoding='utf-8') as f:
                        existing_content = f.read()
                except Exception as read_exc:
                    logger.error(f"Failed to read existing {target_path}: {read_exc}")

            # 准备要写入的内容
            migration_content = self._prepare_migration_content(selected_configs, progress_callback)

            # 写入配置
            try:
                with open(target_path, 'w', encoding='utf-8') as f:
                    # 写入现有内容
                    if existing_content.strip():
                        f.write(existing_content)
                        if not existing_content.endswith('\n'):
                            f.write('\n')
                        f.write('\n')

                    # 写入迁移内容
                    f.write(migration_content)

                logger.info(f"Successfully migrated configurations to {target_path}")
                progress_callback("配置迁移完成！")

                # 构建成功消息
                tool_names = [config.tool_name for config in selected_configs]
                success_msg = f"成功迁移 {len(tool_names)} 个工具配置: {', '.join(tool_names)}"
                if backup_path:
                    success_msg += f"\n备份文件: {backup_path}"

                return {
                    "success": True,
                    "error": "",
                    "output": success_msg,
                    "backup_path": str(backup_path) if backup_path else ""
                }

            except Exception as write_exc:
                logger.error(f"Failed to write configurations: {write_exc}")

                # 尝试回滚
                if backup_path and backup_path.exists():
                    try:
                        progress_callback("写入失败，正在回滚...")
                        shutil.copy2(backup_path, target_path)
                        logger.info("Rollback completed")
                    except Exception as rollback_exc:
                        logger.error(f"Rollback failed: {rollback_exc}")

                return {
                    "success": False,
                    "error": f"Failed to write configurations: {write_exc}",
                    "output": "",
                    "backup_path": str(backup_path) if backup_path else ""
                }

        except Exception as exc:
            logger.error(f"Failed to migrate shell configurations: {exc}", exc_info=True)
            return {
                "success": False,
                "error": str(exc),
                "output": "",
                "backup_path": ""
            }

    def _prepare_migration_content(self, configs: List[ShellConfig], progress_callback) -> str:
        """
        准备迁移内容，包括头部注释和配置行。

        Args:
            configs: 要迁移的配置列表
            progress_callback: 进度回调函数

        Returns:
            str: 格式化的迁移内容
        """
        from datetime import datetime

        lines = []

        # 添加迁移标记头部
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines.append("# ================================================")
        lines.append(f"# Shell Configuration Migration - {timestamp}")
        lines.append("# 检测到的工具配置自动迁移")
        lines.append("# ================================================\n")

        # 按工具分组配置
        tool_groups = {}
        for config in configs:
            if config.tool_name not in tool_groups:
                tool_groups[config.tool_name] = {
                    "description": config.description,
                    "source_file": config.source_file,
                    "config_lines": []
                }
            tool_groups[config.tool_name]["config_lines"].extend(config.config_lines)

        # 为每个工具生成配置块
        for tool_name, tool_data in tool_groups.items():
            progress_callback(f"处理 {tool_name} 配置...")

            lines.append(f"# {tool_name} - {tool_data['description']}")
            lines.append(f"# 源文件: {tool_data['source_file']}")
            lines.append(f"# {tool_data['description']} 配置开始")

            for line in tool_data["config_lines"]:
                lines.append(line)

            lines.append(f"# {tool_name} 配置结束\n")

        # 添加迁移说明
        lines.append("# ================================================")
        lines.append("# 迁移说明:")
        lines.append("# 1. 以上配置已从原有 shell 配置文件自动检测并迁移")
        lines.append("# 2. 请检查配置是否在新的 Zsh 环境中正常工作")
        lines.append("# 3. 如有问题，可以从备份文件恢复原配置")
        lines.append("# 4. 建议重新启动终端或运行 'source ~/.zshrc' 使配置生效")
        lines.append("# ================================================\n")

        return '\n'.join(lines) + '\n'

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
            # 构造命令字符串，如果太长则简化显示
            cmd_str = ' '.join(cmd)
            if len(cmd_str) > 80:
                # 简化长命令的显示
                display_cmd = f"{cmd[0]} ..."
            else:
                display_cmd = cmd_str

            logger.debug(f"Running command: {cmd_str}")
            progress_callback(f"Executing: {display_cmd}")

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
                error_detail = f'Command failed with exit code {process.returncode}. Output: {output}' if output.strip() else f'Command failed with exit code {process.returncode}'
                return {
                    "success": False,
                    "error": error_detail,
                    "output": output,
                }

        except subprocess.TimeoutExpired:
            logger.error("Command timed out")
            process.kill()
            return {"success": False, "error": "Operation timed out", "output": ""}
        except Exception as exc:
            logger.error(f"Command execution failed: {exc}", exc_info=True)
            return {"success": False, "error": str(exc), "output": ""}
