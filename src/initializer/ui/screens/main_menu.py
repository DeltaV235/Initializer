"""Main menu screen for the Linux System Initializer."""

import re
import asyncio
from textual import on, work
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.screen import Screen
from textual.widgets import Button, Static, Rule, Label, ProgressBar, ListView, ListItem, LoadingIndicator
from textual.reactive import reactive
from textual.message import Message

from ...config_manager import ConfigManager
from ...modules.system_info import SystemInfoModule


class MainMenuScreen(Screen):
    """Main menu screen with configurator interface."""
    
    BINDINGS = [
        ("1", "select_segment", "System Status"),
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
    
    # Cache and loading states for each segment
    system_info_cache = reactive(None)
    system_info_loading = reactive(False)
    
    homebrew_cache = reactive(None)
    homebrew_loading = reactive(False)
    
    package_manager_cache = reactive(None)
    package_manager_loading = reactive(False)
    
    user_management_cache = reactive(None)
    user_management_loading = reactive(False)
    
    settings_cache = reactive(None)
    settings_loading = reactive(False)
    
    help_cache = reactive(None)
    help_loading = reactive(False)
    
    # Define segments configuration
    SEGMENTS = [
        {"id": "system_info", "name": "System Status"},
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
            self._update_panel_title(new_value)
        
    def compose(self) -> ComposeResult:
        """Compose the configurator interface."""
        with Container(id="main-container"):
            # Title section with configurator style
            yield Static(f"{self.app_config.name} Configurator v{self.app_config.version}", id="title")
            
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
                        
                        # Create button with fixed-width arrow indicator space
                        yield Button(f"  {segment['name']}", id=f"segment-{segment['id']}", classes="segment-item")
                
                # Right panel - Settings
                with Vertical(id="right-panel"):
                    with ScrollableContainer(id="settings-scroll"):
                        yield Static("Select a segment to view settings", id="settings-content")
    
    def on_mount(self) -> None:
        """Initialize when screen is mounted."""
        # Set initial segment content
        self.update_settings_panel()
        # Initialize button states
        self._update_segment_buttons(self.selected_segment)
        # Initialize panel title
        self._update_panel_title(self.selected_segment)
        # Set initial focus to the selected segment button
        try:
            initial_button = self.query_one(f"#segment-{self.selected_segment}", Button)
            initial_button.focus()
        except:
            pass
        
        # Schedule immediate content update after mount to ensure it's visible
        self.call_after_refresh(self._initial_content_load)
    
    def _initial_content_load(self) -> None:
        """Load initial content for the default selected segment."""
        # Force update the settings panel again to ensure content is visible
        self.update_settings_panel()
        self.refresh()
    
    def refresh_system_info(self) -> None:
        """Refresh system information cache."""
        self.system_info_cache = None
        self.system_info_loading = False
        if self.selected_segment == "system_info":
            self.update_settings_panel()
    
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
        # Show title
        container.mount(Label("System Status", classes="section-title"))
        
        # Check if we have cached data and not currently loading
        if self.system_info_cache and not self.system_info_loading:
            self._display_system_info(container, self.system_info_cache)
        elif self.system_info_loading:
            # Show loading indicator
            container.mount(LoadingIndicator())
            container.mount(Label("Loading system information...", classes="info-display"))
        else:
            # Start loading system info asynchronously
            self.system_info_loading = True
            container.mount(LoadingIndicator())
            container.mount(Label("Loading system information...", classes="info-display"))
            # Start the background task
            self._load_system_info()
    
    def _display_system_info(self, container: ScrollableContainer, all_info: dict) -> None:
        """Display comprehensive system information in the container."""
        # Handle error case
        if "error" in all_info:
            container.mount(Label(f"Error loading system info: {all_info['error']}", classes="info-display"))
            return
        
        # System & Distribution Information
        if "distribution" in all_info:
            container.mount(Label("🖥️ System", classes="info-key"))
            
            dist_info = all_info["distribution"]
            if "System" in dist_info:
                container.mount(Label(f"System: {dist_info['System']}", classes="info-display"))
            if "Distribution" in dist_info:
                container.mount(Label(f"Distribution: {dist_info['Distribution']}", classes="info-display"))
            if "Machine" in dist_info:
                container.mount(Label(f"Architecture: {dist_info['Machine']}", classes="info-display"))
            if "Release" in dist_info:
                container.mount(Label(f"Kernel: {dist_info['Release']}", classes="info-display"))
            if "Distro Version" in dist_info and dist_info["Distro Version"]:
                container.mount(Label(f"Version: {dist_info['Distro Version']}", classes="info-display"))
        
        # CPU Information
        if "cpu" in all_info:
            container.mount(Label("", classes="info-display"))  # Spacing
            container.mount(Label("🎯 CPU", classes="info-key"))
            
            cpu_info = all_info["cpu"]
            if "CPU Count" in cpu_info:
                container.mount(Label(f"CPU Cores: {cpu_info['CPU Count']}", classes="info-display"))
            if "Logical CPUs" in cpu_info:
                container.mount(Label(f"Logical CPUs: {cpu_info['Logical CPUs']}", classes="info-display"))
            if "Current Usage" in cpu_info:
                container.mount(Label(f"CPU Usage: {cpu_info['Current Usage']}", classes="info-display"))
            if "CPU Frequency" in cpu_info:
                container.mount(Label(f"CPU Frequency: {cpu_info['CPU Frequency']}", classes="info-display"))
            if "Processor" in cpu_info and cpu_info["Processor"]:
                container.mount(Label(f"Processor: {cpu_info['Processor']}", classes="info-display"))
        
        # Memory Information  
        if "memory" in all_info:
            container.mount(Label("", classes="info-display"))  # Spacing
            container.mount(Label("💾 Memory", classes="info-key"))
            
            memory_info = all_info["memory"]
            if "Total RAM" in memory_info:
                container.mount(Label(f"Total RAM: {memory_info['Total RAM']}", classes="info-display"))
            if "Available RAM" in memory_info:
                container.mount(Label(f"Available RAM: {memory_info['Available RAM']}", classes="info-display"))
            if "Used RAM" in memory_info:
                container.mount(Label(f"Used RAM: {memory_info['Used RAM']}", classes="info-display"))
            if "RAM Usage" in memory_info:
                container.mount(Label(f"Memory Usage: {memory_info['RAM Usage']}", classes="info-display"))
            if "Total Swap" in memory_info and memory_info["Total Swap"] != "0.0 B":
                container.mount(Label(f"Swap: {memory_info.get('Used Swap', '0')} / {memory_info['Total Swap']}", classes="info-display"))
        
        # Disk Information
        if "disk" in all_info:
            container.mount(Label("", classes="info-display"))  # Spacing
            container.mount(Label("💿 Storage", classes="info-key"))
            
            disk_info = all_info["disk"]
            if "Root Partition Usage" in disk_info:
                container.mount(Label(f"Disk Usage: {disk_info['Root Partition Usage']}", classes="info-display"))
            if "Root Partition Free" in disk_info:
                container.mount(Label(f"Free Space: {disk_info['Root Partition Free']}", classes="info-display"))
            if "Root Partition Total" in disk_info:
                container.mount(Label(f"Total Space: {disk_info['Root Partition Total']}", classes="info-display"))
            
            # Show additional partitions
            partition_count = 0
            for key in disk_info:
                if key.startswith("Partition") and " (" in key:
                    partition_count += 1
                    if partition_count <= 2:  # Show up to 2 additional partitions
                        mount_point = key.split("(")[1].rstrip(")")
                        container.mount(Label(f"Mount {mount_point}: {disk_info[key]}", classes="info-display"))
        
        # Network Information
        if "network" in all_info:
            container.mount(Label("", classes="info-display"))  # Spacing
            container.mount(Label("🌐 Network", classes="info-key"))
            
            network_info = all_info["network"]
            # Show network interfaces
            interface_count = 0
            for key, value in network_info.items():
                if key.startswith("Interface") and "lo" not in key.lower():
                    interface_count += 1
                    if interface_count <= 3:  # Show up to 3 interfaces
                        container.mount(Label(f"{key}: {value}", classes="info-display"))
            
            # Show network statistics if available
            if "Bytes Sent" in network_info:
                container.mount(Label(f"Network Sent: {network_info['Bytes Sent']}", classes="info-display"))
            if "Bytes Received" in network_info:
                container.mount(Label(f"Network Received: {network_info['Bytes Received']}", classes="info-display"))
        
        # Package Managers
        if "package_manager" in all_info:
            pkg_info = all_info["package_manager"]
            if pkg_info:
                container.mount(Label("", classes="info-display"))  # Spacing
                container.mount(Label("📦 Package Managers", classes="info-key"))
                
                # Show all detected package managers
                for pm_name, pm_status in pkg_info.items():
                    container.mount(Label(f"  {pm_name}: {pm_status}", classes="info-display"))
    
    @work(exclusive=True, thread=True)
    async def _load_system_info(self) -> None:
        """Load system information in background thread."""
        try:
            # Get system info in background thread (this may take time)
            all_info = self.system_info_module.get_all_info()
            
            # Update cache and loading state on main thread using app.call_from_thread
            def update_ui():
                self.system_info_cache = all_info
                self.system_info_loading = False
                
                # Refresh the panel if we're still on system_info segment
                if self.selected_segment == "system_info":
                    self.update_settings_panel()
                    # Force refresh the UI
                    self.refresh()
            
            self.app.call_from_thread(update_ui)
                
        except Exception as e:
            # Handle errors on main thread
            def update_error():
                self.system_info_loading = False
                self.system_info_cache = {"error": str(e)}
                if self.selected_segment == "system_info":
                    self.update_settings_panel()
                    # Force refresh the UI
                    self.refresh()
            
            self.app.call_from_thread(update_error)
    
    @work(exclusive=True, thread=True)
    async def _load_homebrew_info(self) -> None:
        """Load Homebrew information in background thread."""
        try:
            # Get homebrew config (this may involve checking system state)
            homebrew_config = self.modules_config.get("homebrew")
            if homebrew_config is None:
                homebrew_config = {"enabled": True, "auto_install": False, "packages": []}
            else:
                homebrew_config = homebrew_config.settings
            
            # Update cache and loading state on main thread using call_from_thread
            def update_ui():
                self.homebrew_cache = homebrew_config
                self.homebrew_loading = False
                
                # Refresh the panel if we're still on homebrew segment
                if self.selected_segment == "homebrew":
                    self.update_settings_panel()
                    # Force refresh the UI
                    self.refresh()
            
            self.app.call_from_thread(update_ui)
                
        except Exception as e:
            # Handle errors on main thread
            def update_error():
                self.homebrew_loading = False
                self.homebrew_cache = {"error": str(e)}
                if self.selected_segment == "homebrew":
                    self.update_settings_panel()
                    # Force refresh the UI
                    self.refresh()
            
            self.app.call_from_thread(update_error)
    
    def _display_homebrew_info(self, container: ScrollableContainer, homebrew_config: dict) -> None:
        """Display Homebrew information in the container."""
        # Handle error case
        if "error" in homebrew_config:
            container.mount(Label(f"Error loading Homebrew info: {homebrew_config['error']}", classes="info-display"))
            return
        
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
    
    @work(exclusive=True, thread=True)
    async def _load_package_manager_info(self) -> None:
        """Load Package Manager information in background thread."""
        try:
            # Get package manager config
            pkg_config = self.modules_config.get("package_manager")
            if pkg_config is None:
                pkg_config = {"auto_detect": True, "mirror_management": False}
            else:
                pkg_config = pkg_config.settings
            
            # Update cache and loading state on main thread using call_from_thread
            def update_ui():
                self.package_manager_cache = pkg_config
                self.package_manager_loading = False
                
                # Refresh the panel if we're still on package_manager segment
                if self.selected_segment == "package_manager":
                    self.update_settings_panel()
                    # Force refresh the UI
                    self.refresh()
            
            self.app.call_from_thread(update_ui)
                
        except Exception as e:
            # Handle errors on main thread
            def update_error():
                self.package_manager_loading = False
                self.package_manager_cache = {"error": str(e)}
                if self.selected_segment == "package_manager":
                    self.update_settings_panel()
                    # Force refresh the UI
                    self.refresh()
            
            self.app.call_from_thread(update_error)
    
    def _display_package_manager_info(self, container: ScrollableContainer, pkg_config: dict) -> None:
        """Display Package Manager information in the container."""
        # Handle error case
        if "error" in pkg_config:
            container.mount(Label(f"Error loading Package Manager info: {pkg_config['error']}", classes="info-display"))
            return
        
        container.mount(Label("► Auto-detect", classes="info-key"))
        auto_detect = "Yes" if pkg_config.get("auto_detect", True) else "No"
        container.mount(Static(f"{auto_detect}", classes="info-value"))
        
        container.mount(Label("► Mirror Management", classes="info-key"))
        mirror_mgmt = "Enabled" if pkg_config.get("mirror_management", False) else "Disabled"
        container.mount(Static(f"{mirror_mgmt}", classes="info-value"))
        
        container.mount(Label("► Supported Managers", classes="info-key"))
        managers = ["apt", "yum", "dnf", "pacman", "zypper"]
        container.mount(Static(", ".join(managers), classes="info-value"))
    
    @work(exclusive=True, thread=True)
    async def _load_user_management_info(self) -> None:
        """Load User Management information in background thread."""
        try:
            # Get user management config
            user_config = self.modules_config.get("user_management")
            if user_config is None:
                user_config = {"user_creation": True, "ssh_keys": True, "sudo_management": True}
            else:
                user_config = user_config.settings
            
            # Update cache and loading state on main thread using call_from_thread
            def update_ui():
                self.user_management_cache = user_config
                self.user_management_loading = False
                
                # Refresh the panel if we're still on user_management segment
                if self.selected_segment == "user_management":
                    self.update_settings_panel()
                    # Force refresh the UI
                    self.refresh()
            
            self.app.call_from_thread(update_ui)
                
        except Exception as e:
            # Handle errors on main thread
            def update_error():
                self.user_management_loading = False
                self.user_management_cache = {"error": str(e)}
                if self.selected_segment == "user_management":
                    self.update_settings_panel()
                    # Force refresh the UI
                    self.refresh()
            
            self.app.call_from_thread(update_error)
    
    def _display_user_management_info(self, container: ScrollableContainer, user_config: dict) -> None:
        """Display User Management information in the container."""
        # Handle error case
        if "error" in user_config:
            container.mount(Label(f"Error loading User Management info: {user_config['error']}", classes="info-display"))
            return
        
        container.mount(Label("► User Creation", classes="info-key"))
        user_creation = "Enabled" if user_config.get("user_creation", True) else "Disabled"
        container.mount(Static(f"{user_creation}", classes="info-value"))
        
        container.mount(Label("► SSH Key Management", classes="info-key"))
        ssh_keys = "Enabled" if user_config.get("ssh_keys", True) else "Disabled"
        container.mount(Static(f"{ssh_keys}", classes="info-value"))
        
        container.mount(Label("► Sudo Access", classes="info-key"))
        sudo_access = "Configurable" if user_config.get("sudo_management", True) else "Manual"
        container.mount(Static(f"{sudo_access}", classes="info-value"))
    
    @work(exclusive=True, thread=True)
    async def _load_settings_info(self) -> None:
        """Load Settings information in background thread."""
        try:
            # Get app config settings
            settings_info = {
                "theme": self.app_config.get("theme", "default"),
                "debug": self.app_config.get("debug", False),
                "auto_save": self.app_config.get("auto_save", True)
            }
            
            # Update cache and loading state on main thread using call_from_thread
            def update_ui():
                self.settings_cache = settings_info
                self.settings_loading = False
                
                # Refresh the panel if we're still on settings segment
                if self.selected_segment == "settings":
                    self.update_settings_panel()
                    # Force refresh the UI
                    self.refresh()
            
            self.app.call_from_thread(update_ui)
                
        except Exception as e:
            # Handle errors on main thread
            def update_error():
                self.settings_loading = False
                self.settings_cache = {"error": str(e)}
                if self.selected_segment == "settings":
                    self.update_settings_panel()
                    # Force refresh the UI
                    self.refresh()
            
            self.app.call_from_thread(update_error)
    
    def _display_settings_info(self, container: ScrollableContainer, settings_info: dict) -> None:
        """Display Settings information in the container."""
        # Handle error case
        if "error" in settings_info:
            container.mount(Label(f"Error loading Settings: {settings_info['error']}", classes="info-display"))
            return
        
        container.mount(Label("► Theme", classes="info-key"))
        current_theme = settings_info.get("theme", "default")
        container.mount(Static(f"{current_theme.title()}", classes="info-value"))
        
        container.mount(Label("► Debug Mode", classes="info-key"))
        debug_mode = "Enabled" if settings_info.get("debug", False) else "Disabled"
        container.mount(Static(f"{debug_mode}", classes="info-value"))
        
        container.mount(Label("► Auto-save", classes="info-key"))
        auto_save = "Enabled" if settings_info.get("auto_save", True) else "Disabled"
        container.mount(Static(f"{auto_save}", classes="info-value"))
        
        container.mount(Rule())
        container.mount(Label("Available Actions", classes="section-title"))
        container.mount(Static("• Change theme", classes="action-item"))
        container.mount(Static("• Export configuration", classes="action-item"))
        container.mount(Static("• Reset to defaults", classes="action-item"))
    
    @work(exclusive=True, thread=True)
    async def _load_help_info(self) -> None:
        """Load Help information in background thread."""
        try:
            # Get help info
            help_info = {
                "app_name": self.app_config.name,
                "app_version": self.app_config.version
            }
            
            # Update cache and loading state on main thread using call_from_thread
            def update_ui():
                self.help_cache = help_info
                self.help_loading = False
                
                # Refresh the panel if we're still on help segment
                if self.selected_segment == "help":
                    self.update_settings_panel()
                    # Force refresh the UI
                    self.refresh()
            
            self.app.call_from_thread(update_ui)
                
        except Exception as e:
            # Handle errors on main thread
            def update_error():
                self.help_loading = False
                self.help_cache = {"error": str(e)}
                if self.selected_segment == "help":
                    self.update_settings_panel()
                    # Force refresh the UI
                    self.refresh()
            
            self.app.call_from_thread(update_error)
    
    def _display_help_info(self, container: ScrollableContainer, help_info: dict) -> None:
        """Display Help information in the container."""
        # Handle error case
        if "error" in help_info:
            container.mount(Label(f"Error loading Help: {help_info['error']}", classes="info-display"))
            return
        
        container.mount(Label("► Keyboard Shortcuts", classes="info-key"))
        container.mount(Static("q - Quit application", classes="help-item"))
        container.mount(Static("s - Settings segment", classes="help-item"))
        container.mount(Static("? - Help segment", classes="help-item"))
        container.mount(Static("h/j/k/l - Vim navigation", classes="help-item"))
        container.mount(Static("Enter - Select item", classes="help-item"))
        
        container.mount(Label("► Segments", classes="info-key"))
        container.mount(Static("System Status - View system information", classes="help-item"))
        container.mount(Static("Homebrew - Manage Homebrew packages", classes="help-item"))
        container.mount(Static("Package Manager - Configure package managers", classes="help-item"))
        container.mount(Static("User Management - Manage users and SSH keys", classes="help-item"))
        container.mount(Static("Settings - Application configuration", classes="help-item"))
        
        container.mount(Rule())
        container.mount(Label("Version Information", classes="section-title"))
        container.mount(Static(f"Application: {help_info['app_name']} v{help_info['app_version']}", classes="version-info"))
        container.mount(Static("Framework: Rich/Textual", classes="version-info"))
    
    def _build_homebrew_settings(self, container: ScrollableContainer) -> None:
        """Build Homebrew settings panel."""
        container.mount(Label("Homebrew Configuration", classes="section-title"))
        container.mount(Rule())
        
        # Check if we have cached data and not currently loading
        if self.homebrew_cache and not self.homebrew_loading:
            self._display_homebrew_info(container, self.homebrew_cache)
        elif self.homebrew_loading:
            # Show loading indicator
            container.mount(LoadingIndicator())
            container.mount(Label("Loading Homebrew configuration...", classes="info-display"))
        else:
            # Start loading homebrew info asynchronously
            self.homebrew_loading = True
            container.mount(LoadingIndicator())
            container.mount(Label("Loading Homebrew configuration...", classes="info-display"))
            # Start the background task
            self._load_homebrew_info()
    
    def _build_package_manager_settings(self, container: ScrollableContainer) -> None:
        """Build Package Manager settings panel."""
        container.mount(Label("Package Manager Configuration", classes="section-title"))
        container.mount(Rule())
        
        # Check if we have cached data and not currently loading
        if self.package_manager_cache and not self.package_manager_loading:
            self._display_package_manager_info(container, self.package_manager_cache)
        elif self.package_manager_loading:
            # Show loading indicator
            container.mount(LoadingIndicator())
            container.mount(Label("Loading package manager configuration...", classes="info-display"))
        else:
            # Start loading package manager info asynchronously
            self.package_manager_loading = True
            container.mount(LoadingIndicator())
            container.mount(Label("Loading package manager configuration...", classes="info-display"))
            # Start the background task
            self._load_package_manager_info()
    
    def _build_user_management_settings(self, container: ScrollableContainer) -> None:
        """Build User Management settings panel."""
        container.mount(Label("User Management Configuration", classes="section-title"))
        container.mount(Rule())
        
        # Check if we have cached data and not currently loading
        if self.user_management_cache and not self.user_management_loading:
            self._display_user_management_info(container, self.user_management_cache)
        elif self.user_management_loading:
            # Show loading indicator
            container.mount(LoadingIndicator())
            container.mount(Label("Loading user management configuration...", classes="info-display"))
        else:
            # Start loading user management info asynchronously
            self.user_management_loading = True
            container.mount(LoadingIndicator())
            container.mount(Label("Loading user management configuration...", classes="info-display"))
            # Start the background task
            self._load_user_management_info()
    
    def _build_app_settings(self, container: ScrollableContainer) -> None:
        """Build application settings panel."""
        container.mount(Label("Application Settings", classes="section-title"))
        container.mount(Rule())
        
        # Check if we have cached data and not currently loading
        if self.settings_cache and not self.settings_loading:
            self._display_settings_info(container, self.settings_cache)
        elif self.settings_loading:
            # Show loading indicator
            container.mount(LoadingIndicator())
            container.mount(Label("Loading application settings...", classes="info-display"))
        else:
            # Start loading settings info asynchronously
            self.settings_loading = True
            container.mount(LoadingIndicator())
            container.mount(Label("Loading application settings...", classes="info-display"))
            # Start the background task
            self._load_settings_info()
    
    def _build_help_content(self, container: ScrollableContainer) -> None:
        """Build help content panel."""
        container.mount(Label("Help & Documentation", classes="section-title"))
        container.mount(Rule())
        
        # Check if we have cached data and not currently loading
        if self.help_cache and not self.help_loading:
            self._display_help_info(container, self.help_cache)
        elif self.help_loading:
            # Show loading indicator
            container.mount(LoadingIndicator())
            container.mount(Label("Loading help documentation...", classes="info-display"))
        else:
            # Start loading help info asynchronously
            self.help_loading = True
            container.mount(LoadingIndicator())
            container.mount(Label("Loading help documentation...", classes="info-display"))
            # Start the background task
            self._load_help_info()
    
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
            # Update panel title
            self._update_panel_title(segment_id)
    
    def _handle_focus_change(self) -> None:
        """Handle focus changes on segment buttons."""
        focused = self.focused
        if focused and hasattr(focused, 'id') and focused.id and focused.id.startswith("segment-"):
            segment_id = focused.id.replace("segment-", "")
            if segment_id != self.selected_segment:
                self.selected_segment = segment_id
                self.update_settings_panel()
                self._update_segment_buttons(segment_id)
                self._update_panel_title(segment_id)
    
    def _update_segment_buttons(self, selected_id: str) -> None:
        """Update segment button styles to show selection."""
        for segment in self.SEGMENTS:
            try:
                button = self.query_one(f"#segment-{segment['id']}", Button)
                if segment['id'] == selected_id:
                    # Use arrow in the reserved space (first 2 characters)
                    button.label = f"▶ {segment['name']}"
                    button.add_class("selected")
                else:
                    # Keep the reserved space with spaces
                    button.label = f"  {segment['name']}"
                    button.remove_class("selected")
            except:
                pass
    
    def _update_panel_title(self, selected_id: str) -> None:
        """Update the right panel title based on selected segment."""
        # Title label has been removed - this method is kept for compatibility
        pass
    
    # Legacy action methods for backward compatibility
    def action_homebrew(self) -> None:
        """Show Homebrew settings."""
        self.selected_segment = "homebrew"
        self.update_settings_panel()
        self._update_segment_buttons("homebrew")
        self._update_panel_title("homebrew")
        
    def action_package_manager(self) -> None:
        """Show package manager settings."""
        self.selected_segment = "package_manager" 
        self.update_settings_panel()
        self._update_segment_buttons("package_manager")
        self._update_panel_title("package_manager")
        
    def action_user_management(self) -> None:
        """Show user management settings."""
        self.selected_segment = "user_management"
        self.update_settings_panel()
        self._update_segment_buttons("user_management")
        self._update_panel_title("user_management")
        
    def action_settings(self) -> None:
        """Show application settings."""
        self.selected_segment = "settings"
        self.update_settings_panel()
        self._update_segment_buttons("settings")
        self._update_panel_title("settings")
        
    def action_help(self) -> None:
        """Show help content."""
        self.selected_segment = "help"
        self.update_settings_panel()
        self._update_segment_buttons("help")
        self._update_panel_title("help")
    
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
