"""Claude Code & Codex Installation Progress Modal."""

from textual import work
from textual.app import ComposeResult
from textual.containers import Container, Vertical, ScrollableContainer
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Label, Static

from ...utils.logger import get_ui_logger
from ...utils.text_utils import format_log_output

logger = get_ui_logger("claude_codex_install_progress")


class ClaudeCodexInstallProgress(ModalScreen[bool]):
    """Progress modal for Claude Code/Codex install/uninstall operations."""

    BINDINGS = [
        ("escape,q", "close", "Close"),
    ]

    CSS = """
    ClaudeCodexInstallProgress {
        align: center middle;
    }

    #progress-title {
        text-style: bold;
        color: $primary;
        margin: 0 0 1 0;
        text-align: center;
    }

    #progress-log {
        height: 20;
        border: solid $primary;
        margin: 1 0;
        padding: 1;
    }

    #log-content {
        color: $text;
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

    # Reactive state
    is_running = reactive(True)
    status = reactive("running")  # "running", "success", "failed"

    def __init__(self, tool_name: str, operation: str, commands: list[str]):
        """Initialize progress modal.

        Args:
            tool_name: Name of the tool ('claude' or 'codex')
            operation: Operation type ('install' or 'uninstall')
            commands: List of commands to execute
        """
        super().__init__()
        self.tool_name = tool_name.title()
        self.operation = operation
        self.commands = commands
        self.log_lines: list[str] = []

        logger.debug(
            f"Created progress modal: tool={tool_name}, "
            f"operation={operation}, commands={len(commands)}"
        )

    def compose(self) -> ComposeResult:
        """Compose the modal content."""
        with Container(classes="modal-container-xl"):
            yield Label(
                f"{self.operation.title()} {self.tool_name}...",
                id="progress-title"
            )

            with ScrollableContainer(id="progress-log"):
                yield Static("Starting...", id="log-content")

            with Container(id="help-box"):
                yield Label("Please wait...", id="help-text", classes="help-text")

    def on_mount(self) -> None:
        """Start operation when modal is mounted."""
        logger.info(f"Starting {self.operation} operation for {self.tool_name}")
        self._execute_operation()

    @work(exclusive=True, thread=True)
    async def _execute_operation(self) -> None:
        """Execute the install/uninstall operation in background thread."""
        import asyncio

        try:
            self._append_log(f"{self.operation.title()} {self.tool_name}...")
            self._append_log("")

            # Execute commands
            success = True
            for idx, cmd in enumerate(self.commands, 1):
                self._append_log(f"[{idx}/{len(self.commands)}] $ {cmd}")
                self._append_log("")

                try:
                    # Execute the command using subprocess
                    process = await asyncio.create_subprocess_shell(
                        cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )

                    # Read output line by line
                    while True:
                        line = await process.stdout.readline()
                        if not line:
                            break
                        decoded_line = line.decode('utf-8', errors='replace').rstrip()
                        if decoded_line:
                            formatted_line = format_log_output(decoded_line, max_length=120)
                            self._append_log(f"  {formatted_line}")

                    # Wait for process to complete
                    returncode = await process.wait()

                    # Check exit code
                    if returncode == 0:
                        self._append_log(f"  ✓ Command completed successfully (exit code: 0)")
                        self._append_log("")
                    else:
                        # Read stderr if command failed
                        stderr = await process.stderr.read()
                        if stderr:
                            stderr_text = stderr.decode('utf-8', errors='replace')
                            self._append_log(f"  ✗ Error output:")
                            for line in stderr_text.split('\n'):
                                if line.strip():
                                    formatted_error_line = format_log_output(line, max_length=110)
                                    self._append_log(f"    {formatted_error_line}")
                        self._append_log(f"  ✗ Command failed (exit code: {returncode})")
                        self._append_log("")
                        success = False
                        break  # Stop executing remaining commands

                except Exception as cmd_error:
                    logger.error(f"Command execution error: {cmd_error}")
                    self._append_log(f"  ✗ Execution error: {cmd_error}")
                    self._append_log("")
                    success = False
                    break

            if success:
                self._append_log(f"{self.operation.title()} completed successfully!")
                self.status = "success"
            else:
                self._append_log(f"{self.operation.title()} failed!")
                self.status = "failed"

        except Exception as e:
            logger.error(f"Operation failed: {e}")
            self._append_log(f"Error: {e}")
            self.status = "failed"

        finally:
            self.is_running = False
            self.call_from_thread(self._update_help_text)

    def _append_log(self, line: str) -> None:
        """Append a line to the log output.

        Args:
            line: Log line to append
        """
        self.log_lines.append(line)
        self.call_from_thread(self._refresh_log)

    def _refresh_log(self) -> None:
        """Refresh the log display."""
        try:
            log_content = self.query_one("#log-content", Static)
            log_content.update("\n".join(self.log_lines))

            # Auto-scroll to bottom
            log_container = self.query_one("#progress-log", ScrollableContainer)
            log_container.scroll_end(animate=False)

        except Exception as e:
            logger.warning(f"Failed to refresh log: {e}")

    def _update_help_text(self) -> None:
        """Update help text based on operation status."""
        try:
            help_text = self.query_one("#help-text", Label)

            if self.status == "success":
                help_text.update("✓ Completed! ESC/Q=Close")
            else:
                help_text.update("✗ Failed! ESC/Q=Close")

            logger.info(f"Operation completed with status: {self.status}")

        except Exception as e:
            logger.warning(f"Failed to update help text: {e}")

    def action_close(self) -> None:
        """Handle close action."""
        if self.is_running:
            logger.debug("Close action blocked: operation still running")
            return  # Prevent closing while operation is running

        logger.info(f"Closing progress modal: status={self.status}")
        self.dismiss(self.status == "success")

    def watch_is_running(self, is_running: bool) -> None:
        """Watch for changes to is_running state.

        Args:
            is_running: Whether operation is still running
        """
        if not is_running:
            logger.debug("Operation completed, updating UI")
