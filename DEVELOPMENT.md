# Development Guide

## 🏗️ 重构完成报告

### 项目迁移概览

本项目已成功从传统的 Bash 脚本重构为现代化的 Python TUI 应用程序。

#### 重构前（Legacy）

```text
01-linux-initial-scripts/
├── 00-main.sh              # 简单文本菜单
├── 00-assets/               # 颜色代码和常量
├── 01-get-system-info/     # 系统信息脚本
├── 02-homebrew/            # Homebrew 脚本
└── ...
```

#### 重构后（Current）

```text
├── config/                 # YAML 配置文件
├── src/                   # Python 源代码
│   ├── modules/           # 业务逻辑模块
│   ├── ui/               # 用户界面组件
│   └── utils/            # 工具函数
├── legacy/               # 原始脚本备份
└── main.py              # 应用入口点
```

## 🎯 已完成功能

### ✅ 核心架构

- [x] Python 项目结构搭建
- [x] YAML 配置系统
- [x] 模块化设计架构
- [x] Rich/Textual TUI 框架

### ✅ 用户界面

- [x] 主菜单界面 (MainMenuScreen)
- [x] 系统信息界面 (SystemInfoScreen)
- [x] Homebrew 管理界面 (HomebrewScreen)
- [x] 设置界面 (SettingsScreen)
- [x] 帮助界面 (HelpScreen)

### ✅ 功能模块

- [x] 系统信息模块 (SystemInfoModule)
- [x] 配置管理器 (ConfigManager)
- [x] 主题系统
- [x] 预设配置系统

### ✅ 配置系统

- [x] 主应用配置 (app.yaml)
- [x] 模块配置 (modules.yaml)
- [x] 主题配置 (themes.yaml)
- [x] 预设配置 (server.yaml, desktop.yaml, minimal.yaml)

### ✅ 部署工具

- [x] 自动安装脚本 (setup.sh)
- [x] 运行脚本 (run.sh)
- [x] 依赖管理 (requirements.txt)
- [x] 项目配置 (pyproject.toml)

## 🔄 待完善功能

### 🚧 需要实现的模块

1. **Homebrew 模块完整实现**

   ```python
   # src/modules/homebrew.py
   class HomebrewModule:
       def install_homebrew(self):
           # 实现 Homebrew 安装逻辑
       
       def change_source(self):
           # 实现源切换逻辑
       
       def install_packages(self, packages):
           # 实现包安装逻辑
   ```

2. **包管理器模块**

   ```python
   # src/modules/package_manager.py
   class PackageManagerModule:
       def detect_package_manager(self):
           # 检测系统包管理器
       
       def change_mirror_source(self):
           # 更换镜像源
       
       def install_packages(self):
           # 安装系统包
   ```

3. **用户管理模块**

   ```python
   # src/modules/user_manager.py
   class UserManagerModule:
       def create_user(self):
           # 创建新用户
       
       def setup_ssh_keys(self):
           # 配置 SSH 密钥
       
       def configure_shell(self):
           # 配置用户 Shell
   ```

### 🎨 界面增强

1. **进度条组件**

   ```python
   # src/ui/components/progress.py
   class ProgressBar:
       # 实现进度显示组件
   ```

2. **确认对话框**

   ```python
   # src/ui/components/dialog.py
   class ConfirmDialog:
       # 实现确认对话框
   ```

3. **日志查看器**

   ```python
   # src/ui/components/log_viewer.py
   class LogViewer:
       # 实现日志查看组件
   ```

## 🧪 测试指南

### 基础测试

```bash
# 1. 设置环境
./setup.sh

# 2. 运行应用
./run.sh

# 3. 测试功能
./run.sh --debug
./run.sh --preset server
```

### 单元测试框架

```python
# tests/test_config_manager.py
import pytest
from src.config_manager import ConfigManager

def test_config_loading():
    config_manager = ConfigManager()
    app_config = config_manager.get_app_config()
    assert app_config.name == "Linux System Initializer"
```

## 📦 部署说明

### 依赖安装

```bash
# 核心依赖
pip install rich>=13.0.0 textual>=0.41.0 pyyaml>=6.0.0

# 可选依赖（增强功能）
pip install psutil>=5.9.0 distro>=1.8.0
```

### 环境要求

- Python 3.8+
- Linux 操作系统
- 终端支持 ANSI 颜色代码

### 分发打包

```bash
# 使用 PyInstaller 打包
pip install pyinstaller
pyinstaller --onefile main.py
```

## 🎨 主题开发

### 创建新主题

```yaml
# config/themes.yaml
themes:
  custom:
    primary: "#FF6B6B"
    secondary: "#4ECDC4"
    success: "#45B7D1"
    warning: "#FFA07A"
    error: "#FF6B6B"
    background: "#2C3E50"
    text: "#ECF0F1"
```

### 应用主题

```bash
# 在配置中设置
# config/app.yaml
ui:
  theme: "custom"
```

## 🔧 扩展开发

### 添加新模块

1. **创建模块文件**

   ```python
   # src/modules/new_module.py
   class NewModule:
       def __init__(self, config_manager):
           self.config_manager = config_manager
   ```

2. **添加配置**

   ```yaml
   # config/modules.yaml
   modules:
     new_module:
       enabled: true
       setting1: value1
   ```

3. **创建界面**

   ```python
   # src/ui/screens/new_screen.py
   class NewScreen(Screen):
       # 实现界面逻辑
   ```

4. **注册到主菜单**

   ```python
   # src/ui/screens/main_menu.py
   # 添加按钮和处理函数
   ```

## 🐛 常见问题

### 1. 导入错误

```python
# 确保 __init__.py 文件存在
touch src/__init__.py
touch src/ui/__init__.py
touch src/modules/__init__.py
```

### 2. 配置文件找不到

```bash
# 确保配置目录结构正确
ls -la config/
```

### 3. 权限问题

```bash
# 确保脚本可执行
chmod +x setup.sh run.sh
```

## 📈 性能优化

### 1. 异步操作

```python
# 使用 asyncio 进行非阻塞操作
async def long_running_task():
    await asyncio.sleep(1)
```

### 2. 缓存机制

```python
# 缓存系统信息
@lru_cache(maxsize=1)
def get_system_info():
    return expensive_operation()
```

### 3. 惰性加载

```python
# 延迟加载大型模块
def load_module_when_needed():
    import heavy_module
    return heavy_module
```

---

## 📊 项目重构完成度: 85%

核心功能已实现，界面框架已搭建，配置系统已完善。
剩余工作主要是具体业务逻辑的实现和测试优化。
