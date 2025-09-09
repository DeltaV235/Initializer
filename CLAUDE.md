# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Communication Language
- **Primary Language**: Respond in Chinese (中文) for all interactions
- **Technical Terms**: Keep technical terms, programming keywords, and proper nouns in English
- **Code Comments**: Follow existing code comment language conventions in the project

## Development Philosophy
- **Simplicity First**: Use simple, straightforward implementations over complex designs
- **Avoid Over-engineering**: Implement only what is needed, avoid premature optimization
- **Readability**: Prefer clear, readable code over clever solutions

## Project Overview

Linux System Initializer is a modern Terminal User Interface (TUI) application for Linux system initialization and configuration. The project has been refactored from legacy bash scripts to a Python-based TUI using Rich/Textual framework.

## UI/UX Design Philosophy

**Keyboard-First Operation**: The entire project is designed primarily for keyboard operation. The basic logic uses arrows (▶) to indicate the current cursor position, and blue borders to show which panel currently has focus. The interface adopts a CLI-style graphical interface rather than modern UI elements, maintaining a terminal-native feel that experienced system administrators would find familiar and efficient.

## Development Commands

### Installation & Setup
```bash
# Install with all dependencies
./install.sh

# Install with development dependencies
./install.sh --dev

# Install in auto-confirm mode (non-interactive)
./install.sh --auto-confirm
```

### Running the Application
```bash
# Primary run method
./run.sh

# Direct execution
python main.py

# With command-line tool (after installation)
initializer

# With options
./run.sh --preset server
./run.sh --debug
./run.sh --headless
```

### Development Tools (when installed with --dev)
```bash
# Code formatting
black src/

# Linting
flake8 src/

# Type checking
mypy src/

# Testing
pytest
```

### Tools Directory
```bash
# Environment detection for Claude execution strategy
tools/check-test-environment.sh

# Remote deployment and synchronization  
tools/sync-to-remote.sh
```

## Architecture

### Project Structure
- `src/initializer/` - Main Python package (20 files total)
  - `app.py` - Main TUI application class
  - `config_manager.py` - YAML configuration management
  - `ui/screens/` - Screen components (9 screens including modals)
    - `main_menu.py` - Primary navigation interface
    - `system_info.py` - Hardware/software information display
    - `package_manager.py` - Package manager detection and configuration
    - `homebrew.py` - Homebrew installation and management
    - `settings.py` - Application settings interface
    - `help.py` - Help and documentation screen
    - `source_selection_modal.py` - Mirror source selection dialog
    - `mirror_confirmation_modal.py` - Source change confirmation dialog
  - `modules/` - Business logic modules
    - `system_info.py` - System information gathering
    - `package_manager.py` - Package manager detection and operations
  - `utils/` - Utility functions
- `config/` - YAML configuration files
  - `app.yaml` - Main application settings
  - `modules.yaml` - Module-specific configuration
  - `themes.yaml` - UI themes and colors
  - `presets/` - Predefined configuration templates
- `tools/` - Development and deployment tools
  - `check-test-environment.sh` - Environment detection for Claude execution
  - `sync-to-remote.sh` - Remote deployment synchronization
- `legacy/` - Original bash scripts (preserved for reference)
- `main.py` - Application entry point

### Key Technologies
- **Rich/Textual**: Terminal UI framework
- **PyYAML**: Configuration file handling
- **Click**: Command-line interface
- **psutil**: System information gathering
- **distro**: Linux distribution detection

## Configuration System

The application uses a YAML-based configuration system with support for:
- **Presets**: server, desktop, minimal configurations
- **Themes**: default, dark, light UI themes
- **Module settings**: per-module configuration options

### Using Presets
```bash
python main.py --preset server    # Headless server environment
python main.py --preset desktop   # Workstation setup
python main.py --preset minimal   # Basic installation
```

## Environment-Specific Execution

### Automated Environment Detection
**Claude 应首先执行环境检测以决定执行策略：**

