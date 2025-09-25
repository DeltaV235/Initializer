"""Main menu screen for the Linux System Initializer."""

import re
import asyncio
from textual import on, work
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.screen import Screen
from textual.widgets import Button, Static, Rule, Label, ProgressBar, ListView, ListItem
from textual.reactive import reactive
from textual.message import Message

from ...config_manager import ConfigManager
from ...modules.system_info import SystemInfoModule
from ...modules.package_manager import PackageManagerDetector
from ...modules.app_installer import AppInstaller
from ...modules.software_models import ApplicationSuite, Application
from ...utils.logger import get_ui_logger

# Initialize logger for this screen
logger = get_ui_logger("main_menu")


class MainMenuScreen(Screen):
    """Main menu screen with configurator interface."""
    
    BINDINGS = [
        ("s", "select_segment", "Settings"),
        ("q", "quit", "Quit"),
        ("enter", "select_item", "Select"),
        ("tab", "switch_panel", "Switch Panel"),
        ("a", "apply_app_changes", "Apply Changes"),
        ("r", "refresh_current_page", "Refresh"),
        # Vim-like navigation
        ("h", "nav_left", "Left"),
        ("j", "nav_down", "Down"),
        ("k", "nav_up", "Up"),
        ("l", "nav_right", "Right"),
    ]
    
    selected_segment = reactive("system_info")

    # Track which panel currently has focus for reliable Esc key behavior
    current_panel_focus = reactive("unset")  # "left", "right", or "unset" initially
    
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
    
    app_install_cache = reactive(None)
    app_install_loading = reactive(False)
    app_selection_state = reactive({})
    app_focused_index = reactive(0)
    
    # Define segments configuration
    SEGMENTS = [
        {"id": "system_info", "name": "System Status"},
        {"id": "package_manager", "name": "Package Manager"},
        {"id": "app_install", "name": "Application Manager"},
        {"id": "homebrew", "name": "Homebrew"},
        {"id": "user_management", "name": "User Management"},
        {"id": "settings", "name": "Settings"},
    ]
    
    def __init__(self, config_manager: ConfigManager):
        super().__init__()
        self.config_manager = config_manager
        self.app_config = config_manager.get_app_config()
        self.modules_config = config_manager.get_modules_config()
        self.system_info_module = SystemInfoModule(config_manager)
        self.app_installer = AppInstaller(config_manager)

        # Initialize app install specific attributes
        self.app_expanded_suites = set()  # Track which suites are expanded
    
    def watch_selected_segment(self, old_value: str, new_value: str) -> None:
        """React to segment selection changes."""
        if old_value != new_value:
            logger.debug(f"Segment changed from '{old_value}' to '{new_value}'")
            self.update_settings_panel()
            # Only show arrow if current panel focus is explicitly "left"
            is_left_focused = (self.current_panel_focus == "left")
            logger.debug(f"Current panel focus: '{self.current_panel_focus}', showing arrow: {is_left_focused}")
            self._update_segment_buttons(new_value, show_arrow=is_left_focused)
            self._update_panel_title(new_value)
            # Update help text when segment changes
            self._update_help_text()

    def watch_current_panel_focus(self, old_value: str, new_value: str) -> None:
        """React to panel focus changes and update arrows accordingly."""
        logger.debug(f"watch_current_panel_focus triggered: '{old_value}' → '{new_value}'")
        if old_value != new_value:
            logger.debug(f"Panel focus changed from '{old_value}' to '{new_value}'")
            # Update arrow display based on new panel focus
            is_left_focused = (new_value == "left")
            logger.debug(f"Updating segment buttons for '{self.selected_segment}' with arrow: {is_left_focused}")
            self._update_segment_buttons(self.selected_segment, show_arrow=is_left_focused)

            # Update right panel arrows based on current segment and focus
            if new_value == "left":
                # When switching to left panel, clear right panel arrows
                if self.selected_segment == "package_manager":
                    self._clear_pm_focus_indicators()
                elif self.selected_segment == "app_install":
                    self._clear_app_focus_indicators()
            elif new_value == "right":
                # When switching to right panel, update right panel arrows based on current focus
                if self.selected_segment == "package_manager" and hasattr(self, '_pm_focused_item') and self._pm_focused_item:
                    self._update_pm_focus_indicators()
                elif self.selected_segment == "app_install":
                    self._update_app_focus_indicators()
        else:
            logger.debug("Panel focus value same, no update needed")
        
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
                        
                        # Create button with numbered prefix for quick select
                        segment_number = next(i+1 for i, s in enumerate(self.SEGMENTS) if s['id'] == segment['id'])
                        yield Button(f"  {segment_number}. {segment['name']}", id=f"segment-{segment['id']}", classes="segment-item")
                
                # Right panel - Settings
                with Vertical(id="right-panel"):
                    yield Label("Settings", id="right-panel-title", classes="panel-title")
                    with ScrollableContainer(id="settings-scroll"):
                        yield Static("Select a segment to view settings", id="settings-content")
            
            # Help box at the bottom
            with Container(id="help-box"):
                yield Label("Loading...", classes="help-text")
    
    def on_mount(self) -> None:
        """Initialize when screen is mounted."""
        logger.info("MainMenuScreen mounting...")
        logger.debug(f"Initial segment: '{self.selected_segment}', initial panel focus: '{self.current_panel_focus}'")

        # Set initial segment content
        self.update_settings_panel()
        # Set initial focus to the selected segment button
        try:
            initial_button = self.query_one(f"#segment-{self.selected_segment}", Button)
            initial_button.focus()
            # Highlight the left panel as initially focused
            self._update_panel_focus(is_left_focused=True)
            logger.debug("Initial focus set to left panel")
        except Exception as e:
            logger.error(f"Failed to set initial focus: {e}")
            pass

        # Initialize button states after panel focus is set
        # Arrow display will be handled by watch_current_panel_focus when _update_panel_focus is called
        logger.debug("Initialization completed, arrow state should be managed by watch_current_panel_focus")

        # Initialize panel title
        self._update_panel_title(self.selected_segment)

        # Schedule immediate content update after mount to ensure it's visible
        self.call_after_refresh(self._initial_content_load)

        # Initialize help text after everything is set up
        self.call_after_refresh(self._update_help_text)

        logger.info("MainMenuScreen mounted successfully")
    
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
            
            # Clear existing content completely
            children = list(settings_container.children)
            for child in children:
                try:
                    child.remove()
                except Exception:
                    pass
            
            # Reset package manager focus state and cleanup when switching segments
            if self.selected_segment != "package_manager":
                self._pm_focused_item = None
                if hasattr(self, '_pm_unique_suffix'):
                    del self._pm_unique_suffix

            # Reset app install focus state when switching segments
            if self.selected_segment != "app_install":
                self.app_focused_index = 0
            
            # Force a refresh to ensure widgets are fully cleared
            self.refresh()
            
            # Add content based on selected segment
            if self.selected_segment == "system_info":
                self._build_system_info_settings(settings_container)
            elif self.selected_segment == "homebrew":
                self._build_homebrew_settings(settings_container)
            elif self.selected_segment == "package_manager":
                self._build_package_manager_settings(settings_container)
            elif self.selected_segment == "app_install":
                self._build_app_install_settings(settings_container)
            elif self.selected_segment == "user_management":
                self._build_user_management_settings(settings_container)
            elif self.selected_segment == "settings":
                self._build_app_settings(settings_container)
            else:
                settings_container.mount(Static("Select a segment to view settings", id="default-message"))
                
        except Exception as e:
            # Handle errors gracefully
            self._show_error_message(f"Settings Panel Error: {str(e)[:100]}")
    
    def _build_system_info_settings(self, container: ScrollableContainer) -> None:
        """Build system information settings panel."""
        # Check if we have cached data and not currently loading
        if self.system_info_cache and not self.system_info_loading:
            # Enable scrollbar for content
            container.styles.scrollbar_size = 1
            self._display_system_info(container, self.system_info_cache)
        elif self.system_info_loading:
            # Disable scrollbar when loading
            container.styles.scrollbar_size = 0
            # Show simple loading text
            container.mount(Label("Loading...", classes="loading-text"))
        else:
            # Disable scrollbar when loading
            container.styles.scrollbar_size = 0
            # Start loading system info asynchronously
            self.system_info_loading = True
            container.mount(Label("Loading...", classes="loading-text"))
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
            container.mount(Label("🖥️ System", classes="section-header"))
            
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
            container.mount(Label("🎯 CPU", classes="section-header"))
            
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
            container.mount(Label("💾 Memory", classes="section-header"))
            
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
            container.mount(Label("💿 Storage", classes="section-header"))
            
            disk_info = all_info["disk"]
            
            # Display all disk information dynamically
            for key, value in disk_info.items():
                if not value or (isinstance(value, str) and not value.strip()):
                    continue
                    
                # Format the display based on key type
                if "Usage" in key:
                    container.mount(Label(f"Disk Usage: {value}", classes="info-display"))
                elif "Free" in key:
                    container.mount(Label(f"Free Space: {value}", classes="info-display"))
                elif "Total" in key:
                    container.mount(Label(f"Total Space: {value}", classes="info-display"))
                elif key.startswith("Mount"):
                    container.mount(Label(f"{key}: {value}", classes="info-display"))
                elif "Available" in key:
                    container.mount(Label(f"{key}: {value}", classes="info-display"))
                elif "Partition" in key:
                    container.mount(Label(f"{key}: {value}", classes="info-display"))
        
        # Network Information
        if "network" in all_info:
            container.mount(Label("", classes="info-display"))  # Spacing
            container.mount(Label("🌐 Network", classes="section-header"))
            
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
        
        # Package Managers & Sources
        if "package_manager" in all_info:
            pkg_info = all_info["package_manager"]
            if pkg_info:
                container.mount(Label("", classes="info-display"))  # Spacing
                container.mount(Label("📦 Package Managers", classes="section-header"))
                
                # Show all detected package managers and their sources
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
        
        container.mount(Label("► Status", classes="section-header"))
        status = "Enabled" if homebrew_config.get("enabled", True) else "Disabled"
        container.mount(Static(f"{status}", classes="info-value"))
        
        container.mount(Label("► Auto-install", classes="section-header"))
        auto_install = "Yes" if homebrew_config.get("auto_install", False) else "No"
        container.mount(Static(f"{auto_install}", classes="info-value"))
        
        container.mount(Label("► Packages", classes="section-header"))
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
            # Detect package managers and get their info
            detector = PackageManagerDetector(self.config_manager)
            package_managers = detector.package_managers
            primary_pm = detector.get_primary_package_manager()
            
            # Build package manager info
            pkg_info = {
                "package_managers": package_managers,
                "primary": primary_pm,
                "count": len(package_managers)
            }
            
            # Update cache and loading state on main thread using call_from_thread
            def update_ui():
                self.package_manager_cache = pkg_info
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
    
    def _display_package_manager_info(self, container: ScrollableContainer, pkg_info: dict) -> None:
        """Display Package Manager information in the container."""
        # Handle error case
        if "error" in pkg_info:
            container.mount(Label(f"Error loading Package Manager info: {pkg_info['error']}", classes="info-display"))
            return
        
        # Show primary package manager (available managers)
        primary = pkg_info.get("primary")
        if primary:
            container.mount(Label("Available Package Managers", classes="section-header"))
            # Use unique IDs to avoid conflicts
            import time
            unique_suffix = str(int(time.time() * 1000))[-6:]  # Use timestamp for uniqueness
            
            # Create clickable static text for the package manager
            pm_text = Static(f"  {primary.name.upper()}", id=f"pm-manager-item-{unique_suffix}", classes="pm-item-text")
            container.mount(pm_text)
            
            container.mount(Rule())
            
            # Show current source (clickable)
            container.mount(Label("Current Source", classes="section-header"))
            if primary.current_source:
                # Truncate long URLs for display
                source = primary.current_source
                if len(source) > 60:
                    source = source[:57] + "..."
                source_text = Static(f"  {source}", id=f"pm-source-item-{unique_suffix}", classes="pm-item-text")
                container.mount(source_text)
            else:
                source_text = Static("  Not configured", id=f"pm-source-item-{unique_suffix}", classes="pm-item-text")
                container.mount(source_text)
        else:
            container.mount(Label("No package managers detected", classes="info-display"))
            
        # Store the primary PM and unique suffix for later use
        if hasattr(self, '_primary_pm'):
            del self._primary_pm
        if primary:
            self._primary_pm = primary
            self._pm_unique_suffix = unique_suffix
            
        # Initialize focus state - reset it each time we rebuild the panel
        self._pm_focused_item = None  # Track which item has focus
        # Don't show any arrows initially when rebuilding
        self._update_pm_focus_indicators(clear_left_arrows=False)
    
    def _update_pm_focus_indicators(self, clear_left_arrows: bool = False) -> None:
        """Update arrow indicators for package manager items."""
        if not hasattr(self, '_pm_unique_suffix'):
            return
        
        # Clear left panel arrows if requested
        if clear_left_arrows:
            self._update_segment_buttons(self.selected_segment, show_arrow=False)
            
        try:
            # Update package manager item using unique ID
            pm_item = self.query_one(f"#pm-manager-item-{self._pm_unique_suffix}", Static)
            if hasattr(self, '_primary_pm') and self._primary_pm:
                # Only show arrow if current panel focus is "right" and this item is focused
                is_right_focused = (self.current_panel_focus == "right")
                if self._pm_focused_item == "manager" and is_right_focused:
                    pm_item.update(f"[#7dd3fc]▶[/#7dd3fc] {self._primary_pm.name.upper()}")
                else:
                    pm_item.update(f"  {self._primary_pm.name.upper()}")
        except:
            pass

        try:
            # Update source item using unique ID
            source_item = self.query_one(f"#pm-source-item-{self._pm_unique_suffix}", Static)
            if hasattr(self, '_primary_pm') and self._primary_pm:
                source = self._primary_pm.current_source or "Not configured"
                if len(source) > 60:
                    source = source[:57] + "..."
                # Only show arrow if current panel focus is "right" and this item is focused
                is_right_focused = (self.current_panel_focus == "right")
                if self._pm_focused_item == "source" and is_right_focused:
                    source_item.update(f"[#7dd3fc]▶[/#7dd3fc] {source}")
                else:
                    source_item.update(f"  {source}")
        except:
            pass
    
    def _clear_pm_focus_indicators(self) -> None:
        """Clear all arrow indicators in package manager section."""
        if not hasattr(self, '_pm_unique_suffix'):
            return
            
        try:
            # Clear package manager item arrow
            pm_item = self.query_one(f"#pm-manager-item-{self._pm_unique_suffix}", Static)
            if hasattr(self, '_primary_pm') and self._primary_pm:
                pm_item.update(f"  {self._primary_pm.name.upper()}")
        except:
            pass
            
        try:
            # Clear source item arrow if it exists
            source_item = self.query_one(f"#pm-source-item-{self._pm_unique_suffix}", Static)
            if hasattr(self, '_primary_pm') and self._primary_pm:
                source = self._primary_pm.current_source or "Not configured"
                if len(source) > 60:
                    source = source[:57] + "..."
                source_item.update(f"  {source}")
        except:
            pass

    def _clear_app_focus_indicators(self) -> None:
        """Clear all arrow indicators in app install section."""
        if not hasattr(self, '_app_unique_suffix'):
            return

        if not self.app_install_cache or isinstance(self.app_install_cache, dict):
            return

        # Build display items to match the current display structure
        display_items = self._build_display_items()

        # Clear all display items - use container structure matching the display logic
        try:
            for i, (item_type, item, indent_level) in enumerate(display_items):
                container_id = f"app-container-{i}-{self._app_unique_suffix}"
                try:
                    from textual.containers import Horizontal
                    container_widget = self.query_one(f"#{container_id}", Horizontal)

                    # Get the status widget (first child)
                    status_widgets = container_widget.query(".app-item-status")
                    if status_widgets:
                        status_widget = status_widgets.first()

                        # Always clear arrow (use spaces instead)
                        arrow = "  "

                        # Calculate indentation
                        indent = "  " * indent_level

                        if item_type == "suite_or_app" and hasattr(item, 'components'):
                            # Suite item - get suite status
                            installed_count = sum(1 for c in item.components if c.installed)
                            total_count = len(item.components)

                            if installed_count == 0:
                                status_text = f"[bright_black]○ {installed_count}/{total_count}[/bright_black]"
                            elif installed_count == total_count:
                                status_text = f"[green]● {installed_count}/{total_count}[/green]"
                            else:
                                status_text = f"[yellow]◐ {installed_count}/{total_count}[/yellow]"

                            status_display = f"{arrow}{indent}{status_text}"

                        elif item_type == "component":
                            # Component item
                            is_selected = self.app_selection_state.get(item.name, False)
                            if item.installed and not is_selected:
                                status_text = "[red]- To Uninstall[/red]"
                            elif item.installed and is_selected:
                                status_text = "[green]✓ Installed[/green]"
                            elif not item.installed and is_selected:
                                status_text = "[yellow]+ To Install[/yellow]"
                            else:
                                status_text = "[bright_black]○ Available[/bright_black]"

                            status_display = f"{arrow}{indent}{status_text}"

                        else:
                            # Standalone application
                            is_selected = self.app_selection_state.get(item.name, False)
                            if item.installed and not is_selected:
                                status_text = "[red]- To Uninstall[/red]"
                            elif item.installed and is_selected:
                                status_text = "[green]✓ Installed[/green]"
                            elif not item.installed and is_selected:
                                status_text = "[yellow]+ To Install[/yellow]"
                            else:
                                status_text = "[bright_black]○ Available[/bright_black]"

                            status_display = f"{arrow}{indent}{status_text}"

                        # Update status widget
                        status_widget.update(status_display)

                except Exception:
                    # If we can't find the container, skip this item
                    continue
        except Exception:
            pass
    
    def _handle_pm_item_selection(self) -> None:
        """Handle selection of package manager items."""
        if self._pm_focused_item == "manager":
            # Clear panel focus before showing modal
            self._clear_panel_focus()
            # Show package manager installation modal instead of separate screen
            from .package_manager_install_modal import PackageManagerInstallModal
            def on_install_actions_selected(actions: list):
                # Handle installation actions if needed
                pass
            self.app.push_screen(PackageManagerInstallModal(on_install_actions_selected, self.config_manager))
        elif self._pm_focused_item == "source":
            # Directly show source selection modal without intermediate screen
            self._show_source_selection_modal()
    
    def _show_source_selection_modal(self) -> None:
        """Show source selection modal directly from main menu."""
        # Clear panel focus before showing modal
        self._clear_panel_focus()

        try:
            from ...modules.package_manager import PackageManagerDetector
            from .source_selection_modal import SourceSelectionModal
            from .mirror_confirmation_modal import MirrorConfirmationModal
            
            # Get the primary package manager
            detector = PackageManagerDetector(self.config_manager)
            primary_pm = detector.get_primary_package_manager()
            
            if not primary_pm:
                self._show_message("No package manager detected", error=True)
                return
            
            # Create source selection modal first to capture its reference
            source_modal_ref = SourceSelectionModal(primary_pm, None, self.config_manager)

            def on_source_selected(selected_source: str):
                # Show confirmation modal
                def on_confirmation_result(success: bool, message: str):
                    if success:
                        # Update the package manager's current source
                        primary_pm.current_source = selected_source
                        # Refresh package manager display in main menu
                        self._update_package_manager_info()
                        self._show_message("Mirror source updated successfully")
                    else:
                        self._show_message(message, error=not success)

                # Show confirmation modal with source modal reference and main menu reference
                try:
                    self.app.push_screen(
                        MirrorConfirmationModal(primary_pm, selected_source, on_confirmation_result, self.config_manager, source_modal_ref, self)
                    )
                except Exception as e:
                    self._show_message(f"Error showing confirmation: {str(e)}", error=True)

            # Set the callback after creating the modal
            source_modal_ref.callback = on_source_selected

            # Show source selection modal
            self.app.push_screen(source_modal_ref)
            
        except Exception as e:
            self._show_message(f"Error opening source selection: {str(e)}", error=True)
    
    def _navigate_pm_items(self, direction: str) -> None:
        """Navigate between package manager items."""
        if not hasattr(self, '_primary_pm') or not self._primary_pm:
            return
            
        items = ["manager", "source"]
        
        if self._pm_focused_item is None:
            # Start with first item
            self._pm_focused_item = items[0]
        else:
            try:
                current_index = items.index(self._pm_focused_item)
                if direction == "down" and current_index < len(items) - 1:
                    self._pm_focused_item = items[current_index + 1]
                elif direction == "up" and current_index > 0:
                    self._pm_focused_item = items[current_index - 1]
            except ValueError:
                self._pm_focused_item = items[0]
        
        self._update_pm_focus_indicators(clear_left_arrows=True)
    
    def _is_in_pm_section(self) -> bool:
        """Check if we're currently in the package manager section."""
        return (self.selected_segment == "package_manager" and 
                hasattr(self, '_pm_focused_item'))
    
    
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
        
        container.mount(Label("► User Creation", classes="section-header"))
        user_creation = "Enabled" if user_config.get("user_creation", True) else "Disabled"
        container.mount(Static(f"{user_creation}", classes="info-value"))
        
        container.mount(Label("► SSH Key Management", classes="section-header"))
        ssh_keys = "Enabled" if user_config.get("ssh_keys", True) else "Disabled"
        container.mount(Static(f"{ssh_keys}", classes="info-value"))
        
        container.mount(Label("► Sudo Access", classes="section-header"))
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
        
        container.mount(Label("► Theme", classes="section-header"))
        current_theme = settings_info.get("theme", "default")
        container.mount(Static(f"{current_theme.title()}", classes="info-value"))
        
        container.mount(Label("► Debug Mode", classes="section-header"))
        debug_mode = "Enabled" if settings_info.get("debug", False) else "Disabled"
        container.mount(Static(f"{debug_mode}", classes="info-value"))
        
        container.mount(Label("► Auto-save", classes="section-header"))
        auto_save = "Enabled" if settings_info.get("auto_save", True) else "Disabled"
        container.mount(Static(f"{auto_save}", classes="info-value"))
        
        container.mount(Rule())
        container.mount(Label("Available Actions", classes="section-header"))
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
        
        container.mount(Label("► Keyboard Shortcuts", classes="section-header"))
        container.mount(Static("Q=Quit | S=Settings | ?=Help", classes="help-item"))
        container.mount(Static("H/J/K/L=Navigate | Enter=Select", classes="help-item"))
        container.mount(Static("1-5=Quick Select Segment", classes="help-item"))
        
        container.mount(Label("► Segments", classes="section-header"))
        container.mount(Static("System Status - View system information", classes="help-item"))
        container.mount(Static("Homebrew - Manage Homebrew packages", classes="help-item"))
        container.mount(Static("Package Manager - Configure package managers", classes="help-item"))
        container.mount(Static("User Management - Manage users and SSH keys", classes="help-item"))
        container.mount(Static("Settings - Application configuration", classes="help-item"))
        
        container.mount(Rule())
        container.mount(Label("Version Information", classes="section-header"))
        container.mount(Static(f"Application: {help_info['app_name']} v{help_info['app_version']}", classes="version-info"))
        container.mount(Static("Framework: Rich/Textual", classes="version-info"))
    
    def _build_app_install_settings(self, container: ScrollableContainer) -> None:
        """Build App installation settings panel."""
        # Check if we have cached data and not currently loading
        if self.app_install_cache and not self.app_install_loading:
            # Enable scrollbar for content
            container.styles.scrollbar_size = 1
            self._display_app_install_list(container, self.app_install_cache)
        elif self.app_install_loading:
            # Disable scrollbar when loading
            container.styles.scrollbar_size = 0
            # Show simple loading text
            container.mount(Label("Loading...", classes="loading-text"))
        else:
            # Disable scrollbar when loading
            container.styles.scrollbar_size = 0
            # Start loading app info asynchronously
            self.app_install_loading = True
            container.mount(Label("Loading...", classes="loading-text"))
            # Start the background task
            self._load_app_install_info()
    
    @work(exclusive=True, thread=True)
    async def _load_app_install_info(self) -> None:
        """Load App installation information in background thread."""
        try:
            # Get all software items (suites and standalone) with their installation status
            software_items = self.app_installer.get_all_software_items()

            # Initialize selection state based on current installation status
            selection_state = {}
            expanded_suites = set()

            # Collect all applications for selection state
            all_applications = self.app_installer._get_all_applications_flat()
            for app in all_applications:
                selection_state[app.name] = app.installed

            # Update cache and loading state on main thread using call_from_thread
            def update_ui():
                self.app_install_cache = software_items
                self.app_selection_state = selection_state
                self.app_expanded_suites = expanded_suites  # Track expanded suites
                self.app_install_loading = False
                self.app_focused_index = 0
                self._ensure_valid_focus_index()  # Ensure valid focus after data load

                # Refresh the panel if we're still on app_install segment
                if self.selected_segment == "app_install":
                    self.update_settings_panel()
                    # Update help text for app section
                    self._update_help_text()
                    # Force refresh the UI
                    self.refresh()
            
            self.app.call_from_thread(update_ui)
                
        except Exception as e:
            # Handle errors on main thread
            def update_error():
                self.app_install_loading = False
                self.app_install_cache = {"error": str(e)}
                if self.selected_segment == "app_install":
                    self.update_settings_panel()
                    # Force refresh the UI
                    self.refresh()
            
            self.app.call_from_thread(update_error)
    
    def _display_app_install_list(self, container: ScrollableContainer, software_items) -> None:
        """Display hierarchical software items list in the container."""
        # Handle error case
        if isinstance(software_items, dict) and "error" in software_items:
            container.mount(Label(f"Error loading App info: {software_items['error']}", classes="info-display"))
            return

        container.mount(Label("Available Applications:", classes="section-header"))
        container.mount(Rule())

        # Generate unique suffix to avoid ID conflicts
        import time
        unique_suffix = str(int(time.time() * 1000))[-6:]
        self._app_unique_suffix = unique_suffix

        # Build display list based on expansion state
        display_items = []
        for item in software_items:
            display_items.append(("suite_or_app", item, 0))  # (type, item, indent_level)

            # If it's an expanded suite, add its components
            if isinstance(item, ApplicationSuite) and item.name in self.app_expanded_suites:
                for component in item.components:
                    display_items.append(("component", component, 1))

        # Display each item with proper indentation and styling
        for i, (item_type, item, indent_level) in enumerate(display_items):
            # Arrow indicator for current selection - only show when right panel has focus
            is_right_focused = (self.current_panel_focus == "right")
            arrow = "[#7dd3fc]▶[/#7dd3fc] " if (i == self.app_focused_index and is_right_focused) else "  "

            # Calculate indentation
            indent = "  " * indent_level

            if item_type == "suite_or_app" and isinstance(item, ApplicationSuite):
                # Suite item
                expansion_icon = "▼" if item.name in self.app_expanded_suites else "▶"
                suite_name = f"{expansion_icon} {item.name}"

                # Get suite status
                installed_count = sum(1 for c in item.components if c.installed)
                total_count = len(item.components)

                if installed_count == 0:
                    status_text = f"[bright_black]○ {installed_count}/{total_count}[/bright_black]"
                elif installed_count == total_count:
                    status_text = f"[green]● {installed_count}/{total_count}[/green]"
                else:
                    status_text = f"[yellow]◐ {installed_count}/{total_count}[/yellow]"

                status_display = f"{arrow}{indent}{status_text}"
                content_text = f"{suite_name}"
                if item.description:
                    content_text += f" - {item.description}"

            elif item_type == "component":
                # Component item (with tree lines)
                # Find the parent suite to determine if this is the last component
                tree_prefix = "├─ "  # Default to middle component

                # Find all components in the current suite by looking backwards for the suite header
                suite_start_index = -1
                for j in range(i - 1, -1, -1):
                    if display_items[j][0] == "suite_or_app":
                        suite_start_index = j
                        break

                if suite_start_index >= 0:
                    # Count components in this suite
                    suite_components = []
                    for k in range(suite_start_index + 1, len(display_items)):
                        if display_items[k][0] == "component":
                            suite_components.append(k)
                        elif display_items[k][0] == "suite_or_app":
                            break

                    # Check if this is the last component in the suite
                    if suite_components and i == suite_components[-1]:
                        tree_prefix = "└─ "

                is_selected = self.app_selection_state.get(item.name, False)
                if item.installed and not is_selected:
                    status_text = "[red]- To Uninstall[/red]"
                elif item.installed and is_selected:
                    status_text = "[green]✓ Installed[/green]"
                elif not item.installed and is_selected:
                    status_text = "[yellow]+ To Install[/yellow]"
                else:
                    status_text = "[bright_black]○ Available[/bright_black]"

                status_display = f"{arrow}{indent}{status_text}"
                content_text = f"{tree_prefix}{item.name}"
                if item.description:
                    content_text += f" - {item.description}"

            else:
                # Standalone application
                is_selected = self.app_selection_state.get(item.name, False)
                if item.installed and not is_selected:
                    status_text = "[red]- To Uninstall[/red]"
                elif item.installed and is_selected:
                    status_text = "[green]✓ Installed[/green]"
                elif not item.installed and is_selected:
                    status_text = "[yellow]+ To Install[/yellow]"
                else:
                    status_text = "[bright_black]○ Available[/bright_black]"

                status_display = f"{arrow}{indent}{status_text}"
                content_text = item.name
                if item.description:
                    content_text += f" - {item.description}"

            # Create container for horizontal layout
            from textual.containers import Horizontal
            app_container = Horizontal(classes="app-item-container", id=f"app-container-{i}-{unique_suffix}")

            # Status column with fixed width (includes arrow)
            status_widget = Static(status_display, classes="app-item-status")

            # Content column with app name and description
            content_widget = Static(content_text, classes="app-item-content")

            # Mount container first, then add children
            container.mount(app_container)
            app_container.mount(status_widget)
            app_container.mount(content_widget)

        container.mount(Static("", classes="bottom-spacer"))

    def _update_app_focus_indicators(self) -> None:
        """Update arrow indicators for app items without full refresh."""
        if not self.app_install_cache or isinstance(self.app_install_cache, dict):
            return

        if not hasattr(self, '_app_unique_suffix'):
            return

        # Build display items to match the current display structure
        display_items = self._build_display_items()

        # Update all display items - now they use container structure
        try:
            for i, (item_type, item, indent_level) in enumerate(display_items):
                container_id = f"app-container-{i}-{self._app_unique_suffix}"
                try:
                    from textual.containers import Horizontal
                    container_widget = self.query_one(f"#{container_id}", Horizontal)

                    # Get the status widget (first child)
                    status_widgets = container_widget.query(".app-item-status")
                    if status_widgets:
                        status_widget = status_widgets.first()

                        # Arrow indicator for current selection - only show when right panel has focus
                        is_right_focused = (self.current_panel_focus == "right")
                        arrow = "[#7dd3fc]▶[/#7dd3fc] " if (i == self.app_focused_index and is_right_focused) else "  "

                        # Calculate indentation
                        indent = "  " * indent_level

                        if item_type == "suite_or_app" and hasattr(item, 'components'):
                            # Suite item - get suite status
                            installed_count = sum(1 for c in item.components if c.installed)
                            total_count = len(item.components)

                            if installed_count == 0:
                                status_text = f"[bright_black]○ {installed_count}/{total_count}[/bright_black]"
                            elif installed_count == total_count:
                                status_text = f"[green]● {installed_count}/{total_count}[/green]"
                            else:
                                status_text = f"[yellow]◐ {installed_count}/{total_count}[/yellow]"

                            status_display = f"{arrow}{indent}{status_text}"

                        elif item_type == "component":
                            # Component item
                            is_selected = self.app_selection_state.get(item.name, False)
                            if item.installed and not is_selected:
                                status_text = "[red]- To Uninstall[/red]"
                            elif item.installed and is_selected:
                                status_text = "[green]✓ Installed[/green]"
                            elif not item.installed and is_selected:
                                status_text = "[yellow]+ To Install[/yellow]"
                            else:
                                status_text = "[bright_black]○ Available[/bright_black]"

                            status_display = f"{arrow}{indent}{status_text}"

                        else:
                            # Standalone application
                            is_selected = self.app_selection_state.get(item.name, False)
                            if item.installed and not is_selected:
                                status_text = "[red]- To Uninstall[/red]"
                            elif item.installed and is_selected:
                                status_text = "[green]✓ Installed[/green]"
                            elif not item.installed and is_selected:
                                status_text = "[yellow]+ To Install[/yellow]"
                            else:
                                status_text = "[bright_black]○ Available[/bright_black]"

                            status_display = f"{arrow}{indent}{status_text}"

                        # Update status widget
                        status_widget.update(status_display)

                except Exception:
                    # If we can't find the container, skip this item
                    continue

        except Exception:
            # If we can't update indicators, fall back to full refresh
            self.update_settings_panel()

    def _navigate_app_items(self, direction: str) -> None:
        """Navigate through app items in the app install section."""
        if not self.app_install_cache or isinstance(self.app_install_cache, dict):
            return

        # Build display items to get correct max index
        display_items = self._build_display_items()
        max_index = len(display_items) - 1

        if direction == "down" and self.app_focused_index < max_index:
            self.app_focused_index += 1
        elif direction == "up" and self.app_focused_index > 0:
            self.app_focused_index -= 1

        # Only update focus indicators instead of full panel refresh
        self._update_app_focus_indicators()
        self._scroll_to_current_app(direction)

    def _scroll_to_current_app(self, direction: str = None) -> None:
        """Scroll to ensure current app selection is visible."""
        try:
            scrollable_container = self.query_one("#settings-scroll", ScrollableContainer)

            # Try to find the current app container by its ID
            if hasattr(self, '_app_unique_suffix'):
                current_container_id = f"app-container-{self.app_focused_index}-{self._app_unique_suffix}"
                from textual.containers import Horizontal
                current_container = self.query_one(f"#{current_container_id}", Horizontal)

                # Use scroll_to_widget if available (preferred method)
                if hasattr(scrollable_container, 'scroll_to_widget'):
                    scrollable_container.scroll_to_widget(current_container, animate=True, speed=60, center=True)
                    return

        except Exception:
            pass

        # Fallback: manual scrolling calculation
        try:
            scrollable_container = self.query_one("#settings-scroll", ScrollableContainer)

            # Calculate the position of the current app item
            header_height = 3  # "Available Applications:" + Rule
            current_position = header_height + self.app_focused_index

            # Get container dimensions
            container_height = scrollable_container.size.height
            current_scroll = scrollable_container.scroll_y

            # Scroll if current item is not visible
            if current_position < current_scroll:
                # Item is above visible area - scroll up
                scrollable_container.scroll_y = max(0, current_position - 1)
            elif current_position >= current_scroll + container_height - 2:
                # Item is below visible area - scroll down
                scrollable_container.scroll_y = current_position - container_height + 3

        except Exception:
            # Final fallback: simple scroll by direction
            if direction:
                try:
                    scrollable_container = self.query_one("#settings-scroll", ScrollableContainer)
                    if direction == "down":
                        scrollable_container.scroll_down(animate=True)
                    else:
                        scrollable_container.scroll_up(animate=True)
                except:
                    pass

    def _toggle_current_app(self) -> None:
        """Toggle the selection state of the currently focused app."""
        if not self.app_install_cache or isinstance(self.app_install_cache, dict):
            return

        # Build display list based on current expansion state
        display_items = self._build_display_items()

        if 0 <= self.app_focused_index < len(display_items):
            item_type, item, indent_level = display_items[self.app_focused_index]

            # Only toggle selection for actual applications/components, not suite headers
            if item_type in ["suite_or_app", "component"] and not isinstance(item, ApplicationSuite):
                current_state = self.app_selection_state.get(item.name, item.installed)
                self.app_selection_state[item.name] = not current_state

                # Only update focus indicators instead of full refresh
                self._update_app_focus_indicators()
                # Update help text when selection changes
                self._update_help_text()

    def _handle_app_enter_key(self) -> None:
        """Handle Enter key press for suite expansion/collapse and app selection."""
        if not self.app_install_cache or isinstance(self.app_install_cache, dict):
            return

        # Build display list based on current expansion state
        display_items = self._build_display_items()

        if 0 <= self.app_focused_index < len(display_items):
            item_type, item, indent_level = display_items[self.app_focused_index]

            if item_type == "suite_or_app" and isinstance(item, ApplicationSuite):
                # Toggle suite expansion
                if item.name in self.app_expanded_suites:
                    self.app_expanded_suites.remove(item.name)
                else:
                    self.app_expanded_suites.add(item.name)

                # Ensure focus index is still valid after expansion state change
                self._ensure_valid_focus_index()

                # Refresh the display to show/hide components
                self.update_settings_panel()
            else:
                # For non-suite items, treat Enter like Space (toggle selection)
                self._toggle_current_app()

    def _build_display_items(self):
        """Build the current display items list based on expansion state."""
        display_items = []
        for item in self.app_install_cache:
            display_items.append(("suite_or_app", item, 0))

            # If it's an expanded suite, add its components
            if isinstance(item, ApplicationSuite) and item.name in self.app_expanded_suites:
                for component in item.components:
                    display_items.append(("component", component, 1))

        return display_items

    def _ensure_valid_focus_index(self):
        """Ensure app_focused_index is within valid bounds."""
        if not self.app_install_cache or isinstance(self.app_install_cache, dict):
            self.app_focused_index = 0
            return

        display_items = self._build_display_items()
        max_index = len(display_items) - 1

        if max_index < 0:
            self.app_focused_index = 0
        elif self.app_focused_index > max_index:
            self.app_focused_index = max_index
        elif self.app_focused_index < 0:
            self.app_focused_index = 0

    def _calculate_app_changes(self) -> dict:
        """Calculate what app changes need to be applied."""
        if not self.app_install_cache or isinstance(self.app_install_cache, dict):
            return {"install": [], "uninstall": []}

        changes = {"install": [], "uninstall": []}

        for app in self.app_install_cache:
            is_selected = self.app_selection_state.get(app.name, app.installed)

            if app.installed and not is_selected:
                # Installed but unmarked - uninstall
                changes["uninstall"].append(app.name)
            elif not app.installed and is_selected:
                # Not installed but marked - install
                changes["install"].append(app.name)

        return changes

    def action_apply_app_changes(self) -> None:
        """Apply the selected app installation changes."""
        if not self.app_install_cache or isinstance(self.app_install_cache, dict):
            return

        changes = self._calculate_app_changes()

        if not changes["install"] and not changes["uninstall"]:
            self._show_message("No changes to apply")
            return

        # Prepare actions list
        actions = []
        for app in self.app_install_cache:
            is_selected = self.app_selection_state.get(app.name, app.installed)

            if app.installed and not is_selected:
                actions.append({
                    "action": "uninstall",
                    "application": app
                })
            elif not app.installed and is_selected:
                actions.append({
                    "action": "install",
                    "application": app
                })

        if actions:
            # Show confirmation modal
            from .app_install_confirmation_modal import AppInstallConfirmationModal

            def on_confirmation(confirmed: bool):
                if confirmed:
                    # Show progress modal
                    from .app_install_progress_modal import AppInstallProgressModal
                    self.app.push_screen(AppInstallProgressModal(actions, self.app_installer))
                    # Refresh the app list after installation
                    self.app_install_cache = None
                    self.app_install_loading = False
                    self.update_settings_panel()

            modal = AppInstallConfirmationModal(actions, on_confirmation, self.app_installer)
            # Clear panel focus before showing modal
            self._clear_panel_focus()
            self.app.push_screen(modal)
    
    # Navigation and interaction methods for right panel content
    
    def _build_homebrew_settings(self, container: ScrollableContainer) -> None:
        """Build Homebrew settings panel."""
        # Check if we have cached data and not currently loading
        if self.homebrew_cache and not self.homebrew_loading:
            # Enable scrollbar for content
            container.styles.scrollbar_size = 1
            self._display_homebrew_info(container, self.homebrew_cache)
        elif self.homebrew_loading:
            # Disable scrollbar when loading
            container.styles.scrollbar_size = 0
            # Show simple loading text
            container.mount(Label("Loading...", classes="loading-text"))
        else:
            # Disable scrollbar when loading
            container.styles.scrollbar_size = 0
            # Start loading homebrew info asynchronously
            self.homebrew_loading = True
            container.mount(Label("Loading...", classes="loading-text"))
            # Start the background task
            self._load_homebrew_info()
    
    def _build_package_manager_settings(self, container: ScrollableContainer) -> None:
        """Build Package Manager settings panel."""
        # Check if we have cached data and not currently loading
        if self.package_manager_cache and not self.package_manager_loading:
            # Enable scrollbar for content
            container.styles.scrollbar_size = 1
            self._display_package_manager_info(container, self.package_manager_cache)
        elif self.package_manager_loading:
            # Disable scrollbar when loading
            container.styles.scrollbar_size = 0
            # Show simple loading text
            container.mount(Label("Loading...", classes="loading-text"))
        else:
            # Disable scrollbar when loading
            container.styles.scrollbar_size = 0
            # Start loading package manager info asynchronously
            self.package_manager_loading = True
            container.mount(Label("Loading...", classes="loading-text"))
            # Start the background task
            self._load_package_manager_info()
    
    def _build_user_management_settings(self, container: ScrollableContainer) -> None:
        """Build User Management settings panel."""
        # Check if we have cached data and not currently loading
        if self.user_management_cache and not self.user_management_loading:
            # Enable scrollbar for content
            container.styles.scrollbar_size = 1
            self._display_user_management_info(container, self.user_management_cache)
        elif self.user_management_loading:
            # Disable scrollbar when loading
            container.styles.scrollbar_size = 0
            # Show simple loading text
            container.mount(Label("Loading...", classes="loading-text"))
        else:
            # Disable scrollbar when loading
            container.styles.scrollbar_size = 0
            # Start loading user management info asynchronously
            self.user_management_loading = True
            container.mount(Label("Loading...", classes="loading-text"))
            # Start the background task
            self._load_user_management_info()
    
    def _build_app_settings(self, container: ScrollableContainer) -> None:
        """Build application settings panel."""
        # Check if we have cached data and not currently loading
        if self.settings_cache and not self.settings_loading:
            # Enable scrollbar for content
            container.styles.scrollbar_size = 1
            self._display_settings_info(container, self.settings_cache)
        elif self.settings_loading:
            # Disable scrollbar when loading
            container.styles.scrollbar_size = 0
            # Show simple loading text
            container.mount(Label("Loading...", classes="loading-text"))
        else:
            # Disable scrollbar when loading
            container.styles.scrollbar_size = 0
            # Start loading settings info asynchronously
            self.settings_loading = True
            container.mount(Label("Loading...", classes="loading-text"))
            # Start the background task
            self._load_settings_info()
    
    def _build_help_content(self, container: ScrollableContainer) -> None:
        """Build help content panel."""
        # Check if we have cached data and not currently loading
        if self.help_cache and not self.help_loading:
            # Enable scrollbar for content
            container.styles.scrollbar_size = 1
            self._display_help_info(container, self.help_cache)
        elif self.help_loading:
            # Disable scrollbar when loading
            container.styles.scrollbar_size = 0
            # Show simple loading text
            container.mount(Label("Loading...", classes="loading-text"))
        else:
            # Disable scrollbar when loading
            container.styles.scrollbar_size = 0
            # Start loading help info asynchronously
            self.help_loading = True
            container.mount(Label("Loading...", classes="loading-text"))
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

            # Update segment selection and switch to right panel
            self.selected_segment = segment_id
            self.update_settings_panel()

            # When a segment button is pressed (Enter key), switch to right panel
            # So don't show arrow since we're moving focus to right panel
            self._update_segment_buttons(segment_id, show_arrow=False)
            # Update panel title
            self._update_panel_title(segment_id)

            # When a segment button is pressed (Enter key), switch to right panel
            self.action_nav_right()

        elif button_id == "open-pm-config":
            # Clear panel focus before showing modal
            self._clear_panel_focus()
            # Open package manager installation modal
            from .package_manager_install_modal import PackageManagerInstallModal
            def on_install_actions_selected(actions: list):
                # Handle installation actions if needed
                pass
            self.app.push_screen(PackageManagerInstallModal(on_install_actions_selected, self.config_manager))

        elif button_id and button_id.startswith("apply-app-changes-"):
            # Apply app changes (legacy support)
            self.action_apply_app_changes()

    def _open_source_selection_modal(self) -> None:
        """Open modal for source selection."""
        if not hasattr(self, '_primary_pm') or not self._primary_pm:
            return
            
        from .source_selection_modal import SourceSelectionModal
        def on_source_selected(source_url: str) -> None:
            """Handle source selection."""
            if source_url:
                # Apply the selected source
                from ...modules.package_manager import PackageManagerDetector
                detector = PackageManagerDetector(self.config_manager)
                success, message = detector.change_mirror(self._primary_pm.name, source_url)
                
                if success:
                    # Update the cached source and refresh display
                    self._primary_pm.current_source = source_url
                    self.package_manager_cache["primary"] = self._primary_pm
                    self.update_settings_panel()
                    # Show success message briefly
                    self._show_temp_message(f"✅ {message}")
                else:
                    # Show error message
                    self._show_temp_message(f"❌ {message}")
        
        modal = SourceSelectionModal(self._primary_pm, on_source_selected, self.config_manager)
        # Clear panel focus before showing modal
        self._clear_panel_focus()
        self.app.push_screen(modal)
    
    def _show_temp_message(self, message: str) -> None:
        """Show a temporary message in the title."""
        try:
            title_widget = self.query_one("#title", Static)
            original_title = title_widget.renderable
            title_widget.update(message)
            # Reset after 3 seconds
            self.set_timer(3.0, lambda: title_widget.update(original_title))
        except:
            pass
    
    def _handle_focus_change(self) -> None:
        """Handle focus changes on segment buttons."""
        focused = self.focused
        if focused and hasattr(focused, 'id') and focused.id and focused.id.startswith("segment-"):
            segment_id = focused.id.replace("segment-", "")
            # Only update if the segment actually changed
            if segment_id != self.selected_segment:
                self.selected_segment = segment_id
                # watch_selected_segment will handle the rest
    
    def _update_segment_buttons(self, selected_id: str, show_arrow: bool = True) -> None:
        """Update segment button styles to show selection."""
        logger.debug(f"Updating segment buttons: selected_id='{selected_id}', show_arrow={show_arrow}")
        for segment in self.SEGMENTS:
            try:
                button = self.query_one(f"#segment-{segment['id']}", Button)
                segment_number = next(i+1 for i, s in enumerate(self.SEGMENTS) if s['id'] == segment['id'])
                if segment['id'] == selected_id and show_arrow:
                    # Use arrow in the reserved space (first 2 characters)
                    button.label = f"[#7dd3fc]▶[/#7dd3fc] {segment_number}. {segment['name']}"
                    button.add_class("selected")
                    logger.debug(f"  → {segment['name']}: ARROW SHOWN")
                else:
                    # Keep the reserved space with spaces
                    button.label = f"  {segment_number}. {segment['name']}"
                    if segment['id'] == selected_id:
                        button.add_class("selected")
                        logger.debug(f"  → {segment['name']}: SELECTED (no arrow)")
                    else:
                        button.remove_class("selected")
                        logger.debug(f"  → {segment['name']}: normal")
            except Exception as e:
                logger.warning(f"Failed to update button for segment '{segment['id']}': {e}")
                pass
    
    def _update_panel_title(self, selected_id: str) -> None:
        """Update the right panel title based on selected segment."""
        try:
            title_widget = self.query_one("#right-panel-title", Label)
            # Map segment IDs to display titles
            title_map = {
                "system_info": "System Status",
                "package_manager": "Package Manager",
                "app_install": "Application Manager",
                "homebrew": "Homebrew",
                "user_management": "User Management", 
                "settings": "Settings",
                "help": "Help"
            }
            
            display_title = title_map.get(selected_id, "Settings")
            title_widget.update(display_title)
        except Exception:
            # Silently fail if title widget not found
            pass
    
    def _clear_panel_focus(self) -> None:
        """Clear panel focus styles to prevent highlight leak to modals."""
        try:
            left_panel = self.query_one("#left-panel", Vertical)
            right_panel = self.query_one("#right-panel", Vertical)
            left_panel.remove_class("panel-focused")
            right_panel.remove_class("panel-focused")
        except:
            pass

    def _update_panel_focus(self, is_left_focused: bool) -> None:
        """Update panel focus styles based on which panel has focus."""
        logger.debug(f"Updating panel focus: is_left_focused={is_left_focused}")
        try:
            left_panel = self.query_one("#left-panel", Vertical)
            right_panel = self.query_one("#right-panel", Vertical)

            if is_left_focused:
                left_panel.add_class("panel-focused")
                right_panel.remove_class("panel-focused")
                # Update state tracking
                old_focus = self.current_panel_focus
                self.current_panel_focus = "left"
                logger.debug(f"Panel focus updated: {old_focus} → left")
            else:
                left_panel.remove_class("panel-focused")
                right_panel.add_class("panel-focused")
                # Update state tracking
                old_focus = self.current_panel_focus
                self.current_panel_focus = "right"
                logger.debug(f"Panel focus updated: {old_focus} → right")

            # Update help text when panel focus changes
            self._update_help_text(is_left_focused)
        except Exception as e:
            logger.error(f"Failed to update panel focus: {e}")
            pass
    
    def action_select_segment(self) -> None:
        """Handle S key shortcut for Settings - works from any panel."""
        # S key always goes to Settings segment regardless of panel focus
        self.selected_segment = "settings"
        self.update_settings_panel()
        # If focus is in left panel, switch to right panel and don't show arrow
        if self._is_focus_in_left_panel():
            self._update_segment_buttons("settings", show_arrow=False)
            self._update_panel_title("settings")
            self.action_nav_right()
        else:
            # If already in right panel, just update normally
            self._update_segment_buttons("settings", show_arrow=False)
            self._update_panel_title("settings")

    def on_key(self, event) -> bool:
        """Handle key events, including 1-6 shortcuts and two-level Esc exit."""
        # Handle Esc key with two-level exit behavior
        if event.key == "escape":
            if self.current_panel_focus == "right":
                # From right panel, go back to left panel
                self.action_nav_left()
                return True
            else:
                # From left panel, quit application
                self.app.exit()
                return True

        # Handle space key for app install section
        if event.key == "space" and self.selected_segment == "app_install":
            # Only handle space key when in right panel (app list)
            if not self._is_focus_in_left_panel():
                self._toggle_current_app()
                return True  # Consume the event

        # Handle enter key for app install section
        if event.key == "enter" and self.selected_segment == "app_install":
            # Only handle enter key when in right panel (app list)
            if not self._is_focus_in_left_panel():
                self._handle_app_enter_key()
                return True  # Consume the event

        # Handle 1-6 shortcuts only when focus is in left panel
        if event.key in ["1", "2", "3", "4", "5", "6"] and self._is_focus_in_left_panel():
            try:
                segment_index = int(event.key) - 1
                if 0 <= segment_index < len(self.SEGMENTS):
                    selected_segment = self.SEGMENTS[segment_index]

                    # Update the selected segment
                    self.selected_segment = selected_segment["id"]
                    self.update_settings_panel()
                    # Don't show arrow since we're switching to right panel
                    self._update_segment_buttons(selected_segment["id"], show_arrow=False)
                    self._update_panel_title(selected_segment["id"])

                    # Switch focus to right panel
                    self.action_nav_right()

                    return True  # Consume the event
            except (ValueError, IndexError):
                pass

        # Let the parent handle other keys
        return False

    def action_refresh_current_page(self) -> None:
        """Refresh the current page by clearing its cache."""
        try:
            if self.selected_segment == "app_install":
                self.refresh_app_install_page()
            elif self.selected_segment == "package_manager":
                self.refresh_package_manager_page()
            elif self.selected_segment == "system_info":
                self.system_info_cache = None
                self.system_info_loading = False
                if self.selected_segment == "system_info":
                    self.update_settings_panel()
            else:
                # For other segments, clear their respective caches
                if hasattr(self, f"{self.selected_segment}_cache"):
                    setattr(self, f"{self.selected_segment}_cache", None)
                    setattr(self, f"{self.selected_segment}_loading", False)
                    self.update_settings_panel()

            logger.info(f"Refreshed {self.selected_segment} page cache")
        except Exception as e:
            logger.error(f"Failed to refresh {self.selected_segment} page: {str(e)}")

    # Legacy action methods for backward compatibility
    def action_homebrew(self) -> None:
        """Show Homebrew settings."""
        self.selected_segment = "homebrew"
        self.update_settings_panel()
        # Arrow display will be handled by watch_current_panel_focus
        self._update_panel_title("homebrew")

    def action_package_manager(self) -> None:
        """Show package manager settings."""
        self.selected_segment = "package_manager"
        self.update_settings_panel()
        # Arrow display will be handled by watch_current_panel_focus
        self._update_panel_title("package_manager")

    def action_user_management(self) -> None:
        """Show user management settings."""
        self.selected_segment = "user_management"
        self.update_settings_panel()
        # Arrow display will be handled by watch_current_panel_focus
        self._update_panel_title("user_management")

    def action_settings(self) -> None:
        """Show application settings."""
        self.selected_segment = "settings"
        self.update_settings_panel()
        # Arrow display will be handled by watch_current_panel_focus
        self._update_panel_title("settings")

    def action_help(self) -> None:
        """Show help content."""
        self.selected_segment = "help"
        self.update_settings_panel()
        # Arrow display will be handled by watch_current_panel_focus
        self._update_panel_title("help")
    
    def action_quit(self) -> None:
        """Exit the application."""
        self.app.exit()
    
    def action_switch_panel(self) -> None:
        """Switch focus between left and right panels using Tab key."""
        logger.debug("action_switch_panel called")
        # Get the currently focused widget
        focused = self.focused

        # If nothing is focused, focus the first segment button
        if not focused:
            logger.debug("No widget focused, focusing first segment button")
            try:
                first_button = self.query_one(f"#segment-{self.SEGMENTS[0]['id']}", Button)
                first_button.focus()
                self._update_panel_focus(is_left_focused=True)
            except:
                pass
            return
            
        # Check if focus is in the left panel
        left_panel = self.query_one("#left-panel", Vertical)
        right_panel = self.query_one("#right-panel", Vertical)
        
        # Check if the focused widget is in the left panel
        is_in_left = False
        try:
            # Walk up the widget tree to see if we're inside the left panel
            current = focused
            while current is not None:
                if current.id == "left-panel":
                    is_in_left = True
                    break
                current = current.parent
        except:
            pass
        
        if is_in_left:
            # Move focus to the right panel - focus the scrollable container
            try:
                right_container = self.query_one("#settings-scroll", ScrollableContainer)
                right_container.focus()
                self._update_panel_focus(is_left_focused=False)
                
                # If switching to package manager section, initialize focus and clear left arrows
                if self.selected_segment == "package_manager" and hasattr(self, '_primary_pm') and self._primary_pm:
                    # Always set initial focus when switching to right panel
                    self._pm_focused_item = "manager"
                    # Clear left arrows and show right arrows
                    self._update_pm_focus_indicators(clear_left_arrows=True)
                elif self.selected_segment == "app_install" and self.app_install_cache and not isinstance(self.app_install_cache, dict):
                    # Initialize app focus when switching to right panel
                    if not hasattr(self, '_app_focus_initialized') or not self._app_focus_initialized:
                        self.app_focused_index = 0
                        self._ensure_valid_focus_index()  # Ensure valid focus
                        self._app_focus_initialized = True
                    # Update focus indicators
                    self._update_app_focus_indicators()
                    # Panel focus change will be handled by watch_current_panel_focus
                else:
                    # Panel focus change will be handled by watch_current_panel_focus
                    pass
            except:
                # If right panel doesn't have focusable elements, stay in left
                pass
        else:
            # Move focus back to the left panel - focus the selected segment button
            # First, clear right panel arrows if we're in package manager section
            if self.selected_segment == "package_manager" and hasattr(self, '_primary_pm') and self._primary_pm:
                self._clear_pm_focus_indicators()

            # Clear right panel arrows if we're in app install section
            if self.selected_segment == "app_install":
                self._clear_app_focus_indicators()

            try:
                selected_button = self.query_one(f"#segment-{self.selected_segment}", Button)
                selected_button.focus()
                self._update_panel_focus(is_left_focused=True)
                # Arrow will be updated by watch_current_panel_focus
            except:
                # Try to focus the first available segment button
                for segment in self.SEGMENTS:
                    try:
                        button = self.query_one(f"#segment-{segment['id']}", Button)
                        button.focus()
                        self._update_panel_focus(is_left_focused=True)
                        # Arrow will be updated by watch_current_panel_focus
                        break
                    except:
                        continue
    
    

    
    # Vim-like navigation actions
    def action_nav_left(self) -> None:
        """Navigate left (h key) - switch to left panel."""
        # H key switches to left panel

        # Clear right panel arrows if we're in package manager section
        if self.selected_segment == "package_manager" and hasattr(self, '_primary_pm') and self._primary_pm:
            self._clear_pm_focus_indicators()

        # Clear right panel arrows if we're in app install section
        if self.selected_segment == "app_install":
            self._clear_app_focus_indicators()

        try:
            # Find and focus the selected segment button in left panel
            selected_button = self.query_one(f"#segment-{self.selected_segment}", Button)
            selected_button.focus()
            self._update_panel_focus(is_left_focused=True)
            # Arrow will be updated by watch_current_panel_focus
        except:
            # Try to focus the first available segment button
            for segment in self.SEGMENTS:
                try:
                    button = self.query_one(f"#segment-{segment['id']}", Button)
                    button.focus()
                    self._update_panel_focus(is_left_focused=True)
                    # Arrow will be updated by watch_current_panel_focus
                    break
                except:
                    continue
    
    def action_nav_down(self) -> None:
        """Navigate down (j key) - move to next item in current panel."""
        focused = self.focused
        if not focused:
            return
            
        # Check which panel we're in
        is_in_left = self._is_focus_in_left_panel()
        
        if is_in_left:
            # In left panel - navigate through segment buttons
            self._navigate_segments_down()
        else:
            # In right panel
            if self.selected_segment == "package_manager" and hasattr(self, '_primary_pm') and self._primary_pm:
                # Navigate through package manager items
                self._navigate_pm_items("down")
            elif self.selected_segment == "app_install":
                # Navigate through app items
                self._navigate_app_items("down")
            else:
                # Scroll down in other sections
                try:
                    scroll_container = self.query_one("#settings-scroll", ScrollableContainer)
                    scroll_container.scroll_down()
                except:
                    pass
    
    def action_nav_up(self) -> None:
        """Navigate up (k key) - move to previous item in current panel."""
        focused = self.focused
        if not focused:
            return
            
        # Check which panel we're in
        is_in_left = self._is_focus_in_left_panel()
        
        if is_in_left:
            # In left panel - navigate through segment buttons
            self._navigate_segments_up()
        else:
            # In right panel
            if self.selected_segment == "package_manager" and hasattr(self, '_primary_pm') and self._primary_pm:
                # Navigate through package manager items
                self._navigate_pm_items("up")
            elif self.selected_segment == "app_install":
                # Navigate through app items
                self._navigate_app_items("up")
            else:
                # Scroll up in other sections
                try:
                    scroll_container = self.query_one("#settings-scroll", ScrollableContainer)
                    scroll_container.scroll_up()
                except:
                    pass
    
    def action_nav_right(self) -> None:
        """Navigate right (l key) - switch to right panel."""
        # L key switches to right panel
        try:
            right_container = self.query_one("#settings-scroll", ScrollableContainer)
            right_container.focus()
            self._update_panel_focus(is_left_focused=False)

            # If switching to package manager section, initialize focus and clear left arrows
            if self.selected_segment == "package_manager" and hasattr(self, '_primary_pm') and self._primary_pm:
                # Always set initial focus when switching to right panel
                self._pm_focused_item = "manager"
                # Clear left arrows and show right arrows
                self._update_pm_focus_indicators(clear_left_arrows=True)
            elif self.selected_segment == "app_install" and self.app_install_cache and not isinstance(self.app_install_cache, dict):
                # Initialize app focus when switching to right panel
                self.app_focused_index = 0
                self._ensure_valid_focus_index()  # Ensure valid focus
                # Update focus indicators
                self._update_app_focus_indicators()
            else:
                # Panel focus change will be handled by watch_current_panel_focus
                pass
        except Exception:
            pass
    
    def _is_focus_in_left_panel(self) -> bool:
        """Check if current focus is in the left panel."""
        focused = self.focused
        if not focused:
            # If no focus, we can't determine - return False to be safe (don't quit)
            return False

        # Walk up the widget tree to determine which panel contains the focused widget
        current = focused
        while current is not None:
            # Explicitly check for left panel
            if current.id == "left-panel":
                return True
            # Explicitly check for right panel or its children
            elif current.id in ["right-panel", "settings-scroll", "settings-content"]:
                return False
            # Also check for segment buttons specifically (they are in left panel)
            elif hasattr(current, 'id') and current.id and current.id.startswith('segment-'):
                return True
            current = current.parent

        # If we reached the top without finding a panel, check widget ID patterns
        if hasattr(focused, 'id') and focused.id:
            # If it's a segment button, it's definitely in the left panel
            if focused.id.startswith('segment-'):
                return True
            # If it's the settings scroll or content, it's in the right panel
            if focused.id in ['settings-scroll', 'settings-content', 'right-panel']:
                return False

        # Default to False (right panel) to be safe - don't accidentally quit
        return False
    
    def _navigate_segments_down(self) -> None:
        """Navigate down through segment buttons."""
        current_segment_index = -1
        for i, segment in enumerate(self.SEGMENTS):
            if segment["id"] == self.selected_segment:
                current_segment_index = i
                break
        
        if current_segment_index >= 0 and current_segment_index < len(self.SEGMENTS) - 1:
            # Move to next segment
            next_segment = self.SEGMENTS[current_segment_index + 1]
            try:
                next_button = self.query_one(f"#segment-{next_segment['id']}", Button)
                next_button.focus()
                # Directly update the selected segment and trigger all updates
                self.selected_segment = next_segment['id']
                # No need to call _handle_focus_change since watch_selected_segment will handle it
            except:
                pass
    
    def _navigate_segments_up(self) -> None:
        """Navigate up through segment buttons."""
        current_segment_index = -1
        for i, segment in enumerate(self.SEGMENTS):
            if segment["id"] == self.selected_segment:
                current_segment_index = i
                break
        
        if current_segment_index > 0:
            # Move to previous segment
            prev_segment = self.SEGMENTS[current_segment_index - 1]
            try:
                prev_button = self.query_one(f"#segment-{prev_segment['id']}", Button)
                prev_button.focus()
                # Directly update the selected segment and trigger all updates
                self.selected_segment = prev_segment['id']
                # No need to call _handle_focus_change since watch_selected_segment will handle it
            except:
                pass
    
    def _check_and_update_panel_focus(self) -> None:
        """Check which panel has focus and update the visual indicators."""
        focused = self.focused
        if not focused:
            return
            
        # Walk up the widget tree to determine which panel contains the focused widget
        current = focused
        while current is not None:
            if current.id == "left-panel":
                self._update_panel_focus(is_left_focused=True)
                return
            elif current.id == "right-panel" or current.id == "settings-scroll":
                self._update_panel_focus(is_left_focused=False)
                return
            current = current.parent
    
    def action_select_item(self) -> None:
        """Select current focused item (enter key)."""
        focused = self.focused
        
        # Check if we're in the left panel (segments)
        is_in_left = self._is_focus_in_left_panel()
        
        if is_in_left:
            # In left panel: Enter acts like Tab/L key - switch to right panel
            self.action_nav_right()
            return
        
        # Check if we're in package manager section with focused items
        if self.selected_segment == "package_manager" and hasattr(self, '_pm_focused_item') and self._pm_focused_item:
            self._handle_pm_item_selection()
            return
        
        # Check if we're in app install section
        if self.selected_segment == "app_install":
            # Toggle current app selection when Enter is pressed in the right panel
            if not is_in_left:
                self._toggle_current_app()
                return
        
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
    
    def _update_package_manager_info(self) -> None:
        """Update package manager information in the main menu display."""
        try:
            # Refresh package manager detection
            from ...modules.package_manager import PackageManagerDetector
            detector = PackageManagerDetector(self.config_manager)
            self._primary_pm = detector.get_primary_package_manager()

            # Update the package manager display in the UI
            if hasattr(self, '_primary_pm') and self._primary_pm:
                self._display_package_manager()
        except Exception as e:
            # Silently fail to avoid disrupting the UI
            pass

    def refresh_package_manager_page(self) -> None:
        """Public method to refresh package manager page after mirror changes."""
        try:
            # Only save focus if we're currently in package manager segment
            saved_focused_item = None
            should_restore_focus = (self.selected_segment == "package_manager" and
                                   hasattr(self, '_pm_focused_item') and self._pm_focused_item)

            if should_restore_focus:
                saved_focused_item = self._pm_focused_item

            # Clear package manager cache to force reload
            self.package_manager_cache = None
            self.package_manager_loading = False

            # If currently viewing package manager segment, refresh it
            if self.selected_segment == "package_manager":
                # Force rebuild the panel content
                self.update_settings_panel()
                # Refresh the UI
                self.refresh()

                # Only restore focus if we saved it and user is still on package manager page
                if should_restore_focus and saved_focused_item and self.selected_segment == "package_manager":
                    # Use call_after_refresh to ensure focus restoration happens after UI update
                    def restore_focus():
                        # Double-check user is still on package manager page
                        if self.selected_segment == "package_manager":
                            self._pm_focused_item = saved_focused_item

                            # Set right panel focus to ensure arrows show properly
                            try:
                                right_container = self.query_one("#settings-scroll", ScrollableContainer)
                                right_container.focus()
                                self._update_panel_focus(is_left_focused=False)
                            except Exception:
                                pass

                            # Update focus indicators to show the restored focus
                            self._update_pm_focus_indicators(clear_left_arrows=True)

                    self.call_after_refresh(restore_focus)

            # Also update the internal package manager reference
            self._update_package_manager_info()

        except Exception as e:
            # Silently fail to avoid disrupting the UI
            pass

    def refresh_app_install_page(self) -> None:
        """Public method to refresh application install page to update status."""
        try:
            # Only save focus if we're currently in app install segment
            saved_focused_index = None
            should_restore_focus = self.selected_segment == "app_install"

            if should_restore_focus:
                saved_focused_index = self.app_focused_index

            # Clear app install cache to force reload and status refresh
            self.app_install_cache = None
            self.app_install_loading = False

            # If currently viewing app install segment, refresh it
            if self.selected_segment == "app_install":
                # Force rebuild the panel content
                self.update_settings_panel()
                # Refresh the UI
                self.refresh()

                # Restore focus if we saved it and user is still on app install page
                if should_restore_focus and saved_focused_index is not None:
                    # Use call_after_refresh to ensure focus restoration happens after UI update
                    def restore_focus():
                        # Double-check user is still on app install page
                        if self.selected_segment == "app_install" and self.app_install_cache:
                            self.app_focused_index = min(saved_focused_index, len(self.app_install_cache) - 1)

                            # Set right panel focus to ensure arrows show properly
                            try:
                                right_container = self.query_one("#settings-scroll", ScrollableContainer)
                                right_container.focus()
                                self._update_panel_focus(is_left_focused=False)
                            except Exception:
                                pass

                            # Update focus indicators to show the restored focus
                            self._update_app_focus_indicators()

                    self.call_after_refresh(restore_focus)

        except Exception as e:
            # Silently fail to avoid disrupting the UI
            logger.error(f"Failed to refresh app install page: {str(e)}")

    def _show_message(self, message: str, error: bool = False) -> None:
        """Show a message to the user by updating the title."""
        try:
            title_widget = self.query_one("#title", Static)
            if error:
                title_widget.update(f"🖥️ Linux System Initializer - Error: {message}")
            else:
                title_widget.update(f"🖥️ Linux System Initializer - {message}")
            
            # Reset title after a delay
            self.set_timer(3.0, lambda: title_widget.update("🖥️ Linux System Initializer"))
        except Exception:
            # Silently fail if title widget is not found
            pass

    def _update_help_text(self, is_left_focused: bool = None) -> None:
        """Update the main menu help text based on current segment and panel focus."""
        try:
            help_widget = self.query_one("#help-box Label", Label)

            # Check which panel has focus - use provided parameter or detect
            if is_left_focused is None:
                is_left_focused = self._is_focus_in_left_panel()

            if is_left_focused:
                # Left panel focused - show navigation help (consistent across all pages)
                help_text = "Esc=Back/Quit | Q=Quit | S=Settings | TAB/H/L=Switch Focus | J/K=Up/Down | Enter=Enter Right Panel | 1-6=Quick Select"
            else:
                # Right panel focused - show page-specific functionality
                if self.selected_segment == "system_info":
                    help_text = "Esc=Back to Left Panel | TAB/H=Back to Left Panel | J/K=Scroll | Q=Quit"
                elif self.selected_segment == "package_manager":
                    help_text = "Esc=Back to Left Panel | TAB/H=Back to Left Panel | J/K=Navigate | Enter=Select | Q=Quit"
                elif self.selected_segment == "app_install":
                    # Show app-specific help with apply changes info when needed
                    changes = self._calculate_app_changes()
                    if changes["install"] or changes["uninstall"]:
                        help_text = "Esc=Back to Left Panel | TAB/H=Back to Left Panel | J/K=Navigate | Enter/Space=Toggle | A=Apply Changes | Q=Quit"
                    else:
                        help_text = "Esc=Back to Left Panel | TAB/H=Back to Left Panel | J/K=Navigate | Enter/Space=Toggle | Q=Quit"
                elif self.selected_segment == "homebrew":
                    help_text = "Esc=Back to Left Panel | TAB/H=Back to Left Panel | J/K=Scroll | Q=Quit"
                elif self.selected_segment == "user_management":
                    help_text = "Esc=Back to Left Panel | TAB/H=Back to Left Panel | J/K=Scroll | Q=Quit"
                elif self.selected_segment == "settings":
                    help_text = "Esc=Back to Left Panel | TAB/H=Back to Left Panel | J/K=Scroll | Q=Quit"
                else:
                    # Default right panel help
                    help_text = "Esc=Back to Left Panel | TAB/H=Back to Left Panel | J/K=Scroll | Q=Quit"

            help_widget.update(help_text)
        except:
            # Silently fail if help widget not found
            pass
