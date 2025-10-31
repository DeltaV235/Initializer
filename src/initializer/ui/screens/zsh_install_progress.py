"""Zsh Installation Progress Modal."""

import asyncio
from typing import Optional

from textual import work
from textual.app import ComposeResult
from textual.containers import Container, Vertical, ScrollableContainer
from textual.events import Key
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Rule, Static

from ...modules.zsh_manager import ZshManager
from ...utils.logger import get_ui_logger

logger = get_ui_logger("zsh_install_progress")


class ZshInstallProgress(ModalScreen[dict]):
    """Progress modal for Zsh install/uninstall operations."""

    BINDINGS = [
        ("escape", "dismiss", "Close"),
        ("j", "scroll_down", "Scroll Down"),
        ("k", "scroll_up", "Scroll Up"),
    ]

    # Reactive 变量用于状态管理
    is_running = reactive(False)
    is_completed = reactive(False)

    CSS = """
    ZshInstallProgress {
        align: center middle;
    }

    #progress-title {
        text-style: bold;
        color: $text;
        margin: 0 0 1 0;
        text-align: center;
    }

    #log-container {
        height: 1fr;
        overflow-y: auto;
        padding: 0 1;
        scrollbar-size: 1 1;
        background: $surface;
    }

    #log-output {
        height: auto;
        min-height: 1;
        background: $surface;
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
    """

    def __init__(
        self,
        target: str,  # "zsh", "ohmyzsh", "plugin", "shell", "config_migration"
        operation: str,  # "install", "uninstall", "change", "migrate"
        zsh_manager: Optional[ZshManager] = None,
        package_manager: Optional[str] = None,
        plugin: Optional[dict] = None,
        shell_path: Optional[str] = None,
        configs: Optional[list] = None,
        completion_callback: Optional[callable] = None,
    ):
        super().__init__()
        self.target = target
        self.operation = operation
        self.zsh_manager = zsh_manager or ZshManager()
        self.package_manager = package_manager
        self.plugin = plugin
        self.shell_path = shell_path
        self.configs = configs
        self.completion_callback = completion_callback

    def compose(self) -> ComposeResult:
        """Compose the progress modal."""
        with Container(classes="modal-container-xl"):
            # 标题
            title_map = {
                ("zsh", "install"): "Installing Zsh",
                ("zsh", "uninstall"): "Uninstalling Zsh",
                ("ohmyzsh", "install"): "Installing Oh-my-zsh",
                ("ohmyzsh", "uninstall"): "Uninstalling Oh-my-zsh",
                ("plugin", "install"): "Installing Plugin",
                ("plugin", "uninstall"): "Uninstalling Plugin",
                ("shell", "change"): "Changing Default Shell",
                ("config_migration", "migrate"): "Migrating Shell Configurations",
            }
            yield Static(
                title_map.get((self.target, self.operation), "Processing..."),
                id="progress-title",
            )

            yield Rule()

            # 日志输出区域
            with ScrollableContainer(id="log-container"):
                with Vertical(id="log-output"):
                    yield Static("Starting operation...", classes="log-line")

            # Help text 使用全局样式
            with Container(id="help-box"):
                yield Static("", id="help-text", classes="help-text")

    def on_mount(self) -> None:
        """初始化 modal 并启动操作。"""
        self.focus()
        self.is_running = True  # 在组件挂载后设置，避免 watch 方法过早触发
        self._execute_operation()

    def watch_is_running(self, old: bool, new: bool) -> None:
        """根据运行状态动态更新 help text。"""
        try:
            help_widget = self.query_one("#help-text", Static)
            if new and not self.is_completed:
                help_widget.update("Operation in progress, please wait...")
            elif self.is_completed:
                help_widget.update("Esc=Close | J/K=Scroll")
        except Exception as exc:
            logger.debug(f"Failed to update help text: {exc}")

    def on_key(self, event: Key) -> None:
        """处理键盘事件，仅在操作完成后允许关闭。"""
        if event.key == "escape":
            if self.is_completed:
                self.action_dismiss()
            else:
                logger.debug("Operation not completed, ignoring ESC")
            event.prevent_default()
            event.stop()

    def action_dismiss(self) -> None:
        """处理 modal 关闭请求，安装中拒绝关闭。"""
        if self.is_running and not self.is_completed:
            logger.debug("Dismiss blocked: operation in progress")
            return

        result = getattr(self, 'result', {})

        # 如果有 completion_callback，先调用它
        if self.completion_callback:
            try:
                self.completion_callback(result)
            except Exception as exc:
                logger.error(f"Completion callback failed: {exc}", exc_info=True)

        self.dismiss(result)

    def action_scroll_down(self) -> None:
        """向下滚动日志内容。"""
        # 运行时不允许滚动
        if self.is_running and not self.is_completed:
            logger.debug("Scroll blocked: operation in progress")
            return

        try:
            log_container = self.query_one("#log-container", ScrollableContainer)
            log_container.scroll_down(animate=False)
        except Exception as exc:
            logger.warning(f"Failed to scroll down: {exc}")

    def action_scroll_up(self) -> None:
        """向上滚动日志内容。"""
        # 运行时不允许滚动
        if self.is_running and not self.is_completed:
            logger.debug("Scroll blocked: operation in progress")
            return

        try:
            log_container = self.query_one("#log-container", ScrollableContainer)
            log_container.scroll_up(animate=False)
        except Exception as exc:
            logger.warning(f"Failed to scroll up: {exc}")

    @work(exclusive=True, thread=True)
    async def _execute_operation(self) -> None:
        """Execute the install/uninstall operation."""
        try:
            def progress_callback(line: str) -> None:
                """进度回调函数，追加日志到输出区域。"""
                self.app.call_from_thread(self._append_log, line)

            result = None

            if self.target == "zsh":
                if self.operation == "install":
                    result = await self.zsh_manager.install_zsh(
                        self.package_manager, progress_callback
                    )
                else:  # uninstall
                    result = await self.zsh_manager.uninstall_zsh(
                        self.package_manager, progress_callback
                    )

            elif self.target == "ohmyzsh":
                if self.operation == "install":
                    # 从配置获取 install_url
                    from ...config_manager import ConfigManager

                    config_manager = ConfigManager()
                    modules_config = config_manager.get_modules_config()
                    zsh_config = modules_config.get("zsh_management")

                    # 获取 ohmyzsh 安装 URL
                    default_url = "https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh"
                    if zsh_config and "ohmyzsh" in zsh_config.settings:
                        install_url = zsh_config.settings["ohmyzsh"].get("install_url", default_url)
                    else:
                        install_url = default_url

                    result = await self.zsh_manager.install_ohmyzsh(
                        install_url, progress_callback
                    )
                else:  # uninstall
                    result = await self.zsh_manager.uninstall_ohmyzsh(progress_callback)

            elif self.target == "plugin":
                if self.operation == "install":
                    result = await self.zsh_manager.install_plugin(
                        self.plugin, progress_callback
                    )
                else:  # uninstall
                    result = await self.zsh_manager.uninstall_plugin(
                        self.plugin, progress_callback
                    )

            elif self.target == "shell":
                result = await self.zsh_manager.change_default_shell(
                    self.shell_path, progress_callback
                )

            elif self.target == "config_migration":
                result = await self.zsh_manager.migrate_shell_configs(
                    self.configs, progress_callback=progress_callback
                )

            # 更新状态文本
            if result and result.get("success"):
                logger.info(f"Operation completed successfully: {self.target} {self.operation}")
                self.app.call_from_thread(
                    self._update_status, "✓ Operation completed successfully!", "success"
                )
                self.app.call_from_thread(self._add_completion_hint)
            else:
                error = result.get("error", "Unknown error") if result else "Unknown error"
                logger.error(f"Operation failed: {error}")
                self.app.call_from_thread(
                    self._update_status, f"✗ Operation failed: {error}", "error"
                )
                self.app.call_from_thread(self._add_completion_hint)

            # 保存 result 供 action_dismiss 使用
            self.app.call_from_thread(lambda: setattr(self, 'result', result or {}))

        except Exception as exc:
            logger.error(f"Operation failed: {exc}", exc_info=True)
            self.app.call_from_thread(
                self._update_status, f"✗ Error: {str(exc)}", "error"
            )
            self.app.call_from_thread(self._add_completion_hint)
            # 保存错误 result 供 action_dismiss 使用
            error_result = {"success": False, "error": str(exc), "output": ""}
            self.app.call_from_thread(lambda: setattr(self, 'result', error_result))

    def _append_log(self, line: str, log_type: str = "normal") -> None:
        """追加日志行到输出区域，带时间戳和分类。

        Args:
            line: 日志内容
            log_type: 日志类型（"normal", "success", "error", "warning"）
        """
        try:
            from datetime import datetime
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_line = f"[{timestamp}] {line}"

            # CSS 类映射
            css_class = {
                "success": "log-line-success",
                "error": "log-line-error",
                "warning": "log-line-warning",
            }.get(log_type, "log-line")

            # 挂载新 widget 到 Vertical 容器
            log_container = self.query_one("#log-output", Vertical)
            log_container.mount(Static(log_line, classes=css_class, markup=False))

            # 限制日志行数（保留最近100行）
            if len(log_container.children) > 100:
                log_container.children[0].remove()

            # 自动滚动到底部
            scroll_container = self.query_one("#log-container", ScrollableContainer)
            scroll_container.scroll_end(animate=False)
        except Exception as exc:
            logger.error(f"Failed to append log: {exc}")

    def _update_status(self, message: str, status: str) -> None:
        """更新状态并添加到日志。"""
        try:
            if status == "success":
                self._append_log(message, "success")
            elif status == "error":
                self._append_log(message, "error")
            else:
                self._append_log(message, "normal")
        except Exception as exc:
            logger.error(f"Failed to update status: {exc}")

    def _add_completion_hint(self) -> None:
        """操作完成后更新状态标志并触发 help text 更新。"""
        self.is_completed = True
        self.is_running = False
        # watch_is_running 会自动触发，更新 help text 为 "Press Esc to close"
