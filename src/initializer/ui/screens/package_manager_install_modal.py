"""Package Manager Installation Selection Modal."""

from textual import on, work
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.screen import ModalScreen
from textual.widgets import Button, Static, Rule, Label, Checkbox
from textual.events import Key
from typing import Callable, Optional, List, Dict
from textual.reactive import reactive

from ...modules.package_manager import PackageManagerDetector, PackageManager


class PackageManagerInstallModal(ModalScreen):
    """Modal screen for selecting package managers to install/uninstall."""
    
    BINDINGS = [
        ("escape", "dismiss", "Cancel"),
        ("i", "install_selected", "Install/Uninstall"),
    ]
    
    # CSS styles for the modal
    CSS = """
    PackageManagerInstallModal {
        align: center middle;
    }
    
    #modal-container {
        width: 80%;
        height: 80%;
        max-height: 30;
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
    
    #pm-list {
        height: auto;
        min-height: 1;
        margin: 0 0 1 0;
    }
    
    .pm-item {
        height: auto;
        min-height: 2;
        padding: 0 0;
    }
    
    .pm-item-selected {
        background: $primary;
    }
    
    .pm-checkbox {
        width: 3;
        height: 1;
        padding: 0;
        margin: 0 1 0 0;
    }
    
    .pm-name {
        width: auto;
        padding: 0;
        margin: 0;
    }
    
    .pm-status {
        color: $text-muted;
        text-style: dim;
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
    """
    
    # Reactive properties
    selected_index = reactive(0)
    
    def __init__(self, callback: Callable[[List[Dict]], None]):
        super().__init__()
        self.callback = callback
        self.detector = PackageManagerDetector()
        self.all_package_managers = self.detector.all_package_managers
        
        # Filter to only show installable package managers
        self.installable_pms = [pm for pm in self.all_package_managers 
                                if pm.installable or pm.available]
        
        # Track selection state for each package manager
        # Initialize: installed PMs are checked, uninstalled are unchecked
        self.selection_state = {
            pm.name: pm.available for pm in self.installable_pms
        }
        
        self.selected_index = 0
    
    def on_mount(self) -> None:
        """Initialize the screen."""
        self._update_display()
        self.focus()
    
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
        if event.key == "enter" or event.key == "space":
            self.action_toggle_current()
            event.prevent_default()
            event.stop()
        elif event.key == "j" or event.key == "down":
            self.action_nav_down()
            event.prevent_default()
            event.stop()
        elif event.key == "k" or event.key == "up":
            self.action_nav_up()
            event.prevent_default()
            event.stop()
        elif event.key == "i":
            self.action_install_selected()
            event.prevent_default()
            event.stop()
        elif event.key == "escape":
            self.dismiss()
            event.prevent_default()
            event.stop()
    
    def compose(self) -> ComposeResult:
        """Compose the modal interface."""
        with Container(id="modal-container"):
            yield Static("Select Package Managers to Install/Uninstall", id="modal-title")
            yield Rule()
            
            with ScrollableContainer(id="modal-content"):
                yield Label("Available Package Managers:", classes="info-key")
                with Vertical(id="pm-list"):
                    for i, pm in enumerate(self.installable_pms):
                        with Horizontal(id=f"pm-item-{i}", classes="pm-item"):
                            # Arrow indicator for current selection
                            arrow = "▶ " if i == self.selected_index else "  "
                            
                            # Checkbox state
                            check = "[X]" if self.selection_state.get(pm.name, False) else "[ ]"
                            
                            # Package manager info
                            pm_text = f"{arrow}{check} {pm.name.upper()}"
                            if pm.description:
                                pm_text += f" - {pm.description}"
                            
                            # Status indicator
                            if pm.available:
                                pm_text += " (Installed)"
                            
                            yield Static(pm_text, classes="pm-display")
                    
                    yield Static("", classes="bottom-spacer")
            
            # Bottom shortcuts area
            yield Rule()
            yield Label("J/K=Up/Down | SPACE/ENTER=Toggle | I=Install/Uninstall | ESC=Cancel", classes="help-text")
    
    def _update_display(self) -> None:
        """Update the package manager list display."""
        try:
            pm_list = self.query_one("#pm-list", Vertical)
            
            # Update each item
            for i, pm in enumerate(self.installable_pms):
                pm_item = pm_list.query_one(f"#pm-item-{i} .pm-display", Static)
                
                # Arrow indicator
                arrow = "▶ " if i == self.selected_index else "  "
                
                # Checkbox state
                check = "[X]" if self.selection_state.get(pm.name, False) else "[ ]"
                
                # Package manager info
                pm_text = f"{arrow}{check} {pm.name.upper()}"
                if pm.description:
                    pm_text += f" - {pm.description}"
                
                # Status indicator
                if pm.available:
                    pm_text += " (Installed)"
                
                pm_item.update(pm_text)
                
        except Exception as e:
            # Fallback if update fails
            pass
    
    def action_nav_down(self) -> None:
        """Navigate down in the list."""
        if self.selected_index < len(self.installable_pms) - 1:
            self.selected_index += 1
            self._update_display()
            self._scroll_to_current()
    
    def action_nav_up(self) -> None:
        """Navigate up in the list."""
        if self.selected_index > 0:
            self.selected_index -= 1
            self._update_display()
            self._scroll_to_current()
    
    def action_toggle_current(self) -> None:
        """Toggle the current package manager selection."""
        if 0 <= self.selected_index < len(self.installable_pms):
            pm = self.installable_pms[self.selected_index]
            # Toggle the selection state
            self.selection_state[pm.name] = not self.selection_state.get(pm.name, False)
            self._update_display()
    
    def action_install_selected(self) -> None:
        """Process the selected package managers for installation/uninstallation."""
        # Determine what actions to take
        actions = []
        
        for pm in self.installable_pms:
            is_selected = self.selection_state.get(pm.name, False)
            
            if pm.available and not is_selected:
                # Installed but unchecked - uninstall
                actions.append({
                    "action": "uninstall",
                    "package_manager": pm,
                })
            elif not pm.available and is_selected:
                # Not installed but checked - install
                actions.append({
                    "action": "install",
                    "package_manager": pm,
                })
        
        if actions:
            # Pass actions to callback
            self.callback(actions)
            self.dismiss()
        else:
            # No changes to make
            self.dismiss()
    
    def _scroll_to_current(self) -> None:
        """Scroll to ensure current selection is visible."""
        try:
            scrollable_container = self.query_one("#modal-content", ScrollableContainer)
            current_item = self.query_one(f"#pm-item-{self.selected_index}", Horizontal)
            
            if hasattr(scrollable_container, 'scroll_to_widget'):
                scrollable_container.scroll_to_widget(current_item, animate=True, speed=60, center=True)
            else:
                # Manual scrolling fallback
                header_height = 2
                visible_height = 20
                current_position = header_height + self.selected_index * 2
                current_scroll = scrollable_container.scroll_y
                
                if current_position < current_scroll:
                    scrollable_container.scroll_y = current_position
                elif current_position > current_scroll + visible_height:
                    scrollable_container.scroll_y = current_position - visible_height + 2
                    
        except Exception:
            pass
    
    def action_dismiss(self) -> None:
        """Dismiss the modal."""
        self.dismiss()