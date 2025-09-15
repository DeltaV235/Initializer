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
from ...utils.log_manager import LogLevel


class AppInstallProgressModal(ModalScreen):
    """Modal screen for showing application installation/uninstallation progress."""
    
    BINDINGS = [
        ("escape", "close", "Close"),
        ("r", "retry_failed", "Retry Failed"),
        ("l", "export_logs", "Export Logs"),
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
    has_failed_tasks = reactive(False)
    
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
                yield Button("重试失败任务 (R)", id="retry-failed", variant="warning", disabled=True)
                yield Static("  ")  # Spacer
                yield Button("导出日志 (L)", id="export-logs", variant="success", disabled=True)
                yield Static("  ")  # Spacer
                yield Button("关闭 (ESC)", id="close", variant="default", disabled=True)
    
    @work(exclusive=True, thread=True)
    async def _start_processing(self) -> None:
        """Process all installation/uninstallation tasks."""
        log_widget = self.query_one("#log-output", RichLog)

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
                f"开始安装会话 - 共 {len(self.tasks)} 个任务",
                action="session_start"
            )

            timestamp = datetime.now().strftime("%H:%M:%S")
            log_widget.write(f"[{timestamp}] 📝 日志会话已启动: {session_id}")

        except Exception as e:
            log_widget.write(f"[yellow]⚠️ 日志初始化失败: {e}[/yellow]")

        # Initial permission check for sudo commands
        has_sudo_commands = any(
            "sudo" in self.app_installer.get_install_command(task["action"]["application"]) or
            "sudo" in (self.app_installer.get_uninstall_command(task["action"]["application"]) or "")
            for task in self.tasks
        )

        if has_sudo_commands:
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_widget.write(f"[{timestamp}] 检查 sudo 权限...")

            # Check if sudo is available
            if not self.app_installer.check_sudo_available():
                log_widget.write("[red]❌ 检测到需要 sudo 权限，但 sudo 不可用或用户无权限[/red]")
                log_widget.write("[yellow]请确保:[/yellow]")
                log_widget.write("[yellow]1. 系统已安装 sudo[/yellow]")
                log_widget.write("[yellow]2. 当前用户已加入 sudo 组[/yellow]")
                log_widget.write("[yellow]3. 已通过 sudo 认证缓存（可尝试手动运行 'sudo -v'）[/yellow]")

                # Mark all tasks as failed
                for task in self.tasks:
                    task["status"] = "failed"
                    task["message"] = "sudo 权限不可用"
                    self._update_task_display(self.tasks.index(task))

                self.all_completed = True
                self._enable_close_button()
                return
            else:
                log_widget.write("[green]✅ sudo 权限验证通过[/green]")

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
                        # Check if this specific command needs sudo
                        if "sudo" in command:
                            log_widget.write(f"[yellow]⚠️ 需要管理员权限执行安装命令[/yellow]")

                        log_widget.write(f"[dim]执行命令: {command}[/dim]")
                        
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

                        success, output = await self._execute_command_async(command, log_widget, update_install_progress)
                        
                        if success:
                            task["progress"] = 70
                            self._update_progress(i, task["progress"])

                            # Execute post-install if any
                            if app.post_install:
                                log_widget.write(f"[dim]执行安装后配置: {app.post_install}[/dim]")

                                # Create progress callback for post-install (70-100%)
                                def update_postinstall_progress(percentage):
                                    task_progress = 70 + int((percentage / 100) * 30)
                                    task["progress"] = min(task_progress, 100)
                                    self._update_progress(i, task["progress"])

                                post_success, post_output = await self._execute_command_async(app.post_install, log_widget, update_postinstall_progress)
                                if not post_success:
                                    log_widget.write(f"[yellow]⚠️ 安装后配置失败: {post_output}[/yellow]")

                            task["status"] = "success"
                            task["progress"] = 100
                            log_widget.write(f"[green]✅ {app.name} 安装成功[/green]")

                            # Log successful installation
                            self.app_installer.log_installation_event(
                                LogLevel.SUCCESS,
                                f"{app.name} 安装成功",
                                application=app.name,
                                action="install",
                                command=command,
                                output=output
                            )

                            # Save installation status to persist state
                            if self.app_installer.save_installation_status(app.name, True):
                                log_widget.write(f"[dim]  📝 已保存 {app.name} 的安装状态[/dim]")
                            else:
                                log_widget.write(f"[yellow]  ⚠️ 保存 {app.name} 安装状态失败[/yellow]")
                        else:
                            task["status"] = "failed"
                            task["message"] = output

                            # Log failed installation
                            self.app_installer.log_installation_event(
                                LogLevel.ERROR,
                                f"{app.name} 安装失败",
                                application=app.name,
                                action="install",
                                command=command,
                                error=output
                            )

                            # Generate user-friendly error analysis
                            friendly_error = self.app_installer.analyze_error_and_suggest_solution(
                                output, command, app.name
                            )

                            log_widget.write(f"[red]❌ {app.name} 安装失败[/red]")
                            log_widget.write("")
                            # Display friendly error with proper formatting
                            for line in friendly_error.split('\n'):
                                if line.strip():
                                    if line.startswith('❌'):
                                        log_widget.write(f"[red]{line}[/red]")
                                    elif line.startswith('📋'):
                                        log_widget.write(f"[blue]{line}[/blue]")
                                    elif line.startswith('🔍'):
                                        log_widget.write(f"[dim]{line}[/dim]")
                                    elif line.startswith('  •'):
                                        log_widget.write(f"[yellow]{line}[/yellow]")
                                    else:
                                        log_widget.write(line)
                    else:
                        task["status"] = "failed"
                        task["message"] = "无法获取安装命令"
                        log_widget.write(f"[red]错误: 无法获取 {app.name} 的安装命令[/red]")
                
                else:  # uninstall
                    # Get uninstall command
                    command = self.app_installer.get_uninstall_command(app)
                    if command:
                        # Check if this specific command needs sudo
                        if "sudo" in command:
                            log_widget.write(f"[yellow]⚠️ 需要管理员权限执行卸载命令[/yellow]")

                        log_widget.write(f"[dim]执行命令: {command}[/dim]")

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

                        success, output = await self._execute_command_async(command, log_widget, update_uninstall_progress)

                        if success:
                            task["status"] = "success"
                            task["progress"] = 100
                            log_widget.write(f"[green]✅ {app.name} 卸载成功[/green]")

                            # Save uninstallation status to persist state
                            if self.app_installer.save_installation_status(app.name, False):
                                log_widget.write(f"[dim]  📝 已保存 {app.name} 的卸载状态[/dim]")
                            else:
                                log_widget.write(f"[yellow]  ⚠️ 保存 {app.name} 卸载状态失败[/yellow]")
                        else:
                            task["status"] = "failed"
                            task["message"] = output

                            # Generate user-friendly error analysis
                            friendly_error = self.app_installer.analyze_error_and_suggest_solution(
                                output, command, app.name
                            )

                            log_widget.write(f"[red]❌ {app.name} 卸载失败[/red]")
                            log_widget.write("")
                            # Display friendly error with proper formatting
                            for line in friendly_error.split('\n'):
                                if line.strip():
                                    if line.startswith('❌'):
                                        log_widget.write(f"[red]{line}[/red]")
                                    elif line.startswith('📋'):
                                        log_widget.write(f"[blue]{line}[/blue]")
                                    elif line.startswith('🔍'):
                                        log_widget.write(f"[dim]{line}[/dim]")
                                    elif line.startswith('  •'):
                                        log_widget.write(f"[yellow]{line}[/yellow]")
                                    else:
                                        log_widget.write(line)
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

        # End logging session and export logs
        try:
            self.app_installer.log_installation_event(
                LogLevel.INFO,
                f"安装会话结束 - 成功: {successful}, 失败: {failed}",
                action="session_end"
            )

            # End logging session
            self.app_installer.end_logging_session()

            # Auto-export logs in multiple formats
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Export as HTML for easy viewing
            try:
                html_file = self.app_installer.export_installation_logs(format="html")
                log_widget.write(f"[dim]📄 HTML 日志已导出: {html_file}[/dim]")
            except Exception as e:
                log_widget.write(f"[yellow]⚠️ HTML 日志导出失败: {e}[/yellow]")

            # Export as TXT for easy reading
            try:
                txt_file = self.app_installer.export_installation_logs(format="txt")
                log_widget.write(f"[dim]📄 文本日志已导出: {txt_file}[/dim]")
            except Exception as e:
                log_widget.write(f"[yellow]⚠️ 文本日志导出失败: {e}[/yellow]")

            # Export as JSON for detailed analysis
            try:
                json_file = self.app_installer.export_installation_logs(format="json")
                log_widget.write(f"[dim]📄 JSON 日志已导出: {json_file}[/dim]")
            except Exception as e:
                log_widget.write(f"[yellow]⚠️ JSON 日志导出失败: {e}[/yellow]")

        except Exception as e:
            log_widget.write(f"[yellow]⚠️ 日志会话结束失败: {e}[/yellow]")
    
    async def _execute_command_async(self, command: str, log_widget=None, progress_callback=None) -> tuple:
        """Execute a command asynchronously with real-time output streaming and progress tracking.

        Args:
            command: Command to execute
            log_widget: RichLog widget for real-time output display
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
                text=True,
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
                    line = await asyncio.wait_for(
                        process.stdout.readline(),
                        timeout=30.0  # 30-second timeout per line
                    )

                    if not line:  # EOF reached
                        break

                    line = line.strip()
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
                            if any(keyword in line.lower() for keyword in ['error', '错误', 'failed', '失败']):
                                log_widget.write(f"[red]  📄 {line}[/red]")
                                error_occurred = True
                            elif any(keyword in line.lower() for keyword in ['warning', '警告', 'warn']):
                                log_widget.write(f"[yellow]  📄 {line}[/yellow]")
                            elif any(keyword in line.lower() for keyword in ['installing', '安装', 'downloading', '下载']):
                                log_widget.write(f"[blue]  📦 {line}[/blue]")
                            elif any(keyword in line.lower() for keyword in ['success', '成功', 'complete', '完成', 'done']):
                                log_widget.write(f"[green]  ✅ {line}[/green]")
                            elif any(keyword in line.lower() for keyword in ['processing', '处理', 'configuring', '配置', 'setting up']):
                                log_widget.write(f"[cyan]  ⚙️ {line}[/cyan]")
                            else:
                                log_widget.write(f"[dim]  📄 {line}[/dim]")

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
                return False, "命令执行总体超时 (4.5分钟)"

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
                # Failure
                if error_occurred or output_lines:
                    error_lines = [line for line in output_lines if any(keyword in line.lower() for keyword in ['error', '错误', 'failed', '失败'])]
                    if error_lines:
                        return False, "\n".join(error_lines[-2:])  # Last 2 error lines
                    else:
                        return False, "\n".join(output_lines[-2:]) if output_lines else f"命令执行失败，退出码: {process.returncode}"
                else:
                    return False, f"命令执行失败，退出码: {process.returncode}"

        except FileNotFoundError:
            return False, "命令未找到或无法执行"
        except PermissionError:
            return False, "权限不足，无法执行命令"
        except Exception as e:
            return False, f"执行错误: {str(e)}"

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
        """Enable the close button and retry button when all tasks are complete."""
        # Enable close button
        close_button = self.query_one("#close", Button)
        close_button.disabled = False
        close_button.label = "✅ 关闭 (ESC)"
        close_button.variant = "primary"

        # Enable export logs button
        export_button = self.query_one("#export-logs", Button)
        export_button.disabled = False
        export_button.label = "📄 导出日志 (L)"
        export_button.variant = "success"

        # Check if there are failed tasks and enable retry button
        failed_tasks = [task for task in self.tasks if task["status"] == "failed"]
        if failed_tasks:
            self.has_failed_tasks = True
            retry_button = self.query_one("#retry-failed", Button)
            retry_button.disabled = False
            retry_button.label = f"🔄 重试失败任务 ({len(failed_tasks)}) (R)"
            retry_button.variant = "warning"
    
    @on(Button.Pressed, "#close")
    def action_close(self) -> None:
        """Close the modal."""
        if self.all_completed:
            self.dismiss()

    @on(Button.Pressed, "#retry-failed")
    def on_retry_button_pressed(self) -> None:
        """Handle retry button press."""
        self.action_retry_failed()

    @on(Button.Pressed, "#export-logs")
    def on_export_logs_button_pressed(self) -> None:
        """Handle export logs button press."""
        self.action_export_logs()

    def action_retry_failed(self) -> None:
        """Handle retry failed tasks action (both button and R key)."""
        if self.has_failed_tasks and self.all_completed:
            self._start_retry_process()

    def _start_retry_process(self) -> None:
        """Start the retry process for failed tasks."""
        log_widget = self.query_one("#log-output", RichLog)

        # Find failed tasks
        failed_tasks = [task for task in self.tasks if task["status"] == "failed"]
        if not failed_tasks:
            log_widget.write("[yellow]没有失败的任务需要重试[/yellow]")
            return

        # Log retry start
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_widget.write("")
        log_widget.write(f"[{timestamp}] " + "="*30)
        log_widget.write(f"[bold blue]🔄 开始重试 {len(failed_tasks)} 个失败任务[/bold blue]")
        log_widget.write("="*50)

        # Reset failed tasks status
        for task in failed_tasks:
            task["status"] = "pending"
            task["progress"] = 0
            task["message"] = ""

        # Reset modal state
        self.all_completed = False
        self.has_failed_tasks = False

        # Disable buttons during retry
        close_button = self.query_one("#close", Button)
        close_button.disabled = True
        close_button.label = "关闭 (ESC)"
        close_button.variant = "default"

        retry_button = self.query_one("#retry-failed", Button)
        retry_button.disabled = True
        retry_button.label = "重试失败任务 (R)"
        retry_button.variant = "warning"

        # Start processing retry tasks
        self._start_retry_processing(failed_tasks)

    @work(exclusive=True, thread=True)
    async def _start_retry_processing(self, retry_tasks: List[Dict]) -> None:
        """Process retry tasks."""
        log_widget = self.query_one("#log-output", RichLog)

        for task in retry_tasks:
            task_index = self.tasks.index(task)
            self.current_task_index = task_index

            # Update task status
            task["status"] = "running"
            self._update_task_display(task_index)

            # Log start
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_widget.write(f"[{timestamp}] 重试: {task['name']}")

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
                        if "sudo" in command:
                            log_widget.write(f"[yellow]⚠️ 需要管理员权限执行安装命令[/yellow]")

                        log_widget.write(f"[dim]执行命令: {command}[/dim]")

                        # Execute installation
                        task["progress"] = 40
                        self._update_progress(task_index, task["progress"])

                        success, output = await self._execute_command_async(command, log_widget)

                        if success:
                            task["progress"] = 70
                            self._update_progress(task_index, task["progress"])

                            # Execute post-install if any
                            if app.post_install:
                                log_widget.write(f"[dim]执行安装后配置: {app.post_install}[/dim]")
                                post_success, post_output = await self._execute_command_async(app.post_install, log_widget)
                                if not post_success:
                                    log_widget.write(f"[yellow]⚠️ 安装后配置失败: {post_output}[/yellow]")

                            task["status"] = "success"
                            task["progress"] = 100
                            log_widget.write(f"[green]✅ {app.name} 重新安装成功[/green]")

                            # Save installation status to persist state
                            if self.app_installer.save_installation_status(app.name, True):
                                log_widget.write(f"[dim]  📝 已保存 {app.name} 的安装状态[/dim]")
                            else:
                                log_widget.write(f"[yellow]  ⚠️ 保存 {app.name} 安装状态失败[/yellow]")
                        else:
                            task["status"] = "failed"
                            task["message"] = output

                            # Generate user-friendly error analysis
                            friendly_error = self.app_installer.analyze_error_and_suggest_solution(
                                output, command, app.name
                            )

                            log_widget.write(f"[red]❌ {app.name} 重新安装失败[/red]")
                            log_widget.write("")
                            # Display friendly error with proper formatting
                            for line in friendly_error.split('\n'):
                                if line.strip():
                                    if line.startswith('❌'):
                                        log_widget.write(f"[red]{line}[/red]")
                                    elif line.startswith('📋'):
                                        log_widget.write(f"[blue]{line}[/blue]")
                                    elif line.startswith('🔍'):
                                        log_widget.write(f"[dim]{line}[/dim]")
                                    elif line.startswith('  •'):
                                        log_widget.write(f"[yellow]{line}[/yellow]")
                                    else:
                                        log_widget.write(line)
                    else:
                        task["status"] = "failed"
                        task["message"] = "无法获取安装命令"
                        log_widget.write(f"[red]错误: 无法获取 {app.name} 的安装命令[/red]")

                else:  # uninstall
                    # Get uninstall command
                    command = self.app_installer.get_uninstall_command(app)
                    if command:
                        # Check if this specific command needs sudo
                        if "sudo" in command:
                            log_widget.write(f"[yellow]⚠️ 需要管理员权限执行卸载命令[/yellow]")

                        log_widget.write(f"[dim]执行命令: {command}[/dim]")

                        # Execute uninstallation
                        task["progress"] = 50
                        self._update_progress(task_index, task["progress"])

                        success, output = await self._execute_command_async(command, log_widget)

                        if success:
                            task["status"] = "success"
                            task["progress"] = 100
                            log_widget.write(f"[green]✅ {app.name} 重新卸载成功[/green]")

                            # Save uninstallation status to persist state
                            if self.app_installer.save_installation_status(app.name, False):
                                log_widget.write(f"[dim]  📝 已保存 {app.name} 的卸载状态[/dim]")
                            else:
                                log_widget.write(f"[yellow]  ⚠️ 保存 {app.name} 卸载状态失败[/yellow]")
                        else:
                            task["status"] = "failed"
                            task["message"] = output

                            # Generate user-friendly error analysis
                            friendly_error = self.app_installer.analyze_error_and_suggest_solution(
                                output, command, app.name
                            )

                            log_widget.write(f"[red]❌ {app.name} 重新卸载失败[/red]")
                            log_widget.write("")
                            # Display friendly error with proper formatting
                            for line in friendly_error.split('\n'):
                                if line.strip():
                                    if line.startswith('❌'):
                                        log_widget.write(f"[red]{line}[/red]")
                                    elif line.startswith('📋'):
                                        log_widget.write(f"[blue]{line}[/blue]")
                                    elif line.startswith('🔍'):
                                        log_widget.write(f"[dim]{line}[/dim]")
                                    elif line.startswith('  •'):
                                        log_widget.write(f"[yellow]{line}[/yellow]")
                                    else:
                                        log_widget.write(line)
                    else:
                        task["status"] = "failed"
                        task["message"] = "无法获取卸载命令"
                        log_widget.write(f"[red]错误: 无法获取 {app.name} 的卸载命令[/red]")

            except Exception as e:
                task["status"] = "failed"
                task["message"] = str(e)
                log_widget.write(f"[red]错误: {str(e)}[/red]")

            self._update_task_display(task_index)
            self._update_progress(task_index, task["progress"])

        # Retry completed
        self.all_completed = True
        self._enable_close_button()

        # Log completion
        timestamp = datetime.now().strftime("%H:%M:%S")
        retry_successful = sum(1 for t in retry_tasks if t["status"] == "success")
        retry_failed = sum(1 for t in retry_tasks if t["status"] == "failed")

        log_widget.write("")
        log_widget.write(f"[{timestamp}] " + "="*50)
        log_widget.write(f"[bold]重试完成: {retry_successful} 成功, {retry_failed} 失败[/bold]")

        if retry_failed == 0:
            log_widget.write("[green]🎉 所有重试任务都成功完成！[/green]")
        else:
            log_widget.write(f"[yellow]⚠️ 仍有 {retry_failed} 个任务失败，可以再次重试。[/yellow]")
    
    def action_dismiss(self) -> None:
        """Dismiss the modal (only if completed)."""
        if self.all_completed:
            self.dismiss()

    def action_export_logs(self) -> None:
        """Export installation logs to file."""
        if not self.all_completed:
            return

        log_widget = self.query_one("#log-output", RichLog)

        try:
            # Get list of available sessions
            sessions = self.app_installer.list_log_sessions()

            if not sessions:
                log_widget.write("[yellow]⚠️ 没有可用的日志会话[/yellow]")
                return

            # Get the most recent session (current or last completed)
            current_session = sessions[0]
            session_id = current_session['session_id']

            log_widget.write("")
            log_widget.write("[bold blue]📄 开始导出安装日志...[/bold blue]")

            # Export in multiple formats
            exported_files = []

            # Export as HTML (for viewing in browser)
            try:
                html_file = self.app_installer.export_installation_logs(
                    session_id=session_id,
                    format="html"
                )
                exported_files.append(("HTML", html_file))
                log_widget.write(f"[green]✅ HTML 日志已导出: {html_file}[/green]")
            except Exception as e:
                log_widget.write(f"[red]❌ HTML 导出失败: {e}[/red]")

            # Export as TXT (for easy reading)
            try:
                txt_file = self.app_installer.export_installation_logs(
                    session_id=session_id,
                    format="txt"
                )
                exported_files.append(("TXT", txt_file))
                log_widget.write(f"[green]✅ 文本日志已导出: {txt_file}[/green]")
            except Exception as e:
                log_widget.write(f"[red]❌ 文本导出失败: {e}[/red]")

            # Export as JSON (for programmatic access)
            try:
                json_file = self.app_installer.export_installation_logs(
                    session_id=session_id,
                    format="json"
                )
                exported_files.append(("JSON", json_file))
                log_widget.write(f"[green]✅ JSON 日志已导出: {json_file}[/green]")
            except Exception as e:
                log_widget.write(f"[red]❌ JSON 导出失败: {e}[/red]")

            # Export as YAML (human-readable structured format)
            try:
                yaml_file = self.app_installer.export_installation_logs(
                    session_id=session_id,
                    format="yaml"
                )
                exported_files.append(("YAML", yaml_file))
                log_widget.write(f"[green]✅ YAML 日志已导出: {yaml_file}[/green]")
            except Exception as e:
                log_widget.write(f"[red]❌ YAML 导出失败: {e}[/red]")

            if exported_files:
                log_widget.write("")
                log_widget.write("[bold green]🎉 日志导出完成![/bold green]")
                log_widget.write(f"[dim]会话 ID: {session_id}[/dim]")
                log_widget.write(f"[dim]共导出 {len(exported_files)} 个文件格式[/dim]")

                # Display summary of exported files
                log_widget.write("")
                log_widget.write("[bold]📁 导出文件列表:[/bold]")
                for format_name, file_path in exported_files:
                    log_widget.write(f"[cyan]  {format_name}:[/cyan] {file_path}")

                # Provide usage instructions
                log_widget.write("")
                log_widget.write("[bold blue]💡 使用建议:[/bold blue]")
                log_widget.write("[dim]• HTML 文件: 在浏览器中打开查看格式化的日志[/dim]")
                log_widget.write("[dim]• TXT 文件: 用文本编辑器打开阅读详细日志[/dim]")
                log_widget.write("[dim]• JSON 文件: 供程序化分析或其他工具使用[/dim]")
                log_widget.write("[dim]• YAML 文件: 人类可读的结构化数据格式[/dim]")

            else:
                log_widget.write("[red]❌ 所有格式的日志导出都失败了[/red]")

        except Exception as e:
            log_widget.write(f"[red]❌ 导出日志时发生错误: {e}[/red]")