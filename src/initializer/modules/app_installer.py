"""Application installer module for managing predefined applications."""

import subprocess
import shutil
import asyncio
import concurrent.futures
from typing import List, Dict, Optional, Tuple, Any, Union, Callable
from ..utils.log_manager import InstallationLogManager, LogLevel
from ..utils.logger import get_module_logger
from .batch_package_checker import BatchPackageChecker
from .two_layer_checker import TwoLayerPackageChecker
from .software_models import Application, ApplicationSuite
from .sudo_manager import SudoManager


class AppInstaller:
    """Manages installation and configuration of predefined applications."""
    
    def __init__(self, config_manager, sudo_manager: Optional[SudoManager] = None):
        """Initialize the application installer.

        Args:
            config_manager: Configuration manager instance
            sudo_manager: Optional SudoManager for handling sudo operations
        """
        self.config_manager = config_manager
        self.sudo_manager = sudo_manager  # 可选的sudo管理器
        # Load raw configuration directly
        modules_config = config_manager.load_config("modules")
        self.app_config = modules_config.get('modules', {}).get('app_install', {})

        # Initialize simplified log manager (UI callback will be set later)
        self.log_manager = InstallationLogManager()
        self.logger = get_module_logger("app_installer")

        # 先检测包管理器
        self.package_manager = self._detect_package_manager()

        # Initialize two-layer package checker for efficient status checking
        self.two_layer_checker = TwoLayerPackageChecker(self.package_manager or "unknown")

        # Keep batch checker for backward compatibility and fallback
        self.batch_checker = BatchPackageChecker(self.package_manager or "unknown")

        # 加载软件项（套件和独立应用）
        self.software_items: List[Union[ApplicationSuite, Application]] = self._load_software_items()

        # 兼容性：提供applications属性访问所有应用（展开套件组件）
        self.applications = self._get_all_applications_flat()

        # Session级别的apt update状态管理
        self._apt_update_executed = False  # 标记当前session是否已执行过apt update
    
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
                    post_install=app_data.get("post_install"),
                    executables=app_data.get("executables", [])
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
                        post_install=app_data.get("post_install"),
                        executables=app_data.get("executables", [])
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
                        post_install=app_data.get("post_install"),
                        executables=app_data.get("executables", [])
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
                    post_install=app_data.get("post_install"),
                    executables=app_data.get("executables", [])
                )
                applications.append(app)

        return applications

    def _load_software_items(self) -> List[Union[ApplicationSuite, Application]]:
        """Load software items from unified configuration format.

        Returns:
            List of software items (mix of ApplicationSuite and Application objects) in config order
        """
        software_items = []

        # 根据包管理器类型加载对应的配置文件
        if self.package_manager == "apt" or self.package_manager == "apt-get":
            config_file = "applications_apt.yaml"
        elif self.package_manager == "brew":
            config_file = "applications_homebrew.yaml"
        else:
            # 如果不是已知包管理器，回退到旧格式
            self.logger.warning(f"Unknown package manager {self.package_manager}, using legacy format")
            return self._load_applications_as_standalone()

        try:
            import yaml
            config_path = self.config_manager.config_dir / config_file

            if not config_path.exists():
                self.logger.warning(f"Config file {config_file} not found, using legacy format")
                return self._load_applications_as_standalone()

            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)

            # 读取统一的 applications 列表
            applications_list = config_data.get("applications", [])

            if not applications_list:
                self.logger.warning("No applications found in config, using legacy format")
                return self._load_applications_as_standalone()

            # 按配置顺序处理每个应用项
            suite_count = 0
            standalone_count = 0

            for app_data in applications_list:
                app_type = app_data.get("type", "standalone")

                if app_type == "suite":
                    # 创建套件
                    suite = self._create_suite_from_config(app_data)
                    software_items.append(suite)
                    suite_count += 1
                elif app_type == "standalone":
                    # 创建独立应用
                    app = self._create_application_from_config(app_data, app_type="standalone")
                    software_items.append(app)
                    standalone_count += 1
                else:
                    self.logger.warning(f"Unknown application type '{app_type}' for {app_data.get('name', 'unnamed')}")

            self.logger.info(f"Loaded {len(software_items)} software items in config order "
                           f"({suite_count} suites, {standalone_count} standalone)")

            return software_items

        except Exception as e:
            self.logger.error(f"Failed to load software items from {config_file}: {str(e)}")
            self.logger.warning("Falling back to legacy application loading")
            return self._load_applications_as_standalone()

    def _create_suite_from_config(self, suite_data: dict) -> ApplicationSuite:
        """Create an ApplicationSuite from configuration data.

        Args:
            suite_data: Suite configuration data

        Returns:
            ApplicationSuite instance
        """
        components = []
        for component_data in suite_data.get("components", []):
            component = self._create_application_from_config(component_data, app_type="component")
            components.append(component)

        suite = ApplicationSuite(
            name=suite_data.get("name", ""),
            description=suite_data.get("description", ""),
            category=suite_data.get("category", ""),
            components=components
        )

        return suite

    def _create_application_from_config(self, app_data: dict, app_type: str = "standalone") -> Application:
        """Create an Application from configuration data.

        Args:
            app_data: Application configuration data
            app_type: Type of application ('standalone' or 'component')

        Returns:
            Application instance
        """
        # 处理不同包管理器的包名字段
        package_name = self._get_package_name_for_manager(app_data)

        app = Application(
            name=app_data.get("name", ""),
            package=package_name,
            executables=app_data.get("executables", []),
            description=app_data.get("description", ""),
            category=app_data.get("category", ""),
            post_install=app_data.get("post_install", ""),
            tags=app_data.get("tags", []),
            recommended=app_data.get("recommended", False),
            type=app_type
        )

        return app

    def _load_applications_as_standalone(self) -> List[Application]:
        """Load legacy applications as standalone items for backward compatibility.

        Returns:
            List of Application objects (all as standalone)
        """
        applications = self._load_applications()
        # 确保所有应用都标记为 standalone 类型
        for app in applications:
            app.type = "standalone"
        return applications

    def _get_all_applications_flat(self) -> List[Application]:
        """Get all applications in a flat list (expand suite components).

        Returns:
            Flat list of all applications (components + standalone)
        """
        all_applications = []

        for item in self.software_items:
            if isinstance(item, ApplicationSuite):
                # 添加套件的所有组件
                all_applications.extend(item.components)
            else:
                # 添加独立应用
                all_applications.append(item)

        return all_applications

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
                "type": "Network Issue",
                "message": "Network unreachable",
                "solutions": [
                    "Check network connection",
                    "Try changing software source mirror",
                    "Check firewall settings"
                ]
            },
            "unable to fetch": {
                "type": "Download Issue",
                "message": "Unable to download package",
                "solutions": [
                    "Check network connection",
                    "Update package list (apt update)",
                    "Change software source mirror"
                ]
            },
            "404 not found": {
                "type": "Package Not Found",
                "message": "Package not found",
                "solutions": [
                    "Verify package name is correct",
                    "Update package list",
                    "Enable required repositories"
                ]
            },

            # Permission issues
            "permission denied": {
                "type": "Permission Issue",
                "message": "Insufficient permissions",
                "solutions": [
                    "Run command with sudo",
                    "Check if user is in sudo group",
                    "Check file/directory permissions"
                ]
            },
            "operation not permitted": {
                "type": "Permission Issue",
                "message": "Operation not permitted",
                "solutions": [
                    "Use administrator privileges",
                    "Check SELinux/AppArmor settings",
                    "Verify filesystem is not read-only"
                ]
            },

            # Dependency issues
            "depends": {
                "type": "Dependency Issue",
                "message": "Unmet dependencies",
                "solutions": [
                    "Install missing dependency packages",
                    "Run apt --fix-broken install",
                    "Clear package cache and retry"
                ]
            },
            "broken packages": {
                "type": "Broken Package",
                "message": "Package in broken state",
                "solutions": [
                    "Run dpkg --configure -a",
                    "Use apt --fix-broken install",
                    "Clean and reinstall"
                ]
            },

            # Disk space issues
            "no space left": {
                "type": "Disk Space",
                "message": "Insufficient disk space",
                "solutions": [
                    "Clean system temporary files",
                    "Remove unnecessary packages",
                    "Clear package cache (apt clean)"
                ]
            },

            # Lock issues
            "could not get lock": {
                "type": "Package Manager Locked",
                "message": "Package manager in use by another process",
                "solutions": [
                    "Wait for other package manager processes to complete",
                    "Terminate blocking process",
                    "Remove lock file (use with caution)"
                ]
            },

            # Repository issues
            "repository is not signed": {
                "type": "Repository Signature Issue",
                "message": "Software repository not signed",
                "solutions": [
                    "Import GPG key",
                    "Use --allow-unauthenticated parameter",
                    "Verify repository source security"
                ]
            },

            # Service issues
            "systemd": {
                "type": "System Service Issue",
                "message": "System service configuration error",
                "solutions": [
                    "Check service status (systemctl status)",
                    "View service logs (journalctl -u service)",
                    "Reload systemd configuration"
                ]
            }
        }

        # Find matching pattern
        for pattern, info in error_patterns.items():
            if pattern in error_lower:
                solution_text = "\n".join([f"  • {sol}" for sol in info["solutions"]])
                return f"""❌ {info['type']}: {info['message']}

📋 Suggested Solutions:
{solution_text}

🔍 Original Error: {error_output.strip()}"""

        # No specific pattern found, provide generic guidance
        if "sudo" in command and ("permission" in error_lower or "denied" in error_lower):
            return f"""❌ Permission Issue: Command requires administrator privileges

📋 Suggested Solutions:
  • Ensure current user is in sudo group
  • Try running manually: sudo -v to verify permissions
  • Check /etc/sudoers configuration

🔍 Original Error: {error_output.strip()}"""

        # Generic error with basic guidance
        return f"""❌ Installation Failed: {app_name}

📋 Debugging Steps:
  • Check network connection
  • Update package list: sudo apt update
  • Check available disk space
  • Review full error message for specific cause

🔍 Original Error: {error_output.strip()}"""

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
            cmd_parts = ["sudo apt-get install"]

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

    def needs_apt_update(self) -> bool:
        """检查是否需要执行apt update。

        Returns:
            True如果需要执行apt update，False如果已执行过或不需要
        """
        if self.package_manager not in ["apt", "apt-get"]:
            return False

        return not self._apt_update_executed

    def get_apt_update_command(self) -> Optional[str]:
        """获取apt update命令。

        Returns:
            apt update命令字符串，如果不需要则返回None
        """
        if not self.needs_apt_update():
            return None

        return "sudo apt-get update"

    def mark_apt_update_executed(self) -> None:
        """标记apt update已执行，避免重复执行。"""
        self._apt_update_executed = True
        self.logger.info("APT update marked as executed for current session")

    def reset_apt_update_status(self) -> None:
        """重置apt update状态，允许在新session中重新执行。"""
        self._apt_update_executed = False
        self.logger.info("APT update status reset for new session")

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
        """Refresh the installation status of all software items using two-layer checking.

        Uses L2 (quick verification) + L3 (batch system check) for optimal performance.
        Supports both suites and standalone applications.
        """
        self.logger.info("Starting two-layer status refresh for all software items")

        try:
            # Use asyncio to run the two-layer check
            import asyncio
            import concurrent.futures

            # Check if we're already in an async context
            try:
                current_loop = asyncio.get_running_loop()
                # We're in an async context, use thread to run the async function
                self.logger.debug("Running in async context, using ThreadPoolExecutor")

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    # Create a new event loop in the thread
                    def run_check():
                        # Create new event loop for this thread
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        try:
                            return new_loop.run_until_complete(
                                self.two_layer_checker.check_software_items(self.software_items)
                            )
                        finally:
                            new_loop.close()

                    status_results = executor.submit(run_check).result()

            except RuntimeError:
                # No event loop running, we can create one
                self.logger.debug("No event loop running, creating new one")
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    status_results = loop.run_until_complete(
                        self.two_layer_checker.check_software_items(self.software_items)
                    )
                finally:
                    loop.close()

            # Update self.applications for backward compatibility
            # The software items are already updated by check_software_items
            self.applications = self._get_all_applications_flat()

            # Log summary
            suite_count = sum(1 for item in self.software_items if isinstance(item, ApplicationSuite))
            standalone_count = sum(1 for item in self.software_items if isinstance(item, Application))
            installed_apps = sum(1 for app in self.applications if app.installed)

            self.logger.info(f"Status refresh completed: {len(self.software_items)} items "
                           f"({suite_count} suites, {standalone_count} standalone), "
                           f"{installed_apps}/{len(self.applications)} applications installed")

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
            import concurrent.futures

            # Check if we're already in an async context
            try:
                current_loop = asyncio.get_running_loop()
                # We're in an async context, use thread to run the async function
                self.logger.debug("Fallback: Running in async context, using ThreadPoolExecutor")

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    # Create a new event loop in the thread
                    def run_batch_check():
                        # Create new event loop for this thread
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        try:
                            return new_loop.run_until_complete(
                                self.batch_checker.batch_check_applications(self.applications)
                            )
                        finally:
                            new_loop.close()

                    status_results = executor.submit(run_batch_check).result()

            except RuntimeError:
                # No event loop running, we can create one
                self.logger.debug("Fallback: No event loop running, creating new one")
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    status_results = loop.run_until_complete(
                        self.batch_checker.batch_check_applications(self.applications)
                    )
                finally:
                    loop.close()

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

    def get_all_software_items(self) -> List[Union[ApplicationSuite, Application]]:
        """Get all configured software items (suites and standalone applications) with current status.

        Returns:
            List of software items (mix of ApplicationSuite and Application objects)
        """
        self.refresh_all_status()
        return self.software_items

    def get_software_items_for_display(self, expanded_suites: set = None) -> List[Union[ApplicationSuite, Application]]:
        """Get software items formatted for UI display with expansion state.

        Args:
            expanded_suites: Set of suite names that should be expanded

        Returns:
            List of software items with expansion state applied
        """
        expanded_suites = expanded_suites or set()

        # Update expansion state based on provided set
        for item in self.software_items:
            if isinstance(item, ApplicationSuite):
                item.expanded = item.name in expanded_suites

        # Refresh status
        self.refresh_all_status()

        return self.software_items

    def toggle_suite_expansion(self, suite_name: str) -> bool:
        """Toggle the expansion state of a suite.

        Args:
            suite_name: Name of the suite to toggle

        Returns:
            New expansion state (True if expanded, False if collapsed)
        """
        for item in self.software_items:
            if isinstance(item, ApplicationSuite) and item.name == suite_name:
                item.expanded = not item.expanded
                self.logger.debug(f"Suite '{suite_name}' {'expanded' if item.expanded else 'collapsed'}")
                return item.expanded

        self.logger.warning(f"Suite '{suite_name}' not found")
        return False

    def get_flat_display_items(self) -> List[Union[ApplicationSuite, Application]]:
        """Get flattened list of items for display (expanded suites show components).

        Returns:
            Flattened list where expanded suites are followed by their components
        """
        display_items = []

        for item in self.software_items:
            display_items.append(item)

            # If it's an expanded suite, add its components
            if isinstance(item, ApplicationSuite) and item.expanded:
                display_items.extend(item.components)

        return display_items
    
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

    def set_sudo_manager(self, sudo_manager: SudoManager) -> None:
        """设置sudo管理器.

        Args:
            sudo_manager: SudoManager实例
        """
        self.sudo_manager = sudo_manager
        self.logger.info("已设置sudo管理器")

    def execute_command_with_sudo_support(self, command: str) -> Tuple[bool, str]:
        """使用sudo支持执行命令（同步版本）.

        Args:
            command: 要执行的命令

        Returns:
            (成功状态, 输出信息或错误信息)
        """
        # 检查是否有sudo管理器且命令需要sudo
        if self.sudo_manager and self.sudo_manager.is_sudo_required(command):
            if not self.sudo_manager.is_verified():
                return False, "sudo权限未验证，请先进行权限验证"

            # 使用sudo管理器执行命令
            return self.sudo_manager.execute_with_sudo(command)
        else:
            # 使用原有的执行方法
            return self.execute_command(command)

    def install_application_with_sudo_support(self, app: Application) -> Tuple[bool, str]:
        """使用sudo支持安装应用程序.

        Args:
            app: 要安装的应用程序

        Returns:
            (成功状态, 消息)
        """
        self.logger.info(f"开始使用sudo支持安装应用程序: {app.name}")
        self.logger.debug(f"应用程序包: {app.package}")

        install_cmd = self.get_install_command(app)
        if not install_cmd:
            error_msg = "未检测到包管理器"
            self.logger.error(error_msg)
            return False, error_msg

        self.logger.debug(f"使用安装命令: {install_cmd}")

        # Log the installation attempt
        self.log_installation_event(
            LogLevel.INFO,
            f"Starting installation of {app.name}",
            application=app.name,
            action="install",
            command=install_cmd
        )

        # 使用sudo支持执行命令
        success, output = self.execute_command_with_sudo_support(install_cmd)

        if success:
            self.logger.info(f"成功安装应用程序: {app.name}")

            # Log successful installation with command output
            self.log_installation_event(
                LogLevel.SUCCESS,
                f"{app.name} installed successfully",
                application=app.name,
                action="install",
                command=install_cmd,
                output=output
            )

            if app.post_install:
                self.logger.info(f"Executing post-install command: {app.name}")
                self.logger.debug(f"Post-install command: {app.post_install}")

                # Execute post-install command
                post_success, post_output = self.execute_command_with_sudo_support(app.post_install)
                if not post_success:
                    self.logger.warning(f"{app.name} post-install command failed: {post_output}")

                    # Log post-install failure
                    self.log_installation_event(
                        LogLevel.WARNING,
                        f"{app.name} post-install command failed",
                        application=app.name,
                        action="post_install",
                        command=app.post_install,
                        error=post_output
                    )

                    return True, f"Application installed successfully, but post-install configuration failed: {post_output}"
                else:
                    self.logger.info(f"{app.name} post-install command executed successfully")

                    # Log successful post-install
                    self.log_installation_event(
                        LogLevel.SUCCESS,
                        f"{app.name} post-install command completed",
                        application=app.name,
                        action="post_install",
                        command=app.post_install,
                        output=post_output
                    )
        else:
            self.logger.error(f"Application {app.name} installation failed: {output}")

            # Log installation failure with command output and error
            self.log_installation_event(
                LogLevel.ERROR,
                f"{app.name} installation failed",
                application=app.name,
                action="install",
                command=install_cmd,
                error=output
            )

        return success, output

    def uninstall_application_with_sudo_support(self, app: Application) -> Tuple[bool, str]:
        """使用sudo支持卸载应用程序.

        Args:
            app: 要卸载的应用程序

        Returns:
            (成功状态, 消息)
        """
        self.logger.info(f"开始使用sudo支持卸载应用程序: {app.name}")
        self.logger.debug(f"应用程序包: {app.package}")

        uninstall_cmd = self.get_uninstall_command(app)
        if not uninstall_cmd:
            error_msg = "未检测到包管理器"
            self.logger.error(error_msg)
            return False, error_msg

        self.logger.debug(f"使用卸载命令: {uninstall_cmd}")

        # 使用sudo支持执行命令
        success, output = self.execute_command_with_sudo_support(uninstall_cmd)

        if success:
            self.logger.info(f"成功卸载应用程序: {app.name}")
        else:
            self.logger.error(f"应用程序 {app.name} 卸载失败: {output}")

        return success, output

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

    def start_logging_session(self) -> str:
        """Start a new installation logging session.

        Returns:
            Session ID
        """
        self.logger.info("Starting new installation logging session")
        self.logger.debug(f"Package manager: {self.package_manager or 'unknown'}")

        session_id = self.log_manager.start_session(
            package_manager=self.package_manager or "unknown"
        )

        self.logger.info(f"Installation logging session started with ID: {session_id}")
        return session_id

    def set_log_ui_callback(self, callback: Callable[[str, str], None]) -> None:
        """Set the UI callback for displaying logs.

        Args:
            callback: Function that takes (message, log_type) and displays in UI
        """
        self.log_manager.set_ui_callback(callback)

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

    # Deprecated methods - removed for simplification
    # Log export, cleanup and listing features removed as logs are now UI-only
    # def export_installation_logs() - no longer needed
    # def list_log_sessions() - no longer needed
    # def cleanup_old_logs() - no longer needed
    # def get_log_export_formats() - no longer needed

    def save_installation_status(self, app_name: str, installed: bool) -> bool:
        """Save installation status for an application.

        Args:
            app_name: Name of the application
            installed: Installation status (True if installed, False if uninstalled)

        Returns:
            True if status was saved successfully, False otherwise
        """
        try:
            self.logger.debug(f"Saving installation status for {app_name}: {installed}")

            # Find the application and update its status
            updated = False
            for app in self.applications:
                if app.name == app_name:
                    app.installed = installed
                    updated = True
                    self.logger.debug(f"Updated application {app_name} status to {installed}")
                    break

            # Also update in software_items if it's in a suite
            for item in self.software_items:
                if isinstance(item, ApplicationSuite):
                    for component in item.components:
                        if component.name == app_name:
                            component.installed = installed
                            updated = True
                            self.logger.debug(f"Updated suite component {app_name} status to {installed}")
                            break

            if not updated:
                self.logger.warning(f"Application {app_name} not found in current configuration")
                return False

            # Log the status change as an installation event
            action = "install" if installed else "uninstall"
            status = "completed" if installed else "removed"
            self.log_installation_event(
                LogLevel.INFO,
                f"Application {app_name} {status}",
                application=app_name,
                action=f"status_{action}"
            )

            return True

        except Exception as e:
            self.logger.error(f"Failed to save installation status for {app_name}: {str(e)}")
            return False