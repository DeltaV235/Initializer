"""Sudo密码输入Modal - 安全的密码输入界面组件."""

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Static, Input, Label
from textual.events import Key
from typing import Optional


class SudoPasswordModal(ModalScreen[Optional[str]]):
    """Sudo密码输入Modal - 提供安全的密码输入界面."""

    BINDINGS = [
        ("escape", "cancel_modal", "取消"),
        ("enter", "confirm_password", "确认"),
    ]

    # CSS样式
    CSS = """
    SudoPasswordModal {
        align: center middle;
    }

    #password-modal-title {
        text-style: bold;
        color: $warning;
        margin: 0 0 1 0;
        text-align: center;
        height: auto;
        min-height: 1;
    }

    #password-modal-description {
        color: $text;
        margin: 0 0 2 0;
        text-align: center;
        height: auto;
        min-height: 2;
    }

    #password-input {
        margin: 0 0 2 0;
        width: 100%;
        border: round $primary;
        background: $surface;
    }

    .password-input-field {
        border: round $primary;
        background: $surface;
        color: $text;
        padding: 0 1;
    }

    .password-input-field:focus {
        border: round $accent;
        background: $surface;
    }

    #error-message {
        color: $error;
        margin: 1 0;
        text-align: center;
        height: auto;
        min-height: 1;
        background: $surface;
    }

    #retry-info {
        color: $warning;
        margin: 0 0 1 0;
        text-align: center;
        height: auto;
        min-height: 1;
        background: $surface;
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

    #help-box {
        dock: bottom;
        width: 100%;
        height: 3;
        border: round white;
        background: $surface;
        padding: 0 1;
        margin: 0;
    }
    """

    def __init__(self, retry_count: int = 0, max_retries: int = 3, error_message: str = ""):
        """初始化密码输入Modal.

        Args:
            retry_count: 当前重试次数
            max_retries: 最大重试次数
            error_message: 错误信息（如果有的话）
        """
        super().__init__()
        self.retry_count = retry_count
        self.max_retries = max_retries
        self.error_message = error_message

    def on_mount(self) -> None:
        """初始化屏幕，自动聚焦到密码输入框."""
        self.focus()
        # 延迟聚焦到密码输入框，确保组件已经完全渲染
        self.call_after_refresh(self._focus_password_input)

    def _focus_password_input(self) -> None:
        """聚焦到密码输入框."""
        try:
            password_input = self.query_one("#password-input", Input)
            password_input.focus()
        except:
            pass  # 如果找不到组件就忽略

    def can_focus(self) -> bool:
        """允许Modal接收焦点."""
        return True

    @property
    def is_modal(self) -> bool:
        """标记为Modal屏幕."""
        return True

    def compose(self) -> ComposeResult:
        """构建Modal界面."""
        with Container(classes="modal-container-xs"):
            # 标题
            yield Static("🔒 管理员权限验证", id="password-modal-title")

            # 描述信息
            if self.retry_count == 0:
                description = "需要管理员权限以继续操作。\n请输入您的系统密码："
            else:
                description = "权限验证失败，请重新输入您的系统密码："
            yield Static(description, id="password-modal-description")

            # 错误信息显示（如果有）
            if self.error_message:
                yield Static(f"❌ {self.error_message}", id="error-message")

            # 重试信息显示
            if self.retry_count > 0:
                remaining = self.max_retries - self.retry_count
                if remaining > 0:
                    retry_text = f"⚠️ 第 {self.retry_count + 1} 次尝试，还可以重试 {remaining} 次"
                else:
                    retry_text = f"⚠️ 最后一次尝试，失败后将取消操作"
                yield Static(retry_text, id="retry-info")

            # 密码输入框 - 使用更简洁的原生输入
            yield Input(
                placeholder="请输入系统密码...",
                password=True,
                id="password-input",
                classes="password-input-field"
            )


            # 底部帮助区域 - 与 Package 模块保持一致
            with Container(id="help-box"):
                yield Label("Enter=确认 | Esc=取消", classes="help-text")

    @on(Key)
    def handle_key_event(self, event: Key) -> None:
        """处理键盘事件."""
        if event.key == "enter":
            self.action_confirm_password()
            event.prevent_default()
            event.stop()
        elif event.key == "escape":
            self.action_cancel_modal()
            event.prevent_default()
            event.stop()


    @on(Input.Submitted, "#password-input")
    def on_password_submitted(self) -> None:
        """密码输入框回车提交."""
        self.action_confirm_password()

    def action_confirm_password(self) -> None:
        """确认密码输入."""
        try:
            password_input = self.query_one("#password-input", Input)
            password = password_input.value.strip()

            if not password:
                # 显示错误信息
                self._show_error("密码不能为空")
                password_input.focus()
                return

            # 返回密码
            self.dismiss(password)

        except Exception as e:
            self._show_error(f"获取密码时出错: {str(e)}")

    def action_cancel_modal(self) -> None:
        """取消密码输入."""
        self.dismiss(None)

    def _show_error(self, message: str) -> None:
        """显示错误信息.

        Args:
            message: 错误信息
        """
        try:
            # 尝试更新现有的错误信息组件
            error_widget = self.query_one("#error-message", Static)
            error_widget.update(f"❌ {message}")
        except:
            # 如果错误信息组件不存在，创建临时提示
            try:
                password_input = self.query_one("#password-input", Input)
                password_input.placeholder = f"错误: {message}"
                # 短暂延迟后恢复原始placeholder
                self.call_later(self._reset_placeholder)
            except:
                pass  # 忽略所有异常

    def _reset_placeholder(self) -> None:
        """重置密码输入框的placeholder."""
        try:
            password_input = self.query_one("#password-input", Input)
            password_input.placeholder = "请输入密码..."
        except:
            pass


