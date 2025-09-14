"""Application installer module for managing predefined applications."""

import subprocess
import shutil
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


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
        self.applications = self._load_applications()
        self.package_manager = self._detect_package_manager()
    
    def _load_applications(self) -> List[Application]:
        """Load applications from configuration."""
        applications = []
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
        
        install_commands = {
            "apt": f"sudo apt-get update && sudo apt-get install -y {packages}",
            "apt-get": f"sudo apt-get update && sudo apt-get install -y {packages}",
            "yum": f"sudo yum install -y {packages}",
            "dnf": f"sudo dnf install -y {packages}",
            "pacman": f"sudo pacman -S --noconfirm {packages}",
            "zypper": f"sudo zypper install -y {packages}",
            "apk": f"sudo apk add {packages}"
        }
        
        return install_commands.get(self.package_manager)
    
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
        
        uninstall_commands = {
            "apt": f"sudo apt-get remove -y {packages}",
            "apt-get": f"sudo apt-get remove -y {packages}",
            "yum": f"sudo yum remove -y {packages}",
            "dnf": f"sudo dnf remove -y {packages}",
            "pacman": f"sudo pacman -R --noconfirm {packages}",
            "zypper": f"sudo zypper remove -y {packages}",
            "apk": f"sudo apk del {packages}"
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
        """Refresh the installation status of all applications."""
        for app in self.applications:
            app.installed = self.check_application_status(app)
    
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
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )
            
            if result.returncode == 0:
                return True, result.stdout
            else:
                return False, result.stderr or f"Command failed with exit code {result.returncode}"
        
        except subprocess.TimeoutExpired:
            return False, "Command timed out after 5 minutes"
        except Exception as e:
            return False, str(e)
    
    def install_application(self, app: Application) -> Tuple[bool, str]:
        """Install an application.
        
        Args:
            app: Application to install
            
        Returns:
            Tuple of (success, message)
        """
        install_cmd = self.get_install_command(app)
        if not install_cmd:
            return False, "No package manager detected"
        
        success, output = self.execute_command(install_cmd)
        
        if success and app.post_install:
            # Execute post-installation commands
            post_success, post_output = self.execute_command(app.post_install)
            if not post_success:
                return True, f"Application installed but post-install failed: {post_output}"
        
        return success, output
    
    def uninstall_application(self, app: Application) -> Tuple[bool, str]:
        """Uninstall an application.
        
        Args:
            app: Application to uninstall
            
        Returns:
            Tuple of (success, message)
        """
        uninstall_cmd = self.get_uninstall_command(app)
        if not uninstall_cmd:
            return False, "No package manager detected"
        
        return self.execute_command(uninstall_cmd)