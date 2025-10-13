"""Zsh Management Screen."""

from typing import Optional

from textual import work
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, ScrollableContainer
from textual.reactive import reactive
from textual.screen import ModalScreen, Screen
from textual.widget import Widget
from textual.widgets import Button, Label, Rule, Static

from ...config_manager import ConfigManager
from ...modules.package_manager import PackageManagerDetector
from ...modules.zsh_manager import ZshManager
from ...utils.logger import get_ui_logger

logger = get_ui_logger("zsh_management")


ZSH_MANAGEMENT_CSS = """
ZshManagementPanel {
    padding: 1;
}

#zsh-panel-scroll {
    height: 1fr;
    padding: 1;
}

.zsh-info-line {
    color: $text;
    margin: 0 0 1 0;
}

.zsh-action {
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


class ZshManagementPanel(Widget):
    """Zsh 管理功能的可复用面板组件。"""

    DEFAULT_CSS = ZSH_MANAGEMENT_CSS

    zsh_info = reactive(None)
    ohmyzsh_info = reactive(None)
    current_shell = reactive("")
    available_shells = reactive([])
    plugin_status = reactive([])
    is_loading = reactive(True)
    dependencies_ok = reactive(True)

    def __init__(self, config_manager: ConfigManager):
        super().__init__()
        self.config_manager = config_manager
        self.zsh_manager = ZshManager()

        pm_detector = PackageManagerDetector(config_manager)
        self.primary_pm = pm_detector.get_primary_package_manager()
        logger.info(
            f"Primary package manager: {self.primary_pm.name if self.primary_pm else 'None'}"
        )

        # 加载模块配置
        modules_config = config_manager.get_modules_config()
        zsh_config = modules_config.get("zsh_management")
        self.module_config = zsh_config.settings if zsh_config else {}

        self.action_entries: list[dict] = []
        self.focus_index: Optional[int] = None

    def compose(self) -> ComposeResult:
        """构建 Zsh 管理面板布局。"""
        with ScrollableContainer(id="zsh-panel-scroll"):
            yield Static("Loading...", classes="loading-text")

    def on_mount(self) -> None:
        """初始化面板并加载 Zsh 状态。"""
        self._show_loading()
        self._load_zsh_status()

    @work(exclusive=True, thread=True)
    async def _load_zsh_status(self) -> None:
        """异步检测 Zsh、Oh-my-zsh 和插件状态。"""
        try:
            logger.info("Loading Zsh status")

            # 并行检测所有状态
            self.zsh_info = await ZshManager.detect_zsh()
            logger.debug(f"Zsh info: {self.zsh_info}")

            self.ohmyzsh_info = await ZshManager.detect_ohmyzsh()
            logger.debug(f"Oh-my-zsh info: {self.ohmyzsh_info}")

            self.current_shell = await ZshManager.get_current_shell()
            logger.debug(f"Current shell: {self.current_shell}")

            self.available_shells = await ZshManager.get_available_shells()
            logger.debug(f"Available shells: {self.available_shells}")

            # 检查依赖
            deps = await ZshManager.check_dependencies()
            self.dependencies_ok = deps.get("git") and deps.get("curl")
            logger.debug(f"Dependencies OK: {self.dependencies_ok}")

            # 检查插件状态
            plugins_config = self.module_config.get("plugins", [])
            self.plugin_status = await self.zsh_manager.get_plugin_status(plugins_config)

            self.is_loading = False

            def update_ui() -> None:
                self._update_content_display()
                self._notify_help_update()

            self.app.call_from_thread(update_ui)

        except Exception as exc:  # noqa: BLE001
            logger.error(f"Failed to load Zsh status: {exc}", exc_info=True)
            self.is_loading = False

            def show_error() -> None:
                self._show_error(str(exc))
                self._notify_help_update()

            self.app.call_from_thread(show_error)

    def _get_content_container(self) -> ScrollableContainer:
        return self.query_one("#zsh-panel-scroll", ScrollableContainer)

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

    def _show_error(self, message: str) -> None:
        """将错误消息展示在内容区域。"""
        try:
            container = self._clear_content()
            container.styles.scrollbar_size = 0
            container.mount(Static(f"[red]Error: {message}[/red]", classes="zsh-info-line"))
            self._register_action_entries([])
        except Exception as exc:  # noqa: BLE001
            logger.error(f"Failed to show error: {exc}")

    def _notify_help_update(self) -> None:
        """通知屏幕更新帮助文本。"""
        try:
            screen = self.app.screen if hasattr(self, "app") and self.app else None
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
            prefix = (
                "[#7dd3fc]▶[/#7dd3fc] "
                if (self._is_active() and self.focus_index == index)
                else "  "
            )
            widget.update(f"{prefix}{entry['label']}")

    def _is_active(self) -> bool:
        """检查当前面板是否处于激活状态。"""
        try:
            screen = self.app.screen if hasattr(self, "app") and self.app else None
            if not screen:
                return False

            has_segment = hasattr(screen, "selected_segment")
            has_focus = hasattr(screen, "current_panel_focus")

            if not (has_segment and has_focus):
                return False

            is_active = (
                screen.selected_segment == "zsh_management"
                and screen.current_panel_focus == "right"
            )
            logger.debug(
                f"_is_active: segment={screen.selected_segment}, "
                f"focus={screen.current_panel_focus}, result={is_active}"
            )
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
        logger.debug(
            f"handle_enter called: focus_index={self.focus_index}, "
            f"action_entries count={len(self.action_entries)}, "
            f"is_loading={self.is_loading}"
        )

        entry = self._current_action_entry()
        if not entry:
            logger.warning(f"No action entry found at focus_index={self.focus_index}")
            return

        logger.info(f"Triggering action: {entry.get('action')} - {entry.get('label')}")
        self._trigger_action(entry.get("action"))

    def _trigger_action(self, action: Optional[str]) -> None:
        if not action or self.is_loading:
            return

        # Shell 切换（通过 modal）
        if action == "change_shell":
            self._open_shell_selection_modal()
            return

        # Shell 切换（直接执行，无 confirm）
        if action.startswith("change_shell:"):
            shell_path = action.split(":", 1)[1]
            self._change_shell_directly(shell_path)

        # Zsh 安装/卸载
        elif action == "install_zsh":
            self._open_zsh_confirm("install")
        elif action == "uninstall_zsh":
            self._open_zsh_confirm("uninstall")

        # Oh-my-zsh 安装/卸载
        elif action == "install_ohmyzsh":
            self._open_ohmyzsh_confirm("install")
        elif action == "uninstall_ohmyzsh":
            self._open_ohmyzsh_confirm("uninstall")

        # 插件管理（通过 modal）
        elif action.startswith("manage_plugin:"):
            plugin_name = action.split(":", 1)[1]
            plugin_info = next(
                (p for p in self.plugin_status if p.name == plugin_name),
                None
            )
            if plugin_info:
                operation = "uninstall" if plugin_info.installed else "install"
                plugin_dict = {
                    "name": plugin_info.name,
                    "description": getattr(plugin_info, "description", ""),
                    "install_method": getattr(plugin_info, "install_method", "git"),
                }
                self._open_plugin_confirm(plugin_dict, operation)
            return

        # 插件安装/卸载（旧逻辑，保留兼容）
        elif action.startswith("install_plugin:") or action.startswith("uninstall_plugin:"):
            operation, plugin_name = action.split(":", 1)
            operation = operation.replace("_plugin", "")
            plugin = self._find_plugin_by_name(plugin_name)
            if plugin:
                self._open_plugin_confirm(plugin, operation)
        else:
            logger.debug(f"Unknown Zsh action: {action}")

    def get_help_text(self) -> str:
        """Generate help text for the panel."""
        return "ESC/TAB/H=Back | R=Refresh | J/K=Navigate | Enter=Select | Q=Quit"

    def _find_plugin_by_name(self, name: str) -> Optional[dict]:
        """根据名称查找插件配置。"""
        plugins_config = self.module_config.get("plugins", [])
        for plugin in plugins_config:
            if plugin.get("name") == name:
                return plugin
        return None

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

            # Section 1: Current Shell
            container.mount(Label("Current Shell", classes="section-header"))

            # 单行交互：状态 + Enter 触发 modal
            if self.available_shells:
                widget = Static("", classes="zsh-action")
                container.mount(widget)
                action_entries.append({
                    "label": f"Default Shell: {self.current_shell} (Enter to change)",
                    "action": "change_shell",
                    "widget": widget
                })
            else:
                # 无可用 shell，仅显示状态
                container.mount(
                    Static(f"Default Shell: {self.current_shell}", classes="zsh-info-line")
                )

            container.mount(Rule())

            # Section 2: Zsh Status
            container.mount(Label("Zsh Status", classes="section-header"))
            if self.zsh_info:
                if self.zsh_info.installed:
                    version_info = (
                        f"v{self.zsh_info.version}" if self.zsh_info.version else "Unknown"
                    )
                    container.mount(
                        Static(
                            f"Status: [bold green]Installed[/bold green] ({version_info})",
                            classes="zsh-info-line",
                        )
                    )
                    if self.zsh_info.path:
                        container.mount(
                            Static(f"Path: {self.zsh_info.path}", classes="zsh-info-line")
                        )

                    widget = Static("", classes="zsh-action")
                    container.mount(widget)
                    action_entries.append(
                        {"label": "Uninstall Zsh", "action": "uninstall_zsh", "widget": widget}
                    )
                else:
                    container.mount(
                        Static(
                            "Status: [bold yellow]Not Installed[/bold yellow]",
                            classes="zsh-info-line",
                        )
                    )
                    widget = Static("", classes="zsh-action")
                    container.mount(widget)
                    action_entries.append(
                        {
                            "label": f"Install Zsh (via {manager_name})",
                            "action": "install_zsh",
                            "widget": widget,
                        }
                    )
            else:
                container.mount(
                    Static("Status: [red]Error checking status[/red]", classes="zsh-info-line")
                )

            container.mount(Rule())

            # Section 3: Oh-my-zsh Status
            container.mount(Label("Oh-my-zsh Status", classes="section-header"))
            if self.ohmyzsh_info:
                if self.ohmyzsh_info.installed:
                    container.mount(
                        Static("Status: [bold green]Installed[/bold green]", classes="zsh-info-line")
                    )
                    if self.ohmyzsh_info.version:
                        container.mount(
                            Static(
                                f"Version: [bold cyan]{self.ohmyzsh_info.version}[/bold cyan]",
                                classes="zsh-info-line",
                            )
                        )
                    if self.ohmyzsh_info.config_path:
                        container.mount(
                            Static(
                                f"Config: {self.ohmyzsh_info.config_path}",
                                classes="zsh-info-line",
                            )
                        )

                    widget = Static("", classes="zsh-action")
                    container.mount(widget)
                    action_entries.append(
                        {
                            "label": "Uninstall Oh-my-zsh",
                            "action": "uninstall_ohmyzsh",
                            "widget": widget,
                        }
                    )
                else:
                    container.mount(
                        Static(
                            "Status: [bold yellow]Not Installed[/bold yellow]",
                            classes="zsh-info-line",
                        )
                    )
                    widget = Static("", classes="zsh-action")
                    container.mount(widget)
                    action_entries.append(
                        {
                            "label": "Install Oh-my-zsh",
                            "action": "install_ohmyzsh",
                            "widget": widget,
                        }
                    )
            else:
                container.mount(
                    Static("Status: [red]Error checking status[/red]", classes="zsh-info-line")
                )

            container.mount(Rule())

            # Section 4: Plugins
            container.mount(Label("Oh-my-zsh Plugins", classes="section-header"))
            if not self.dependencies_ok:
                container.mount(
                    Static(
                        "⚠️  Required dependencies missing (git, curl). Please install them first.",
                        classes="warning-text",
                    )
                )

            for plugin_info in self.plugin_status:
                try:
                    # 单行交互：状态 + Enter 触发 modal
                    status_text = (
                        "[green]Installed[/green]"
                        if plugin_info.installed
                        else "[yellow]Not Installed[/yellow]"
                    )
                    action_hint = "Uninstall" if plugin_info.installed else "Install"

                    widget = Static("", classes="zsh-action")
                    container.mount(widget)
                    action_entries.append({
                        "label": f"{plugin_info.name}: {status_text} (Enter to {action_hint})",
                        "action": f"manage_plugin:{plugin_info.name}",
                        "widget": widget
                    })
                except Exception as e:
                    logger.warning(f"Failed to render plugin '{plugin_info.name}': {e}")
                    continue

            # 即使渲染过程中有部分失败，也要注册已收集的 action_entries
            # 确保至少有部分交互功能可用
            if action_entries:
                self._register_action_entries(action_entries)
            else:
                logger.warning("No action entries collected during content update")

        except Exception as exc:  # noqa: BLE001
            logger.error(f"Failed to update content display: {exc}", exc_info=True)
            # 即使出现严重错误，尝试注册已有的部分 action_entries
            # 这样至少能保持部分交互功能

    def _open_shell_selection_modal(self) -> None:
        """打开 shell 选择 modal。"""
        from .shell_selection_modal import ShellSelectionModal

        logger.info("Opening shell selection modal")

        def handle_selection(selected_shell: Optional[str]) -> None:
            """处理 shell 选择结果。"""
            if not selected_shell:
                logger.debug("User cancelled shell selection")
                return

            logger.info(f"User selected shell: {selected_shell}")

            # 直接执行 shell 更新（异步后台执行）
            self._execute_shell_change(selected_shell)

        # 打开选择 modal
        selection_modal = ShellSelectionModal(
            current_shell=self.current_shell,
            available_shells=list(self.available_shells),
        )
        self.app.push_screen(selection_modal, handle_selection)

    def _change_shell_directly(self, shell_path: str) -> None:
        """直接切换 shell，无 confirm，显示 Progress modal。"""
        from .zsh_install_progress import ZshInstallProgress

        logger.info(f"Changing shell directly to: {shell_path}")

        def handle_completion(result: dict) -> None:
            if result.get("success"):
                self.app.notify(
                    "Shell changed successfully. Please log out and log back in.",
                    severity="information",
                    timeout=5,
                )
            else:
                self.app.notify(
                    f"Failed to change shell: {result.get('error')}", severity="error"
                )
            self.is_loading = True
            self._show_loading()
            self._load_zsh_status()

        modal = ZshInstallProgress(
            target="shell",
            operation="change",
            zsh_manager=self.zsh_manager,
            package_manager=None,
            plugin=None,
            shell_path=shell_path,
        )
        self.app.push_screen(modal, handle_completion)

    def _open_zsh_confirm(self, operation: str) -> None:
        """打开 Zsh 安装/卸载确认弹窗。"""
        from .zsh_install_confirm import ZshInstallConfirm

        logger.info(f"Opening Zsh {operation} confirmation")

        def handle_confirmation(confirmed: bool) -> None:
            if confirmed:
                self._execute_zsh_operation(operation)

        modal = ZshInstallConfirm(
            target="zsh",
            operation=operation,
            package_manager=self.primary_pm.name if self.primary_pm else "unknown",
            zsh_info=self.zsh_info,
            ohmyzsh_info=self.ohmyzsh_info,
            plugin=None,
        )
        self.app.push_screen(modal, handle_confirmation)

    def _open_ohmyzsh_confirm(self, operation: str) -> None:
        """打开 Oh-my-zsh 安装/卸载确认弹窗。"""
        from .zsh_install_confirm import ZshInstallConfirm

        logger.info(f"Opening Oh-my-zsh {operation} confirmation")

        def handle_confirmation(confirmed: bool) -> None:
            if confirmed:
                self._execute_ohmyzsh_operation(operation)

        modal = ZshInstallConfirm(
            target="ohmyzsh",
            operation=operation,
            package_manager=self.primary_pm.name if self.primary_pm else "unknown",
            zsh_info=self.zsh_info,
            ohmyzsh_info=self.ohmyzsh_info,
            plugin=None,
        )
        self.app.push_screen(modal, handle_confirmation)

    def _open_plugin_confirm(self, plugin: dict, operation: str) -> None:
        """打开插件安装/卸载确认弹窗。"""
        from .zsh_install_confirm import ZshInstallConfirm

        logger.info(f"Opening plugin {operation} confirmation: {plugin.get('name')}")

        def handle_confirmation(confirmed: bool) -> None:
            if confirmed:
                self._execute_plugin_operation(plugin, operation)

        modal = ZshInstallConfirm(
            target="plugin",
            operation=operation,
            package_manager=self.primary_pm.name if self.primary_pm else "unknown",
            zsh_info=self.zsh_info,
            ohmyzsh_info=self.ohmyzsh_info,
            plugin=plugin,
        )
        self.app.push_screen(modal, handle_confirmation)

    def _execute_zsh_operation(self, operation: str) -> None:
        """打开 Zsh 安装/卸载进度弹窗并在完成后刷新状态。"""
        from .zsh_install_progress import ZshInstallProgress

        logger.info(f"Executing Zsh {operation}")

        def handle_completion(result: dict) -> None:
            logger.info(f"Zsh {operation} completed: {result}")
            if result.get("success") and operation == "install":
                self._prompt_shell_change()
            self.is_loading = True
            self._show_loading()
            self._load_zsh_status()

        modal = ZshInstallProgress(
            target="zsh",
            operation=operation,
            package_manager=self.primary_pm.name if self.primary_pm else "unknown",
            zsh_manager=self.zsh_manager,
            plugin=None,
            shell_path=None,
        )
        self.app.push_screen(modal, handle_completion)

    def _execute_ohmyzsh_operation(self, operation: str) -> None:
        """打开 Oh-my-zsh 安装/卸载进度弹窗并在完成后刷新状态。"""
        from .zsh_install_progress import ZshInstallProgress

        logger.info(f"Executing Oh-my-zsh {operation}")

        def handle_completion(result: dict) -> None:
            logger.info(f"Oh-my-zsh {operation} completed: {result}")
            self.is_loading = True
            self._show_loading()
            self._load_zsh_status()

        modal = ZshInstallProgress(
            target="ohmyzsh",
            operation=operation,
            package_manager=None,
            zsh_manager=self.zsh_manager,
            plugin=None,
            shell_path=None,
        )
        self.app.push_screen(modal, handle_completion)

    def _execute_plugin_operation(self, plugin: dict, operation: str) -> None:
        """打开插件安装/卸载进度弹窗并在完成后刷新状态。"""
        from .zsh_install_progress import ZshInstallProgress

        logger.info(f"Executing plugin {operation}: {plugin.get('name')}")

        def handle_completion(result: dict) -> None:
            logger.info(f"Plugin {operation} completed: {result}")
            self.is_loading = True
            self._show_loading()
            self._load_zsh_status()

        modal = ZshInstallProgress(
            target="plugin",
            operation=operation,
            package_manager=None,
            zsh_manager=self.zsh_manager,
            plugin=plugin,
            shell_path=None,
        )
        self.app.push_screen(modal, handle_completion)

    def _prompt_shell_change(self) -> None:
        """提示用户是否切换默认 shell。"""

        class ShellChangePrompt(ModalScreen[bool]):
            CSS = """
            ShellChangePrompt {
                align: center middle;
            }

            .info-text {
                color: $text;
                margin: 1;
                text-align: center;
            }

            #button-container {
                height: auto;
                align: center middle;
                margin: 1 0 0 0;
            }
            """

            def compose(self) -> ComposeResult:
                with Container(classes="modal-container-xs"):
                    yield Static("Set Zsh as default shell?", classes="info-text")
                    with Horizontal(id="button-container"):
                        yield Button("Yes", id="yes", variant="primary")
                        yield Button("No", id="no")

            def on_button_pressed(self, event: Button.Pressed) -> None:
                self.dismiss(event.button.id == "yes")

        def handle_prompt(change: bool) -> None:
            if change:
                zsh_path = (
                    self.zsh_info.path
                    if self.zsh_info and self.zsh_info.path
                    else "/usr/bin/zsh"
                )
                self._change_shell_directly(zsh_path)

        self.app.push_screen(ShellChangePrompt(), handle_prompt)


    @work(exclusive=True, thread=True)
    async def _execute_shell_change(self, selected_shell: str) -> None:
        """在后台线程执行 shell 更新操作。

        Args:
            selected_shell: 目标 shell 的完整路径
        """
        from .shell_change_error_modal import ShellChangeErrorModal

        logger.info(f"Executing shell change to: {selected_shell}")

        try:
            # 调用 ZshManager 更新 shell（传入空回调避免显示 progress）
            result = await self.zsh_manager.change_default_shell(
                selected_shell,
                progress_callback=lambda msg: logger.debug(
                    f"Shell change progress: {msg}"
                ),
            )

            # 成功：在后台线程重新确认 shell（不阻塞 UI）
            if result and result.get("success"):
                logger.info(f"Shell changed successfully to {selected_shell}")
                logger.info(f"Shell update successful: {selected_shell}")

                def update_ui_on_complete():
                    """UI 更新回调（在主线程执行）。"""
                    # 更新 reactive 属性
                    self.current_shell = selected_shell
                    logger.debug(f"Updated current_shell to: {selected_shell}")

                    # 刷新内容显示
                    self._update_content_display()

                    # 刷新帮助文本
                    self._notify_help_update()

                    # 显示成功通知
                    self.app.notify(
                        f"Shell changed to {selected_shell}. Please log out and log back in.",
                        severity="information",
                        timeout=5,
                    )
                    logger.debug("UI refresh completed after shell change")

                # 在主线程更新 UI
                self.app.call_from_thread(update_ui_on_complete)
            else:
                # 失败：显示错误 modal
                error_message = (
                    result.get("error", "Unknown error")
                    if result
                    else "Unknown error"
                )
                logger.error(f"Shell change failed: {error_message}")

                def update_ui_on_error():
                    error_modal = ShellChangeErrorModal(
                        error_message=error_message, shell_path=selected_shell
                    )
                    self.app.push_screen(error_modal)

                # 在主线程显示错误 modal
                self.app.call_from_thread(update_ui_on_error)

        except Exception as exc:
            logger.error(f"Exception during shell change: {exc}", exc_info=True)

            def update_ui_on_error():
                error_modal = ShellChangeErrorModal(
                    error_message=str(exc), shell_path=selected_shell
                )
                self.app.push_screen(error_modal)

            self.app.call_from_thread(update_ui_on_error)

    def action_refresh(self) -> None:
        """手动刷新检测状态。"""
        logger.info("Refreshing Zsh status")
        self.is_loading = True

        self._show_loading()
        self._notify_help_update()
        self._load_zsh_status()

    def action_scroll_down(self) -> None:
        """向下滚动内容区域。"""
        try:
            content_area = self.query_one("#zsh-panel-scroll", ScrollableContainer)
            content_area.scroll_down(animate=False)
        except Exception:  # noqa: BLE001
            pass

    def action_scroll_up(self) -> None:
        """向上滚动内容区域。"""
        try:
            content_area = self.query_one("#zsh-panel-scroll", ScrollableContainer)
            content_area.scroll_up(animate=False)
        except Exception:  # noqa: BLE001
            pass


class ZshManagementScreen(Screen):
    """Zsh 管理独立屏幕，复用共享面板组件。"""

    BINDINGS = [
        ("escape", "back", "Back"),
        ("q", "back", "Back"),
        ("r", "refresh", "Refresh"),
        ("j", "scroll_down", "Scroll Down"),
        ("k", "scroll_up", "Scroll Up"),
    ]

    CSS = ZSH_MANAGEMENT_CSS

    def __init__(self, config_manager: ConfigManager):
        super().__init__()
        self.panel = ZshManagementPanel(config_manager)

    def compose(self) -> ComposeResult:
        """渲染屏幕内容。"""
        yield self.panel

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
