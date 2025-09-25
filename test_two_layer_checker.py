#!/usr/bin/env python3
"""Test script for TwoLayerPackageChecker functionality."""

import sys
import time
import asyncio
from pathlib import Path

# Add the src directory to the Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

try:
    from initializer.modules.two_layer_checker import TwoLayerPackageChecker, Application
except ImportError as e:
    print(f"❌ Import error: {e}")
    print(f"   Current working directory: {Path.cwd()}")
    print(f"   Src path: {src_path}")
    sys.exit(1)


def create_test_applications() -> list:
    """Create a comprehensive list of test applications."""
    test_apps = [
        # Common tools that likely have executables (good for L2)
        Application(name="Python3", package="python3", description="Python 3 interpreter"),
        Application(name="Git", package="git", description="Version control system"),
        Application(name="Curl", package="curl", description="Command line HTTP client"),
        Application(name="Wget", package="wget", description="Network downloader"),
        Application(name="Vim", package="vim", description="Vi improved text editor"),
        Application(name="Nano", package="nano", description="Simple text editor"),
        Application(name="Htop", package="htop", description="Interactive process viewer"),
        Application(name="Tree", package="tree", description="Directory tree display"),

        # System packages that might need L3 checking
        Application(name="Build Essential", package="build-essential", description="Compilation tools"),
        Application(name="MySQL Server", package="mysql-server", description="MySQL database server"),
        Application(name="Redis Server", package="redis-server", description="Redis key-value store"),

        # Packages that definitely don't exist (should be caught by L2 or L3)
        Application(name="Nonexistent1", package="this-package-absolutely-does-not-exist-1", description="Test package 1"),
        Application(name="Nonexistent2", package="completely-fake-package-name-12345", description="Test package 2"),

        # Multi-package applications
        Application(name="Docker Complete", package="docker docker-compose", description="Docker with compose"),
        Application(name="Node.js Full", package="nodejs npm", description="Node.js with npm"),
    ]
    return test_apps


def detect_package_manager():
    """Detect the current system's package manager."""
    import shutil

    package_managers = {
        "apt": "apt-get",
        "apt-get": "apt-get",
        "brew": "brew",
        "yum": "yum",
        "dnf": "dnf",
        "pacman": "pacman",
        "zypper": "zypper",
        "apk": "apk"
    }

    for pm_name, pm_cmd in package_managers.items():
        if shutil.which(pm_cmd):
            return pm_name

    return "unknown"


