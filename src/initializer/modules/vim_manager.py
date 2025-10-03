"""NeoVim and LazyVim management module."""

import os
import subprocess
import asyncio
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Callable
from pathlib import Path
from datetime import datetime
import re

from ..utils.logger import get_module_logger


@dataclass
class NeoVimInfo:
    """NeoVim installation information."""
    installed: bool
    version: Optional[str] = None
    path: Optional[str] = None
    repo_version: Optional[str] = None
    meets_requirement: bool = False  # >= 0.9.0


@dataclass
class LazyVimInfo:
    """LazyVim installation information."""
    installed: bool
    config_path: Optional[str] = None
    has_lazy_lua: bool = False


class VimManager:
    """NeoVim and LazyVim management."""

    MIN_NVIM_VERSION = "0.9.0"
    LAZYVIM_REPO_URL = "https://github.com/LazyVim/starter.git"

    def __init__(self):
        self.logger = get_module_logger("vim_manager")
        self.logger.info("Initializing Vim manager")

    @staticmethod
    async def detect_neovim() -> NeoVimInfo:
        """
        Detect NeoVim installation status and version.

        Returns:
            NeoVimInfo object with installation details
        """
        logger = get_module_logger("vim_manager")
        logger.debug("Detecting NeoVim installation")

        # Check if nvim is installed
        nvim_path = subprocess.run(
            ["which", "nvim"],
            capture_output=True,
            text=True
        )

        if nvim_path.returncode != 0:
            logger.info("NeoVim not installed")
            return NeoVimInfo(installed=False)

        path = nvim_path.stdout.strip()
        logger.debug(f"NeoVim found at: {path}")

        # Get NeoVim version
        version_output = subprocess.run(
            ["nvim", "--version"],
            capture_output=True,
            text=True
        )

        version = None
        if version_output.returncode == 0:
            # Extract version from output like "NVIM v0.9.5"
            match = re.search(r'v(\d+\.\d+\.\d+)', version_output.stdout)
            if match:
                version = match.group(1)
                logger.debug(f"NeoVim version: {version}")

        # Check version compatibility
        meets_requirement = False
        if version:
            meets_requirement = VimManager._compare_versions(
                version,
                VimManager.MIN_NVIM_VERSION
            ) >= 0

        logger.info(f"NeoVim detection complete: version={version}, "
                   f"meets_requirement={meets_requirement}")

        return NeoVimInfo(
            installed=True,
            version=version,
            path=path,
            meets_requirement=meets_requirement
        )

    @staticmethod
    async def detect_lazyvim() -> LazyVimInfo:
        """
        Detect LazyVim installation status.

        Returns:
            LazyVimInfo object with installation details
        """
        logger = get_module_logger("vim_manager")
        logger.debug("Detecting LazyVim installation")

        config_path = Path.home() / ".config" / "nvim"
        lazy_lua_path = config_path / "lua" / "config" / "lazy.lua"

        installed = config_path.exists()
        has_lazy_lua = lazy_lua_path.exists()

        logger.info(f"LazyVim detection complete: installed={installed}, "
                   f"has_lazy_lua={has_lazy_lua}")

        return LazyVimInfo(
            installed=installed and has_lazy_lua,
            config_path=str(config_path) if config_path.exists() else None,
            has_lazy_lua=has_lazy_lua
        )

    @staticmethod
    async def check_dependencies() -> Dict[str, bool]:
        """
        Check required dependencies for LazyVim installation.

        Returns:
            Dictionary with dependency status
        """
        logger = get_module_logger("vim_manager")
        logger.debug("Checking dependencies")

        # Check Git
        git_result = subprocess.run(
            ["which", "git"],
            capture_output=True,
            text=True
        )
        git_available = git_result.returncode == 0

        # Check network connectivity to GitHub
        network_available = False
        try:
            network_result = subprocess.run(
                ["curl", "-Is", "https://github.com"],
                capture_output=True,
                text=True,
                timeout=5
            )
            network_available = network_result.returncode == 0
        except subprocess.TimeoutExpired:
            logger.warning("Network check timed out")
        except Exception as e:
            logger.warning(f"Network check failed: {e}")

        logger.info(f"Dependencies check: git={git_available}, "
                   f"network={network_available}")

        return {
            "git": git_available,
            "network": network_available
        }

    @staticmethod
    async def install_neovim(
        package_manager: str,
        progress_callback: Optional[Callable[[str, str], None]] = None
    ) -> Dict[str, any]:
        """
        Install NeoVim via system package manager.

        Args:
            package_manager: "apt", "yum", or "dnf"
            progress_callback: Function(level, message) to report progress

        Returns:
            {
                "success": bool,
                "version": str,
                "message": str,
                "logs": List[str]
            }
        """
        logger = get_module_logger("vim_manager")
        logger.info(f"Installing NeoVim via {package_manager}")

        logs = []

        def log(level: str | int, message: str) -> None:
            """Helper to log and report progress with safe level handling."""
            if isinstance(level, str):
                numeric_level = getattr(logging, level.upper(), logging.INFO)
                level_label = level.upper()
                callback_level = level
            else:
                numeric_level = level
                level_label = logging.getLevelName(level).upper()
                callback_level = level_label.lower()

            logger.log(numeric_level, message)
            logs.append(f"[{level_label}] {message}")
            if progress_callback:
                progress_callback(callback_level, message)

        try:
            # Step 1: Check repository version
            log("info", "Checking NeoVim version in repository...")

            repo_version = None
            if package_manager == "apt":
                result = subprocess.run(
                    ["apt-cache", "policy", "neovim"],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    # Extract version from apt-cache output
                    match = re.search(r'Candidate:\s+(\d+\.\d+)', result.stdout)
                    if match:
                        repo_version = match.group(1) + ".0"  # Assume patch version 0

            elif package_manager in ["yum", "dnf"]:
                result = subprocess.run(
                    [package_manager, "info", "neovim"],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    match = re.search(r'Version\s+:\s+(\d+\.\d+)', result.stdout)
                    if match:
                        repo_version = match.group(1) + ".0"

            if repo_version:
                log("info", f"Repository version: {repo_version}")

                # Step 2: Verify version >= 0.9.0
                if VimManager._compare_versions(repo_version, VimManager.MIN_NVIM_VERSION) < 0:
                    log("error", f"NeoVim version {repo_version} is too old. "
                                f"LazyVim requires >= {VimManager.MIN_NVIM_VERSION}")
                    log("info", "Please upgrade manually: https://github.com/neovim/neovim/releases")
                    return {
                        "success": False,
                        "version": repo_version,
                        "message": f"Version {repo_version} too old, requires >= {VimManager.MIN_NVIM_VERSION}",
                        "logs": logs
                    }
            else:
                log("warning", "Could not detect repository version, proceeding anyway")

            # Step 3: Install NeoVim
            log("info", f"Installing NeoVim via {package_manager}...")

            install_cmd = []
            if package_manager == "apt":
                install_cmd = ["sudo", "apt-get", "install", "-y", "neovim"]
            elif package_manager == "yum":
                install_cmd = ["sudo", "yum", "install", "-y", "neovim"]
            elif package_manager == "dnf":
                install_cmd = ["sudo", "dnf", "install", "-y", "neovim"]

            result = subprocess.run(
                install_cmd,
                capture_output=True,
                text=True
            )

            # Log command output
            if result.stdout:
                for line in result.stdout.splitlines():
                    log("info", line)

            if result.returncode != 0:
                log("error", f"Installation failed: {result.stderr}")
                return {
                    "success": False,
                    "version": None,
                    "message": "Installation failed",
                    "logs": logs
                }

            # Step 4: Verify installation
            nvim_info = await VimManager.detect_neovim()
            if nvim_info.installed:
                log("success", f"NeoVim {nvim_info.version} installed successfully")
                return {
                    "success": True,
                    "version": nvim_info.version,
                    "message": "Installation successful",
                    "logs": logs
                }
            else:
                log("error", "Installation verification failed")
                return {
                    "success": False,
                    "version": None,
                    "message": "Installation verification failed",
                    "logs": logs
                }

        except Exception as e:
            log("error", f"Installation error: {str(e)}")
            return {
                "success": False,
                "version": None,
                "message": str(e),
                "logs": logs
            }

    @staticmethod
    async def uninstall_neovim(
        package_manager: str,
        progress_callback: Optional[Callable[[str, str], None]] = None
    ) -> Dict[str, any]:
        """Uninstall NeoVim via system package manager."""
        logger = get_module_logger("vim_manager")
        logger.info(f"Uninstalling NeoVim via {package_manager}")

        logs = []

        def log(level: str | int, message: str) -> None:
            if isinstance(level, str):
                numeric_level = getattr(logging, level.upper(), logging.INFO)
                level_label = level.upper()
                callback_level = level
            else:
                numeric_level = level
                level_label = logging.getLevelName(level).upper()
                callback_level = level_label.lower()

            logger.log(numeric_level, message)
            logs.append(f"[{level_label}] {message}")
            if progress_callback:
                progress_callback(callback_level, message)

        try:
            log("info", "Removing NeoVim package...")

            uninstall_cmd = []
            if package_manager == "apt":
                uninstall_cmd = ["sudo", "apt-get", "remove", "-y", "neovim"]
            elif package_manager == "yum":
                uninstall_cmd = ["sudo", "yum", "remove", "-y", "neovim"]
            elif package_manager == "dnf":
                uninstall_cmd = ["sudo", "dnf", "remove", "-y", "neovim"]
            else:
                log("error", f"Unsupported package manager: {package_manager}")
                return {
                    "success": False,
                    "message": f"Unsupported package manager: {package_manager}",
                    "logs": logs,
                }

            result = subprocess.run(
                uninstall_cmd,
                capture_output=True,
                text=True
            )

            if result.stdout:
                for line in result.stdout.splitlines():
                    log("info", line)

            if result.stderr:
                for line in result.stderr.splitlines():
                    log("info", line)

            if result.returncode != 0:
                log("error", f"Removal failed: {result.stderr.strip()}")
                return {
                    "success": False,
                    "message": "Removal failed",
                    "logs": logs,
                }

            # Verify removal
            nvim_info = await VimManager.detect_neovim()
            if not nvim_info.installed:
                log("success", "NeoVim removed successfully")
                return {
                    "success": True,
                    "message": "NeoVim removed",
                    "logs": logs,
                }

            log("error", "NeoVim still detected after removal attempt")
            return {
                "success": False,
                "message": "NeoVim still installed",
                "logs": logs,
            }

        except Exception as e:
            log("error", f"Removal error: {str(e)}")
            return {
                "success": False,
                "message": str(e),
                "logs": logs,
            }

    @staticmethod
    async def install_lazyvim(
        progress_callback: Optional[Callable[[str, str], None]] = None
    ) -> Dict[str, any]:
        """
        Install LazyVim configuration framework.

        Args:
            progress_callback: Function(level, message) to report progress

        Returns:
            {
                "success": bool,
                "backup_path": Optional[str],
                "message": str,
                "logs": List[str]
            }
        """
        logger = get_module_logger("vim_manager")
        logger.info("Installing LazyVim")

        logs = []

        def log(level: str | int, message: str) -> None:
            """Helper to log and report progress."""
            if isinstance(level, str):
                numeric_level = getattr(logging, level.upper(), logging.INFO)
                level_label = level.upper()
                callback_level = level
            else:
                numeric_level = level
                level_label = logging.getLevelName(level).upper()
                callback_level = level_label.lower()

            logger.log(numeric_level, message)
            logs.append(f"[{level_label}] {message}")
            if progress_callback:
                progress_callback(callback_level, message)

        try:
            config_path = Path.home() / ".config" / "nvim"
            backup_path = None

            # Step 1: Backup existing config if exists
            if config_path.exists():
                timestamp = int(datetime.now().timestamp())
                backup_path = f"{config_path}.backup.{timestamp}"
                log("info", f"Backing up existing config to: {backup_path}")

                subprocess.run(
                    ["mv", str(config_path), backup_path],
                    check=True
                )
                log("success", f"Backup created at: {backup_path}")

            # Step 2: Clone LazyVim starter
            log("info", "Cloning LazyVim starter repository...")

            clone_result = subprocess.run(
                ["git", "clone", VimManager.LAZYVIM_REPO_URL, str(config_path)],
                capture_output=True,
                text=True
            )

            # Log git output
            if clone_result.stdout:
                for line in clone_result.stdout.splitlines():
                    log("info", line)
            if clone_result.stderr:
                for line in clone_result.stderr.splitlines():
                    # Git outputs progress to stderr
                    log("info", line)

            if clone_result.returncode != 0:
                log("error", "Failed to clone LazyVim repository")
                # Rollback
                if backup_path:
                    log("info", "Rolling back: restoring backup")
                    subprocess.run(["mv", backup_path, str(config_path)])
                return {
                    "success": False,
                    "backup_path": backup_path,
                    "message": "Git clone failed",
                    "logs": logs
                }

            # Step 3: Remove .git directory
            log("info", "Removing .git directory...")
            git_dir = config_path / ".git"
            if git_dir.exists():
                subprocess.run(["rm", "-rf", str(git_dir)], check=True)

            log("success", "LazyVim installed successfully!")
            log("info", "")
            log("info", "Next steps:")
            log("info", "1. Run 'nvim' to start plugin installation")
            log("info", "2. First launch will download plugins (~5-10 minutes)")

            return {
                "success": True,
                "backup_path": backup_path,
                "message": "LazyVim installed successfully",
                "logs": logs
            }

        except Exception as e:
            log("error", f"Installation error: {str(e)}")
            return {
                "success": False,
                "backup_path": backup_path,
                "message": str(e),
                "logs": logs
            }

    @staticmethod
    async def uninstall_lazyvim(
        progress_callback: Optional[Callable[[str, str], None]] = None
    ) -> Dict[str, any]:
        """Remove LazyVim configuration directory."""
        logger = get_module_logger("vim_manager")
        logger.info("Uninstalling LazyVim configuration")

        logs = []

        def log(level: str | int, message: str) -> None:
            if isinstance(level, str):
                numeric_level = getattr(logging, level.upper(), logging.INFO)
                level_label = level.upper()
                callback_level = level
            else:
                numeric_level = level
                level_label = logging.getLevelName(level).upper()
                callback_level = level_label.lower()

            logger.log(numeric_level, message)
            logs.append(f"[{level_label}] {message}")
            if progress_callback:
                progress_callback(callback_level, message)

        try:
            config_path = Path.home() / ".config" / "nvim"

            if not config_path.exists():
                log("info", "LazyVim configuration not found")
                return {
                    "success": True,
                    "message": "LazyVim configuration not found",
                    "backup_path": None,
                    "logs": logs,
                }

            timestamp = int(datetime.now().timestamp())
            backup_path = f"{config_path}.removed.{timestamp}"

            log("info", f"Renaming {config_path} to {backup_path}")
            subprocess.run(["mv", str(config_path), backup_path], check=True)

            log("success", "LazyVim configuration removed")
            return {
                "success": True,
                "message": "LazyVim removed",
                "backup_path": backup_path,
                "logs": logs,
            }

        except Exception as e:
            log("error", f"Removal error: {str(e)}")
            return {
                "success": False,
                "message": str(e),
                "backup_path": None,
                "logs": logs,
            }

    @staticmethod
    async def rollback_installation(backup_path: Optional[str]) -> Dict[str, any]:
        """
        Rollback failed installation.

        Args:
            backup_path: Path to backup directory (if exists)

        Returns:
            {"success": bool, "message": str}
        """
        logger = get_module_logger("vim_manager")

        if not backup_path or not Path(backup_path).exists():
            logger.warning("No backup to restore")
            return {"success": False, "message": "No backup found"}

        try:
            config_path = Path.home() / ".config" / "nvim"

            # Remove failed installation
            if config_path.exists():
                subprocess.run(["rm", "-rf", str(config_path)], check=True)

            # Restore backup
            subprocess.run(["mv", backup_path, str(config_path)], check=True)

            logger.info(f"Rollback successful: restored from {backup_path}")
            return {"success": True, "message": "Configuration restored from backup"}

        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return {"success": False, "message": str(e)}

    @staticmethod
    def _compare_versions(version1: str, version2: str) -> int:
        """
        Compare two version strings.

        Args:
            version1: First version (e.g., "0.9.5")
            version2: Second version (e.g., "0.9.0")

        Returns:
            -1 if version1 < version2
             0 if version1 == version2
             1 if version1 > version2
        """
        def parse_version(v: str):
            return tuple(map(int, v.split('.')))

        v1 = parse_version(version1)
        v2 = parse_version(version2)

        if v1 < v2:
            return -1
        elif v1 > v2:
            return 1
        else:
            return 0
