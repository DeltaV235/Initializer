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