"""Vim Installation Progress Modal."""

from textual import work
from textual.app import ComposeResult
from textual.containers import Container, Vertical, ScrollableContainer
from textual.screen import ModalScreen
from textual.widgets import Static, Rule, Label
from textual.reactive import reactive
from datetime import datetime
from typing import Optional

from ...modules.vim_manager import VimManager
from ...utils.logger import get_ui_logger

logger = get_ui_logger("vim_install_progress")


class VimInstallProgress(ModalScreen[dict]):
    """Progress modal for Vim install/uninstall operations."""

    BINDINGS = [
        ("escape", "close", "Close"),
        ("j", "scroll_down", "Scroll Down"),
        ("k", "scroll_up", "Scroll Up"),
    ]

    CSS = """
    VimInstallProgress {
        align: center middle;
    }

    #modal-title {
        text-style: bold;
        color: $text;
        margin: 0 0 1 0;
        text-align: center;
    }

    #log-container {
        height: 1fr;
        border: round $primary;
        padding: 0;
        margin: 0 0 1 0;
        background: $surface;
        overflow-y: auto;
    }

    #log-output {
        height: auto;
        min-height: 1;
        background: $surface;
        padding: 1;
    }

    .log-line {
        height: auto;
        min-height: 1;
        color: $text;
        background: transparent;
    }

    .log-line-success {
        color: $success;
        text-style: bold;
    }

    .log-line-error {
        color: $error;
        text-style: bold;
    }

    .log-line-warning {
        color: $warning;
    }

    .log-line-info {
        color: $primary;
    }

    .help-text {
        text-align: center;
        color: $text-muted;
        margin: 0;
    }
    """

    # Reactive properties
    is_completed = reactive(False)
    operation_result = reactive(None)

    def __init__(
        self,
        target: str,
        operation: str,
        package_manager: str,
        vim_manager: VimManager
    ):
        super().__init__()
        self.target = target
        self.operation = operation
        self.package_manager = package_manager
        self.vim_manager = vim_manager
        self.log_lines = []

    def compose(self) -> ComposeResult:
        """Compose the progress modal."""
        with Container(classes="modal-container-lg"):
            title_prefix = "Installing" if self.operation == "install" else "Uninstalling"
            title_target = "NeoVim" if self.target == "neovim" else "LazyVim"
            yield Static(f"📦 {title_prefix} {title_target}", id="modal-title")

            yield Rule()

            # Operation log area
            yield Label("📋 Operation Logs:", classes="log-line-info")
            with ScrollableContainer(id="log-container"):
                with Vertical(id="log-output"):
                    yield Static("Starting operation...", classes="log-line")

            yield Rule()
            yield Label("ESC=Close | J/K=Scroll", classes="help-text")

    def on_mount(self) -> None:
        """Start operation when mounted."""
        self._start_operation()

    def add_log_line(self, message: str, log_type: str = "normal") -> None:
        """Add a line to the log display.

        Args:
            message: The message to display
            log_type: Type of log (normal, success, error, warning, info)
        """
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")

            # Add timestamp if not already present
            if not message.startswith('['):
                log_line = f"[{timestamp}] {message}"
            else:
                log_line = message

            # Track log lines
            self.log_lines.append(log_line)

            # Determine CSS class
            css_class = "log-line"
            if log_type == "success":
                css_class = "log-line-success"
            elif log_type == "error":
                css_class = "log-line-error"
            elif log_type == "warning":
                css_class = "log-line-warning"
            elif log_type == "info":
                css_class = "log-line-info"

            # Add to log output
            log_container = self.query_one("#log-output", Vertical)
            log_container.mount(Static(log_line, classes=css_class))

            # Keep only last 200 lines
            if len(self.log_lines) > 200:
                self.log_lines = self.log_lines[-200:]
                log_widgets = log_container.children
                if len(log_widgets) > 200:
                    log_widgets[0].remove()

            # Auto-scroll to bottom
            content_area = self.query_one("#log-container", ScrollableContainer)
            content_area.scroll_end(animate=False)

        except Exception as e:
            logger.error(f"Failed to add log line: {e}")

    def add_log_line_safe(self, message: str, log_type: str = "normal") -> None:
        """Thread-safe wrapper for add_log_line."""
        try:
            import threading
            if threading.current_thread() is threading.main_thread():
                self.add_log_line(message, log_type)
            else:
                def safe_add():
                    self.add_log_line(message, log_type)
                self.app.call_from_thread(safe_add)
        except Exception as e:
            logger.error(f"Failed to add log line (safe): {e}")

    def progress_callback(self, level: str, message: str) -> None:
        """Callback for installation progress updates.

        Args:
            level: Log level (info, success, error, warning)
            message: Log message
        """
        # Map level to log type
        log_type_map = {
            "info": "info",
            "success": "success",
            "error": "error",
            "warning": "warning"
        }
        log_type = log_type_map.get(level.lower(), "normal")

        self.add_log_line_safe(message, log_type)

    @work(exclusive=True, thread=True)
    async def _start_operation(self) -> None:
        """Execute the requested operation."""
        try:
            verb = "installation" if self.operation == "install" else "removal"
            self.add_log_line(f"Starting {verb} process...", "info")

            if self.target == "neovim":
                if self.operation == "install":
                    await self._install_neovim()
                else:
                    await self._uninstall_neovim()
            else:
                if self.operation == "install":
                    await self._install_lazyvim()
                else:
                    await self._uninstall_lazyvim()

        except Exception as e:
            logger.error(f"Operation failed with exception: {e}", exc_info=True)
            self.add_log_line_safe(f"Critical error: {str(e)}", "error")
            self.operation_result = {"success": False, "message": str(e)}
        finally:
            self.is_completed = True

    async def _install_neovim(self) -> None:
        """Install NeoVim."""
        self.add_log_line_safe("Installing NeoVim...", "info")

        # Check dependencies first
        self.add_log_line_safe("Checking dependencies...", "info")
        deps = await VimManager.check_dependencies()

        if not deps.get("git"):
            self.add_log_line_safe("Warning: Git not found, may be needed for some operations", "warning")

        # Execute installation
        result = await VimManager.install_neovim(
            self.package_manager,
            self.progress_callback
        )

        self.operation_result = result

        if result["success"]:
            self.add_log_line_safe("", "normal")
            self.add_log_line_safe("=" * 50, "normal")
            self.add_log_line_safe(f"✅ NeoVim {result.get('version', 'unknown')} installed successfully!", "success")
            self.add_log_line_safe("=" * 50, "normal")
        else:
            self.add_log_line_safe("", "normal")
            self.add_log_line_safe("=" * 50, "normal")
            self.add_log_line_safe("❌ NeoVim installation failed", "error")
            self.add_log_line_safe(f"Error: {result.get('message', 'Unknown error')}", "error")
            self.add_log_line_safe("=" * 50, "normal")

    async def _install_lazyvim(self) -> None:
        """Install LazyVim."""
        self.add_log_line_safe("Installing LazyVim...", "info")

        # Check dependencies first
        self.add_log_line_safe("Checking dependencies...", "info")
        deps = await VimManager.check_dependencies()

        if not deps.get("git"):
            self.add_log_line_safe("Error: Git is required for LazyVim installation", "error")
            self.operation_result = {"success": False, "message": "Git not found"}
            return

        if not deps.get("network"):
            self.add_log_line_safe("Warning: Network check failed, installation may fail", "warning")

        self.add_log_line_safe("Dependencies OK", "success")

        # Execute installation
        result = await VimManager.install_lazyvim(self.progress_callback)

        self.operation_result = result

        if result["success"]:
            self.add_log_line_safe("", "normal")
            self.add_log_line_safe("=" * 50, "normal")
            self.add_log_line_safe("✅ LazyVim installed successfully!", "success")
            if result.get("backup_path"):
                self.add_log_line_safe(f"📁 Backup created: {result['backup_path']}", "info")
            self.add_log_line_safe("", "normal")
            self.add_log_line_safe("📝 Next steps:", "info")
            self.add_log_line_safe("  1. Run 'nvim' to start NeoVim", "info")
            self.add_log_line_safe("  2. LazyVim will automatically install plugins", "info")
            self.add_log_line_safe("  3. This may take 5-10 minutes on first launch", "info")
            self.add_log_line_safe("=" * 50, "normal")
        else:
            self.add_log_line_safe("", "normal")
            self.add_log_line_safe("=" * 50, "normal")
            self.add_log_line_safe("❌ LazyVim installation failed", "error")
            self.add_log_line_safe(f"Error: {result.get('message', 'Unknown error')}", "error")

            # Rollback if needed
            if result.get("backup_path"):
                self.add_log_line_safe("", "normal")
                self.add_log_line_safe("Attempting rollback...", "warning")
                rollback_result = await VimManager.rollback_installation(result["backup_path"])
                if rollback_result["success"]:
                    self.add_log_line_safe("✅ Configuration restored from backup", "success")
                else:
                    self.add_log_line_safe(f"❌ Rollback failed: {rollback_result['message']}", "error")

            self.add_log_line_safe("=" * 50, "normal")

    async def _uninstall_neovim(self) -> None:
        """Uninstall NeoVim."""
        self.add_log_line_safe("Removing NeoVim...", "info")

        result = await VimManager.uninstall_neovim(
            self.package_manager,
            self.progress_callback
        )

        self.operation_result = result

        if result["success"]:
            self.add_log_line_safe("", "normal")
            self.add_log_line_safe("=" * 50, "normal")
            self.add_log_line_safe("✅ NeoVim removed successfully!", "success")
            self.add_log_line_safe("=" * 50, "normal")
        else:
            self.add_log_line_safe("", "normal")
            self.add_log_line_safe("=" * 50, "normal")
            self.add_log_line_safe("❌ NeoVim removal failed", "error")
            self.add_log_line_safe(f"Error: {result.get('message', 'Unknown error')}", "error")
            self.add_log_line_safe("=" * 50, "normal")

    async def _uninstall_lazyvim(self) -> None:
        """Uninstall LazyVim configuration."""
        self.add_log_line_safe("Removing LazyVim configuration...", "info")

        result = await VimManager.uninstall_lazyvim(self.progress_callback)
        self.operation_result = result

        if result["success"]:
            self.add_log_line_safe("", "normal")
            self.add_log_line_safe("=" * 50, "normal")
            self.add_log_line_safe("✅ LazyVim configuration removed", "success")
            backup = result.get("backup_path")
            if backup:
                self.add_log_line_safe(f"📁 Backup created at: {backup}", "info")
            self.add_log_line_safe("=" * 50, "normal")
        else:
            self.add_log_line_safe("", "normal")
            self.add_log_line_safe("=" * 50, "normal")
            self.add_log_line_safe("❌ LazyVim removal failed", "error")
            self.add_log_line_safe(f"Error: {result.get('message', 'Unknown error')}", "error")
            self.add_log_line_safe("=" * 50, "normal")

    def action_close(self) -> None:
        """Close the modal if operation finished."""
        if self.is_completed:
            self.dismiss(self.operation_result or {"success": False, "message": "Unknown result"})

    def action_scroll_down(self) -> None:
        """Scroll log down."""
        try:
            content_area = self.query_one("#log-container", ScrollableContainer)
            content_area.scroll_down(animate=False)
        except Exception:
            pass

    def action_scroll_up(self) -> None:
        """Scroll log up."""
        try:
            content_area = self.query_one("#log-container", ScrollableContainer)
            content_area.scroll_up(animate=False)
        except Exception:
            pass

    def on_key(self, event) -> None:
        """Handle key events."""
        if event.key == "escape":
            if self.is_completed:
                self.action_close()
