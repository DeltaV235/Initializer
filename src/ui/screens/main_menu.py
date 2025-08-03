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
    ]
    
    system_status = reactive("")
    
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
            yield Static(f"v{self.app_config.version} by {self.app_config.author}", id="subtitle")
            yield Rule()
            
            # Main content area
            with Horizontal(id="content-area"):
                # Left panel - Menu options
                with Vertical(id="menu-panel"):
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
                
                # Right panel - System status
                with Vertical(id="status-panel"):
                    yield Label("📈 System Status", classes="panel-title")
                    yield Static(self.system_status, id="status-content")
                    
                    yield Label("🔧 Quick Actions", classes="panel-title")
                    yield Button("🔄 Refresh Status", id="refresh", size=Button.size(width=20))
                    yield Button("💾 Save Config", id="save-config", size=Button.size(width=20))
    
    def on_mount(self) -> None:
        """Initialize when screen is mounted."""
        self.update_system_status()
    
    def update_system_status(self) -> None:
        """Update system status information."""
        try:
            import platform
            import psutil
            
            # Get basic system information
            status_lines = [
                f"OS: {platform.system()} {platform.release()}",
                f"CPU: {psutil.cpu_count()} cores ({psutil.cpu_percent():.1f}% used)",
                f"Memory: {psutil.virtual_memory().percent:.1f}% used",
                f"Disk: {psutil.disk_usage('/').percent:.1f}% used",
            ]
            
            self.system_status = "\n".join(status_lines)
            
        except ImportError:
            self.system_status = "System information unavailable\n(psutil not installed)"
        except Exception as e:
            self.system_status = f"Error getting system info:\n{str(e)}"
    
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
        
    @on(Button.Pressed, "#refresh")
    def action_refresh(self) -> None:
        """Refresh system status."""
        self.update_system_status()
        
    @on(Button.Pressed, "#save-config")
    def action_save_config(self) -> None:
        """Save current configuration."""
        self.app.bell()  # Placeholder for save functionality