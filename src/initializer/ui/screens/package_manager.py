"""Package Manager management screen."""

from textual import on, work
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.screen import Screen
from textual.widgets import Button, Static, Rule, Label, Input, RadioSet, RadioButton
from textual.reactive import reactive

from ...config_manager import ConfigManager
from ...modules.package_manager import PackageManagerDetector
from .source_selection_modal import SourceSelectionModal
from .mirror_confirmation_modal import MirrorConfirmationModal


class PackageManagerScreen(Screen):
    """Screen for Package Manager detection and source management."""
    
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
        self.detector = PackageManagerDetector()
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
                    yield Label("Detected Package Managers", classes="panel-title")
                    with ScrollableContainer(id="pm-list"):
                        yield Static("Detecting package managers...", id="pm-loading")
                    
                # Right panel - Source management
                with Vertical(id="pm-right-panel", classes="panel"):
                    yield Label("Mirror Source Management", classes="panel-title")
                    with ScrollableContainer(id="source-container"):
                        yield Static("Select a package manager to view sources", id="source-placeholder")
            
            # Bottom action buttons
            with Horizontal(id="pm-actions"):
                yield Button("🔙 Back", id="back", variant="default")
    
    def on_mount(self) -> None:
        """Initialize the screen."""
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
            pm_list = self.query_one("#pm-list", ScrollableContainer)
            
            # Clear loading message
            for child in list(pm_list.children):
                child.remove()
            
            if not self.package_managers:
                pm_list.mount(Static("No package managers detected", classes="info-message"))
                return
            
            # Display each package manager with arrow indicators
            for i, pm in enumerate(self.package_managers):
                # Create arrow indicator for CLI-style navigation
                arrow = "▶ " if (self.focus_panel == "left" and self.left_focused_item == i) else "  "
                
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
                
                pm_list.mount(Static(pm_info, id=f"pm-{i}", classes="pm-item"))
                
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
            source_container = self.query_one("#source-container", ScrollableContainer)
            
            # Clear existing content
            for child in list(source_container.children):
                child.remove()
            
            if not pm:
                source_container.mount(Static("Select a package manager to configure", classes="info-message"))
                return
            
            # Show current package manager info
            source_container.mount(Label(f"Package Manager: {pm.name.upper()}", classes="section-title"))
            source_container.mount(Rule())
            
            # Show current source
            source_container.mount(Label("Current Source:", classes="info-key"))
            if pm.current_source:
                source_container.mount(Static(pm.current_source, classes="current-source-display"))
            else:
                source_container.mount(Static("Not configured", classes="current-source-none"))
            
            source_container.mount(Rule())
            source_container.mount(Static("ENTER=Change Source", classes="help-text"))
                
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
                    MirrorConfirmationModal(pm, selected_source, on_confirmation_result)
                )
            except Exception as e:
                self._show_message(f"Error showing confirmation: {str(e)}", error=True)
        
        # Show source selection modal
        self.app.push_screen(
            SourceSelectionModal(pm, on_source_selected)
        )
    
    @on(Button.Pressed)
    def handle_button_press(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        button_id = event.button.id
        
        if button_id == "back":
            self.app.pop_screen()
    
    def action_select_current(self) -> None:
        """Handle Enter key - select current item."""
        if self.focus_panel == "left" and self.package_managers:
            # Select package manager and show source selection modal
            if 0 <= self.left_focused_item < len(self.package_managers):
                pm = self.package_managers[self.left_focused_item]
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
        if self.focus_panel == "left" and self.package_managers:
            if self.left_focused_item < len(self.package_managers) - 1:
                self.left_focused_item += 1
                # Auto-select and display details
                pm = self.package_managers[self.left_focused_item]
                self.selected_pm = pm
                self._display_source_options(pm)
            self._display_package_managers()
    
    def action_nav_up(self) -> None:
        """Navigate up within current panel."""
        if self.focus_panel == "left" and self.package_managers:
            if self.left_focused_item > 0:
                self.left_focused_item -= 1
                # Auto-select and display details
                pm = self.package_managers[self.left_focused_item]
                self.selected_pm = pm
                self._display_source_options(pm)
            self._display_package_managers()