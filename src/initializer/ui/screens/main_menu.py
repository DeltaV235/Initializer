"""Main menu screen for the Linux System Initializer."""

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.screen import Screen
from textual.widgets import Button, Static, Rule, Label
from textual.reactive import reactive

from ...config_manager import ConfigManager


class MainMenuScreen(Screen):
    """Main menu screen with system overview."""
    
    BINDINGS = [
        ("1", "system_info", "System Info"),
        ("2", "homebrew", "Homebrew"),
        ("3", "package_manager", "Package Manager"),
        ("4", "user_management", "User Management"),
        ("s", "settings", "Settings"),
        ("q", "quit", "Quit"),
        ("enter", "select_item", "Select"),
    ]
    
    selected_item = reactive("")
    submenu_content = reactive("")
    
    def __init__(self, config_manager: ConfigManager):
        super().__init__()
        self.config_manager = config_manager
        self.app_config = config_manager.get_app_config()
        self.modules_config = config_manager.get_modules_config()
        
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
                        yield Button("📊 System Information", id="system-info", variant="primary")
                    
                    if self.modules_config.get("homebrew", {}).enabled:
                        yield Button("🍺 Homebrew Management", id="homebrew")
                    
                    if self.modules_config.get("package_manager", {}).enabled:
                        yield Button("📦 Package Manager", id="package-manager")
                    
                    if self.modules_config.get("user_management", {}).enabled:
                        yield Button("👤 User Management", id="user-management")
                    
                    yield Rule(line_style="dashed")
                    yield Button("⚙️ Settings", id="settings")
                    yield Button("❓ Help", id="help")
                    yield Button("❌ Exit", id="exit", variant="error")
                
                # Right panel - Submenu/Details
                with Vertical(id="right-panel"):
                    yield Label("详细信息", classes="panel-title", id="submenu-title")
                    yield Static(self.submenu_content, id="submenu-content")
    
    def on_mount(self) -> None:
        """Initialize when screen is mounted."""
        # Set initial submenu content
        self.update_submenu_content("system-info")
    

    
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
    
    def update_submenu_content(self, option_id: str) -> None:
        """Update the right panel content based on selected option."""
        content_map = {
            "system-info": """**📊 系统信息**

• 查看系统详细信息
• CPU、内存、磁盘状态
• 网络接口信息
• 系统发行版信息

按 Enter 进入系统信息模块""",
            
            "homebrew": """**🍺 Homebrew 管理**

• 安装 Homebrew 包管理器
• 配置国内镜像源
• 管理已安装包
• 更新和清理

按 Enter 进入 Homebrew 管理""",
            
            "package-manager": """**📦 包管理器**

• 检测系统包管理器
• 配置软件源镜像
• 安装常用软件包
• 系统更新管理

按 Enter 进入包管理器模块""",
            
            "user-management": """**👤 用户管理**

• 创建和管理用户账户
• 配置用户权限
• SSH 密钥管理
• 用户组设置

按 Enter 进入用户管理""",
            
            "settings": """**⚙️ 设置**

• 应用配置选项
• 主题和显示设置
• 模块启用/禁用
• 导入/导出配置

按 Enter 进入设置""",
            
            "help": """**❓ 帮助**

• 使用说明和文档
• 快捷键列表
• 常见问题解答
• 关于信息

按 Enter 查看帮助""",
            
            "exit": """**❌ 退出**

• 退出应用程序
• 保存当前配置
• 清理临时文件

按 Enter 退出应用程序"""
        }
        
        self.submenu_content = content_map.get(option_id, "请选择一个选项查看详细信息")
