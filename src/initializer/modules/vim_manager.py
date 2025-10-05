"""NeoVim and LazyVim management module."""

import os
import subprocess
import asyncio
import logging
import json
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
    version: Optional[str] = None
    can_run: bool = False  # Whether LazyVim can run (NeoVim available and compatible)
    nvim_compatible: bool = False  # Whether current NeoVim version is compatible


class VimManager:
    """NeoVim and LazyVim management."""

    MIN_NVIM_VERSION = "0.11.2"
    LAZYVIM_REPO_URL = "https://github.com/LazyVim/starter.git"
    NVIM_TARBALL_URL = "https://github.com/neovim/neovim/releases/latest/download/nvim-linux-x86_64.tar.gz"
    NVIM_INSTALL_DIR = "/opt/nvim-linux-x86_64"

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
        Detect LazyVim installation status, version, and compatibility.

        Returns:
            LazyVimInfo object with installation details
        """
        logger = get_module_logger("vim_manager")
        logger.debug("Detecting LazyVim installation")

        config_path = Path.home() / ".config" / "nvim"
        lazy_lua_path = config_path / "lua" / "config" / "lazy.lua"
        lazy_lock_path = config_path / "lazy-lock.json"

        installed = config_path.exists()
        has_lazy_lua = lazy_lua_path.exists()

        # Detect version from multiple sources (in priority order)
        version = None
        version_source = None

        # Priority 1: Check .lazyvim-version file (created during installation)
        version_file = config_path / ".lazyvim-version"
        if version_file.exists():
            try:
                with open(version_file, 'r') as f:
                    lines = f.read().strip().split('\n')
                    if lines:
                        commit_hash = lines[0].strip()

                        # Line 3: starter tag (usually empty)
                        # Line 4: LazyVim version from GitHub API
                        if len(lines) >= 4 and lines[3].strip():
                            version = lines[3].strip()  # LazyVim version (e.g., v15.7.1)
                            version_source = "api"
                            logger.debug(f"LazyVim version from API: {version}")
                        elif len(lines) >= 3 and lines[2].strip():
                            version = lines[2].strip()  # Starter tag (rare)
                            version_source = "tag"
                            logger.debug(f"LazyVim version from starter tag: {version}")
                        else:
                            version = commit_hash[:8]  # Use short commit hash
                            version_source = "starter"
                            logger.debug(f"LazyVim version from starter commit: {version}")

                        if len(lines) > 1:
                            commit_date = lines[1].strip()
                            logger.debug(f"LazyVim starter date: {commit_date}")
            except Exception as e:
                logger.warning(f"Failed to read .lazyvim-version: {e}")

        # Priority 2: Check lazy-lock.json (after first nvim run)
        if not version and lazy_lock_path.exists():
            try:
                with open(lazy_lock_path, 'r') as f:
                    lock_data = json.load(f)
                    # LazyVim version is stored in lazy-lock.json under "LazyVim" key
                    if "LazyVim" in lock_data:
                        lazyvim_entry = lock_data["LazyVim"]
                        # The commit hash can be used as version identifier
                        if isinstance(lazyvim_entry, dict) and "commit" in lazyvim_entry:
                            commit_hash = lazyvim_entry["commit"]
                            version = commit_hash[:8]  # Use short commit hash as version
                            version_source = "lock"
                            logger.debug(f"LazyVim version from lazy-lock.json: {version}")
            except Exception as e:
                logger.warning(f"Failed to read LazyVim version from lazy-lock.json: {e}")

        # Priority 3: Check if LazyVim is configured but not yet initialized
        if not version and lazy_lua_path.exists():
            try:
                with open(lazy_lua_path, 'r') as f:
                    lazy_content = f.read()
                    # Check if LazyVim is configured in lazy.lua
                    if 'LazyVim/LazyVim' in lazy_content or 'lazyvim.plugins' in lazy_content:
                        # For existing installations without version file, try to get version from git (if .git exists)
                        git_dir = config_path / ".git"
                        if git_dir.exists():
                            try:
                                # Try to get version tag
                                tag_result = subprocess.run(
                                    ["git", "-C", str(config_path), "describe", "--tags", "--abbrev=0"],
                                    capture_output=True,
                                    text=True
                                )
                                if tag_result.returncode == 0:
                                    version = tag_result.stdout.strip()
                                    version_source = "git-tag"
                                    logger.debug(f"LazyVim version from git tag: {version}")
                                else:
                                    # Fallback to commit hash
                                    git_result = subprocess.run(
                                        ["git", "-C", str(config_path), "rev-parse", "HEAD"],
                                        capture_output=True,
                                        text=True
                                    )
                                    if git_result.returncode == 0:
                                        commit_hash = git_result.stdout.strip()
                                        version = commit_hash[:8]
                                        version_source = "git"
                                        logger.debug(f"LazyVim version from git: {version}")
                                    else:
                                        version = "Not initialized"
                                        version_source = "config"
                            except Exception:
                                version = "Not initialized"
                                version_source = "config"
                        else:
                            version = "Not initialized"
                            version_source = "config"
                            logger.debug("LazyVim configured but not yet initialized (run nvim to initialize)")
            except Exception as e:
                logger.warning(f"Failed to read lazy.lua: {e}")

        # Check NeoVim compatibility
        nvim_info = await VimManager.detect_neovim()
        nvim_compatible = nvim_info.installed and nvim_info.meets_requirement
        can_run = (installed and has_lazy_lua and nvim_compatible)

        logger.info(f"LazyVim detection complete: installed={installed}, "
                   f"has_lazy_lua={has_lazy_lua}, version={version}, "
                   f"can_run={can_run}, nvim_compatible={nvim_compatible}")

        return LazyVimInfo(
            installed=installed and has_lazy_lua,
            config_path=str(config_path) if config_path.exists() else None,
            has_lazy_lua=has_lazy_lua,
            version=version,
            can_run=can_run,
            nvim_compatible=nvim_compatible
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
    async def _uninstall_all_neovim(package_manager: str, log_func: Callable) -> None:
        """
        Uninstall all NeoVim installations (package manager + tarball).

        Args:
            package_manager: "apt", "yum", or "dnf"
            log_func: Logging function
        """
        logger = get_module_logger("vim_manager")

        # Remove package manager installation
        try:
            log_func("info", f"Checking for {package_manager} package...")
            check_cmd = []
            if package_manager == "apt":
                check_cmd = ["dpkg", "-l", "neovim"]
            elif package_manager in ["yum", "dnf"]:
                check_cmd = [package_manager, "list", "installed", "neovim"]

            result = subprocess.run(check_cmd, capture_output=True, text=True)
            if result.returncode == 0:
                log_func("info", f"Removing NeoVim package via {package_manager}...")
                uninstall_cmd = []
                if package_manager == "apt":
                    uninstall_cmd = ["sudo", "apt-get", "remove", "-y", "neovim"]
                elif package_manager == "yum":
                    uninstall_cmd = ["sudo", "yum", "remove", "-y", "neovim"]
                elif package_manager == "dnf":
                    uninstall_cmd = ["sudo", "dnf", "remove", "-y", "neovim"]

                subprocess.run(uninstall_cmd, capture_output=True)
                log_func("success", "Package manager version removed")
        except Exception as e:
            logger.debug(f"Error removing package version: {e}")

        # Remove tarball installation
        install_dir = Path(VimManager.NVIM_INSTALL_DIR)
        if install_dir.exists():
            log_func("info", f"Removing tarball installation at {install_dir}...")
            try:
                subprocess.run(["sudo", "rm", "-rf", str(install_dir)], check=True)
                log_func("success", "Tarball installation removed")
            except Exception as e:
                logger.warning(f"Error removing tarball installation: {e}")

        # Remove symlink
        symlink_path = Path("/usr/local/bin/nvim")
        if symlink_path.is_symlink() or symlink_path.exists():
            log_func("info", "Removing nvim symlink...")
            try:
                subprocess.run(["sudo", "rm", "-f", str(symlink_path)], check=True)
            except Exception as e:
                logger.debug(f"Error removing symlink: {e}")

    @staticmethod
    def check_repo_version(package_manager: str) -> Optional[str]:
        """
        Check NeoVim version available in package manager repository.

        Args:
            package_manager: "apt", "yum", or "dnf"

        Returns:
            Version string if available, None otherwise
        """
        logger = get_module_logger("vim_manager")
        logger.debug(f"Checking NeoVim version in {package_manager} repository")

        try:
            if package_manager == "apt":
                result = subprocess.run(
                    ["apt-cache", "policy", "neovim"],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    # Extract version from apt-cache output
                    # Format: "Candidate: 0.x.x-x"
                    match = re.search(r'Candidate:\s+(\d+\.\d+\.\d+)', result.stdout)
                    if match:
                        version = match.group(1)
                        logger.info(f"APT repository NeoVim version: {version}")
                        return version
                    # Try alternative format
                    match = re.search(r'Candidate:\s+(\d+\.\d+)', result.stdout)
                    if match:
                        version = match.group(1) + ".0"
                        logger.info(f"APT repository NeoVim version: {version}")
                        return version

            elif package_manager in ["yum", "dnf"]:
                result = subprocess.run(
                    [package_manager, "info", "neovim"],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    match = re.search(r'Version\s+:\s+(\d+\.\d+\.\d+)', result.stdout)
                    if match:
                        version = match.group(1)
                        logger.info(f"{package_manager.upper()} repository NeoVim version: {version}")
                        return version
                    # Try alternative format
                    match = re.search(r'Version\s+:\s+(\d+\.\d+)', result.stdout)
                    if match:
                        version = match.group(1) + ".0"
                        logger.info(f"{package_manager.upper()} repository NeoVim version: {version}")
                        return version

        except Exception as e:
            logger.warning(f"Failed to check repository version: {e}")

        return None

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
            # Step 1: Check if NeoVim is already installed
            log("info", "Checking for existing NeoVim installation...")
            nvim_info = await VimManager.detect_neovim()

            if nvim_info.installed:
                if nvim_info.meets_requirement:
                    log("info", f"NeoVim {nvim_info.version} is already installed and meets requirements")
                    return {
                        "success": True,
                        "version": nvim_info.version,
                        "message": "Already installed",
                        "logs": logs
                    }
                else:
                    log("warning", f"Found NeoVim {nvim_info.version} (requires >= {VimManager.MIN_NVIM_VERSION})")
                    log("info", "Removing old version...")

                    # Uninstall old version
                    await VimManager._uninstall_all_neovim(package_manager, log)

            # Step 2: Check repository version
            log("info", "Checking NeoVim version in repository...")

            repo_version = VimManager.check_repo_version(package_manager)

            # Step 2: Decide installation method based on repository version
            use_tarball = False
            if repo_version:
                log("info", f"Repository version: {repo_version}")

                if VimManager._compare_versions(repo_version, VimManager.MIN_NVIM_VERSION) < 0:
                    log("warning", f"Repository version {repo_version} is too old.")
                    log("info", f"LazyVim requires >= {VimManager.MIN_NVIM_VERSION}")
                    log("info", "Will install from official tarball instead...")
                    use_tarball = True
            else:
                log("warning", "Could not detect repository version")
                log("info", "Will try package manager installation first")

            # Step 3: Install via tarball if needed
            if use_tarball:
                log("info", "Switching to tarball installation method...")
                result = await VimManager.install_neovim_from_tarball(progress_callback)
                return result

            # Step 4: Install NeoVim via package manager
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

            # Step 5: Verify installation
            nvim_info = await VimManager.detect_neovim()
            if nvim_info.installed:
                # Check if installed version meets requirement
                if not nvim_info.meets_requirement:
                    log("warning", f"Installed version {nvim_info.version} does not meet requirement >= {VimManager.MIN_NVIM_VERSION}")
                    log("info", "Switching to tarball installation...")

                    # Uninstall the old version first
                    log("info", "Removing package manager version...")
                    uninstall_cmd = []
                    if package_manager == "apt":
                        uninstall_cmd = ["sudo", "apt-get", "remove", "-y", "neovim"]
                    elif package_manager == "yum":
                        uninstall_cmd = ["sudo", "yum", "remove", "-y", "neovim"]
                    elif package_manager == "dnf":
                        uninstall_cmd = ["sudo", "dnf", "remove", "-y", "neovim"]

                    subprocess.run(uninstall_cmd, capture_output=True)

                    # Install from tarball
                    result = await VimManager.install_neovim_from_tarball(progress_callback)
                    return result

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
            log("info", "Removing all NeoVim installations...")

            # Use the comprehensive uninstall method
            await VimManager._uninstall_all_neovim(package_manager, log)

            # Verify removal
            nvim_info = await VimManager.detect_neovim()
            if not nvim_info.installed:
                log("success", "NeoVim removed successfully")
                return {
                    "success": True,
                    "message": "NeoVim removed",
                    "logs": logs,
                }

            log("warning", "NeoVim still detected after removal attempt")
            log("info", "You may need to manually remove custom installations")
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
    async def install_neovim_from_tarball(
        progress_callback: Optional[Callable[[str, str], None]] = None
    ) -> Dict[str, any]:
        """
        Install NeoVim from official tarball.

        Args:
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
        logger.info("Installing NeoVim from tarball")

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
            install_dir = Path(VimManager.NVIM_INSTALL_DIR)
            tarball_path = Path("/tmp/nvim-linux-x86_64.tar.gz")

            # Step 1: Download tarball
            log("info", f"Downloading NeoVim from {VimManager.NVIM_TARBALL_URL}...")
            download_result = subprocess.run(
                ["curl", "-fL", "-o", str(tarball_path), VimManager.NVIM_TARBALL_URL],
                capture_output=True,
                text=True
            )

            if download_result.returncode != 0:
                log("error", f"Download failed: {download_result.stderr}")
                return {
                    "success": False,
                    "version": None,
                    "message": "Download failed",
                    "logs": logs
                }

            # Verify downloaded file is actually a gzip tarball
            file_check = subprocess.run(
                ["file", str(tarball_path)],
                capture_output=True,
                text=True
            )
            if "gzip compressed" not in file_check.stdout:
                log("error", f"Downloaded file is not a valid tarball: {file_check.stdout}")
                subprocess.run(["rm", "-f", str(tarball_path)])
                return {
                    "success": False,
                    "version": None,
                    "message": "Invalid tarball downloaded",
                    "logs": logs
                }

            log("success", "Download completed and verified")

            # Step 2: Remove old installation if exists
            if install_dir.exists():
                log("info", f"Removing old installation at {install_dir}...")
                subprocess.run(["sudo", "rm", "-rf", str(install_dir)], check=True)

            # Step 3: Extract tarball
            log("info", "Extracting tarball...")
            subprocess.run(
                ["sudo", "mkdir", "-p", str(install_dir.parent)],
                check=True
            )

            extract_result = subprocess.run(
                ["sudo", "tar", "-xzf", str(tarball_path), "-C", str(install_dir.parent)],
                capture_output=True,
                text=True
            )

            if extract_result.returncode != 0:
                log("error", f"Extraction failed: {extract_result.stderr}")
                subprocess.run(["rm", "-f", str(tarball_path)])
                return {
                    "success": False,
                    "version": None,
                    "message": "Tarball extraction failed",
                    "logs": logs
                }

            # Step 4: Create symlinks
            log("info", "Creating symlinks...")
            nvim_bin = install_dir / "bin" / "nvim"
            if nvim_bin.exists():
                subprocess.run(
                    ["sudo", "ln", "-sf", str(nvim_bin), "/usr/local/bin/nvim"],
                    check=True
                )
            else:
                log("error", f"NeoVim binary not found at {nvim_bin}")
                return {
                    "success": False,
                    "version": None,
                    "message": "Binary not found after extraction",
                    "logs": logs
                }

            # Step 5: Cleanup
            log("info", "Cleaning up temporary files...")
            subprocess.run(["rm", "-f", str(tarball_path)])

            # Step 6: Verify installation
            nvim_info = await VimManager.detect_neovim()
            if nvim_info.installed:
                log("success", f"NeoVim {nvim_info.version} installed successfully from tarball")
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

            # Step 3: Get Git version info before removing .git directory
            log("info", "Recording version information...")
            git_dir = config_path / ".git"
            version_file = config_path / ".lazyvim-version"

            if git_dir.exists():
                try:
                    # Get current commit hash
                    git_result = subprocess.run(
                        ["git", "-C", str(config_path), "rev-parse", "HEAD"],
                        capture_output=True,
                        text=True
                    )
                    if git_result.returncode == 0:
                        commit_hash = git_result.stdout.strip()

                        # Try to get version tag from starter repo (unlikely to have one)
                        tag_result = subprocess.run(
                            ["git", "-C", str(config_path), "describe", "--tags", "--exact-match"],
                            capture_output=True,
                            text=True
                        )

                        version_tag = None
                        if tag_result.returncode == 0:
                            version_tag = tag_result.stdout.strip()
                        else:
                            # Try to get the most recent tag from starter repo
                            recent_tag_result = subprocess.run(
                                ["git", "-C", str(config_path), "describe", "--tags", "--abbrev=0"],
                                capture_output=True,
                                text=True
                            )
                            if recent_tag_result.returncode == 0:
                                version_tag = recent_tag_result.stdout.strip()

                        # Get commit date
                        date_result = subprocess.run(
                            ["git", "-C", str(config_path), "log", "-1", "--format=%ci"],
                            capture_output=True,
                            text=True
                        )
                        commit_date = date_result.stdout.strip() if date_result.returncode == 0 else "unknown"

                        # Get LazyVim latest version from GitHub (with fallback methods)
                        lazyvim_version = None
                        try:
                            # Method 1: Try GitHub API (may hit rate limit)
                            api_result = subprocess.run(
                                ["curl", "-s", "-f", "https://api.github.com/repos/LazyVim/LazyVim/releases/latest"],
                                capture_output=True,
                                text=True,
                                timeout=5
                            )
                            if api_result.returncode == 0 and "tag_name" in api_result.stdout:
                                import json
                                try:
                                    release_data = json.loads(api_result.stdout)
                                    if "tag_name" in release_data:
                                        lazyvim_version = release_data["tag_name"]
                                        log("info", f"Latest LazyVim plugin version: {lazyvim_version}")
                                except json.JSONDecodeError:
                                    pass
                        except Exception:
                            pass

                        # Method 2: Fallback - note that version will be available after running nvim
                        if not lazyvim_version:
                            log("info", "LazyVim version will be available after first 'nvim' run")

                        # Save version info to file
                        # Format: commit_hash\ncommit_date\nstarter_tag\nlazyvim_version
                        with open(version_file, 'w') as f:
                            f.write(f"{commit_hash}\n{commit_date}\n")
                            if version_tag:
                                f.write(f"{version_tag}\n")
                            else:
                                f.write("\n")  # Empty line for starter tag
                            if lazyvim_version:
                                f.write(f"{lazyvim_version}\n")

                        if lazyvim_version:
                            log("info", f"LazyVim reference version: {lazyvim_version}")
                        if version_tag:
                            log("info", f"Starter template version: {version_tag} ({commit_hash[:8]})")
                        else:
                            log("info", f"Starter commit: {commit_hash[:8]}")
                except Exception as e:
                    log("warning", f"Failed to record version info: {e}")

            # Step 4: Remove .git directory
            log("info", "Removing .git directory...")
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
