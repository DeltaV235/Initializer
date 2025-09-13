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
- **Textual Framework Priority**: Always prioritize using Textual's native components, methods, and patterns over custom implementations. Leverage Textual's built-in event handling, styling system, and UI components for consistency and reliability.
- **Context7 Comprehensive Documentation**: When encountering unfamiliar libraries, frameworks, or technologies, use Context7 extensively with multiple queries covering different aspects (components, events, styling, patterns, best practices) to build complete understanding before implementation. Query multiple times with different topics to ensure comprehensive coverage.

## Project Overview

Linux System Initializer is a modern Terminal User Interface (TUI) application for Linux system initialization and configuration. The project has been refactored from legacy bash scripts to a Python-based TUI using Rich/Textual framework.

## UI/UX Design Philosophy

**Keyboard-First Operation**: The entire project is designed primarily for keyboard operation. The basic logic uses arrows (▶) to indicate the current cursor position, and blue borders to show which panel currently has focus. The interface adopts a CLI-style graphical interface rather than modern UI elements, maintaining a terminal-native feel that experienced system administrators would find familiar and efficient.

## Terminal State Management

**Important**: The application includes automatic terminal state cleanup to prevent terminal issues after exit:
- `tools/reset-terminal.sh` - Manual terminal reset script
- `run.sh` automatically runs reset script after application exits
- Python code includes cleanup handlers for normal and abnormal exits
- Cleanup includes: exiting alternate screen buffer, disabling mouse tracking, showing cursor

**Claude 执行后清理规则**: 
- 正常退出：应用会自动重置终端状态
- 强制中断（KillBash/Ctrl+C）：必须手动执行 `./tools/reset-terminal.sh` 清理终端状态（不要使用 `--clear` 参数）
- 任何异常终端显示：使用 `./tools/reset-terminal.sh` 进行清理（保留终端历史内容）

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

# Terminal state reset (automatically called by run.sh)
tools/reset-terminal.sh
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

## Textual Framework Documentation

### Core Components and Architecture

#### Widgets and UI Components
- **Built-in Widgets**: Button, Input, Label, Static, Header, Footer, ProgressBar, DataTable, Tree, ListView, Markdown, TextArea, OptionList, Tabs, TabbedContent, etc.
- **Containers**: Vertical, Horizontal, Grid, Container, VerticalScroll, HorizontalScroll, VerticalGroup, HorizontalGroup, Center, Right, Middle
- **Custom Widgets**: Extend Widget base class, implement `compose()` method, use `DEFAULT_CSS` for default styling
- **Component Classes**: Use `COMPONENT_CLASSES` for styling specific parts of widgets (e.g., `"widget--element"`)
- **Widget Lifecycle**: `on_mount()`, `on_unmount()`, reactive attributes, watch methods

#### Layout System
- **Layout Types**: `vertical` (default), `horizontal`, `grid`
- **Grid Layout**: Use `grid-size`, `grid-columns`, `grid-rows`, `grid-gutter` for cell arrangement
- **Container Behavior**: Horizontal/Vertical containers divide available space equally
- **Scrolling**: Use VerticalScroll/HorizontalScroll for scrollable content
- **Alignment**: Use `align: center middle` for centering, `content-align` for widget content
- **Fractional Units**: Use `fr` units for proportional sizing (`1fr`, `2fr`, etc.)

#### Event Handling System
- **Event Methods**: `on_key()`, `on_mouse_down()`, `on_click()`, `on_button_pressed()`, etc.
- **Event Objects**: Event classes contain relevant data (coordinates, key pressed, widget reference)
- **Event Bubbling**: Events propagate up the widget hierarchy
- **@on Decorator**: `@on(Button.Pressed, "#button-id")` for targeted event handling
- **Handler Parameters**: Can omit event parameter if not needed in handler
- **Message Queue**: Each widget has async message queue for event processing

#### Screen and Navigation Management
- **Screen Stack**: Use `push_screen()`, `pop_screen()`, `switch_screen()` for navigation
- **Modal Screens**: Inherit from `ModalScreen` for overlay dialogs
- **Screen Modes**: Use `MODES` class variable to define mode-specific screen stacks
- **Screen Lifecycle**: `on_mount()`, `on_unmount()`, `dismiss(result)` for modal return values
- **Screen Push/Pop**: Support callbacks and async `wait_for_dismiss` patterns

#### Reactivity System
- **Reactive Attributes**: Use `reactive()` or `var()` for automatic UI updates
- **Watch Methods**: `watch_attribute_name()` called when reactive attributes change
- **Computed Properties**: Automatic recalculation when dependencies change
- **Dynamic Watching**: Use `watch(obj, "attribute", callback)` for external objects
- **Reactivity Options**: `layout=True`, `repaint=True`, `recompose=True`, `bindings=True`
- **Initialization**: Use `set_reactive()` in constructor to avoid premature watcher calls

