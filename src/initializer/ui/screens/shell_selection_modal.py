"""Shell Selection Modal."""

from typing import Optional

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, ListItem, ListView, Rule, Static

from ...utils.logger import get_ui_logger

logger = get_ui_logger("shell_selection_modal")


class ShellSelectionModal(ModalScreen[Optional[str]]):
    """Modal for selecting default shell from available options."""

    CSS = """
    ShellSelectionModal {
        align: center middle;
    }

    #shell-modal-title {
        text-style: bold;
        color: $text;
        margin: 0 0 1 0;
        text-align: center;
    }

    .shell-modal-description {
        color: $text-muted;
        margin: 0 0 1 0;
        text-align: center;
    }

    #shell-list {
        height: 15;
        border: solid $primary;
        margin: 1 0;
    }

    .shell-list-item {
        padding: 0 1;
    }

    .shell-current {
        color: $success;
        text-style: bold;
    }

    .shell-available {
        color: $text;
    }

    .help-text {
        text-align: center;
        color: $text-muted;
        margin: 1 0 0 0;
    }
    """

    def __init__(
        self,
        current_shell: str,
        available_shells: list[str],
    ):
        """Initialize shell selection modal.

        Args:
            current_shell: Current default shell path
            available_shells: List of available shell paths
        """
        super().__init__()
        self.current_shell = current_shell
        self.available_shells = available_shells

    def compose(self) -> ComposeResult:
        """Compose the shell selection modal."""
        with Container(classes="modal-container-sm"):
            yield Static("Select Default Shell", id="shell-modal-title")

            yield Static(
                f"Current: {self.current_shell}",
                classes="shell-modal-description",
            )

            yield Rule()

            # Shell list
            with ListView(id="shell-list"):
                for shell in self.available_shells:
                    is_current = shell == self.current_shell
                    display_text = f"{'● ' if is_current else '  '}{shell}"
                    if is_current:
                        display_text += " (Current)"

                    yield ListItem(
                        Label(display_text),
                        classes="shell-list-item " + ("shell-current" if is_current else "shell-available"),
                    )

            yield Rule()

            yield Static("↑↓ Navigate | Enter Select | ESC Cancel", classes="help-text")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle shell selection."""
        try:
            # Get selected index
            selected_index = event.list_view.index
            if selected_index is None or selected_index >= len(self.available_shells):
                logger.warning(f"Invalid selection index: {selected_index}")
                self.dismiss(None)
                return

            selected_shell = self.available_shells[selected_index]
            logger.info(f"User selected shell: {selected_shell}")

            # If selecting the same shell, no action needed
            if selected_shell == self.current_shell:
                logger.debug("Selected shell is already the current shell")
                self.dismiss(None)
                return

            # Return selected shell path
            self.dismiss(selected_shell)

        except Exception as exc:
            logger.error(f"Failed to handle shell selection: {exc}", exc_info=True)
            self.dismiss(None)

    def on_key(self, event) -> None:  # type: ignore[override]
        """Handle key events."""
        if event.key == "escape":
            logger.debug("User pressed ESC to cancel")
            self.dismiss(None)
