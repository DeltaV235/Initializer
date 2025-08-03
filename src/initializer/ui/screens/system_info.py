"""System information screen."""

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.screen import Screen
from textual.widgets import Button, Static, Rule, Label, DataTable
from textual.reactive import reactive

from ...config_manager import ConfigManager
from ...modules.system_info import SystemInfoModule


class SystemInfoScreen(Screen):
    """Screen for displaying detailed system information."""
    
    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("e", "export", "Export"),
        ("escape", "back", "Back"),
        ("q", "back", "Back"),
    ]
    
    def __init__(self, config_manager: ConfigManager):
        super().__init__()
        self.config_manager = config_manager
        self.system_info = SystemInfoModule(config_manager)
        
    def compose(self) -> ComposeResult:
        """Compose the system information interface."""
        with Container():
            yield Static("📊 System Information", id="title")
            yield Rule()
            
            with Horizontal():
                # Main content
                with Vertical(id="main-content", classes="panel"):
                    yield Label("System Details")
                    yield DataTable(id="system-table")
                    
                # Side panel
                with Vertical(id="side-panel", classes="panel"):
                    yield Label("Actions")
                    yield Button("🔄 Refresh", id="refresh", variant="primary")
                    yield Button("💾 Export JSON", id="export-json")
                    yield Button("📄 Export Text", id="export-txt")
                    yield Button("🔙 Back", id="back")
    
    def on_mount(self) -> None:
        """Initialize the screen."""
        self.load_system_info()
    
    def load_system_info(self) -> None:
        """Load and display system information."""
        table = self.query_one("#system-table", DataTable)
        table.clear(columns=True)
        
        # Add columns
        table.add_columns("Component", "Information")
        
        # Get system information
        info = self.system_info.get_all_info()
        
        # Add rows
        for category, data in info.items():
            if isinstance(data, dict):
                for key, value in data.items():
                    table.add_row(f"{category.title()} - {key}", str(value))
            else:
                table.add_row(category.title(), str(data))
    
    @on(Button.Pressed, "#refresh")
    def action_refresh(self) -> None:
        """Refresh system information."""
        self.load_system_info()
        
    @on(Button.Pressed, "#export-json")
    def action_export_json(self) -> None:
        """Export system info as JSON."""
        # TODO: Implement JSON export
        self.app.bell()
        
    @on(Button.Pressed, "#export-txt")
    def action_export_txt(self) -> None:
        """Export system info as text."""
        # TODO: Implement text export
        self.app.bell()
        
    @on(Button.Pressed, "#back")
    def action_back(self) -> None:
        """Go back to main menu."""
        self.app.pop_screen()