#### Styling and Theming
- **CSS-like Syntax**: Use Textual CSS (TCSS) for styling widgets
- **Selectors**: Type (`Widget`), ID (`#my-id`), class (`.my-class`), pseudo (`Widget:hover`)
- **Theme Variables**: Use `$primary`, `$secondary`, `$foreground`, `$background`, etc.
- **Color System**: Support named colors, hex codes, RGB/HSL, theme variables
- **Component Styling**: Target widget parts with component classes
- **Dynamic Styling**: Set styles via `widget.styles.property = value`
- **Responsive Design**: Use `:light/:dark` pseudo-selectors for theme-aware styling

#### Input and Interaction
- **Keyboard Input**: Handle via `on_key()`, support key bindings with `BINDINGS`
- **Mouse Events**: `on_mouse_down()`, `on_mouse_move()`, `on_click()` with coordinates
- **Input Widgets**: Input, TextArea with validation, suggestions, and event handling
- **Focus Management**: Tab navigation, `can_focus` attribute, focus/blur events
- **Mouse Capture**: `capture_mouse()` for drag-and-drop functionality
- **Input Types**: text, integer, number, password with built-in validation

#### Actions and Key Bindings
- **Action Methods**: Define `action_name()` methods, callable via `run_action()`
- **Key Bindings**: Use `BINDINGS` class variable to map keys to actions
- **Binding Structure**: `("key", "action", "description", show_in_footer)`
- **Built-in Actions**: `quit`, `bell`, `toggle_dark`, `focus_next`, `screenshot`, etc.
- **Action Links**: Use `[@click=action_name]text[/]` in markup for clickable actions
- **Priority Bindings**: Use `priority=True` for app-level key handling
- **Dynamic Actions**: Implement `check_action()` for conditional action availability

### Best Practices and Patterns

#### Widget Development
- Always call `super().__init__()` in custom widget constructors
- Use `compose()` method to define child widgets
- Implement watch methods for reactive attribute changes
- Use component classes for styling specific widget parts
- Follow naming conventions: `watch_attribute_name()`, `action_name()`

#### Layout and UI Design
- Use containers (Vertical/Horizontal) for macro layout division
- Apply grid layout for structured arrangements with `grid-size`
- Use fractional units (`fr`) for responsive sizing
- Center content with `align: center middle` on containers
- Implement keyboard-first navigation with proper focus handling

#### Performance and Memory
- Use reactive attributes with appropriate flags (`layout`, `repaint`)
- Implement efficient event handling with targeted selectors
- Use `recompose=True` for lists that change size
- Avoid expensive operations in watch methods
- Clean up resources in `on_unmount()` if needed

#### Testing and Development
- Use `App.run_test()` context manager for testing
- Simulate events with Pilot: `pilot.click()`, `pilot.press()`, `pilot.type()`
- Test reactive attribute changes and watch method calls
- Verify screen navigation and modal dismiss behavior
- Use `app.screenshot()` for visual regression testing

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

### Testing Policy
**重要说明：Claude 在任何环境下都不应该执行应用程序测试**

- **用户手动测试**: 所有应用程序的运行和测试都由用户手动执行
- **Claude 职责**: 仅限于代码编写、修改、分析和文档更新
- **不执行测试**: 无论是 Ubuntu、非 Ubuntu 还是其他任何环境，Claude 都不应该运行 `./run.sh`、`python main.py` 或其他测试命令
- **代码验证**: Claude 可以通过代码分析、静态检查和逻辑审查来确保代码质量，但不执行动态测试

### Environment Detection (仅用于参考)
项目包含环境检测工具，但 Claude 不应该使用它们来决定是否执行测试：

```bash
# 环境检测工具（Claude 不使用）
tools/check-test-environment.sh --exit-code-only
```

### Claude 工作范围
- ✅ **代码开发**: 编写、修改、重构代码
- ✅ **代码分析**: 阅读、理解、解释代码逻辑
- ✅ **问题诊断**: 分析错误信息、日志输出、调试信息
- ✅ **文档更新**: 修改配置文件、文档、注释
- ✅ **架构设计**: 规划模块结构、接口设计
- ❌ **应用程序执行**: 不运行 TUI 应用程序进行测试
- ❌ **自动化测试**: 不执行任何形式的应用程序测试
- ❌ **部署操作**: 不执行远程同步或部署命令

### 用户测试流程
当 Claude 完成代码修改后：
1. Claude 提供代码修改说明和预期行为
2. 用户手动执行 `./run.sh` 或 `python main.py` 进行测试
3. 用户报告测试结果或问题
4. Claude 根据用户反馈进行代码调整

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
- **用户测试**: 用户手动运行 run.sh 测试应用程序，测试完成后按 Q 正常退出程序。