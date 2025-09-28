"""Two-layer package status checker combining quick verification and batch system checking."""

import time
from typing import List, Dict, Any, Union
from ..utils.logger import get_module_logger
from .quick_verification_checker import QuickVerificationChecker
from .batch_package_checker import BatchPackageChecker
from .software_models import Application, ApplicationSuite, SoftwareItem


class TwoLayerPackageChecker:
    """Efficient two-layer package status checker using L2 (quick verification) + L3 (batch system check)."""

    def __init__(self, package_manager_type: str):
        """Initialize the two-layer checker.

        Args:
            package_manager_type: Type of package manager (apt, brew, yum, etc.)
        """
        self.pm_type = package_manager_type
        self.logger = get_module_logger("two_layer_package_checker")

        # Initialize both layers
        self.quick_checker = QuickVerificationChecker(package_manager_type)
        self.batch_checker = BatchPackageChecker(package_manager_type)

        # Performance tracking
        self.stats = {
            "total_checks": 0,
            "l2_hits": 0,
            "l3_checks": 0,
            "l2_hit_rate": 0.0,
            "total_time": 0.0,
            "l2_time": 0.0,
            "l3_time": 0.0
        }

        self.logger.info(f"TwoLayerPackageChecker initialized for {package_manager_type}")

    async def check_applications(self, applications: List[Application]) -> Dict[str, bool]:
        """Check applications using two-layer strategy.

        Flow:
        1. L2: Quick filesystem-based verification
        2. L3: Batch system-level checking for unverified apps

        Args:
            applications: List of applications to check

        Returns:
            Dictionary mapping application names to installation status
        """
        if not applications:
            return {}

        self.logger.info(f"Starting two-layer check for {len(applications)} applications")
        start_time = time.time()

        # Update stats
        self.stats["total_checks"] += len(applications)

        try:
            # Layer 2: Quick verification
            l2_start = time.time()
            quick_results, unverified_apps = self.quick_checker.quick_verify_applications(applications)
            l2_duration = time.time() - l2_start

            self.stats["l2_hits"] += len(quick_results)
            self.stats["l2_time"] += l2_duration

            self.logger.info(f"L2 quick verification: {len(quick_results)} verified, {len(unverified_apps)} need L3")

            # Layer 3: Batch system check for remaining apps
            batch_results = {}
            if unverified_apps:
                l3_start = time.time()
                batch_results = await self.batch_checker.batch_check_applications(unverified_apps)
                l3_duration = time.time() - l3_start

                self.stats["l3_checks"] += len(unverified_apps)
                self.stats["l3_time"] += l3_duration

                self.logger.info(f"L3 batch check completed for {len(unverified_apps)} applications")

            # Combine results
            final_results = {**quick_results, **batch_results}

            # Update performance stats
            total_duration = time.time() - start_time
            self.stats["total_time"] += total_duration
            self.stats["l2_hit_rate"] = (self.stats["l2_hits"] / self.stats["total_checks"]) * 100 if self.stats["total_checks"] > 0 else 0

            # Log performance summary
            self.logger.info(f"Two-layer check completed in {total_duration:.3f}s")
            self.logger.info(f"L2 hit rate: {len(quick_results)}/{len(applications)} ({(len(quick_results)/len(applications)*100):.1f}%)")

            if len(quick_results) > 0:
                self.logger.info(f"L2 average time per app: {l2_duration/len(applications):.4f}s")
            if len(unverified_apps) > 0:
                self.logger.info(f"L3 average time per app: {l3_duration/len(unverified_apps):.4f}s")

            return final_results

        except Exception as e:
            self.logger.error(f"Two-layer check failed: {str(e)}")
            # Complete fallback: use only batch checker
            self.logger.info("Falling back to L3-only mode")
            return await self.batch_checker.batch_check_applications(applications)

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics for the two-layer checker.

        Returns:
            Dictionary containing performance metrics
        """
        return {
            "total_applications_checked": self.stats["total_checks"],
            "l2_quick_verifications": self.stats["l2_hits"],
            "l3_system_checks": self.stats["l3_checks"],
            "l2_hit_rate_percent": round(self.stats["l2_hit_rate"], 1),
            "total_time_seconds": round(self.stats["total_time"], 3),
            "l2_time_seconds": round(self.stats["l2_time"], 3),
            "l3_time_seconds": round(self.stats["l3_time"], 3),
            "average_time_per_check": round(self.stats["total_time"] / max(1, self.stats["total_checks"]), 4),
            "performance_breakdown": {
                "quick_verification_percentage": round((self.stats["l2_time"] / max(0.001, self.stats["total_time"])) * 100, 1),
                "system_check_percentage": round((self.stats["l3_time"] / max(0.001, self.stats["total_time"])) * 100, 1)
            }
        }


    async def check_software_items(self, software_items: List[Union[ApplicationSuite, Application]]) -> Dict[str, bool]:
        """Check installation status for mixed software items (suites and standalone applications).

        Args:
            software_items: List of software items (mix of ApplicationSuite and Application objects)

        Returns:
            Dictionary mapping software item names to installation status
        """
        self.logger.info(f"Starting software items check for {len(software_items)} items")
        start_time = time.time()

        # Collect all applications that need to be checked
        all_applications = []
        item_to_applications = {}  # Map item name to its applications

        for item in software_items:
            if isinstance(item, ApplicationSuite):
                # For suites, collect all components
                item_to_applications[item.name] = item.components
                all_applications.extend(item.components)
            else:
                # For standalone applications
                item_to_applications[item.name] = [item]
                all_applications.append(item)

        self.logger.debug(f"Expanded {len(software_items)} software items to {len(all_applications)} applications")

        # Use the existing two-layer checking logic
        app_results = await self.check_applications(all_applications)

        # Map results back to software items
        item_results = {}

        for item in software_items:
            if isinstance(item, ApplicationSuite):
                # For suites, update component status and determine suite status
                for component in item.components:
                    component.installed = app_results.get(component.name, False)

                # Suite is considered installed if any component is installed
                # This matches the UI display logic for partial/full installation
                suite_installed = any(component.installed for component in item.components)
                item_results[item.name] = suite_installed

                # Log suite status for debugging
                installed_count = sum(1 for c in item.components if c.installed)
                total_count = len(item.components)
                self.logger.debug(f"Suite '{item.name}': {installed_count}/{total_count} components installed")

            else:
                # For standalone applications
                item.installed = app_results.get(item.name, False)
                item_results[item.name] = item.installed

        duration = time.time() - start_time
        self.logger.info(f"Software items check completed in {duration:.3f}s")

        return item_results

