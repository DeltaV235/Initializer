"""Main menu screen for the Linux System Initializer."""

from textual import on, work
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.screen import Screen
from textual.widgets import Button, Static, Rule, Label
from textual.reactive import reactive
from textual.events import Key

from ...config_manager import ConfigManager
from ...modules.system_info import SystemInfoModule
from ...modules.package_manager import PackageManagerDetector
from ...modules.app_installer import AppInstaller
from ...modules.software_models import ApplicationSuite
from ...utils.logger import get_ui_logger
from .main_menu_components import (
    SegmentStateManager,
    SegmentDisplayRenderer,
    PackageManagerInteractionManager,
    AppInstallInteractionManager,
)
from .main_menu_components.app_install_renderer import AppInstallRenderer
from .main_menu_components.event_handlers import EventHandlers
from .main_menu_components.ui_builders import UIBuilders
from .main_menu_components.app_install_manager import AppInstallManager
from .main_menu_components.modal_manager import ModalManager
from .main_menu_components.navigation_manager import NavigationManager, RefreshManager

# Initialize logger for this screen
logger = get_ui_logger("main_menu")


class MainMenuScreen(Screen):
    """Main menu screen with configurator interface."""
    
    BINDINGS = [
        ("s", "select_segment", "Settings"),
        ("q", "quit", "Quit"),
        ("enter", "select_item", "Select"),
        ("tab", "switch_panel", "Switch Panel"),
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

    # Cache and loading states managed by SegmentStateManager
    # Migrated: system_info, homebrew, package_manager, user_management, settings, help

    # App install has special state management
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
        {"id": "vim_management", "name": "Vim Management"},
        {"id": "zsh_management", "name": "Zsh Manager"},
        {"id": "claude_codex_management", "name": "Claude & Codex"},
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

        # Initialize unified segment state manager
        segment_ids = [seg["id"] for seg in self.SEGMENTS]
        self.segment_states = SegmentStateManager(segment_ids)
        logger.debug(f"Initialized SegmentStateManager with {len(segment_ids)} segments")

        # Initialize interaction managers
        self.pm_interaction = PackageManagerInteractionManager(self)
        self.app_interaction = AppInstallInteractionManager(self)
        self.app_manager = AppInstallManager(self)
        self.vim_management_panel = None
        self.zsh_management_panel = None
        self.claude_codex_management_panel = None

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
        try:
            logger.debug(f"watch_current_panel_focus triggered: '{old_value}' → '{new_value}'")
            if old_value != new_value:
                logger.debug(f"Panel focus changed from '{old_value}' to '{new_value}'")
                # Update arrow display based on new panel focus
                is_left_focused = (new_value == "left")
                logger.debug(f"Updating segment buttons for '{self.selected_segment}' with arrow: {is_left_focused}")
                self._update_segment_buttons(self.selected_segment, show_arrow=is_left_focused)

                # Update panel border styles
                left_panel = self.query_one("#left-panel", Vertical)
                right_panel = self.query_one("#right-panel", Vertical)
                if new_value == "left":
                    left_panel.add_class("panel-focused")
                    right_panel.remove_class("panel-focused")
                    logger.debug("Panel borders updated: left focused")
                elif new_value == "right":
                    left_panel.remove_class("panel-focused")
                    right_panel.add_class("panel-focused")
                    logger.debug("Panel borders updated: right focused")

                # Update right panel arrows based on current segment and focus
                if new_value == "left":
                    # When switching to left panel, clear right panel arrows
                    if self.selected_segment == "package_manager":
                        logger.debug("Clearing PM focus indicators")
                        # Clear arrows even if data not loaded
                        if hasattr(self.pm_interaction, '_pm_unique_suffix') and self.pm_interaction._pm_unique_suffix:
                            self.pm_interaction.clear_focus_indicators()
                    elif self.selected_segment == "app_install":
                        logger.debug("Clearing app install focus indicators")
                        # Clear arrows even if data not loaded
                        if hasattr(self, '_app_unique_suffix') and self._app_unique_suffix:
                            self.app_manager.clear_focus_indicators()
                    elif self.selected_segment == "vim_management":
                        panel = getattr(self, "vim_management_panel", None)
                        if panel:
                            logger.debug("Clearing Vim management focus indicators")
                            panel.refresh_action_labels()
                    elif self.selected_segment == "zsh_management":
                        panel = getattr(self, "zsh_management_panel", None)
                        if panel:
                            logger.debug("Clearing Zsh management focus indicators")
                            panel.refresh_action_labels()
                    elif self.selected_segment == "claude_codex_management":
                        panel = getattr(self, "claude_codex_management_panel", None)
                        if panel:
                            logger.debug("Clearing Claude Codex management focus indicators")
                            panel.refresh_action_labels()
                elif new_value == "right":
                    # When switching to right panel, initialize/update arrows based on segment
                    logger.debug(f"Right panel focused, segment: {self.selected_segment}")
                    if self.selected_segment == "package_manager":
                        # Check if PM data is loaded (unique_suffix exists)
                        has_suffix = hasattr(self.pm_interaction, '_pm_unique_suffix')
                        suffix_value = getattr(self.pm_interaction, '_pm_unique_suffix', None) if has_suffix else None
                        logger.debug(f"PM check: has_suffix={has_suffix}, suffix_value={suffix_value}")

                        if has_suffix and suffix_value:
                            logger.debug(f"PM segment - current focused item: {self.pm_interaction._pm_focused_item}")
                            # Initialize focus if not set
                            if not self.pm_interaction._pm_focused_item:
                                logger.debug("Initializing PM focus to 'manager'")
                                self.pm_interaction._pm_focused_item = "manager"
                            logger.debug(f"Calling PM update_focus_indicators(), focused_item now: {self.pm_interaction._pm_focused_item}")
                            self.pm_interaction.update_focus_indicators()
                            logger.debug("PM update_focus_indicators() completed")
                        else:
                            logger.debug(f"PM data not yet loaded, skipping arrow update (has_suffix={has_suffix}, value={suffix_value})")
                    elif self.selected_segment == "app_install":
                        # Check if App Install data is loaded
                        if hasattr(self, '_app_unique_suffix') and self._app_unique_suffix:
                            logger.debug("App install segment - updating focus indicators")
                            # Ensure app_focused_index is valid
                            if not hasattr(self, 'app_focused_index'):
                                self.app_focused_index = 0
                            self.app_manager.update_focus_indicators()
                        else:
                            logger.debug("App install data not yet loaded, skipping arrow update")
                    elif self.selected_segment == "vim_management":
                        panel = getattr(self, "vim_management_panel", None)
                        if panel:
                            if panel.focus_index is None and panel.action_entries:
                                panel.focus_index = 0
                            panel.refresh_action_labels()
                    elif self.selected_segment == "zsh_management":
                        panel = getattr(self, "zsh_management_panel", None)
                        if panel:
                            if panel.focus_index is None and panel.action_entries:
                                panel.focus_index = 0
                            panel.refresh_action_labels()
                    elif self.selected_segment == "claude_codex_management":
                        panel = getattr(self, "claude_codex_management_panel", None)
                        if panel:
                            if panel.focus_index is None and panel.action_entries:
                                panel.focus_index = 0
                            panel.refresh_action_labels()
                    else:
                        logger.debug(f"Segment {self.selected_segment} has no interactive items")
                    # Note: system_info and other segments don't have interactive items with arrows

                # Update help text
                self._update_help_text(is_left_focused)
            else:
                logger.debug("Panel focus value same, no update needed")
        except Exception as e:
            logger.error(f"Error in watch_current_panel_focus: {e}", exc_info=True)
        
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

        # Make right panel scrollable container focusable
        try:
            settings_container = self.query_one("#settings-scroll", ScrollableContainer)
            settings_container.can_focus = True
            logger.debug("Made settings-scroll container focusable")
        except Exception as e:
            logger.warning(f"Failed to make settings container focusable: {e}")

        # Set initial segment content
        self.update_settings_panel()
        # Set initial focus to the selected segment button
        try:
            initial_button = self.query_one(f"#segment-{self.selected_segment}", Button)
            initial_button.focus()
            # Set initial panel focus - this will trigger watch_current_panel_focus
            self.current_panel_focus = "left"
            logger.debug("Initial focus set to left panel (reactive attribute updated)")
        except Exception as e:
            logger.error(f"Failed to set initial focus: {e}")

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
        self.segment_states.clear("system_info")
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
                except Exception as e:
                    # Widget already removed or not mounted
                    logger.debug(f"Could not remove child widget: {e}")

            # Reset package manager focus state and cleanup when switching segments
            if self.selected_segment != "package_manager":
                self.pm_interaction._pm_focused_item = None
                if hasattr(self, '_pm_unique_suffix'):
                    del self.pm_interaction._pm_unique_suffix

            # Reset app install focus state when switching segments
            if self.selected_segment != "app_install":
                self.app_focused_index = 0

            # Reset scroll position to top to maintain consistency
            settings_container.scroll_home(animate=False)

            # Force a refresh to ensure widgets are fully cleared
            self.refresh()

            if self.selected_segment != "vim_management":
                self.vim_management_panel = None

            if self.selected_segment != "zsh_management":
                self.zsh_management_panel = None

            if self.selected_segment != "claude_codex_management":
                self.claude_codex_management_panel = None

            # Add content based on selected segment
            if self.selected_segment == "system_info":
                self._build_system_info_settings(settings_container)
            elif self.selected_segment == "homebrew":
                self._build_homebrew_settings(settings_container)
            elif self.selected_segment == "package_manager":
                self._build_package_manager_settings(settings_container)
            elif self.selected_segment == "app_install":
                self._build_app_install_settings(settings_container)
            elif self.selected_segment == "vim_management":
                self._build_vim_management_settings(settings_container)
            elif self.selected_segment == "zsh_management":
                self._build_zsh_management_settings(settings_container)
            elif self.selected_segment == "claude_codex_management":
                self._build_claude_codex_management_settings(settings_container)
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
        """Delegate to UIBuilders."""
        UIBuilders.build_system_info_settings(self, container)

    @work(exclusive=True, thread=True)
    async def _load_system_info(self) -> None:
        """Load system information in background thread."""
        try:
            # Get system info in background thread (this may take time)
            all_info = self.system_info_module.get_all_info()

            # Update cache and loading state on main thread using app.call_from_thread
            def update_ui():
                self.segment_states.finish_loading("system_info", all_info)

                # Refresh the panel if we're still on system_info segment
                if self.selected_segment == "system_info":
                    self.update_settings_panel()
                    # Force refresh the UI
                    self.refresh()

            self.app.call_from_thread(update_ui)

        except Exception as e:
            # Handle errors on main thread
            def update_error():
                self.segment_states.set_error("system_info", str(e))
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
                self.segment_states.finish_loading("homebrew", homebrew_config)

                # Refresh the panel if we're still on homebrew segment
                if self.selected_segment == "homebrew":
                    self.update_settings_panel()
                    # Force refresh the UI
                    self.refresh()

            self.app.call_from_thread(update_ui)

        except Exception as e:
            # Handle errors on main thread
            def update_error():
                self.segment_states.set_error("homebrew", str(e))
                if self.selected_segment == "homebrew":
                    self.update_settings_panel()
                    # Force refresh the UI
                    self.refresh()

            self.app.call_from_thread(update_error)

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
                self.segment_states.finish_loading("package_manager", pkg_info)

                # Refresh the panel if we're still on package_manager segment
                if self.selected_segment == "package_manager":
                    self.update_settings_panel()
                    # Force refresh the UI
                    self.refresh()

            self.app.call_from_thread(update_ui)

        except Exception as e:
            # Handle errors on main thread
            def update_error():
                self.segment_states.set_error("package_manager", str(e))
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

            # Determine arrow display based on current state
            is_right_focused = (self.current_panel_focus == "right")

            # Initialize PM focus if right panel is focused and not yet set
            if is_right_focused and not self.pm_interaction._pm_focused_item:
                self.pm_interaction._pm_focused_item = "manager"

            pm_focused = self.pm_interaction._pm_focused_item

            # Create static text with arrow if appropriate
            manager_arrow = "[#7dd3fc]▶[/#7dd3fc] " if (pm_focused == "manager" and is_right_focused) else "  "
            pm_text = Static(f"{manager_arrow}{primary.name.upper()}", id=f"pm-manager-item-{unique_suffix}", classes="pm-item-text")
            container.mount(pm_text)

            container.mount(Rule())

            # Show current source (clickable)
            container.mount(Label("Current Source", classes="section-header"))
            if primary.current_source:
                # Truncate long URLs for display
                source = primary.current_source
                if len(source) > 60:
                    source = source[:57] + "..."
                source_arrow = "[#7dd3fc]▶[/#7dd3fc] " if (pm_focused == "source" and is_right_focused) else "  "
                source_text = Static(f"{source_arrow}{source}", id=f"pm-source-item-{unique_suffix}", classes="pm-item-text")
                container.mount(source_text)
            else:
                source_arrow = "[#7dd3fc]▶[/#7dd3fc] " if (pm_focused == "source" and is_right_focused) else "  "
                source_text = Static(f"{source_arrow}Not configured", id=f"pm-source-item-{unique_suffix}", classes="pm-item-text")
                container.mount(source_text)
        else:
            container.mount(Label("No package managers detected", classes="info-display"))

        # Store the primary PM and unique suffix in PM interaction manager
        if primary:
            self.pm_interaction.set_primary_pm(primary, unique_suffix)
    


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
                self.segment_states.finish_loading("user_management", user_config)

                # Refresh the panel if we're still on user_management segment
                if self.selected_segment == "user_management":
                    self.update_settings_panel()
                    # Force refresh the UI
                    self.refresh()

            self.app.call_from_thread(update_ui)

        except Exception as e:
            # Handle errors on main thread
            def update_error():
                self.segment_states.set_error("user_management", str(e))
                if self.selected_segment == "user_management":
                    self.update_settings_panel()
                    # Force refresh the UI
                    self.refresh()

            self.app.call_from_thread(update_error)
    
    @work(exclusive=True, thread=True)
    async def _load_settings_info(self) -> None:
        """Load Settings information in background thread."""
        try:
            # Get app config settings (app_config is an object, not a dict)
            settings_info = {
                "theme": getattr(self.app_config, "theme", "default"),
                "debug": getattr(self.app_config, "debug", False),
                "auto_save": getattr(self.app_config, "auto_save", True)
            }

            # Update cache and loading state on main thread using call_from_thread
            def update_ui():
                self.segment_states.finish_loading("settings", settings_info)

                # Refresh the panel if we're still on settings segment
                if self.selected_segment == "settings":
                    self.update_settings_panel()
                    # Force refresh the UI
                    self.refresh()

            self.app.call_from_thread(update_ui)

        except Exception as e:
            # Handle errors on main thread
            def update_error():
                self.segment_states.set_error("settings", str(e))
                if self.selected_segment == "settings":
                    self.update_settings_panel()
                    # Force refresh the UI
                    self.refresh()

            self.app.call_from_thread(update_error)
    
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
                self.segment_states.finish_loading("help", help_info)

                # Refresh the panel if we're still on help segment
                if self.selected_segment == "help":
                    self.update_settings_panel()
                    # Force refresh the UI
                    self.refresh()

            self.app.call_from_thread(update_ui)

        except Exception as e:
            # Handle errors on main thread
            def update_error():
                self.segment_states.set_error("help", str(e))
                if self.selected_segment == "help":
                    self.update_settings_panel()
                    # Force refresh the UI
                    self.refresh()

            self.app.call_from_thread(update_error)
    
    def _build_app_install_settings(self, container: ScrollableContainer) -> None:
        """Delegate to UIBuilders."""
        UIBuilders.build_app_install_settings(self, container)

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

    def _on_install_complete(self, result=None) -> None:
        """Callback when app installation/uninstallation completes."""
        from ...utils.logger import get_ui_logger
        logger = get_ui_logger("main_menu")

        logger.info("App install/uninstall completed, refreshing app list")

        # Reload app install info to reflect new installation status
        if self.selected_segment == "app_install":
            # Clear cache and reload
            self.app_install_cache = None
            self.app_install_loading = True
            self._load_app_install_info()

            # Update the panel
            self.update_settings_panel()





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

        # Use the same logic as display items to iterate through all apps/components
        for item in self.app_install_cache:
            # Handle standalone applications and application suites
            if not isinstance(item, ApplicationSuite):
                # Standalone application
                is_selected = self.app_selection_state.get(item.name, item.installed)

                if item.installed and not is_selected:
                    # Installed but unmarked - uninstall
                    changes["uninstall"].append(item.name)
                elif not item.installed and is_selected:
                    # Not installed but marked - install
                    changes["install"].append(item.name)
            else:
                # Application suite - check its components
                for component in item.components:
                    is_selected = self.app_selection_state.get(component.name, component.installed)

                    if component.installed and not is_selected:
                        # Installed but unmarked - uninstall
                        changes["uninstall"].append(component.name)
                    elif not component.installed and is_selected:
                        # Not installed but marked - install
                        changes["install"].append(component.name)

        return changes

    def _apply_app_changes_internal(self) -> None:
        """Internal method to apply app changes without focus checks."""
        logger.debug("_apply_app_changes_internal called")

        if not self.app_install_cache or isinstance(self.app_install_cache, dict):
            logger.debug("No app install cache or cache is dict, returning")
            return

        changes = self._calculate_app_changes()
        logger.debug(f"Changes calculated: {changes}")

        if not changes["install"] and not changes["uninstall"]:
            logger.debug("No changes to apply, showing message")
            self._show_message("No changes to apply")
            return

        # 调用完整的应用安装逻辑，跳过开头的焦点检查
        self.app_manager.execute_changes(changes)


    def action_apply_app_changes(self) -> None:
        """Delegate to EventHandlers."""
        EventHandlers.action_apply_app_changes(self)

    def refresh_and_reset_app_page(self) -> None:
        """Refresh and reset app page - wrapper for navigation_manager.

        This method exists to maintain API compatibility with AppInstallProgress
        which calls this method after install/uninstall completion.
        """
        from .main_menu_components.navigation_manager import RefreshManager
        RefreshManager.refresh_and_reset_app_page(self)

    def _build_homebrew_settings(self, container: ScrollableContainer) -> None:
        """Delegate to UIBuilders."""
        UIBuilders.build_homebrew_settings(self, container)

    def _build_package_manager_settings(self, container: ScrollableContainer) -> None:
        """Delegate to UIBuilders."""
        UIBuilders.build_package_manager_settings(self, container)

    def _build_user_management_settings(self, container: ScrollableContainer) -> None:
        """Delegate to UIBuilders."""
        UIBuilders.build_user_management_settings(self, container)

    def _build_vim_management_settings(self, container: ScrollableContainer) -> None:
        """构建 Vim 管理面板。"""
        UIBuilders.build_vim_management_settings(self, container)

    def _build_zsh_management_settings(self, container: ScrollableContainer) -> None:
        """构建 Zsh 管理面板。"""
        UIBuilders.build_zsh_management_settings(self, container)

    def _build_claude_codex_management_settings(self, container: ScrollableContainer) -> None:
        """构建 Claude Code & Codex 管理面板。"""
        UIBuilders.build_claude_codex_management_settings(self, container)

    def _build_app_settings(self, container: ScrollableContainer) -> None:
        """Delegate to UIBuilders."""
        UIBuilders.build_app_settings(self, container)

    def _build_help_content(self, container: ScrollableContainer) -> None:
        """Delegate to UIBuilders."""
        UIBuilders.build_help_content(self, container)

    def _show_error_message(self, message: str) -> None:
        """Show error message in the settings panel."""
        try:
            settings_container = self.query_one("#settings-scroll", ScrollableContainer)
            # Clear existing content
            children = list(settings_container.children)
            for child in children:
                child.remove()
            settings_container.mount(Static(f"❌ {message}", id="error-message"))
        except Exception as e:
            logger.error(f"显示错误消息失败: {e}")
    
    @on(Button.Pressed)
    def handle_segment_selection(self, event: Button.Pressed) -> None:
        """Handle segment button selection."""
        button_id = event.button.id
        logger.debug(f"Button.Pressed: button_id={button_id}, current_segment={self.selected_segment}, current_panel_focus={self.current_panel_focus}")

        if button_id and button_id.startswith("segment-"):
            segment_id = button_id.replace("segment-", "")

            # IMPORTANT: Only process button press if we're in the left panel
            # This prevents accidental segment switches when focus is not properly managed
            if self.current_panel_focus != "left":
                logger.debug(f"Ignoring button press because focus is on '{self.current_panel_focus}' panel")
                return

            # Also check if this button actually has focus
            if self.focused != event.button:
                logger.warning(f"Button pressed but doesn't have focus! focused={self.focused}, button={event.button}")
                # Don't process if the button doesn't actually have focus
                return

            logger.debug(f"Processing segment switch from '{self.selected_segment}' to '{segment_id}'")

            # Update segment selection - this will trigger watch_selected_segment
            # which automatically calls update_settings_panel(), so we don't need to call it here
            self.selected_segment = segment_id

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
            from .package_manager_installer import PackageManagerInstaller
            def on_install_actions_selected(actions: list):
                # Handle installation actions if needed
                pass
            self.app.push_screen(PackageManagerInstaller(on_install_actions_selected, self.config_manager))

        elif button_id and button_id.startswith("apply-app-changes-"):
            # Apply app changes (legacy support)
            self.action_apply_app_changes()

    def _open_source_selection_modal(self) -> None:
        """Open modal for source selection."""
        from ...utils.logger import get_ui_logger
        logger = get_ui_logger("main_menu")

        logger.info("[PM] _open_source_selection_modal called")

        if not hasattr(self.pm_interaction, '_primary_pm') or not self.pm_interaction._primary_pm:
            logger.warning("[PM] No primary PM, cannot open modal")
            return

        logger.info(f"[PM] Opening modal for {self.pm_interaction._primary_pm.name}")
            
        from .package_mirror_picker import PackageMirrorPicker
        def on_source_selected(source_url: str) -> None:
            """Handle source selection - show confirmation modal."""
            if source_url:
                logger.info(f"[PM] Source selected: {source_url[:50]}...")
                # Show confirmation modal instead of directly changing
                from .package_mirror_confirm import PackageMirrorConfirm

                def on_confirm_callback(confirmed: bool, message: str) -> None:
                    """Handle confirmation result."""
                    logger.info(f"[PM] Confirmation result: confirmed={confirmed}")
                    if confirmed:
                        # Update the cached source and refresh display
                        self.pm_interaction._primary_pm.current_source = source_url
                        # Update the cache in SegmentStateManager
                        state = self.segment_states.get_state("package_manager")
                        if state and state.cache:
                            state.cache["primary"] = self.pm_interaction._primary_pm
                        self.update_settings_panel()
                        # Show success message briefly
                        self._show_temp_message(f"✅ {message}")
                    else:
                        # Show error/cancel message
                        if message:
                            self._show_temp_message(f"❌ {message}")

                logger.info(f"[PM] Creating PackageMirrorConfirm modal")
                confirm_modal = PackageMirrorConfirm(
                    self.pm_interaction._primary_pm,
                    source_url,
                    on_confirm_callback,
                    self.config_manager
                )
                self.app.push_screen(confirm_modal)
                logger.info(f"[PM] PackageMirrorConfirm modal pushed")

        logger.info(f"[PM] Creating PackageMirrorPicker modal")
        modal = PackageMirrorPicker(self.pm_interaction._primary_pm, on_source_selected, self.config_manager)
        # Clear panel focus before showing modal
        logger.info(f"[PM] Clearing panel focus")
        self._clear_panel_focus()
        logger.info(f"[PM] Pushing modal to app")
        self.app.push_screen(modal)
        logger.info(f"[PM] Modal pushed successfully")
    
    def _show_temp_message(self, message: str) -> None:
        """Show a temporary message in the title."""
        try:
            title_widget = self.query_one("#title", Static)
            original_title = title_widget.renderable
            title_widget.update(message)
            # Reset after 3 seconds
            self.set_timer(3.0, lambda: title_widget.update(original_title))
        except Exception as e:
            logger.debug(f"显示临时消息失败: {e}")
    
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
                "vim_management": "Vim Management",
                "zsh_management": "Zsh Manager",
                "claude_codex_management": "Claude & Codex",
                "user_management": "User Management",
                "settings": "Settings",
                "help": "Help"
            }
            
            display_title = title_map.get(selected_id, "Settings")
            title_widget.update(display_title)
        except Exception as e:
            # Silently fail if title widget not found
            logger.debug(f"更新面板标题失败: {e}")
    
    def _clear_panel_focus(self) -> None:
        """Clear panel focus styles to prevent highlight leak to modals."""
        try:
            left_panel = self.query_one("#left-panel", Vertical)
            right_panel = self.query_one("#right-panel", Vertical)
            left_panel.remove_class("panel-focused")
            right_panel.remove_class("panel-focused")
        except Exception as e:
            logger.debug(f"清除面板焦点样式失败: {e}")

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
    
    def action_select_segment(self) -> None:
        """Delegate to EventHandlers."""
        EventHandlers.action_select_segment(self)

    def on_key(self, event) -> bool:
        """Handle key events, including 1-6 shortcuts and two-level Esc exit."""
        logger.debug(f"on_key: key={event.key}, panel_focus={self.current_panel_focus}, segment={self.selected_segment}")

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

        # Handle space key for app install section (selection toggle)
        if event.key == "space" and self.selected_segment == "app_install":
            is_left = self._is_focus_in_left_panel()
            logger.debug(
                f"Space pressed - is_left_by_focus: {is_left}, current_panel_focus: {self.current_panel_focus}"
            )
            if not is_left:
                logger.info("Toggling app selection via space key")
                self.app_manager.toggle_current_item()
                event.prevent_default()
                event.stop()
                return True
            logger.debug("Space pressed but in left panel, ignoring")

        # Handle L key for suite expansion/collapse
        if event.key in ("l", "L") and self.selected_segment == "app_install":
            is_left = self._is_focus_in_left_panel()
            logger.debug(
                f"L pressed - is_left_by_focus: {is_left}, current_panel_focus: {self.current_panel_focus}"
            )
            if not is_left:
                handled = self.app_manager.toggle_current_suite_expansion()
                if handled:
                    event.prevent_default()
                    event.stop()
                    return True
            else:
                logger.debug("L pressed but in left panel, ignoring")

        # Handle enter key based on current segment and panel focus
        if event.key == "enter":
            # Check both reactive state and actual focus position
            is_left_by_reactive = (self.current_panel_focus == "left")
            is_left_by_focus = self._is_focus_in_left_panel()
            logger.info(
                f"[ENTER] Enter pressed - reactive: {self.current_panel_focus}, is_left_by_focus: {is_left_by_focus}, focused_widget: {self.focused}, segment: {self.selected_segment}"
            )

            # Only handle enter in right panel to prevent triggering left panel buttons
            if not is_left_by_focus:
                if self.selected_segment == "app_install":
                    logger.info("[ENTER] Handling enter in app_install segment")
                    handled = self.app_manager.handle_enter_key()
                    logger.info(f"[ENTER] handle_enter_key returned: {handled}")
                    if handled:
                        event.prevent_default()
                        event.stop()
                        return True  # Consume the event only if it was actually handled
                elif self.selected_segment == "package_manager":
                    logger.info("[ENTER] Handling enter in package_manager segment")
                    # Call PM interaction directly instead of relying on action
                    self.pm_interaction.handle_item_selection()
                    logger.info("[ENTER] Called pm_interaction.handle_item_selection()")
                    event.prevent_default()
                    event.stop()
                    return True
                elif self.selected_segment == "vim_management":
                    logger.info("[ENTER] Handling enter in vim_management segment")
                    panel = getattr(self, "vim_management_panel", None)
                    if panel:
                        logger.info("[ENTER] Calling panel.handle_enter()")
                        panel.handle_enter()
                        event.prevent_default()
                        event.stop()
                        return True
                    logger.warning("[ENTER] vim_management_panel is None!")
                elif self.selected_segment == "zsh_management":
                    logger.info("[ENTER] Handling enter in zsh_management segment")
                    panel = getattr(self, "zsh_management_panel", None)
                    if panel:
                        logger.info("[ENTER] Calling panel.handle_enter()")
                        panel.handle_enter()
                        event.prevent_default()
                        event.stop()
                        return True
                    logger.warning("[ENTER] zsh_management_panel is None!")
                elif self.selected_segment == "claude_codex_management":
                    logger.info("[ENTER] Handling enter in claude_codex_management segment")
                    panel = getattr(self, "claude_codex_management_panel", None)
                    if panel:
                        logger.info("[ENTER] Calling panel.handle_enter()")
                        panel.handle_enter()
                        event.prevent_default()
                        event.stop()
                        return True
                    logger.warning("[ENTER] claude_codex_management_panel is None!")
                else:
                    # For other segments (system_info, etc.), prevent enter from triggering buttons
                    logger.debug(f"Preventing enter default behavior in {self.selected_segment} segment")
                    event.prevent_default()
                    event.stop()
                    return True  # Consume the event to prevent left panel button activation
            else:
                logger.debug("Enter pressed in left panel - allowing default behavior")

        # Handle number shortcuts only when focus is in left panel
        if event.key.isdecimal() and self._is_focus_in_left_panel():
            try:
                segment_index = int(event.key) - 1
                if 0 <= segment_index < len(self.SEGMENTS):
                    selected_segment = self.SEGMENTS[segment_index]

                    # Update the selected segment - this will trigger watch_selected_segment
                    self.selected_segment = selected_segment["id"]
                    # Don't call update_settings_panel() here - it's handled by watch_selected_segment
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
        """Delegate to EventHandlers."""
        EventHandlers.action_refresh_current_page(self)

    def action_homebrew(self) -> None:
        """Delegate to EventHandlers."""
        EventHandlers.action_homebrew(self)

    def action_package_manager(self) -> None:
        """Delegate to EventHandlers."""
        EventHandlers.action_package_manager(self)

    def action_user_management(self) -> None:
        """Delegate to EventHandlers."""
        EventHandlers.action_user_management(self)

    def action_settings(self) -> None:
        """Delegate to EventHandlers."""
        EventHandlers.action_settings(self)

    def action_help(self) -> None:
        """Delegate to EventHandlers."""
        EventHandlers.action_help(self)

    def action_quit(self) -> None:
        """Delegate to EventHandlers."""
        EventHandlers.action_quit(self)

    def action_switch_panel(self) -> None:
        """Delegate to EventHandlers."""
        EventHandlers.action_switch_panel(self)

    def action_nav_left(self) -> None:
        """Delegate to EventHandlers."""
        logger.debug("action_nav_left called in MainMenuScreen")
        EventHandlers.action_nav_left(self)

    def action_nav_down(self) -> None:
        """Delegate to EventHandlers."""
        EventHandlers.action_nav_down(self)

    def action_nav_up(self) -> None:
        """Delegate to EventHandlers."""
        EventHandlers.action_nav_up(self)

    def action_nav_right(self) -> None:
        """Delegate to EventHandlers."""
        logger.debug("action_nav_right called in MainMenuScreen")
        EventHandlers.action_nav_right(self)

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
    


    def _check_and_update_panel_focus(self) -> None:
        """Check which panel has focus and update the visual indicators."""
        focused = self.focused
        if not focused:
            return

        # Walk up the widget tree to determine which panel contains the focused widget
        current = focused
        while current is not None:
            if current.id == "left-panel":
                if self.current_panel_focus != "left":
                    self.current_panel_focus = "left"
                return
            elif current.id == "right-panel" or current.id == "settings-scroll":
                if self.current_panel_focus != "right":
                    self.current_panel_focus = "right"
                return
            current = current.parent
    
    def action_select_item(self) -> None:
        """Delegate to EventHandlers."""
        EventHandlers.action_select_item(self)

    def _update_package_manager_info(self) -> None:
        """Update package manager information in the main menu display."""
        try:
            # Refresh package manager detection
            from ...modules.package_manager import PackageManagerDetector
            detector = PackageManagerDetector(self.config_manager)
            self.pm_interaction._primary_pm = detector.get_primary_package_manager()

            # Update the package manager display in the UI
            if hasattr(self, '_primary_pm') and self.pm_interaction._primary_pm:
                self._display_package_manager()
        except Exception as e:
            # Silently fail to avoid disrupting the UI
            logger.debug(f"watch_selected_segment 执行失败: {e}")



    def reset_app_selection_state(self) -> None:
        """重置应用选择状态到当前安装状态。"""
        try:
            logger.info("Resetting app selection state to current installation status")

            # Reset selection state based on current installation status
            if self.app_install_cache and not isinstance(self.app_install_cache, dict):
                # Get all applications and reset their selection state
                all_applications = self.app_installer._get_all_applications_flat()
                for app in all_applications:
                    # Reset to current installation status
                    self.app_selection_state[app.name] = app.installed

                logger.info(f"Reset selection state for {len(all_applications)} applications")
            else:
                logger.warning("Cannot reset app selection state: cache not available")
        except Exception as e:
            logger.error(f"Failed to reset app selection state: {str(e)}")


    def _safe_ui_update_after_refresh(self) -> None:
        """安全地更新UI，避免冲突。"""
        try:
            # 只在仍在app_install段时才更新
            if self.selected_segment == "app_install":
                self.update_settings_panel()
                # 不调用self.refresh()以避免冲突
                logger.debug("Safe UI update completed after app refresh")
        except Exception as e:
            logger.error(f"Error in safe UI update: {str(e)}")

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
        except Exception as e:
            # Silently fail if title widget is not found
            logger.debug(f"显示消息失败: {e}")

    def _update_help_text(self, is_left_focused: bool = None) -> None:
        """Update the main menu help text based on current segment and panel focus."""
        logger.debug(f"_update_help_text called: segment={self.selected_segment}, left_focused={is_left_focused}")
        try:
            help_widget = self.query_one("#help-box Label", Label)

            # Check which panel has focus - use provided parameter or detect
            if is_left_focused is None:
                is_left_focused = self._is_focus_in_left_panel()

            logger.debug(f"Help text update: segment={self.selected_segment}, is_left_focused={is_left_focused}")

            if is_left_focused:
                # Left panel focused - show navigation help (consistent across all pages)
                help_text = "Esc=Back/Quit | Q=Quit | R=Refresh | S=Settings | TAB/H/L=Switch Focus | J/K=Up/Down | Enter=Enter Right Panel | 1-6=Quick Select"
            else:
                # Right panel focused - show page-specific functionality
                if self.selected_segment == "system_info":
                    help_text = "Esc=Back to Left Panel | TAB/H=Back to Left Panel | R=Refresh | J/K=Scroll | Q=Quit"
                elif self.selected_segment == "package_manager":
                    help_text = "Esc=Back to Left Panel | TAB/H=Back to Left Panel | R=Refresh | J/K=Navigate | Enter=Select | Q=Quit"
                elif self.selected_segment == "app_install":
                    # Show app-specific help with apply changes info when needed
                    changes = self._calculate_app_changes()
                    logger.debug(f"App changes calculated: install={len(changes['install'])}, uninstall={len(changes['uninstall'])}")
                    if changes["install"] or changes["uninstall"]:
                        help_text = "Esc=Back to Left Panel | TAB/H=Back to Left Panel | R=Refresh | J/K=Navigate | Space=Select | L=Expand | Enter=Apply Changes | Q=Quit"
                    else:
                        help_text = "Esc=Back to Left Panel | TAB/H=Back to Left Panel | R=Refresh | J/K=Navigate | Space=Select | L=Expand | Enter=Apply Changes | Q=Quit"
                elif self.selected_segment == "homebrew":
                    help_text = "Esc=Back to Left Panel | TAB/H=Back to Left Panel | R=Refresh | J/K=Scroll | Q=Quit"
                elif self.selected_segment == "vim_management":
                    panel = getattr(self, "vim_management_panel", None)
                    if panel:
                        help_text = panel.get_help_text()
                    else:
                        help_text = "Esc=Back to Left Panel | TAB/H=Back to Left Panel | R=Refresh | I=Install | J/K=Scroll | Q=Quit"
                elif self.selected_segment == "zsh_management":
                    panel = getattr(self, "zsh_management_panel", None)
                    if panel:
                        help_text = panel.get_help_text()
                    else:
                        help_text = "Esc=Back to Left Panel | TAB/H=Back to Left Panel | R=Refresh | J/K=Scroll | Q=Quit"
                elif self.selected_segment == "claude_codex_management":
                    panel = getattr(self, "claude_codex_management_panel", None)
                    if panel:
                        help_text = panel.get_help_text()
                    else:
                        help_text = "Esc=Back to Left Panel | TAB/H=Back to Left Panel | R=Refresh | J/K=Navigate | Enter=Select | Q=Quit"
                elif self.selected_segment == "user_management":
                    help_text = "Esc=Back to Left Panel | TAB/H=Back to Left Panel | R=Refresh | J/K=Scroll | Q=Quit"
                elif self.selected_segment == "settings":
                    help_text = "Esc=Back to Left Panel | TAB/H=Back to Left Panel | R=Refresh | J/K=Scroll | Q=Quit"
                else:
                    # Default right panel help
                    help_text = "Esc=Back to Left Panel | TAB/H=Back to Left Panel | R=Refresh | J/K=Scroll | Q=Quit"

            logger.debug(f"Setting help text: {help_text}")
            help_widget.update(help_text)
        except Exception as e:
            # Log the error instead of silently failing
            logger.error(f"Failed to update help text: {e}")
            pass
