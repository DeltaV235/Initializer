"""Installation Confirmation Modal."""

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, ScrollableContainer
from textual.screen import ModalScreen
from textual.widgets import Button, Static, Rule, Label
from textual.events import Key
from typing import Callable, List, Dict

from ...modules.package_manager import PackageManagerDetector


class InstallationConfirmationModal(ModalScreen):
    """Modal screen for confirming package manager installation/uninstallation."""
    
    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("enter", "confirm", "Confirm"),
        ("y", "confirm", "Confirm"),
        ("n", "cancel", "Cancel"),
    ]
    
    # CSS styles for the modal
    CSS = """
    InstallationConfirmationModal {
        align: center middle;
    }
    
    #modal-container {
        width: 80%;
        height: auto;
        max-height: 80%;
        background: $surface;
        border: solid $warning;
        padding: 1;
        layout: vertical;
    }
    
    #modal-title {
        text-style: bold;
        color: $warning;
        margin: 0 0 1 0;
    }
    
    #modal-content {
        height: auto;
        max-height: 20;
        overflow-y: auto;
        padding: 0 1;
        margin: 0 0 1 0;
    }
    
    .action-header {
        text-style: bold;
        color: $text;
        margin: 1 0 0 0;
    }
    
    .action-item {
        margin: 0 0 0 2;
        color: $text;
    }
    
    .command-display {
        margin: 0 0 0 2;
        padding: 1;
        background: $boost;
        border: round #7dd3fc;
        color: $text;
    }
    
    .warning-text {
        color: $warning;
        text-style: bold;
        margin: 1 0;
    }
    
    #button-container {
        layout: horizontal;
        align: center middle;
        height: 3;
        margin: 1 0 0 0;
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
    """
    
    def __init__(self, actions: List[Dict], callback: Callable[[bool], None], config_manager=None):
        super().__init__()
        self.actions = actions
        self.callback = callback
        self.detector = PackageManagerDetector(config_manager)
    
    def on_mount(self) -> None:
        """Initialize the screen."""
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
        if event.key == "y" or event.key == "enter":
            self.action_confirm()
            event.prevent_default()
            event.stop()
        elif event.key == "n" or event.key == "escape":
            self.action_cancel()
            event.prevent_default()
            event.stop()
    
    def compose(self) -> ComposeResult:
        """Compose the modal interface."""
        with Container(id="modal-container"):
            yield Static("⚠️ Confirm Installation/Uninstallation", id="modal-title")
            yield Rule()
            
            with ScrollableContainer(id="modal-content"):
                # Group actions by type
                install_actions = [a for a in self.actions if a["action"] == "install"]
                uninstall_actions = [a for a in self.actions if a["action"] == "uninstall"]
                
                if install_actions:
                    yield Label("Package Managers to Install:", classes="action-header")
                    for action in install_actions:
                        pm = action["package_manager"]
                        yield Static(f"• {pm.name.upper()} - {pm.description or 'Package Manager'}", 
                                   classes="action-item")
                        
                        # Show install command
                        command = self.detector.get_install_command(pm.name)
                        if command:
                            yield Label("  Command:", classes="action-item")
                            # Truncate long commands for display
                            display_cmd = command if len(command) < 100 else command[:97] + "..."
                            yield Static(f"  {display_cmd}", classes="command-display")
                
                if uninstall_actions:
                    if install_actions:
                        yield Static("")  # Spacer
                    yield Label("Package Managers to Uninstall:", classes="action-header")
                    for action in uninstall_actions:
                        pm = action["package_manager"]
                        yield Static(f"• {pm.name.upper()} - {pm.description or 'Package Manager'}", 
                                   classes="action-item")
                        
                        # Show uninstall command
                        command = self.detector.get_uninstall_command(pm.name)
                        if command:
                            yield Label("  Command:", classes="action-item")
                            # Truncate long commands for display
                            display_cmd = command if len(command) < 100 else command[:97] + "..."
                            yield Static(f"  {display_cmd}", classes="command-display")
                
                # Warning message
                yield Static("")  # Spacer
                if uninstall_actions:
                    yield Static("⚠️ Warning: Uninstalling package managers may affect your system!", 
                               classes="warning-text")
            
            yield Rule()
            
            # Buttons
            with Horizontal(id="button-container"):
                yield Button("✅ Confirm (Y)", id="confirm", variant="primary")
                yield Static("  ")  # Spacer
                yield Button("❌ Cancel (N)", id="cancel", variant="default")
            
            yield Label("Press Y to confirm, N to cancel", classes="help-text")
    
    @on(Button.Pressed, "#confirm")
    def action_confirm(self) -> None:
        """Confirm the installation/uninstallation."""
        self.callback(True)
        self.dismiss()
    
    @on(Button.Pressed, "#cancel")
    def action_cancel(self) -> None:
        """Cancel the operation."""
        self.callback(False)
        self.dismiss()
    
    def action_dismiss(self) -> None:
        """Dismiss the modal (same as cancel)."""
        self.action_cancel()