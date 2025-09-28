"""Simplified Installation Log Manager for the Linux System Initializer."""

from datetime import datetime
from typing import Optional, Callable
from enum import Enum

from .logger import get_utils_logger


class LogLevel(Enum):
    """Log level enumeration."""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    SUCCESS = "SUCCESS"
    DEBUG = "DEBUG"


class InstallationLogManager:
    """Simplified installation log manager that only outputs to UI display."""

    def __init__(self, ui_callback: Optional[Callable[[str, str], None]] = None):
        """Initialize the simplified log manager.

        Args:
            ui_callback: Optional callback function to display logs in UI (message, log_type)
        """
        # Initialize logger for internal use
        self.logger = get_utils_logger("log_manager")

        # UI callback for displaying logs in progress modal
        self.ui_callback = ui_callback

        # Session tracking (simplified)
        self.session_active = False
        self.session_id = None
        self.package_manager = None

    def start_session(self, package_manager: str) -> str:
        """Start a new installation session.

        Args:
            package_manager: Package manager being used

        Returns:
            Session ID
        """
        timestamp = datetime.now()
        self.session_id = timestamp.strftime("%Y%m%d_%H%M%S")
        self.package_manager = package_manager
        self.session_active = True

        self._log_to_ui(f"Installation session started - package manager: {package_manager}", "info")

        return self.session_id

    def end_session(self) -> None:
        """End the current installation session."""
        if not self.session_active:
            return

        self._log_to_ui("Installation session completed", "info")

        self.session_active = False
        self.session_id = None
        self.package_manager = None

    def log(self, level: LogLevel, message: str, command: str = None,
            output: str = None, error: str = None, application: str = None,
            action: str = None) -> None:
        """Add a log entry to the session (displays in UI only).

        Args:
            level: Log level
            message: Log message
            command: Command that was executed (optional)
            output: Command output (optional)
            error: Error message if any (optional)
            application: Application name (optional)
            action: Action performed (optional)
        """
        if not self.session_active:
            return

        # Format message with additional info if provided
        full_message = message
        if application:
            full_message = f"{application}: {message}"

        # Convert LogLevel to UI log type
        log_type = self._convert_log_level_to_ui_type(level)

        # Send basic message to UI first
        self._log_to_ui(full_message, log_type)

        # If we have command details, log them separately for better readability
        if command:
            self._log_to_ui(f"Command: {command}", "info")

        if output and output.strip():
            # Split output into lines and send each line
            output_lines = output.strip().split('\n')
            for line in output_lines[-20:]:  # Only show last 20 lines to avoid flooding
                if line.strip():  # Only log non-empty lines
                    self._log_to_ui(f"  {line}", "normal")

        if error and error.strip():
            # Split error into lines and send each line
            error_lines = error.strip().split('\n')
            for line in error_lines:
                if line.strip():  # Only log non-empty lines
                    self._log_to_ui(f"  {line}", "error")

        # Also log to internal logger for debugging
        detailed_log = f"[{level.value}] {full_message}"
        if command:
            detailed_log += f" | Command: {command}"
        if output:
            detailed_log += f" | Output: {output[:200]}..."
        if error:
            detailed_log += f" | Error: {error[:200]}..."

        self.logger.info(detailed_log)

    def set_total_apps(self, count: int) -> None:
        """Set the total number of applications to be processed.

        Args:
            count: Total application count
        """
        if self.session_active:
            self._log_to_ui(f"Starting installation session - {count} tasks", "info")

    def set_ui_callback(self, callback: Callable[[str, str], None]) -> None:
        """Set the UI callback function for displaying logs.

        Args:
            callback: Function that takes (message, log_type) and displays in UI
        """
        self.ui_callback = callback

    def _log_to_ui(self, message: str, log_type: str) -> None:
        """Send log message to UI if callback is available.

        Args:
            message: Message to display
            log_type: Type of log (info, success, error, warning, normal)
        """
        if self.ui_callback:
            try:
                self.ui_callback(message, log_type)
            except Exception as e:
                self.logger.error(f"Failed to send log to UI: {e}")

    def _convert_log_level_to_ui_type(self, level: LogLevel) -> str:
        """Convert LogLevel enum to UI log type string.

        Args:
            level: LogLevel enum value

        Returns:
            UI log type string
        """
        conversion_map = {
            LogLevel.SUCCESS: "success",
            LogLevel.ERROR: "error",
            LogLevel.WARNING: "warning",
            LogLevel.INFO: "info",
            LogLevel.DEBUG: "normal"
        }
        return conversion_map.get(level, "normal")