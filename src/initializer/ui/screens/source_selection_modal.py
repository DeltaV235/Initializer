"""Source Selection Modal for Package Manager."""

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer, VerticalScroll
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

    #current-source-container {
        height: auto;
        min-height: 1;
        padding: 0 1;
        margin: 0 0 1 0;
        background: $surface;
    }

    #available-sources-header {
        height: auto;
        min-height: 1;
        padding: 0 1;
        background: $surface;
    }

    #mirror-list {
        height: auto;
        min-height: 1;
        margin: 0 0 1 0;
    }

    .section-divider {
        height: 1;
        color: #7dd3fc;
        margin: 0;
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

    .mirror-item {
        height: auto;
        min-height: 1;
    }
    
    .mirror-item:hover {
        background: $primary;
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

    #help-box {
        dock: bottom;
        width: 100%;
        height: 3;
        border: round white;
        background: $surface;
        padding: 0 1;
        margin: 0;
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
    
    def __init__(self, package_manager, callback: Callable[[str], None], config_manager=None):
        super().__init__()
        self.package_manager = package_manager
        self.callback = callback
        self.detector = PackageManagerDetector(config_manager)
        self.available_mirrors = self.detector.get_available_mirrors(package_manager.name)

        # State management
        self.mirror_list = []  # List of (name, url, is_current) tuples
        self.selected_index = 0  # Currently selected mirror index (only selectable mirrors)

        # Prepare mirror list
        current_source_url = (self.package_manager.current_source or "").strip().rstrip('/')

        if self.available_mirrors:
            for name, url in self.available_mirrors.items():
                # More robust URL comparison
                is_current = self._urls_match(url, current_source_url)
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

    def _normalize_url(self, url: str) -> str:
        """Normalize URL for comparison."""
        if not url:
            return ""
        # Remove protocol, trailing slashes, and standardize
        normalized = url.strip().rstrip('/')
        # Remove common protocols
        for protocol in ['https://', 'http://', 'ftp://']:
            if normalized.startswith(protocol):
                normalized = normalized[len(protocol):]
                break
        return normalized.lower()

    def _urls_match(self, url1: str, url2: str) -> bool:
        """Check if two URLs represent the same mirror source."""
        if not url1 or not url2:
            return False

        norm1 = self._normalize_url(url1)
        norm2 = self._normalize_url(url2)

        # Direct match
        if norm1 == norm2:
            return True

        # Check if one is contained in the other (handle subpaths)
        if norm1 and norm2:
            if norm1.startswith(norm2) or norm2.startswith(norm1):
                return True

        return False

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
        with Container(classes="modal-container-xs"):
            yield Static(f"Select Mirror Source for {self.package_manager.name.upper()}", id="modal-title")
            yield Rule(classes="section-divider")

            # Fixed Current Source Section (outside of scrollable area)
            if self.mirror_list:
                current_sources = [(i, name, url) for i, (name, url, is_current) in enumerate(self.mirror_list) if is_current]
                selectable_sources = [(i, name, url) for i, (name, url, is_current) in enumerate(self.mirror_list) if not is_current]

                if current_sources:
                    with Container(id="current-source-container"):
                        yield Label("Current Source:", classes="section-header")
                        for i, name, url in current_sources:
                            display_url = url
                            if len(display_url) > 60:
                                display_url = display_url[:57] + "..."
                            text = f"  {name.title()}: {display_url}"
                            yield Static(text, id=f"current-source-{i}", classes="current-source-display")

                    yield Rule(classes="section-divider")

                # Scrollable Available Sources Section
                with Container(id="available-sources-header"):
                    yield Label("Available Sources:", classes="section-header")
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
            
            # Bottom shortcuts area - mimic main menu style exactly
            with Container(id="help-box"):
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
        """Scroll to current item using Textual's built-in VerticalScroll behavior."""
        try:
            # With VerticalScroll, we just need to scroll the selected item into view
            current_item = self.query_one(f"#mirror-item-{self.selected_index}", Static)
            current_item.scroll_visible(animate=False)
        except Exception:
            # If item not found, ignore silently
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