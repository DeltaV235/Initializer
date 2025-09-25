#!/usr/bin/env python3
"""Test script to verify Node.js and Neovim detection issue."""

import sys
import asyncio
from pathlib import Path

# Add the src directory to the Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from initializer.modules.quick_verification_checker import QuickVerificationChecker, Application
from initializer.modules.batch_package_checker import BatchPackageChecker
from initializer.modules.two_layer_checker import TwoLayerPackageChecker


async def test_node_neovim_detection():
    """Test the detection of Node.js and Neovim packages."""
    print("🔍 Testing Node.js and Neovim Detection Issue")
    print("=" * 60)

    # Create test applications
    nodejs_app = Application(
        name="Node.js",
        package="nodejs npm",
        description="JavaScript runtime and package manager"
    )

    neovim_app = Application(
        name="Neovim",
        package="neovim",
        description="Terminal-based text editor"
    )

    test_apps = [nodejs_app, neovim_app]

    # Test L2 layer (Quick Verification)
    print("\n📋 Layer 2 - Quick Verification Check:")
    print("-" * 40)
    quick_checker = QuickVerificationChecker("apt")
    quick_results, unverified = quick_checker.quick_verify_applications(test_apps)

    print(f"Quick verification results: {quick_results}")
    print(f"Unverified apps: {[app.name for app in unverified]}")

    # Test L3 layer (Batch System Check)
    print("\n📋 Layer 3 - Batch System Check:")
    print("-" * 40)
    batch_checker = BatchPackageChecker("apt")
    batch_results = await batch_checker.batch_check_applications(test_apps)

    print(f"Batch check results: {batch_results}")

    # Test Two-Layer Combined Check
    print("\n📋 Two-Layer Combined Check:")
    print("-" * 40)
    two_layer = TwoLayerPackageChecker("apt")
    combined_results = await two_layer.check_applications(test_apps)

    print(f"Combined results: {combined_results}")

    # Analysis
    print("\n🔎 Analysis:")
    print("-" * 40)

    # Check for Node.js executable
    import shutil
    node_path = shutil.which("node")
    npm_path = shutil.which("npm")
    nodejs_path = shutil.which("nodejs")

    print(f"node executable: {node_path}")
    print(f"npm executable: {npm_path}")
    print(f"nodejs executable: {nodejs_path}")

    # Check for Neovim executable
    nvim_path = shutil.which("nvim")
    neovim_path = shutil.which("neovim")

    print(f"nvim executable: {nvim_path}")
    print(f"neovim executable: {neovim_path}")

    # Check apt packages
    print("\n📦 APT Package Status:")
    import subprocess
    try:
        result = subprocess.run(
            ["apt", "list", "--installed"],
            capture_output=True,
            text=True,
            timeout=5
        )
        lines = result.stdout.splitlines()
        for line in lines:
            if any(pkg in line.lower() for pkg in ["nodejs", "npm", "neovim"]):
                print(f"  Found: {line}")
    except Exception as e:
        print(f"  Error checking apt: {e}")

    print("\n🚨 Issues Found:")
    print("-" * 40)

    # Node.js issue
    if node_path and "Node.js" in combined_results and not combined_results["Node.js"]:
        print("❌ Node.js: Executable found but marked as not installed")
        print(f"   Executable: {node_path}")
        print("   Likely installed via nvm, not apt")
    elif not node_path and "Node.js" in combined_results and combined_results["Node.js"]:
        print("❌ Node.js: No executable but marked as installed")

    # Neovim issue
    if not nvim_path and "Neovim" in combined_results and combined_results["Neovim"]:
        print("❌ Neovim: No executable but marked as installed")
    elif nvim_path and "Neovim" in combined_results and not combined_results["Neovim"]:
        print("❌ Neovim: Executable found but marked as not installed")


if __name__ == "__main__":
    asyncio.run(test_node_neovim_detection())