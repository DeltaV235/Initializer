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
        self.system_info = SystemInfoModule(config_manager)
        
    def compose(self) -> ComposeResult:
        """Compose the system information interface."""
        with Container():
            yield Static("📊 System Status", id="title")
            yield Rule()
            
            with Horizontal():
                # Main content
                with Vertical(id="main-content", classes="panel"):
                    yield Label("System Details")
                    # Add cursor="row" for better navigation, zebra_stripes for readability
                    yield DataTable(id="system-table", cursor_type="row", zebra_stripes=True)
                    
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
        """Load and display all system information."""
        table = self.query_one("#system-table", DataTable)
        table.clear(columns=True)
        
        # Add columns with specific widths for better display
        table.add_column("Category", width=45)
        table.add_column("Information", width=55)
        
        # Get all system information
        info = self.system_info.get_all_info()
        
        # Define category display names and order
        category_order = ["distribution", "cpu", "memory", "disk", "network", "package_manager"]
        category_names = {
            "distribution": "🖥️ System",
            "package_manager": "📦 Package Managers", 
            "cpu": "🎯 CPU",
            "memory": "💾 Memory",
            "disk": "💿 Storage",
            "network": "🌐 Network",
        }
        
        # Track total rows added
        row_count = 0
        
        # Process categories in a specific order for better organization
        for category in category_order:
            if category not in info:
                continue
                
            data = info[category]
            display_name = category_names.get(category, category.title())
            
            # Add category separator (except for the first category)
            if row_count > 0:
                table.add_row("", "")  # Empty row as separator
                row_count += 1
            
            if isinstance(data, dict) and data:  # Check if dict is not empty
                # Add each item in the category
                for key, value in data.items():
                    # Skip empty values
                    if not value or (isinstance(value, str) and not value.strip()):
                        continue
                        
                    # Format the key for better readability
                    formatted_key = f"{display_name} - {key}"
                    
                    # Handle long values by truncating if necessary
                    str_value = str(value)
                    if len(str_value) > 80:
                        str_value = str_value[:77] + "..."
                    
                    table.add_row(formatted_key, str_value)
                    row_count += 1
            elif data:  # Non-dict data that's not empty
                table.add_row(display_name, str(data))
                row_count += 1
        
        # Add a final row showing total count
        if row_count > 0:
            table.add_row("", "")
            table.add_row("📊 Total Items Displayed", str(row_count - 1))  # -1 to exclude this row
        
        # Set focus to the table for better navigation
        table.focus()
    
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