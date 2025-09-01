"""Main menu screen for the Linux System Initializer."""

import re
from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.screen import Screen
from textual.widgets import Button, Static, Rule, Label, ProgressBar
from textual.reactive import reactive

from ...config_manager import ConfigManager
from ...modules.system_info import SystemInfoModule


class MainMenuScreen(Screen):
    """Main menu screen with system overview."""
    
    BINDINGS = [
        ("2", "homebrew", "Homebrew"),
        ("3", "package_manager", "Package Manager"),
        ("4", "user_management", "User Management"),
        ("s", "settings", "Settings"),
        ("?", "help", "Help"),
        ("q", "quit", "Quit"),
        ("enter", "select_item", "Select"),
        # Vim-like navigation
        ("h", "nav_left", "Left"),
        ("j", "nav_down", "Down"),
        ("k", "nav_up", "Up"),
        ("l", "nav_right", "Right"),
    ]
    
    selected_item = reactive("")
    
    def __init__(self, config_manager: ConfigManager):
        super().__init__()
        self.config_manager = config_manager
        self.app_config = config_manager.get_app_config()
        self.modules_config = config_manager.get_modules_config()
        self.system_info_module = SystemInfoModule(config_manager)
        
    def compose(self) -> ComposeResult:
        """Compose the main menu interface."""
        with Container(id="main-container"):
            # Title section
            yield Static(f"🚀 {self.app_config.name}", id="title")
            yield Rule()
            
            # Main content area with left-right split
            with Horizontal(id="content-area"):
                # Left panel - Main menu
                with Vertical(id="left-panel"):
                    yield Label("📋 Main Menu", classes="panel-title")
                    
                    if self.modules_config.get("homebrew", {}).enabled:
                        yield Button("🍺 Homebrew Management (2)", id="homebrew")
                    
                    if self.modules_config.get("package_manager", {}).enabled:
                        yield Button("📦 Package Manager (3)", id="package-manager")
                    
                    if self.modules_config.get("user_management", {}).enabled:
                        yield Button("👤 User Management (4)", id="user-management")
                    
                    yield Rule(line_style="dashed")
                    yield Button("⚙️ Settings (S)", id="settings")
                    yield Button("❓ Help (?)", id="help")
                    yield Button("❌ Exit (Q)", id="exit", variant="error")
                
                # Right panel - System Status
                with Vertical(id="right-panel"):
                    yield Label("System Status", classes="panel-title", id="submenu-title")
                    with ScrollableContainer(id="system-info-scroll"):
                        yield Static("🔄 Loading System Information...", id="loading-message")
    
    def on_mount(self) -> None:
        """Initialize when screen is mounted."""
        # Set initial system status content
        self.update_system_status()
        # Start periodic refresh timer (every 5 seconds)
        self.set_timer(5.0, self._refresh_system_status)
    
    def on_unmount(self) -> None:
        """Clean up when screen is unmounted."""
        # Cancel any active timers
        try:
            self.cancel_timer()
        except:
            pass
    
    def _refresh_system_status(self) -> None:
        """Callback for periodic system status refresh."""
        self.update_system_status()
        # Schedule next refresh
        self.set_timer(5.0, self._refresh_system_status)
    
    def update_system_status(self) -> None:
        """Update the right panel with detailed system information using dynamic widgets."""
        try:
            # Get comprehensive system information
            all_info = self.system_info_module.get_all_info()
            
            # Clear existing content and rebuild
            self._clear_system_panel()
            self._build_system_panel(all_info)
            
        except ImportError as e:
            # Handle missing dependencies
            self._show_error_message(f"Missing Dependencies: {str(e)}")
            
        except Exception as e:
            # Handle other errors
            self._show_error_message(f"System Status Failed: {str(e)[:100]}")

    def _clear_system_panel(self) -> None:
        """Clear the system info panel."""
        try:
            scroll_container = self.query_one("#system-info-scroll", ScrollableContainer)
            # Remove all children except loading message
            children = list(scroll_container.children)
            for child in children:
                child.remove()
        except Exception:
            pass

    def _build_system_panel(self, all_info: dict) -> None:
        """Build the system panel with dynamic widgets."""
        scroll_container = self.query_one("#system-info-scroll", ScrollableContainer)
        
        # Category configuration with icons and priority fields
        category_configs = [
            ("distribution", "🐧 System Information", [
                ("System", "System"),
                ("Distribution", "Distribution"),
                ("Distro Version", "Version"),
                ("Architecture", "Architecture"),
                ("Machine", "Machine"),
            ]),
            ("cpu", "🖥️ CPU Information", [
                ("Processor", "Processor"),
                ("CPU Count", "Physical Cores"),
                ("Logical CPUs", "Logical Cores"),
                ("Current Usage", "CPU Usage"),
                ("CPU Frequency", "CPU Frequency"),
            ]),
            ("memory", "💾 Memory Information", [
                ("Total RAM", "Total RAM"),
                ("Available RAM", "Available RAM"),
                ("Used RAM", "Used RAM"),
                ("RAM Usage", "RAM Usage"),
                ("Total Swap", "Total Swap"),
                ("Used Swap", "Used Swap"),
                ("Swap Usage", "Swap Usage"),
            ]),
            ("disk", "💽 Storage Information", [
                ("Root Partition Total", "Total Storage"),
                ("Root Partition Used", "Used Storage"),
                ("Root Partition Free", "Free Storage"),
                ("Root Partition Usage", "Storage Usage"),
            ]),
            ("package_manager", "📦 Package Managers", None),
            ("network", "🌐 Network Information", [
                ("Bytes Sent", "Network Sent"),
                ("Bytes Received", "Network Received"),
            ])
        ]
        
        for category_key, category_title, field_mappings in category_configs:
            if category_key not in all_info or not all_info[category_key]:
                continue
                
            data = all_info[category_key]
            
            # Add category separator and title
            self._add_category_section(scroll_container, category_title)
            
            # Add data rows
            if field_mappings:
                # Use priority fields
                for eng_key, cn_key in field_mappings:
                    if eng_key in data:
                        self._add_data_row(scroll_container, cn_key, data[eng_key])
            else:
                # Add all fields (for package_manager and interface fields)
                for key, value in data.items():
                    display_key = self._translate_key(category_key, key)
                    self._add_data_row(scroll_container, display_key, value)

    def _add_category_section(self, container: ScrollableContainer, title: str) -> None:
        """Add a category section with separator."""
        container.mount(Rule(line_style="heavy", classes="category-separator"))
        container.mount(Label(title, classes="category-title"))

    def _add_data_row(self, container: ScrollableContainer, key: str, value: str) -> None:
        """Add a data row with appropriate widget type."""
        if not value or str(value) == "Unknown" or not str(value).strip():
            return
            
        # Check if this is a percentage field that needs progress bar
        percentage_fields = ["CPU Usage", "RAM Usage", "Swap Usage", "Storage Usage"]
        
        if key in percentage_fields and "%" in str(value):
            self._add_progress_row(container, key, str(value))
        else:
            self._add_info_row(container, key, str(value))

    def _add_info_row(self, container: ScrollableContainer, key: str, value: str) -> None:
        """Add a regular info row with two columns."""
        row_container = Horizontal(classes="info-row")
        container.mount(row_container)
        row_container.mount(Label(key, classes="info-key"))
        row_container.mount(Label(value, classes="info-value"))

    def _add_progress_row(self, container: ScrollableContainer, key: str, value: str) -> None:
        """Add a progress row with ProgressBar."""
        # Extract percentage value
        percentage_match = re.search(r'(\d+\.?\d*)%', value)
        if not percentage_match:
            self._add_info_row(container, key, value)
            return
            
        percentage = float(percentage_match.group(1))
        
        row_container = Horizontal(classes="progress-row")
        container.mount(row_container)
        row_container.mount(Label(key, classes="info-key"))
        
        # Create progress bar
        progress_bar = ProgressBar(total=100.0, show_percentage=False, show_eta=False)
        progress_bar.update(progress=percentage)
        progress_bar.add_class("info-progress")
        
        # Set color based on usage level
        if percentage < 50:
            progress_bar.add_class("progress-good")
        elif percentage < 80:
            progress_bar.add_class("progress-warning")
        else:
            progress_bar.add_class("progress-danger")
        
        row_container.mount(progress_bar)
        row_container.mount(Label(f"{percentage:.1f}%", classes="progress-label"))

    def _translate_key(self, category: str, key: str) -> str:
        """Translate English keys for display."""
        translations = {
            "network": {
                "Bytes Sent": "Network Sent",
                "Bytes Received": "Network Received",
            }
        }
        
        if category in translations and key in translations[category]:
            return translations[category][key]
        
        # Handle interface keys
        if key.startswith("Interface "):
            return key.replace("Interface ", "Network Interface ")
        elif key.startswith("IP Address "):
            return key.replace("IP Address ", "IP Address ")
            
        return key

    def _show_error_message(self, message: str) -> None:
        """Show error message in the system panel."""
        try:
            scroll_container = self.query_one("#system-info-scroll", ScrollableContainer)
            self._clear_system_panel()
            scroll_container.mount(Static(f"❌ {message}", id="error-message"))
        except Exception:
            pass

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
    

    
    # Vim-like navigation actions
    def action_nav_left(self) -> None:
        """Navigate left (h key) - move to previous focusable element."""
        self.focus_previous()
    
    def action_nav_down(self) -> None:
        """Navigate down (j key) - move to next focusable element."""
        self.focus_next()
    
    def action_nav_up(self) -> None:
        """Navigate up (k key) - move to previous focusable element."""
        self.focus_previous()
    
    def action_nav_right(self) -> None:
        """Navigate right (l key) - move to next focusable element."""
        self.focus_next()
    
    def action_select_item(self) -> None:
        """Select current focused item (enter key)."""
        focused = self.focused
        if focused and hasattr(focused, 'press'):
            # For Button widgets, directly press them
            focused.press()
        elif focused:
            # For other widgets, try to trigger their default action
            try:
                if hasattr(focused, 'action_select'):
                    focused.action_select()
            except AttributeError:
                pass
