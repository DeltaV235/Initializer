"""Shell Change Error Modal."""

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, ScrollableContainer
from textual.events import Key
from textual.screen import ModalScreen
from textual.widgets import Label, Rule, Static

from ...utils.logger import get_ui_logger

logger = get_ui_logger("shell_change_error")


class ShellChangeErrorModal(ModalScreen):
    """Modal screen for displaying shell change errors with troubleshooting tips."""

    BINDINGS = [
        ("escape", "dismiss_modal", "Cancel"),
        ("enter", "dismiss_modal", "Close"),
    ]

    # CSS styles for the modal
    CSS = """
    ShellChangeErrorModal {
        align: center middle;
    }

    #error-content {
        height: 1fr;
        overflow-y: auto;
        padding: 0 1;
        scrollbar-size: 1 1;
    }

    .warning-title {
        color: #f59e0b;
        text-style: bold;
        text-align: center;
        height: auto;
        margin: 0 0 1 0;
    }

    .section-header {
        color: $text;
        text-style: bold;
        height: auto;
        margin: 1 0 0 0;
    }

    .error-message {
        height: auto;
        min-height: 1;
        color: #ef4444;
        background: $surface;
        margin: 0 0 0 1;
    }

    .file-item {
        height: auto;
        min-height: 1;
        color: $text;
        background: $surface;
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

    #help-box {
        dock: bottom;
        width: 100%;
        height: 3;
        border: round white;
        background: $surface;
        padding: 0 1;
        margin: 0;
    }
    """

    def __init__(self, error_message: str, shell_path: str):
        """Initialize shell change error modal.

        Args:
            error_message: Detailed error message from the shell change operation
            shell_path: The target shell path that failed to set
        """
        super().__init__()
        self.error_message = error_message
        self.shell_path = shell_path
        logger.info(f"Shell change error modal initialized: {shell_path}")

    def compose(self) -> ComposeResult:
        """Compose the error modal interface."""
        with Container(classes="modal-container-xs"):
            yield Static(
                "⚠️  Shell Change Failed", id="error-title", classes="warning-title"
            )
            yield Rule()

            with ScrollableContainer(id="error-content"):
                # Target shell information
                yield Label("Target Shell:", classes="section-header")
                yield Static(f"  {self.shell_path}", classes="file-item")

                yield Rule()

                # Error message
                yield Label("Error:", classes="section-header")
                yield Static(f"  {self.error_message}", classes="error-message")

                yield Rule()

                # Troubleshooting tips
                yield Label("Troubleshooting:", classes="section-header")
                yield Static(
                    "  • Ensure the shell is installed (run: which <shell>)",
                    classes="file-item",
                )
                yield Static(
                    "  • Check if shell is listed in /etc/shells", classes="file-item"
                )
                yield Static("  • Verify your permissions", classes="file-item")
                yield Static(
                    f"  • Try manually: sudo chsh -s {self.shell_path}",
                    classes="file-item",
                )

            # Fixed action help at the bottom
            with Container(id="help-box"):
                yield Label("Enter=Close | Esc=Close", classes="help-text")

    def on_mount(self) -> None:
        """Initialize the modal and ensure it can receive focus."""
        self.focus()
        logger.debug("Shell change error modal mounted")

    @on(Key)
    def handle_key_event(self, event: Key) -> None:
        """Handle key events using @on decorator for reliable event processing."""
        if event.key in ["enter", "escape"]:
            logger.debug(f"User pressed {event.key} to close error modal")
            self.dismiss()
            event.prevent_default()
            event.stop()

    def can_focus(self) -> bool:
        """Return True to allow this modal to receive focus."""
        return True

    @property
    def is_modal(self) -> bool:
        """Mark this as a modal screen."""
        return True

    def action_dismiss_modal(self) -> None:
        """Dismiss the modal."""
        logger.debug("Dismissing shell change error modal")
        self.dismiss()
