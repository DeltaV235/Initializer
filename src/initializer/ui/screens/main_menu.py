"""Main menu screen for the Linux System Initializer."""

import re
from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.screen import Screen
from textual.widgets import Button, Static, Rule, Label, ProgressBar, ListView, ListItem
from textual.reactive import reactive
from textual.message import Message

from ...config_manager import ConfigManager
from ...modules.system_info import SystemInfoModule


class MainMenuScreen(Screen):
    """Main menu screen with configurator interface."""
    
    BINDINGS = [
        ("1", "select_segment", "System Info"),
        ("2", "select_segment", "Homebrew"),
        ("3", "select_segment", "Package Manager"),
        ("4", "select_segment", "User Management"),
        ("s", "select_segment", "Settings"),
        ("?", "select_segment", "Help"),
        ("q", "quit", "Quit"),
        ("enter", "select_item", "Select"),
        # Vim-like navigation
        ("h", "nav_left", "Left"),
        ("j", "nav_down", "Down"),
        ("k", "nav_up", "Up"),
        ("l", "nav_right", "Right"),
    ]
    
    selected_segment = reactive("system_info")
    
    # Define segments configuration
    SEGMENTS = [
        {"id": "system_info", "name": "System Info"},
        {"id": "homebrew", "name": "Homebrew"},
        {"id": "package_manager", "name": "Package Manager"},
        {"id": "user_management", "name": "User Management"},
        {"id": "settings", "name": "Settings"},
        {"id": "help", "name": "Help"},
    ]
    
    def __init__(self, config_manager: ConfigManager):
        super().__init__()
        self.config_manager = config_manager
        self.app_config = config_manager.get_app_config()
        self.modules_config = config_manager.get_modules_config()
        self.system_info_module = SystemInfoModule(config_manager)
    
    def watch_selected_segment(self, old_value: str, new_value: str) -> None:
        """React to segment selection changes."""
        if old_value != new_value:
            self.update_settings_panel()
            self._update_segment_buttons(new_value)
        
    def compose(self) -> ComposeResult:
        """Compose the configurator interface."""
        with Container(id="main-container"):
            # Title section with configurator style
            yield Static(f"{self.app_config.name} Configurator v{self.app_config.version}", id="title")
            yield Rule()
            
            # Main content area with left-right split
            with Horizontal(id="content-area"):
                # Left panel - Segments list
                with Vertical(id="left-panel"):
                    yield Label("Segments", classes="panel-title")
                    
                    # Create segments list
                    for segment in self.SEGMENTS:
                        # Only show enabled modules
                        if segment["id"] == "homebrew" and segment["id"] in self.modules_config and not self.modules_config[segment["id"]].enabled:
                            continue
                        if segment["id"] == "package_manager" and segment["id"] in self.modules_config and not self.modules_config[segment["id"]].enabled:
                            continue
                        if segment["id"] == "user_management" and segment["id"] in self.modules_config and not self.modules_config[segment["id"]].enabled:
                            continue
                        
                        yield Button(f"{segment['name']}", id=f"segment-{segment['id']}", classes="segment-item")
                
                # Right panel - Settings
                with Vertical(id="right-panel"):
                    yield Label("Settings", classes="panel-title", id="settings-title")
                    with ScrollableContainer(id="settings-scroll"):
                        yield Static("Select a segment to view settings", id="settings-content")
    
    def on_mount(self) -> None:
        """Initialize when screen is mounted."""
        # Set initial segment content
        self.update_settings_panel()
        # Initialize button states
        self._update_segment_buttons(self.selected_segment)
        # Set initial focus to the selected segment button
        try:
            initial_button = self.query_one(f"#segment-{self.selected_segment}", Button)
            initial_button.focus()
        except:
            pass
    
    def update_settings_panel(self) -> None:
        """Update the settings panel based on selected segment."""
        try:
            settings_container = self.query_one("#settings-scroll", ScrollableContainer)
            
            # Clear existing content
            children = list(settings_container.children)
            for child in children:
                child.remove()
            
            # Add content based on selected segment
            if self.selected_segment == "system_info":
                self._build_system_info_settings(settings_container)
            elif self.selected_segment == "homebrew":
                self._build_homebrew_settings(settings_container)
            elif self.selected_segment == "package_manager":
                self._build_package_manager_settings(settings_container)
            elif self.selected_segment == "user_management":
                self._build_user_management_settings(settings_container)
            elif self.selected_segment == "settings":
                self._build_app_settings(settings_container)
            elif self.selected_segment == "help":
                self._build_help_content(settings_container)
            else:
                settings_container.mount(Static("Select a segment to view settings", id="default-message"))
                
        except Exception as e:
            # Handle errors gracefully
            self._show_error_message(f"Settings Panel Error: {str(e)[:100]}")
    
    def _build_system_info_settings(self, container: ScrollableContainer) -> None:
        """Build system information settings panel."""
        # Get system info
        all_info = self.system_info_module.get_all_info()
        
        container.mount(Label("System Information Configuration", classes="section-title"))
        container.mount(Rule())
        
        container.mount(Label("► Enabled", classes="info-key"))
        container.mount(Static("✓ System information collection is enabled", classes="info-value"))
        
        container.mount(Label("► Export Format", classes="info-key"))  
        container.mount(Static("JSON, YAML, TXT formats supported", classes="info-value"))
        
        container.mount(Label("► Auto-refresh", classes="info-key"))
        container.mount(Static("Every 5 seconds", classes="info-value"))
        
        # Show current system status
        container.mount(Rule())
        container.mount(Label("Current System Status", classes="section-title"))
        
        # Show key system metrics
        if "distribution" in all_info:
            dist_info = all_info["distribution"]
            if "System" in dist_info:
                container.mount(Label(f"System: {dist_info['System']}", classes="info-display"))
            if "Distribution" in dist_info:
                container.mount(Label(f"Distribution: {dist_info['Distribution']}", classes="info-display"))
        
        if "cpu" in all_info and "Current Usage" in all_info["cpu"]:
            container.mount(Label(f"CPU Usage: {all_info['cpu']['Current Usage']}", classes="info-display"))
        
        if "memory" in all_info and "RAM Usage" in all_info["memory"]:
            container.mount(Label(f"Memory Usage: {all_info['memory']['RAM Usage']}", classes="info-display"))
    
    def _build_homebrew_settings(self, container: ScrollableContainer) -> None:
        """Build Homebrew settings panel."""
        container.mount(Label("Homebrew Configuration", classes="section-title"))
        container.mount(Rule())
        
        homebrew_config = self.modules_config.get("homebrew")
        if homebrew_config is None:
            homebrew_config = {"enabled": True, "auto_install": False, "packages": []}
        else:
            homebrew_config = homebrew_config.settings
        
        container.mount(Label("► Status", classes="info-key"))
        status = "Enabled" if homebrew_config.get("enabled", True) else "Disabled"
        container.mount(Static(f"{status}", classes="info-value"))
        
        container.mount(Label("► Auto-install", classes="info-key"))
        auto_install = "Yes" if homebrew_config.get("auto_install", False) else "No"
        container.mount(Static(f"{auto_install}", classes="info-value"))
        
        container.mount(Label("► Packages", classes="info-key"))
        packages = homebrew_config.get("packages", [])
        if packages:
            container.mount(Static(f"{len(packages)} packages configured", classes="info-value"))
            container.mount(Rule(line_style="dashed"))
            for pkg in packages[:10]:  # Show first 10 packages
                container.mount(Static(f"  • {pkg}", classes="package-item"))
            if len(packages) > 10:
                container.mount(Static(f"  ... and {len(packages) - 10} more", classes="package-item"))
        else:
            container.mount(Static("No packages configured", classes="info-value"))
    
    def _build_package_manager_settings(self, container: ScrollableContainer) -> None:
        """Build Package Manager settings panel."""
        container.mount(Label("Package Manager Configuration", classes="section-title"))
        container.mount(Rule())
        
        pkg_config = self.modules_config.get("package_manager")
        if pkg_config is None:
            pkg_config = {"auto_detect": True, "mirror_management": False}
        else:
            pkg_config = pkg_config.settings
        
        container.mount(Label("► Auto-detect", classes="info-key"))
        auto_detect = "Yes" if pkg_config.get("auto_detect", True) else "No"
        container.mount(Static(f"{auto_detect}", classes="info-value"))
        
        container.mount(Label("► Mirror Management", classes="info-key"))
        mirror_mgmt = "Enabled" if pkg_config.get("mirror_management", False) else "Disabled"
        container.mount(Static(f"{mirror_mgmt}", classes="info-value"))
        
        container.mount(Label("► Supported Managers", classes="info-key"))
        managers = ["apt", "yum", "dnf", "pacman", "zypper"]
        container.mount(Static(", ".join(managers), classes="info-value"))
    
    def _build_user_management_settings(self, container: ScrollableContainer) -> None:
        """Build User Management settings panel."""
        container.mount(Label("User Management Configuration", classes="section-title"))
        container.mount(Rule())
        
        user_config = self.modules_config.get("user_management")
        if user_config is None:
            user_config = {"user_creation": True, "ssh_keys": True, "sudo_management": True}
        else:
            user_config = user_config.settings
        
        container.mount(Label("► User Creation", classes="info-key"))
        user_creation = "Enabled" if user_config.get("user_creation", True) else "Disabled"
        container.mount(Static(f"{user_creation}", classes="info-value"))
        
        container.mount(Label("► SSH Key Management", classes="info-key"))
        ssh_keys = "Enabled" if user_config.get("ssh_keys", True) else "Disabled"
        container.mount(Static(f"{ssh_keys}", classes="info-value"))
        
        container.mount(Label("► Sudo Access", classes="info-key"))
        sudo_access = "Configurable" if user_config.get("sudo_management", True) else "Manual"
        container.mount(Static(f"{sudo_access}", classes="info-value"))
    
    def _build_app_settings(self, container: ScrollableContainer) -> None:
        """Build application settings panel."""
        container.mount(Label("Application Settings", classes="section-title"))
        container.mount(Rule())
        
        container.mount(Label("► Theme", classes="info-key"))
        current_theme = self.app_config.get("theme", "default")
        container.mount(Static(f"{current_theme.title()}", classes="info-value"))
        
        container.mount(Label("► Debug Mode", classes="info-key"))
        debug_mode = "Enabled" if self.app_config.get("debug", False) else "Disabled"
        container.mount(Static(f"{debug_mode}", classes="info-value"))
        
        container.mount(Label("► Auto-save", classes="info-key"))
        auto_save = "Enabled" if self.app_config.get("auto_save", True) else "Disabled"
        container.mount(Static(f"{auto_save}", classes="info-value"))
        
        container.mount(Rule())
        container.mount(Label("Available Actions", classes="section-title"))
        container.mount(Static("• Change theme", classes="action-item"))
        container.mount(Static("• Export configuration", classes="action-item"))
        container.mount(Static("• Reset to defaults", classes="action-item"))
    
    def _build_help_content(self, container: ScrollableContainer) -> None:
        """Build help content panel."""
        container.mount(Label("Help & Documentation", classes="section-title"))
        container.mount(Rule())
        
        container.mount(Label("► Keyboard Shortcuts", classes="info-key"))
        container.mount(Static("q - Quit application", classes="help-item"))
        container.mount(Static("s - Settings segment", classes="help-item"))
        container.mount(Static("? - Help segment", classes="help-item"))
        container.mount(Static("h/j/k/l - Vim navigation", classes="help-item"))
        container.mount(Static("Enter - Select item", classes="help-item"))
        
        container.mount(Label("► Segments", classes="info-key"))
        container.mount(Static("System Info - View system information", classes="help-item"))
        container.mount(Static("Homebrew - Manage Homebrew packages", classes="help-item"))
        container.mount(Static("Package Manager - Configure package managers", classes="help-item"))
        container.mount(Static("User Management - Manage users and SSH keys", classes="help-item"))
        container.mount(Static("Settings - Application configuration", classes="help-item"))
        
        container.mount(Rule())
        container.mount(Label("Version Information", classes="section-title"))
        container.mount(Static(f"Application: {self.app_config.name} v{self.app_config.version}", classes="version-info"))
        container.mount(Static("Framework: Rich/Textual", classes="version-info"))
    
    def _show_error_message(self, message: str) -> None:
        """Show error message in the settings panel."""
        try:
            settings_container = self.query_one("#settings-scroll", ScrollableContainer)
            # Clear existing content
            children = list(settings_container.children)
            for child in children:
                child.remove()
            settings_container.mount(Static(f"❌ {message}", id="error-message"))
        except Exception:
            pass
    
    @on(Button.Pressed)
    def handle_segment_selection(self, event: Button.Pressed) -> None:
        """Handle segment button selection."""
        button_id = event.button.id
        if button_id and button_id.startswith("segment-"):
            segment_id = button_id.replace("segment-", "")
            self.selected_segment = segment_id
            self.update_settings_panel()
            
            # Update button styles to show selection
            self._update_segment_buttons(segment_id)
    
    def _handle_focus_change(self) -> None:
        """Handle focus changes on segment buttons."""
        focused = self.focused
        if focused and hasattr(focused, 'id') and focused.id and focused.id.startswith("segment-"):
            segment_id = focused.id.replace("segment-", "")
            if segment_id != self.selected_segment:
                self.selected_segment = segment_id
                self.update_settings_panel()
                self._update_segment_buttons(segment_id)
    
    def _update_segment_buttons(self, selected_id: str) -> None:
        """Update segment button styles to show selection."""
        for segment in self.SEGMENTS:
            try:
                button = self.query_one(f"#segment-{segment['id']}", Button)
                if segment['id'] == selected_id:
                    button.label = f"▶ {segment['name']}"
                    button.add_class("selected")
                else:
                    button.label = segment['name']
                    button.remove_class("selected")
            except:
                pass
    
    # Legacy action methods for backward compatibility
    def action_homebrew(self) -> None:
        """Show Homebrew settings."""
        self.selected_segment = "homebrew"
        self.update_settings_panel()
        self._update_segment_buttons("homebrew")
        
    def action_package_manager(self) -> None:
        """Show package manager settings."""
        self.selected_segment = "package_manager" 
        self.update_settings_panel()
        self._update_segment_buttons("package_manager")
        
    def action_user_management(self) -> None:
        """Show user management settings."""
        self.selected_segment = "user_management"
        self.update_settings_panel()
        self._update_segment_buttons("user_management")
        
    def action_settings(self) -> None:
        """Show application settings."""
        self.selected_segment = "settings"
        self.update_settings_panel()
        self._update_segment_buttons("settings")
        
    def action_help(self) -> None:
        """Show help content."""
        self.selected_segment = "help"
        self.update_settings_panel()
        self._update_segment_buttons("help")
    
    def action_quit(self) -> None:
        """Exit the application."""
        self.app.exit()
    

    
    # Vim-like navigation actions
    def action_nav_left(self) -> None:
        """Navigate left (h key) - move to previous focusable element."""
        self.focus_previous()
        self._handle_focus_change()
    
    def action_nav_down(self) -> None:
        """Navigate down (j key) - move to next focusable element."""
        self.focus_next()
        self._handle_focus_change()
    
    def action_nav_up(self) -> None:
        """Navigate up (k key) - move to previous focusable element."""
        self.focus_previous()
        self._handle_focus_change()
    
    def action_nav_right(self) -> None:
        """Navigate right (l key) - move to next focusable element."""
        self.focus_next()
        self._handle_focus_change()
    
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
