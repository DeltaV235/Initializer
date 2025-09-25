#!/usr/bin/env python3
"""Test script for auto_yes parameter functionality."""

import sys
import tempfile
import shutil
from pathlib import Path

# Add the src directory to the Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

try:
    from initializer.modules.app_installer import AppInstaller, Application
    from initializer.config_manager import ConfigManager
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


def create_test_config_with_auto_yes(auto_yes_value: bool):
    """Create a test configuration with specified auto_yes value."""
    # Create temporary directory for test config
    temp_dir = Path(tempfile.mkdtemp(prefix="auto_yes_test_"))
    config_dir = temp_dir / "config"
    config_dir.mkdir()

    # Create applications_apt.yaml with auto_yes setting
    apt_config = {
        "apt_config": {
            "auto_yes": auto_yes_value,
            "install_recommends": True,
            "install_suggests": False,
            "verbose": False
        },
        "applications": [
            {
                "name": "Test Package",
                "package": "curl",
                "description": "Test package for auto_yes"
            }
        ]
    }

    # Write APT config
    import yaml
    with open(config_dir / "applications_apt.yaml", 'w') as f:
        yaml.dump(apt_config, f)

    # Create basic modules.yaml
    modules_config = {
        "modules": {
            "app_install": {
                "applications": [
                    {
                        "name": "Test Package",
                        "package": "curl",
                        "description": "Test package"
                    }
                ]
            }
        }
    }

    with open(config_dir / "modules.yaml", 'w') as f:
        yaml.dump(modules_config, f)

    # Create app.yaml (basic config)
    app_config = {"app": {"name": "Test Initializer"}}
    with open(config_dir / "app.yaml", 'w') as f:
        yaml.dump(app_config, f)

    return temp_dir


def test_auto_yes_functionality():
    """Test the auto_yes parameter functionality."""
    print("🔧 Testing auto_yes Parameter Functionality")
    print("=" * 60)

    test_results = []

    # Test case 1: auto_yes = true
    print("🧪 Test Case 1: auto_yes = true")
    test_dir_true = create_test_config_with_auto_yes(True)
    config_dir_true = test_dir_true / "config"

    try:
        config_manager = ConfigManager(config_dir_true)
        app_installer = AppInstaller(config_manager)

        test_app = Application(name="Test Package", package="curl", description="Test")

        install_cmd = app_installer.get_install_command(test_app)
        uninstall_cmd = app_installer.get_uninstall_command(test_app)

        print(f"   Install command: {install_cmd}")
        print(f"   Uninstall command: {uninstall_cmd}")

        # Verify that -y is present
        if "-y" in install_cmd and "-y" in uninstall_cmd:
            print("   ✅ auto_yes=true: Commands correctly include -y parameter")
            test_results.append(("auto_yes=true", True))
        else:
            print("   ❌ auto_yes=true: Commands missing -y parameter")
            test_results.append(("auto_yes=true", False))

    except Exception as e:
        print(f"   ❌ auto_yes=true test failed: {str(e)}")
        test_results.append(("auto_yes=true", False))
    finally:
        shutil.rmtree(test_dir_true)

    print()

    # Test case 2: auto_yes = false
    print("🧪 Test Case 2: auto_yes = false")
    test_dir_false = create_test_config_with_auto_yes(False)
    config_dir_false = test_dir_false / "config"

    try:
        config_manager = ConfigManager(config_dir_false)
        app_installer = AppInstaller(config_manager)

        test_app = Application(name="Test Package", package="curl", description="Test")

        install_cmd = app_installer.get_install_command(test_app)
        uninstall_cmd = app_installer.get_uninstall_command(test_app)

        print(f"   Install command: {install_cmd}")
        print(f"   Uninstall command: {uninstall_cmd}")

        # Verify that -y is NOT present
        if "-y" not in install_cmd and "-y" not in uninstall_cmd:
            print("   ✅ auto_yes=false: Commands correctly exclude -y parameter")
            test_results.append(("auto_yes=false", True))
        else:
            print("   ❌ auto_yes=false: Commands incorrectly include -y parameter")
            test_results.append(("auto_yes=false", False))

    except Exception as e:
        print(f"   ❌ auto_yes=false test failed: {str(e)}")
        test_results.append(("auto_yes=false", False))
    finally:
        shutil.rmtree(test_dir_false)

    print()

    # Test case 3: Test other package managers
    print("🧪 Test Case 3: Other package managers")
    test_dir_other = create_test_config_with_auto_yes(False)
    config_dir_other = test_dir_other / "config"

    try:
        config_manager = ConfigManager(config_dir_other)
        app_installer = AppInstaller(config_manager)

        # Override package manager for testing
        original_pm = app_installer.package_manager

        # Test different package managers
        test_package_managers = ["yum", "dnf", "pacman", "zypper"]

        for pm in test_package_managers:
            app_installer.package_manager = pm

            # Create a fake config file for this package manager to ensure auto_yes=false is read
            pm_config_file = config_dir_other / f"applications_{pm}.yaml"
            pm_config = {
                f"{pm}_config": {
                    "auto_yes": False
                },
                "applications": []
            }

            import yaml
            with open(pm_config_file, 'w') as f:
                yaml.dump(pm_config, f)

            test_app = Application(name="Test Package", package="test-pkg", description="Test")
            install_cmd = app_installer.get_install_command(test_app)

            print(f"   {pm} install command: {install_cmd}")

            # Check appropriate no-confirm flags
            expected_flags = {
                "yum": "-y" not in install_cmd,
                "dnf": "-y" not in install_cmd,
                "pacman": "--noconfirm" not in install_cmd,
                "zypper": "-y" not in install_cmd
            }

            if expected_flags[pm]:
                print(f"   ✅ {pm}: Correctly excludes auto-confirm flag")
                test_results.append((f"{pm} auto_yes=false", True))
            else:
                print(f"   ❌ {pm}: Incorrectly includes auto-confirm flag")
                test_results.append((f"{pm} auto_yes=false", False))

        # Restore original package manager
        app_installer.package_manager = original_pm

    except Exception as e:
        print(f"   ❌ Other package managers test failed: {str(e)}")
        test_results.append(("other_pm", False))
    finally:
        shutil.rmtree(test_dir_other)

    return test_results


