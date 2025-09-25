"""Two-layer package status checker combining quick verification and batch system checking."""

import time
import asyncio
from typing import List, Dict, Tuple, Any
from dataclasses import dataclass
from ..utils.logger import get_module_logger
from .quick_verification_checker import QuickVerificationChecker
from .batch_package_checker import BatchPackageChecker


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

    def reset_stats(self) -> None:
        """Reset performance statistics."""
        self.stats = {
            "total_checks": 0,
            "l2_hits": 0,
            "l3_checks": 0,
            "l2_hit_rate": 0.0,
            "total_time": 0.0,
            "l2_time": 0.0,
            "l3_time": 0.0
        }
        self.logger.info("Performance statistics reset")

    async def analyze_verification_potential(self, applications: List[Application]) -> Dict[str, Any]:
        """Analyze how well the quick verification layer works for given applications.

        Args:
            applications: List of applications to analyze

        Returns:
            Analysis report with verification potential
        """
        self.logger.info("Analyzing quick verification potential...")

        # Get quick verification stats
        quick_stats = self.quick_checker.get_quick_verification_stats(applications)

        # Simulate a quick verification run (without actually doing system checks)
        quick_results, unverified_apps = self.quick_checker.quick_verify_applications(applications)

        analysis = {
            "total_applications": len(applications),
            "quick_verifiable": len(quick_results),
            "need_system_check": len(unverified_apps),
            "quick_verification_rate": round((len(quick_results) / len(applications)) * 100, 1) if applications else 0,
            "detailed_stats": quick_stats,
            "applications_by_verification_method": {
                "quick_verified": [app.name for app in applications if app.name in quick_results],
                "need_system_check": [app.name for app in unverified_apps]
            }
        }

        self.logger.info(f"Analysis: {analysis['quick_verification_rate']}% can be quickly verified")
        return analysis

    def configure_quick_verification(self, custom_rules: Dict[str, List[str]] = None,
                                   custom_paths: Dict[str, List[str]] = None) -> None:
        """Configure custom rules for quick verification.

        Args:
            custom_rules: Custom package detection rules {package_name: [alternative_names]}
            custom_paths: Custom path templates {pm_type: [path_templates]}
        """
        if custom_rules:
            self.quick_checker.special_detection_rules.update(custom_rules)
            self.logger.info(f"Added {len(custom_rules)} custom detection rules")

        if custom_paths:
            for pm_type, paths in custom_paths.items():
                if pm_type in self.quick_checker.common_paths:
                    self.quick_checker.common_paths[pm_type].extend(paths)
                else:
                    self.quick_checker.common_paths[pm_type] = paths
            self.logger.info(f"Added custom paths for {len(custom_paths)} package managers")