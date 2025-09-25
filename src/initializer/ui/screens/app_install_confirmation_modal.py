"""Application Installation Confirmation Modal."""

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, ScrollableContainer
from textual.screen import ModalScreen
from textual.widgets import Static, Rule, Label
from textual.events import Key
from typing import Callable, List, Dict


class AppInstallConfirmationModal(ModalScreen):
    """Modal screen for confirming application installation/uninstallation."""
    
    BINDINGS = [
        ("escape", "cancel_operation", "Cancel"),
        ("enter", "confirm_change", "Confirm"),
        ("y", "confirm_change", "Yes"),
        ("n", "cancel_operation", "No"),
        ("j", "scroll_down", "Scroll Down"),
        ("k", "scroll_up", "Scroll Up"),
        ("down", "scroll_down", "Scroll Down"),
        ("up", "scroll_up", "Scroll Up"),
        ("pagedown", "scroll_page_down", "Page Down"),
        ("pageup", "scroll_page_up", "Page Up"),
    ]
    
    # CSS styles for the modal - only custom styles not covered by global styles
    CSS = """
    AppInstallConfirmationModal {
        align: center middle;
    }

    .action-header {
        text-style: bold;
        color: $text;
        margin: 1 0 0 0;
        height: auto;
        min-height: 1;
    }

    .action-item {
        margin: 0 0 0 2;
        color: $text;
        height: auto;
        min-height: 1;
        background: $surface;
    }

    .command-display {
        margin: 0 0 0 2;
        padding: 1;
        background: $boost;
        border: round #7dd3fc;
        color: $text;
        height: auto;
        min-height: 1;
    }

    .warning-text {
        color: #f59e0b;
        text-style: bold;
        margin: 1 0;
        height: auto;
        min-height: 1;
        background: $surface;
    }
    """
    
    def __init__(self, actions: List[Dict], callback: Callable[[bool], None], app_installer):
        super().__init__()
        self.actions = actions
        self.callback = callback
        self.app_installer = app_installer
    
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
        """Handle key events using @on decorator for reliable event processing."""
        if event.key == "enter":
            self.action_confirm_change()
            event.prevent_default()
            event.stop()
        elif event.key == "escape":
            self.action_cancel_operation()
            event.prevent_default()
            event.stop()
        elif event.key == "y":
            self.action_confirm_change()
            event.prevent_default()
            event.stop()
        elif event.key == "n":
            self.action_cancel_operation()
            event.prevent_default()
            event.stop()
    
    def compose(self) -> ComposeResult:
        """Compose the modal interface."""
        with Container(classes="modal-container-xs"):
            yield Static("⚠️ 确认应用安装/卸载", id="confirmation-title")
            yield Rule()

            with ScrollableContainer(id="confirmation-content"):
                # Group actions by type
                install_actions = [a for a in self.actions if a["action"] == "install"]
                uninstall_actions = [a for a in self.actions if a["action"] == "uninstall"]
                
                if install_actions:
                    yield Label("将要安装的应用:", classes="action-header")
                    for action in install_actions:
                        app = action["application"]
                        yield Static(f"• {app.name} - {app.description}", 
                                   classes="action-item")
                        
                        # Show install command
                        command = self.app_installer.get_install_command(app)
                        if command:
                            yield Label("  命令:", classes="action-item")
                            # Truncate long commands for display
                            display_cmd = command if len(command) < 100 else command[:97] + "..."
                            yield Static(f"  {display_cmd}", classes="command-display")
                        
                        # Show post-install command if any
                        if app.post_install:
                            yield Label("  安装后配置:", classes="action-item")
                            display_post = app.post_install if len(app.post_install) < 100 else app.post_install[:97] + "..."
                            yield Static(f"  {display_post}", classes="command-display")
                
                if uninstall_actions:
                    if install_actions:
                        yield Static("")  # Spacer
                    yield Label("将要卸载的应用:", classes="action-header")
                    for action in uninstall_actions:
                        app = action["application"]
                        yield Static(f"• {app.name} - {app.description}", 
                                   classes="action-item")
                        
                        # Show uninstall command
                        command = self.app_installer.get_uninstall_command(app)
                        if command:
                            yield Label("  命令:", classes="action-item")
                            # Truncate long commands for display
                            display_cmd = command if len(command) < 100 else command[:97] + "..."
                            yield Static(f"  {display_cmd}", classes="command-display")
                
                # Warning message
                yield Static("")  # Spacer
                if uninstall_actions:
                    yield Static("⚠️ 警告: 卸载应用可能会影响系统功能！", 
                               classes="warning-text")
                
                # Summary
                yield Static("")  # Spacer
                yield Label(f"总计: {len(install_actions)} 个安装, {len(uninstall_actions)} 个卸载", 
                          classes="section-header")
            

            # Fixed action help at the bottom - mimic mirror confirmation modal style exactly
            with Container(id="help-box"):
                yield Label("J/K=Up/Down | Enter=Confirm | Esc=Cancel", classes="help-text")

    def action_confirm_change(self) -> None:
        """Confirm the installation/uninstallation."""
        self.callback(True)
        self.dismiss()

    def action_cancel_operation(self) -> None:
        """Cancel the operation."""
        self.callback(False)
        self.dismiss()

    def action_scroll_down(self) -> None:
        """Scroll content down."""
        try:
            content = self.query_one("#confirmation-content", ScrollableContainer)
            content.scroll_down()
        except:
            pass

    def action_scroll_up(self) -> None:
        """Scroll content up."""
        try:
            content = self.query_one("#confirmation-content", ScrollableContainer)
            content.scroll_up()
        except:
            pass

    def action_scroll_page_down(self) -> None:
        """Scroll content page down."""
        try:
            content = self.query_one("#confirmation-content", ScrollableContainer)
            content.scroll_page_down()
        except:
            pass

    def action_scroll_page_up(self) -> None:
        """Scroll content page up."""
        try:
            content = self.query_one("#confirmation-content", ScrollableContainer)
            content.scroll_page_up()
        except:
            pass