def test_apt_config_integration():
    """Test APT config parameter integration."""
    print("\n🔧 Testing APT Config Integration")
    print("=" * 60)

    test_dir = create_test_config_with_auto_yes(True)
    config_dir = test_dir / "config"

    # Update config to include install_recommends and install_suggests
    apt_config_path = config_dir / "applications_apt.yaml"

    import yaml
    with open(apt_config_path, 'r') as f:
        config = yaml.safe_load(f)

    config["apt_config"].update({
        "install_recommends": False,
        "install_suggests": True
    })

    with open(apt_config_path, 'w') as f:
        yaml.dump(config, f)

    try:
        config_manager = ConfigManager(config_dir)
        app_installer = AppInstaller(config_manager)

        test_app = Application(name="Test Package", package="vim", description="Test")
        install_cmd = app_installer.get_install_command(test_app)

        print(f"📋 Generated install command: {install_cmd}")

        # Verify all parameters are present
        expected_params = ["-y", "--no-install-recommends", "--install-suggests"]
        all_present = all(param in install_cmd for param in expected_params)

        if all_present:
            print("✅ All APT config parameters correctly applied")
            print("   ✓ auto_yes=true → -y included")
            print("   ✓ install_recommends=false → --no-install-recommends included")
            print("   ✓ install_suggests=true → --install-suggests included")
            return True
        else:
            print("❌ Some APT config parameters missing")
            for param in expected_params:
                if param in install_cmd:
                    print(f"   ✓ {param} found")
                else:
                    print(f"   ❌ {param} missing")
            return False

    except Exception as e:
        print(f"❌ APT config integration test failed: {str(e)}")
        return False
    finally:
        shutil.rmtree(test_dir)


def main():
    """Run all auto_yes functionality tests."""
    print("🧪 auto_yes Parameter Test Suite")
    print("=" * 60)
    print("Testing implementation of auto_yes configuration parameter")
    print("")

    success = True

    # Test basic auto_yes functionality
    test_results = test_auto_yes_functionality()

    # Test APT config integration
    apt_config_success = test_apt_config_integration()

    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Results Summary:")

    passed_tests = sum(1 for _, result in test_results if result)
    total_tests = len(test_results)

    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name}: {status}")

    apt_status = "✅ PASS" if apt_config_success else "❌ FAIL"
    print(f"   APT config integration: {apt_status}")

    if passed_tests == total_tests and apt_config_success:
        print("\n🎉 ALL TESTS PASSED!")
        print("\n✨ auto_yes Parameter Implementation Success:")
        print("   🔧 auto_yes=true → Adds -y/--noconfirm to commands")
        print("   🔧 auto_yes=false → Removes auto-confirmation flags")
        print("   🔧 Works with all supported package managers")
        print("   🔧 Integrates with install_recommends and install_suggests")
        print("   🔧 Properly loads from applications_apt.yaml config")
    else:
        print(f"\n❌ SOME TESTS FAILED: {passed_tests}/{total_tests} basic tests passed")
        print("Please check the implementation and fix any issues.")
        success = False

    return success


if __name__ == "__main__":
    try:
        success = main()
        if not success:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Test suite crashed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)