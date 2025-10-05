"""Vim Management Screen."""

from typing import Optional

from textual import work
from textual.app import ComposeResult
from textual.containers import ScrollableContainer
from textual.reactive import reactive
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import Label, Rule, Static

from ...modules.vim_manager import VimManager
from ...modules.package_manager import PackageManagerDetector
from ...config_manager import ConfigManager
from ...utils.logger import get_ui_logger
logger = get_ui_logger("vim_management")


VIM_MANAGEMENT_CSS = """
VimManagementPanel {
    padding: 1;
}

#vim-panel-scroll {
    height: 1fr;
    padding: 1;
}

.vim-info-line {
    color: $text;
    margin: 0 0 1 0;
}

.vim-action {
    color: $text;
    margin: 1 0 0 0;
}

.loading-text {
    text-align: center;
    color: $primary;
    text-style: bold;
    margin: 2 0;
}
"""


class VimManagementPanel(Widget):
    """Vim 管理功能的可复用面板组件。"""

    DEFAULT_CSS = VIM_MANAGEMENT_CSS

    nvim_info = reactive(None)
    lazyvim_info = reactive(None)
    is_loading = reactive(True)

    def __init__(self, config_manager: ConfigManager):
        super().__init__()
        self.config_manager = config_manager
        self.vim_manager = VimManager()

        pm_detector = PackageManagerDetector(config_manager)
        self.primary_pm = pm_detector.get_primary_package_manager()
        logger.info(
            f"Primary package manager: {self.primary_pm.name if self.primary_pm else 'None'}"
        )

        self.action_entries: list[dict] = []
        self.focus_index: Optional[int] = None

    def compose(self) -> ComposeResult:
        """构建 Vim 管理面板布局。"""
        with ScrollableContainer(id="vim-panel-scroll"):
            yield Static("Loading...", classes="loading-text")

    def on_mount(self) -> None:
        """初始化面板并加载 Vim 状态。"""
        self._show_loading()
        self._load_vim_status()

    def _update_help_text(self) -> None:
        """已废弃：保留占位以兼容旧逻辑。"""
        return None

    @work(exclusive=True, thread=True)
    async def _load_vim_status(self) -> None:
        """异步检测 NeoVim 与 LazyVim 状态。"""
        try:
            logger.info("Loading Vim status")

            self.nvim_info = await VimManager.detect_neovim()
            logger.debug(f"NeoVim info: {self.nvim_info}")

            self.lazyvim_info = await VimManager.detect_lazyvim()
            logger.debug(f"LazyVim info: {self.lazyvim_info}")

            self.is_loading = False

            def update_ui() -> None:
                self._update_content_display()
                self._notify_help_update()

            self.app.call_from_thread(update_ui)

        except Exception as exc:  # noqa: BLE001
            logger.error(f"Failed to load Vim status: {exc}", exc_info=True)
            self.is_loading = False

            def show_error() -> None:
                self._show_error(str(exc))
                self._notify_help_update()

            self.app.call_from_thread(show_error)

    def _get_content_container(self) -> ScrollableContainer:
        return self.query_one("#vim-panel-scroll", ScrollableContainer)

    def _clear_content(self) -> ScrollableContainer:
        container = self._get_content_container()
        for child in list(container.children):
            child.remove()
        return container

    def _show_loading(self) -> None:
        container = self._clear_content()
        container.styles.scrollbar_size = 0
        container.mount(Static("Loading...", classes="loading-text"))
        self._register_action_entries([])

    def _notify_help_update(self) -> None:
        """通知屏幕更新帮助文本。"""
        try:
            screen = self.app.screen if hasattr(self, 'app') and self.app else None
            if screen and hasattr(screen, "_update_help_text"):
                screen._update_help_text()
        except Exception as exc:  # noqa: BLE001
            logger.debug(f"Failed to notify help update: {exc}")

    def _register_action_entries(self, entries: list[dict]) -> None:
        """记录可交互的操作条目并刷新指示。"""
        self.action_entries = entries
        self.focus_index = 0 if entries else None
        self._refresh_action_labels()
        self._notify_help_update()

    def _refresh_action_labels(self) -> None:
        """根据焦点状态刷新箭头指示。"""
        for index, entry in enumerate(self.action_entries):
            widget = entry.get("widget")
            if not widget:
                continue
            prefix = "[#7dd3fc]\u25b6[/#7dd3fc] " if (self._is_active() and self.focus_index == index) else "  "
            widget.update(f"{prefix}{entry['label']}")

    def _is_active(self) -> bool:
        """检查当前面板是否处于激活状态。"""
        try:
            # Try to get screen from app
            screen = self.app.screen if hasattr(self, 'app') and self.app else None
            if not screen:
                logger.debug("Cannot determine screen from app")
                return False

            # Check if this is a MainMenuScreen with the required attributes
            has_segment = hasattr(screen, 'selected_segment')
            has_focus = hasattr(screen, 'current_panel_focus')

            if not (has_segment and has_focus):
                logger.debug(f"Screen missing required attributes: has_segment={has_segment}, has_focus={has_focus}")
                return False

            is_active = (
                screen.selected_segment == "vim_management"
                and screen.current_panel_focus == "right"
            )
            logger.debug(f"_is_active: segment={screen.selected_segment}, "
                        f"focus={screen.current_panel_focus}, result={is_active}")
            return is_active
        except Exception as e:
            logger.debug(f"Error in _is_active: {e}")
            return False

    def refresh_action_labels(self) -> None:
        """供外部调用以刷新箭头状态。"""
        self._refresh_action_labels()
        self._notify_help_update()

    def navigate(self, direction: str) -> None:
        """在操作条目之间移动焦点。"""
        if not self.action_entries:
            return

        if self.focus_index is None:
            self.focus_index = 0
        elif direction == "down":
            self.focus_index = min(len(self.action_entries) - 1, self.focus_index + 1)
        elif direction == "up":
            self.focus_index = max(0, self.focus_index - 1)

        self._refresh_action_labels()
        self._notify_help_update()

    def _current_action_entry(self) -> Optional[dict]:
        if self.focus_index is None:
            return None
        if 0 <= self.focus_index < len(self.action_entries):
            return self.action_entries[self.focus_index]
        return None

    def handle_enter(self) -> None:
        """处理回车键，执行当前选中操作。"""
        logger.debug(f"handle_enter called: focus_index={self.focus_index}, "
                    f"action_entries count={len(self.action_entries)}, "
                    f"is_loading={self.is_loading}")

        entry = self._current_action_entry()
        if not entry:
            logger.warning(f"No action entry found at focus_index={self.focus_index}")
            return

        logger.info(f"Triggering action: {entry.get('action')} - {entry.get('label')}")
        self._trigger_action(entry.get("action"))

    def _trigger_action(self, action: Optional[str]) -> None:
        if not action or self.is_loading:
            return

        if action == "install_neovim":
            self._open_neovim_confirm("install")
        elif action == "uninstall_neovim":
            self._open_neovim_confirm("uninstall")
        elif action == "install_lazyvim":
            self._open_lazyvim_confirm("install")
        elif action == "uninstall_lazyvim":
            self._open_lazyvim_confirm("uninstall")
        elif action == "upgrade_info":
            self._show_upgrade_info()
        else:
            logger.debug(f"Unknown Vim action: {action}")

    def get_help_text(self) -> str:
        base_prefix = "Esc=Back to Left Panel | TAB/H=Back to Left Panel | R=Refresh | J/K=Move"
        entry = self._current_action_entry()
        if entry:
            enter_hint = f"Enter={entry['label']}"
        else:
            enter_hint = "Enter=Select"
        return f"{base_prefix} | {enter_hint} | Q=Quit"

    def _update_content_display(self) -> None:
        """将最新检测结果渲染到面板。"""
        try:
            container = self._clear_content()
            container.styles.scrollbar_size = 1

            action_entries: list[dict] = []
            manager_name = (
                self.primary_pm.name
                if self.primary_pm and getattr(self.primary_pm, "name", None)
                else "system package manager"
            )

            # NeoVim 状态
            container.mount(Label("NeoVim Status", classes="section-header"))
            if self.nvim_info:
                if self.nvim_info.installed:
                    version_info = (
                        f"v{self.nvim_info.version}" if self.nvim_info.version else "Unknown"
                    )
                    container.mount(
                        Static(
                            f"• Status: [bold green]Installed[/bold green] ({version_info})",
                            classes="vim-info-line",
                        )
                    )
                    if self.nvim_info.path:
                        container.mount(
                            Static(
                                f"• Path: {self.nvim_info.path}",
                                classes="vim-info-line",
                            )
                        )
                    if self.nvim_info.meets_requirement:
                        container.mount(
                            Static(
                                f"• Compatibility: [bold green]Ready for LazyVim (>= {VimManager.MIN_NVIM_VERSION})[/bold green]",
                                classes="vim-info-line",
                            )
                        )
                    else:
                        container.mount(
                            Static(
                                f"• Compatibility: [bold red]Requires upgrade to >= {VimManager.MIN_NVIM_VERSION}[/bold red]",
                                classes="vim-info-line",
                            )
                        )
                else:
                    container.mount(
                        Static(
                            "• Status: [bold yellow]Not Installed[/bold yellow]",
                            classes="vim-info-line",
                        )
                    )
            else:
                container.mount(
                    Static("• Status: [red]Error checking status[/red]", classes="vim-info-line"),
                )

            # NeoVim 操作
            if not self.nvim_info or not getattr(self.nvim_info, "installed", False):
                widget = Static("", classes="vim-action", id="vim-action-neovim")
                container.mount(widget)
                action_entries.append(
                    {
                        "label": f"Install NeoVim (via {manager_name})",
                        "action": "install_neovim",
                        "widget": widget,
                    }
                )
            elif self.nvim_info.installed and not getattr(
                self.nvim_info, "meets_requirement", False
            ):
                widget = Static("", classes="vim-action", id="vim-action-neovim")
                container.mount(widget)
                action_entries.append(
                    {
                        "label": "Show NeoVim upgrade guidance",
                        "action": "upgrade_info",
                        "widget": widget,
                    }
                )
            else:
                widget = Static("", classes="vim-action", id="vim-action-neovim")
                container.mount(widget)
                action_entries.append(
                    {
                        "label": "Uninstall NeoVim",
                        "action": "uninstall_neovim",
                        "widget": widget,
                    }
                )

            container.mount(Rule())

            # LazyVim 状态
            container.mount(Label("LazyVim Status", classes="section-header"))
            if self.lazyvim_info:
                if self.lazyvim_info.installed:
                    # Status with version display
                    if self.lazyvim_info.version:
                        container.mount(
                            Static(
                                f"• Status: [bold green]Installed[/bold green]",
                                classes="vim-info-line",
                            )
                        )
                        if self.lazyvim_info.version == "Not initialized":
                            container.mount(
                                Static(
                                    f"• Version: [bold yellow]{self.lazyvim_info.version}[/bold yellow] (run 'nvim' to initialize)",
                                    classes="vim-info-line",
                                )
                            )
                        else:
                            container.mount(
                                Static(
                                    f"• Version: [bold cyan]{self.lazyvim_info.version}[/bold cyan]",
                                    classes="vim-info-line",
                                )
                            )
                    else:
                        container.mount(
                            Static(
                                "• Status: [bold green]Installed[/bold green]",
                                classes="vim-info-line",
                            )
                        )

                    if self.lazyvim_info.config_path:
                        container.mount(
                            Static(
                                f"• Config: {self.lazyvim_info.config_path}",
                                classes="vim-info-line",
                            )
                        )

                    # Runtime status check
                    if self.lazyvim_info.can_run:
                        container.mount(
                            Static(
                                "• Runtime: [bold green]Ready to run[/bold green]",
                                classes="vim-info-line",
                            )
                        )
                    else:
                        if not self.lazyvim_info.nvim_compatible:
                            container.mount(
                                Static(
                                    f"• Runtime: [bold red]Cannot run - NeoVim >= {VimManager.MIN_NVIM_VERSION} required[/bold red]",
                                    classes="vim-info-line",
                                )
                            )
                        else:
                            container.mount(
                                Static(
                                    "• Runtime: [bold yellow]NeoVim not detected[/bold yellow]",
                                    classes="vim-info-line",
                                )
                            )
                else:
                    container.mount(
                        Static(
                            "• Status: [bold yellow]Not Installed[/bold yellow]",
                            classes="vim-info-line",
                        )
                    )
            else:
                container.mount(
                    Static("• Status: [red]Error checking status[/red]", classes="vim-info-line"),
                )

            # LazyVim 操作
            lazy_note = None
            lazy_label = "Install LazyVim configuration"
            lazy_action = "install_lazyvim"

            lazy_installed = bool(
                self.lazyvim_info and getattr(self.lazyvim_info, "installed", False)
            )

            if lazy_installed:
                lazy_label = "Uninstall LazyVim configuration"
                lazy_action = "uninstall_lazyvim"
            else:
                if not self.nvim_info or not getattr(self.nvim_info, "installed", False):
                    lazy_label = "Install LazyVim configuration (NeoVim required at runtime)"
                    lazy_note = (
                        "• NeoVim not detected. Install NeoVim to use LazyVim effectively."
                    )
                elif self.nvim_info.installed and not getattr(
                    self.nvim_info, "meets_requirement", False
                ):
                    lazy_label = (
                        f"Install LazyVim configuration (requires NeoVim >= {VimManager.MIN_NVIM_VERSION})"
                    )
                    lazy_note = (
                        f"• Current NeoVim version is below {VimManager.MIN_NVIM_VERSION}."
                    )

            if lazy_note:
                container.mount(Static(lazy_note, classes="vim-info-line"))

            lazy_widget = Static("", classes="vim-action", id="vim-action-lazyvim")
            container.mount(lazy_widget)
            action_entries.append(
                {
                    "label": lazy_label,
                    "action": lazy_action,
                    "widget": lazy_widget,
                }
            )

            self._register_action_entries(action_entries)

        except Exception as exc:  # noqa: BLE001
            logger.error(f"Failed to update content display: {exc}", exc_info=True)

    def _show_error(self, message: str) -> None:
        """将错误消息展示在内容区域。"""
        try:
            container = self._clear_content()
            container.styles.scrollbar_size = 0
            container.mount(Static(f"[red]Error: {message}[/red]", classes="vim-info-line"))
            self._register_action_entries([])
        except Exception as exc:  # noqa: BLE001
            logger.error(f"Failed to show error: {exc}")

    def action_install(self) -> None:
        """快捷键 I 默认执行当前高亮操作。"""
        if self.is_loading:
            return
        if not self.action_entries:
            logger.debug("No Vim actions available for shortcut")
            return
        self.handle_enter()

    def _open_neovim_confirm(self, operation: str) -> None:
        """打开 NeoVim 安装/卸载确认弹窗。"""
        from .vim_install_confirm import VimInstallConfirm

        logger.info(f"Opening NeoVim {operation} confirmation")

        def handle_confirmation(confirmed: bool) -> None:
            if confirmed:
                self._execute_neovim_operation(operation)

        modal = VimInstallConfirm(
            target="neovim",
            operation=operation,
            package_manager=self.primary_pm.name if self.primary_pm else "unknown",
            nvim_info=self.nvim_info,
            lazyvim_info=self.lazyvim_info,
        )
        self.app.push_screen(modal, handle_confirmation)

    def _open_lazyvim_confirm(self, operation: str) -> None:
        """打开 LazyVim 安装/卸载确认弹窗。"""
        from .vim_install_confirm import VimInstallConfirm

        logger.info(f"Opening LazyVim {operation} confirmation")

        def handle_confirmation(confirmed: bool) -> None:
            if confirmed:
                self._execute_lazyvim_operation(operation)

        modal = VimInstallConfirm(
            target="lazyvim",
            operation=operation,
            package_manager=self.primary_pm.name if self.primary_pm else "unknown",
            nvim_info=self.nvim_info,
            lazyvim_info=self.lazyvim_info,
        )
        self.app.push_screen(modal, handle_confirmation)

    def _show_upgrade_info(self) -> None:
        """展示升级说明模态框。"""
        from textual.containers import Container
        from textual.screen import ModalScreen
        from textual.widgets import Rule, Static

        class UpgradeInfoModal(ModalScreen[bool]):
            """提示 NeoVim 升级步骤的模态框。"""

            CSS = """
            UpgradeInfoModal {
                align: center middle;
            }

            .info-text {
                color: $text;
                margin: 0 0 1 0;
            }

            .warning-text {
                color: $warning;
                text-style: bold;
            }

            .help-text {
                text-align: center;
                color: $text-muted;
                margin: 1 0 0 0;
            }
            """

            def __init__(self, current_version: str, required_version: str):
                super().__init__()
                self.current_version = current_version
                self.required_version = required_version

            def compose(self) -> ComposeResult:
                with Container(classes="modal-container-md"):
                    yield Static("⚠️ NeoVim Upgrade Required", classes="warning-text")
                    yield Rule()
                    yield Static(
                        f"Current Version: {self.current_version}\n"
                        f"Required Version: >= {self.required_version}\n\n"
                        "Manual upgrade steps:\n"
                        "1. Visit: https://github.com/neovim/neovim/releases\n"
                        "2. Download latest version\n"
                        "3. Install using instructions for your system\n\n"
                        "Alternative: Use AppImage or build from source",
                        classes="info-text",
                    )
                    yield Rule()
                    yield Static("Press ESC to close", classes="help-text")

            def on_key(self, event) -> None:  # type: ignore[override]
                if event.key == "escape":
                    self.dismiss(False)

        modal = UpgradeInfoModal(
            self.nvim_info.version if self.nvim_info and self.nvim_info.version else "unknown",
            VimManager.MIN_NVIM_VERSION,
        )
        self.app.push_screen(modal)

    def _execute_neovim_operation(self, operation: str) -> None:
        """打开 NeoVim 安装/卸载进度弹窗并在完成后刷新状态。"""
        from .vim_install_progress import VimInstallProgress

        logger.info(f"Executing NeoVim {operation}")

        def handle_completion(result: dict) -> None:
            logger.info(f"NeoVim {operation} completed: {result}")
            self.is_loading = True
            self._show_loading()
            self._load_vim_status()

        modal = VimInstallProgress(
            target="neovim",
            operation=operation,
            package_manager=self.primary_pm.name if self.primary_pm else "unknown",
            vim_manager=self.vim_manager,
        )
        self.app.push_screen(modal, handle_completion)

    def _execute_lazyvim_operation(self, operation: str) -> None:
        """打开 LazyVim 安装/卸载进度弹窗并在完成后刷新状态。"""
        from .vim_install_progress import VimInstallProgress

        logger.info(f"Executing LazyVim {operation}")

        def handle_completion(result: dict) -> None:
            logger.info(f"LazyVim {operation} completed: {result}")
            self.is_loading = True
            self._show_loading()
            self._load_vim_status()

        modal = VimInstallProgress(
            target="lazyvim",
            operation=operation,
            package_manager=self.primary_pm.name if self.primary_pm else "unknown",
            vim_manager=self.vim_manager,
        )
        self.app.push_screen(modal, handle_completion)

    def action_refresh(self) -> None:
        """手动刷新检测状态。"""
        logger.info("Refreshing Vim status")
        self.is_loading = True

        self._show_loading()
        self._notify_help_update()
        self._load_vim_status()

    def action_scroll_down(self) -> None:
        """向下滚动内容区域。"""
        try:
            content_area = self.query_one("#vim-panel-scroll", ScrollableContainer)
            content_area.scroll_down(animate=False)
        except Exception:  # noqa: BLE001
            pass

    def action_scroll_up(self) -> None:
        """向上滚动内容区域。"""
        try:
            content_area = self.query_one("#vim-panel-scroll", ScrollableContainer)
            content_area.scroll_up(animate=False)
        except Exception:  # noqa: BLE001
            pass

class VimManagementScreen(Screen):
    """Vim 管理独立屏幕，复用共享面板组件。"""

    BINDINGS = [
        ("escape", "back", "Back"),
        ("q", "back", "Back"),
        ("i", "install", "Install"),
        ("r", "refresh", "Refresh"),
        ("j", "scroll_down", "Scroll Down"),
        ("k", "scroll_up", "Scroll Up"),
    ]

    CSS = VIM_MANAGEMENT_CSS

    def __init__(self, config_manager: ConfigManager):
        super().__init__()
        self.panel = VimManagementPanel(config_manager)

    def compose(self) -> ComposeResult:
        """渲染屏幕内容。"""
        yield self.panel

    def action_install(self) -> None:
        """转发安装操作。"""
        self.panel.action_install()

    def action_refresh(self) -> None:
        """转发刷新操作。"""
        self.panel.action_refresh()

    def action_scroll_down(self) -> None:
        """转发向下滚动操作。"""
        self.panel.action_scroll_down()

    def action_scroll_up(self) -> None:
        """转发向上滚动操作。"""
        self.panel.action_scroll_up()

    def action_back(self) -> None:
        """返回主菜单。"""
        logger.debug("Returning to main menu")
        self.app.pop_screen()
