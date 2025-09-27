"""Installation Progress Modal."""

from textual import on, work
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.screen import ModalScreen
from textual.widgets import Button, Static, Rule, Label, ProgressBar, RichLog
from textual.reactive import reactive
from textual.events import Key
from typing import List, Dict, Optional
import asyncio
import subprocess
import signal
from datetime import datetime

from ...modules.package_manager import PackageManagerDetector


class InstallationProgressModal(ModalScreen):
    """Modal screen for showing installation/uninstallation progress."""
    
    BINDINGS = [
        ("escape", "close", "Close"),
    ]
    
    # CSS styles for the modal
    CSS = """
    InstallationProgressModal {
        align: center middle;
    }
    
    #modal-container {
        width: 90%;
        height: 80%;
        background: $surface;
        border: round #7dd3fc;
        padding: 1;
        layout: vertical;
    }
    
    #modal-title {
        text-style: bold;
        margin: 0 0 1 0;
    }
    
    #task-container {
        height: auto;
        max-height: 8;
        overflow-y: auto;
        padding: 0 1;
        margin: 0 0 1 0;
    }
    
    .task-item {
        layout: horizontal;
        height: 2;
        margin: 0 0 1 0;
    }
    
    .task-name {
        width: 30%;
        padding: 0 1 0 0;
    }
    
    .task-status {
        width: 15%;
        padding: 0 1 0 0;
    }
    
    .task-progress {
        width: 55%;
    }
    
    #progress-container {
        height: 3;
        padding: 1;
        margin: 0 0 1 0;
    }
    
    #log-container {
        height: 1fr;
        border: round #7dd3fc;
        padding: 1;
        margin: 0 0 1 0;
    }
    
    #log-output {
        height: 100%;
    }
    
    #button-container {
        layout: horizontal;
        align: center middle;
        height: 3;
        margin: 1 0 0 0;
    }
    
    .status-pending {
        color: $text-muted;
    }
    
    .status-running {
        color: $warning;
    }
    
    .status-success {
        color: $success;
    }
    
    .status-failed {
        color: $error;
    }
    """
    
    # Reactive properties
    current_task_index = reactive(0)
    all_completed = reactive(False)

    # Process tracking for cleanup
    _active_processes = []  # Track all active subprocesses
    _is_aborting = False  # Flag to indicate user requested abort
    
    def __init__(self, actions: List[Dict], config_manager=None):
        super().__init__()
        self.actions = actions
        self.detector = PackageManagerDetector(config_manager)
        
        # Task tracking
        self.tasks = []
        for action in actions:
            pm = action["package_manager"]
            task_name = f"{'Install' if action['action'] == 'install' else 'Uninstall'} {pm.name.upper()}"
            self.tasks.append({
                "name": task_name,
                "action": action,
                "status": "pending",  # pending, running, success, failed
                "progress": 0,
                "message": "",
            })
    
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
        if event.key == "escape":
            if self.all_completed:
                # Normal close after completion
                self.dismiss()
            else:
                # Show abort confirmation dialog
                self._show_abort_confirmation()
            event.prevent_default()
            event.stop()
    
    def compose(self) -> ComposeResult:
        """Compose the modal interface."""
        with Container(id="modal-container"):
            yield Static("📦 Installation Progress", id="modal-title")
            yield Rule()
            
            # Task list (for multiple tasks)
            if len(self.tasks) > 1:
                with ScrollableContainer(id="task-container"):
                    for i, task in enumerate(self.tasks):
                        with Horizontal(classes="task-item"):
                            yield Static(task["name"], id=f"task-name-{i}", classes="task-name")
                            yield Static("⏳ Pending", id=f"task-status-{i}", classes="task-status status-pending")
                            yield ProgressBar(id=f"task-progress-{i}", classes="task-progress", total=100)
            
            # Main progress bar (for single task or overall progress)
            with Container(id="progress-container"):
                if len(self.tasks) == 1:
                    yield Label(f"Task: {self.tasks[0]['name']}")
                else:
                    yield Label("Overall Progress")
                yield ProgressBar(id="main-progress", total=100)
            
            # Log output
            yield Label("📋 Installation Log:", classes="section-header")
            with Container(id="log-container"):
                yield RichLog(id="log-output", highlight=True, markup=True, wrap=True)
            
            # Buttons
            with Horizontal(id="button-container"):
                yield Button("Close (Esc)", id="close", variant="default", disabled=True)
    
    @work(exclusive=True, thread=True)
    async def _start_processing(self) -> None:
        """Process all installation/uninstallation tasks."""
        log_widget = self.query_one("#log-output", RichLog)
        
        for i, task in enumerate(self.tasks):
            # Check if user requested abort before starting each task
            if self._is_aborting:
                # Mark all remaining tasks as aborted
                for remaining_task in self.tasks[i:]:
                    if remaining_task["status"] in ["pending", "running"]:
                        remaining_task["status"] = "failed"
                        remaining_task["message"] = "User aborted"
                        remaining_task["progress"] = 0
                        self._update_task_display(self.tasks.index(remaining_task))
                break

            self.current_task_index = i
            
            # Update task status
            task["status"] = "running"
            self._update_task_display(i)
            
            # Log start
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_widget.write(f"[{timestamp}] Starting: {task['name']}")
            
            # Get the command
            action = task["action"]
            pm = action["package_manager"]
            
            if action["action"] == "install":
                command = self.detector.get_install_command(pm.name)
            else:
                command = self.detector.get_uninstall_command(pm.name)
            
            if not command:
                task["status"] = "failed"
                task["message"] = "No command available"
                log_widget.write(f"[error]Error: No command available for {pm.name}[/error]")
                self._update_task_display(i)
                continue
            
            # Log command
            log_widget.write(f"[dim]Command: {command}[/dim]")
            
            try:
                # Execute command with real-time output
                if pm.name == "brew" or "curl" in command:
                    # For scripts, use shell execution
                    process = await asyncio.create_subprocess_shell(
                        command,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.STDOUT,
                        text=False
                    )
                else:
                    # For regular commands
                    cmd_parts = command.split()
                    process = await asyncio.create_subprocess_exec(
                        *cmd_parts,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.STDOUT,
                        text=False
                    )

                # Track process for cleanup
                self._active_processes.append(process)

                # Read output line by line
                while True:
                    # Check if user requested abort
                    if self._is_aborting:
                        # Process was aborted by user
                        break

                    line = await process.stdout.readline()
                    if not line:
                        break
                    
                    # Decode and display line
                    try:
                        decoded_line = line.decode('utf-8', errors='replace').rstrip()
                        if decoded_line:
                            log_widget.write(decoded_line)
                    except:
                        pass
                    
                    # Update progress (simulate based on output)
                    task["progress"] = min(task["progress"] + 5, 90)
                    self._update_progress(i, task["progress"])
                
                # Wait for process to complete
                return_code = await process.wait()

                # Remove process from active list when done
                if process in self._active_processes:
                    self._active_processes.remove(process)
                
                if return_code == 0:
                    task["status"] = "success"
                    task["progress"] = 100
                    task["message"] = "Completed successfully"
                    log_widget.write(f"[green]✅ {task['name']} completed successfully[/green]")
                else:
                    task["status"] = "failed"
                    task["message"] = f"Failed with exit code {return_code}"
                    log_widget.write(f"[red]❌ {task['name']} failed with exit code {return_code}[/red]")
                
            except Exception as e:
                task["status"] = "failed"
                task["message"] = str(e)
                log_widget.write(f"[red]Error: {str(e)}[/red]")
            
            self._update_task_display(i)
            self._update_progress(i, task["progress"])
        
        # All tasks completed
        self.all_completed = True
        self._enable_close_button()
        
        # Log completion
        timestamp = datetime.now().strftime("%H:%M:%S")
        successful = sum(1 for t in self.tasks if t["status"] == "success")
        failed = sum(1 for t in self.tasks if t["status"] == "failed")
        
        log_widget.write("")
        log_widget.write(f"[{timestamp}] " + "="*50)
        log_widget.write(f"[bold]Installation completed: {successful} succeeded, {failed} failed[/bold]")
        
        if failed == 0:
            log_widget.write("[green]✅ All tasks completed successfully![/green]")
        else:
            log_widget.write("[yellow]⚠️ Some tasks failed. Check the log for details.[/yellow]")
    
    def _update_task_display(self, index: int) -> None:
        """Update the display for a specific task."""
        if len(self.tasks) <= 1:
            return
        
        task = self.tasks[index]
        status_widget = self.query_one(f"#task-status-{index}", Static)
        
        status_map = {
            "pending": ("⏳ Pending", "status-pending"),
            "running": ("🔄 Running", "status-running"),
            "success": ("✅ Success", "status-success"),
            "failed": ("❌ Failed", "status-failed"),
        }
        
        text, css_class = status_map.get(task["status"], ("Unknown", ""))
        status_widget.update(text)
        status_widget.set_class(css_class, True)
    
    def _update_progress(self, task_index: int, progress: int) -> None:
        """Update progress bars."""
        # Update task-specific progress bar if multiple tasks
        if len(self.tasks) > 1:
            task_progress = self.query_one(f"#task-progress-{task_index}", ProgressBar)
            task_progress.update(progress=progress)
        
        # Update main progress bar
        main_progress = self.query_one("#main-progress", ProgressBar)
        if len(self.tasks) == 1:
            # Single task - show its progress
            main_progress.update(progress=progress)
        else:
            # Multiple tasks - show overall progress
            total_progress = sum(t["progress"] for t in self.tasks) / len(self.tasks)
            main_progress.update(progress=int(total_progress))
    
    def _enable_close_button(self) -> None:
        """Enable the close button when all tasks are complete."""
        close_button = self.query_one("#close", Button)
        close_button.disabled = False
        close_button.label = "✅ Close (Esc)"
        close_button.variant = "primary"
    
    @on(Button.Pressed, "#close")
    def action_close(self) -> None:
        """Close the modal."""
        if self.all_completed:
            self.dismiss()
    
    def action_dismiss(self) -> None:
        """Dismiss the modal (only if completed)."""
        if self.all_completed:
            self.dismiss()

    def _show_abort_confirmation(self) -> None:
        """Show installation abort confirmation dialog."""
        from .abort_confirmation_modal import AbortConfirmationModal

        def handle_abort_result(confirmed: bool):
            """Handle abort confirmation result."""
            if confirmed:
                # User confirmed abort
                self._abort_installation()

        # Push abort confirmation dialog
        self.app.push_screen(AbortConfirmationModal(), handle_abort_result)

    def _abort_installation(self) -> None:
        """Abort the installation process."""
        try:
            self._is_aborting = True
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_widget = self.query_one("#log-output", RichLog)

            log_widget.write("")
            log_widget.write(f"[{timestamp}] " + "="*50)
            log_widget.write("[yellow]⚠️ User requested installation abort...[/yellow]")

            # Terminate all active processes
            terminated_count = 0
            for process in self._active_processes:
                try:
                    if process and process.returncode is None:  # Process is still running
                        process.terminate()  # Send SIGTERM
                        terminated_count += 1
                        log_widget.write(f"[dim]  • Terminating process PID {process.pid}[/dim]")
                except Exception as e:
                    log_widget.write(f"[yellow]  ⚠️ Failed to terminate process: {str(e)}[/yellow]")

            if terminated_count > 0:
                log_widget.write(f"[yellow]✅ Requested termination of {terminated_count} active processes[/yellow]")
                log_widget.write("[yellow]⚠️ Warning: Some packages may be in partially installed state[/yellow]")
                log_widget.write("[dim]  Suggestion: Run package manager repair command (e.g., 'sudo apt --fix-broken install')[/dim]")
            else:
                log_widget.write("[dim]  • No active processes to terminate[/dim]")

            # Mark all unfinished tasks as interrupted
            for task in self.tasks:
                if task["status"] in ["pending", "running"]:
                    task["status"] = "failed"
                    task["message"] = "User aborted"
                    task["progress"] = 0

            self.all_completed = True
            self._enable_close_button()

            log_widget.write(f"[{timestamp}] Installation aborted, you can close this window")
            log_widget.write("="*50)

        except Exception as e:
            log_widget = self.query_one("#log-output", RichLog)
            log_widget.write(f"[red]❌ Abort handling failed: {str(e)}[/red]")

    def on_unmount(self) -> None:
        """Clean up resources and ensure all subprocesses are properly handled."""
        try:
            # Clean up all active processes
            for process in self._active_processes:
                try:
                    if process and process.returncode is None:
                        # Send SIGTERM for graceful termination
                        process.terminate()
                        try:
                            # Wait up to 2 seconds for graceful exit
                            import asyncio
                            asyncio.wait_for(process.wait(), timeout=2.0)
                        except asyncio.TimeoutError:
                            # If process doesn't respond, force kill
                            process.kill()
                            process.wait()
                except Exception as e:
                    print(f"Warning: Failed to cleanup process {process.pid}: {e}")

            # Clear process list
            self._active_processes.clear()

        except Exception as e:
            print(f"Error in on_unmount cleanup: {e}")