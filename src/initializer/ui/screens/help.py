"""Help screen with usage information."""

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.screen import Screen
from textual.widgets import Button, Static, Rule, Markdown

from ...config_manager import ConfigManager
from ...utils.logger import get_ui_logger


class HelpScreen(Screen):
    """Help screen with usage information."""

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
        self.app_config = config_manager.get_app_config()
        self.logger = get_ui_logger("help")
        self.logger.info("帮助界面初始化")

    def on_mount(self) -> None:
        """Mount the help screen."""
        self.logger.info("帮助界面已加载")
        
    def compose(self) -> ComposeResult:
        """Compose the help interface."""
        help_text = f"""
# {self.app_config.name} Help

## Keyboard Shortcuts

### Navigation
- **H/J/K/L**: Vim-style navigation (Left/Down/Up/Right)
- **J/K=Up/Down**: Navigate up/down
- **Enter**: Select/Activate focused item | Confirm action
- **TAB**: Move to next focusable element

### Actions
- **Esc**: Go back/cancel | Close dialog
- **Q**: Quit application
- **1-5**: Quick segment selection (Main Menu)
- **S**: Settings
- **?**: Help
- **CTRL+C**: Quit application

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
        self.logger.info("用户从帮助页面返回主菜单")
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