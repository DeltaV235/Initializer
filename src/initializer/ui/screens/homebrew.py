"""Homebrew management screen."""

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.screen import Screen
from textual.widgets import Button, Static, Rule, Label

from ...config_manager import ConfigManager


class HomebrewScreen(Screen):
    """Screen for Homebrew management."""
    
    BINDINGS = [
        ("escape", "back", "Back"),
        ("q", "back", "Back"),
    ]
    
    def __init__(self, config_manager: ConfigManager):
        super().__init__()
        self.config_manager = config_manager
        
    def compose(self) -> ComposeResult:
        """Compose the Homebrew management interface."""
        with Container():
            yield Static("🍺 Homebrew Management", id="title")
            yield Rule()
            
            with Horizontal():
                with Vertical(id="main-content", classes="panel"):
                    yield Label("Homebrew Options")
                    yield Button("📥 Install Homebrew", id="install")
                    yield Button("🔄 Change Source", id="change-source")
                    yield Button("📦 Install Packages", id="install-packages")
                    yield Button("ℹ️ Show Status", id="status")
                    
                with Vertical(id="side-panel", classes="panel"):
                    yield Label("Status")
                    yield Static("Checking Homebrew status...", id="status-text")
                    yield Button("🔙 Back", id="back")
    
    def on_mount(self) -> None:
        """Initialize the screen."""
        self.check_homebrew_status()
    
    def check_homebrew_status(self) -> None:
        """Check if Homebrew is installed."""
        import shutil
        
        status_widget = self.query_one("#status-text", Static)
        
        if shutil.which("brew"):
            status_widget.update("✅ Homebrew is installed")
        else:
            status_widget.update("❌ Homebrew not found")
    
    @on(Button.Pressed, "#install")
    def action_install(self) -> None:
        """Install Homebrew."""
        # TODO: Implement Homebrew installation
        self.app.bell()
        
    @on(Button.Pressed, "#change-source")
    def action_change_source(self) -> None:
        """Change Homebrew source."""
        # TODO: Implement source changing
        self.app.bell()
        
    @on(Button.Pressed, "#install-packages")
    def action_install_packages(self) -> None:
        """Install packages via Homebrew."""
        # TODO: Implement package installation
        self.app.bell()
        
    @on(Button.Pressed, "#status")
    def action_status(self) -> None:
        """Show Homebrew status."""
        self.check_homebrew_status()
        
    @on(Button.Pressed, "#back")
    def action_back(self) -> None:
        """Go back to main menu."""
        self.app.pop_screen()