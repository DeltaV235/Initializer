"""Batch package status checker for efficient application status verification."""

import subprocess
import asyncio
import shutil
import time
from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path
from dataclasses import dataclass
from ..utils.logger import get_module_logger


@dataclass
class Application:
    """Represents an application that can be checked."""
    name: str
    package: str
    description: str = ""
    installed: bool = False

    def get_package_list(self) -> List[str]:
        """Get list of packages from the package string."""
        return self.package.split()


class BatchPackageChecker:
    """Efficient batch package status checker using native package manager commands."""

    def __init__(self, package_manager_type: str):
        """Initialize the batch package checker.

        Args:
            package_manager_type: Type of package manager (apt, brew, yum, etc.)
        """
        self.pm_type = package_manager_type
        self.logger = get_module_logger("batch_package_checker")
        self.batch_timeout = 30  # 30 seconds timeout for batch operations

        # Package manager specific configurations
        self.pm_configs = {
            "apt": {
                "batch_supported": True,
                "check_cmd": ["dpkg-query", "-W", "-f", "${Package}\\t${Status}\\n"],
                "installed_pattern": "install ok installed"
            },
            "apt-get": {
                "batch_supported": True,
                "check_cmd": ["dpkg-query", "-W", "-f", "${Package}\\t${Status}\\n"],
                "installed_pattern": "install ok installed"
            },
            "brew": {
                "batch_supported": True,
                "list_formula_cmd": ["brew", "list", "--formula"],
                "list_cask_cmd": ["brew", "list", "--cask"]
            },
            "yum": {
                "batch_supported": True,
                "check_cmd": ["rpm", "-qa", "--queryformat", "%{NAME}\\n"]
            },
            "dnf": {
                "batch_supported": True,
                "check_cmd": ["rpm", "-qa", "--queryformat", "%{NAME}\\n"]
            },
            "pacman": {
                "batch_supported": True,
                "check_cmd": ["pacman", "-Qq"]
            },
            "zypper": {
                "batch_supported": False,  # Use individual checks
                "check_cmd": ["rpm", "-q"]
            },
            "apk": {
                "batch_supported": False,  # Use individual checks
                "check_cmd": ["apk", "info", "-e"]
            }
        }

        self.logger.info(f"BatchPackageChecker initialized for package manager: {package_manager_type}")

    async def batch_check_applications(self, applications: List[Application]) -> Dict[str, bool]:
        """Batch check application installation status.

        Args:
            applications: List of applications to check

        Returns:
            Dictionary mapping application names to installation status
        """
        if not applications:
            return {}

        self.logger.debug(f"Starting batch check for {len(applications)} applications")
        start_time = time.time()

        try:
            # Check if batch checking is supported for this package manager
            if self._supports_batch_check():
                self.logger.debug(f"Using batch check for {self.pm_type}")
                results = await self._perform_batch_check(applications)
            else:
                self.logger.debug(f"Batch not supported for {self.pm_type}, using concurrent individual checks")
                results = await self._concurrent_individual_checks(applications)

            duration = time.time() - start_time
            self.logger.info(f"Batch check completed in {duration:.2f}s for {len(applications)} applications")
            self.logger.debug(f"Results: {sum(results.values())} installed, {len(results) - sum(results.values())} not installed")

            return results

        except Exception as e:
            self.logger.error(f"Batch check failed: {str(e)}")
            # Fallback to individual checks
            self.logger.info("Falling back to individual checks due to batch failure")
            return await self._concurrent_individual_checks(applications)

    def _supports_batch_check(self) -> bool:
        """Check if current package manager supports batch checking."""
        config = self.pm_configs.get(self.pm_type, {})
        return config.get("batch_supported", False)

    async def _perform_batch_check(self, applications: List[Application]) -> Dict[str, bool]:
        """Perform package manager specific batch check."""
        if self.pm_type in ["apt", "apt-get"]:
            return await self._batch_apt_check(applications)
        elif self.pm_type == "brew":
            return await self._batch_brew_check(applications)
        elif self.pm_type in ["yum", "dnf"]:
            return await self._batch_rpm_check(applications)
        elif self.pm_type == "pacman":
            return await self._batch_pacman_check(applications)
        else:
            # Unknown package manager, fallback to individual
            return await self._concurrent_individual_checks(applications)

    async def _batch_apt_check(self, applications: List[Application]) -> Dict[str, bool]:
        """APT/DEB batch check using dpkg-query."""
        self.logger.debug("Executing APT batch check")
        results = {}

        try:
            # Collect all packages to check
            app_to_packages = {}
            all_packages = []

            for app in applications:
                packages = app.get_package_list()
                app_to_packages[app.name] = packages
                all_packages.extend(packages)

            if not all_packages:
                return results

            # Build dpkg-query command
            config = self.pm_configs[self.pm_type]
            cmd = config["check_cmd"] + all_packages

            self.logger.debug(f"Running APT batch command: {' '.join(cmd[:5])}... ({len(all_packages)} packages)")

            # Execute batch query
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.batch_timeout
            )

            # Parse results
            if process.returncode == 0 or stdout:  # dpkg-query may return non-zero for missing packages
                installed_packages = set()

                for line in stdout.decode().strip().split('\n'):
                    if line.strip():
                        parts = line.split('\t')
                        if len(parts) >= 2:
                            package = parts[0]
                            status = parts[1]
                            if config["installed_pattern"] in status:
                                installed_packages.add(package)

                self.logger.debug(f"APT batch check found {len(installed_packages)} installed packages")

                # Map results to applications
                for app_name, packages in app_to_packages.items():
                    # All packages must be installed for the application to be considered installed
                    app_installed = all(pkg in installed_packages for pkg in packages)
                    results[app_name] = app_installed

            else:
                self.logger.warning(f"APT batch check returned error: {stderr.decode()}")
                # If batch command failed, use individual checks as fallback
                return await self._concurrent_individual_checks(applications)

        except asyncio.TimeoutError:
            self.logger.warning("APT batch check timed out")
            return await self._concurrent_individual_checks(applications)
        except Exception as e:
            self.logger.error(f"APT batch check failed: {str(e)}")
            return await self._concurrent_individual_checks(applications)

        return results

    async def _batch_brew_check(self, applications: List[Application]) -> Dict[str, bool]:
        """Homebrew batch check using brew list commands."""
        self.logger.debug("Executing Homebrew batch check")
        results = {}

        try:
            # Get all installed formulas and casks
            config = self.pm_configs["brew"]

            # Run both commands concurrently
            formula_task = asyncio.create_subprocess_exec(
                *config["list_formula_cmd"],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            cask_task = asyncio.create_subprocess_exec(
                *config["list_cask_cmd"],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            self.logger.debug("Running Homebrew batch commands for formulas and casks")

            formula_process, cask_process = await asyncio.gather(formula_task, cask_task)

            # Get results with timeout
            formula_result = await asyncio.wait_for(
                formula_process.communicate(), timeout=self.batch_timeout
            )
            cask_result = await asyncio.wait_for(
                cask_process.communicate(), timeout=self.batch_timeout
            )

            # Combine installed packages
            installed_packages = set()

            if formula_process.returncode == 0:
                formula_packages = formula_result[0].decode().strip().split('\n')
                installed_packages.update(pkg.strip() for pkg in formula_packages if pkg.strip())

            if cask_process.returncode == 0:
                cask_packages = cask_result[0].decode().strip().split('\n')
                installed_packages.update(pkg.strip() for pkg in cask_packages if pkg.strip())

            self.logger.debug(f"Homebrew batch check found {len(installed_packages)} installed packages")

            # Check each application
            for app in applications:
                packages = app.get_package_list()
                app_installed = all(pkg in installed_packages for pkg in packages)
                results[app.name] = app_installed

        except asyncio.TimeoutError:
            self.logger.warning("Homebrew batch check timed out")
            return await self._concurrent_individual_checks(applications)
        except Exception as e:
            self.logger.error(f"Homebrew batch check failed: {str(e)}")
            return await self._concurrent_individual_checks(applications)

        return results

    async def _batch_rpm_check(self, applications: List[Application]) -> Dict[str, bool]:
        """YUM/DNF batch check using rpm -qa."""
        self.logger.debug("Executing RPM batch check")
        results = {}

        try:
            config = self.pm_configs[self.pm_type]
            cmd = config["check_cmd"]

            self.logger.debug(f"Running RPM batch command: {' '.join(cmd)}")

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.batch_timeout
            )

            if process.returncode == 0:
                installed_packages = set()
                for line in stdout.decode().strip().split('\n'):
                    if line.strip():
                        installed_packages.add(line.strip())

                self.logger.debug(f"RPM batch check found {len(installed_packages)} installed packages")

                # Check each application
                for app in applications:
                    packages = app.get_package_list()
                    app_installed = all(pkg in installed_packages for pkg in packages)
                    results[app.name] = app_installed
            else:
                self.logger.warning(f"RPM batch check failed: {stderr.decode()}")
                return await self._concurrent_individual_checks(applications)

        except asyncio.TimeoutError:
            self.logger.warning("RPM batch check timed out")
            return await self._concurrent_individual_checks(applications)
        except Exception as e:
            self.logger.error(f"RPM batch check failed: {str(e)}")
            return await self._concurrent_individual_checks(applications)

        return results

    async def _batch_pacman_check(self, applications: List[Application]) -> Dict[str, bool]:
        """Pacman batch check using pacman -Qq."""
        self.logger.debug("Executing Pacman batch check")
        results = {}

        try:
            config = self.pm_configs["pacman"]
            cmd = config["check_cmd"]

            self.logger.debug(f"Running Pacman batch command: {' '.join(cmd)}")

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.batch_timeout
            )

            if process.returncode == 0:
                installed_packages = set()
                for line in stdout.decode().strip().split('\n'):
                    if line.strip():
                        installed_packages.add(line.strip())

                self.logger.debug(f"Pacman batch check found {len(installed_packages)} installed packages")

                # Check each application
                for app in applications:
                    packages = app.get_package_list()
                    app_installed = all(pkg in installed_packages for pkg in packages)
                    results[app.name] = app_installed
            else:
                self.logger.warning(f"Pacman batch check failed: {stderr.decode()}")
                return await self._concurrent_individual_checks(applications)

        except asyncio.TimeoutError:
            self.logger.warning("Pacman batch check timed out")
            return await self._concurrent_individual_checks(applications)
        except Exception as e:
            self.logger.error(f"Pacman batch check failed: {str(e)}")
            return await self._concurrent_individual_checks(applications)

        return results

    async def _concurrent_individual_checks(self, applications: List[Application]) -> Dict[str, bool]:
        """Fallback: Concurrent individual package checks."""
        self.logger.debug(f"Running concurrent individual checks for {len(applications)} applications")
        results = {}

        async def check_single_app(app: Application) -> Tuple[str, bool]:
            """Check a single application."""
            try:
                packages = app.get_package_list()
                for package in packages:
                    if not await self._is_package_installed_async(package):
                        return app.name, False
                return app.name, True
            except Exception as e:
                self.logger.warning(f"Individual check failed for {app.name}: {str(e)}")
                return app.name, False

        # Run all checks concurrently
        tasks = [check_single_app(app) for app in applications]

        try:
            check_results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in check_results:
                if isinstance(result, tuple):
                    app_name, is_installed = result
                    results[app_name] = is_installed
                else:
                    # Exception occurred
                    self.logger.warning(f"Individual check exception: {result}")

        except Exception as e:
            self.logger.error(f"Concurrent individual checks failed: {str(e)}")
            # Final fallback: assume all not installed
            for app in applications:
                results[app.name] = False

        return results

    async def _is_package_installed_async(self, package: str) -> bool:
        """Async version of individual package check."""
        try:
            if self.pm_type in ["apt", "apt-get"]:
                cmd = ["dpkg", "-l", package]
            elif self.pm_type == "brew":
                # Try both formula and cask
                formula_cmd = ["brew", "list", package]
                cask_cmd = ["brew", "list", "--cask", package]

                # Check formula first
                process = await asyncio.create_subprocess_exec(
                    *formula_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.wait()
                if process.returncode == 0:
                    return True

                # Check cask if formula failed
                process = await asyncio.create_subprocess_exec(
                    *cask_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.wait()
                return process.returncode == 0

            elif self.pm_type in ["yum", "dnf"]:
                cmd = ["rpm", "-q", package]
            elif self.pm_type == "pacman":
                cmd = ["pacman", "-Q", package]
            elif self.pm_type == "zypper":
                cmd = ["rpm", "-q", package]
            elif self.pm_type == "apk":
                cmd = ["apk", "info", "-e", package]
            else:
                return False

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            await asyncio.wait_for(process.wait(), timeout=10)
            return process.returncode == 0

        except Exception:
            return False