class SudoRetryModal(ModalScreen[bool]):
    """Sudo重试确认Modal - 询问用户是否继续重试."""

    BINDINGS = [
        ("escape", "cancel_retry", "取消"),
        ("enter", "confirm_retry", "重试"),
        ("y", "confirm_retry", "是"),
        ("n", "cancel_retry", "否"),
    ]

    # CSS样式
    CSS = """
    SudoRetryModal {
        align: center middle;
    }

    #retry-modal-title {
        text-style: bold;
        color: $error;
        margin: 0 0 1 0;
        text-align: center;
        height: auto;
        min-height: 1;
    }

    #retry-modal-message {
        color: $text;
        margin: 0 0 2 0;
        text-align: center;
        height: auto;
        min-height: 3;
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

    #help-box {
        dock: bottom;
        width: 100%;
        height: 3;
        border: round white;
        background: $surface;
        padding: 0 1;
        margin: 0;
    }
    """

    def __init__(self, retry_count: int, max_retries: int, error_message: str = ""):
        """初始化重试确认Modal.

        Args:
            retry_count: 当前重试次数
            max_retries: 最大重试次数
            error_message: 错误信息
        """
        super().__init__()
        self.retry_count = retry_count
        self.max_retries = max_retries
        self.error_message = error_message

    def on_mount(self) -> None:
        """初始化屏幕."""
        self.focus()

    def can_focus(self) -> bool:
        """允许Modal接收焦点."""
        return True

    @property
    def is_modal(self) -> bool:
        """标记为Modal屏幕."""
        return True

    def compose(self) -> ComposeResult:
        """构建Modal界面."""
        with Container(classes="modal-container-xs"):
            # 标题
            yield Static("❌ 权限验证失败", id="retry-modal-title")

            # 消息内容
            remaining = self.max_retries - self.retry_count
            if remaining > 0:
                message = f"密码验证失败。\n\n{self.error_message}\n\n还可以重试 {remaining} 次，是否继续？"
            else:
                message = f"密码验证失败。\n\n{self.error_message}\n\n已达到最大重试次数，操作将被取消。"

            yield Static(message, id="retry-modal-message")


            # 底部帮助区域 - 与 Package 模块保持一致
            remaining = self.max_retries - self.retry_count
            with Container(id="help-box"):
                if remaining > 0:
                    yield Label("Enter/Y=重试 | Esc/N=取消", classes="help-text")
                else:
                    yield Label("Enter=确定", classes="help-text")

    @on(Key)
    def handle_key_event(self, event: Key) -> None:
        """处理键盘事件."""
        remaining = self.max_retries - self.retry_count

        if event.key == "enter":
            if remaining > 0:
                self.action_confirm_retry()
            else:
                self.action_cancel_retry()
            event.prevent_default()
            event.stop()
        elif event.key == "escape" or event.key == "n":
            self.action_cancel_retry()
            event.prevent_default()
            event.stop()
        elif event.key == "y" and remaining > 0:
            self.action_confirm_retry()
            event.prevent_default()
            event.stop()


    def action_confirm_retry(self) -> None:
        """确认重试."""
        self.dismiss(True)

    def action_cancel_retry(self) -> None:
        """取消重试."""
        self.dismiss(False)