"""Settings screen for configuration management."""

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.screen import Screen
from textual.widgets import Button, Static, Rule, Label

from ...config_manager import ConfigManager


class SettingsScreen(Screen):
    """Settings screen for app configuration."""
    
    BINDINGS = [
        ("escape", "back", "Back"),
        ("q", "back", "Back"),
    ]
    
    def __init__(self, config_manager: ConfigManager):
        super().__init__()
        self.config_manager = config_manager
        
    def compose(self) -> ComposeResult:
        """Compose the settings interface."""
        with Container():
            yield Static("⚙️ Settings", id="title")
            yield Rule()
            
            with Vertical(classes="panel"):
                yield Label("Configuration Options")
                yield Static("Settings management coming soon...", id="placeholder")
                yield Button("🔙 Back to Main Menu", id="back")
    
    @on(Button.Pressed, "#back")
    def action_back(self) -> None:
        """Go back to main menu."""
        self.app.pop_screen()