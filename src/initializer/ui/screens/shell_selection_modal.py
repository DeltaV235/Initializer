"""Shell Selection Modal."""

from typing import Optional

from textual.app import ComposeResult
from textual.containers import Container, Vertical, VerticalScroll
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Label, Rule, Static

from ...utils.logger import get_ui_logger

logger = get_ui_logger("shell_selection_modal")


class ShellSelectionModal(ModalScreen[Optional[str]]):
    """Modal for selecting default shell from available options."""

    BINDINGS = [
        ("escape", "dismiss", "Cancel"),
    ]

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

    #shell-scroll {
        height: 15;
        border: solid $primary;
        margin: 1 0;
    }

    #shell-list {
        height: auto;
    }

    .shell-item {
        padding: 0 1;
        color: $text;
    }

    .shell-current {
        color: $success;
        text-style: bold;
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

    .help-text {
        width: 100%;
        height: 1;
        content-align: center middle;
        text-align: center;
        color: $text-muted;
    }
    """

    selected_index: reactive[int] = reactive(0)

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

            # Shell list with scroll
            with VerticalScroll(id="shell-scroll"):
                with Vertical(id="shell-list"):
                    for shell in self.available_shells:
                        is_current = shell == self.current_shell
                        # Initial render without arrow (will be updated by _update_shell_display)
                        display_text = f"  {shell}"
                        if is_current:
                            display_text += " (Current)"

                        classes = "shell-item"
                        if is_current:
                            classes += " shell-current"

                        yield Static(display_text, classes=classes)

            yield Rule()

            with Container(id="help-box"):
                yield Label("J/K=Navigate | Enter=Select | ESC=Cancel", classes="help-text")

    def on_mount(self) -> None:
        """Handle mount event to set initial selection."""
        try:
            self.selected_index = 0
            self.call_after_refresh(self._update_shell_display)
            logger.debug("Shell selection modal mounted")
        except Exception as e:
            logger.debug(f"Failed to initialize shell selection modal: {e}")

    def watch_selected_index(self, old_value: int, new_value: int) -> None:
        """Watch for changes to selected_index and update display."""
        self._update_shell_display()

    def _update_shell_display(self) -> None:
        """Update shell list display with arrow indicators."""
        try:
            shell_items = self.query(".shell-item")
            for i, item in enumerate(shell_items):
                if i >= len(self.available_shells):
                    break

                shell = self.available_shells[i]
                is_current = shell == self.current_shell
                arrow = "▶ " if i == self.selected_index else "  "
                display_text = f"{arrow}{shell}"
                if is_current:
                    display_text += " (Current)"

                item.update(display_text)
        except Exception as e:
            logger.debug(f"Failed to update shell display: {e}")

    def _scroll_to_current(self) -> None:
        """Scroll to ensure current selection is visible."""
        try:
            scroll = self.query_one("#shell-scroll", VerticalScroll)
            shell_items = self.query(".shell-item")
            if self.selected_index < len(shell_items):
                current_item = shell_items[self.selected_index]
                scroll.scroll_to_widget(current_item, animate=False)
        except Exception as e:
            logger.debug(f"Failed to scroll to current item: {e}")

    def action_nav_up(self) -> None:
        """Navigate up in the shell list."""
        if self.selected_index > 0:
            self.selected_index -= 1
            self._scroll_to_current()

    def action_nav_down(self) -> None:
        """Navigate down in the shell list."""
        if self.selected_index < len(self.available_shells) - 1:
            self.selected_index += 1
            self._scroll_to_current()

    def action_select_current(self) -> None:
        """Select the currently highlighted shell."""
        try:
            if 0 <= self.selected_index < len(self.available_shells):
                selected_shell = self.available_shells[self.selected_index]
                logger.info(f"User selected shell: {selected_shell}")

                # If selecting the same shell, no action needed
                if selected_shell == self.current_shell:
                    logger.debug("Selected shell is already the current shell")
                    self.dismiss(None)
                    return

                # Return selected shell path
                self.dismiss(selected_shell)
            else:
                logger.warning(f"Invalid selection index: {self.selected_index}")
                self.dismiss(None)
        except Exception as exc:
            logger.error(f"Failed to handle shell selection: {exc}", exc_info=True)
            self.dismiss(None)

    def on_key(self, event) -> None:  # type: ignore[override]
        """Handle key events."""
        if event.key == "escape":
            logger.debug("User pressed ESC to cancel")
            self.dismiss(None)
        elif event.key == "j":
            self.action_nav_down()
            event.prevent_default()
            event.stop()
        elif event.key == "k":
            self.action_nav_up()
            event.prevent_default()
            event.stop()
        elif event.key == "enter":
            self.action_select_current()
            event.prevent_default()
            event.stop()
