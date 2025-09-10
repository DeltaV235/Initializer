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
    
    # CSS styles for the modal
    CSS = """
    SourceSelectionModal {
        align: center middle;
    }
    
    #modal-container {
        width: 80%;
        height: 24;
        max-height: 24;
        background: $surface;
        border: solid $primary;
        padding: 1;
        layout: vertical;
    }
    
    #modal-content {
        height: 1fr;
        overflow-y: auto;
        padding: 0 1;
    }
    
    .info-key {
        margin: 1 0 0 0;
        color: $text;
    }
    
    .current-mirror-item {
        height: auto;
        min-height: 1;
        color: $text-muted;
        text-style: dim;
        background: transparent;
    }
    
    .current-mirror-item:hover {
        background: transparent;
    }
    
    .current-source-display {
        height: auto;
        min-height: 1;
        color: $text;
        background: $surface;
        margin: 0 0 0 1;
    }
    
    #mirror-list {
        height: auto;
        min-height: 1;
        margin: 0 0 1 0;
    }
    
    .mirror-item {
        height: auto;
        min-height: 1;
    }
    
    .mirror-item:hover {
        background: $primary;
    }
    
    .help-text {
        text-align: center;
        color: $text;
        height: auto;
        min-height: 1;
        margin: 0;
        padding: 0;
        background: $surface;
    }
    
    .bottom-spacer {
        height: 1;
        background: transparent;
    }
    
    .section-separator {
        height: 1;
        background: transparent;
    }
    """
    
    def __init__(self, package_manager, callback: Callable[[str], None]):
        super().__init__()
        self.package_manager = package_manager
        self.callback = callback
        self.detector = PackageManagerDetector()
        self.available_mirrors = self.detector.get_available_mirrors(package_manager.name)
        
        # State management
        self.mirror_list = []  # List of (name, url, is_current) tuples
        self.selected_index = 0  # Currently selected mirror index (only selectable mirrors)
        
        # Prepare mirror list
        current_source_url = (self.package_manager.current_source or "").strip().rstrip('/')
        if self.available_mirrors:
            for name, url in self.available_mirrors.items():
                is_current = url.strip().rstrip('/') == current_source_url
                self.mirror_list.append((name, url, is_current))
            
            # Set initial selected_index to first non-current item
            self.selected_index = 0
            for i, (_, _, is_current) in enumerate(self.mirror_list):
                if not is_current:
                    self.selected_index = i
                    break
            
            # If no non-current item found, default to first item
            if self.selected_index >= len(self.mirror_list):
                self.selected_index = 0
    
    def on_mount(self) -> None:
        """Initialize the screen."""
        try:
            # Use call_after_refresh to ensure components are rendered
            self.call_after_refresh(self._update_mirror_display)
            
            # Set initial title display
            self.call_after_refresh(lambda: self._show_error(""))
            
            # Try to ensure focus with higher priority
            self.focus()
            
            # Set higher priority for this screen
            if hasattr(self.app, '_screen_stack'):
                # Ensure this modal is at the top of the screen stack
                pass
        except Exception as e:
            # Prevent any mounting errors from showing confusing messages
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
        if event.key == "enter":
            self.action_select_current()
            event.prevent_default()
            event.stop()
        elif event.key == "j":
            self.action_nav_down()
            event.prevent_default()
            event.stop()
        elif event.key == "k": 
            self.action_nav_up()
            event.prevent_default()
            event.stop()
        elif event.key == "escape":
            self.dismiss()
            event.prevent_default()
            event.stop()
        
    def compose(self) -> ComposeResult:
        """Compose the modal interface."""
        with Container(id="modal-container"):
            yield Static(f"Select Mirror Source for {self.package_manager.name.upper()}", id="modal-title")
            yield Rule()
            
            with ScrollableContainer(id="modal-content"):
                # Show current source at the top in separate section
                if self.mirror_list:
                    current_sources = [(i, name, url) for i, (name, url, is_current) in enumerate(self.mirror_list) if is_current]
                    selectable_sources = [(i, name, url) for i, (name, url, is_current) in enumerate(self.mirror_list) if not is_current]
                    
                    # Current Source Section (at the top)
                    if current_sources:
                        yield Label("Current Source:", classes="info-key")
                        for i, name, url in current_sources:
                            display_url = url
                            if len(display_url) > 60:
                                display_url = display_url[:57] + "..."
                            text = f"  {name.title()}: {display_url}"
                            yield Static(text, id=f"current-source-{i}", classes="current-source-display")
                        
                        # Add separator between sections
                        yield Static("", classes="section-separator")
                    
                    # Available Sources Section
                    yield Label("Available Sources:", classes="info-key")
                    with Vertical(id="mirror-list"):
                        # Display selectable sources with arrows
                        for i, name, url in selectable_sources:
                            display_url = url
                            if len(display_url) > 60:
                                display_url = display_url[:57] + "..."
                            is_selected = (i == self.selected_index)
                            arrow = "▶ " if is_selected else "  "
                            text = f"{arrow}{name.title()}: {display_url}"
                            yield Static(text, id=f"mirror-item-{i}", classes="mirror-item")
                        
                        # Add bottom padding to ensure scrollbar calculation
                        yield Static("", classes="bottom-spacer")
            
            # Bottom shortcuts area - now as part of the main container
            yield Rule()
            yield Label("J/K=Up/Down | ENTER=Select | ESC=Cancel", classes="help-text")
    
    def _update_mirror_display(self) -> None:
        """Update mirror list display with arrow indicators."""
        try:
            if not self.mirror_list:
                return
            
            # Update only selectable mirror items (current source is in separate section)
            for i, (name, url, is_current) in enumerate(self.mirror_list):
                if not is_current:  # Only update selectable items
                    mirror_item = self.query_one(f"#mirror-item-{i}", Static)
                    
                    # Format display URL
                    display_url = url
                    if len(display_url) > 60:
                        display_url = display_url[:57] + "..."
                    
                    # Selectable mirror - show arrow only for selected item
                    arrow = "▶ " if i == self.selected_index else "  "
                    text = f"{arrow}{name.title()}: {display_url}"
                    
                    mirror_item.update(text)
                
        except Exception as e:
            # If specific item not found, try to recreate selectable items only
            try:
                mirror_list_container = self.query_one("#mirror-list", Vertical)
                
                # Clear existing selectable items
                for child in list(mirror_list_container.children):
                    child.remove()
                
                # Recreate selectable sources only
                selectable_sources = [(i, name, url) for i, (name, url, is_current) in enumerate(self.mirror_list) if not is_current]
                
                for i, name, url in selectable_sources:
                    display_url = url
                    if len(display_url) > 60:
                        display_url = display_url[:57] + "..."
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
            name, url, is_current = self.mirror_list[self.selected_index]
            # Don't allow selection of current source
            if not is_current:
                return url
        
        return None
    
    def action_nav_down(self) -> None:
        """Navigate down in the current focus area, skipping current source."""
        if not self.mirror_list:
            return
            
        # Find next selectable item
        for next_index in range(self.selected_index + 1, len(self.mirror_list)):
            _, _, is_current = self.mirror_list[next_index]
            if not is_current:
                self.selected_index = next_index
                # Force immediate scroll and display update
                self._scroll_to_current()  
                self._update_mirror_display()
                self._show_error("")
                break
    
    def action_nav_up(self) -> None:
        """Navigate up in the current focus area, skipping current source."""
        if not self.mirror_list:
            return
            
        # Find previous selectable item
        for prev_index in range(self.selected_index - 1, -1, -1):
            _, _, is_current = self.mirror_list[prev_index]
            if not is_current:
                self.selected_index = prev_index
                # Force immediate scroll and display update
                self._scroll_to_current()  
                self._update_mirror_display()
                self._show_error("")
                break
    
    def action_select_current(self) -> None:
        """Select current item."""
        selected_source = self._get_selected_source()
        
        if selected_source:
            self.callback(selected_source)
            self.dismiss()
        else:
            self._show_error("No mirror selected")
    
    def _scroll_to_current(self) -> None:
        """Scroll the modal content to ensure current selection is visible with smooth synchronous behavior."""
        try:
            # Get the scrollable container
            scrollable_container = self.query_one("#modal-content", ScrollableContainer)
            
            # Try Textual's built-in scroll_to_widget method first
            current_item = self.query_one(f"#mirror-item-{self.selected_index}", Static)
            if hasattr(scrollable_container, 'scroll_to_widget'):
                # Use smooth scrolling with center positioning
                scrollable_container.scroll_to_widget(current_item, animate=True, speed=60, center=True)
            else:
                # Enhanced manual scrolling for immediate response
                header_height = 2  # Only "Available Mirrors:" label now
                visible_height = 15  # More visible height with expanded modal (18 total - 3 for margins)
                
                # Calculate current item position
                current_item_position = header_height + self.selected_index
                current_scroll = scrollable_container.scroll_y
                
                # Calculate optimal scroll position to keep item in view
                # Target: keep selected item roughly in the middle third of visible area
                target_position_from_top = 3  # 3 lines from top of visible area
                
                # Calculate new scroll position
                new_scroll_position = max(0, current_item_position - header_height - target_position_from_top)
                
                # Apply smooth scrolling if position changes significantly
                scroll_diff = abs(new_scroll_position - current_scroll)
                if scroll_diff > 0:
                    # Immediate scroll for synchronous feel
                    scrollable_container.scroll_y = new_scroll_position
                    
        except Exception:
            # Fallback: basic scrolling
            try:
                scrollable_container = self.query_one("#modal-content", ScrollableContainer)
                # Simple position calculation based on selected_index
                target_scroll = max(0, self.selected_index - 3)
                scrollable_container.scroll_y = target_scroll
            except:
                pass

    def _show_error(self, message: str) -> None:
        """Show error message in the modal title."""
        try:
            title_widget = self.query_one("#modal-title", Static)
            # Store original title if not already stored
            if not hasattr(self, '_original_title'):
                self._original_title = f"Select Mirror Source for {self.package_manager.name.upper()}"
            
            # Show current selection info along with any message
            if (hasattr(self, 'selected_index') and self.mirror_list and 
                0 <= self.selected_index < len(self.mirror_list)):
                # Count only selectable (non-current) items
                selectable_count = sum(1 for _, _, is_current in self.mirror_list if not is_current)
                if selectable_count > 0:
                    # Find position among selectable items
                    selectable_position = 1
                    for i in range(self.selected_index):
                        if i < len(self.mirror_list):
                            _, _, is_current = self.mirror_list[i]
                            if not is_current:
                                selectable_position += 1
                    
                    current_name = self.mirror_list[self.selected_index][0].title()
                    display_message = f"[{selectable_position}/{selectable_count}] {current_name}"
                    if message:
                        display_message += f" | {message}"
                else:
                    display_message = message or self._original_title
            else:
                display_message = message or self._original_title
                
            title_widget.update(display_message)
            
            # Only reset after delay if there was a message
            if message:
                self.set_timer(2.0, lambda: self._reset_title())
                
        except Exception as e:
            # Fallback to simple title
            try:
                title_widget = self.query_one("#modal-title", Static)
                title_widget.update(f"Select Mirror Source for {self.package_manager.name.upper()}")
            except:
                pass

    def _reset_title(self) -> None:
        """Reset title to show current selection."""
        self._show_error("")  # This will show just the selection info
    
    def action_dismiss(self) -> None:
        """Dismiss the modal."""
        self.dismiss()