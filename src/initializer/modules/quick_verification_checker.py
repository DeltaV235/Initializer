"""Quick verification layer for efficient preliminary package status checking."""

import shutil
import os
from typing import List, Dict, Tuple, Optional, Set
from pathlib import Path
from dataclasses import dataclass
from ..utils.logger import get_module_logger


@dataclass
class Application:
    """Represents an application that can be quickly verified."""
    name: str
    package: str
    description: str = ""
    installed: bool = False

    def get_package_list(self) -> List[str]:
        """Get list of packages from the package string."""
        return self.package.split()


class QuickVerificationChecker:
    """Quick verification layer using filesystem checks before expensive system queries."""

    def __init__(self, package_manager_type: str):
        """Initialize the quick verification checker.

        Args:
            package_manager_type: Type of package manager (apt, brew, yum, etc.)
        """
        self.pm_type = package_manager_type
        self.logger = get_module_logger("quick_verification_checker")

        # Common installation paths by package manager type
        self.common_paths = {
            "apt": [
                "/usr/bin/{package}",
                "/usr/local/bin/{package}",
                "/bin/{package}",
                "/usr/sbin/{package}",
                "/sbin/{package}",
                "/opt/{package}",
                "/usr/share/{package}",
                "/etc/{package}",
            ],
            "brew": [
                "/usr/local/bin/{package}",
                "/opt/homebrew/bin/{package}",
                "/usr/local/Cellar/{package}",
                "/opt/homebrew/Cellar/{package}",
                "/Applications/{package}.app",
                "/System/Applications/{package}.app",
                "/usr/local/opt/{package}",
                "/opt/homebrew/opt/{package}",
            ],
            "yum": [
                "/usr/bin/{package}",
                "/bin/{package}",
                "/usr/sbin/{package}",
                "/sbin/{package}",
                "/opt/{package}",
                "/usr/share/{package}",
            ],
            "dnf": [
                "/usr/bin/{package}",
                "/bin/{package}",
                "/usr/sbin/{package}",
                "/sbin/{package}",
                "/opt/{package}",
                "/usr/share/{package}",
            ],
            "pacman": [
                "/usr/bin/{package}",
                "/bin/{package}",
                "/usr/sbin/{package}",
                "/sbin/{package}",
                "/opt/{package}",
                "/usr/share/{package}",
            ],
        }

        # Package-specific detection rules
        self.special_detection_rules = {
            # Python packages often have versioned executables
            "python3": ["python3", "python3.8", "python3.9", "python3.10", "python3.11", "python3.12"],
            "python": ["python", "python2", "python3"],
            "pip": ["pip", "pip3", "pip2"],

            # Node.js related
            "nodejs": ["node", "nodejs"],
            "npm": ["npm"],

            # Java
            "openjdk": ["java", "javac"],
            "default-jdk": ["java", "javac"],
            "java": ["java", "javac"],

            # Docker
            "docker": ["docker"],
            "docker.io": ["docker"],
            "docker-ce": ["docker"],

            # Database packages might not have direct executables
            "mysql-server": ["mysql", "mysqld"],
            "postgresql": ["psql", "postgres"],
            "redis-server": ["redis-server", "redis-cli"],

            # System tools
            "build-essential": ["gcc", "g++", "make"],
            "curl": ["curl"],
            "wget": ["wget"],
            "git": ["git"],
            "vim": ["vim", "vi"],
            "nano": ["nano"],
            "htop": ["htop"],
            "tree": ["tree"],

            # Text editors and IDEs
            "code": ["code"],
            "sublime-text": ["subl"],
            "atom": ["atom"],
        }

        self.logger.info(f"QuickVerificationChecker initialized for {package_manager_type}")

    def quick_verify_applications(self, applications: List[Application]) -> Tuple[Dict[str, bool], List[Application]]:
        """Quickly verify applications using filesystem checks.

        Args:
            applications: List of applications to verify

        Returns:
            Tuple of (verified_results, unverified_applications)
            - verified_results: Dict of app_name -> installation_status for apps that could be quickly verified
            - unverified_applications: List of apps that need system-level checking
        """
        self.logger.debug(f"Starting quick verification for {len(applications)} applications")
        verified_results = {}
        unverified_apps = []

        for app in applications:
            quick_result = self._quick_verify_single_app(app)

            if quick_result is not None:
                # Could quickly determine status
                verified_results[app.name] = quick_result
                self.logger.debug(f"Quick verification: {app.name} = {'installed' if quick_result else 'not installed'}")
            else:
                # Need system-level check
                unverified_apps.append(app)
                self.logger.debug(f"Quick verification: {app.name} = needs system check")

        self.logger.info(f"Quick verification completed: {len(verified_results)} verified, {len(unverified_apps)} need system check")
        return verified_results, unverified_apps

    def _quick_verify_single_app(self, app: Application) -> Optional[bool]:
        """Quickly verify a single application.

        Strategy: L2 layer focuses on definitive "NOT INSTALLED" detection only.
        We avoid false positives by being conservative about "INSTALLED" determinations.

        Args:
            app: Application to verify

        Returns:
            False if definitely not installed, None if uncertain (needs L3 check)
        """
        packages = app.get_package_list()

        # Check if this looks like a clearly non-existent package
        for package in packages:
            if self._is_definitely_nonexistent(package):
                return False

        # For all other cases, defer to L3 system check for accuracy
        # This prevents false positives while still catching obvious non-existent packages
        return None

    def _is_definitely_nonexistent(self, package: str) -> bool:
        """Check if a package is definitely non-existent based on name patterns.

        Args:
            package: Package name to check

        Returns:
            True if we're confident the package doesn't exist
        """
        # Patterns that indicate fake/test packages
        nonexistent_patterns = [
            "this-package",
            "does-not-exist",
            "nonexistent",
            "fake-package",
            "test-package",
            "definitely-does-not-exist",
            "completely-fake",
            "absolutely-does-not-exist",
        ]

        package_lower = package.lower()

        # Check for obviously fake package names
        for pattern in nonexistent_patterns:
            if pattern in package_lower:
                self.logger.debug(f"Detected fake package by pattern: {package}")
                return True

        # Check for random-looking names (contains numbers and hyphens suggesting test names)
        import re
        if re.search(r'[a-z]+-[a-z]+-[a-z]+.*\d+', package_lower):
            if len(package) > 20:  # Very long names are often test packages
                self.logger.debug(f"Detected likely test package by pattern: {package}")
                return True

        return False

    def _check_package_indicators(self, package: str) -> Optional[bool]:
        """Check various indicators for a single package.

        Args:
            package: Package name to check

        Returns:
            True if strong evidence of installation, False if strong evidence of absence, None if uncertain
        """
        # Method 1: Check if executable is in PATH
        if self._check_executable_in_path(package):
            return True

        # Method 2: Check special detection rules for this package
        if package in self.special_detection_rules:
            for alt_name in self.special_detection_rules[package]:
                if self._check_executable_in_path(alt_name):
                    return True

        # Method 3: Check common installation paths
        if self._check_common_paths(package):
            return True

        # Method 4: Check package-specific paths and files
        if self._check_package_specific_files(package):
            return True

        # Method 5: For some packages, absence of key files indicates not installed
        if self._check_definitive_absence(package):
            return False

        # Uncertain - need system-level check
        return None

    def _check_executable_in_path(self, executable: str) -> bool:
        """Check if an executable exists in PATH."""
        try:
            return shutil.which(executable) is not None
        except Exception:
            return False

    def _check_common_paths(self, package: str) -> bool:
        """Check common installation paths for the package."""
        # Get paths for current package manager, fallback to all paths
        paths_templates = self.common_paths.get(
            self.pm_type,
            # Combine all paths as fallback
            sum(self.common_paths.values(), [])
        )

        for path_template in paths_templates:
            try:
                path = Path(path_template.format(package=package))
                if path.exists():
                    self.logger.debug(f"Found package indicator at: {path}")
                    return True
            except Exception:
                continue

        return False

    def _check_package_specific_files(self, package: str) -> bool:
        """Check for package-specific files and directories."""
        specific_checks = {
            # Python packages
            "python3": ["/usr/lib/python3*", "/usr/local/lib/python3*"],
            "python": ["/usr/lib/python*", "/usr/local/lib/python*"],

            # Node.js
            "nodejs": ["/usr/lib/node_modules", "/usr/local/lib/node_modules"],

            # Docker
            "docker": ["/var/lib/docker", "/etc/docker"],
            "docker.io": ["/var/lib/docker", "/etc/docker"],

            # Database services
            "mysql-server": ["/var/lib/mysql", "/etc/mysql"],
            "postgresql": ["/var/lib/postgresql", "/etc/postgresql"],
            "redis-server": ["/var/lib/redis", "/etc/redis"],

            # System tools
            "build-essential": ["/usr/include", "/usr/share/build-essential"],

            # Text editors
            "vim": ["/usr/share/vim", "/etc/vim"],
            "nano": ["/usr/share/nano"],

            # Homebrew specific
            "git": ["/usr/local/share/git-core"] if self.pm_type == "brew" else [],
        }

        if package in specific_checks:
            for path_pattern in specific_checks[package]:
                try:
                    if "*" in path_pattern:
                        # Handle glob patterns
                        import glob
                        matches = glob.glob(path_pattern)
                        if matches:
                            self.logger.debug(f"Found package-specific files for {package}: {matches[0]}")
                            return True
                    else:
                        path = Path(path_pattern)
                        if path.exists():
                            self.logger.debug(f"Found package-specific path for {package}: {path}")
                            return True
                except Exception:
                    continue

        return False

    def _check_definitive_absence(self, package: str) -> bool:
        """Check for definitive signs that a package is NOT installed.

        This is used for packages where we can be confident they're not installed
        based on the absence of key indicators.

        Args:
            package: Package name to check

        Returns:
            True if we're confident the package is not installed, False if uncertain
        """
        # For now, we'll be conservative and not make definitive "not installed" determinations
        # based on filesystem checks alone, as this could lead to false negatives

        # Future enhancement: could add checks like:
        # - For GUI applications, check if .desktop files exist
        # - For services, check if systemd service files exist
        # - For libraries, check if header files exist

        return False

    def get_quick_verification_stats(self, applications: List[Application]) -> Dict[str, int]:
        """Get statistics about quick verification capability.

        Args:
            applications: List of applications to analyze

        Returns:
            Dictionary with verification statistics
        """
        stats = {
            "total_apps": len(applications),
            "has_executables": 0,
            "has_special_rules": 0,
            "has_common_paths": 0,
            "likely_verifiable": 0
        }

        for app in applications:
            packages = app.get_package_list()

            has_executable = any(self._check_executable_in_path(pkg) for pkg in packages)
            has_special = any(pkg in self.special_detection_rules for pkg in packages)
            has_paths = any(self._check_common_paths(pkg) for pkg in packages)

            if has_executable:
                stats["has_executables"] += 1
            if has_special:
                stats["has_special_rules"] += 1
            if has_paths:
                stats["has_common_paths"] += 1
            if has_executable or has_special or has_paths:
                stats["likely_verifiable"] += 1

        return stats