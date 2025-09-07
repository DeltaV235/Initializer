"""Source Selection Modal for Package Manager."""

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.screen import ModalScreen
from textual.widgets import Button, Static, Rule, Label, Input
from textual.events import Key
from typing import Callable, Optional, List, Dict

from ...modules.package_manager import PackageManagerDetector


class SourceSelectionModal(ModalScreen):
    """Modal screen for selecting package manager source."""
    
    BINDINGS = [
        ("escape", "dismiss", "Cancel"),
    ]
    
    def __init__(self, package_manager, callback: Callable[[str], None]):
        super().__init__()
        self.package_manager = package_manager
        self.callback = callback
        self.detector = PackageManagerDetector()
        self.available_mirrors = self.detector.get_available_mirrors(package_manager.name)
        
        # State management
        self.mirror_list = []  # List of (name, url) tuples
        self.selected_index = 0  # Currently selected mirror index
        
        # Prepare mirror list
        if self.available_mirrors:
            for name, url in self.available_mirrors.items():
                self.mirror_list.append((name, url))
    
    def on_mount(self) -> None:
        """Initialize the screen."""
        # Use call_after_refresh to ensure components are rendered
        self.call_after_refresh(self._update_mirror_display)
        
        # Test: Show that the modal was created
        self._show_error("Modal created - use j/k to navigate, Enter to select")
        
        # Try to ensure focus with higher priority
        self.focus()
        
        # Set higher priority for this screen
        if hasattr(self.app, '_screen_stack'):
            # Ensure this modal is at the top of the screen stack
            pass
    
    def can_focus(self) -> bool:
        """Return True to allow this modal to receive focus."""
        return True
    
    @property
    def is_modal(self) -> bool:
        """Mark this as a modal screen."""
        return True
    
    @on(Key)
    def handle_key_event(self, event: Key) -> None:
        """Handle key events using @on decorator."""
        self._show_error(f"@ON KEY: {event.key} - Detected")
        
        if event.key == "enter":
            self._show_error("@ON ENTER - Calling action")
            self.action_select_current()
            event.prevent_default()
            event.stop()
        elif event.key == "j":
            self._show_error("@ON J - Moving down")
            self.action_nav_down()
            event.prevent_default()
            event.stop()
        elif event.key == "k": 
            self._show_error("@ON K - Moving up")
            self.action_nav_up()
            event.prevent_default()
            event.stop()
        elif event.key == "escape":
            self._show_error("@ON ESC - Dismissing")
            self.dismiss()
            event.prevent_default()
            event.stop()
        
    def compose(self) -> ComposeResult:
        """Compose the modal interface."""
        with Container(id="modal-container"):
            yield Static(f"Select Mirror Source for {self.package_manager.name.upper()}", id="modal-title")
            yield Rule()
            
            with ScrollableContainer(id="modal-content"):
                # Current source info
                yield Label("Current Source:", classes="info-key")
                current = self.package_manager.current_source or "Not configured"
                if len(current) > 80:
                    current = current[:77] + "..."
                yield Static(current, classes="current-source-display")
                
                yield Rule()
                
                # Available mirrors (displayed as text with arrows)
                if self.mirror_list:
                    yield Label("Available Mirrors:", classes="info-key")
                    with Vertical(id="mirror-list"):
                        # Pre-populate mirror items to avoid mounting issues
                        for i, (name, url) in enumerate(self.mirror_list):
                            display_url = url
                            if len(display_url) > 60:
                                display_url = display_url[:57] + "..."
                            
                            # Start with first item selected
                            arrow = "▶ " if i == 0 else "  "
                            text = f"{arrow}{name.title()}: {display_url}"
                            yield Static(text, id=f"mirror-item-{i}", classes="mirror-item")
            
            # Fixed bottom shortcuts - single line format like main menu
            with Container(id="modal-actions"):
                yield Static("Keyboard Shortcuts: j/k=Navigate | Enter=Select | Esc=Cancel", classes="help-text")
    
    def _update_mirror_display(self) -> None:
        """Update mirror list display with arrow indicators."""
        try:
            if not self.mirror_list:
                return
            
            # Update existing mirror items
            for i, (name, url) in enumerate(self.mirror_list):
                mirror_item = self.query_one(f"#mirror-item-{i}", Static)
                
                # Format display URL
                display_url = url
                if len(display_url) > 60:
                    display_url = display_url[:57] + "..."
                
                # Create arrow indicator
                arrow = "▶ " if i == self.selected_index else "  "
                text = f"{arrow}{name.title()}: {display_url}"
                
                mirror_item.update(text)
                
        except Exception as e:
            # If specific item not found, try to recreate all items
            try:
                mirror_list_container = self.query_one("#mirror-list", Vertical)
                
                # Clear existing items
                for child in list(mirror_list_container.children):
                    child.remove()
                
                # Add mirror items
                for i, (name, url) in enumerate(self.mirror_list):
                    # Format display URL
                    display_url = url
                    if len(display_url) > 60:
                        display_url = display_url[:57] + "..."
                    
                    # Create arrow indicator
                    arrow = "▶ " if i == self.selected_index else "  "
                    text = f"{arrow}{name.title()}: {display_url}"
                    
                    mirror_item = Static(text, id=f"mirror-item-{i}", classes="mirror-item")
                    mirror_list_container.mount(mirror_item)
            except Exception:
                pass
    
    def _get_selected_source(self) -> Optional[str]:
        """Get the currently selected source URL."""
        # Check selected mirror
        if self.mirror_list and 0 <= self.selected_index < len(self.mirror_list):
            return self.mirror_list[self.selected_index][1]
        
        return None
    
    def action_nav_down(self) -> None:
        """Navigate down in the current focus area."""
        if self.mirror_list and self.selected_index < len(self.mirror_list) - 1:
            old_index = self.selected_index
            self.selected_index += 1
            self._show_error(f"Nav down: {old_index} -> {self.selected_index}")
            self._update_mirror_display()
        else:
            self._show_error(f"Nav down blocked: index={self.selected_index}, max={len(self.mirror_list)-1 if self.mirror_list else 0}")
    
    def action_nav_up(self) -> None:
        """Navigate up in the current focus area."""
        if self.mirror_list and self.selected_index > 0:
            old_index = self.selected_index
            self.selected_index -= 1
            self._show_error(f"Nav up: {old_index} -> {self.selected_index}")
            self._update_mirror_display()
        else:
            self._show_error(f"Nav up blocked: index={self.selected_index}")
    
    def action_select_current(self) -> None:
        """Select current item."""
        # VERY OBVIOUS TEST MESSAGE
        self._show_error("=== ACTION_SELECT_CURRENT CALLED ===")
        
        selected_source = self._get_selected_source()
        current = self.package_manager.current_source
        
        # Debug: Show the comparison
        self._show_error(f"Selected: {selected_source}")
        self._show_error(f"Current: {current}")
        
        if selected_source:
            # Test: Show that we're calling callback
            self._show_error(f"Calling callback with: {selected_source[:50]}...")
            self.callback(selected_source)
            self.dismiss()
        else:
            self._show_error("No mirror selected")
    
    def _show_error(self, message: str) -> None:
        """Show error message in the modal title."""
        title_widget = self.query_one("#modal-title", Static)
        original_title = title_widget.renderable
        title_widget.update(f"❌ {message}")
        # Reset after 2 seconds
        self.set_timer(2.0, lambda: title_widget.update(original_title))
    
    def action_dismiss(self) -> None:
        """Dismiss the modal."""
        self.dismiss()