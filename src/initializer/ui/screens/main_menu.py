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
    submenu_content = reactive("**🔄 正在加载系统信息...**\n\n请稍候，正在检测系统状态...")
    
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
        # Start periodic refresh timer (every 5 seconds)
        self.set_timer(5.0, self._refresh_system_status)
    
    def on_unmount(self) -> None:
        """Clean up when screen is unmounted."""
        # Cancel any active timers
        try:
            self.cancel_timer()
        except:
            pass
    
    def _refresh_system_status(self) -> None:
        """Callback for periodic system status refresh."""
        self.update_system_status()
        # Schedule next refresh
        self.set_timer(5.0, self._refresh_system_status)
    
    def watch_submenu_content(self, content: str) -> None:
        """Watch for changes in submenu_content and update the UI."""
        try:
            submenu_widget = self.query_one("#submenu-content", Static)
            submenu_widget.update(content)
        except Exception:
            # Widget might not be ready yet
            pass
    
    def update_system_status(self) -> None:
        """Update the right panel with detailed system information."""
        try:
            # Get comprehensive system information
            all_info = self.system_info_module.get_all_info()
            
            # Format system information sections
            sections = []
            
            # 1. Distribution Information
            if "distribution" in all_info:
                dist_info = all_info["distribution"]
                dist_lines = []
                for key, value in dist_info.items():
                    if key in ["Distribution", "System"] and value != "Unknown":
                        dist_lines.append(f"系统: {value}")
                    elif key == "Distro Version" and value:
                        dist_lines.append(f"版本: {value}")
                    elif key == "Architecture":
                        dist_lines.append(f"架构: {value}")
                    elif key == "Machine" and "Architecture" not in dist_info:
                        dist_lines.append(f"架构: {value}")
                
                if dist_lines:
                    sections.append("**🖥️ 系统信息**\n" + "\n".join(dist_lines))
            
            # 2. CPU Information
            if "cpu" in all_info:
                cpu_info = all_info["cpu"]
                cpu_lines = []
                for key, value in cpu_info.items():
                    if key == "Processor" and value != "Unknown":
                        cpu_lines.append(f"处理器: {value[:40]}...")
                    elif key == "CPU Count":
                        cpu_lines.append(f"核心数: {value}")
                    elif key == "Logical CPUs":
                        cpu_lines.append(f"逻辑核心: {value}")
                    elif key == "Current Usage":
                        cpu_lines.append(f"当前使用率: {value}")
                    elif key == "CPU Frequency":
                        cpu_lines.append(f"频率: {value}")
                
                if cpu_lines:
                    sections.append("**⚡ CPU信息**\n" + "\n".join(cpu_lines))
            
            # 3. Memory Information
            if "memory" in all_info:
                mem_info = all_info["memory"]
                mem_lines = []
                for key, value in mem_info.items():
                    if "RAM" in key:
                        if key == "Total RAM":
                            mem_lines.append(f"总内存: {value}")
                        elif key == "Used RAM":
                            mem_lines.append(f"已用内存: {value}")
                        elif key == "Available RAM":
                            mem_lines.append(f"可用内存: {value}")
                        elif key == "RAM Usage":
                            mem_lines.append(f"内存使用率: {value}")
                    elif "Swap" in key:
                        if key == "Total Swap":
                            mem_lines.append(f"交换分区: {value}")
                        elif key == "Swap Usage":
                            mem_lines.append(f"交换使用率: {value}")
                
                if mem_lines:
                    sections.append("**💾 内存信息**\n" + "\n".join(mem_lines))
            
            # 4. Disk Information
            if "disk" in all_info:
                disk_info = all_info["disk"]
                disk_lines = []
                for key, value in disk_info.items():
                    if "Root Partition" in key:
                        if key == "Root Partition Total":
                            disk_lines.append(f"总容量: {value}")
                        elif key == "Root Partition Used":
                            disk_lines.append(f"已用空间: {value}")
                        elif key == "Root Partition Free":
                            disk_lines.append(f"可用空间: {value}")
                        elif key == "Root Partition Usage":
                            disk_lines.append(f"磁盘使用率: {value}")
                
                if disk_lines:
                    sections.append("**💿 磁盘信息**\n" + "\n".join(disk_lines))
            
            # 5. Package Manager Information
            if "package_manager" in all_info:
                pm_info = all_info["package_manager"]
                pm_lines = []
                for pm, status in pm_info.items():
                    # Truncate long version strings
                    if len(status) > 45:
                        status = status[:42] + "..."
                    pm_lines.append(f"• {pm}: {status}")
                
                if pm_lines:
                    sections.append("**📦 包管理器**\n" + "\n".join(pm_lines))
            
            # 6. Quick Help
            help_section = """**⚡ 快捷键说明**
• 1 - 系统详细信息
• 2 - Homebrew 管理  
• 3 - 包管理器设置
• 4 - 用户管理
• S - 设置 • ? - 帮助 • Q - 退出

**🎮 导航控制**
• H/J/K/L - 方向控制
• Enter - 确认选择"""
            
            sections.append(help_section)
            
            # Combine all sections
            self.submenu_content = "\n\n".join(sections)
            
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
