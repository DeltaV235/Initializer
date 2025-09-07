"""Source Selection Modal for Package Manager."""

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.screen import ModalScreen
from textual.widgets import Button, Static, Rule, Label, Input, RadioSet, RadioButton
from typing import Callable, Optional

from ...modules.package_manager import PackageManagerDetector


class SourceSelectionModal(ModalScreen):
    """Modal screen for selecting package manager source."""
    
    BINDINGS = [
        ("escape", "dismiss", "Cancel"),
        ("enter", "apply_selection", "Apply"),
    ]
    
    def __init__(self, package_manager, callback: Callable[[str], None]):
        super().__init__()
        self.package_manager = package_manager
        self.callback = callback
        self.detector = PackageManagerDetector()
        self.available_mirrors = self.detector.get_available_mirrors(package_manager.name)
        
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
                
                # Available mirrors
                if self.available_mirrors:
                    yield Label("Available Mirrors:", classes="info-key")
                    
                    radio_set = RadioSet(id="mirror-selection")
                    for mirror_name, mirror_url in self.available_mirrors.items():
                        # Format label
                        display_url = mirror_url
                        if len(display_url) > 60:
                            display_url = display_url[:57] + "..."
                        label = f"{mirror_name.title()}: {display_url}"
                        radio_button = RadioButton(label, value=mirror_url, id=f"mirror-{mirror_name}")
                        radio_set.mount(radio_button)
                    
                    yield radio_set
                    
                    yield Rule()
                
                # Custom source input
                yield Label("Custom Source:", classes="info-key")
                yield Input(placeholder="Enter custom mirror URL", id="custom-source")
            
            # Action buttons
            with Horizontal(id="modal-actions"):
                yield Button("Apply", id="apply", variant="primary")
                yield Button("Cancel", id="cancel", variant="default")
    
    @on(Button.Pressed, "#apply")
    def apply_selection(self) -> None:
        """Apply the selected mirror source."""
        # Check custom input first
        custom_input = self.query_one("#custom-source", Input)
        custom_source = custom_input.value.strip()
        
        selected_source = None
        
        if custom_source:
            # Use custom source if provided
            selected_source = custom_source
        else:
            # Check radio button selection
            try:
                radio_set = self.query_one("#mirror-selection", RadioSet)
                selected_source = radio_set.value
            except:
                pass
        
        if selected_source:
            self.callback(selected_source)
            self.dismiss()
        else:
            # Show error - no selection made
            self._show_error("Please select a mirror or enter a custom source")
    
    @on(Button.Pressed, "#cancel")
    def cancel_selection(self) -> None:
        """Cancel source selection."""
        self.dismiss()
    
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
    
    def action_apply_selection(self) -> None:
        """Apply selection with Enter key."""
        self.apply_selection()