"""UI builder methods for main menu segments.

This module contains all _build_ methods that construct UI panels for each segment.
"""

from textual.containers import ScrollableContainer
from textual.widgets import Label


from ..vim_management import VimManagementPanel

class UIBuilders:
    """Builds UI panels for different segments."""

    @staticmethod
    def build_system_info_settings(screen, container: ScrollableContainer) -> None:
        """Build System Info settings panel."""
        from ..main_menu_components import SegmentDisplayRenderer

        state = screen.segment_states.get_state("system_info")
        if state and state.is_loaded():
            container.styles.scrollbar_size = 1
            SegmentDisplayRenderer.display_system_info(container, state.cache)
        elif state and state.is_loading():
            container.styles.scrollbar_size = 0
            container.mount(Label("Loading...", classes="loading-text"))
        else:
            container.styles.scrollbar_size = 0
            screen.segment_states.start_loading("system_info")
            container.mount(Label("Loading...", classes="loading-text"))
            screen._load_system_info()

    @staticmethod
    def build_homebrew_settings(screen, container: ScrollableContainer) -> None:
        """Build Homebrew settings panel."""
        from ..main_menu_components import SegmentDisplayRenderer

        state = screen.segment_states.get_state("homebrew")
        if state and state.is_loaded():
            container.styles.scrollbar_size = 1
            SegmentDisplayRenderer.display_homebrew_info(container, state.cache)
        elif state and state.is_loading():
            container.styles.scrollbar_size = 0
            container.mount(Label("Loading...", classes="loading-text"))
        else:
            container.styles.scrollbar_size = 0
            screen.segment_states.start_loading("homebrew")
            container.mount(Label("Loading...", classes="loading-text"))
            screen._load_homebrew_info()

    @staticmethod
    def build_package_manager_settings(screen, container: ScrollableContainer) -> None:
        """Build Package Manager settings panel."""
        state = screen.segment_states.get_state("package_manager")
        if state and state.is_loaded():
            container.styles.scrollbar_size = 1
            screen._display_package_manager_info(container, state.cache)
        elif state and state.is_loading():
            container.styles.scrollbar_size = 0
            container.mount(Label("Loading...", classes="loading-text"))
        else:
            container.styles.scrollbar_size = 0
            screen.segment_states.start_loading("package_manager")
            container.mount(Label("Loading...", classes="loading-text"))
            screen._load_package_manager_info()

    @staticmethod
    def build_user_management_settings(screen, container: ScrollableContainer) -> None:
        """Build User Management settings panel."""
        from ..main_menu_components import SegmentDisplayRenderer

        state = screen.segment_states.get_state("user_management")
        if state and state.is_loaded():
            container.styles.scrollbar_size = 1
            SegmentDisplayRenderer.display_user_management_info(container, state.cache)
        elif state and state.is_loading():
            container.styles.scrollbar_size = 0
            container.mount(Label("Loading...", classes="loading-text"))
        else:
            container.styles.scrollbar_size = 0
            screen.segment_states.start_loading("user_management")
            container.mount(Label("Loading...", classes="loading-text"))
            screen._load_user_management_info()

    @staticmethod
    def build_vim_management_settings(screen, container: ScrollableContainer) -> None:
        """构建 Vim 管理设置面板。"""
        container.styles.scrollbar_size = 1
        panel = VimManagementPanel(screen.config_manager)
        screen.vim_management_panel = panel
        container.mount(panel)
        if screen.current_panel_focus == "right":
            panel.refresh_action_labels()

    @staticmethod
    def build_zsh_management_settings(screen, container: ScrollableContainer) -> None:
        """构建 Zsh 管理设置面板。"""
        from ..zsh_manager import ZshManagementPanel

        container.styles.scrollbar_size = 1
        panel = ZshManagementPanel(screen.config_manager)
        screen.zsh_management_panel = panel
        container.mount(panel)
        if screen.current_panel_focus == "right":
            panel.refresh_action_labels()

    @staticmethod
    def build_claude_codex_management_settings(screen, container: ScrollableContainer) -> None:
        """构建 Claude Code & Codex 管理设置面板（带缓存支持）。"""
        from ..claude_codex_manager import ClaudeCodexManagementPanel

        container.styles.scrollbar_size = 1

        # 第一层：Panel 实例缓存（避免重建 Widget）
        if not screen.claude_codex_management_panel:
            panel = ClaudeCodexManagementPanel(screen.config_manager)
            screen.claude_codex_management_panel = panel
        else:
            panel = screen.claude_codex_management_panel

        # 先挂载 Panel 到 DOM（确保节点存在）
        container.mount(panel)

        # 第二层：检测数据缓存（避免重复检测）
        state = screen.segment_states.get_state("claude_codex_management")
        if state and state.is_loaded():
            # 关键修复：使用 call_after_refresh 确保 DOM 完成挂载后再恢复缓存
            # 这是为了避免第二次进入时 query_one 找不到节点的竞态问题
            cache_data = state.cache

            def restore_from_cache():
                panel.load_from_cache(cache_data)
                if screen.current_panel_focus == "right":
                    panel.refresh_action_labels()

            screen.call_after_refresh(restore_from_cache)
        elif state and state.is_loading():
            # 正在加载中，显示 loading 状态
            panel.is_loading = True
            panel._show_loading()
            if screen.current_panel_focus == "right":
                panel.refresh_action_labels()
        else:
            # 首次加载，启动异步检测
            screen.segment_states.start_loading("claude_codex_management")
            panel.is_loading = True
            panel._show_loading()
            screen._load_claude_codex_status()
            if screen.current_panel_focus == "right":
                panel.refresh_action_labels()

    @staticmethod
    def build_app_settings(screen, container: ScrollableContainer) -> None:
        """Build application settings panel."""
        from ..main_menu_components import SegmentDisplayRenderer

        state = screen.segment_states.get_state("settings")
        if state and state.is_loaded():
            container.styles.scrollbar_size = 1
            SegmentDisplayRenderer.display_settings_info(container, state.cache)
        elif state and state.is_loading():
            container.styles.scrollbar_size = 0
            container.mount(Label("Loading...", classes="loading-text"))
        else:
            container.styles.scrollbar_size = 0
            screen.segment_states.start_loading("settings")
            container.mount(Label("Loading...", classes="loading-text"))
            screen._load_settings_info()

    @staticmethod
    def build_help_content(screen, container: ScrollableContainer) -> None:
        """Build help content panel."""
        from ..main_menu_components import SegmentDisplayRenderer

        state = screen.segment_states.get_state("help")
        if state and state.is_loaded():
            container.styles.scrollbar_size = 1
            SegmentDisplayRenderer.display_help_info(container, state.cache)
        elif state and state.is_loading():
            container.styles.scrollbar_size = 0
            container.mount(Label("Loading...", classes="loading-text"))
        else:
            container.styles.scrollbar_size = 0
            screen.segment_states.start_loading("help")
            container.mount(Label("Loading...", classes="loading-text"))
            screen._load_help_info()

    @staticmethod
    def build_app_install_settings(screen, container: ScrollableContainer) -> None:
        """Build App installation settings panel."""
        from ..main_menu_components.app_install_renderer import AppInstallRenderer

        if screen.app_install_cache and not screen.app_install_loading:
            container.styles.scrollbar_size = 1
            AppInstallRenderer.display_app_install_list(screen, container, screen.app_install_cache)

            # If right panel is focused, show arrows immediately
            if screen.current_panel_focus == "right" and screen.selected_segment == "app_install":
                # Ensure app_focused_index is valid
                if not hasattr(screen, 'app_focused_index'):
                    screen.app_focused_index = 0
                screen.app_manager.update_focus_indicators()
        elif screen.app_install_loading:
            container.styles.scrollbar_size = 0
            container.mount(Label("Loading...", classes="loading-text"))
        else:
            container.styles.scrollbar_size = 0
            screen.app_install_loading = True
            container.mount(Label("Loading...", classes="loading-text"))
            screen._load_app_install_info()
