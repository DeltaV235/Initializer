"""Application Installation Confirmation."""

from textual import on, work
from textual.app import ComposeResult
from textual.containers import Container, ScrollableContainer
from textual.screen import ModalScreen
from textual.widgets import Static, Rule, Label
from textual.events import Key
from typing import Callable, List, Dict, Optional
from ...modules.sudo_manager import SudoManager
from .sudo_prompt import SudoPrompt, SudoRetry
from ...utils.logger import get_module_logger


class AppInstallConfirm(ModalScreen):
    """Screen for confirming application installation/uninstallation."""
    
    BINDINGS = [
        ("escape", "cancel_operation", "Cancel"),
        ("y", "confirm_change", "Yes"),
        ("n", "cancel_operation", "No"),
        ("j", "scroll_down", "Scroll Down"),
        ("k", "scroll_up", "Scroll Up"),
        ("down", "scroll_down", "Scroll Down"),
        ("up", "scroll_up", "Scroll Up"),
        ("pagedown", "scroll_page_down", "Page Down"),
        ("pageup", "scroll_page_up", "Page Up"),
    ]
    
    # CSS styles for the modal - only custom styles not covered by global styles
    CSS = """
    AppInstallConfirm {
        align: center middle;
    }

    .action-header {
        text-style: bold;
        color: $text;
        margin: 1 0 0 0;
        height: auto;
        min-height: 1;
    }

    .action-item {
        margin: 0 0 0 2;
        color: $text;
        height: auto;
        min-height: 1;
        background: $surface;
    }

    .command-display {
        margin: 0 0 0 2;
        padding: 1;
        background: $boost;
        border: round #7dd3fc;
        color: $text;
        height: auto;
        min-height: 1;
    }

    .warning-text {
        color: #f59e0b;
        text-style: bold;
        margin: 1 0;
        height: auto;
        min-height: 1;
        background: $surface;
    }
    """
    
    def __init__(self, actions: List[Dict], callback: Callable[[bool, Optional[SudoManager]], None], app_installer):
        super().__init__()
        self.actions = actions
        self.callback = callback
        self.app_installer = app_installer

        # 初始化logger和sudo管理器
        self.logger = get_module_logger("app_install_confirmation_modal")
        self.sudo_manager = SudoManager()

        # 防止立即确认的标志
        self._just_opened = True

        self.logger.info(f"AppInstallConfirm initialized with {len(actions)} actions")
    
    def on_mount(self) -> None:
        """Initialize the screen."""
        self.focus()
        # 延迟一小段时间后允许键盘确认，防止立即触发
        self.set_timer(0.5, self._enable_keyboard_confirm)
    
    def _enable_keyboard_confirm(self) -> None:
        """Enable keyboard confirmation after a short delay."""
        self._just_opened = False

    def can_focus(self) -> bool:
        """Return True to allow this modal to receive focus."""
        return True
    
    @property
    def is_modal(self) -> bool:
        """Mark this as a modal screen."""
        return True
    
    @on(Key)
    def handle_key_event(self, event: Key) -> None:
        """Handle key events using @on decorator for reliable event processing."""
        if event.key == "enter":
            # 防止立即确认（刚打开对话框时）
            if self._just_opened:
                self.logger.debug("Ignoring Enter key - dialog just opened")
                event.prevent_default()
                event.stop()
                return
            self.action_confirm_change()
            event.prevent_default()
            event.stop()
        elif event.key == "escape":
            self.action_cancel_operation()
            event.prevent_default()
            event.stop()
        elif event.key == "y":
            # Y键也需要检查延迟
            if self._just_opened:
                self.logger.debug("Ignoring Y key - dialog just opened")
                event.prevent_default()
                event.stop()
                return
            self.action_confirm_change()
            event.prevent_default()
            event.stop()
        elif event.key == "n":
            self.action_cancel_operation()
            event.prevent_default()
            event.stop()
    
    def compose(self) -> ComposeResult:
        """Compose the modal interface."""
        with Container(classes="modal-container-lg"):
            yield Static("⚠️ Confirm Application Installation/Uninstallation", id="confirmation-title")
            yield Rule()

            with ScrollableContainer(id="confirmation-content"):
                # Group actions by type
                install_actions = [a for a in self.actions if a["action"] == "install"]
                uninstall_actions = [a for a in self.actions if a["action"] == "uninstall"]
                
                if install_actions:
                    yield Label("Applications to Install:", classes="action-header")
                    for action in install_actions:
                        app = action["application"]
                        yield Static(f"• {app.name} - {app.description}", 
                                   classes="action-item")
                        
                        # Show install command
                        command = self.app_installer.get_install_command(app)
                        if command:
                            yield Label("  Command:", classes="action-item")
                            # Truncate long commands for display
                            display_cmd = command if len(command) < 100 else command[:97] + "..."
                            yield Static(f"  {display_cmd}", classes="command-display")
                        
                        # Show post-install command if any
                        if app.post_install:
                            yield Label("  Post-install Configuration:", classes="action-item")
                            display_post = app.post_install if len(app.post_install) < 100 else app.post_install[:97] + "..."
                            yield Static(f"  {display_post}", classes="command-display")
                
                if uninstall_actions:
                    if install_actions:
                        yield Static("")  # Spacer
                    yield Label("Applications to Uninstall:", classes="action-header")
                    for action in uninstall_actions:
                        app = action["application"]
                        yield Static(f"• {app.name} - {app.description}", 
                                   classes="action-item")
                        
                        # Show uninstall command
                        command = self.app_installer.get_uninstall_command(app)
                        if command:
                            yield Label("  Command:", classes="action-item")
                            # Truncate long commands for display
                            display_cmd = command if len(command) < 100 else command[:97] + "..."
                            yield Static(f"  {display_cmd}", classes="command-display")
                
                # Warning message
                yield Static("")  # Spacer
                if uninstall_actions:
                    yield Static("⚠️ Warning: Uninstalling applications may affect system functionality!",
                               classes="warning-text")
                
                # Summary
                yield Static("")  # Spacer
                yield Label(f"Total: {len(install_actions)} to install, {len(uninstall_actions)} to uninstall",
                          classes="section-header")
            

            # Fixed action help at the bottom - mimic mirror confirmation modal style exactly
            with Container(id="help-box"):
                yield Label("J/K=Up/Down | Enter=Confirm | Esc=Cancel", classes="help-text")

    def action_confirm_change(self) -> None:
        """Confirm the installation/uninstallation."""
        self.logger.info("User confirmed installation/uninstallation")
        self.logger.info("About to start confirmation process...")
        try:
            self._start_confirmation_process()
            self.logger.info("_start_confirmation_process() call completed")
        except Exception as e:
            self.logger.error(f"Exception in action_confirm_change: {e}", exc_info=True)
            # 确保出错时也调用callback
            self.callback(False, None)
            self.dismiss()

    @work(exclusive=True)
    async def _start_confirmation_process(self) -> None:
        """开始确认流程，检查sudo权限并处理密码验证."""
        try:
            self.logger.info("=== Starting confirmation process ===")
            self.logger.info(f"App instance: {self.app}")
            self.logger.info(f"Callback function: {self.callback}")
            self.logger.info(f"Actions count: {len(self.actions)}")

            # 检查是否需要sudo权限
            self.logger.info("About to check sudo requirement...")
            needs_sudo = self._check_sudo_required()
            self.logger.info(f"Sudo check completed - Sudo required: {needs_sudo}")

            if needs_sudo:
                # 需要sudo权限，进行权限验证流程
                self.logger.info("=== Sudo verification required ===")
                self.logger.info("Starting sudo verification process")

                # 如果是root用户，创建伪造的验证成功状态
                if self.sudo_manager.is_root_user():
                    self.logger.info("Root用户跳过密码验证，直接设置验证状态")
                    # Root用户不需要密码验证，直接标记为已验证
                    self.sudo_manager._verified = True
                    success = True
                else:
                    # 非root用户进行正常的密码验证流程
                    success = await self._handle_sudo_verification()

                self.logger.info(f"=== Sudo verification completed - Result: {success} ===")

                if success:
                    # sudo验证成功，继续操作
                    self.logger.info("=== Sudo verification successful, calling callback ===")
                    self.logger.info(f"About to call callback with (True, {self.sudo_manager})")
                    self.callback(True, self.sudo_manager)
                    self.logger.info("Callback called successfully, about to dismiss modal")
                    self.dismiss()
                    self.logger.info("Modal dismissed successfully")
                else:
                    # sudo验证失败，取消操作
                    self.logger.warning("=== Sudo verification failed, cancelling operation ===")
                    self.logger.info("About to call callback with (False, None)")
                    self.callback(False, None)
                    self.logger.info("Callback called, about to dismiss modal")
                    self.dismiss()
                    self.logger.info("Modal dismissed")
            else:
                # 不需要sudo权限，直接继续
                self.logger.info("=== No sudo required, proceeding without sudo ===")
                self.logger.info("About to call callback with (True, None)")
                self.callback(True, None)
                self.logger.info("Callback called successfully, about to dismiss modal")
                self.dismiss()
                self.logger.info("Modal dismissed successfully")

        except Exception as e:
            self.logger.error(f"=== CRITICAL ERROR in confirmation process: {e} ===", exc_info=True)
            # 出错时取消操作
            try:
                self.logger.info("About to call callback with (False, None) due to error")
                self.callback(False, None)
                self.logger.info("Error callback called successfully, about to dismiss")
                self.dismiss()
                self.logger.info("Modal dismissed after error")
            except Exception as callback_error:
                self.logger.error(f"Error in error handling callback: {callback_error}", exc_info=True)

    def _check_sudo_required(self) -> bool:
        """检查是否有命令需要sudo权限.

        Returns:
            True如果有命令需要sudo权限且不是root用户，False否则
        """
        try:
            self.logger.debug("Checking if sudo is required for actions")

            # 如果是root用户，直接返回False（不需要sudo权限验证）
            if self.sudo_manager.is_root_user():
                self.logger.info("当前用户是root，无需sudo权限验证")
                return False

            for action in self.actions:
                app = action["application"]

                if action["action"] == "install":
                    command = self.app_installer.get_install_command(app)
                    self.logger.debug(f"Install command for {app.name}: {command}")
                else:  # uninstall
                    command = self.app_installer.get_uninstall_command(app)
                    self.logger.debug(f"Uninstall command for {app.name}: {command}")

                if command and self.sudo_manager.is_sudo_required(command):
                    self.logger.info(f"Sudo required for {app.name} ({action['action']})")
                    return True

            self.logger.info("No sudo required for any actions")
            return False
        except Exception as e:
            self.logger.error(f"Error checking sudo requirement: {e}", exc_info=True)
            return False

    async def _handle_sudo_verification(self) -> bool:
        """处理sudo权限验证流程.

        Returns:
            True如果验证成功，False如果验证失败或用户取消
        """
        try:
            self.logger.info("Starting sudo verification")

            # 检查sudo是否可用
            if not self.sudo_manager.check_sudo_available():
                self.logger.error("Sudo is not available on this system")
                # 显示sudo不可用的错误信息
                await self._show_sudo_unavailable_error()
                return False

            self.logger.info("Sudo is available, starting password verification loop")

            # 开始密码验证循环
            while self.sudo_manager.is_retry_available():
                self.logger.debug(f"Retry attempt {self.sudo_manager.get_retry_count() + 1}")

                # 显示密码输入modal
                password = await self._show_password_modal()

                if password is None:
                    # 用户取消了密码输入
                    self.logger.info("User cancelled password input")
                    return False

                self.logger.info("Password provided, verifying...")

                # 验证密码
                success, error_message = self.sudo_manager.verify_sudo_access(password)

                if success:
                    # 验证成功
                    self.logger.info("Sudo password verification successful")
                    return True
                else:
                    # 验证失败，检查是否还可以重试
                    self.logger.warning(f"Sudo password verification failed: {error_message}")

                    if self.sudo_manager.is_retry_available():
                        # 询问用户是否重试
                        should_retry = await self._show_retry_modal(error_message)
                        if not should_retry:
                            self.logger.info("User chose not to retry")
                            return False
                    else:
                        # 已达到最大重试次数
                        self.logger.error("Maximum retry attempts reached")
                        await self._show_retry_modal(error_message)  # 显示最终错误信息
                        return False

            self.logger.error("Exhausted all retry attempts")
            return False

        except Exception as e:
            self.logger.error(f"Error in sudo verification: {e}", exc_info=True)
            return False

    async def _show_password_modal(self) -> Optional[str]:
        """显示密码输入modal.

        Returns:
            用户输入的密码，如果用户取消则返回None
        """
        password_modal = SudoPrompt(
            retry_count=self.sudo_manager.get_retry_count(),
            max_retries=3
        )

        password = await self.app.push_screen_wait(password_modal)
        return password

    async def _show_retry_modal(self, error_message: str) -> bool:
        """显示重试确认modal.

        Args:
            error_message: 错误信息

        Returns:
            True如果用户选择重试，False如果用户取消
        """
        retry_modal = SudoRetry(
            retry_count=self.sudo_manager.get_retry_count(),
            max_retries=3,
            error_message=error_message
        )

        should_retry = await self.app.push_screen_wait(retry_modal)
        return should_retry or False

    async def _show_sudo_unavailable_error(self) -> None:
        """显示sudo不可用的错误信息."""
        error_modal = SudoRetry(
            retry_count=3,  # 显示为已达到最大重试次数
            max_retries=3,
            error_message="系统未安装sudo或当前用户无权限使用sudo"
        )

        await self.app.push_screen_wait(error_modal)

    def action_cancel_operation(self) -> None:
        """Cancel the operation."""
        self.callback(False, None)
        self.dismiss()

    def action_scroll_down(self) -> None:
        """Scroll content down."""
        try:
            content = self.query_one("#confirmation-content", ScrollableContainer)
            content.scroll_down()
        except:
            pass

    def action_scroll_up(self) -> None:
        """Scroll content up."""
        try:
            content = self.query_one("#confirmation-content", ScrollableContainer)
            content.scroll_up()
        except:
            pass

    def action_scroll_page_down(self) -> None:
        """Scroll content page down."""
        try:
            content = self.query_one("#confirmation-content", ScrollableContainer)
            content.scroll_page_down()
        except:
            pass

    def action_scroll_page_up(self) -> None:
        """Scroll content page up."""
        try:
            content = self.query_one("#confirmation-content", ScrollableContainer)
            content.scroll_page_up()
        except:
            pass