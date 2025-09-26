"""Application Installation Progress Modal."""

from textual import on, work
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.screen import ModalScreen
from textual.widgets import Button, Static, Rule, Label, ProgressBar
from textual.reactive import reactive
from textual.events import Key
from typing import List, Dict, Optional
import asyncio
from datetime import datetime
from ...utils.log_manager import LogLevel
from ...modules.sudo_manager import SudoManager


class AppInstallProgressModal(ModalScreen):
    """Modal screen for showing application installation/uninstallation progress."""
    
    BINDINGS = [
        ("escape", "close", "Close"),
        ("r", "retry_failed", "Retry Failed"),
        ("j", "scroll_down", "Scroll Down"),
        ("k", "scroll_up", "Scroll Up"),
    ]
    
    # CSS styles consistent with Package module
    CSS = """
    AppInstallProgressModal {
        align: center middle;
    }

    #modal-title {
        text-style: bold;
        color: $text;
        margin: 0 0 1 0;
        text-align: center;
        height: auto;
        min-height: 1;
    }

    #log-container {
        height: 1fr;
        border: round $primary;
        padding: 0;
        margin: 0 0 1 0;
        background: $surface;
    }

    #log-container {
        height: 1fr;
        border: round $primary;
        padding: 0;
        margin: 0 0 1 0;
        background: $surface;
        overflow-y: auto;
        scrollbar-size: 1 1;
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

    .section-divider {
        height: 1;
        color: #7dd3fc;
        margin: 0;
    }

    .info-key {
        color: $text;
        text-style: bold;
        margin: 0 0 1 0;
        background: $surface;
    }

    .status-pending {
        color: $text-muted;
    }

    .status-running {
        color: $warning;
        text-style: bold;
    }

    .status-success {
        color: $success;
        text-style: bold;
    }

    .status-failed {
        color: $error;
        text-style: bold;
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
    """
    
    # Reactive properties
    current_task_index = reactive(0)
    all_completed = reactive(False)
    has_failed_tasks = reactive(False)
    
    def __init__(self, actions: List[Dict], app_installer, sudo_manager: Optional[SudoManager] = None):
        try:
            super().__init__()
            print(f"DEBUG: AppInstallProgressModal __init__ called with {len(actions)} actions")
            print(f"DEBUG: sudo_manager provided: {sudo_manager is not None}")
            print(f"DEBUG: app_installer: {app_installer}")

            self.actions = actions
            self.app_installer = app_installer
            self.sudo_manager = sudo_manager  # Optional sudo manager

            # Add log lines tracking like APT modal
            self.log_lines = []

            # Initialize independent log file system
            self._init_independent_log_system()

            print("DEBUG: Basic attributes set successfully")

            # Task tracking
            self.tasks = []
            for i, action in enumerate(actions):
                print(f"DEBUG: Processing action {i}: {action}")
                app = action["application"]
                task_name = f"{'Installing' if action['action'] == 'install' else 'Uninstalling'} {app.name}"
                self.tasks.append({
                    "name": task_name,
                    "action": action,
                    "status": "pending",  # pending, running, success, failed
                    "progress": 0,
                    "message": "",
                })
                print(f"DEBUG: Task {i} added: {task_name}")

            print(f"DEBUG: AppInstallProgressModal __init__ completed successfully with {len(self.tasks)} tasks")
        except Exception as e:
            print(f"CRITICAL ERROR in AppInstallProgressModal __init__: {e}")
            import traceback
            traceback.print_exc()
            raise

    def _init_independent_log_system(self) -> None:
        """Initialize the independent log file system for app progress."""
        try:
            from datetime import datetime
            import os
            from pathlib import Path

            # Use project root logs directory instead of user config
            self.progress_logs_dir = Path("logs")
            self.progress_logs_dir.mkdir(exist_ok=True)

            # Generate unique log file name with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Get package manager name for prefix
            package_manager = getattr(self.app_installer, 'package_manager', 'unknown') or 'unknown'

            # Generate filename without app names (cleaner approach)
            log_filename = f"app_install_{package_manager}_{timestamp}.log"
            self.progress_log_file = self.progress_logs_dir / log_filename

            # Initialize log file with header
            self._write_to_log_file(f"=== App Installation Progress Log ===")
            self._write_to_log_file(f"Session started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self._write_to_log_file(f"Total tasks: {len(self.actions)}")
            self._write_to_log_file(f"Log file: {self.progress_log_file}")
            self._write_to_log_file("=" * 50)

            print(f"DEBUG: Independent log system initialized: {self.progress_log_file}")

        except Exception as e:
            print(f"WARNING: Failed to initialize independent log system: {e}")
            self.progress_log_file = None

    def _write_to_log_file(self, message: str) -> None:
        """Write a message to the independent log file.

        Args:
            message: Message to write to the log file
        """
        try:
            if self.progress_log_file:
                from datetime import datetime
                import re

                # Only convert \r to \n for specific apt progress patterns
                if 'Reading database' in message and '\r' in message:
                    # This is apt progress with carriage returns, convert to separate lines
                    clean_message = message.replace('\r', '\n')
                else:
                    # For other content, just remove \r but keep content
                    clean_message = message.replace('\r', '')

                # Remove ANSI escape sequences
                clean_message = re.sub(r'\x1b\[[0-9;]*m', '', clean_message)
                clean_message = re.sub(r'\x1b\[[0-9;]*[A-Za-z]', '', clean_message)
                clean_message = clean_message.strip()

                timestamp = datetime.now().strftime("%H:%M:%S")

                # Handle potential multiple lines
                lines = clean_message.split('\n') if '\n' in clean_message else [clean_message]

                with open(self.progress_log_file, 'a', encoding='utf-8') as f:
                    for line in lines:
                        line = line.strip()
                        if line:  # Only write non-empty lines
                            # Don't add timestamp if line already has one or is a separator
                            if line.startswith("[") or line.startswith("="):
                                log_entry = line
                            else:
                                log_entry = f"[{timestamp}] {line}"
                            f.write(log_entry + "\n")
                    f.flush()  # Ensure immediate writing
        except Exception as e:
            print(f"Failed to write to log file: {e}")

    def add_log_line(self, message: str, log_type: str = "normal") -> None:
        """Add a line to the log display using Static components.

        Args:
            message: The message to display
            log_type: Type of log line (normal, success, error, warning, info)
        """
        try:
            from datetime import datetime

            # Clean message and handle potential Reading database progress lines
            clean_message = message.strip()

            # Only split by newlines for Reading database progress
            if 'Reading database' in clean_message and '\n' in clean_message:
                message_lines = clean_message.split('\n')
            else:
                message_lines = [clean_message]

            for line in message_lines:
                line = line.strip()
                if not line:  # Skip empty lines
                    continue

                # Add timestamp only if not already present
                if not line.startswith('[') and not line.startswith('='):
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    log_line = f"[{timestamp}] {line}"
                else:
                    log_line = line

                # Track log lines for memory management
                self.log_lines.append(log_line)

                # Determine CSS class based on log type
                css_class = "log-line"
                if log_type == "success":
                    css_class = "log-line-success"
                elif log_type == "error":
                    css_class = "log-line-error"
                elif log_type == "warning":
                    css_class = "log-line-warning"
                elif log_type == "info":
                    css_class = "log-line-info"

                # Add to log output container
                log_container = self.query_one("#log-output", Vertical)
                log_container.mount(Static(log_line, classes=css_class))

            # Keep only last 100 lines to prevent memory issues
            if len(self.log_lines) > 100:
                self.log_lines = self.log_lines[-100:]
                # Remove old log widgets
                log_widgets = log_container.children
                if len(log_widgets) > 100:
                    log_widgets[0].remove()

            # Auto-scroll to bottom
            content_area = self.query_one("#log-container", ScrollableContainer)
            content_area.scroll_end(animate=False)

        except Exception as e:
            # Fallback: print to console if UI update fails
            print(f"Failed to add log line: {e}")
            # Try to continue without crashing

    def add_log_line_safe(self, message: str, log_type: str = "normal") -> None:
        """Thread-safe wrapper for add_log_line that also writes to independent log file."""
        try:
            # Clean message before processing
            clean_message = message.strip()

            # Always write clean message to independent log file first (thread-safe)
            self._write_to_log_file(clean_message)

            # Check if we're in the main thread for UI update
            import threading
            if threading.current_thread() is threading.main_thread():
                # We're in the main thread, call directly
                self.add_log_line(clean_message, log_type)
            else:
                # We're in a worker thread, use call_from_thread
                def safe_add():
                    self.add_log_line(clean_message, log_type)
                self.app.call_from_thread(safe_add)
        except Exception as e:
            # Fallback: print to console and try to log to file
            print(f"Failed to add log line (safe): {message} - {e}")
            try:
                self._write_to_log_file(f"ERROR: Failed to display log: {message}")
            except:
                pass

    def _append_log(self, log_widget, message: str) -> None:
        """Legacy method for compatibility - determine log type from Rich markup and forward to add_log_line.

        Args:
            log_widget: Unused (kept for compatibility)
            message: Message with potential Rich markup
        """
        # Parse Rich markup to determine log type
        log_type = "normal"
        clean_message = message.strip()

        # Remove Rich markup and determine type
        import re

        # Check for color patterns in Rich markup
        if re.search(r'\[green\]|\[success\]', clean_message):
            log_type = "success"
        elif re.search(r'\[red\]|\[error\]', clean_message):
            log_type = "error"
        elif re.search(r'\[yellow\]|\[warning\]', clean_message):
            log_type = "warning"
        elif re.search(r'\[blue\]|\[cyan\]|\[primary\]', clean_message):
            log_type = "info"

        # Clean up Rich markup for display
        clean_message = re.sub(r'\[/?[^\]]*\]', '', clean_message)

        self.add_log_line_safe(clean_message, log_type)

    def on_mount(self) -> None:
        """Initialize the screen and start processing."""
        self._start_processing()
    
    def can_focus(self) -> bool:
        """Return True to allow this modal to receive focus."""
        return True
    
    @property
    def is_modal(self) -> bool:
        """Mark this as a modal screen."""
        return True
    
    @on(Key)
    def handle_key_event(self, event: Key) -> None:
        """Handle key events using @on decorator."""
        if event.key == "escape" and self.all_completed:
            self.dismiss()
            event.prevent_default()
            event.stop()
        elif event.key == "r" and self.has_failed_tasks and self.all_completed:
            self.action_retry_failed()
            event.prevent_default()
            event.stop()
        elif event.key == "j":
            self.action_scroll_down()
            event.prevent_default()
            event.stop()
        elif event.key == "k":
            self.action_scroll_up()
            event.prevent_default()
            event.stop()
    
    def compose(self) -> ComposeResult:
        """Compose the modal interface."""
        try:
            print("DEBUG: Starting compose() method")
            print(f"DEBUG: Tasks count: {len(self.tasks)}")

            with Container(classes="modal-container-lg"):
                yield Static("📦 Application Installation Progress", id="modal-title")

                print("DEBUG: Basic elements created")

                yield Rule(classes="section-divider")

                # Installation log area
                print("DEBUG: Creating log output")
                yield Label("📋 Installation Logs:", classes="info-key")
                with ScrollableContainer(id="log-container"):
                    with Vertical(id="log-output"):
                        # Add an initial log line to ensure container works
                        yield Static("Starting installation process...", classes="log-line")

                print("DEBUG: Log output created")

                # After log output completion, no operation button area is added, all changed to keyboard shortcuts
                print("DEBUG: All elements created, no button container")

                # Bottom help area inside modal - consistent with other modals
                yield Rule(classes="section-divider")
                yield Label("ESC=Close | R=Retry Failed | J/K=Scroll", classes="help-text")

            print("DEBUG: compose() method completed successfully")
        except Exception as e:
            print(f"CRITICAL ERROR in compose(): {e}")
            import traceback
            traceback.print_exc()
            raise
    
    @work(exclusive=True, thread=True)
    async def _start_processing(self) -> None:
        """Process all installation/uninstallation tasks."""
        # Set up log UI callback to connect app installer logs to UI
        self.app_installer.set_log_ui_callback(self.add_log_line_safe)

        # Start logging session (simplified)
        try:
            session_id = self.app_installer.start_logging_session()
            self.app_installer.set_total_applications(len(self.tasks))

            # Log session start
            self.app_installer.log_installation_event(
                LogLevel.INFO,
                f"Starting installation session - {len(self.tasks)} tasks",
                action="session_start"
            )

            timestamp = datetime.now().strftime("%H:%M:%S")
            # Use thread-safe log method
            self.add_log_line_safe(f"📝 Log session started: {session_id}")
            # Also write detailed task list to independent log
            self._write_to_log_file("Task list:")
            for i, task in enumerate(self.tasks):
                self._write_to_log_file(f"  {i+1}. {task['name']}")
            self._write_to_log_file("=" * 30)

        except Exception as e:
            self._append_log(None, f"[yellow]⚠️ Log initialization failed: {e}[/yellow]")

        # Initial permission check for sudo commands
        has_sudo_commands = any(
            self._command_needs_sudo(task) for task in self.tasks
        )

        if has_sudo_commands:
            timestamp = datetime.now().strftime("%H:%M:%S")
            self._append_log(None,f"[{timestamp}] Checking sudo permissions...")

            if self.sudo_manager and self.sudo_manager.is_verified():
                self._append_log(None,"[green]✅ Sudo permissions verified, using cached permissions[/green]")
            elif not self.sudo_manager:
                # No sudo manager, fallback to original check method
                if not self.app_installer.check_sudo_available():
                    self._append_log(None,"[red]❌ Sudo permissions required but sudo is unavailable or user lacks permissions[/red]")
                    self._append_log(None,"[yellow]Please ensure:[/yellow]")
                    self._append_log(None,"[yellow]1. System has sudo installed[/yellow]")
                    self._append_log(None,"[yellow]2. Current user is in sudo group[/yellow]")
                    self._append_log(None,"[yellow]3. Sudo authentication is cached (try running 'sudo -v' manually)[/yellow]")

                    # Mark all tasks as failed
                    for task in self.tasks:
                        task["status"] = "failed"
                        task["message"] = "Sudo permissions unavailable"
                        self._update_task_display(self.tasks.index(task))

                    self.all_completed = True
                    self._enable_close_button()
                    return
                else:
                    self._append_log(None,"[green]✅ Sudo permissions verified[/green]")
            else:
                # Has sudo manager but not verified, this situation should not happen
                self._append_log(None,"[red]❌ Sudo permission manager not properly initialized[/red]")
                # Mark all tasks as failed
                for task in self.tasks:
                    task["status"] = "failed"
                    task["message"] = "Sudo permission manager not initialized"
                    self._update_task_display(self.tasks.index(task))

                self.all_completed = True
                self._enable_close_button()
                return

        # Check if APT update is needed and execute it once for the session
        if self.app_installer.needs_apt_update():
            timestamp = datetime.now().strftime("%H:%M:%S")
            self._append_log(None, f"[{timestamp}] Checking if APT update is needed...")
            self._append_log(None, "[blue]📦 APT update required for current session[/blue]")

            apt_update_command = self.app_installer.get_apt_update_command()
            if apt_update_command:
                self._append_log(None, f"[dim]Executing: {apt_update_command}[/dim]")

                try:
                    # Execute APT update with progress feedback
                    success, output = await self._execute_command_with_sudo_support(apt_update_command, "log_widget")

                    if success:
                        self.app_installer.mark_apt_update_executed()
                        self._append_log(None, "[green]✅ APT update completed successfully[/green]")
                        self._append_log(None, "[dim]  Package list updated for current session[/dim]")
                    else:
                        self._append_log(None, f"[yellow]⚠️ APT update failed: {output}[/yellow]")
                        self._append_log(None, "[yellow]  Continuing with installation, but packages may be outdated[/yellow]")
                        # Don't fail completely, just warn and continue

                except Exception as e:
                    self._append_log(None, f"[yellow]⚠️ APT update error: {str(e)}[/yellow]")
                    self._append_log(None, "[yellow]  Continuing with installation[/yellow]")

                self._append_log(None, "")  # Add blank line for readability
        else:
            if self.app_installer.package_manager in ["apt", "apt-get"]:
                self._append_log(None, "[dim]📦 APT update already executed in current session, skipping[/dim]")
                self._append_log(None, "")  # Add blank line for readability

        for i, task in enumerate(self.tasks):
            self.current_task_index = i

            # Update task status
            task["status"] = "running"
            self._update_task_display(i)

            # Log start
            timestamp = datetime.now().strftime("%H:%M:%S")
            self._append_log(None,f"[{timestamp}] Starting: {task['name']}")

            # Get the action and application
            action = task["action"]
            app = action["application"]

            # Simulate progress updates
            task["progress"] = 20
            self._update_progress(i, task["progress"])

            try:
                if action["action"] == "install":
                    # Get install command
                    command = self.app_installer.get_install_command(app)
                    if command:
                        # Check if this specific command needs sudo
                        if self._command_needs_sudo_for_task(task):
                            self._append_log(None,f"[yellow]⚠️ Administrator privileges required for installation command[/yellow]")

                        self._append_log(None,f"[dim]Executing command: {command}[/dim]")

                        # Execute installation
                        initial_progress = 40
                        task["progress"] = initial_progress
                        self._update_progress(i, initial_progress)

                        # Create progress callback for this task
                        def update_install_progress(percentage):
                            # Map command progress to task progress range (40-70%)
                            task_progress = initial_progress + int((percentage / 100) * 30)
                            task["progress"] = min(task_progress, 70)
                            self._update_progress(i, task["progress"])

                        success, output = await self._execute_command_with_sudo_support(command, "log_widget", update_install_progress)
                        
                        if success:
                            task["progress"] = 70
                            self._update_progress(i, task["progress"])

                            # Execute post-install if any
                            if app.post_install:
                                self._append_log(None,f"[dim]Executing post-install configuration: {app.post_install}[/dim]")

                                # Create progress callback for post-install (70-100%)
                                def update_postinstall_progress(percentage):
                                    task_progress = 70 + int((percentage / 100) * 30)
                                    task["progress"] = min(task_progress, 100)
                                    self._update_progress(i, task["progress"])

                                post_success, post_output = await self._execute_command_with_sudo_support(app.post_install, "log_widget", update_postinstall_progress)
                                if not post_success:
                                    self._append_log(None,f"[yellow]⚠️ Post-install configuration failed: {post_output}[/yellow]")

                            task["status"] = "success"
                            task["progress"] = 100
                            self._append_log(None,f"[green]✅ {app.name} installed successfully[/green]")

                            # Log successful installation
                            self.app_installer.log_installation_event(
                                LogLevel.SUCCESS,
                                f"{app.name} installed successfully",
                                application=app.name,
                                action="install",
                                command=command,
                                output=output
                            )

                            # Save installation status to persist state
                            if self.app_installer.save_installation_status(app.name, True):
                                self._append_log(None,f"[dim]  📝 Saved installation status for {app.name}[/dim]")
                            else:
                                self._append_log(None,f"[yellow]  ⚠️ Failed to save installation status for {app.name}[/yellow]")

                            # Immediately refresh main menu app page after successful installation
                            self._refresh_main_menu_app_page(f"{app.name} installed successfully")
                        else:
                            task["status"] = "failed"
                            task["message"] = output

                            # Log failed installation
                            self.app_installer.log_installation_event(
                                LogLevel.ERROR,
                                f"{app.name} installation failed",
                                application=app.name,
                                action="install",
                                command=command,
                                error=output
                            )

                            # Generate user-friendly error analysis
                            friendly_error = self.app_installer.analyze_error_and_suggest_solution(
                                output, command, app.name
                            )

                            self._append_log(None,f"[red]❌ {app.name} installation failed[/red]")
                            self._append_log(None,"")

                            # Show raw error output first for debugging
                            if output and len(output.strip()) > 0:
                                self._append_log(None,"[red]🔍 Raw error output:[/red]")
                                for line in output.split('\n')[-5:]:  # Last 5 lines of raw output
                                    if line.strip():
                                        self._append_log(None,f"[dim]  {line}[/dim]")
                                self._append_log(None,"")

                            # Generate user-friendly error analysis
                            friendly_error = self.app_installer.analyze_error_and_suggest_solution(
                                output, command, app.name
                            )

                            # Display friendly error with proper formatting
                            for line in friendly_error.split('\n'):
                                if line.strip():
                                    if line.startswith('❌'):
                                        self._append_log(None,f"[red]{line}[/red]")
                                    elif line.startswith('📋'):
                                        self._append_log(None,f"[blue]{line}[/blue]")
                                    elif line.startswith('🔍'):
                                        self._append_log(None,f"[dim]{line}[/dim]")
                                    elif line.startswith('  •'):
                                        self._append_log(None,f"[yellow]{line}[/yellow]")
                                    else:
                                        self._append_log(None,line)
                    else:
                        task["status"] = "failed"
                        task["message"] = "Cannot get installation command"
                        self._append_log(None,f"[red]Error: Cannot get installation command for {app.name}[/red]")
                
                else:  # uninstall
                    # Get uninstall command
                    command = self.app_installer.get_uninstall_command(app)
                    if command:
                        # Check if this specific command needs sudo
                        if self._command_needs_sudo_for_task(task):
                            self._append_log(None,f"[yellow]⚠️ Administrator privileges required for uninstallation command[/yellow]")

                        self._append_log(None,f"[dim]Executing command: {command}[/dim]")

                        # Execute uninstallation
                        initial_progress = 50
                        task["progress"] = initial_progress
                        self._update_progress(i, initial_progress)

                        # Create progress callback for this task
                        def update_uninstall_progress(percentage):
                            # Map command progress to task progress range (50-100%)
                            task_progress = initial_progress + int((percentage / 100) * 50)
                            task["progress"] = min(task_progress, 100)
                            self._update_progress(i, task["progress"])

                        success, output = await self._execute_command_with_sudo_support(command, "log_widget", update_uninstall_progress)

                        if success:
                            task["status"] = "success"
                            task["progress"] = 100
                            self._append_log(None,f"[green]✅ {app.name} uninstalled successfully[/green]")

                            # Save uninstallation status to persist state
                            if self.app_installer.save_installation_status(app.name, False):
                                self._append_log(None,f"[dim]  📝 Saved uninstall status for {app.name}[/dim]")
                            else:
                                self._append_log(None,f"[yellow]  ⚠️ Failed to save uninstall status for {app.name}[/yellow]")

                            # Immediately refresh main menu app page after successful uninstallation
                            self._refresh_main_menu_app_page(f"{app.name} uninstalled successfully")
                        else:
                            task["status"] = "failed"
                            task["message"] = output

                            # Generate user-friendly error analysis
                            friendly_error = self.app_installer.analyze_error_and_suggest_solution(
                                output, command, app.name
                            )

                            self._append_log(None,f"[red]❌ {app.name} uninstallation failed[/red]")
                            self._append_log(None,"")

                            # Show raw error output first for debugging
                            if output and len(output.strip()) > 0:
                                self._append_log(None,"[red]🔍 Raw error output:[/red]")
                                for line in output.split('\n')[-5:]:  # Last 5 lines of raw output
                                    if line.strip():
                                        self._append_log(None,f"[dim]  {line}[/dim]")
                                self._append_log(None,"")

                            # Display friendly error with proper formatting
                            for line in friendly_error.split('\n'):
                                if line.strip():
                                    if line.startswith('❌'):
                                        self._append_log(None,f"[red]{line}[/red]")
                                    elif line.startswith('📋'):
                                        self._append_log(None,f"[blue]{line}[/blue]")
                                    elif line.startswith('🔍'):
                                        self._append_log(None,f"[dim]{line}[/dim]")
                                    elif line.startswith('  •'):
                                        self._append_log(None,f"[yellow]{line}[/yellow]")
                                    else:
                                        self._append_log(None,line)
                    else:
                        task["status"] = "failed"
                        task["message"] = "Cannot get uninstall command"
                        self._append_log(None,f"[red]Error: Cannot get uninstall command for {app.name}[/red]")
            
            except Exception as e:
                task["status"] = "failed"
                task["message"] = str(e)
                self._append_log(None,f"[red]Error: {str(e)}[/red]")
            
            self._update_task_display(i)
            self._update_progress(i, task["progress"])
        
        # All tasks completed
        self.all_completed = True
        self._enable_close_button()
        
        # Log completion
        timestamp = datetime.now().strftime("%H:%M:%S")
        successful = sum(1 for t in self.tasks if t["status"] == "success")
        failed = sum(1 for t in self.tasks if t["status"] == "failed")
        
        self._append_log(None,"")
        self._append_log(None,f"[{timestamp}] " + "="*50)
        self._append_log(None,f"[bold]Installation completed: {successful} successful, {failed} failed[/bold]")
        
        if failed == 0:
            self._append_log(None,"[green]✅ All tasks completed successfully![/green]")
        else:
            self._append_log(None,"[yellow]⚠️ Some tasks failed, please check logs for details.[/yellow]")

        # End logging session
        try:
            self.app_installer.log_installation_event(
                LogLevel.INFO,
                f"Installation session ended - Success: {successful}, Failed: {failed}",
                action="session_end"
            )

            # End logging session
            self.app_installer.end_logging_session()

        except Exception as e:
            self._append_log(None,f"[yellow]⚠️ Log session end failed: {e}[/yellow]")
    
    def _command_needs_sudo(self, task: Dict) -> bool:
        """Check if task needs sudo permissions.

        Args:
            task: Task dictionary

        Returns:
            True if sudo permissions needed, False otherwise
        """
        action = task["action"]
        app = action["application"]

        if action["action"] == "install":
            command = self.app_installer.get_install_command(app)
        else:  # uninstall
            command = self.app_installer.get_uninstall_command(app)

        return command and "sudo" in command

    def _command_needs_sudo_for_task(self, task: Dict) -> bool:
        """Check if current task command needs sudo permissions.

        Args:
            task: Task dictionary

        Returns:
            True if sudo privileges are required, False otherwise
        """
        action = task["action"]
        app = action["application"]

        if action["action"] == "install":
            command = self.app_installer.get_install_command(app)
        else:  # uninstall
            command = self.app_installer.get_uninstall_command(app)

        return command and "sudo" in command

    async def _execute_command_with_sudo_support(self, command: str, log_widget=None, progress_callback=None) -> tuple:
        """Execute command with sudo support.

        Args:
            command: Command to execute
            log_widget: TextArea widget for log display
            progress_callback: Progress callback function

        Returns:
            (success, output) tuple
        """
        try:
            # Check if sudo manager exists and command requires sudo
            if self.sudo_manager and self.sudo_manager.is_sudo_required(command):
                if not self.sudo_manager.is_verified():
                    error_msg = "Sudo permissions not verified"
                    if log_widget:
                        self._append_log(None,f"[red]❌ {error_msg}[/red]")
                    return False, error_msg

                # Use sudo manager to execute command, but need to implement real-time output support
                return await self._execute_sudo_command_with_output(command, None, progress_callback)
            else:
                # Use original execution method
                return await self._execute_command_async(command, None, progress_callback)

        except Exception as e:
            error_msg = f"Command execution failed: {str(e)}"
            if log_widget:
                self._append_log(None,f"[red]❌ {error_msg}[/red]")
            return False, error_msg

    async def _execute_sudo_command_with_output(self, command: str, log_widget=None, progress_callback=None) -> tuple:
        """Execute sudo command with real-time output and progress tracking.

        Args:
            command: Command to execute with sudo
            log_widget: TextArea widget for real-time output display
            progress_callback: Function to call for progress updates

        Returns:
            Tuple of (success, output/error message)
        """
        try:
            # If root user, remove sudo part
            if self.sudo_manager.is_root_user():
                if self.sudo_manager.is_sudo_required(command):
                    clean_command = self.sudo_manager._remove_sudo_from_command(command)
                    if log_widget:
                        self._append_log(None,f"[dim]🔑 Root user executing: {clean_command}[/dim]")
                    return await self._execute_command_async(clean_command, None, progress_callback)
                else:
                    return await self._execute_command_async(command, None, progress_callback)

            # Non-root user, need to use sudo password
            password = self.sudo_manager._decrypt_password(self.sudo_manager._password)
            if not password:
                error_msg = "Failed to decrypt sudo password"
                if log_widget:
                    self._append_log(None,f"[red]❌ {error_msg}[/red]")
                return False, error_msg

            if log_widget:
                self._append_log(None,f"[dim]🔐 Executing with sudo: {command}[/dim]")

            # Create subprocess with password input
            process = await asyncio.create_subprocess_shell(
                command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,  # Redirect stderr to stdout for unified output
                text=False,  # Use binary mode to avoid "text must be False" error
                shell=True
            )

            output_lines = []
            error_occurred = False
            progress_percentage = 0

            # Send password first
            if password:
                process.stdin.write(f"{password}\n".encode('utf-8'))
                await process.stdin.drain()

            # Read output lines for real-time display
            try:
                line_count = 0
                while True:
                    line_bytes = await asyncio.wait_for(
                        process.stdout.readline(),
                        timeout=30.0  # 30-second timeout per line
                    )

                    if not line_bytes:  # EOF reached
                        break

                    # Decode bytes to string and clean control characters
                    try:
                        line = line_bytes.decode('utf-8').strip()
                        # Only convert \r to \n for specific apt progress patterns
                        if 'Reading database' in line and '\r' in line:
                            # This is apt progress with carriage returns, convert to separate lines
                            line = line.replace('\r', '\n')
                        else:
                            # For other content, just remove \r but keep content
                            line = line.replace('\r', '')

                        # Remove ANSI escape sequences
                        import re
                        line = re.sub(r'\x1b\[[0-9;]*m', '', line)
                        line = re.sub(r'\x1b\[[0-9;]*[A-Za-z]', '', line)
                        line = line.strip()
                    except UnicodeDecodeError:
                        line = line_bytes.decode('utf-8', errors='ignore').strip()
                        # Apply same logic for error case
                        if 'Reading database' in line and '\r' in line:
                            line = line.replace('\r', '\n')
                        else:
                            line = line.replace('\r', '')

                    if line:
                        # Split line by newlines if any were created from \r conversion
                        line_parts = line.split('\n')
                        for part in line_parts:
                            part = part.strip()
                            if part:  # Only add non-empty parts
                                output_lines.append(part)
                        line_count += 1

                        # Smart progress estimation based on output patterns
                        new_progress = self._estimate_progress_from_output(line, line_count, command)
                        if new_progress > progress_percentage:
                            progress_percentage = min(new_progress, 95)  # Cap at 95% until completion
                            if progress_callback:
                                progress_callback(progress_percentage)

                        # Real-time log display if widget provided
                        if log_widget:
                            # Color-code different types of output
                            if any(keyword in line.lower() for keyword in ['error', 'failed', 'permission denied', 'access denied']):
                                self.add_log_line_safe(f"  📄 {line}", "error")
                                error_occurred = True
                            elif any(keyword in line.lower() for keyword in ['warning', 'warn']):
                                self.add_log_line_safe(f"  📄 {line}", "warning")
                            elif any(keyword in line.lower() for keyword in ['installing', 'downloading']):
                                self.add_log_line_safe(f"  📦 {line}", "info")
                            elif any(keyword in line.lower() for keyword in ['success', 'complete', 'done']):
                                self.add_log_line_safe(f"  ✅ {line}", "success")
                            elif any(keyword in line.lower() for keyword in ['processing', 'configuring', 'setting up']):
                                self.add_log_line_safe(f"  ⚙️ {line}", "info")
                            else:
                                self.add_log_line_safe(f"  📄 {line}", "normal")
                        else:
                            # No log widget, always display real-time output
                            if any(keyword in line.lower() for keyword in ['error', 'failed', 'permission denied', 'access denied']):
                                self.add_log_line_safe(f"  📄 {line}", "error")
                                error_occurred = True
                            elif any(keyword in line.lower() for keyword in ['warning', 'warn']):
                                self.add_log_line_safe(f"  📄 {line}", "warning")
                            elif any(keyword in line.lower() for keyword in ['installing', 'downloading']):
                                self.add_log_line_safe(f"  📦 {line}", "info")
                            elif any(keyword in line.lower() for keyword in ['success', 'complete', 'done']):
                                self.add_log_line_safe(f"  ✅ {line}", "success")
                            elif any(keyword in line.lower() for keyword in ['processing', 'configuring', 'setting up']):
                                self.add_log_line_safe(f"  ⚙️ {line}", "info")
                            else:
                                self.add_log_line_safe(f"  📄 {line}", "normal")

                        # Small delay to prevent UI flooding
                        await asyncio.sleep(0.1)

            except asyncio.TimeoutError:
                # If readline times out, continue to check process status
                pass

            # Close stdin and wait for process completion
            if process.stdin:
                process.stdin.close()
                await process.stdin.wait_closed()

            # Wait for process completion with overall timeout
            try:
                await asyncio.wait_for(process.wait(), timeout=270.0)  # 4.5 minutes for process completion
            except asyncio.TimeoutError:
                # Kill the process if it times out
                process.terminate()
                await process.wait()
                error_msg = "Command execution timeout (4.5 minutes)"
                if log_widget:
                    self._append_log(None,f"[red]❌ {error_msg}[/red]")
                return False, error_msg

            # Command completed - set progress to 100%
            if progress_callback:
                progress_callback(100)

            # Check return code
            if process.returncode == 0:
                # Success
                if not output_lines:
                    return True, "Command executed successfully"
                else:
                    # Return last few lines as summary
                    summary_lines = output_lines[-3:] if len(output_lines) > 3 else output_lines
                    return True, "\n".join(summary_lines)
            else:
                # Failure - provide detailed error information
                if log_widget:
                    self._append_log(None,f"[red]❌ Command failed with exit code: {process.returncode}[/red]")

                if error_occurred or output_lines:
                    # Extract error lines for detailed reporting
                    error_lines = [line for line in output_lines if any(keyword in line.lower() for keyword in
                                 ['error', 'failed', 'permission denied', 'access denied', 'cannot', 'unable'])]
                    if error_lines:
                        detailed_error = "\n".join(error_lines[-3:])  # Last 3 error lines
                        if log_widget:
                            self._append_log(None,f"[red]🔍 Error details: {detailed_error}[/red]")
                        return False, detailed_error
                    else:
                        # No specific error lines, return last output lines
                        last_output = "\n".join(output_lines[-2:]) if output_lines else f"Command failed with exit code: {process.returncode}"
                        if log_widget:
                            self._append_log(None,f"[red]📋 Last output: {last_output}[/red]")
                        return False, last_output
                else:
                    error_msg = f"Command failed with exit code: {process.returncode}"
                    if log_widget:
                        self._append_log(None,f"[red]❌ {error_msg}[/red]")
                    return False, error_msg

        except Exception as e:
            error_msg = f"Sudo command execution error: {str(e)}"
            if log_widget:
                self._append_log(None,f"[red]❌ {error_msg}[/red]")
            return False, error_msg

    async def _execute_command_async(self, command: str, log_widget=None, progress_callback=None) -> tuple:
        """Execute a command asynchronously with real-time output streaming and progress tracking.

        Args:
            command: Command to execute
            log_widget: TextArea widget for real-time output display
            progress_callback: Function to call for progress updates (percentage: int)

        Returns:
            Tuple of (success, output/error message)
        """
        try:
            # Create subprocess for command execution
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,  # Redirect stderr to stdout for unified output
                text=False,  # Use binary mode to avoid "text must be False" error
                env=None,  # Inherit environment variables
                shell=True
            )

            output_lines = []
            error_occurred = False
            progress_percentage = 0

            # Read output line by line for real-time display
            try:
                line_count = 0
                while True:
                    line_bytes = await asyncio.wait_for(
                        process.stdout.readline(),
                        timeout=30.0  # 30-second timeout per line
                    )

                    if not line_bytes:  # EOF reached
                        break

                    # Decode bytes to string and clean control characters
                    try:
                        line = line_bytes.decode('utf-8').strip()
                        # Only convert \r to \n for specific apt progress patterns
                        if 'Reading database' in line and '\r' in line:
                            # This is apt progress with carriage returns, convert to separate lines
                            line = line.replace('\r', '\n')
                        else:
                            # For other content, just remove \r but keep content
                            line = line.replace('\r', '')

                        # Remove ANSI escape sequences
                        import re
                        line = re.sub(r'\x1b\[[0-9;]*m', '', line)
                        line = re.sub(r'\x1b\[[0-9;]*[A-Za-z]', '', line)
                        line = line.strip()
                    except UnicodeDecodeError:
                        line = line_bytes.decode('utf-8', errors='ignore').strip()
                        # Apply same logic for error case
                        if 'Reading database' in line and '\r' in line:
                            line = line.replace('\r', '\n')
                        else:
                            line = line.replace('\r', '')

                    if line:
                        # Split line by newlines if any were created from \r conversion
                        line_parts = line.split('\n')
                        for part in line_parts:
                            part = part.strip()
                            if part:  # Only add non-empty parts
                                output_lines.append(part)
                        line_count += 1

                        # Smart progress estimation based on output patterns
                        new_progress = self._estimate_progress_from_output(line, line_count, command)
                        if new_progress > progress_percentage:
                            progress_percentage = min(new_progress, 95)  # Cap at 95% until completion
                            if progress_callback:
                                progress_callback(progress_percentage)

                        # Real-time log display if widget provided
                        if log_widget:
                            # Color-code different types of output
                            if any(keyword in line.lower() for keyword in ['error', 'failed', 'permission denied', 'access denied', 'cannot', 'unable']):
                                self.add_log_line_safe(f"  📄 {line}", "error")
                                error_occurred = True
                            elif any(keyword in line.lower() for keyword in ['warning', 'warn']):
                                self.add_log_line_safe(f"  📄 {line}", "warning")
                            elif any(keyword in line.lower() for keyword in ['installing', 'downloading']):
                                self.add_log_line_safe(f"  📦 {line}", "info")
                            elif any(keyword in line.lower() for keyword in ['success', 'complete', 'done']):
                                self.add_log_line_safe(f"  ✅ {line}", "success")
                            elif any(keyword in line.lower() for keyword in ['processing', 'configuring', 'setting up']):
                                self.add_log_line_safe(f"  ⚙️ {line}", "info")
                            else:
                                self.add_log_line_safe(f"  📄 {line}", "normal")
                        else:
                            # No log widget, always display real-time output
                            if any(keyword in line.lower() for keyword in ['error', 'failed', 'permission denied', 'access denied', 'cannot', 'unable']):
                                self.add_log_line_safe(f"  📄 {line}", "error")
                                error_occurred = True
                            elif any(keyword in line.lower() for keyword in ['warning', 'warn']):
                                self.add_log_line_safe(f"  📄 {line}", "warning")
                            elif any(keyword in line.lower() for keyword in ['installing', 'downloading']):
                                self.add_log_line_safe(f"  📦 {line}", "info")
                            elif any(keyword in line.lower() for keyword in ['success', 'complete', 'done']):
                                self.add_log_line_safe(f"  ✅ {line}", "success")
                            elif any(keyword in line.lower() for keyword in ['processing', 'configuring', 'setting up']):
                                self.add_log_line_safe(f"  ⚙️ {line}", "info")
                            else:
                                self.add_log_line_safe(f"  📄 {line}", "normal")

                        # Small delay to prevent UI flooding
                        await asyncio.sleep(0.1)

            except asyncio.TimeoutError:
                # If readline times out, continue to check process status
                pass

            # Wait for process completion with overall timeout
            try:
                await asyncio.wait_for(process.wait(), timeout=270.0)  # 4.5 minutes for process completion
            except asyncio.TimeoutError:
                # Kill the process if it times out
                process.terminate()
                await process.wait()
                error_msg = "Command execution timeout (4.5 minutes)"
                if log_widget:
                    self._append_log(None,f"[red]❌ {error_msg}[/red]")
                return False, error_msg

            # Command completed - set progress to 100%
            if progress_callback:
                progress_callback(100)

            # Check return code
            if process.returncode == 0:
                # Success
                if not output_lines:
                    return True, "Command executed successfully"
                else:
                    # Return last few lines as summary
                    summary_lines = output_lines[-3:] if len(output_lines) > 3 else output_lines
                    return True, "\n".join(summary_lines)
            else:
                # Failure - provide detailed error information
                if log_widget:
                    self._append_log(None,f"[red]❌ Command failed with exit code: {process.returncode}[/red]")

                if error_occurred or output_lines:
                    # Extract error lines for detailed reporting
                    error_lines = [line for line in output_lines if any(keyword in line.lower() for keyword in
                                 ['error', 'failed', 'permission denied', 'access denied', 'cannot', 'unable', 'not found', 'no such'])]
                    if error_lines:
                        detailed_error = "\n".join(error_lines[-3:])  # Last 3 error lines
                        if log_widget:
                            self._append_log(None,f"[red]🔍 Error details: {detailed_error}[/red]")
                        return False, detailed_error
                    else:
                        # No specific error lines, return last output lines
                        last_output = "\n".join(output_lines[-2:]) if output_lines else f"Command failed with exit code: {process.returncode}"
                        if log_widget:
                            self._append_log(None,f"[red]📋 Last output: {last_output}[/red]")
                        return False, last_output
                else:
                    error_msg = f"Command failed with exit code: {process.returncode}"
                    if log_widget:
                        self._append_log(None,f"[red]❌ {error_msg}[/red]")
                    return False, error_msg

        except FileNotFoundError:
            error_msg = "Command not found or cannot execute"
            if log_widget:
                self._append_log(None,f"[red]❌ {error_msg}[/red]")
            return False, error_msg
        except PermissionError:
            error_msg = "Permission denied, cannot execute command"
            if log_widget:
                self._append_log(None,f"[red]❌ {error_msg}[/red]")
            return False, error_msg
        except Exception as e:
            error_msg = f"Execution error: {str(e)}"
            if log_widget:
                self._append_log(None,f"[red]❌ {error_msg}[/red]")
            return False, error_msg

    def _estimate_progress_from_output(self, line: str, line_count: int, command: str) -> int:
        """Estimate progress percentage based on command output patterns.

        Args:
            line: Current output line
            line_count: Total lines processed so far
            command: The command being executed

        Returns:
            Estimated progress percentage (0-100)
        """
        line_lower = line.lower()

        # Progress indicators for different package managers
        progress_patterns = {
            # APT progress patterns
            'reading package lists': 10,
            'building dependency tree': 15,
            'reading state information': 20,
            'the following new packages will be installed': 25,
            'need to get': 30,
            'get:': min(30 + (line_count * 2), 60),  # Download progress
            'fetched': 65,
            'unpacking': min(65 + (line_count * 2), 80),  # Unpacking progress
            'setting up': min(80 + (line_count * 2), 90),  # Setup progress
            'processing triggers': 90,

            # YUM/DNF progress patterns
            'resolving dependencies': 15,
            'checking for conflicts': 20,
            'downloading packages': min(25 + (line_count * 3), 60),
            'installing': min(60 + (line_count * 3), 85),
            'cleanup': 90,
            'complete!': 95,

            # Pacman progress patterns
            'checking dependencies': 15,
            'checking for conflicting packages': 20,
            'downloading required keys': 25,
            'checking package integrity': 30,
            'loading package files': 35,
            'checking available disk space': 40,
            'installing': min(45 + (line_count * 4), 85),
            'running post-transaction hooks': 90,

            # Generic patterns
            'downloading': min(20 + (line_count * 2), 50),
            'extracting': min(50 + (line_count * 3), 70),
            'configuring': min(70 + (line_count * 2), 85),
            'done': 95,
        }

        # Check for specific progress indicators
        for pattern, progress in progress_patterns.items():
            if pattern in line_lower:
                return progress

        # Percentage-based progress (look for "x%" patterns)
        import re
        percentage_match = re.search(r'(\d+)%', line)
        if percentage_match:
            percentage = int(percentage_match.group(1))
            # Scale percentage based on estimated completion stage
            if 'download' in line_lower:
                return min(30 + (percentage * 0.3), 60)  # Download phase: 30-60%
            elif 'install' in line_lower or 'setup' in line_lower:
                return min(60 + (percentage * 0.3), 90)  # Install phase: 60-90%
            else:
                return min(20 + (percentage * 0.7), 95)  # General: 20-95%

        # Fallback: gradual progress based on line count and command type
        if 'install' in command.lower():
            base_progress = min(10 + (line_count * 1.5), 85)
        elif 'remove' in command.lower() or 'uninstall' in command.lower():
            base_progress = min(20 + (line_count * 3), 85)  # Uninstall is usually faster
        else:
            base_progress = min(5 + (line_count * 2), 80)

        return int(base_progress)
    
    def _update_task_display(self, index: int) -> None:
        """Update task display - simplified without task list UI."""
        # No UI task displays to update anymore
        pass
    
    def _update_progress(self, task_index: int, progress: int) -> None:
        """Update progress - simplified without progress bars."""
        # No UI progress bars to update anymore
        pass
    
    def _enable_close_button(self) -> None:
        """Enable keyboard shortcuts after tasks completion (original button functionality)."""
        # Check if there are any failed tasks
        failed_tasks = [task for task in self.tasks if task["status"] == "failed"]
        if failed_tasks:
            self.has_failed_tasks = True
    
    def action_retry_failed(self) -> None:
        """Handle retry failed tasks action (both button and R key)."""
        if self.has_failed_tasks and self.all_completed:
            self._start_retry_process()

    def _start_retry_process(self) -> None:
        """Start the retry process for failed tasks."""
        # No longer need to query for log widget - use add_log_line directly

        # Find failed tasks
        failed_tasks = [task for task in self.tasks if task["status"] == "failed"]
        if not failed_tasks:
            self._append_log(None, "[yellow]No failed tasks to retry[/yellow]")
            return

        # Log retry start
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._append_log(None,"")
        self._append_log(None,f"[{timestamp}] " + "="*30)
        self._append_log(None,f"[bold blue]🔄 Starting retry for {len(failed_tasks)} failed tasks[/bold blue]")
        self._append_log(None,"="*50)

        # Reset failed tasks status
        for task in failed_tasks:
            task["status"] = "pending"
            task["progress"] = 0
            task["message"] = ""

        # Reset modal state
        self.all_completed = False
        self.has_failed_tasks = False

        # Start retry processing (pure keyboard operation, no button state management)
        self._start_retry_processing(failed_tasks)

    @work(exclusive=True, thread=True)
    async def _start_retry_processing(self, retry_tasks: List[Dict]) -> None:
        """Process retry tasks."""
        # No longer need to query for log widget - use add_log_line directly

        for task in retry_tasks:
            task_index = self.tasks.index(task)
            self.current_task_index = task_index

            # Update task status
            task["status"] = "running"
            self._update_task_display(task_index)

            # Log start
            timestamp = datetime.now().strftime("%H:%M:%S")
            self._append_log(None,f"[{timestamp}] Retry: {task['name']}")

            # Get the action and application
            action = task["action"]
            app = action["application"]

            # Reset progress
            task["progress"] = 20
            self._update_progress(task_index, task["progress"])

            try:
                if action["action"] == "install":
                    # Get install command
                    command = self.app_installer.get_install_command(app)
                    if command:
                        # Check if this specific command needs sudo
                        if self._command_needs_sudo_for_task(task):
                            self._append_log(None,f"[yellow]⚠️ Administrator privileges required for installation command[/yellow]")

                        self._append_log(None,f"[dim]Executing command: {command}[/dim]")

                        # Execute installation
                        task["progress"] = 40
                        self._update_progress(task_index, task["progress"])

                        success, output = await self._execute_command_with_sudo_support(command, "log_widget")

                        if success:
                            task["progress"] = 70
                            self._update_progress(task_index, task["progress"])

                            # Execute post-install if any
                            if app.post_install:
                                self._append_log(None,f"[dim]Executing post-install configuration: {app.post_install}[/dim]")
                                post_success, post_output = await self._execute_command_with_sudo_support(app.post_install, "log_widget")
                                if not post_success:
                                    self._append_log(None,f"[yellow]⚠️ Post-install configuration failed: {post_output}[/yellow]")

                            task["status"] = "success"
                            task["progress"] = 100
                            self._append_log(None,f"[green]✅ {app.name} re-installed successfully[/green]")

                            # Save installation status to persist state
                            if self.app_installer.save_installation_status(app.name, True):
                                self._append_log(None,f"[dim]  📝 Saved installation status for {app.name}[/dim]")
                            else:
                                self._append_log(None,f"[yellow]  ⚠️ Failed to save installation status for {app.name}[/yellow]")

                            # Immediately refresh main menu app page after successful re-installation
                            self._refresh_main_menu_app_page(f"{app.name} re-installed successfully")
                        else:
                            task["status"] = "failed"
                            task["message"] = output

                            # Generate user-friendly error analysis
                            friendly_error = self.app_installer.analyze_error_and_suggest_solution(
                                output, command, app.name
                            )

                            self._append_log(None,f"[red]❌ {app.name} retry installation failed[/red]")
                            self._append_log(None,"")

                            # Show raw error output first for debugging
                            if output and len(output.strip()) > 0:
                                self._append_log(None,"[red]🔍 Raw error output:[/red]")
                                for line in output.split('\n')[-5:]:  # Last 5 lines of raw output
                                    if line.strip():
                                        self._append_log(None,f"[dim]  {line}[/dim]")
                                self._append_log(None,"")

                            # Display friendly error with proper formatting
                            for line in friendly_error.split('\n'):
                                if line.strip():
                                    if line.startswith('❌'):
                                        self._append_log(None,f"[red]{line}[/red]")
                                    elif line.startswith('📋'):
                                        self._append_log(None,f"[blue]{line}[/blue]")
                                    elif line.startswith('🔍'):
                                        self._append_log(None,f"[dim]{line}[/dim]")
                                    elif line.startswith('  •'):
                                        self._append_log(None,f"[yellow]{line}[/yellow]")
                                    else:
                                        self._append_log(None,line)
                    else:
                        task["status"] = "failed"
                        task["message"] = "Cannot get installation command"
                        self._append_log(None,f"[red]Error: Cannot get installation command for {app.name}[/red]")

                else:  # uninstall
                    # Get uninstall command
                    command = self.app_installer.get_uninstall_command(app)
                    if command:
                        # Check if this specific command needs sudo
                        if self._command_needs_sudo_for_task(task):
                            self._append_log(None,f"[yellow]⚠️ Administrator privileges required for uninstallation command[/yellow]")

                        self._append_log(None,f"[dim]Executing command: {command}[/dim]")

                        # Execute uninstallation
                        task["progress"] = 50
                        self._update_progress(task_index, task["progress"])

                        success, output = await self._execute_command_with_sudo_support(command, "log_widget")

                        if success:
                            task["status"] = "success"
                            task["progress"] = 100
                            self._append_log(None,f"[green]✅ {app.name} re-uninstalled successfully[/green]")

                            # Save uninstallation status to persist state
                            if self.app_installer.save_installation_status(app.name, False):
                                self._append_log(None,f"[dim]  📝 Saved uninstall status for {app.name}[/dim]")
                            else:
                                self._append_log(None,f"[yellow]  ⚠️ Failed to save uninstall status for {app.name}[/yellow]")

                            # Immediately refresh main menu app page after successful re-uninstallation
                            self._refresh_main_menu_app_page(f"{app.name} re-uninstalled successfully")
                        else:
                            task["status"] = "failed"
                            task["message"] = output

                            # Generate user-friendly error analysis
                            friendly_error = self.app_installer.analyze_error_and_suggest_solution(
                                output, command, app.name
                            )

                            self._append_log(None,f"[red]❌ {app.name} retry uninstallation failed[/red]")
                            self._append_log(None,"")

                            # Show raw error output first for debugging
                            if output and len(output.strip()) > 0:
                                self._append_log(None,"[red]🔍 Raw error output:[/red]")
                                for line in output.split('\n')[-5:]:  # Last 5 lines of raw output
                                    if line.strip():
                                        self._append_log(None,f"[dim]  {line}[/dim]")
                                self._append_log(None,"")

                            # Display friendly error with proper formatting
                            for line in friendly_error.split('\n'):
                                if line.strip():
                                    if line.startswith('❌'):
                                        self._append_log(None,f"[red]{line}[/red]")
                                    elif line.startswith('📋'):
                                        self._append_log(None,f"[blue]{line}[/blue]")
                                    elif line.startswith('🔍'):
                                        self._append_log(None,f"[dim]{line}[/dim]")
                                    elif line.startswith('  •'):
                                        self._append_log(None,f"[yellow]{line}[/yellow]")
                                    else:
                                        self._append_log(None,line)
                    else:
                        task["status"] = "failed"
                        task["message"] = "Cannot get uninstall command"
                        self._append_log(None,f"[red]Error: Cannot get uninstall command for {app.name}[/red]")

            except Exception as e:
                task["status"] = "failed"
                task["message"] = str(e)
                self._append_log(None,f"[red]Error: {str(e)}[/red]")

            self._update_task_display(task_index)
            self._update_progress(task_index, task["progress"])

        # Retry completed
        self.all_completed = True
        self._enable_close_button()

        # Log completion
        timestamp = datetime.now().strftime("%H:%M:%S")
        retry_successful = sum(1 for t in retry_tasks if t["status"] == "success")
        retry_failed = sum(1 for t in retry_tasks if t["status"] == "failed")

        self._append_log(None,"")
        self._append_log(None,f"[{timestamp}] " + "="*50)
        self._append_log(None,f"[bold]Retry completed: {retry_successful} successful, {retry_failed} failed[/bold]")

        if retry_failed == 0:
            self._append_log(None,"[green]🎉 All retry tasks completed successfully![/green]")
        else:
            self._append_log(None,f"[yellow]⚠️ {retry_failed} tasks still failed, can retry again.[/yellow]")
    
    def action_dismiss(self) -> None:
        """Dismiss the modal (only if completed)."""
        if self.all_completed:
            # Write session summary to log file before dismissing
            self._write_session_summary()
            self.dismiss()

    def _write_session_summary(self) -> None:
        """Write session summary to the independent log file."""
        try:
            from datetime import datetime

            # Count results
            successful_count = sum(1 for task in self.tasks if task["status"] == "success")
            failed_count = sum(1 for task in self.tasks if task["status"] == "failed")

            self._write_to_log_file("=" * 50)
            self._write_to_log_file("=== Session Summary ===")
            self._write_to_log_file(f"Session ended: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self._write_to_log_file(f"Total tasks: {len(self.tasks)}")
            self._write_to_log_file(f"Successful: {successful_count}")
            self._write_to_log_file(f"Failed: {failed_count}")

            if failed_count > 0:
                self._write_to_log_file("Failed tasks:")
                for task in self.tasks:
                    if task["status"] == "failed":
                        self._write_to_log_file(f"  - {task['name']}: {task.get('message', 'No details')}")

            self._write_to_log_file("=" * 50)
            print(f"DEBUG: Session summary written to: {self.progress_log_file}")
        except Exception as e:
            print(f"Failed to write session summary: {e}")

    def action_scroll_down(self) -> None:
        """Scroll the log output down."""
        try:
            content_area = self.query_one("#log-container", ScrollableContainer)
            content_area.scroll_down(animate=False)
        except Exception:
            # If container not available yet, ignore
            pass

    def action_scroll_up(self) -> None:
        """Scroll the log output up."""
        try:
            content_area = self.query_one("#log-container", ScrollableContainer)
            content_area.scroll_up(animate=False)
        except Exception:
            # If container not available yet, ignore
            pass

    def _refresh_main_menu_app_page(self, operation_message: str) -> None:
        """刷新主菜单的应用安装页面以显示最新状态。

        Args:
            operation_message: 操作完成消息，用于日志记录
        """
        try:
            if hasattr(self, '_main_menu_ref') and self._main_menu_ref:
                self._append_log(None, f"[dim]  🔄 Refreshing main menu app page after operation[/dim]")

                # 使用call_from_thread确保在主线程中执行UI更新
                def safe_refresh():
                    try:
                        self._main_menu_ref.refresh_and_reset_app_page()
                        # 记录成功日志应该通过主菜单的日志系统，避免线程问题
                    except Exception as e:
                        # 如果刷新失败，记录错误但不影响主流程
                        print(f"Failed to refresh main menu: {str(e)}")

                # 安全地调用主菜单刷新
                self.app.call_from_thread(safe_refresh)

                self._append_log(None, f"[dim]  ✅ Main menu refresh requested successfully[/dim]")
            else:
                self._append_log(None, f"[yellow]  ⚠️ No main menu reference available for refresh[/yellow]")
        except Exception as e:
            self._append_log(None, f"[yellow]  ⚠️ Failed to refresh main menu: {str(e)}[/yellow]")
            # 记录错误但不重新抛出，确保不影响主流程