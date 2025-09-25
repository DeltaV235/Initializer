#!/usr/bin/env python3
"""Test script for BatchPackageChecker functionality."""

import sys
import time
import asyncio
from pathlib import Path

# Add the src directory to the Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

try:
    from initializer.modules.batch_package_checker import BatchPackageChecker, Application
except ImportError as e:
    print(f"❌ Import error: {e}")
    print(f"   Current working directory: {Path.cwd()}")
    print(f"   Src path: {src_path}")
    print(f"   Src path exists: {src_path.exists()}")
    if src_path.exists():
        print(f"   Src contents: {list(src_path.iterdir())}")
    sys.exit(1)


def create_test_applications() -> list:
    """Create a list of test applications for checking."""
    test_apps = [
        Application(name="Python3", package="python3", description="Python 3 interpreter"),
        Application(name="Git", package="git", description="Version control system"),
        Application(name="Curl", package="curl", description="Command line HTTP client"),
        Application(name="Vim", package="vim", description="Vi improved text editor"),
        Application(name="Htop", package="htop", description="Interactive process viewer"),
        Application(name="Nonexistent", package="this-package-definitely-does-not-exist", description="Test package that should not be installed"),
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


async def test_batch_checker():
    """Test the BatchPackageChecker functionality."""
    print("🚀 Testing BatchPackageChecker...")
    print("=" * 60)

    # Detect package manager
    pm_type = detect_package_manager()
    print(f"📦 Detected package manager: {pm_type}")

    if pm_type == "unknown":
        print("❌ No supported package manager found!")
        return False

    # Create batch checker
    checker = BatchPackageChecker(pm_type)

    # Create test applications
    test_apps = create_test_applications()
    print(f"🧪 Testing with {len(test_apps)} applications:")
    for app in test_apps:
        print(f"   • {app.name} ({app.package})")

    print("\n🔍 Starting batch check...")
    start_time = time.time()

    try:
        # Run batch check
        results = await checker.batch_check_applications(test_apps)

        duration = time.time() - start_time
        print(f"⚡ Batch check completed in {duration:.2f} seconds")

        # Display results
        print("\n📊 Results:")
        installed_count = 0
        for app_name, is_installed in results.items():
            status = "✅ INSTALLED" if is_installed else "❌ NOT INSTALLED"
            print(f"   {app_name}: {status}")
            if is_installed:
                installed_count += 1

        print(f"\n📈 Summary: {installed_count}/{len(test_apps)} applications installed")

        # Validate expected results
        print("\n🧐 Validation:")
        expected_nonexistent = results.get("Nonexistent", True)  # Should be False
        if not expected_nonexistent:
            print("   ✅ Correctly identified non-existent package as not installed")
        else:
            print("   ❌ ERROR: Non-existent package reported as installed!")
            return False

        # At least some common packages should be available on most systems
        common_packages = ["Python3", "Git", "Curl"]
        found_any = any(results.get(pkg, False) for pkg in common_packages)
        if found_any:
            print("   ✅ At least one common package detected as installed")
        else:
            print("   ⚠️  WARNING: No common packages found (this might be expected on minimal systems)")

        return True

    except Exception as e:
        print(f"❌ Batch check failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_individual_vs_batch_performance():
    """Compare individual vs batch checking performance."""
    print("\n🏎️  Performance Comparison Test")
    print("=" * 60)

    pm_type = detect_package_manager()
    if pm_type == "unknown":
        print("❌ No package manager found for performance test")
        return

    checker = BatchPackageChecker(pm_type)
    test_apps = create_test_applications()

    # Test batch checking
    print("🚀 Testing batch checking...")
    start_time = time.time()
    batch_results = await checker.batch_check_applications(test_apps)
    batch_duration = time.time() - start_time

    # Test individual checking (simulation)
    print("🐌 Testing individual checking simulation...")
    start_time = time.time()
    individual_results = {}
    for app in test_apps:
        # Simulate individual check by calling batch with single app
        single_result = await checker.batch_check_applications([app])
        individual_results.update(single_result)
    individual_duration = time.time() - start_time

    # Compare results
    print(f"\n📊 Performance Results:")
    print(f"   Batch checking: {batch_duration:.2f} seconds")
    print(f"   Individual checking: {individual_duration:.2f} seconds")

    if individual_duration > 0:
        speedup = individual_duration / batch_duration
        print(f"   🏆 Batch is {speedup:.1f}x faster!")
    else:
        print("   ⚡ Both methods were too fast to measure accurately")

    # Verify results are identical
    if batch_results == individual_results:
        print("   ✅ Results are identical between batch and individual methods")
    else:
        print("   ❌ Results differ between methods:")
        print(f"      Batch: {batch_results}")
        print(f"      Individual: {individual_results}")


async def main():
    """Run all tests."""
    print("🧪 BatchPackageChecker Test Suite")
    print("=" * 60)

    success = True

    # Test basic functionality
    if not await test_batch_checker():
        success = False

    # Test performance comparison
    await test_individual_vs_batch_performance()

    print("\n" + "=" * 60)
    if success:
        print("🎉 All tests passed! BatchPackageChecker is working correctly.")
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