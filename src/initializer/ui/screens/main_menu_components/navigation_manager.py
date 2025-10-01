"""Navigation and refresh management.

This module handles navigation logic and page refresh operations.
"""


class NavigationManager:
    """Manages navigation operations."""

    @staticmethod
    def navigate_segments_down(screen) -> None:
        """Navigate down through segments."""
        current_index = next((i for i, seg in enumerate(screen.SEGMENTS) if seg["id"] == screen.selected_segment), 0)
        if current_index < len(screen.SEGMENTS) - 1:
            screen.selected_segment = screen.SEGMENTS[current_index + 1]["id"]

    @staticmethod
    def navigate_segments_up(screen) -> None:
        """Navigate up through segments."""
        current_index = next((i for i, seg in enumerate(screen.SEGMENTS) if seg["id"] == screen.selected_segment), 0)
        if current_index > 0:
            screen.selected_segment = screen.SEGMENTS[current_index - 1]["id"]


class RefreshManager:
    """Manages page refresh operations."""

    @staticmethod
    def refresh_package_manager_page(screen) -> None:
        """Refresh package manager page."""
        screen.segment_states.start_loading("package_manager")
        screen._load_package_manager_info()
        screen.update_settings_panel()

    @staticmethod
    def refresh_app_install_page(screen) -> None:
        """Refresh app install page."""
        screen.app_install_loading = True
        screen._load_app_install_info()
        screen.update_settings_panel()

    @staticmethod
    def refresh_homebrew_page(screen) -> None:
        """Refresh homebrew page."""
        screen.segment_states.start_loading("homebrew")
        screen._load_homebrew_info()
        screen.update_settings_panel()

    @staticmethod
    def refresh_and_reset_app_page(screen) -> None:
        """Refresh and reset app page."""
        screen.app_selection_state = {}
        screen.app_focused_index = 0
        screen.app_expanded_suites = set()
        RefreshManager.refresh_app_install_page(screen)