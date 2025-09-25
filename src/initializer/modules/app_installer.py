"""Application installer module for managing predefined applications."""

import subprocess
import shutil
import asyncio
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from pathlib import Path
from ..utils.log_manager import InstallationLogManager, LogLevel
from ..utils.logger import get_module_logger
from .batch_package_checker import BatchPackageChecker
from .two_layer_checker import TwoLayerPackageChecker


@dataclass
class Application:
    """Represents an application that can be installed."""
    name: str
    package: str
    description: str
    post_install: Optional[str] = None
    installed: bool = False
    
    def get_package_list(self) -> List[str]:
        """Get list of packages from the package string."""
        return self.package.split()


class AppInstaller:
    """Manages installation and configuration of predefined applications."""
    
    def __init__(self, config_manager):
        """Initialize the application installer.

        Args:
            config_manager: Configuration manager instance
        """
        self.config_manager = config_manager
        # Load raw configuration directly
        modules_config = config_manager.load_config("modules")
        self.app_config = modules_config.get('modules', {}).get('app_install', {})

        # Initialize loggers first
        self.log_manager = InstallationLogManager(config_manager.config_dir)
        self.logger = get_module_logger("app_installer")

        # 先检测包管理器
        self.package_manager = self._detect_package_manager()

        # Initialize two-layer package checker for efficient status checking
        self.two_layer_checker = TwoLayerPackageChecker(self.package_manager or "unknown")

        # Keep batch checker for backward compatibility and fallback
        self.batch_checker = BatchPackageChecker(self.package_manager or "unknown")

        # 然后加载应用列表
        self.applications = self._load_applications()
    
    def _load_applications(self) -> List[Application]:
        """Load applications from package manager specific configuration file."""
        applications = []

        # 根据包管理器类型加载对应的配置文件
        if self.package_manager == "apt" or self.package_manager == "apt-get":
            config_file = "applications_apt.yaml"
        elif self.package_manager == "brew":
            config_file = "applications_homebrew.yaml"
        else:
            # 回退到原始配置方法
            app_list = self.app_config.get("applications", [])
            for app_data in app_list:
                app = Application(
                    name=app_data.get("name", ""),
                    package=app_data.get("package", ""),
                    description=app_data.get("description", ""),
                    post_install=app_data.get("post_install")
                )
                applications.append(app)
            return applications

        # 加载包管理器特定的配置文件
        try:
            import yaml
            config_path = self.config_manager.config_dir / config_file

            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f)

                app_list = config_data.get("applications", [])

                for app_data in app_list:
                    # 处理不同包管理器的包名字段
                    package_name = self._get_package_name_for_manager(app_data)

                    app = Application(
                        name=app_data.get("name", ""),
                        package=package_name,
                        description=app_data.get("description", ""),
                        post_install=app_data.get("post_install")
                    )
                    applications.append(app)
            else:
                # 如果特定配置文件不存在，回退到原始配置
                self.logger.warning(f"Package manager specific config {config_file} not found, falling back to modules.yaml")
                app_list = self.app_config.get("applications", [])
                for app_data in app_list:
                    app = Application(
                        name=app_data.get("name", ""),
                        package=app_data.get("package", ""),
                        description=app_data.get("description", ""),
                        post_install=app_data.get("post_install")
                    )
                    applications.append(app)

        except Exception as e:
            self.logger.error(f"Failed to load package manager specific config: {str(e)}")
            # 回退到原始配置
            app_list = self.app_config.get("applications", [])
            for app_data in app_list:
                app = Application(
                    name=app_data.get("name", ""),
                    package=app_data.get("package", ""),
                    description=app_data.get("description", ""),
                    post_install=app_data.get("post_install")
                )
                applications.append(app)

        return applications

    def _get_package_name_for_manager(self, app_data: dict) -> str:
        """Get package name based on package manager type.

        Args:
            app_data: Application data from configuration

        Returns:
            Package name string for the current package manager
        """
        if self.package_manager == "brew":
            # Homebrew 可能使用 formula 或 cask
            app_type = app_data.get("type", "formula")

            if app_type == "cask":
                return app_data.get("cask", "")
            elif app_type == "both":
                # 优先使用 cask（GUI 应用）
                return app_data.get("cask", app_data.get("formula", ""))
            else:
                # 默认使用 formula
                return app_data.get("formula", "")
        else:
            # APT 等使用标准 package 字段
            return app_data.get("package", "")

    def _detect_package_manager(self) -> Optional[str]:
        """Detect the system's package manager."""
        package_managers = {
            "apt": "apt-get",
            "apt-get": "apt-get",
            "yum": "yum",
            "dnf": "dnf",
            "pacman": "pacman",
            "zypper": "zypper",
            "apk": "apk"
        }

        for pm_name, pm_cmd in package_managers.items():
            if shutil.which(pm_cmd):
                return pm_name

        return None

    def analyze_error_and_suggest_solution(self, error_output: str, command: str, app_name: str) -> str:
        """Analyze error output and provide user-friendly solutions.

        Args:
            error_output: The error message from command execution
            command: The command that failed
            app_name: Name of the application being installed/uninstalled

        Returns:
            User-friendly error message with suggested solutions
        """
        error_lower = error_output.lower()

        # Common package manager error patterns and solutions
        error_patterns = {
            # Network/Download issues
            "network is unreachable": {
                "type": "网络问题",
                "message": "网络连接不可达",
                "solutions": [
                    "检查网络连接是否正常",
                    "尝试更换软件源镜像",
                    "检查防火墙设置"
                ]
            },
            "unable to fetch": {
                "type": "下载问题",
                "message": "无法下载软件包",
                "solutions": [
                    "检查网络连接",
                    "更新软件包列表 (apt update)",
                    "更换软件源镜像"
                ]
            },
            "404 not found": {
                "type": "软件包不存在",
                "message": "软件包未找到",
                "solutions": [
                    "检查软件包名称是否正确",
                    "更新软件包列表",
                    "启用所需的软件仓库"
                ]
            },

            # Permission issues
            "permission denied": {
                "type": "权限问题",
                "message": "权限不足",
                "solutions": [
                    "使用 sudo 运行命令",
                    "检查用户是否在 sudo 组中",
                    "检查文件/目录权限"
                ]
            },
            "operation not permitted": {
                "type": "权限问题",
                "message": "操作不被允许",
                "solutions": [
                    "使用管理员权限",
                    "检查 SELinux/AppArmor 设置",
                    "确认文件系统不是只读"
                ]
            },

            # Dependency issues
            "depends": {
                "type": "依赖问题",
                "message": "存在未满足的依赖关系",
                "solutions": [
                    "安装缺失的依赖包",
                    "运行 apt --fix-broken install",
                    "清理软件包缓存并重试"
                ]
            },
            "broken packages": {
                "type": "软件包损坏",
                "message": "软件包状态异常",
                "solutions": [
                    "运行 dpkg --configure -a",
                    "使用 apt --fix-broken install",
                    "清理并重新安装"
                ]
            },

            # Disk space issues
            "no space left": {
                "type": "磁盘空间",
                "message": "磁盘空间不足",
                "solutions": [
                    "清理系统垃圾文件",
                    "删除不需要的软件包",
                    "清理软件包缓存 (apt clean)"
                ]
            },

            # Lock issues
            "could not get lock": {
                "type": "包管理器锁定",
                "message": "包管理器被其他进程占用",
                "solutions": [
                    "等待其他包管理器进程完成",
                    "终止占用的进程",
                    "删除锁文件 (谨慎操作)"
                ]
            },

            # Repository issues
            "repository is not signed": {
                "type": "仓库签名问题",
                "message": "软件仓库未签名",
                "solutions": [
                    "导入 GPG 密钥",
                    "使用 --allow-unauthenticated 参数",
                    "验证仓库来源的安全性"
                ]
            },

            # Service issues
            "systemd": {
                "type": "系统服务问题",
                "message": "系统服务配置出错",
                "solutions": [
                    "检查服务状态 (systemctl status)",
                    "查看服务日志 (journalctl -u service)",
                    "重新加载 systemd 配置"
                ]
            }
        }

        # Find matching pattern
        for pattern, info in error_patterns.items():
            if pattern in error_lower:
                solution_text = "\n".join([f"  • {sol}" for sol in info["solutions"]])
                return f"""❌ {info['type']}: {info['message']}

📋 建议解决方案:
{solution_text}

🔍 原始错误: {error_output.strip()}"""

        # No specific pattern found, provide generic guidance
        if "sudo" in command and ("permission" in error_lower or "denied" in error_lower):
            return f"""❌ 权限问题: 执行命令需要管理员权限

📋 建议解决方案:
  • 确保当前用户在 sudo 组中
  • 尝试手动运行: sudo -v 验证权限
  • 检查 /etc/sudoers 配置

🔍 原始错误: {error_output.strip()}"""

        # Generic error with basic guidance
        return f"""❌ 安装失败: {app_name}

📋 建议调试步骤:
  • 检查网络连接是否正常
  • 更新软件包列表: sudo apt update
  • 检查磁盘空间是否充足
  • 查看完整的错误信息寻找具体原因

🔍 原始错误: {error_output.strip()}"""

    def check_dependencies(self, app: Application) -> Dict[str, Any]:
        """Check dependencies for an application before installation.

        Args:
            app: Application to check dependencies for

        Returns:
            Dictionary containing dependency information
        """
        if not self.package_manager:
            return {"success": False, "error": "包管理器未检测到"}

        packages = app.get_package_list()
        dependency_info = {
            "success": True,
            "packages": packages,
            "dependencies": [],
            "conflicts": [],
            "disk_space": "未知",
            "warnings": [],
            "recommendations": []
        }

        try:
            for package in packages:
                pkg_deps = self._get_package_dependencies(package)
                if pkg_deps:
                    dependency_info["dependencies"].extend(pkg_deps)

            # Remove duplicates
            dependency_info["dependencies"] = list(set(dependency_info["dependencies"]))

            # Check for potential conflicts
            conflicts = self._check_dependency_conflicts(packages)
            dependency_info["conflicts"] = conflicts

            # Estimate disk space requirements
            disk_space = self._estimate_disk_space(packages)
            dependency_info["disk_space"] = disk_space

            # Generate warnings and recommendations
            warnings, recommendations = self._analyze_dependencies(packages, dependency_info)
            dependency_info["warnings"] = warnings
            dependency_info["recommendations"] = recommendations

        except Exception as e:
            dependency_info["success"] = False
            dependency_info["error"] = f"依赖检查失败: {str(e)}"

        return dependency_info

    def _get_package_dependencies(self, package: str) -> List[str]:
        """Get dependencies for a specific package.

        Args:
            package: Package name to check

        Returns:
            List of dependency package names
        """
        dependencies = []

        try:
            if self.package_manager in ["apt", "apt-get"]:
                # Use apt-cache to get dependencies
                result = subprocess.run(
                    ["apt-cache", "depends", package],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        line = line.strip()
                        if line.startswith('Depends:'):
                            dep = line.split(':', 1)[1].strip()
                            # Remove version constraints and alternatives
                            dep = dep.split('(')[0].split('|')[0].strip()
                            if dep and dep != package:
                                dependencies.append(dep)

            elif self.package_manager in ["yum", "dnf"]:
                # Use yum/dnf to get dependencies
                cmd = "dnf" if self.package_manager == "dnf" else "yum"
                result = subprocess.run(
                    [cmd, "deplist", package],
                    capture_output=True,
                    text=True,
                    timeout=15
                )

                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        line = line.strip()
                        if 'dependency:' in line.lower():
                            parts = line.split()
                            if len(parts) >= 2:
                                dep = parts[1]
                                if dep and dep != package:
                                    dependencies.append(dep)

            elif self.package_manager == "pacman":
                # Use pacman to get dependencies
                result = subprocess.run(
                    ["pacman", "-Si", package],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        line = line.strip()
                        if line.startswith('Depends On'):
                            deps_str = line.split(':', 1)[1].strip()
                            if deps_str != 'None':
                                for dep in deps_str.split():
                                    dep = dep.split('>=')[0].split('=')[0].split('<')[0]
                                    if dep and dep != package:
                                        dependencies.append(dep)

        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            # If dependency checking fails, return empty list
            pass

        return dependencies[:10]  # Limit to first 10 dependencies to avoid overwhelming output

    def _check_dependency_conflicts(self, packages: List[str]) -> List[Dict[str, str]]:
        """Check for potential conflicts between packages.

        Args:
            packages: List of package names to check

        Returns:
            List of conflict information dictionaries
        """
        conflicts = []

        try:
            if self.package_manager in ["apt", "apt-get"]:
                for package in packages:
                    result = subprocess.run(
                        ["apt-cache", "show", package],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )

                    if result.returncode == 0:
                        for line in result.stdout.split('\n'):
                            line = line.strip()
                            if line.startswith('Conflicts:'):
                                conflicts_str = line.split(':', 1)[1].strip()
                                for conflict in conflicts_str.split(','):
                                    conflict = conflict.strip().split('(')[0].strip()
                                    if conflict:
                                        conflicts.append({
                                            "package": package,
                                            "conflicts_with": conflict,
                                            "type": "包冲突"
                                        })

        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            pass

        return conflicts[:5]  # Limit conflicts list

    def _estimate_disk_space(self, packages: List[str]) -> str:
        """Estimate disk space requirements for packages.

        Args:
            packages: List of package names

        Returns:
            Human-readable disk space estimate
        """
        try:
            if self.package_manager in ["apt", "apt-get"]:
                # Use apt-get with --dry-run to get size estimation
                result = subprocess.run(
                    ["apt-get", "install", "--dry-run", "-y"] + packages,
                    capture_output=True,
                    text=True,
                    timeout=15
                )

                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if 'need to get' in line.lower():
                            # Extract size information
                            import re
                            size_match = re.search(r'(\d+(?:\.\d+)?)\s*([kMG]?B)', line)
                            if size_match:
                                return f"约 {size_match.group(1)} {size_match.group(2)}"

            elif self.package_manager in ["yum", "dnf"]:
                cmd = "dnf" if self.package_manager == "dnf" else "yum"
                result = subprocess.run(
                    [cmd, "install", "--assumeno"] + packages,
                    capture_output=True,
                    text=True,
                    timeout=15
                )

                for line in result.stdout.split('\n'):
                    if 'total download size' in line.lower():
                        import re
                        size_match = re.search(r'(\d+(?:\.\d+)?)\s*([kMG]?B)', line)
                        if size_match:
                            return f"约 {size_match.group(1)} {size_match.group(2)}"

        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            pass

        return "未知"

    def _analyze_dependencies(self, packages: List[str], dependency_info: Dict) -> tuple:
        """Analyze dependencies and generate warnings/recommendations.

        Args:
            packages: List of package names
            dependency_info: Dependency information

        Returns:
            Tuple of (warnings, recommendations)
        """
        warnings = []
        recommendations = []

        # Check for large number of dependencies
        if len(dependency_info["dependencies"]) > 20:
            warnings.append("此软件包有大量依赖项，安装可能需要较长时间")

        # Check for conflicts
        if dependency_info["conflicts"]:
            warnings.append("检测到潜在的软件包冲突，请谨慎安装")

        # Check for system packages
        system_packages = ["libc6", "systemd", "kernel", "glibc", "bash"]
        risky_deps = [dep for dep in dependency_info["dependencies"]
                     if any(sys_pkg in dep.lower() for sys_pkg in system_packages)]

        if risky_deps:
            warnings.append("包含系统级依赖，建议谨慎操作")

        # Generate recommendations
        if dependency_info["dependencies"]:
            recommendations.append("建议在安装前更新包列表: sudo apt update")

        if any('dev' in pkg for pkg in packages):
            recommendations.append("检测到开发包，确保有足够的磁盘空间")

        if len(packages) > 1:
            recommendations.append("批量安装多个包，建议分批进行以便排查问题")

        return warnings, recommendations

    def check_application_status(self, app: Application) -> bool:
        """Check if an application is installed.
        
        Args:
            app: Application to check
            
        Returns:
            True if all packages are installed, False otherwise
        """
        if not self.package_manager:
            return False
        
        packages = app.get_package_list()
        
        for package in packages:
            if not self._is_package_installed(package):
                return False
        
        return True
    
    def _is_package_installed(self, package: str) -> bool:
        """Check if a specific package is installed.

        Args:
            package: Package name to check

        Returns:
            True if installed, False otherwise
        """
        if not self.package_manager:
            return False

        # 处理 Homebrew 特殊情况
        if self.package_manager == "brew":
            check_commands = [
                ["brew", "list", package],      # 检查 formula
                ["brew", "list", "--cask", package]  # 检查 cask
            ]

            # 尝试两种检查方式，任一成功即表示已安装
            for cmd in check_commands:
                try:
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    if result.returncode == 0:
                        return True
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    continue

            return False

        # 其他包管理器保持原有逻辑
        check_commands = {
            "apt": ["dpkg", "-l", package],
            "apt-get": ["dpkg", "-l", package],
            "yum": ["rpm", "-q", package],
            "dnf": ["rpm", "-q", package],
            "pacman": ["pacman", "-Q", package],
            "zypper": ["rpm", "-q", package],
            "apk": ["apk", "info", "-e", package]
        }

        cmd = check_commands.get(self.package_manager)
        if not cmd:
            return False

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def get_install_command(self, app: Application) -> Optional[str]:
        """Get the installation command for an application.

        Args:
            app: Application to install

        Returns:
            Installation command string or None
        """
        if not self.package_manager:
            return None

        packages = app.package

        # 处理 Homebrew 特殊情况
        if self.package_manager == "brew":
            # 尝试从配置文件获取应用类型信息
            app_type = self._get_app_type_from_config(app.name)

            if app_type == "cask":
                return f"brew install --cask {packages}"
            elif app_type == "both":
                # 默认使用 cask 安装（GUI 应用优先）
                return f"brew install --cask {packages}"
            else:
                # 默认使用 formula 安装
                return f"brew install {packages}"

        # 获取配置参数
        config = self._get_package_manager_config()
        auto_yes = config.get("auto_yes", True)
        install_recommends = config.get("install_recommends", True)
        install_suggests = config.get("install_suggests", False)

        # 构建 APT 命令参数
        if self.package_manager in ["apt", "apt-get"]:
            cmd_parts = ["sudo apt-get update && sudo apt-get install"]

            # 添加自动确认参数
            if auto_yes:
                cmd_parts.append("-y")

            # 添加推荐包参数
            if not install_recommends:
                cmd_parts.append("--no-install-recommends")

            # 添加建议包参数
            if install_suggests:
                cmd_parts.append("--install-suggests")
            elif not install_suggests:
                cmd_parts.append("--no-install-suggests")

            cmd_parts.append(packages)
            return " ".join(cmd_parts)

        # 其他包管理器保持原有逻辑
        install_commands = {
            "yum": f"sudo yum install {'-y' if auto_yes else ''} {packages}",
            "dnf": f"sudo dnf install {'-y' if auto_yes else ''} {packages}",
            "pacman": f"sudo pacman -S {'--noconfirm' if auto_yes else ''} {packages}",
            "zypper": f"sudo zypper install {'-y' if auto_yes else ''} {packages}",
            "apk": f"sudo apk add {packages}"  # apk 没有交互式确认
        }

        return install_commands.get(self.package_manager)

    def _get_package_manager_config(self) -> Dict[str, Any]:
        """Get package manager specific configuration parameters.

        Returns:
            Dictionary containing package manager configuration settings
        """
        try:
            # Try to load package manager specific config first
            config_file_map = {
                "apt": "applications_apt.yaml",
                "apt-get": "applications_apt.yaml",
                "brew": "applications_homebrew.yaml",
                "yum": "applications_yum.yaml",
                "dnf": "applications_dnf.yaml",
                "pacman": "applications_pacman.yaml",
                "zypper": "applications_zypper.yaml",
                "apk": "applications_apk.yaml"
            }

            config_file = config_file_map.get(self.package_manager)
            if config_file:
                config_path = self.config_manager.config_dir / config_file
                if config_path.exists():
                    import yaml
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config_data = yaml.safe_load(f)

                    # Return the package manager configuration section
                    if self.package_manager in ["apt", "apt-get"]:
                        return config_data.get('apt_config', {})
                    elif self.package_manager == "brew":
                        return config_data.get('brew_config', {})
                    else:
                        # For other package managers, use pm_config or default to apt_config structure
                        return config_data.get(f'{self.package_manager}_config',
                                             config_data.get('apt_config', {}))

            # Fallback to general app_install config
            return self.app_config.get('apt_config', {})

        except Exception as e:
            self.logger.warning(f"Failed to load package manager config: {str(e)}")
            # Return sensible defaults
            return {
                "auto_yes": True,
                "install_recommends": True,
                "install_suggests": False
            }

    def _get_apt_config(self) -> Dict[str, Any]:
        """Get APT-specific configuration parameters (legacy method).

        Returns:
            Dictionary containing APT configuration settings
        """
        # Use the new generic method for backwards compatibility
        return self._get_package_manager_config()

    def _get_app_type_from_config(self, app_name: str) -> str:
        """Get application type from configuration file for Homebrew.

        Args:
            app_name: Name of the application

        Returns:
            Application type ('formula', 'cask', 'both') or 'formula' as default
        """
        if self.package_manager != "brew":
            return "formula"

        try:
            import yaml
            config_path = self.config_manager.config_dir / "applications_homebrew.yaml"

            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f)

                app_list = config_data.get("applications", [])

                for app_data in app_list:
                    if app_data.get("name") == app_name:
                        return app_data.get("type", "formula")

        except Exception as e:
            self.logger.debug(f"Failed to get app type from config: {str(e)}")

        return "formula"  # 默认返回 formula
    def get_uninstall_command(self, app: Application) -> Optional[str]:
        """Get the uninstallation command for an application.

        Args:
            app: Application to uninstall

        Returns:
            Uninstallation command string or None
        """
        if not self.package_manager:
            return None

        packages = app.package

        # 处理 Homebrew 特殊情况
        if self.package_manager == "brew":
            # 对于 Homebrew，卸载命令统一使用 brew uninstall
            # 不论是 formula 还是 cask 都用相同的命令
            return f"brew uninstall {packages}"

        # 获取配置参数 (所有包管理器都需要)
        config = self._get_package_manager_config()
        auto_yes = config.get("auto_yes", True)

        # 其他包管理器，根据 auto_yes 配置添加确认参数
        uninstall_commands = {
            "apt": f"sudo apt-get remove {'-y' if auto_yes else ''} {packages}",
            "apt-get": f"sudo apt-get remove {'-y' if auto_yes else ''} {packages}",
            "yum": f"sudo yum remove {'-y' if auto_yes else ''} {packages}",
            "dnf": f"sudo dnf remove {'-y' if auto_yes else ''} {packages}",
            "pacman": f"sudo pacman -R {'--noconfirm' if auto_yes else ''} {packages}",
            "zypper": f"sudo zypper remove {'-y' if auto_yes else ''} {packages}",
            "apk": f"sudo apk del {packages}"  # apk 没有交互式确认
        }

        return uninstall_commands.get(self.package_manager)
    
    def get_post_install_command(self, app: Application) -> Optional[str]:
        """Get the post-installation command for an application.
        
        Args:
            app: Application that was installed
            
        Returns:
            Post-installation command string or None
        """
        return app.post_install
    
    def refresh_all_status(self) -> None:
        """Refresh the installation status of all applications using two-layer checking.

        Uses L2 (quick verification) + L3 (batch system check) for optimal performance.
        """
        self.logger.info("Starting two-layer status refresh for all applications")

        try:
            # Use asyncio to run the two-layer check
            import asyncio

            # Create event loop if one doesn't exist
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # Run two-layer check
            if loop.is_running():
                # If we're already in an async context, create a task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        lambda: loop.run_until_complete(self.two_layer_checker.check_applications(self.applications))
                    )
                    status_results = future.result()
            else:
                # Run the two-layer check in the event loop
                status_results = loop.run_until_complete(self.two_layer_checker.check_applications(self.applications))

            # Update application status based on two-layer check results
            for app in self.applications:
                app.installed = status_results.get(app.name, False)

            installed_count = sum(1 for app in self.applications if app.installed)
            self.logger.info(f"Two-layer status refresh completed: {installed_count}/{len(self.applications)} applications installed")

            # Log performance stats
            perf_stats = self.two_layer_checker.get_performance_stats()
            self.logger.info(f"Performance: L2 hit rate {perf_stats['l2_hit_rate_percent']}%, "
                           f"avg {perf_stats['average_time_per_check']}s per app")

        except Exception as e:
            self.logger.error(f"Two-layer status refresh failed: {str(e)}")
            # Fallback to batch-only checking
            self.logger.info("Falling back to batch-only status checks")
            self._fallback_batch_refresh()

    def _fallback_batch_refresh(self) -> None:
        """Fallback method using batch checking only."""
        try:
            import asyncio

            # Create event loop if one doesn't exist
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # Run batch check as fallback
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        lambda: loop.run_until_complete(self.batch_checker.batch_check_applications(self.applications))
                    )
                    status_results = future.result()
            else:
                status_results = loop.run_until_complete(self.batch_checker.batch_check_applications(self.applications))

            # Update application status
            for app in self.applications:
                app.installed = status_results.get(app.name, False)

            installed_count = sum(1 for app in self.applications if app.installed)
            self.logger.info(f"Batch fallback completed: {installed_count}/{len(self.applications)} applications installed")

        except Exception as e:
            self.logger.error(f"Batch fallback also failed: {str(e)}")
            # Final fallback to individual checks
            self._fallback_individual_refresh()

    def _fallback_individual_refresh(self) -> None:
        """Fallback method using individual status checks."""
        for app in self.applications:
            try:
                app.installed = self.check_application_status(app)
            except Exception as e:
                self.logger.warning(f"Individual status check failed for {app.name}: {str(e)}")
                app.installed = False
    
    def get_all_applications(self) -> List[Application]:
        """Get all configured applications with their current status.
        
        Returns:
            List of Application objects with updated status
        """
        self.refresh_all_status()
        return self.applications
    
    def execute_command(self, command: str) -> Tuple[bool, str]:
        """Execute a shell command.

        Args:
            command: Command to execute

        Returns:
            Tuple of (success, output/error message)
        """
        try:
            # Log the command being executed (for debugging)
            self.logger.debug(f"Executing command: {command}")

            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutes timeout
                env=None  # Inherit environment variables
            )

            if result.returncode == 0:
                # Success - return stdout or success message
                output = result.stdout.strip() if result.stdout.strip() else "命令执行成功"
                return True, output
            else:
                # Failure - return detailed error information
                error_msg = result.stderr.strip() if result.stderr.strip() else "命令执行失败"
                if result.returncode:
                    error_msg += f" (退出码: {result.returncode})"
                return False, error_msg

        except subprocess.TimeoutExpired:
            return False, "命令执行超时 (5分钟)，可能需要用户输入或命令卡住"
        except FileNotFoundError:
            return False, "命令或程序未找到，请检查命令是否正确"
        except PermissionError:
            return False, "权限不足，无法执行命令。可能需要 sudo 权限"
        except OSError as e:
            if e.errno == 8:  # Exec format error
                return False, "无法执行命令，文件格式错误"
            elif e.errno == 13:  # Permission denied
                return False, "权限不足，无法访问命令或文件"
            else:
                return False, f"系统错误: {str(e)}"
        except Exception as e:
            return False, f"执行错误: {str(e)}"

    def check_sudo_available(self) -> bool:
        """Check if sudo is available and user has permission to use it.

        Returns:
            True if sudo is available and usable, False otherwise
        """
        try:
            # Check if sudo command exists
            result = subprocess.run(
                ["which", "sudo"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0:
                return False

            # Check if user can use sudo (this will prompt for password if needed)
            result = subprocess.run(
                ["sudo", "-n", "true"],
                capture_output=True,
                text=True,
                timeout=5
            )

            return result.returncode == 0

        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            return False
    
    def install_application(self, app: Application) -> Tuple[bool, str]:
        """Install an application.

        Args:
            app: Application to install

        Returns:
            Tuple of (success, message)
        """
        self.logger.info(f"Starting installation of application: {app.name}")
        self.logger.debug(f"Application package: {app.package}")

        install_cmd = self.get_install_command(app)
        if not install_cmd:
            error_msg = "No package manager detected"
            self.logger.error(error_msg)
            return False, error_msg

        self.logger.debug(f"Using install command: {install_cmd}")

        success, output = self.execute_command(install_cmd)

        if success:
            self.logger.info(f"Successfully installed application: {app.name}")

            if app.post_install:
                self.logger.info(f"Executing post-install commands for: {app.name}")
                self.logger.debug(f"Post-install command: {app.post_install}")

                # Execute post-installation commands
                post_success, post_output = self.execute_command(app.post_install)
                if not post_success:
                    self.logger.warning(f"Post-install commands failed for {app.name}: {post_output}")
                    return True, f"Application installed but post-install failed: {post_output}"
                else:
                    self.logger.info(f"Post-install commands completed successfully for: {app.name}")
        else:
            self.logger.error(f"Failed to install application {app.name}: {output}")

        return success, output

    def uninstall_application(self, app: Application) -> Tuple[bool, str]:
        """Uninstall an application.

        Args:
            app: Application to uninstall

        Returns:
            Tuple of (success, message)
        """
        self.logger.info(f"Starting uninstallation of application: {app.name}")
        self.logger.debug(f"Application package: {app.package}")

        uninstall_cmd = self.get_uninstall_command(app)
        if not uninstall_cmd:
            error_msg = "No package manager detected"
            self.logger.error(error_msg)
            return False, error_msg

        self.logger.debug(f"Using uninstall command: {uninstall_cmd}")

        success, output = self.execute_command(uninstall_cmd)

        if success:
            self.logger.info(f"Successfully uninstalled application: {app.name}")
        else:
            self.logger.error(f"Failed to uninstall application {app.name}: {output}")

        return success, output

    # Log Management Methods

    def start_logging_session(self, system_info: Dict = None) -> str:
        """Start a new installation logging session.

        Args:
            system_info: System information dictionary

        Returns:
            Session ID
        """
        self.logger.info("Starting new installation logging session")
        self.logger.debug(f"Package manager: {self.package_manager or 'unknown'}")

        session_id = self.log_manager.start_session(
            package_manager=self.package_manager or "unknown",
            system_info=system_info
        )

        self.logger.info(f"Installation logging session started with ID: {session_id}")
        return session_id

    def end_logging_session(self) -> None:
        """End the current logging session."""
        self.logger.info("Ending installation logging session")
        self.log_manager.end_session()
        self.logger.debug("Installation logging session ended successfully")

    def log_installation_event(self, level: LogLevel, message: str,
                             application: str = None, action: str = None,
                             command: str = None, output: str = None,
                             error: str = None) -> None:
        """Log an installation event.

        Args:
            level: Log level (INFO, WARNING, ERROR, SUCCESS, DEBUG)
            message: Log message
            application: Application name
            action: Action performed (install/uninstall/retry)
            command: Command executed
            output: Command output
            error: Error message
        """
        self.logger.debug(f"Logging installation event: {level.value} - {message}")
        if application:
            self.logger.debug(f"Event for application: {application}")

        self.log_manager.log(
            level=level,
            message=message,
            command=command,
            output=output,
            error=error,
            application=application,
            action=action
        )

    def set_total_applications(self, count: int) -> None:
        """Set the total number of applications to be processed.

        Args:
            count: Total application count
        """
        self.logger.info(f"Setting total applications count: {count}")
        self.log_manager.set_total_apps(count)

    def export_installation_logs(self, session_id: str = None,
                                format: str = "json", output_file: str = None) -> str:
        """Export installation logs to a file.

        Args:
            session_id: Session ID to export (current session if None)
            format: Export format ('json', 'yaml', 'txt', 'html')
            output_file: Output file path (auto-generated if None)

        Returns:
            Path to exported file

        Raises:
            ValueError: If session not found or format not supported
        """
        return self.log_manager.export_logs(
            session_id=session_id,
            format=format,
            output_file=output_file
        )

    def list_log_sessions(self) -> List[Dict]:
        """List all available log sessions.

        Returns:
            List of session summary dictionaries containing:
            - session_id: Session identifier
            - start_time: Session start time
            - end_time: Session end time (if completed)
            - package_manager: Package manager used
            - total_apps: Total applications processed
            - successful_apps: Successfully processed applications
            - failed_apps: Failed applications
            - log_entries_count: Number of log entries
        """
        return self.log_manager.list_sessions()

    def cleanup_old_logs(self, keep_days: int = 30) -> int:
        """Clean up old log files.

        Args:
            keep_days: Number of days to keep logs (default: 30)

        Returns:
            Number of files deleted
        """
        return self.log_manager.cleanup_old_logs(keep_days)

    def get_log_export_formats(self) -> List[str]:
        """Get list of supported log export formats.

        Returns:
            List of supported format strings
        """
        return ["json", "yaml", "txt", "html"]