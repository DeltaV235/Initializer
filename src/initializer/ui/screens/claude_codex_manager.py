"""Claude Code and Codex Management Screen."""

from typing import Optional

from textual import work
from textual.app import ComposeResult
from textual.containers import ScrollableContainer
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Label, Rule, Static

from ...config_manager import ConfigManager
from ...modules.claude_codex_manager import (
    ClaudeCodexManager,
    ClaudeCodeInfo,
    CodexInfo
)
from ...utils.logger import get_ui_logger

logger = get_ui_logger("claude_codex_management")


CLAUDE_CODEX_MANAGEMENT_CSS = """
ClaudeCodexManagementPanel {
    padding: 1;
}

#claude-codex-panel-scroll {
    height: 1fr;
    padding: 1;
    width: 100%;
    scrollbar-size-vertical: 2;
}

.tool-info-line {
    color: $text;
    margin: 0 0 0 0;
    width: 100%;
    text-wrap: wrap;
}

.tool-action {
    color: $text;
    margin: 0 0 0 0;
    width: 100%;
    text-wrap: wrap;
}

.loading-text {
    text-align: center;
    color: $primary;
    text-style: bold;
    margin: 2 0;
}
"""


class ClaudeCodexManagementPanel(Widget):
    """Claude Code & Codex 管理功能的可复用面板组件。"""

    DEFAULT_CSS = CLAUDE_CODEX_MANAGEMENT_CSS

    # Reactive 状态
    claude_info = reactive(None)
    codex_info = reactive(None)
    is_loading = reactive(True)
    expanded_item = reactive(None)

    def __init__(self, config_manager: ConfigManager):
        super().__init__()
        self.config_manager = config_manager

        # 焦点管理
        self.action_entries: list[dict] = []
        self.focus_index: Optional[int] = None

    def compose(self) -> ComposeResult:
        """构建 Claude Code & Codex 管理面板布局。"""
        with ScrollableContainer(id="claude-codex-panel-scroll"):
            yield Static("Loading...", classes="loading-text")

    def on_mount(self) -> None:
        """初始化面板并加载状态。"""
        logger.info("Mounting Claude Code & Codex management panel")
        self._show_loading()
        self._load_status()

    def _show_loading(self) -> None:
        """显示加载状态。"""
        scroll_container = self.query_one("#claude-codex-panel-scroll")
        scroll_container.remove_children()
        scroll_container.mount(Static("Loading...", classes="loading-text"))

    @work(exclusive=True, thread=True)
    async def _load_status(self) -> None:
        """异步并行检测 Claude Code 和 Codex 状态。"""
        try:
            logger.info("Loading Claude Code and Codex status")

            # 并行检测两个工具
            self.claude_info = await ClaudeCodexManager.detect_claude_code()
            self.codex_info = await ClaudeCodexManager.detect_codex()

            logger.info(
                f"Status loaded: Claude Code={self.claude_info.installed}, "
                f"Codex={self.codex_info.installed}"
            )

            self.is_loading = False
            self.app.call_from_thread(self._refresh_panel)

        except Exception as e:
            logger.error(f"Failed to load status: {e}")
            self.is_loading = False
            self.app.call_from_thread(self._show_error)

    def _show_error(self) -> None:
        """显示错误信息。"""
        scroll_container = self.query_one("#claude-codex-panel-scroll")
        scroll_container.remove_children()
        with scroll_container:
            scroll_container.mount(
                Static(
                    "Failed to load tool status. Please check logs.",
                    classes="loading-text"
                )
            )

    def _refresh_panel(self) -> None:
        """重新渲染面板内容。"""
        logger.debug("Refreshing panel content")

        # 清空现有内容
        scroll_container = self.query_one("#claude-codex-panel-scroll")
        scroll_container.remove_children()

        # 清空 action entries
        self.action_entries = []

        # 构建新内容
        widgets = []

        # === Claude Code 部分 ===
        widgets.append(Label("[bold cyan]Claude Code[/bold cyan]", classes="tool-section-title"))

        # 版本信息（可操作）
        if self.claude_info.installed:
            version_text = f"Claude Code: v{self.claude_info.version} / Installed"
        else:
            version_text = "Claude Code: Not Installed"

        version_label = Label(version_text, classes="tool-action")
        widgets.append(version_label)
        self._register_action("install_claude", version_label, version_text)

        if self.claude_info.installed:
            # API Endpoint
            api_endpoint = self.claude_info.api_endpoint or "Unknown"
            widgets.append(Label(f"  API Endpoint: {api_endpoint}", classes="tool-info-line"))

            # MCP 配置（可展开）
            mcp_text = f"MCP Configurations: {self.claude_info.mcp_count} [Press Enter]"
            mcp_label = Label(mcp_text, classes="tool-action")
            widgets.append(mcp_label)
            self._register_action("expand_mcp_claude", mcp_label, mcp_text)

            # 展开 MCP 详情
            if self.expanded_item == "mcp_claude":
                from pathlib import Path
                config_path = str(Path.home() / ".claude")
                mcp_list = ClaudeCodexManager.get_mcp_configs(config_path)

                if not mcp_list:
                    widgets.append(Label("    (No MCP configurations found)", classes="tool-info-line"))
                else:
                    for mcp in mcp_list:
                        widgets.append(Label(f"    - {mcp['name']}: {mcp['command']}", classes="tool-info-line"))

            # 全局记忆 (CLAUDE.md)
            if self.claude_info.global_memory_path:
                claude_md_text = "  Global Memory (CLAUDE.md): Available"
            else:
                claude_md_text = "  Global Memory (CLAUDE.md): Not Found"
            widgets.append(Label(claude_md_text, classes="tool-info-line"))

            # Agents（可展开）
            agent_text = f"Agents: {self.claude_info.agent_count} [Press Enter]"
            agent_label = Label(agent_text, classes="tool-action")
            widgets.append(agent_label)
            self._register_action("expand_agents_claude", agent_label, agent_text)

            # 展开 Agents 详情
            if self.expanded_item == "agents_claude":
                from pathlib import Path
                config_path = str(Path.home() / ".claude")
                agents = ClaudeCodexManager.get_agents(config_path)

                if not agents:
                    widgets.append(Label("    (No agents found)", classes="tool-info-line"))
                else:
                    for agent in agents:
                        widgets.append(Label(f"    - {agent['name']}: {agent['description']}", classes="tool-info-line"))

            # Commands（可展开）
            command_text = f"Commands: {self.claude_info.command_count} [Press Enter]"
            command_label = Label(command_text, classes="tool-action")
            widgets.append(command_label)
            self._register_action("expand_commands_claude", command_label, command_text)

            # 展开 Commands 详情
            if self.expanded_item == "commands_claude":
                from pathlib import Path
                config_path = str(Path.home() / ".claude")
                commands = ClaudeCodexManager.get_commands(config_path)

                if not commands:
                    widgets.append(Label("    (No commands found)", classes="tool-info-line"))
                else:
                    for cmd in commands:
                        widgets.append(Label(f"    - {cmd['name']}: {cmd['description']}", classes="tool-info-line"))

            # Output Styles（可展开）
            output_style_text = f"Output Styles: {self.claude_info.output_style_count} [Press Enter]"
            output_style_label = Label(output_style_text, classes="tool-action")
            widgets.append(output_style_label)
            self._register_action("expand_output_styles_claude", output_style_label, output_style_text)

            # 展开 Output Styles 详情
            if self.expanded_item == "output_styles_claude":
                from pathlib import Path
                config_path = str(Path.home() / ".claude")
                output_styles = ClaudeCodexManager.get_output_styles(config_path)

                if not output_styles:
                    widgets.append(Label("    (No output styles found)", classes="tool-info-line"))
                else:
                    for style in output_styles:
                        widgets.append(Label(f"    - {style['name']}: {style['description']}", classes="tool-info-line"))

            # Plugins
            plugin_text = f"  Plugins: {self.claude_info.plugin_count}"
            widgets.append(Label(plugin_text, classes="tool-info-line"))

            # Hooks（可展开）
            hook_text = f"Hooks: {self.claude_info.hook_count} [Press Enter]"
            hook_label = Label(hook_text, classes="tool-action")
            widgets.append(hook_label)
            self._register_action("expand_hooks_claude", hook_label, hook_text)

            # 展开 Hooks 详情
            if self.expanded_item == "hooks_claude":
                from pathlib import Path
                config_path = str(Path.home() / ".claude")
                hooks = ClaudeCodexManager.get_hooks(config_path)

                if not hooks:
                    widgets.append(Label("    (No hooks found)", classes="tool-info-line"))
                else:
                    for hook in hooks:
                        widgets.append(Label(f"    - {hook['name']} ({hook['type']})", classes="tool-info-line"))

        # 分割线
        widgets.append(Rule())

        # === Codex 部分 ===
        widgets.append(Label("[bold cyan]Codex[/bold cyan]", classes="tool-section-title"))

        # 版本信息（可操作）
        if self.codex_info.installed:
            codex_version_text = f"Codex: v{self.codex_info.version} / Installed"
        else:
            codex_version_text = "Codex: Not Installed"

        codex_version_label = Label(codex_version_text, classes="tool-action")
        widgets.append(codex_version_label)
        self._register_action("install_codex", codex_version_label, codex_version_text)

        if self.codex_info.installed:
            # API Endpoint
            codex_api_endpoint = self.codex_info.api_endpoint or "Unknown"
            widgets.append(Label(f"  API Endpoint: {codex_api_endpoint}", classes="tool-info-line"))

            # MCP 配置（可展开）
            codex_mcp_text = f"MCP Configurations: {self.codex_info.mcp_count} [Press Enter]"
            codex_mcp_label = Label(codex_mcp_text, classes="tool-action")
            widgets.append(codex_mcp_label)
            self._register_action("expand_mcp_codex", codex_mcp_label, codex_mcp_text)

            # 展开 MCP 详情
            if self.expanded_item == "mcp_codex":
                from pathlib import Path
                config_path = str(Path.home() / ".codex")
                mcp_list = ClaudeCodexManager.get_mcp_configs(config_path)

                if not mcp_list:
                    widgets.append(Label("    (No MCP configurations found)", classes="tool-info-line"))
                else:
                    for mcp in mcp_list:
                        widgets.append(Label(f"    - {mcp['name']}: {mcp['command']}", classes="tool-info-line"))

            # AGENTS.md
            if self.codex_info.agents_md_path:
                agents_md_text = "  AGENTS.md: Available"
            else:
                agents_md_text = "  AGENTS.md: Not Found"
            widgets.append(Label(agents_md_text, classes="tool-info-line"))

            # Model
            current_model = self.codex_info.current_model or "Unknown"
            widgets.append(Label(f"  Model: {current_model}", classes="tool-info-line"))

            # Reasoning Effort
            reasoning_effort = self.codex_info.reasoning_effort or "Unknown"
            widgets.append(Label(f"  Reasoning Effort: {reasoning_effort}", classes="tool-info-line"))

        # 挂载所有 widgets
        for widget in widgets:
            scroll_container.mount(widget)

        # 刷新箭头
        self._refresh_action_labels()

        logger.debug(f"Panel refreshed with {len(self.action_entries)} action entries")

    def _register_action(self, action: str, widget: Widget, label: str) -> None:
        """注册可操作项。"""
        self.action_entries.append({
            "action": action,
            "widget": widget,
            "label": label
        })

    def _refresh_action_labels(self) -> None:
        """根据焦点状态刷新箭头指示。"""
        for index, entry in enumerate(self.action_entries):
            widget = entry.get("widget")
            if not widget:
                continue

            # 统一对齐：有焦点时箭头替换前导空格，无焦点时使用2个空格
            if self._is_active() and self.focus_index == index:
                prefix = "[#7dd3fc]▶[/#7dd3fc] "
            else:
                prefix = "  "

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
                screen.selected_segment == "claude_codex_management"
                and screen.current_panel_focus == "right"
            )
            return is_active
        except Exception as e:
            logger.debug(f"Error in _is_active: {e}")
            return False

    def refresh_action_labels(self) -> None:
        """供外部调用以刷新箭头状态。"""
        if self.focus_index is None and self.action_entries:
            self.focus_index = 0
        self._refresh_action_labels()

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

    def handle_enter(self) -> None:
        """处理回车键，执行当前选中操作。"""
        logger.debug(
            f"handle_enter called: focus_index={self.focus_index}, "
            f"action_entries count={len(self.action_entries)}"
        )

        if self.focus_index is None or not self.action_entries:
            logger.warning("No action entry selected")
            return

        if not (0 <= self.focus_index < len(self.action_entries)):
            logger.warning(f"Invalid focus_index: {self.focus_index}")
            return

        entry = self.action_entries[self.focus_index]
        action = entry.get("action")

        logger.info(f"Executing action: {action}")

        # Install/Uninstall 操作
        if action == "install_claude":
            if self.claude_info and self.claude_info.installed:
                logger.info("Claude Code uninstall requested")
                self._open_uninstall_confirm("claude")
            else:
                logger.info("Claude Code install requested")
                self._open_install_confirm("claude")
        elif action == "install_codex":
            if self.codex_info and self.codex_info.installed:
                logger.info("Codex uninstall requested")
                self._open_uninstall_confirm("codex")
            else:
                logger.info("Codex install requested")
                self._open_install_confirm("codex")
        # 展开/折叠操作
        elif action.startswith("expand_"):
            item_key = action.replace("expand_", "")
            logger.info(f"Toggle expand for {item_key}")
            self._toggle_expand(item_key)

    def _open_install_confirm(self, tool_name: str) -> None:
        """打开安装确认弹窗。

        Args:
            tool_name: 工具名称（'claude' 或 'codex'）
        """
        from .claude_codex_install_confirm import ClaudeCodexInstallConfirm

        # 准备安装命令
        if tool_name == "claude":
            commands = [
                "# Note: Actual installation commands depend on the official method",
                "curl -fsSL https://docs.claude.ai/install.sh | bash",
                "claude --version"
            ]
        else:  # codex
            commands = [
                "# Note: Actual installation commands depend on the official method",
                "pip install anthropic-codex",
                "codex --version"
            ]

        logger.debug(f"Opening install confirmation for {tool_name}")

        # 打开确认弹窗
        confirm_modal = ClaudeCodexInstallConfirm(
            tool_name=tool_name,
            operation="install",
            commands=commands
        )

        self.app.push_screen(
            confirm_modal,
            callback=lambda confirmed: self._handle_confirm(
                confirmed, tool_name, "install", commands
            )
        )

    def _open_uninstall_confirm(self, tool_name: str) -> None:
        """打开卸载确认弹窗。

        Args:
            tool_name: 工具名称（'claude' 或 'codex'）
        """
        from .claude_codex_install_confirm import ClaudeCodexInstallConfirm

        # 准备卸载命令
        commands = [
            f"# Remove {tool_name} configuration directory",
            f"rm -rf ~/.{tool_name}",
            f"# Note: You may need to manually remove the CLI binary"
        ]

        logger.debug(f"Opening uninstall confirmation for {tool_name}")

        # 打开确认弹窗
        confirm_modal = ClaudeCodexInstallConfirm(
            tool_name=tool_name,
            operation="uninstall",
            commands=commands
        )

        self.app.push_screen(
            confirm_modal,
            callback=lambda confirmed: self._handle_confirm(
                confirmed, tool_name, "uninstall", commands
            )
        )

    def _handle_confirm(
        self, confirmed: bool, tool_name: str, operation: str, commands: list[str]
    ) -> None:
        """处理确认结果。

        Args:
            confirmed: 用户是否确认
            tool_name: 工具名称
            operation: 操作类型（'install' 或 'uninstall'）
            commands: 要执行的命令列表
        """
        if not confirmed:
            logger.info(f"User cancelled {operation} for {tool_name}")
            return

        logger.info(f"User confirmed {operation} for {tool_name}")

        # 打开进度弹窗
        from .claude_codex_install_progress import ClaudeCodexInstallProgress

        progress_modal = ClaudeCodexInstallProgress(
            tool_name=tool_name,
            operation=operation,
            commands=commands
        )

        self.app.push_screen(
            progress_modal,
            callback=lambda success: self._handle_operation_complete(
                success, tool_name, operation
            )
        )

    def _handle_operation_complete(
        self, success: bool, tool_name: str, operation: str
    ) -> None:
        """处理操作完成。

        Args:
            success: 操作是否成功
            tool_name: 工具名称
            operation: 操作类型
        """
        if success:
            logger.info(f"{tool_name} {operation} completed successfully")
        else:
            logger.error(f"{tool_name} {operation} failed")

        # 重新加载状态
        logger.debug("Reloading tool status after operation")
        self._load_status()

    def _toggle_expand(self, item_key: str) -> None:
        """切换展开/折叠状态。

        Args:
            item_key: 展开项的键（如 "mcp_claude", "agents_claude"）
        """
        if self.expanded_item == item_key:
            logger.debug(f"Collapsing {item_key}")
            self.expanded_item = None  # 折叠
        else:
            logger.debug(f"Expanding {item_key}")
            self.expanded_item = item_key  # 展开

        # 重新渲染面板
        self._refresh_panel()

    def get_help_text(self) -> str:
        """获取当前面板的帮助文本。

        Returns:
            帮助文本字符串
        """
        return "Esc=Back to Left Panel | TAB/H=Back to Left Panel | R=Refresh | J/K=Navigate | Enter=Expand/Install/Uninstall | Q=Quit"
