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
        ("enter", "select_item", "Select"),
        # Vim-like navigation
        ("h", "nav_left", "Left"),
        ("j", "nav_down", "Down"),
        ("k", "nav_up", "Up"),
        ("l", "nav_right", "Right"),
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
    
    # Vim-like navigation actions
    def action_nav_left(self) -> None:
        """Navigate left (h key)."""
        self.focus_previous()
    
    def action_nav_down(self) -> None:
        """Navigate down (j key)."""
        self.focus_next()
    
    def action_nav_up(self) -> None:
        """Navigate up (k key)."""
        self.focus_previous()
    
    def action_nav_right(self) -> None:
        """Navigate right (l key)."""
        self.focus_next()
    
    def action_select_item(self) -> None:
        """Select current focused item (enter key)."""
        focused = self.focused
        if focused and hasattr(focused, 'press'):
            focused.press()
        elif focused:
            try:
                if hasattr(focused, 'action_select'):
                    focused.action_select()
            except AttributeError:
                pass