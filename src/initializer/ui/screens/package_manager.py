"""Package Manager management screen."""

from textual import on, work
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Static, Rule, Label, Input, RadioSet, RadioButton
from textual.reactive import reactive

from ...config_manager import ConfigManager
from ...modules.package_manager import PackageManagerDetector
from .source_selection_modal import SourceSelectionModal
from .mirror_confirmation_modal import MirrorConfirmationModal
from .package_manager_install_modal import PackageManagerInstallModal
from .installation_confirmation_modal import InstallationConfirmationModal
from .installation_progress_modal import InstallationProgressModal


class PackageManagerScreen(Screen):
    """Screen for Package Manager detection and source management."""
    
    CSS = """
    #pm-content {
        height: 1fr;
    }
    
    #pm-left-panel, #pm-right-panel {
        height: 100%;
        width: 50%;
    }
    
    #pm-list, #source-container {
        height: 1fr;
        overflow-y: auto;
        scrollbar-size: 1 1;
    }
    
    .panel {
        border: solid $primary-lighten-2;
        padding: 0 1;
    }
    
    .panel:focus-within {
        border: solid $primary;
    }
    
    .panel-title {
        background: $surface;
        text-style: bold;
        margin: 0 0 1 0;
    }
    
    .pm-item {
        padding: 0 1;
        margin: 0 0 1 0;
    }
    
    .info-key {
        text-style: bold;
        color: $text;
        margin: 1 0 0 0;
    }
    
    .section-title {
        text-style: bold;
        color: $primary;
        margin: 0 0 0 0;
    }
    
    .current-source-display {
        color: $success;
        margin: 0 0 0 1;
    }
    
    .current-source-none {
        color: $text-muted;
        margin: 0 0 0 1;
    }
    
    .help-text {
        text-align: center;
        color: $text-muted;
        height: 1;
        min-height: 1;
        max-height: 1;
        margin: 0 0 0 0;
        padding: 0 0 0 0;
        background: $surface;
        text-style: none;
    }
    
    #pm-actions {
        height: auto;
        margin: 1 0 0 0;
    }
    """
    
    BINDINGS = [
        ("escape", "back", "Back"),
        ("q", "back", "Back"),
        ("tab", "switch_focus", "Switch Focus"),
        # Vim-like navigation
        ("h", "nav_left", "Left"),
        ("j", "nav_down", "Down"),
        ("k", "nav_up", "Up"),
        ("l", "nav_right", "Right"),
        ("enter", "select_current", "Select"),
    ]
    
    # Reactive properties for state management
    selected_pm = reactive(None)
    current_source = reactive("")
    loading = reactive(True)
    focus_panel = reactive("left")  # "left" or "right"
    left_focused_item = reactive(0)  # Index of focused item in left panel
    
    def __init__(self, config_manager: ConfigManager):
        super().__init__()
        self.config_manager = config_manager
        self.detector = PackageManagerDetector(config_manager)
        self.package_managers = []
        self.primary_pm = None
        
    def compose(self) -> ComposeResult:
        """Compose the Package Manager interface."""
        with Container(id="pm-container"):
            yield Static("📦 Package Manager Configuration", id="title")
            yield Rule()
            
            with Horizontal(id="pm-content"):
                # Left panel - Package managers list
                with Vertical(id="pm-left-panel", classes="panel"):
                    yield Label("Package Managers", classes="panel-title")
                    # Don't add any initial content - will be populated in on_mount
                    with VerticalScroll(id="pm-list"):
                        yield Vertical(id="pm-list-container")
                    
                # Right panel - Source management
                with Vertical(id="pm-right-panel", classes="panel"):
                    yield Label("Mirror Source Management", classes="panel-title")
                    # Don't add any initial content - will be populated dynamically
                    with VerticalScroll(id="source-container"):
                        yield Vertical(id="source-list-container")
            
            # Bottom action buttons
            with Horizontal(id="pm-actions"):
                yield Button("🔙 Back", id="back", variant="default")
    
    def on_mount(self) -> None:
        """Initialize the screen."""
        # Add initial loading message
        try:
            pm_list_container = self.query_one("#pm-list-container", Vertical)
            pm_list_container.mount(Static("Detecting package managers...", id="pm-loading"))
            
            source_list_container = self.query_one("#source-list-container", Vertical)
            source_list_container.mount(Static("Select a package manager to view sources", id="source-placeholder"))
        except Exception:
            pass
        
        self._detect_package_managers()
    
    @work(exclusive=True, thread=True)
    async def _detect_package_managers(self) -> None:
        """Detect available package managers in background."""
        try:
            # Get package managers from detector
            self.package_managers = self.detector.package_managers
            self.primary_pm = self.detector.get_primary_package_manager()
            
            # Update UI on main thread
            def update_ui():
                self.loading = False
                self._display_package_managers()
                
                # Auto-select primary package manager
                if self.primary_pm:
                    self.selected_pm = self.primary_pm
                    self._display_source_options(self.primary_pm)
            
            self.app.call_from_thread(update_ui)
            
        except Exception as e:
            def show_error():
                self.loading = False
                self._show_error(f"Error detecting package managers: {str(e)}")
            
            self.app.call_from_thread(show_error)
    
    def _display_package_managers(self) -> None:
        """Display detected package managers in the left panel."""
        try:
            pm_list_container = self.query_one("#pm-list-container", Vertical)
            
            # Check if we need to initialize (first time) or just update
            needs_init = len(pm_list_container.children) == 0
            
            if needs_init:
                # First time setup - create all components
                # Add "Available Package Managers" option
                arrow = "▶ " if (self.focus_panel == "left" and self.left_focused_item == 0) else "  "
                pm_list_container.mount(Static(f"{arrow}🔧 Available Package Managers\n    Install/Uninstall package managers", 
                                    id="pm-available", classes="pm-item"))
                
                if not self.package_managers:
                    pm_list_container.mount(Static("No package managers installed", classes="info-message"))
                    return
                
                # Display label for installed package managers with minimal spacing
                pm_list_container.mount(Label("Installed Package Managers:", classes="info-key"))
                
                # Display each installed package manager
                for i, pm in enumerate(self.package_managers):
                    # Adjust index for arrow indicator (account for "Available" option)
                    display_index = i + 1  # +1 for "Available Package Managers" option
                    
                    # Create arrow indicator for CLI-style navigation
                    arrow = "▶ " if (self.focus_panel == "left" and self.left_focused_item == display_index) else "  "
                    
                    # Package manager name and status
                    pm_info = f"{arrow}📦 {pm.name.upper()}"
                    if pm == self.primary_pm:
                        pm_info += " (Primary)"
                    
                    # Show current source if available on the same line
                    if pm.current_source:
                        source_text = self._truncate_source(pm.current_source, 25)
                        pm_info += f"\n    Source: {source_text}"
                    else:
                        pm_info += "\n    Source: Not configured"
                    
                    pm_list_container.mount(Static(pm_info, id=f"pm-{i}", classes="pm-item"))
            else:
                # Update existing components without recreating them
                # Update "Available Package Managers" arrow
                try:
                    available_item = self.query_one("#pm-available", Static)
                    arrow = "▶ " if (self.focus_panel == "left" and self.left_focused_item == 0) else "  "
                    available_item.update(f"{arrow}🔧 Available Package Managers\n    Install/Uninstall package managers")
                except Exception:
                    pass
                
                # Update each package manager item
                for i, pm in enumerate(self.package_managers):
                    try:
                        pm_item = self.query_one(f"#pm-{i}", Static)
                        
                        # Adjust index for arrow indicator (account for "Available" option)
                        display_index = i + 1  # +1 for "Available Package Managers" option
                        
                        # Create arrow indicator for CLI-style navigation
                        arrow = "▶ " if (self.focus_panel == "left" and self.left_focused_item == display_index) else "  "
                        
                        # Package manager name and status
                        pm_info = f"{arrow}📦 {pm.name.upper()}"
                        if pm == self.primary_pm:
                            pm_info += " (Primary)"
                        
                        # Show current source if available on the same line
                        if pm.current_source:
                            source_text = self._truncate_source(pm.current_source, 25)
                            pm_info += f"\n    Source: {source_text}"
                        else:
                            pm_info += "\n    Source: Not configured"
                        
                        pm_item.update(pm_info)
                    except Exception:
                        # If item doesn't exist, we might need to recreate
                        pass
            
            # Scroll to current selection directly after update
            self._scroll_to_current()
                
        except Exception as e:
            self._show_error(f"Error displaying package managers: {str(e)}")
    
    def _truncate_source(self, source: str, max_length: int = 40) -> str:
        """Truncate long source URLs for display."""
        if len(source) <= max_length:
            return source
        return source[:max_length-3] + "..."
    
    def _display_source_options(self, pm) -> None:
        """Display package manager information in the right panel."""
        try:
            source_list_container = self.query_one("#source-list-container", Vertical)
            
            # Clear ALL existing content completely
            source_list_container.remove_children()
            
            # Reset scroll position to top when displaying new content
            source_container = self.query_one("#source-container", VerticalScroll)
            source_container.scroll_y = 0
            
            if pm is None and self.left_focused_item == 0:
                # Show info about package manager installation
                source_list_container.mount(Label("Package Manager Installation", classes="section-title"))
                source_list_container.mount(Static("Press ENTER to manage package manager installations.", classes="info-message"))
                source_list_container.mount(Label("Available Actions:", classes="info-key"))
                source_list_container.mount(Static("• Install new package managers (Homebrew, Snap, Flatpak)"))
                source_list_container.mount(Static("• Uninstall existing package managers"))
                source_list_container.mount(Static("• View installation status"))
            elif not pm:
                source_list_container.mount(Static("Select a package manager to configure", classes="info-message"))
            else:
                # Show current package manager info
                source_list_container.mount(Label(f"Package Manager: {pm.name.upper()}", classes="section-title"))
                
                # Show current source
                source_list_container.mount(Label("Current Source:", classes="info-key"))
                if pm.current_source:
                    source_list_container.mount(Static(pm.current_source, classes="current-source-display"))
                else:
                    source_list_container.mount(Static("Not configured", classes="current-source-none"))
                
                source_list_container.mount(Static("ENTER=Change Source", classes="help-text"))
                
        except Exception as e:
            self._show_error(f"Error displaying source options: {str(e)}")
    
    def _show_source_selection_modal(self, pm) -> None:
        """Show the source selection modal."""
        def on_source_selected(selected_source: str):
            # Show confirmation modal
            def on_confirmation_result(success: bool, message: str):
                if success:
                    # Update the package manager's current source
                    pm.current_source = selected_source
                    # Refresh the displays
                    self._display_package_managers()
                    self._display_source_options(pm)
                    self._show_message(message)
                else:
                    self._show_message(message, error=not success)
            
            # Show confirmation modal
            try:
                self.app.push_screen(
                    MirrorConfirmationModal(pm, selected_source, on_confirmation_result, self.config_manager)
                )
            except Exception as e:
                self._show_message(f"Error showing confirmation: {str(e)}", error=True)
        
        # Show source selection modal
        self.app.push_screen(
            SourceSelectionModal(pm, on_source_selected, self.config_manager)
        )
    
    @on(Button.Pressed)
    def handle_button_press(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        button_id = event.button.id
        
        if button_id == "back":
            self.app.pop_screen()
    
    def action_select_current(self) -> None:
        """Handle Enter key - select current item."""
        if self.focus_panel == "left":
            # Check if "Available Package Managers" is selected
            if self.left_focused_item == 0:
                # Show package manager installation modal
                self._show_package_manager_install_modal()
            elif self.package_managers and self.left_focused_item > 0:
                # Adjust index for actual package manager (subtract 1 for "Available" option)
                pm_index = self.left_focused_item - 1
                if 0 <= pm_index < len(self.package_managers):
                    pm = self.package_managers[pm_index]
                    self.selected_pm = pm
                    self._display_source_options(pm)
                    try:
                        self._show_source_selection_modal(pm)
                    except Exception as e:
                        self._show_error(f"Error showing source selection: {str(e)}")
    
    def _show_message(self, message: str, error: bool = False) -> None:
        """Show a message to the user."""
        # For now, just update the title - in production, use a proper notification system
        title_widget = self.query_one("#title", Static)
        if error:
            title_widget.update(f"📦 Package Manager - {message}")
        else:
            title_widget.update(f"📦 Package Manager - {message}")
        
        # Reset title after a delay
        self.set_timer(3.0, lambda: title_widget.update("📦 Package Manager Configuration"))
    
    def _show_error(self, error_message: str) -> None:
        """Show an error message."""
        self._show_message(error_message, error=True)
    
    # Navigation actions
    def action_back(self) -> None:
        """Go back to main menu."""
        self.app.pop_screen()
    
    def action_switch_focus(self) -> None:
        """Switch focus between panels."""
        if self.focus_panel == "left":
            self.focus_panel = "right"
        else:
            self.focus_panel = "left"
        
        # Update displays
        self._display_package_managers()
    
    def action_nav_left(self) -> None:
        """Navigate left - switch to left panel."""
        if self.focus_panel == "right":
            self.focus_panel = "left"
            self._display_package_managers()
    
    def action_nav_right(self) -> None:
        """Navigate right - switch to right panel."""
        if self.focus_panel == "left":
            self.focus_panel = "right"
            self._display_package_managers()
    
    def action_nav_down(self) -> None:
        """Navigate down within current panel."""
        if self.focus_panel == "left":
            # Total items = 1 (Available) + number of installed PMs
            total_items = 1 + len(self.package_managers)
            
            if self.left_focused_item < total_items - 1:
                self.left_focused_item += 1
                
                # Auto-select and display details if it's an installed PM
                if self.left_focused_item > 0 and self.package_managers:
                    pm_index = self.left_focused_item - 1
                    if pm_index < len(self.package_managers):
                        pm = self.package_managers[pm_index]
                        self.selected_pm = pm
                        self._display_source_options(pm)
                else:
                    # Clear right panel when "Available" is selected
                    self._display_source_options(None)
            
            # Update display first, then scroll directly
            self._display_package_managers()
            self._scroll_to_current()
    
    def action_nav_up(self) -> None:
        """Navigate up within current panel."""
        if self.focus_panel == "left":
            if self.left_focused_item > 0:
                self.left_focused_item -= 1
                
                # Auto-select and display details if it's an installed PM
                if self.left_focused_item > 0 and self.package_managers:
                    pm_index = self.left_focused_item - 1
                    if pm_index < len(self.package_managers):
                        pm = self.package_managers[pm_index]
                        self.selected_pm = pm
                        self._display_source_options(pm)
                else:
                    # Clear right panel when "Available" is selected
                    self._display_source_options(None)
            
            # Update display first, then scroll directly
            self._display_package_managers()
            self._scroll_to_current()
    
    def _show_package_manager_install_modal(self) -> None:
        """Show the package manager installation modal."""
        def on_install_actions_selected(actions: list):
            if not actions:
                return
            
            # Show confirmation modal
            def on_confirmation(confirmed: bool):
                if confirmed:
                    # Show progress modal and execute installations
                    try:
                        self.app.push_screen(
                            InstallationProgressModal(actions, self.config_manager)
                        )
                        # After installation completes, refresh the package manager list
                        self.set_timer(0.5, lambda: self._refresh_package_managers())
                    except Exception as e:
                        self._show_error(f"Error starting installation: {str(e)}")
            
            # Show confirmation modal
            try:
                self.app.push_screen(
                    InstallationConfirmationModal(actions, on_confirmation, self.config_manager)
                )
            except Exception as e:
                self._show_error(f"Error showing confirmation: {str(e)}")
        
        # Show package manager installation modal
        try:
            self.app.push_screen(
                PackageManagerInstallModal(on_install_actions_selected, self.config_manager)
            )
        except Exception as e:
            self._show_error(f"Error showing installation modal: {str(e)}")
    
    def _refresh_package_managers(self) -> None:
        """Refresh the package manager list after installation/uninstallation."""
        # Re-detect package managers
        self.detector = PackageManagerDetector(self.config_manager)
        self.package_managers = self.detector.package_managers
        self.primary_pm = self.detector.get_primary_package_manager()
        
        # Update displays
        self._display_package_managers()
        if self.selected_pm:
            self._display_source_options(self.selected_pm)
    
    def _scroll_to_current(self) -> None:
        """Scroll the left panel to ensure current selection is visible."""
        try:
            # Try different approaches to scroll to current item
            scroll_container = self.query_one("#pm-list", VerticalScroll)
            
            if self.left_focused_item == 0:
                # Scroll to top for "Available Package Managers"
                try:
                    current_item = self.query_one("#pm-available", Static)
                    # Try using scroll_to method on the container
                    y_offset = current_item.region.y if hasattr(current_item, 'region') else 0
                    scroll_container.scroll_to(y=y_offset, animate=False)
                except Exception as e:
                    # Fallback: try scroll_visible on the item itself
                    try:
                        current_item = self.query_one("#pm-available", Static)
                        current_item.scroll_visible(animate=False)
                    except Exception:
                        pass
                        
            elif self.package_managers and self.left_focused_item > 0:
                # Scroll to specific package manager item
                pm_index = self.left_focused_item - 1
                if pm_index < len(self.package_managers):
                    try:
                        current_item = self.query_one(f"#pm-{pm_index}", Static)
                        # Try using scroll_to method on the container
                        y_offset = current_item.region.y if hasattr(current_item, 'region') else 0
                        scroll_container.scroll_to(y=y_offset, animate=False)
                    except Exception as e:
                        # Fallback: try scroll_visible on the item itself
                        try:
                            current_item = self.query_one(f"#pm-{pm_index}", Static)
                            current_item.scroll_visible(animate=False)
                        except Exception:
                            pass
                            
        except Exception:
            # Final fallback: do nothing silently
            pass