"""Package manager detection and source management module."""

import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import Optional, Dict, List, Tuple
from pathlib import Path
from datetime import datetime

from ..config_manager import ConfigManager
from ..utils.logger import get_module_logger


@dataclass
class PackageManager:
    """Package manager information."""
    name: str
    command: str
    current_source: Optional[str] = None
    available: bool = False
    installable: bool = False  # Whether this package manager can be installed
    description: Optional[str] = None  # Description of the package manager


class PackageManagerDetector:
    """Detect and manage system package managers."""
    
    # Define all known package managers with their install info
    PACKAGE_MANAGERS_INFO = {
        "apt": {
            "command": "apt-get",
            "description": "Debian/Ubuntu package manager",
            "installable": False,  # Usually pre-installed
        },
        "yum": {
            "command": "yum",
            "description": "RedHat/CentOS package manager",
            "installable": False,  # Usually pre-installed
        },
        "dnf": {
            "command": "dnf",
            "description": "Fedora package manager",
            "installable": False,  # Usually pre-installed
        },
        "brew": {
            "command": "brew",
            "description": "macOS/Linux package manager",
            "installable": True,  # Can be installed
            "install_script": '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"',
            "uninstall_script": '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/uninstall.sh)"',
        },
    }
    
    def __init__(self, config_manager: Optional[ConfigManager] = None):
        self.config_manager = config_manager or ConfigManager()
        self.logger = get_module_logger("package_manager")

        self.logger.info("Initializing package manager detector")
        self._mirror_sources = self._load_mirror_sources_from_config()
        self.all_package_managers = self._get_all_package_managers()
        self.package_managers = [pm for pm in self.all_package_managers if pm.available]

        self.logger.info(f"Detected {len(self.package_managers)} available package managers: "
                        f"{[pm.name for pm in self.package_managers]}")

    def _get_all_package_managers(self) -> List[PackageManager]:
        """Get all package managers (installed and installable)."""
        self.logger.debug("Scanning for package managers")
        managers = []

        for name, info in self.PACKAGE_MANAGERS_INFO.items():
            command = info["command"]
            is_available = shutil.which(command) is not None

            self.logger.debug(f"Checking package manager '{name}' (command: {command}): "
                            f"{'available' if is_available else 'not available'}")

            pm = PackageManager(
                name=name,
                command=command,
                available=is_available,
                installable=info.get("installable", False),
                description=info.get("description", ""),
                current_source=self._get_current_source(name) if is_available else None
            )
            managers.append(pm)

        return managers
    
    def _get_current_source(self, pm_name: str) -> Optional[str]:
        """Get the current source/mirror for a package manager."""
        try:
            if pm_name == "apt":
                sources_file = "/etc/apt/sources.list"
                if os.path.exists(sources_file):
                    with open(sources_file, 'r') as f:
                        for line in f:
                            if line.strip() and not line.startswith('#'):
                                # Extract the URL from the line
                                parts = line.split()
                                if len(parts) >= 2 and parts[0] == 'deb':
                                    return parts[1]
                                    
            elif pm_name == "yum":
                # Check CentOS repo files
                repo_dir = "/etc/yum.repos.d/"
                if os.path.exists(repo_dir):
                    for repo_file in Path(repo_dir).glob("*.repo"):
                        with open(repo_file, 'r') as f:
                            for line in f:
                                if line.startswith('baseurl='):
                                    return line.split('=', 1)[1].strip()
                                    
            elif pm_name == "dnf":
                # Similar to yum
                repo_dir = "/etc/yum.repos.d/"
                if os.path.exists(repo_dir):
                    for repo_file in Path(repo_dir).glob("*.repo"):
                        with open(repo_file, 'r') as f:
                            for line in f:
                                if line.startswith('baseurl='):
                                    return line.split('=', 1)[1].strip()

            elif pm_name == "brew":
                # Check Homebrew remote
                result = subprocess.run(
                    ["git", "-C", "/usr/local/Homebrew", "remote", "get-url", "origin"],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    return result.stdout.strip()
                                
        except Exception:
            pass
            
        return None
    
    def get_primary_package_manager(self) -> Optional[PackageManager]:
        """Get the primary package manager for the system."""
        # Priority order for primary package manager
        priority = ["apt", "yum", "dnf", "brew"]

        for pm_name in priority:
            for pm in self.package_managers:
                if pm.name == pm_name:
                    return pm

        # Return first available if none in priority list
        return self.package_managers[0] if self.package_managers else None
    
    def get_available_mirrors(self, pm_name: str) -> Dict[str, str]:
        """Get available mirror sources for a package manager."""
        return self._mirror_sources.get(pm_name, {})
    
    def _load_mirror_sources_from_config(self) -> Dict[str, Dict[str, str]]:
        """Load mirror sources from configuration file."""
        try:
            # Load the raw configuration directly
            modules_config = self.config_manager.load_config("modules")
            package_manager_config = modules_config.get('modules', {}).get('package_manager', {})
            mirrors_config = package_manager_config.get('mirrors', {})
            
            # Convert new format to old format for backward compatibility
            mirror_sources = {}
            
            for pm_name, pm_mirrors in mirrors_config.items():
                if isinstance(pm_mirrors, dict) and 'sources' in pm_mirrors:
                    # New format with sources list
                    mirror_sources[pm_name] = {}
                    for source in pm_mirrors['sources']:
                        key = source.get('key', source.get('name', '').lower())
                        url = source.get('url', '')
                        if key and url:
                            mirror_sources[pm_name][key] = url
                elif isinstance(pm_mirrors, list):
                    # Legacy format - convert to new format
                    mirror_sources[pm_name] = {}
                    for mirror in pm_mirrors:
                        if isinstance(mirror, dict) and 'name' in mirror and 'url' in mirror:
                            key = mirror['name'].lower().replace(' ', '_')
                            mirror_sources[pm_name][key] = mirror['url']
                            
            return mirror_sources
            
        except Exception as e:
            # Fallback to empty dict if config loading fails
            return {}
    
    def change_mirror(self, pm_name: str, mirror_url: str, backup_suffix: Optional[str] = None) -> Tuple[bool, str]:
        """Change the mirror source for a package manager.
        
        Args:
            pm_name: Package manager name
            mirror_url: New mirror URL
            backup_suffix: Optional backup suffix (if None, will generate timestamp)
        
        Returns:
            Tuple of (success, message)
        """
        if backup_suffix is None:
            backup_suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
            
        try:
            if pm_name == "apt":
                # Backup current sources.list
                sources_file = "/etc/apt/sources.list"
                backup_file = f"{sources_file}.bak_{backup_suffix}"
                
                if os.path.exists(sources_file):
                    shutil.copy2(sources_file, backup_file)
                
                # Write new sources.list
                # This is a simplified example - real implementation would need proper parsing
                with open(sources_file, 'w') as f:
                    # Detect distribution codename
                    codename = subprocess.run(
                        ["lsb_release", "-cs"],
                        capture_output=True,
                        text=True
                    ).stdout.strip()
                    
                    f.write(f"deb {mirror_url} {codename} main restricted universe multiverse\n")
                    f.write(f"deb {mirror_url} {codename}-updates main restricted universe multiverse\n")
                    f.write(f"deb {mirror_url} {codename}-backports main restricted universe multiverse\n")
                    f.write(f"deb {mirror_url} {codename}-security main restricted universe multiverse\n")
                
                # Update package index using apt instead of apt-get
                subprocess.run(["apt", "update"], check=True)
                return True, f"Successfully changed APT mirror to {mirror_url}"
                
            elif pm_name == "brew":
                # Change Homebrew repository remote
                brew_repo = "/usr/local/Homebrew"
                config_file = f"{brew_repo}/.git/config"
                backup_file = f"{config_file}.bak_{backup_suffix}"
                
                # Backup git config if it exists
                if os.path.exists(config_file):
                    shutil.copy2(config_file, backup_file)
                
                if os.path.exists(brew_repo):
                    subprocess.run(
                        ["git", "-C", brew_repo, "remote", "set-url", "origin", mirror_url],
                        check=True
                    )
                    return True, f"Successfully changed Homebrew mirror to {mirror_url}"
                else:
                    return False, "Homebrew repository not found"
                    
            # Add more package manager implementations as needed
            else:
                return False, f"Mirror change not implemented for {pm_name}"
                
        except Exception as e:
            return False, f"Failed to change mirror: {str(e)}"
    
    def get_install_command(self, pm_name: str) -> Optional[str]:
        """Get the installation command for a package manager.

        Args:
            pm_name: Package manager name

        Returns:
            Installation command string or None if not installable
        """
        info = self.PACKAGE_MANAGERS_INFO.get(pm_name, {})

        if not info.get("installable", False):
            return None

        # For brew, return the install script
        if pm_name == "brew":
            return info.get("install_script")

        return None
    
    def get_uninstall_command(self, pm_name: str) -> Optional[str]:
        """Get the uninstallation command for a package manager.

        Args:
            pm_name: Package manager name

        Returns:
            Uninstallation command string or None if not uninstallable
        """
        info = self.PACKAGE_MANAGERS_INFO.get(pm_name, {})

        # For brew, return the uninstall script
        if pm_name == "brew":
            return info.get("uninstall_script")

        return None
    
