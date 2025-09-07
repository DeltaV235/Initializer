"""Package Manager management screen."""

from textual import on, work
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.screen import Screen
from textual.widgets import Button, Static, Rule, Label, Input, RadioSet, RadioButton
from textual.reactive import reactive

from ...config_manager import ConfigManager
from ...modules.package_manager import PackageManagerDetector


class PackageManagerScreen(Screen):
    """Screen for Package Manager detection and source management."""
    
    BINDINGS = [
        ("escape", "back", "Back"),
        ("q", "back", "Back"),
        ("enter", "select_item", "Select"),
        ("tab", "switch_focus", "Switch Focus"),
        # Vim-like navigation
        ("h", "nav_left", "Left"),
        ("j", "nav_down", "Down"),
        ("k", "nav_up", "Up"),
        ("l", "nav_right", "Right"),
    ]
    
    # Reactive properties for state management
    selected_pm = reactive(None)
    current_source = reactive("")
    loading = reactive(True)
    
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
            
            # Display each package manager
            for pm in self.package_managers:
                # Create a container for each PM entry
                pm_container = Vertical(id=f"pm-{pm.name}", classes="pm-item")
                
                # Package manager name and status
                pm_info = f"📦 {pm.name.upper()}"
                if pm == self.primary_pm:
                    pm_info += " (Primary)"
                
                pm_container.mount(Label(pm_info, classes="pm-name"))
                
                # Show current source if available
                if pm.current_source:
                    source_text = self._truncate_source(pm.current_source)
                    pm_container.mount(Label(f"  Source: {source_text}", classes="pm-source"))
                else:
                    pm_container.mount(Label("  Source: Not configured", classes="pm-source-none"))
                
                # Make it clickable
                pm_container.mount(Button(f"Configure {pm.name}", id=f"btn-{pm.name}", classes="pm-button"))
                
                pm_list.mount(pm_container)
                pm_list.mount(Rule(line_style="dotted"))
                
        except Exception as e:
            self._show_error(f"Error displaying package managers: {str(e)}")
    
    def _truncate_source(self, source: str, max_length: int = 40) -> str:
        """Truncate long source URLs for display."""
        if len(source) <= max_length:
            return source
        return source[:max_length-3] + "..."
    
    def _display_source_options(self, pm) -> None:
        """Display mirror source options for selected package manager."""
        try:
            source_container = self.query_one("#source-container", ScrollableContainer)
            
            # Clear existing content
            for child in list(source_container.children):
                child.remove()
            
            if not pm:
                source_container.mount(Static("Select a package manager to configure", classes="info-message"))
                return
            
            # Show current package manager info
            source_container.mount(Label(f"Configuring: {pm.name.upper()}", classes="section-title"))
            source_container.mount(Rule())
            
            # Show current source
            source_container.mount(Label("Current Source:", classes="info-key"))
            if pm.current_source:
                source_container.mount(Static(pm.current_source, classes="current-source"))
            else:
                source_container.mount(Static("Not configured", classes="current-source-none"))
            
            source_container.mount(Rule())
            
            # Get available mirrors
            mirrors = self.detector.get_available_mirrors(pm.name)
            
            if mirrors:
                source_container.mount(Label("Available Mirrors:", classes="info-key"))
                
                # Create radio buttons for mirror selection
                radio_set = RadioSet(id="mirror-selection")
                
                for mirror_name, mirror_url in mirrors.items():
                    # Format the label
                    label = f"{mirror_name.title()}: {self._truncate_source(mirror_url, 35)}"
                    radio_set.mount(RadioButton(label, value=mirror_url, id=f"mirror-{mirror_name}"))
                
                source_container.mount(radio_set)
                
                # Custom source input
                source_container.mount(Rule())
                source_container.mount(Label("Custom Source:", classes="info-key"))
                source_container.mount(Input(placeholder="Enter custom mirror URL", id="custom-source"))
                
                # Apply button
                source_container.mount(Rule())
                with source_container:
                    with Horizontal(classes="action-buttons"):
                        yield Button("Apply Mirror", id="apply-mirror", variant="primary")
                        yield Button("Test Connection", id="test-mirror", variant="default")
            else:
                source_container.mount(Static(f"No predefined mirrors available for {pm.name}", classes="info-message"))
                
                # Still allow custom source
                source_container.mount(Rule())
                source_container.mount(Label("Custom Source:", classes="info-key"))
                source_container.mount(Input(placeholder="Enter custom mirror URL", id="custom-source"))
                
                source_container.mount(Rule())
                with source_container:
                    with Horizontal(classes="action-buttons"):
                        yield Button("Apply Custom Source", id="apply-custom", variant="primary")
                
        except Exception as e:
            self._show_error(f"Error displaying source options: {str(e)}")
    
    @on(Button.Pressed)
    def handle_button_press(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        button_id = event.button.id
        
        if button_id == "back":
            self.app.pop_screen()
        elif button_id and button_id.startswith("btn-"):
            # Package manager selection button
            pm_name = button_id.replace("btn-", "")
            for pm in self.package_managers:
                if pm.name == pm_name:
                    self.selected_pm = pm
                    self._display_source_options(pm)
                    break
        elif button_id == "apply-mirror":
            self._apply_mirror_change()
        elif button_id == "apply-custom":
            self._apply_custom_source()
        elif button_id == "test-mirror":
            self._test_mirror_connection()
    
    def _apply_mirror_change(self) -> None:
        """Apply the selected mirror change."""
        try:
            # Get selected mirror from radio buttons
            radio_set = self.query_one("#mirror-selection", RadioSet)
            selected_mirror = radio_set.value
            
            # Check for custom source
            custom_input = self.query_one("#custom-source", Input)
            custom_source = custom_input.value.strip()
            
            # Prefer custom source if provided
            mirror_url = custom_source if custom_source else selected_mirror
            
            if not mirror_url:
                self._show_message("Please select a mirror or enter a custom source", error=True)
                return
            
            if not self.selected_pm:
                self._show_message("No package manager selected", error=True)
                return
            
            # Apply the mirror change
            self._show_message(f"Applying mirror: {mirror_url}...")
            success, message = self.detector.change_mirror(self.selected_pm.name, mirror_url)
            
            if success:
                self._show_message(f"✅ {message}")
                # Update the current source
                self.selected_pm.current_source = mirror_url
                # Refresh the display
                self._display_package_managers()
                self._display_source_options(self.selected_pm)
            else:
                self._show_message(f"❌ {message}", error=True)
                
        except Exception as e:
            self._show_message(f"Error applying mirror: {str(e)}", error=True)
    
    def _apply_custom_source(self) -> None:
        """Apply a custom source URL."""
        try:
            custom_input = self.query_one("#custom-source", Input)
            custom_source = custom_input.value.strip()
            
            if not custom_source:
                self._show_message("Please enter a custom source URL", error=True)
                return
            
            if not self.selected_pm:
                self._show_message("No package manager selected", error=True)
                return
            
            # Apply the custom source
            self._show_message(f"Applying custom source: {custom_source}...")
            success, message = self.detector.change_mirror(self.selected_pm.name, custom_source)
            
            if success:
                self._show_message(f"✅ {message}")
                # Update the current source
                self.selected_pm.current_source = custom_source
                # Refresh the display
                self._display_package_managers()
                self._display_source_options(self.selected_pm)
            else:
                self._show_message(f"❌ {message}", error=True)
                
        except Exception as e:
            self._show_message(f"Error applying custom source: {str(e)}", error=True)
    
    def _test_mirror_connection(self) -> None:
        """Test connection to the selected mirror."""
        try:
            # Get selected mirror
            radio_set = self.query_one("#mirror-selection", RadioSet)
            selected_mirror = radio_set.value
            
            # Check for custom source
            custom_input = self.query_one("#custom-source", Input)
            custom_source = custom_input.value.strip()
            
            # Prefer custom source if provided
            mirror_url = custom_source if custom_source else selected_mirror
            
            if not mirror_url:
                self._show_message("Please select a mirror or enter a custom source to test", error=True)
                return
            
            # Test the connection
            self._show_message(f"Testing connection to: {mirror_url}...")
            
            # Simple connectivity test
            import urllib.request
            import urllib.error
            
            try:
                response = urllib.request.urlopen(mirror_url, timeout=5)
                if response.status == 200:
                    self._show_message(f"✅ Connection successful to {mirror_url}")
                else:
                    self._show_message(f"⚠️ Unexpected response from {mirror_url}: {response.status}")
            except urllib.error.URLError as e:
                self._show_message(f"❌ Failed to connect: {str(e)}", error=True)
            except Exception as e:
                self._show_message(f"❌ Connection test failed: {str(e)}", error=True)
                
        except Exception as e:
            self._show_message(f"Error testing connection: {str(e)}", error=True)
    
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
        self.focus_next()
    
    def action_nav_left(self) -> None:
        """Navigate left."""
        # Focus left panel
        try:
            left_panel = self.query_one("#pm-left-panel")
            left_panel.focus()
        except:
            self.focus_previous()
    
    def action_nav_right(self) -> None:
        """Navigate right."""
        # Focus right panel
        try:
            right_panel = self.query_one("#pm-right-panel")
            right_panel.focus()
        except:
            self.focus_next()
    
    def action_nav_down(self) -> None:
        """Navigate down."""
        self.focus_next()
    
    def action_nav_up(self) -> None:
        """Navigate up."""
        self.focus_previous()
    
    def action_select_item(self) -> None:
        """Select current focused item."""
        focused = self.focused
        if focused and hasattr(focused, 'press'):
            focused.press()