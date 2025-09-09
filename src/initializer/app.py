"""Main application class for the Linux System Initializer."""

import asyncio
from pathlib import Path
from typing import Optional

from rich.console import Console
from textual import on
from textual.app import App, ComposeResult
from textual.widgets import Footer, Header
from textual.screen import Screen

from .config_manager import ConfigManager


class InitializerApp(App):
    """Linux System Initializer TUI Application."""
    
    CSS_PATH = "styles.css"
    TITLE = "Linux System Initializer"
    SUB_TITLE = "Modern TUI for System Setup"
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("s", "settings", "Settings"),
        ("h", "help", "Help"),
        ("ctrl+c", "quit", "Quit"),
    ]
    
    def __init__(self, config_manager: ConfigManager, preset: str = None, 
                 headless: bool = False, debug: bool = False):
        super().__init__()
        
        self.config_manager = config_manager
        self.preset = preset
        self.headless = headless
        self.debug_mode = debug
        self.console = Console()
        
        # Load configuration
        self.app_config = config_manager.get_app_config()
        self.modules_config = config_manager.get_modules_config()
        self.theme_config = config_manager.get_theme_config()
        
        # Apply preset if specified
        if preset:
            self._apply_preset(preset)
            
        # Update title
        self.title = self.app_config.name
        self.sub_title = f"v{self.app_config.version}"
        
    def _apply_preset(self, preset_name: str) -> None:
        """Apply a configuration preset."""
        try:
            preset_config = self.config_manager.load_preset(preset_name)
            if self.debug_mode:
                self.console.print(f"[green]Applied preset: {preset_name}[/green]")
        except FileNotFoundError:
            if self.debug_mode:
                self.console.print(f"[yellow]Preset not found: {preset_name}[/yellow]")
        
    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield Footer()
        
    def on_mount(self) -> None:
        """Called when app starts."""
        # Push the main screen
        from .ui.screens.main_menu import MainMenuScreen
        self.push_screen(MainMenuScreen(self.config_manager))
        
    async def action_settings(self) -> None:
        """Show settings screen."""
        from .ui.screens.settings import SettingsScreen
        self.push_screen(SettingsScreen(self.config_manager))
        
    async def action_help(self) -> None:
        """Show help screen."""
        from .ui.screens.help import HelpScreen
        self.push_screen(HelpScreen(self.config_manager))
        
    def action_quit(self) -> None:
        """Quit the application."""
        # Disable mouse tracking immediately before exit
        try:
            import sys
            sys.stdout.write('\033[?1000l\033[?1002l\033[?1003l\033[?1006l\033[?1015l\033[?1004l\033[?2004l')
            sys.stdout.flush()
        except Exception:
            pass
        self.exit()
        
    def on_unmount(self) -> None:
        """Called when app is unmounted - ensure proper cleanup."""
        # Disable mouse tracking to prevent control sequences after exit
        try:
            import sys
            # Send escape sequences to disable mouse tracking
            sys.stdout.write('\033[?1000l\033[?1002l\033[?1003l\033[?1006l\033[?1015l')
            sys.stdout.flush()
        except Exception:
            pass