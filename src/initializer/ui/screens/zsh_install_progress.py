"""Zsh Installation Progress Modal."""

import asyncio
from typing import Optional

from textual import work
from textual.app import ComposeResult
from textual.containers import Container, ScrollableContainer
from textual.screen import ModalScreen
from textual.widgets import Rule, Static

from ...modules.zsh_manager import ZshManager
from ...utils.logger import get_ui_logger

logger = get_ui_logger("zsh_install_progress")


class ZshInstallProgress(ModalScreen[dict]):
    """Progress modal for Zsh install/uninstall operations."""

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
        height: 20;
        border: solid $primary;
        padding: 1;
        margin: 1 0;
    }

    #log-output {
        color: $text;
    }

    #status-text {
        text-align: center;
        color: $text;
        margin: 1 0;
        text-style: bold;
    }

    .help-text {
        text-align: center;
        color: $text-muted;
        margin: 1 0 0 0;
    }
    """

    def __init__(
        self,
        target: str,  # "zsh", "ohmyzsh", "plugin", "shell"
        operation: str,  # "install", "uninstall", "change"
        zsh_manager: ZshManager,
        package_manager: Optional[str] = None,
        plugin: Optional[dict] = None,
        shell_path: Optional[str] = None,
    ):
        super().__init__()
        self.target = target
        self.operation = operation
        self.zsh_manager = zsh_manager
        self.package_manager = package_manager
        self.plugin = plugin
        self.shell_path = shell_path

    def compose(self) -> ComposeResult:
        """Compose the progress modal."""
        with Container(classes="modal-container-lg"):
            # 标题
            title_map = {
                ("zsh", "install"): "Installing Zsh",
                ("zsh", "uninstall"): "Uninstalling Zsh",
                ("ohmyzsh", "install"): "Installing Oh-my-zsh",
                ("ohmyzsh", "uninstall"): "Uninstalling Oh-my-zsh",
                ("plugin", "install"): "Installing Plugin",
                ("plugin", "uninstall"): "Uninstalling Plugin",
                ("shell", "change"): "Changing Default Shell",
            }
            yield Static(
                title_map.get((self.target, self.operation), "Processing..."),
                id="progress-title",
            )

            yield Rule()

            # 日志输出区域
            with ScrollableContainer(id="log-container"):
                yield Static("", id="log-output")

            yield Rule()

            # 状态文本
            yield Static("Operation in progress...", id="status-text")

            yield Static("Please wait...", classes="help-text")

    def on_mount(self) -> None:
        """Start the operation when mounted."""
        self._execute_operation()

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

            # 更新状态文本
            if result and result.get("success"):
                logger.info(f"Operation completed successfully: {self.target} {self.operation}")
                self.app.call_from_thread(
                    self._update_status, "✓ Operation completed successfully!", "success"
                )
            else:
                error = result.get("error", "Unknown error") if result else "Unknown error"
                logger.error(f"Operation failed: {error}")
                self.app.call_from_thread(
                    self._update_status, f"✗ Operation failed: {error}", "error"
                )

            # 延迟 2 秒后自动关闭
            await asyncio.sleep(2)
            self.app.call_from_thread(lambda: self.dismiss(result or {}))

        except Exception as exc:
            logger.error(f"Operation failed: {exc}", exc_info=True)
            self.app.call_from_thread(
                self._update_status, f"✗ Error: {str(exc)}", "error"
            )
            await asyncio.sleep(2)
            self.app.call_from_thread(
                lambda: self.dismiss({"success": False, "error": str(exc), "output": ""})
            )

    def _append_log(self, line: str) -> None:
        """追加日志到输出区域。"""
        try:
            log_widget = self.query_one("#log-output", Static)
            current_text = str(log_widget.renderable)
            if current_text:
                log_widget.update(f"{current_text}\n{line}")
            else:
                log_widget.update(line)

            # 自动滚动到底部
            container = self.query_one("#log-container", ScrollableContainer)
            container.scroll_end(animate=False)
        except Exception as exc:
            logger.error(f"Failed to append log: {exc}")

    def _update_status(self, message: str, status: str) -> None:
        """更新状态文本。"""
        try:
            status_widget = self.query_one("#status-text", Static)
            if status == "success":
                status_widget.update(f"[green]{message}[/green]")
            elif status == "error":
                status_widget.update(f"[red]{message}[/red]")
            else:
                status_widget.update(message)
        except Exception as exc:
            logger.error(f"Failed to update status: {exc}")