```bash
# 检测环境并获取退出码判断
tools/check-test-environment.sh --exit-code-only

# 退出码 0 = Ubuntu 环境，可本地执行
# 退出码 1 = 非 Ubuntu 环境，需远程执行
```

**Claude 执行逻辑：**
1. **首先运行**: `tools/check-test-environment.sh --exit-code-only`
2. **根据退出码决定**:
   - 退出码 `0`: 直接执行 `./run.sh` 或 `python main.py`
   - 退出码 `1`: 使用 `tools/sync-to-remote.sh` 同步到远程执行
3. **无需询问用户**: 自动根据环境选择执行策略

**当前环境状态**: Ubuntu 24.10 ✅ (退出码 0 = 本地执行)

### Ubuntu Environments ✅
- **Claude 可以直接执行应用**: `./install.sh`, `./run.sh`, `python main.py`
- **无需远程部署**: 在 Ubuntu 环境下 Claude 可以直接运行和测试应用程序
- **本地执行完全支持**: 包括安装、运行、开发工具等所有操作
- **测试策略**: Ubuntu = 本地直接执行，无需同步到远程服务器

### Non-Ubuntu Environments ⚠️  
- **必须在远程服务器执行** (192.168.0.33)
- **Claude 应使用远程部署**: 先用 `tools/sync-to-remote.sh` 同步，再远程执行
- **本地执行不支持**: 按项目要求必须远程运行
- **测试策略**: 非 Ubuntu = 远程部署执行，禁止本地运行

### WSL Environments
- If WSL is Ubuntu: Follow Ubuntu rules (direct execution allowed)
- If WSL is non-Ubuntu: Follow non-Ubuntu rules (remote execution required)
- Environment detection automatically handles WSL scenarios

## Adding New Modules

1. Create module in `src/initializer/modules/`
2. Add configuration to `config/modules.yaml`
3. Create UI screen in `src/initializer/ui/screens/`
4. Register in main menu (`src/initializer/ui/screens/main_menu.py`)

## UI Navigation & Keyboard Shortcuts

### Panel Navigation
- **Tab**: Switch focus between left and right panels
- **h/l**: Switch to left/right panel (Vim-style)
- **j/k**: Navigate up/down within the currently focused panel
  - Left panel: Move between segment buttons
  - Right panel: Scroll content up/down
- **Enter**: Select/activate current item
- **1-5**: Quick select segments by number
- **q**: Quit application
- **s**: Jump to Settings segment

### Visual Feedback
- **Panel Focus Indicator**: Active panel shows with blue border (primary color)
- **Segment Selection**: Selected segment shows with arrow indicator (▶)
- **Help Box**: Bottom of screen displays keyboard shortcuts

## Current Implementation Status

### Completed Features ✅
- Core TUI architecture with Rich/Textual
- Configuration management system with YAML support
- System information module with comprehensive hardware/software details
- **Package manager module** with auto-detection and mirror source management
- Advanced panel navigation system with focus management
- Visual focus indicators and panel highlighting  
- Keyboard shortcuts displayed in bottom help box
- Async loading with proper UI feedback
- Theme system with multiple color schemes (default, dark, light)
- Preset configuration system (server, desktop, minimal)
- Automated installation and deployment scripts
- **Environment detection tool** for Ubuntu vs non-Ubuntu execution strategy
- **Modal dialogs** for source selection and mirror confirmation
- **CLI-style UI components** with keyboard-first operation

### In Development 🚧
- Complete Homebrew module implementation
- User management module (user creation, SSH keys)  
- Export functionality for system information (JSON/Text)
- Enhanced UI components (progress bars, additional confirmation dialogs)

### Architecture Summary
- **20 Python files** across the codebase
- **9 UI screens** including modals and main screens
- **3 core modules**: system_info, package_manager, (homebrew in progress)
- **Comprehensive navigation**: Tab, hjkl, Enter, 1-5 shortcuts, q for quit
- **Automated tools**: Installation, deployment, environment detection
- 执行完 run.sh，测试完成后，按 Q 正常退出程序。