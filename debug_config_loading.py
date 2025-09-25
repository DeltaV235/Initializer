#!/usr/bin/env python3
"""Debug script to check what configuration is actually being loaded by the app."""

import sys
from pathlib import Path
import yaml

# Add the src directory to the Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from initializer.config_manager import ConfigManager
from initializer.modules.app_installer import AppInstaller


def debug_configuration_loading():
    """Debug what configuration is actually being loaded."""
    print("🔍 Debugging Configuration Loading")
    print("=" * 60)

    # Initialize config manager
    config_dir = Path(__file__).parent / "config"
    config_manager = ConfigManager(config_dir)

    print(f"📁 Config directory: {config_dir}")
    print(f"📁 Directory exists: {config_dir.exists()}")

    # Check if applications_apt.yaml exists and its content
    apt_config_path = config_dir / "applications_apt.yaml"
    print(f"\n📄 APT Config file: {apt_config_path}")
    print(f"📄 File exists: {apt_config_path.exists()}")

    if apt_config_path.exists():
        with open(apt_config_path, 'r', encoding='utf-8') as f:
            apt_config = yaml.safe_load(f)

        print("\n📋 First few applications in APT config:")
        applications = apt_config.get("applications", [])
        for i, app in enumerate(applications[:3], 1):
            print(f"  {i}. {app.get('name', 'Unknown')}")
            print(f"     package: {app.get('package', 'None')}")
            print(f"     executables: {app.get('executables', 'None')}")
            print()

    # Initialize AppInstaller and check what it loads
    print("🔧 Initializing AppInstaller...")
    try:
        app_installer = AppInstaller(config_manager)

        print(f"📦 Package manager detected: {app_installer.package_manager}")
        print(f"📋 Total applications loaded: {len(app_installer.applications)}")

        print("\n📋 First few loaded applications:")
        for i, app in enumerate(app_installer.applications[:5], 1):
            print(f"  {i}. {app.name}")
            print(f"     package: {app.package}")
            print(f"     executables: {app.executables}")
            print(f"     installed: {app.installed}")
            print()

        # Specifically check Node.js and Neovim
        nodejs_app = next((app for app in app_installer.applications if "Node.js" in app.name), None)
        neovim_app = next((app for app in app_installer.applications if "Neovim" in app.name), None)

        if nodejs_app:
            print(f"🟢 Found Node.js application:")
            print(f"   name: {nodejs_app.name}")
            print(f"   package: {nodejs_app.package}")
            print(f"   executables: {nodejs_app.executables}")
            print(f"   installed: {nodejs_app.installed}")
        else:
            print("🔴 Node.js application not found!")

        if neovim_app:
            print(f"\n🟢 Found Neovim application:")
            print(f"   name: {neovim_app.name}")
            print(f"   package: {neovim_app.package}")
            print(f"   executables: {neovim_app.executables}")
            print(f"   installed: {neovim_app.installed}")
        else:
            print("🔴 Neovim application not found!")

        # Test the refresh functionality
        print("\n🔄 Testing status refresh...")
        app_installer.refresh_all_status()

        print("📊 After refresh:")
        if nodejs_app:
            print(f"   Node.js installed: {nodejs_app.installed}")
        if neovim_app:
            print(f"   Neovim installed: {neovim_app.installed}")

    except Exception as e:
        print(f"❌ Error initializing AppInstaller: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    debug_configuration_loading()