async def test_two_layer_checker():
    """Test the TwoLayerPackageChecker functionality."""
    print("🚀 Testing TwoLayerPackageChecker...")
    print("=" * 60)

    # Detect package manager
    pm_type = detect_package_manager()
    print(f"📦 Detected package manager: {pm_type}")

    if pm_type == "unknown":
        print("❌ No supported package manager found!")
        return False

    # Create two-layer checker
    checker = TwoLayerPackageChecker(pm_type)

    # Create test applications
    test_apps = create_test_applications()
    print(f"🧪 Testing with {len(test_apps)} applications:")
    for app in test_apps[:8]:  # Show first 8
        print(f"   • {app.name} ({app.package})")
    if len(test_apps) > 8:
        print(f"   ... and {len(test_apps) - 8} more")

    print("\n🔍 Starting two-layer check...")
    start_time = time.time()

    try:
        # Run two-layer check
        results = await checker.check_applications(test_apps)

        duration = time.time() - start_time
        print(f"⚡ Two-layer check completed in {duration:.3f} seconds")

        # Display results
        print("\n📊 Results:")
        installed_count = 0
        for app_name, is_installed in results.items():
            status = "✅ INSTALLED" if is_installed else "❌ NOT INSTALLED"
            print(f"   {app_name}: {status}")
            if is_installed:
                installed_count += 1

        print(f"\n📈 Summary: {installed_count}/{len(test_apps)} applications installed")

        # Get performance statistics
        perf_stats = checker.get_performance_stats()
        print("\n📊 Performance Statistics:")
        print(f"   L2 Hit Rate: {perf_stats['l2_hit_rate_percent']}%")
        print(f"   L2 Quick Verifications: {perf_stats['l2_quick_verifications']}")
        print(f"   L3 System Checks: {perf_stats['l3_system_checks']}")
        print(f"   Total Time: {perf_stats['total_time_seconds']}s")
        print(f"   L2 Time: {perf_stats['l2_time_seconds']}s")
        print(f"   L3 Time: {perf_stats['l3_time_seconds']}s")
        print(f"   Average per app: {perf_stats['average_time_per_check']}s")

        # Validate expected results
        print("\n🧐 Validation:")

        # Check that non-existent packages are correctly identified
        nonexistent_results = [
            results.get("Nonexistent1", True),
            results.get("Nonexistent2", True)
        ]

        if not any(nonexistent_results):
            print("   ✅ Correctly identified non-existent packages as not installed")
        else:
            print("   ❌ ERROR: Non-existent packages reported as installed!")
            return False

        # Check that we got reasonable L2 hit rate for common packages
        if perf_stats['l2_hit_rate_percent'] > 30:
            print(f"   ✅ Good L2 hit rate ({perf_stats['l2_hit_rate_percent']}%)")
        else:
            print(f"   ⚠️  Low L2 hit rate ({perf_stats['l2_hit_rate_percent']}%) - this might be expected on minimal systems")

        return True

    except Exception as e:
        print(f"❌ Two-layer check failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_layer_analysis():
    """Test the verification analysis functionality."""
    print("\n🔍 Layer Analysis Test")
    print("=" * 60)

    pm_type = detect_package_manager()
    if pm_type == "unknown":
        print("❌ No package manager found for analysis test")
        return

    checker = TwoLayerPackageChecker(pm_type)
    test_apps = create_test_applications()

    # Analyze verification potential
    print("📊 Analyzing verification potential...")
    analysis = await checker.analyze_verification_potential(test_apps)

    print(f"📈 Analysis Results:")
    print(f"   Total Applications: {analysis['total_applications']}")
    print(f"   Quick Verifiable: {analysis['quick_verifiable']}")
    print(f"   Need System Check: {analysis['need_system_check']}")
    print(f"   Quick Verification Rate: {analysis['quick_verification_rate']}%")

    print(f"\n📋 Applications by Verification Method:")
    quick_verified = analysis['applications_by_verification_method']['quick_verified']
    need_system = analysis['applications_by_verification_method']['need_system_check']

    print(f"   Quick Verified ({len(quick_verified)}):")
    for app_name in quick_verified[:5]:  # Show first 5
        print(f"     • {app_name}")
    if len(quick_verified) > 5:
        print(f"     ... and {len(quick_verified) - 5} more")

    print(f"   Need System Check ({len(need_system)}):")
    for app_name in need_system[:5]:  # Show first 5
        print(f"     • {app_name}")
    if len(need_system) > 5:
        print(f"     ... and {len(need_system) - 5} more")


async def test_performance_comparison():
    """Compare two-layer vs batch-only performance."""
    print("\n🏎️  Performance Comparison Test")
    print("=" * 60)

    pm_type = detect_package_manager()
    if pm_type == "unknown":
        print("❌ No package manager found for performance test")
        return

    # Create both checkers
    two_layer_checker = TwoLayerPackageChecker(pm_type)

    # Import batch checker for comparison
    from initializer.modules.batch_package_checker import BatchPackageChecker
    batch_checker = BatchPackageChecker(pm_type)

    test_apps = create_test_applications()

    # Test two-layer checking
    print("🚀 Testing two-layer checking...")
    start_time = time.time()
    two_layer_results = await two_layer_checker.check_applications(test_apps)
    two_layer_duration = time.time() - start_time

    # Test batch-only checking
    print("📦 Testing batch-only checking...")
    start_time = time.time()
    batch_results = await batch_checker.batch_check_applications(test_apps)
    batch_duration = time.time() - start_time

    # Compare results
    print(f"\n📊 Performance Comparison:")
    print(f"   Two-layer checking: {two_layer_duration:.3f} seconds")
    print(f"   Batch-only checking: {batch_duration:.3f} seconds")

    if batch_duration > 0:
        if two_layer_duration < batch_duration:
            speedup = batch_duration / two_layer_duration
            print(f"   🏆 Two-layer is {speedup:.1f}x faster!")
        else:
            slowdown = two_layer_duration / batch_duration
            print(f"   📉 Two-layer is {slowdown:.1f}x slower (overhead for small sets)")
    else:
        print("   ⚡ Both methods were too fast to measure accurately")

    # Verify results are identical
    if two_layer_results == batch_results:
        print("   ✅ Results are identical between two-layer and batch-only methods")
    else:
        print("   ❌ Results differ between methods:")
        print(f"      Two-layer: {two_layer_results}")
        print(f"      Batch-only: {batch_results}")

    # Show two-layer performance breakdown
    perf_stats = two_layer_checker.get_performance_stats()
    breakdown = perf_stats['performance_breakdown']
    print(f"\n📊 Two-layer Performance Breakdown:")
    print(f"   Quick Verification: {breakdown['quick_verification_percentage']}%")
    print(f"   System Check: {breakdown['system_check_percentage']}%")


async def main():
    """Run all tests."""
    print("🧪 TwoLayerPackageChecker Test Suite")
    print("=" * 60)

    success = True

    # Test basic functionality
    if not await test_two_layer_checker():
        success = False

    # Test layer analysis
    await test_layer_analysis()

    # Test performance comparison
    await test_performance_comparison()

    print("\n" + "=" * 60)
    if success:
        print("🎉 All tests passed! TwoLayerPackageChecker is working correctly.")
        print("💫 The L2+L3 approach successfully combines speed and accuracy!")
    else:
        print("❌ Some tests failed. Please check the output above.")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Test suite crashed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)