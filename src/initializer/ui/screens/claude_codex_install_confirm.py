"""Claude Code & Codex Installation Confirmation Modal."""

from textual.app import ComposeResult
from textual.containers import Container, Vertical, ScrollableContainer
from textual.screen import ModalScreen
from textual.widgets import Label, Static

from ...utils.logger import get_ui_logger
from ...utils.text_utils import truncate_command_for_display

logger = get_ui_logger("claude_codex_install_confirm")


class ClaudeCodexInstallConfirm(ModalScreen[bool]):
    """Confirmation modal for Claude Code/Codex install/uninstall operations."""

    BINDINGS = [
        ("y,Y", "confirm", "Yes"),
        ("n,N", "cancel", "No"),
        ("enter", "confirm", "Confirm"),
        ("escape", "cancel", "Cancel"),
    ]

    CSS = """
    ClaudeCodexInstallConfirm {
        align: center middle;
    }

    #confirm-title {
        text-style: bold;
        color: $primary;
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
    }

    .command-list {
        color: $primary;
        margin: 0 0 1 0;
        padding: 0 1;
    }

    #help-box {
        height: 3;
        background: $panel;
        padding: 1;
    }

    .help-text {
        color: $text;
        text-align: center;
    }
    """

    def __init__(self, tool_name: str, operation: str, commands: list[str]):
        """Initialize confirmation modal.

        Args:
            tool_name: Name of the tool ('claude' or 'codex')
            operation: Operation type ('install' or 'uninstall')
            commands: List of commands to execute
        """
        super().__init__()
        self.tool_name = tool_name.title()
        self.operation = operation
        self.commands = commands

        logger.debug(
            f"Created confirmation modal: tool={tool_name}, "
            f"operation={operation}, commands={len(commands)}"
        )

    def compose(self) -> ComposeResult:
        """Compose the modal content."""
        with Container(classes="modal-container-md"):
            yield Label(
                f"{self.operation.title()} {self.tool_name}?",
                id="confirm-title"
            )

            with Vertical(classes="confirm-content"):
                yield Label(
                    "The following commands will be executed:",
                    classes="info-text"
                )

                with ScrollableContainer(classes="command-list"):
                    for cmd in self.commands:
                        truncated_cmd = truncate_command_for_display(cmd, max_length=100)
                        yield Label(f"  $ {truncated_cmd}")

            with Container(id="help-box"):
                yield Static(
                    "[Y/Enter] Confirm  [N/Esc] Cancel",
                    classes="help-text"
                )

    def action_confirm(self) -> None:
        """Handle confirmation action."""
        logger.info(f"User confirmed {self.operation} for {self.tool_name}")
        self.dismiss(True)

    def action_cancel(self) -> None:
        """Handle cancel action."""
        logger.info(f"User cancelled {self.operation} for {self.tool_name}")
        self.dismiss(False)
