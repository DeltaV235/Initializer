"""Application Installation Progress Modal."""

from textual import on, work
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.screen import ModalScreen
from textual.widgets import Button, Static, Rule, Label, ProgressBar, RichLog
from textual.reactive import reactive
from textual.events import Key
from typing import List, Dict
import asyncio
from datetime import datetime


class AppInstallProgressModal(ModalScreen):
    """Modal screen for showing application installation/uninstallation progress."""
    
    BINDINGS = [
        ("escape", "close", "Close"),
    ]
    
    # CSS styles for the modal
    CSS = """
    AppInstallProgressModal {
        align: center middle;
    }
    
    #modal-container {
        width: 90%;
        height: 80%;
        background: $surface;
        border: solid $primary;
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
        border: solid $primary;
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
    
    def __init__(self, actions: List[Dict], app_installer):
        super().__init__()
        self.actions = actions
        self.app_installer = app_installer
        
        # Task tracking
        self.tasks = []
        for action in actions:
            app = action["application"]
            task_name = f"{'安装' if action['action'] == 'install' else '卸载'} {app.name}"
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
        if event.key == "escape" and self.all_completed:
            self.dismiss()
            event.prevent_default()
            event.stop()
    
    def compose(self) -> ComposeResult:
        """Compose the modal interface."""
        with Container(id="modal-container"):
            yield Static("📦 应用安装进度", id="modal-title")
            yield Rule()
            
            # Task list (for multiple tasks)
            if len(self.tasks) > 1:
                with ScrollableContainer(id="task-container"):
                    for i, task in enumerate(self.tasks):
                        with Horizontal(classes="task-item"):
                            yield Static(task["name"], id=f"task-name-{i}", classes="task-name")
                            yield Static("⏳ 等待中", id=f"task-status-{i}", classes="task-status status-pending")
                            yield ProgressBar(id=f"task-progress-{i}", classes="task-progress", total=100)
            
            # Main progress bar (for single task or overall progress)
            with Container(id="progress-container"):
                if len(self.tasks) == 1:
                    yield Label(f"任务: {self.tasks[0]['name']}")
                else:
                    yield Label("总体进度")
                yield ProgressBar(id="main-progress", total=100)
            
            # Log output
            yield Label("📋 安装日志:", classes="info-key")
            with Container(id="log-container"):
                yield RichLog(id="log-output", highlight=True, markup=True, wrap=True)
            
            # Buttons
            with Horizontal(id="button-container"):
                yield Button("关闭 (ESC)", id="close", variant="default", disabled=True)
    
    @work(exclusive=True, thread=True)
    async def _start_processing(self) -> None:
        """Process all installation/uninstallation tasks."""
        log_widget = self.query_one("#log-output", RichLog)
        
        for i, task in enumerate(self.tasks):
            self.current_task_index = i
            
            # Update task status
            task["status"] = "running"
            self._update_task_display(i)
            
            # Log start
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_widget.write(f"[{timestamp}] 开始: {task['name']}")
            
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
                        log_widget.write(f"[dim]执行命令: {command}[/dim]")
                        
                        # Execute installation
                        task["progress"] = 40
                        self._update_progress(i, task["progress"])
                        
                        success, output = await self._execute_command_async(command)
                        
                        if success:
                            task["progress"] = 70
                            self._update_progress(i, task["progress"])
                            
                            # Execute post-install if any
                            if app.post_install:
                                log_widget.write(f"[dim]执行安装后配置: {app.post_install}[/dim]")
                                post_success, post_output = await self._execute_command_async(app.post_install)
                                if not post_success:
                                    log_widget.write(f"[yellow]⚠️ 安装后配置失败: {post_output}[/yellow]")
                            
                            task["status"] = "success"
                            task["progress"] = 100
                            log_widget.write(f"[green]✅ {app.name} 安装成功[/green]")
                        else:
                            task["status"] = "failed"
                            task["message"] = output
                            log_widget.write(f"[red]❌ {app.name} 安装失败: {output}[/red]")
                    else:
                        task["status"] = "failed"
                        task["message"] = "无法获取安装命令"
                        log_widget.write(f"[red]错误: 无法获取 {app.name} 的安装命令[/red]")
                
                else:  # uninstall
                    # Get uninstall command
                    command = self.app_installer.get_uninstall_command(app)
                    if command:
                        log_widget.write(f"[dim]执行命令: {command}[/dim]")
                        
                        # Execute uninstallation
                        task["progress"] = 50
                        self._update_progress(i, task["progress"])
                        
                        success, output = await self._execute_command_async(command)
                        
                        if success:
                            task["status"] = "success"
                            task["progress"] = 100
                            log_widget.write(f"[green]✅ {app.name} 卸载成功[/green]")
                        else:
                            task["status"] = "failed"
                            task["message"] = output
                            log_widget.write(f"[red]❌ {app.name} 卸载失败: {output}[/red]")
                    else:
                        task["status"] = "failed"
                        task["message"] = "无法获取卸载命令"
                        log_widget.write(f"[red]错误: 无法获取 {app.name} 的卸载命令[/red]")
            
            except Exception as e:
                task["status"] = "failed"
                task["message"] = str(e)
                log_widget.write(f"[red]错误: {str(e)}[/red]")
            
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
        log_widget.write(f"[bold]安装完成: {successful} 成功, {failed} 失败[/bold]")
        
        if failed == 0:
            log_widget.write("[green]✅ 所有任务成功完成！[/green]")
        else:
            log_widget.write("[yellow]⚠️ 部分任务失败，请查看日志了解详情。[/yellow]")
    
    async def _execute_command_async(self, command: str) -> tuple:
        """Execute a command asynchronously.
        
        Args:
            command: Command to execute
            
        Returns:
            Tuple of (success, output/error message)
        """
        try:
            # For demonstration, we'll simulate the execution
            # In a real implementation, this would use asyncio.create_subprocess_shell
            await asyncio.sleep(1)  # Simulate execution time
            
            # For now, return a simulated success
            # In production, this would actually execute the command
            return True, "Command executed successfully (simulated)"
            
        except Exception as e:
            return False, str(e)
    
    def _update_task_display(self, index: int) -> None:
        """Update the display for a specific task."""
        if len(self.tasks) <= 1:
            return
        
        task = self.tasks[index]
        status_widget = self.query_one(f"#task-status-{index}", Static)
        
        status_map = {
            "pending": ("⏳ 等待中", "status-pending"),
            "running": ("🔄 执行中", "status-running"),
            "success": ("✅ 成功", "status-success"),
            "failed": ("❌ 失败", "status-failed"),
        }
        
        text, css_class = status_map.get(task["status"], ("未知", ""))
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
        close_button.label = "✅ 关闭 (ESC)"
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