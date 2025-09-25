#!/usr/bin/env python3
"""Debug script to show what's actually stored in UI cache."""

import sys
from pathlib import Path

# Add the src directory to the Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from initializer.config_manager import ConfigManager
from initializer.modules.app_installer import AppInstaller

def show_cache_contents():
    """Show what would be stored in UI cache."""
    print("🔍 UI 缓存内容示例")
    print("=" * 60)

    config_dir = Path(__file__).parent / "config"
    config_manager = ConfigManager(config_dir)
    app_installer = AppInstaller(config_manager)

    print("📋 app_install_cache 实际内容类型:")
    applications = app_installer.get_all_applications()

    print(f"   类型: {type(applications)}")
    print(f"   长度: {len(applications)} 个应用")
    print(f"   内存地址: {id(applications)}")

    print("\n📊 缓存中具体的数据结构:")
    for i, app in enumerate(applications[:3], 1):
        print(f"   应用 {i}: {type(app).__name__}")
        print(f"     - name: {repr(app.name)}")
        print(f"     - package: {repr(app.package)}")
        print(f"     - executables: {repr(app.executables)}")
        print(f"     - installed: {repr(app.installed)}")
        print(f"     - description: {repr(app.description[:50])}...")
        print(f"     - 内存地址: {id(app)}")
        print()

    print("🧠 reactive 属性如何工作:")
    print("   - reactive(None) 创建一个响应式属性")
    print("   - 当值改变时，自动触发 UI 重绘")
    print("   - 存储在 MainMenuScreen 实例的 __dict__ 中")
    print("   - 应用退出时随对象销毁")

    print("\n💾 缓存存储位置:")
    print("   📍 物理位置: 系统 RAM")
    print("   📍 逻辑位置: MainMenuScreen 实例属性")
    print("   📍 作用域: 单个应用实例生命周期")
    print("   📍 持久化: 否（重启丢失）")

    print("\n⚡ 性能影响:")
    import sys
    print(f"   缓存对象大小: ~{sys.getsizeof(applications)} 字节")
    print("   避免重复系统调用（apt list --installed）")
    print("   首次加载: ~0.5-2秒")
    print("   缓存访问: <0.001秒")

if __name__ == "__main__":
    show_cache_contents()