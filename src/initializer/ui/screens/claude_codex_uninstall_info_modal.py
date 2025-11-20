"""Claude Code & Codex Uninstall Information Modal."""

from textual.app import ComposeResult
from textual.containers import Container, ScrollableContainer
from textual.screen import ModalScreen
from textual.widgets import Label, Static

from ...utils.logger import get_ui_logger

logger = get_ui_logger("claude_codex_uninstall_info")


class ClaudeCodexUninstallInfoModal(ModalScreen[bool]):
    """Information modal for Claude Code/Codex uninstall steps."""

    BINDINGS = [
        ("enter", "acknowledge", "OK"),
        ("escape", "dismiss", "Cancel"),
    ]

    CSS = """
    ClaudeCodexUninstallInfoModal {
        align: center middle;
    }

    #info-title {
        text-style: bold;
        color: $primary;
        margin: 0 0 1 0;
        text-align: center;
    }

    .info-content {
        padding: 1;
        margin: 0 0 1 0;
    }

    .info-text {
        color: $text;
        margin: 0 0 1 0;
        width: 100%;
    }

    .warning-text {
        color: $warning;
        text-style: bold;
        margin: 0 0 1 0;
        width: 100%;
    }

    .command-text {
        color: $primary;
        margin: 0 0 1 0;
        padding: 0 2;
        width: 100%;
    }

    .step-title {
        text-style: bold;
        color: $secondary;
        margin: 1 0 0 0;
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

    def __init__(self, tool_name: str, installation_method: str = "unknown"):
        """Initialize uninstall information modal.

        Args:
            tool_name: Name of the tool ('claude' or 'codex')
            installation_method: Installation method (npm_global, manual, script, unknown)
        """
        super().__init__()
        self.tool_name = tool_name.title()
        self.tool_name_lower = tool_name.lower()
        self.installation_method = installation_method

        logger.debug(
            f"Created uninstall info modal: tool={tool_name}, "
            f"install_method={installation_method}"
        )

    def compose(self) -> ComposeResult:
        """Compose the modal content."""
        with Container(classes="modal-container-md"):
            yield Label(
                f"Uninstall {self.tool_name} - Manual Steps",
                id="info-title"
            )

            with ScrollableContainer(classes="info-content"):
                yield Static(
                    "⚠️ Configuration Directory Will Be PRESERVED",
                    classes="warning-text"
                )
                yield Label(
                    f"~/.{self.tool_name_lower}/ will NOT be deleted.",
                    classes="info-text"
                )
                yield Label(
                    "This preserves settings, MCP configs, and session data.",
                    classes="info-text"
                )

                yield Label("Manual Steps Required:", classes="step-title")

                # 根据安装方式显示不同的卸载步骤
                if self.installation_method == "npm_global":
                    # npm 全局安装的卸载方式
                    yield Label(
                        f"1. Uninstall {self.tool_name} via npm:",
                        classes="info-text"
                    )
                    yield Static(
                        f"  $ npm uninstall -g {self.tool_name_lower}",
                        classes="command-text"
                    )

                    yield Label(
                        "2. (Optional) Remove configuration:",
                        classes="info-text"
                    )
                    yield Static(
                        f"  $ rm -rf ~/.{self.tool_name_lower}",
                        classes="command-text"
                    )
                else:
                    # 手动安装或其他方式的卸载步骤
                    yield Label(
                        f"1. Find {self.tool_name} CLI binary:",
                        classes="info-text"
                    )
                    yield Static(
                        f"  $ which {self.tool_name_lower}",
                        classes="command-text"
                    )

                    yield Label(
                        f"2. Remove {self.tool_name} CLI binary:",
                        classes="info-text"
                    )
                    yield Static(
                        f"  $ sudo rm $(which {self.tool_name_lower})",
                        classes="command-text"
                    )

                    yield Label(
                        "3. (Optional) Remove configuration:",
                        classes="info-text"
                    )
                    yield Static(
                        f"  $ rm -rf ~/.{self.tool_name_lower}",
                        classes="command-text"
                    )

                yield Label(
                    "Note: No commands will be executed automatically.",
                    classes="info-text"
                )
                yield Label(
                    "Please run the commands above manually in your terminal.",
                    classes="info-text"
                )

            with Container(id="help-box"):
                yield Label("Enter=OK | ESC=Cancel", classes="help-text")

    def action_acknowledge(self) -> None:
        """Handle acknowledge action."""
        logger.info(f"User acknowledged uninstall info for {self.tool_name}")
        self.dismiss(True)

    def action_dismiss(self) -> None:
        """Handle dismiss action."""
        logger.info(f"User dismissed uninstall info for {self.tool_name}")
        self.dismiss(False)
