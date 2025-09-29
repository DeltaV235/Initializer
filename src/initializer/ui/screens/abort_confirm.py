"""Abort Installation Confirmation."""

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Static, Rule
from textual.events import Key


class AbortConfirm(ModalScreen[bool]):
    """Screen for confirming installation abort."""

    BINDINGS = [
        ("escape", "cancel_abort", "Cancel"),
        ("enter", "confirm_abort", "Confirm"),
        ("y", "confirm_abort", "Yes"),
        ("n", "cancel_abort", "No"),
    ]

    # CSS styles for the modal
    CSS = """
    AbortConfirm {
        align: center middle;
    }

    .abort-warning-title {
        color: #ef4444;
        text-style: bold;
        text-align: center;
        height: auto;
        margin: 0 0 1 0;
    }

    .abort-warning-text {
        color: #f59e0b;
        text-align: center;
        height: auto;
        margin: 0 0 1 0;
    }

    .abort-consequence-text {
        color: $text-muted;
        text-align: center;
        height: auto;
        margin: 0 0 2 0;
    }

    .abort-button-container {
        layout: horizontal;
        align: center middle;
        height: 3;
        margin: 1 0 0 0;
    }

    .abort-button {
        margin: 0 1;
        min-width: 12;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose the confirmation modal interface."""
        with Container(classes="modal-container-sm"):
            yield Static("⚠️ Confirm Installation Abort", classes="abort-warning-title")
            yield Rule()

            yield Static(
                "Installation process is currently running",
                classes="abort-warning-text"
            )

            yield Static(
                "Force abort may cause:\n"
                "• Packages in inconsistent state\n"
                "• Package manager may need manual repair\n"
                "• System may require repair commands",
                classes="abort-consequence-text"
            )

            with Horizontal(classes="abort-button-container"):
                yield Button("🛑 Confirm Abort (Y)", id="confirm", variant="error", classes="abort-button")
                yield Button("📦 Continue Install (N)", id="cancel", variant="primary", classes="abort-button")

    @on(Key)
    def handle_key_event(self, event: Key) -> None:
        """Handle key events using @on decorator."""
        if event.key == "y" or event.key == "enter":
            self.action_confirm_abort()
            event.prevent_default()
            event.stop()
        elif event.key == "n" or event.key == "escape":
            self.action_cancel_abort()
            event.prevent_default()
            event.stop()

    @on(Button.Pressed, "#confirm")
    def action_confirm_abort(self) -> None:
        """Confirm the abort operation."""
        self.dismiss(True)

    @on(Button.Pressed, "#cancel")
    def action_cancel_abort(self) -> None:
        """Cancel the abort operation."""
        self.dismiss(False)