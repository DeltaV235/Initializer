"""Main menu screen for the Linux System Initializer."""

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.screen import Screen
from textual.widgets import Button, Static, Rule, Label
from textual.reactive import reactive

from ...config_manager import ConfigManager
from ...modules.system_info import SystemInfoModule


class MainMenuScreen(Screen):
    """Main menu screen with system overview."""
    
    BINDINGS = [
        ("1", "system_info", "System Detail Information"),
        ("2", "homebrew", "Homebrew"),
        ("3", "package_manager", "Package Manager"),
        ("4", "user_management", "User Management"),
        ("s", "settings", "Settings"),
        ("?", "help", "Help"),
        ("q", "quit", "Quit"),
        ("enter", "select_item", "Select"),
        # Vim-like navigation
        ("h", "nav_left", "Left"),
        ("j", "nav_down", "Down"),
        ("k", "nav_up", "Up"),
        ("l", "nav_right", "Right"),
    ]
    
    selected_item = reactive("")
    submenu_content = reactive("")
    
    def __init__(self, config_manager: ConfigManager):
        super().__init__()
        self.config_manager = config_manager
        self.app_config = config_manager.get_app_config()
        self.modules_config = config_manager.get_modules_config()
        self.system_info_module = SystemInfoModule(config_manager)
        
    def compose(self) -> ComposeResult:
        """Compose the main menu interface."""
        with Container(id="main-container"):
            # Title section
            yield Static(f"🚀 {self.app_config.name}", id="title")
            yield Rule()
            
            # Main content area with left-right split
            with Horizontal(id="content-area"):
                # Left panel - Main menu
                with Vertical(id="left-panel"):
                    yield Label("📋 Main Menu", classes="panel-title")
                    
                    if self.modules_config.get("system_info", {}).enabled:
                        yield Button("📊 System Detail Information (1)", id="system-info")
                    
                    if self.modules_config.get("homebrew", {}).enabled:
                        yield Button("🍺 Homebrew Management (2)", id="homebrew")
                    
                    if self.modules_config.get("package_manager", {}).enabled:
                        yield Button("📦 Package Manager (3)", id="package-manager")
                    
                    if self.modules_config.get("user_management", {}).enabled:
                        yield Button("👤 User Management (4)", id="user-management")
                    
                    yield Rule(line_style="dashed")
                    yield Button("⚙️ Settings (S)", id="settings")
                    yield Button("❓ Help (?)", id="help")
                    yield Button("❌ Exit (Q)", id="exit", variant="error")
                
                # Right panel - System Status
                with Vertical(id="right-panel"):
                    yield Label("系统状态", classes="panel-title", id="submenu-title")
                    yield Static(self.submenu_content, id="submenu-content")
    
    def on_mount(self) -> None:
        """Initialize when screen is mounted."""
        # Set initial system status content
        self.update_system_status()
    
    def update_system_status(self) -> None:
        """Update the right panel with current system status."""
        try:
            # Get basic system information
            quick_status = self.system_info_module.get_quick_status()
            
            # Get package manager info  
            package_managers = self.system_info_module.get_package_manager_info()
            if package_managers:
                pm_lines = []
                for pm, version in package_managers.items():
                    # Truncate long version strings
                    if len(version) > 50:
                        version = version[:47] + "..."
                    pm_lines.append(f"• {pm}: {version}")
                pm_status = "\n".join(pm_lines)
            else:
                pm_status = "• 未检测到包管理器"
            
            # Combine all information
            status_content = f"""**🖥️ 系统概览**

{quick_status}

**📦 包管理器**
{pm_status}

**⚡ 快捷键说明**
• 1 - System Detail Information
• 2 - Homebrew 管理  
• 3 - 包管理器设置
• 4 - 用户管理
• S - 设置
• ? - 帮助
• Q - 退出

**🎮 导航控制**
• H/J/K/L - 方向控制 (左/下/上/右)
• Enter - 确认选择

**💡 使用提示**
使用数字键快速访问模块，hjkl键导航界面"""

            self.submenu_content = status_content
            
        except ImportError as e:
            # Handle missing dependencies
            self.submenu_content = f"""**⚠️ 依赖库缺失**

某些系统信息库未安装: {str(e)}

**📋 基本信息**
系统: Linux
状态: 运行中

**⚡ 快捷键说明**
• 1 - System Detail Information
• 2 - Homebrew 管理  
• 3 - 包管理器设置
• 4 - 用户管理
• S - 设置
• ? - 帮助
• Q - 退出

**🎮 导航控制**
• H/J/K/L - 方向控制 (左/下/上/右)
• Enter - 确认选择

**💡 提示**
请确保虚拟环境已激活并安装所需依赖：
pip install -r requirements.txt"""
            
        except Exception as e:
            # Handle other errors
            self.submenu_content = f"""**❌ 系统状态获取失败**

错误详情: {str(e)[:100]}

**⚡ 快捷键说明**
• 1 - System Detail Information
• 2 - Homebrew 管理  
• 3 - 包管理器设置
• 4 - 用户管理
• S - 设置
• ? - 帮助
• Q - 退出

**🎮 导航控制**
• H/J/K/L - 方向控制 (左/下/上/右)
• Enter - 确认选择

**💡 提示**
尝试重启应用或检查系统权限"""

    @on(Button.Pressed, "#system-info")
    def action_system_info(self) -> None:
        """Show system information screen."""
        from .system_info import SystemInfoScreen
        self.app.push_screen(SystemInfoScreen(self.config_manager))
    
    @on(Button.Pressed, "#homebrew")
    def action_homebrew(self) -> None:
        """Show Homebrew management screen."""
        from .homebrew import HomebrewScreen
        self.app.push_screen(HomebrewScreen(self.config_manager))
    
    @on(Button.Pressed, "#package-manager")
    def action_package_manager(self) -> None:
        """Show package manager screen."""
        self.app.bell()  # Placeholder
        
    @on(Button.Pressed, "#user-management")
    def action_user_management(self) -> None:
        """Show user management screen."""
        self.app.bell()  # Placeholder
        
    @on(Button.Pressed, "#settings")
    def action_settings(self) -> None:
        """Show settings screen."""
        from .settings import SettingsScreen
        self.app.push_screen(SettingsScreen(self.config_manager))
        
    @on(Button.Pressed, "#help")
    def action_help(self) -> None:
        """Show help screen."""
        from .help import HelpScreen
        self.app.push_screen(HelpScreen(self.config_manager))
    
    @on(Button.Pressed, "#exit")
    def action_exit(self) -> None:
        """Exit the application."""
        self.app.exit()
    
    # Vim-like navigation actions
    def action_nav_left(self) -> None:
        """Navigate left (h key) - move to previous focusable element."""
        self.focus_previous()
    
    def action_nav_down(self) -> None:
        """Navigate down (j key) - move to next focusable element."""
        self.focus_next()
    
    def action_nav_up(self) -> None:
        """Navigate up (k key) - move to previous focusable element."""
        self.focus_previous()
    
    def action_nav_right(self) -> None:
        """Navigate right (l key) - move to next focusable element."""
        self.focus_next()
    
    def action_select_item(self) -> None:
        """Select current focused item (enter key)."""
        focused = self.focused
        if focused and hasattr(focused, 'press'):
            # For Button widgets, directly press them
            focused.press()
        elif focused:
            # For other widgets, try to trigger their default action
            try:
                if hasattr(focused, 'action_select'):
                    focused.action_select()
            except AttributeError:
                pass
