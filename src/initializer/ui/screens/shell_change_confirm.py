"""Shell Change Confirmation Modal."""

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.events import Key
from textual.screen import ModalScreen
from textual.widgets import Label, Rule, Static

from ...utils.logger import get_ui_logger

logger = get_ui_logger("shell_change_confirm")


class ShellChangeConfirm(ModalScreen[bool]):
    """Confirmation modal for changing default shell to Zsh."""

    BINDINGS = [
        ("y", "confirm", "Yes"),
        ("n", "cancel", "No"),
        ("enter", "confirm", "Confirm"),
        ("escape", "cancel", "Cancel"),
    ]

    CSS = """
    ShellChangeConfirm {
        align: center middle;
    }

    #confirm-title {
        text-style: bold;
        color: $text;
        margin: 0 0 1 0;
        text-align: center;
    }

    .confirm-content {
        padding: 1;
        margin: 0 0 1 0;
    }

    .info-text {
        color: $text;
        margin: 0 0 1 0;
        text-align: center;
    }

    .action-list {
        color: $primary;
        margin: 0 0 1 0;
        text-align: center;
    }

    #help-box {
        dock: bottom;
        width: 100%;
        height: auto;
        min-height: 3;
        border: round white;
        background: $surface;
        padding: 0 1;
        margin: 0;
    }

    .help-text {
        width: 100%;
        height: 1;
        content-align: center middle;
        text-align: center;
        color: $text-muted;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose the confirmation modal."""
        with Container(classes="modal-container-mini"):
            yield Static("⚠️ Change Default Shell?", id="confirm-title")
            yield Rule()

            with Vertical(classes="confirm-content"):
                yield Static(
                    "Set Zsh as your default shell?",
                    classes="info-text"
                )
                yield Static(
                    "Command: chsh -s $(which zsh)",
                    classes="action-list"
                )

            with Container(id="help-box"):
                yield Label("Y/Enter=Yes | N/ESC=No", classes="help-text")

    def on_mount(self) -> None:
        """Handle mount event and set focus."""
        try:
            self.focus()
            logger.debug("Shell change confirm modal mounted and focused")
        except Exception as e:
            logger.debug(f"Failed to initialize modal: {e}")

    def action_confirm(self) -> None:
        """Confirm action."""
        logger.info("User confirmed shell change")
        self.dismiss(True)

    def action_cancel(self) -> None:
        """Cancel action."""
        logger.info("User declined shell change")
        self.dismiss(False)

    @on(Key)
    def handle_key_event(self, event: Key) -> None:
        """Handle keyboard shortcuts."""
        if event.key in ("y", "enter"):
            self.action_confirm()
            event.prevent_default()
            event.stop()
        elif event.key in ("n", "escape"):
            self.action_cancel()
            event.prevent_default()
            event.stop()
