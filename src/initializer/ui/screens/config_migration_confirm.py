"""Configuration Migration Confirmation Modal."""

from typing import List

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.events import Key
from textual.screen import ModalScreen
from textual.widgets import Label, Rule, Static, Checkbox

from ...modules.zsh_manager import ShellConfig
from ...utils.logger import get_ui_logger

logger = get_ui_logger("config_migration_confirm")


class ConfigMigrationConfirm(ModalScreen[List[ShellConfig]]):
    """Confirmation modal for shell configuration migration."""

    BINDINGS = [
        ("y", "confirm", "Confirm"),
        ("n", "cancel", "Cancel"),
        ("enter", "confirm", "Confirm"),
        ("escape", "cancel", "Cancel"),
        ("up", "nav_up", "Navigate Up"),
        ("down", "nav_down", "Navigate Down"),
        ("space", "toggle", "Toggle Selection"),
        ("j", "nav_down", "Navigate Down"),
        ("k", "nav_up", "Navigate Up"),
    ]

    CSS = """
    ConfigMigrationConfirm {
        align: center middle;
    }

    #confirm-title {
        text-style: bold;
        color: $text;
        margin: 0 0 1 0;
        text-align: center;
    }

    .confirm-content {
        padding: 1;
        margin: 0 0 1 0;
    }

    .info-text {
        color: $text;
        margin: 0 0 1 0;
    }

    .config-list {
        margin: 1 0;
        padding: 1;
        border: solid $primary;
        background: $surface;
    }

    .config-item {
        margin: 0 0 1 0;
        padding: 0 1;
        height: auto;
    }

    .config-item:hover {
        background: $primary;
        color: $background;
    }

    .config-item:focus {
        background: $accent;
        color: $background;
    }

    .tool-name {
        text-style: bold;
        color: $primary;
    }

    .tool-description {
        color: $text-muted;
        text-style: italic;
        margin: 0 0 0 2;
    }

    .config-source {
        color: $text-muted;
        font-size: 80%;
        margin: 0 0 0 2;
    }

    .config-lines {
        margin: 0 0 0 2;
        padding: 0 1;
        background: $surface;
        color: $success;
        font-family: monospace;
        font-size: 90%;
    }

    .selected-count {
        color: $accent;
        text-style: bold;
        margin: 1 0;
        text-align: center;
    }

    .note-text {
        color: $text-muted;
        margin: 1 0;
        padding: 1;
        border: solid $warning;
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

    .help-text {
        width: 100%;
        height: 1;
        content-align: center middle;
        text-align: center;
        color: $text-muted;
    }
    """

    def __init__(self, configs: List[ShellConfig], current_shell: str):
        super().__init__()
        self.configs = configs
        self.current_shell = current_shell
        self.checkboxes: List[Checkbox] = []

    def compose(self) -> ComposeResult:
        """Compose the modal content."""
        with Container(classes="modal-container-confirm"):
            with Vertical():
                yield Label("检测到的 Shell 配置", id="confirm-title")
                yield Rule()

                # 信息文本
                yield Static(
                    f"从 {self.current_shell} 检测到 {len(self.configs)} 个工具配置，"
                    "选择要迁移到 Zsh 的配置：",
                    classes="info-text"
                )

                # 配置列表
                with Vertical(classes="config-list"):
                    for config in self.configs:
                        config_item = Vertical(classes="config-item")

                        # 工具名称和描述
                        header = Static(
                            f"🔧 {config.tool_name} - {config.description}",
                            classes="tool-description"
                        )

                        # 源文件信息
                        source = Static(
                            f"📁 源文件: {config.source_file}",
                            classes="config-source"
                        )

                        # 配置行示例
                        config_preview = "\n".join(config.config_lines[:2])
                        if len(config.config_lines) > 2:
                            config_preview += f"\n... (+{len(config.config_lines)-2} 行)"
                        preview = Static(
                            f"📝 配置预览:\n{config_preview}",
                            classes="config-lines"
                        )

                        # 选择框
                        checkbox = Checkbox(
                            f"迁移 {config.tool_name}",
                            value=config.selected,
                            name=f"config_{config.tool_name}"
                        )
                        self.checkboxes.append(checkbox)

                        with config_item:
                            yield header
                            yield source
                            yield preview
                            yield checkbox

                # 选择计数
                yield Static(
                    f"已选择 {self._get_selected_count()} / {len(self.configs)} 个配置",
                    classes="selected-count"
                )

                # 提示信息
                yield Static(
                    "注意：迁移前会自动备份现有的 .zshrc 文件\n"
                    "迁移完成后需要重新启动终端或运行 'source ~/.zshrc'",
                    classes="note-text"
                )

                # 帮助信息
                with Container(id="help-box"):
                    yield Static("J/K=上下移动 空格=切换选择 Y/N=确认/取消 ESC=关闭", classes="help-text")

    def _get_selected_count(self) -> int:
        """获取选中的配置数量。"""
        return sum(1 for checkbox in self.checkboxes if checkbox.value)

    def _update_selected_count(self) -> None:
        """更新选择计数显示。"""
        selected_count = self._get_selected_count()
        count_widget = self.query_one(".selected-count")
        count_widget.update(f"已选择 {selected_count} / {len(self.configs)} 个配置")

    def action_toggle(self) -> None:
        """切换当前焦点 checkbox 的状态。"""
        focused = self.focused
        if focused and isinstance(focused, Checkbox):
            focused.value = not focused.value
            self._update_selected_count()

    def action_nav_up(self) -> None:
        """向上导航。"""
        focused = self.focused
        if focused:
            # 获取所有可聚焦的 widgets
            focusable = self.query("Checkbox, Button")
            if focusable:
                current_index = list(focusable).index(focused) if focused in focusable else -1
                if current_index > 0:
                    focusable[current_index - 1].focus()

    def action_nav_down(self) -> None:
        """向下导航。"""
        focused = self.focused
        if focused:
            # 获取所有可聚焦的 widgets
            focusable = self.query("Checkbox, Button")
            if focusable:
                current_index = list(focusable).index(focused) if focused in focusable else -1
                if current_index < len(focusable) - 1:
                    focusable[current_index + 1].focus()

    def action_confirm(self) -> None:
        """确认迁移。"""
        # 更新 configs 的选择状态
        for i, checkbox in enumerate(self.checkboxes):
            if i < len(self.configs):
                self.configs[i].selected = checkbox.value

        # 返回选中的配置
        selected_configs = [config for config in self.configs if config.selected]

        logger.info(f"User confirmed migration of {len(selected_configs)} configurations")
        self.dismiss(selected_configs)

    def action_cancel(self) -> None:
        """取消迁移。"""
        logger.info("User cancelled configuration migration")
        self.dismiss([])

    @on(Checkbox.Changed)
    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """当 checkbox 状态改变时更新计数。"""
        self._update_selected_count()

    def on_key(self, event: Key) -> None:
        """处理按键事件。"""
        if event.key == "space":
            event.prevent_default()
            self.action_toggle()
        elif event.key in {"j", "down"}:
            event.prevent_default()
            self.action_nav_down()
        elif event.key in {"k", "up"}:
            event.prevent_default()
            self.action_nav_up()
        elif event.key in {"y", "enter"}:
            event.prevent_default()
            self.action_confirm()
        elif event.key in {"n", "escape"}:
            event.prevent_default()
            self.action_cancel()