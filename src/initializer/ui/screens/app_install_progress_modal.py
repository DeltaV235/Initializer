"""Application Installation Progress Modal."""

from textual import on, work
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.screen import ModalScreen
from textual.widgets import Button, Static, Rule, Label, ProgressBar, TextArea
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

    #log-output {
        height: 100%;
        padding: 1;
        background: $surface;
        border: none;
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

    def _append_log(self, log_widget: TextArea, message: str) -> None:
        """Append a log message to the TextArea widget.

        Args:
            log_widget: The TextArea widget to append to
            message: The message to append (supports Rich markup)
        """
        current_text = log_widget.text
        if current_text:
            # Add newline if there's existing content
            new_text = current_text + "\n" + message
        else:
            new_text = message
        log_widget.text = new_text
        # Scroll to bottom to show latest message
        log_widget.scroll_end(animate=False)

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
                with Container(id="log-container"):
                    yield TextArea(
                        id="log-output",
                        read_only=True,
                        show_line_numbers=False,
                        soft_wrap=True,
                        language=None
                    )

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
        log_widget = self.query_one("#log-output", TextArea)

        # Start logging session
        try:
            # Gather basic system info for logging
            system_info = {
                "package_manager": self.app_installer.package_manager or "unknown",
                "task_count": len(self.tasks),
                "timestamp": datetime.now().isoformat()
            }

            session_id = self.app_installer.start_logging_session(system_info)
            self.app_installer.set_total_applications(len(self.tasks))

            # Log session start
            self.app_installer.log_installation_event(
                LogLevel.INFO,
                f"Starting installation session - {len(self.tasks)} tasks",
                action="session_start"
            )

            timestamp = datetime.now().strftime("%H:%M:%S")
            self._append_log(log_widget,f"[{timestamp}] 📝 Log session started: {session_id}")

        except Exception as e:
            self._append_log(log_widget,f"[yellow]⚠️ Log initialization failed: {e}[/yellow]")

        # Initial permission check for sudo commands
        has_sudo_commands = any(
            self._command_needs_sudo(task) for task in self.tasks
        )

        if has_sudo_commands:
            timestamp = datetime.now().strftime("%H:%M:%S")
            self._append_log(log_widget,f"[{timestamp}] Checking sudo permissions...")

            if self.sudo_manager and self.sudo_manager.is_verified():
                self._append_log(log_widget,"[green]✅ Sudo permissions verified, using cached permissions[/green]")
            elif not self.sudo_manager:
                # No sudo manager, fallback to original check method
                if not self.app_installer.check_sudo_available():
                    self._append_log(log_widget,"[red]❌ Sudo permissions required but sudo is unavailable or user lacks permissions[/red]")
                    self._append_log(log_widget,"[yellow]Please ensure:[/yellow]")
                    self._append_log(log_widget,"[yellow]1. System has sudo installed[/yellow]")
                    self._append_log(log_widget,"[yellow]2. Current user is in sudo group[/yellow]")
                    self._append_log(log_widget,"[yellow]3. Sudo authentication is cached (try running 'sudo -v' manually)[/yellow]")

                    # Mark all tasks as failed
                    for task in self.tasks:
                        task["status"] = "failed"
                        task["message"] = "Sudo permissions unavailable"
                        self._update_task_display(self.tasks.index(task))

                    self.all_completed = True
                    self._enable_close_button()
                    return
                else:
                    self._append_log(log_widget,"[green]✅ Sudo permissions verified[/green]")
            else:
                # Has sudo manager but not verified, this situation should not happen
                self._append_log(log_widget,"[red]❌ Sudo permission manager not properly initialized[/red]")
                # Mark all tasks as failed
                for task in self.tasks:
                    task["status"] = "failed"
                    task["message"] = "Sudo permission manager not initialized"
                    self._update_task_display(self.tasks.index(task))

                self.all_completed = True
                self._enable_close_button()
                return

        for i, task in enumerate(self.tasks):
            self.current_task_index = i

            # Update task status
            task["status"] = "running"
            self._update_task_display(i)

            # Log start
            timestamp = datetime.now().strftime("%H:%M:%S")
            self._append_log(log_widget,f"[{timestamp}] Starting: {task['name']}")

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
                            self._append_log(log_widget,f"[yellow]⚠️ Administrator privileges required for installation command[/yellow]")

                        self._append_log(log_widget,f"[dim]Executing command: {command}[/dim]")

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

                        success, output = await self._execute_command_with_sudo_support(command, log_widget, update_install_progress)
                        
                        if success:
                            task["progress"] = 70
                            self._update_progress(i, task["progress"])

                            # Execute post-install if any
                            if app.post_install:
                                self._append_log(log_widget,f"[dim]Executing post-install configuration: {app.post_install}[/dim]")

                                # Create progress callback for post-install (70-100%)
                                def update_postinstall_progress(percentage):
                                    task_progress = 70 + int((percentage / 100) * 30)
                                    task["progress"] = min(task_progress, 100)
                                    self._update_progress(i, task["progress"])

                                post_success, post_output = await self._execute_command_with_sudo_support(app.post_install, log_widget, update_postinstall_progress)
                                if not post_success:
                                    self._append_log(log_widget,f"[yellow]⚠️ Post-install configuration failed: {post_output}[/yellow]")

                            task["status"] = "success"
                            task["progress"] = 100
                            self._append_log(log_widget,f"[green]✅ {app.name} installed successfully[/green]")

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
                                self._append_log(log_widget,f"[dim]  📝 Saved installation status for {app.name}[/dim]")
                            else:
                                self._append_log(log_widget,f"[yellow]  ⚠️ Failed to save installation status for {app.name}[/yellow]")
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

                            self._append_log(log_widget,f"[red]❌ {app.name} installation failed[/red]")
                            self._append_log(log_widget,"")

                            # Show raw error output first for debugging
                            if output and len(output.strip()) > 0:
                                self._append_log(log_widget,"[red]🔍 Raw error output:[/red]")
                                for line in output.split('\n')[-5:]:  # Last 5 lines of raw output
                                    if line.strip():
                                        self._append_log(log_widget,f"[dim]  {line}[/dim]")
                                self._append_log(log_widget,"")

                            # Generate user-friendly error analysis
                            friendly_error = self.app_installer.analyze_error_and_suggest_solution(
                                output, command, app.name
                            )

                            # Display friendly error with proper formatting
                            for line in friendly_error.split('\n'):
                                if line.strip():
                                    if line.startswith('❌'):
                                        self._append_log(log_widget,f"[red]{line}[/red]")
                                    elif line.startswith('📋'):
                                        self._append_log(log_widget,f"[blue]{line}[/blue]")
                                    elif line.startswith('🔍'):
                                        self._append_log(log_widget,f"[dim]{line}[/dim]")
                                    elif line.startswith('  •'):
                                        self._append_log(log_widget,f"[yellow]{line}[/yellow]")
                                    else:
                                        self._append_log(log_widget,line)
                    else:
                        task["status"] = "failed"
                        task["message"] = "Cannot get installation command"
                        self._append_log(log_widget,f"[red]Error: Cannot get installation command for {app.name}[/red]")
                
                else:  # uninstall
                    # Get uninstall command
                    command = self.app_installer.get_uninstall_command(app)
                    if command:
                        # Check if this specific command needs sudo
                        if self._command_needs_sudo_for_task(task):
                            self._append_log(log_widget,f"[yellow]⚠️ Administrator privileges required for uninstallation command[/yellow]")

                        self._append_log(log_widget,f"[dim]Executing command: {command}[/dim]")

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

                        success, output = await self._execute_command_with_sudo_support(command, log_widget, update_uninstall_progress)

                        if success:
                            task["status"] = "success"
                            task["progress"] = 100
                            self._append_log(log_widget,f"[green]✅ {app.name} uninstalled successfully[/green]")

                            # Save uninstallation status to persist state
                            if self.app_installer.save_installation_status(app.name, False):
                                self._append_log(log_widget,f"[dim]  📝 Saved uninstall status for {app.name}[/dim]")
                            else:
                                self._append_log(log_widget,f"[yellow]  ⚠️ Failed to save uninstall status for {app.name}[/yellow]")
                        else:
                            task["status"] = "failed"
                            task["message"] = output

                            # Generate user-friendly error analysis
                            friendly_error = self.app_installer.analyze_error_and_suggest_solution(
                                output, command, app.name
                            )

                            self._append_log(log_widget,f"[red]❌ {app.name} uninstallation failed[/red]")
                            self._append_log(log_widget,"")

                            # Show raw error output first for debugging
                            if output and len(output.strip()) > 0:
                                self._append_log(log_widget,"[red]🔍 Raw error output:[/red]")
                                for line in output.split('\n')[-5:]:  # Last 5 lines of raw output
                                    if line.strip():
                                        self._append_log(log_widget,f"[dim]  {line}[/dim]")
                                self._append_log(log_widget,"")

                            # Display friendly error with proper formatting
                            for line in friendly_error.split('\n'):
                                if line.strip():
                                    if line.startswith('❌'):
                                        self._append_log(log_widget,f"[red]{line}[/red]")
                                    elif line.startswith('📋'):
                                        self._append_log(log_widget,f"[blue]{line}[/blue]")
                                    elif line.startswith('🔍'):
                                        self._append_log(log_widget,f"[dim]{line}[/dim]")
                                    elif line.startswith('  •'):
                                        self._append_log(log_widget,f"[yellow]{line}[/yellow]")
                                    else:
                                        self._append_log(log_widget,line)
                    else:
                        task["status"] = "failed"
                        task["message"] = "Cannot get uninstall command"
                        self._append_log(log_widget,f"[red]Error: Cannot get uninstall command for {app.name}[/red]")
            
            except Exception as e:
                task["status"] = "failed"
                task["message"] = str(e)
                self._append_log(log_widget,f"[red]Error: {str(e)}[/red]")
            
            self._update_task_display(i)
            self._update_progress(i, task["progress"])
        
        # All tasks completed
        self.all_completed = True
        self._enable_close_button()
        
        # Log completion
        timestamp = datetime.now().strftime("%H:%M:%S")
        successful = sum(1 for t in self.tasks if t["status"] == "success")
        failed = sum(1 for t in self.tasks if t["status"] == "failed")
        
        self._append_log(log_widget,"")
        self._append_log(log_widget,f"[{timestamp}] " + "="*50)
        self._append_log(log_widget,f"[bold]Installation completed: {successful} successful, {failed} failed[/bold]")
        
        if failed == 0:
            self._append_log(log_widget,"[green]✅ All tasks completed successfully![/green]")
        else:
            self._append_log(log_widget,"[yellow]⚠️ Some tasks failed, please check logs for details.[/yellow]")

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
            self._append_log(log_widget,f"[yellow]⚠️ Log session end failed: {e}[/yellow]")
    
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
            True如果需要sudo权限，False否则
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
                        self._append_log(log_widget,f"[red]❌ {error_msg}[/red]")
                    return False, error_msg

                # Use sudo manager to execute command, but need to implement real-time output support
                return await self._execute_sudo_command_with_output(command, log_widget, progress_callback)
            else:
                # Use original execution method
                return await self._execute_command_async(command, log_widget, progress_callback)

        except Exception as e:
            error_msg = f"Command execution failed: {str(e)}"
            if log_widget:
                self._append_log(log_widget,f"[red]❌ {error_msg}[/red]")
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
                        self._append_log(log_widget,f"[dim]🔑 Root user executing: {clean_command}[/dim]")
                    return await self._execute_command_async(clean_command, log_widget, progress_callback)
                else:
                    return await self._execute_command_async(command, log_widget, progress_callback)

            # Non-root user, need to use sudo password
            password = self.sudo_manager._decrypt_password(self.sudo_manager._password)
            if not password:
                error_msg = "Failed to decrypt sudo password"
                if log_widget:
                    self._append_log(log_widget,f"[red]❌ {error_msg}[/red]")
                return False, error_msg

            if log_widget:
                self._append_log(log_widget,f"[dim]🔐 Executing with sudo: {command}[/dim]")

            # 创建带密码输入的subprocess
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

                    # Decode bytes to string
                    try:
                        line = line_bytes.decode('utf-8').strip()
                    except UnicodeDecodeError:
                        line = line_bytes.decode('utf-8', errors='ignore').strip()

                    if line:
                        output_lines.append(line)
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
                                self._append_log(log_widget,f"[red]  📄 {line}[/red]")
                                error_occurred = True
                            elif any(keyword in line.lower() for keyword in ['warning', 'warn']):
                                self._append_log(log_widget,f"[yellow]  📄 {line}[/yellow]")
                            elif any(keyword in line.lower() for keyword in ['installing', 'downloading']):
                                self._append_log(log_widget,f"[blue]  📦 {line}[/blue]")
                            elif any(keyword in line.lower() for keyword in ['success', 'complete', 'done']):
                                self._append_log(log_widget,f"[green]  ✅ {line}[/green]")
                            elif any(keyword in line.lower() for keyword in ['processing', 'configuring', 'setting up']):
                                self._append_log(log_widget,f"[cyan]  ⚙️ {line}[/cyan]")
                            else:
                                self._append_log(log_widget,f"[dim]  📄 {line}[/dim]")

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
                    self._append_log(log_widget,f"[red]❌ {error_msg}[/red]")
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
                    self._append_log(log_widget,f"[red]❌ Command failed with exit code: {process.returncode}[/red]")

                if error_occurred or output_lines:
                    # Extract error lines for detailed reporting
                    error_lines = [line for line in output_lines if any(keyword in line.lower() for keyword in
                                 ['error', 'failed', 'permission denied', 'access denied', 'cannot', 'unable'])]
                    if error_lines:
                        detailed_error = "\n".join(error_lines[-3:])  # Last 3 error lines
                        if log_widget:
                            self._append_log(log_widget,f"[red]🔍 Error details: {detailed_error}[/red]")
                        return False, detailed_error
                    else:
                        # No specific error lines, return last output lines
                        last_output = "\n".join(output_lines[-2:]) if output_lines else f"Command failed with exit code: {process.returncode}"
                        if log_widget:
                            self._append_log(log_widget,f"[red]📋 Last output: {last_output}[/red]")
                        return False, last_output
                else:
                    error_msg = f"Command failed with exit code: {process.returncode}"
                    if log_widget:
                        self._append_log(log_widget,f"[red]❌ {error_msg}[/red]")
                    return False, error_msg

        except Exception as e:
            error_msg = f"Sudo command execution error: {str(e)}"
            if log_widget:
                self._append_log(log_widget,f"[red]❌ {error_msg}[/red]")
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

                    # Decode bytes to string
                    try:
                        line = line_bytes.decode('utf-8').strip()
                    except UnicodeDecodeError:
                        line = line_bytes.decode('utf-8', errors='ignore').strip()

                    if line:
                        output_lines.append(line)
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
                            if any(keyword in line.lower() for keyword in ['error', '错误', 'failed', '失败', 'permission denied', 'access denied', 'cannot', 'unable']):
                                self._append_log(log_widget,f"[red]  📄 {line}[/red]")
                                error_occurred = True
                            elif any(keyword in line.lower() for keyword in ['warning', 'warn']):
                                self._append_log(log_widget,f"[yellow]  📄 {line}[/yellow]")
                            elif any(keyword in line.lower() for keyword in ['installing', 'downloading']):
                                self._append_log(log_widget,f"[blue]  📦 {line}[/blue]")
                            elif any(keyword in line.lower() for keyword in ['success', 'complete', 'done']):
                                self._append_log(log_widget,f"[green]  ✅ {line}[/green]")
                            elif any(keyword in line.lower() for keyword in ['processing', 'configuring', 'setting up']):
                                self._append_log(log_widget,f"[cyan]  ⚙️ {line}[/cyan]")
                            else:
                                self._append_log(log_widget,f"[dim]  📄 {line}[/dim]")

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
                    self._append_log(log_widget,f"[red]❌ {error_msg}[/red]")
                return False, error_msg

            # Command completed - set progress to 100%
            if progress_callback:
                progress_callback(100)

            # Check return code
            if process.returncode == 0:
                # Success
                if not output_lines:
                    return True, "命令执行成功"
                else:
                    # Return last few lines as summary
                    summary_lines = output_lines[-3:] if len(output_lines) > 3 else output_lines
                    return True, "\n".join(summary_lines)
            else:
                # Failure - provide detailed error information
                if log_widget:
                    self._append_log(log_widget,f"[red]❌ Command failed with exit code: {process.returncode}[/red]")

                if error_occurred or output_lines:
                    # Extract error lines for detailed reporting
                    error_lines = [line for line in output_lines if any(keyword in line.lower() for keyword in
                                 ['error', '错误', 'failed', '失败', 'permission denied', 'access denied', 'cannot', 'unable', 'not found', 'no such'])]
                    if error_lines:
                        detailed_error = "\n".join(error_lines[-3:])  # Last 3 error lines
                        if log_widget:
                            self._append_log(log_widget,f"[red]🔍 Error details: {detailed_error}[/red]")
                        return False, detailed_error
                    else:
                        # No specific error lines, return last output lines
                        last_output = "\n".join(output_lines[-2:]) if output_lines else f"Command failed with exit code: {process.returncode}"
                        if log_widget:
                            self._append_log(log_widget,f"[red]📋 Last output: {last_output}[/red]")
                        return False, last_output
                else:
                    error_msg = f"Command failed with exit code: {process.returncode}"
                    if log_widget:
                        self._append_log(log_widget,f"[red]❌ {error_msg}[/red]")
                    return False, error_msg

        except FileNotFoundError:
            error_msg = "Command not found or cannot execute"
            if log_widget:
                self._append_log(log_widget,f"[red]❌ {error_msg}[/red]")
            return False, error_msg
        except PermissionError:
            error_msg = "Permission denied, cannot execute command"
            if log_widget:
                self._append_log(log_widget,f"[red]❌ {error_msg}[/red]")
            return False, error_msg
        except Exception as e:
            error_msg = f"Execution error: {str(e)}"
            if log_widget:
                self._append_log(log_widget,f"[red]❌ {error_msg}[/red]")
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
        """任务完成后启用键盘快捷键操作（原按钮功能）."""
        # 检查是否有失败的任务
        failed_tasks = [task for task in self.tasks if task["status"] == "failed"]
        if failed_tasks:
            self.has_failed_tasks = True
    
    def action_retry_failed(self) -> None:
        """Handle retry failed tasks action (both button and R key)."""
        if self.has_failed_tasks and self.all_completed:
            self._start_retry_process()

    def _start_retry_process(self) -> None:
        """Start the retry process for failed tasks."""
        log_widget = self.query_one("#log-output", TextArea)

        # Find failed tasks
        failed_tasks = [task for task in self.tasks if task["status"] == "failed"]
        if not failed_tasks:
            self._append_log(log_widget,"[yellow]没有失败的任务需要重试[/yellow]")
            return

        # Log retry start
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._append_log(log_widget,"")
        self._append_log(log_widget,f"[{timestamp}] " + "="*30)
        self._append_log(log_widget,f"[bold blue]🔄 开始重试 {len(failed_tasks)} 个失败任务[/bold blue]")
        self._append_log(log_widget,"="*50)

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
        log_widget = self.query_one("#log-output", TextArea)

        for task in retry_tasks:
            task_index = self.tasks.index(task)
            self.current_task_index = task_index

            # Update task status
            task["status"] = "running"
            self._update_task_display(task_index)

            # Log start
            timestamp = datetime.now().strftime("%H:%M:%S")
            self._append_log(log_widget,f"[{timestamp}] 重试: {task['name']}")

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
                            self._append_log(log_widget,f"[yellow]⚠️ Administrator privileges required for installation command[/yellow]")

                        self._append_log(log_widget,f"[dim]Executing command: {command}[/dim]")

                        # Execute installation
                        task["progress"] = 40
                        self._update_progress(task_index, task["progress"])

                        success, output = await self._execute_command_with_sudo_support(command, log_widget)

                        if success:
                            task["progress"] = 70
                            self._update_progress(task_index, task["progress"])

                            # Execute post-install if any
                            if app.post_install:
                                self._append_log(log_widget,f"[dim]Executing post-install configuration: {app.post_install}[/dim]")
                                post_success, post_output = await self._execute_command_with_sudo_support(app.post_install, log_widget)
                                if not post_success:
                                    self._append_log(log_widget,f"[yellow]⚠️ Post-install configuration failed: {post_output}[/yellow]")

                            task["status"] = "success"
                            task["progress"] = 100
                            self._append_log(log_widget,f"[green]✅ {app.name} re-installed successfully[/green]")

                            # Save installation status to persist state
                            if self.app_installer.save_installation_status(app.name, True):
                                self._append_log(log_widget,f"[dim]  📝 Saved installation status for {app.name}[/dim]")
                            else:
                                self._append_log(log_widget,f"[yellow]  ⚠️ Failed to save installation status for {app.name}[/yellow]")
                        else:
                            task["status"] = "failed"
                            task["message"] = output

                            # Generate user-friendly error analysis
                            friendly_error = self.app_installer.analyze_error_and_suggest_solution(
                                output, command, app.name
                            )

                            self._append_log(log_widget,f"[red]❌ {app.name} retry installation failed[/red]")
                            self._append_log(log_widget,"")

                            # Show raw error output first for debugging
                            if output and len(output.strip()) > 0:
                                self._append_log(log_widget,"[red]🔍 Raw error output:[/red]")
                                for line in output.split('\n')[-5:]:  # Last 5 lines of raw output
                                    if line.strip():
                                        self._append_log(log_widget,f"[dim]  {line}[/dim]")
                                self._append_log(log_widget,"")

                            # Display friendly error with proper formatting
                            for line in friendly_error.split('\n'):
                                if line.strip():
                                    if line.startswith('❌'):
                                        self._append_log(log_widget,f"[red]{line}[/red]")
                                    elif line.startswith('📋'):
                                        self._append_log(log_widget,f"[blue]{line}[/blue]")
                                    elif line.startswith('🔍'):
                                        self._append_log(log_widget,f"[dim]{line}[/dim]")
                                    elif line.startswith('  •'):
                                        self._append_log(log_widget,f"[yellow]{line}[/yellow]")
                                    else:
                                        self._append_log(log_widget,line)
                    else:
                        task["status"] = "failed"
                        task["message"] = "Cannot get installation command"
                        self._append_log(log_widget,f"[red]Error: Cannot get installation command for {app.name}[/red]")

                else:  # uninstall
                    # Get uninstall command
                    command = self.app_installer.get_uninstall_command(app)
                    if command:
                        # Check if this specific command needs sudo
                        if self._command_needs_sudo_for_task(task):
                            self._append_log(log_widget,f"[yellow]⚠️ Administrator privileges required for uninstallation command[/yellow]")

                        self._append_log(log_widget,f"[dim]Executing command: {command}[/dim]")

                        # Execute uninstallation
                        task["progress"] = 50
                        self._update_progress(task_index, task["progress"])

                        success, output = await self._execute_command_with_sudo_support(command, log_widget)

                        if success:
                            task["status"] = "success"
                            task["progress"] = 100
                            self._append_log(log_widget,f"[green]✅ {app.name} re-uninstalled successfully[/green]")

                            # Save uninstallation status to persist state
                            if self.app_installer.save_installation_status(app.name, False):
                                self._append_log(log_widget,f"[dim]  📝 Saved uninstall status for {app.name}[/dim]")
                            else:
                                self._append_log(log_widget,f"[yellow]  ⚠️ Failed to save uninstall status for {app.name}[/yellow]")
                        else:
                            task["status"] = "failed"
                            task["message"] = output

                            # Generate user-friendly error analysis
                            friendly_error = self.app_installer.analyze_error_and_suggest_solution(
                                output, command, app.name
                            )

                            self._append_log(log_widget,f"[red]❌ {app.name} retry uninstallation failed[/red]")
                            self._append_log(log_widget,"")

                            # Show raw error output first for debugging
                            if output and len(output.strip()) > 0:
                                self._append_log(log_widget,"[red]🔍 Raw error output:[/red]")
                                for line in output.split('\n')[-5:]:  # Last 5 lines of raw output
                                    if line.strip():
                                        self._append_log(log_widget,f"[dim]  {line}[/dim]")
                                self._append_log(log_widget,"")

                            # Display friendly error with proper formatting
                            for line in friendly_error.split('\n'):
                                if line.strip():
                                    if line.startswith('❌'):
                                        self._append_log(log_widget,f"[red]{line}[/red]")
                                    elif line.startswith('📋'):
                                        self._append_log(log_widget,f"[blue]{line}[/blue]")
                                    elif line.startswith('🔍'):
                                        self._append_log(log_widget,f"[dim]{line}[/dim]")
                                    elif line.startswith('  •'):
                                        self._append_log(log_widget,f"[yellow]{line}[/yellow]")
                                    else:
                                        self._append_log(log_widget,line)
                    else:
                        task["status"] = "failed"
                        task["message"] = "Cannot get uninstall command"
                        self._append_log(log_widget,f"[red]Error: Cannot get uninstall command for {app.name}[/red]")

            except Exception as e:
                task["status"] = "failed"
                task["message"] = str(e)
                self._append_log(log_widget,f"[red]Error: {str(e)}[/red]")

            self._update_task_display(task_index)
            self._update_progress(task_index, task["progress"])

        # Retry completed
        self.all_completed = True
        self._enable_close_button()

        # Log completion
        timestamp = datetime.now().strftime("%H:%M:%S")
        retry_successful = sum(1 for t in retry_tasks if t["status"] == "success")
        retry_failed = sum(1 for t in retry_tasks if t["status"] == "failed")

        self._append_log(log_widget,"")
        self._append_log(log_widget,f"[{timestamp}] " + "="*50)
        self._append_log(log_widget,f"[bold]重试完成: {retry_successful} 成功, {retry_failed} 失败[/bold]")

        if retry_failed == 0:
            self._append_log(log_widget,"[green]🎉 All retry tasks completed successfully![/green]")
        else:
            self._append_log(log_widget,f"[yellow]⚠️ {retry_failed} tasks still failed, can retry again.[/yellow]")
    
    def action_dismiss(self) -> None:
        """Dismiss the modal (only if completed)."""
        if self.all_completed:
            self.dismiss()

    def action_scroll_down(self) -> None:
        """Scroll the log output down."""
        try:
            log_widget = self.query_one("#log-output", TextArea)
            log_widget.scroll_down(animate=False)
        except Exception:
            # If log widget not available yet, ignore
            pass

    def action_scroll_up(self) -> None:
        """Scroll the log output up."""
        try:
            log_widget = self.query_one("#log-output", TextArea)
            log_widget.scroll_up(animate=False)
        except Exception:
            # If log widget not available yet, ignore
            pass