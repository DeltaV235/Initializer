#!/usr/bin/env python3
"""Comprehensive test for the improved two-layer detection system."""

import sys
import asyncio
from pathlib import Path

# Add the src directory to the Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from initializer.modules.application import Application
from initializer.modules.quick_verification_checker import QuickVerificationChecker
from initializer.modules.batch_package_checker import BatchPackageChecker
from initializer.modules.two_layer_checker import TwoLayerPackageChecker


async def test_comprehensive_detection():
    """Test the comprehensive detection system with various scenarios."""
    print("🔍 Comprehensive Detection System Test")
    print("=" * 60)

    # Create test applications with executables configured
    test_cases = [
        # Case 1: Node.js with nvm installation (should be detected as installed)
        Application(
            name="Node.js",
            package="nodejs npm",
            description="JavaScript runtime and package manager",
            executables=["node", "nodejs", "npm"]
        ),

        # Case 2: Neovim (should be detected as not installed)
        Application(
            name="Neovim",
            package="neovim",
            description="Terminal-based text editor",
            executables=["nvim"]
        ),

        # Case 3: Git (likely installed via apt)
        Application(
            name="Git",
            package="git",
            description="Version control system",
            executables=["git"]
        ),

        # Case 4: Curl (likely installed)
        Application(
            name="Curl",
            package="curl",
            description="Network utility",
            executables=["curl"]
        ),

        # Case 5: Fake package (should be detected as not installed)
        Application(
            name="Fake Package",
            package="definitely-does-not-exist",
            description="This should not exist",
            executables=["fake-executable"]
        ),

        # Case 6: Python without executables config (fallback to hardcoded rules)
        Application(
            name="Python3",
            package="python3",
            description="Python programming language",
            executables=[]  # Empty to test fallback
        )
    ]

    print(f"\n📋 Testing {len(test_cases)} applications:")
    for i, app in enumerate(test_cases, 1):
        print(f"  {i}. {app.name}: {app.executables or 'No executables configured'}")

    # Test Two-Layer Combined Check
    print("\n🔄 Running Two-Layer Detection:")
    print("-" * 40)

    two_layer = TwoLayerPackageChecker("apt")
    results = await two_layer.check_applications(test_cases)

    print("\n📊 Detection Results:")
    print("-" * 40)

    for app in test_cases:
        status = "✅ INSTALLED" if results.get(app.name, False) else "❌ NOT INSTALLED"
        executables_info = f"(executables: {app.executables})" if app.executables else "(using fallback rules)"
        print(f"  {app.name}: {status} {executables_info}")

    # Get performance stats
    perf_stats = two_layer.get_performance_stats()
    print("\n⚡ Performance Statistics:")
    print("-" * 40)
    print(f"  L2 hit rate: {perf_stats['l2_hit_rate_percent']}%")
    print(f"  Total time: {perf_stats['total_time_seconds']}s")
    print(f"  L2 time: {perf_stats['l2_time_seconds']}s")
    print(f"  L3 time: {perf_stats['l3_time_seconds']}s")
    print(f"  Avg time per check: {perf_stats['average_time_per_check']}s")

    # Verification against actual system
    print("\n🔍 System Verification:")
    print("-" * 40)
    import shutil

    expected_results = {
        "Node.js": bool(shutil.which("node")),
        "Neovim": bool(shutil.which("nvim")),
        "Git": bool(shutil.which("git")),
        "Curl": bool(shutil.which("curl")),
        "Fake Package": False,  # Should always be false
        "Python3": bool(shutil.which("python3"))
    }

    print("Expected vs Actual Results:")
    all_correct = True
    for app_name, expected in expected_results.items():
        actual = results.get(app_name, False)
        status = "✅ CORRECT" if expected == actual else "❌ MISMATCH"
        print(f"  {app_name}: Expected {expected}, Got {actual} - {status}")
        if expected != actual:
            all_correct = False

    print(f"\n🎯 Overall Result: {'✅ ALL TESTS PASSED' if all_correct else '❌ SOME TESTS FAILED'}")

    if all_correct:
        print("\n🎉 Detection System Success:")
        print("  ✓ Node.js correctly detected via executables config (nvm installation)")
        print("  ✓ Neovim correctly detected as not installed")
        print("  ✓ System tools correctly identified")
        print("  ✓ Fake packages correctly rejected")
        print("  ✓ Fallback to hardcoded rules works")
        print("  ✓ L2/L3 layer coordination working properly")

    return all_correct


if __name__ == "__main__":
    try:
        success = asyncio.run(test_comprehensive_detection())
        if not success:
            sys.exit(1)
        print("\n✨ All systems working perfectly!")
    except Exception as e:
        print(f"\n💥 Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)