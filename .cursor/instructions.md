# Linux System Initializer - Cursor AI 指令

## 🎯 项目概述
这是一个 Linux 系统自动化初始化工具，使用现代 Python 技术栈构建：
- **UI**: Rich + Textual (终端用户界面)
- **配置**: YAML 驱动的模块化设计
- **架构**: 现代 Python 项目 (pyproject.toml)

## 🚨 关键执行规则
**此项目严格要求远端执行！所有脚本必须在远端服务器 192.168.0.33 上运行。**

### 禁止本地执行
- ❌ ./setup.sh
- ❌ ./run.sh  
- ❌ python main.py
- ❌ 创建本地虚拟环境

### 正确工作流程
```bash
# 1. 同步代码
rsync -avz --exclude='venv/' --exclude='initializer-venv/' ./ root@192.168.0.33:~/Initializer/

# 2. 远端执行
ssh root@192.168.0.33
cd ~/Initializer
./setup.sh
./run.sh
```

## 📁 项目结构
```
src/              # Python 源代码 (本地编辑)
  ├── app.py      # 主应用类
  ├── config_manager.py  # 配置管理
  └── modules/    # 功能模块
config/           # YAML 配置文件 (本地编辑)
  ├── app.yaml    # 应用配置
  └── presets/    # 预设配置
legacy/           # 原始 Bash 脚本 (参考)
setup.sh          # 安装脚本 (仅远端执行)
run.sh            # 启动脚本 (仅远端执行)
main.py           # 程序入口 (仅远端执行)
```

## ⚙️ 技术配置
- **Python 版本**: 3.8+
- **虚拟环境**: `initializer-venv` (不是 venv)
- **远端服务器**: 192.168.0.33
- **包管理**: pyproject.toml (支持 pip install -e .)

## 🔧 依赖管理
- **核心依赖**: rich, textual, pyyaml, click, psutil, distro
- **开发依赖**: pytest, black, flake8, mypy
- **安装方式**: `pip install -e .` 和 `pip install -e .[dev]`

## 📚 文档参考
- **主规则**: `.cursorrules` (Cursor 自动读取)
- **项目说明**: `README.md`
- **开发指南**: `DEVELOPMENT.md`

## 🎨 用户界面特性
- TUI (Terminal User Interface) 应用
- 模块化配置系统
- 预设支持 (server, desktop, minimal)
- 实时系统信息显示
- 彩色主题支持

## 💡 AI 助手行为准则
1. **代码编辑**: 可以建议本地编辑源文件
2. **脚本执行**: 必须引导到远端服务器
3. **依赖安装**: 必须在远端进行
4. **测试验证**: 必须在远端环境
5. **规则提醒**: 始终强调远端执行要求