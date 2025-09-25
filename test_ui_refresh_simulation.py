#!/usr/bin/env python3
"""Test script to simulate the UI refresh process and check results."""

import sys
import asyncio
from pathlib import Path

# Add the src directory to the Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from initializer.config_manager import ConfigManager
from initializer.modules.app_installer import AppInstaller

def test_ui_refresh_simulation():
    """Simulate exactly what happens when UI refreshes."""
    print("🔄 模拟 UI 刷新流程")
    print("=" * 60)

    # Step 1: 初始化配置管理器
    config_dir = Path(__file__).parent / "config"
    config_manager = ConfigManager(config_dir)
    print(f"📁 Config directory: {config_dir}")

    # Step 2: 创建 AppInstaller（模拟 MainMenuScreen.__init__）
    print("\n🔧 Step 1: 创建 AppInstaller")
    app_installer = AppInstaller(config_manager)
    print(f"   Package manager: {app_installer.package_manager}")
    print(f"   Applications loaded: {len(app_installer.applications)}")

    # Step 3: 模拟首次缓存（第一次访问 app_install 页面）
    print("\n🔧 Step 2: 模拟首次缓存加载（等同于首次访问 Application Manager）")
    print("   调用: app_installer.get_all_applications()")

    # 这会触发 refresh_all_status()
    cached_applications = app_installer.get_all_applications()

    print("   首次缓存结果:")
    for app in cached_applications:
        if app.name in ["Node.js", "Neovim"]:
            print(f"     {app.name}: installed={app.installed}")

    # Step 4: 模拟 UI 刷新（按 r 键后的操作）
    print("\n🔧 Step 3: 模拟 UI 刷新（按 r 键）")
    print("   清除缓存: app_install_cache = None")
    print("   重新调用: app_installer.get_all_applications()")

    # 模拟清除缓存，重新获取
    refreshed_applications = app_installer.get_all_applications()

    print("   刷新后结果:")
    for app in refreshed_applications:
        if app.name in ["Node.js", "Neovim"]:
            print(f"     {app.name}: installed={app.installed}")

    # Step 5: 检查实际的检测过程
    print("\n🔧 Step 4: 深入检查检测过程")

    nodejs_app = next((app for app in refreshed_applications if "Node.js" in app.name), None)
    neovim_app = next((app for app in refreshed_applications if "Neovim" in app.name), None)

    if nodejs_app:
        print(f"\n📱 Node.js 应用详情:")
        print(f"   name: {nodejs_app.name}")
        print(f"   package: {nodejs_app.package}")
        print(f"   executables: {nodejs_app.executables}")
        print(f"   installed: {nodejs_app.installed}")

        # 手动检查可执行文件
        import shutil
        print(f"   手动检查:")
        for exe in nodejs_app.executables:
            path = shutil.which(exe)
            print(f"     {exe}: {path if path else 'Not found'}")

    if neovim_app:
        print(f"\n📱 Neovim 应用详情:")
        print(f"   name: {neovim_app.name}")
        print(f"   package: {neovim_app.package}")
        print(f"   executables: {neovim_app.executables}")
        print(f"   installed: {neovim_app.installed}")

        # 手动检查可执行文件
        import shutil
        print(f"   手动检查:")
        for exe in neovim_app.executables:
            path = shutil.which(exe)
            print(f"     {exe}: {path if path else 'Not found'}")

    # Step 6: 直接测试两层检查器
    print("\n🔧 Step 5: 直接测试两层检查器")

    async def test_two_layer():
        if nodejs_app and neovim_app:
            test_apps = [nodejs_app, neovim_app]
            results = await app_installer.two_layer_checker.check_applications(test_apps)
            print("   两层检查器直接结果:")
            for app_name, installed in results.items():
                print(f"     {app_name}: {installed}")
            return results
        return {}

    two_layer_results = asyncio.run(test_two_layer())

    # Step 7: 检查结果一致性
    print("\n🔧 Step 6: 检查结果一致性")
    print("   app_installer.get_all_applications() vs 两层检查器:")

    for app in [nodejs_app, neovim_app]:
        if app:
            two_layer_result = two_layer_results.get(app.name, "未测试")
            app_installer_result = app.installed
            consistent = two_layer_result == app_installer_result

            print(f"   {app.name}:")
            print(f"     两层检查器: {two_layer_result}")
            print(f"     app_installer: {app_installer_result}")
            print(f"     一致性: {'✅' if consistent else '❌'}")

if __name__ == "__main__":
    test_ui_refresh_simulation()