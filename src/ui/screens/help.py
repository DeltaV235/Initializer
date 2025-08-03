"""Help screen with usage information."""

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.screen import Screen
from textual.widgets import Button, Static, Rule, Label, Markdown

from ...config_manager import ConfigManager


class HelpScreen(Screen):
    """Help screen with usage information."""
    
    BINDINGS = [
        ("escape", "back", "Back"),
        ("q", "back", "Back"),
    ]
    
    def __init__(self, config_manager: ConfigManager):
        super().__init__()
        self.config_manager = config_manager
        self.app_config = config_manager.get_app_config()
        
    def compose(self) -> ComposeResult:
        """Compose the help interface."""
        help_text = f"""
# {self.app_config.name} Help

## Keyboard Shortcuts

- **q** or **Escape**: Go back/quit
- **1-4**: Quick menu navigation
- **s**: Settings
- **h**: Help
- **Ctrl+C**: Quit application

## Features

### System Information
- View detailed system information
- Export data in multiple formats
- Real-time status monitoring

### Homebrew Management
- Install and manage Homebrew
- Change package sources
- Install packages

### Package Manager
- Detect available package managers
- Change mirror sources
- Install essential packages

### User Management
- Create new users
- Configure user settings
- Manage permissions

## Configuration

The application uses YAML configuration files located in the `config/` directory:

- `app.yaml`: Main application settings
- `modules.yaml`: Module-specific configuration
- `themes.yaml`: UI themes and colors
- `presets/`: Predefined configuration templates

## Author

Created by {self.app_config.author}
Version {self.app_config.version}
        """
        
        with Container():
            yield Static("❓ Help & Usage", id="title")
            yield Rule()
            
            with Vertical(classes="panel"):
                yield Markdown(help_text.strip())
                yield Button("🔙 Back to Main Menu", id="back")
    
    @on(Button.Pressed, "#back")
    def action_back(self) -> None:
        """Go back to main menu."""
        self.app.pop_screen()