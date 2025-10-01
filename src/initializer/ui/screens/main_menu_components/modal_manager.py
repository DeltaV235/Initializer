"""Modal dialog managers.

This module handles all modal dialog creation and interaction.
"""


class ModalManager:
    """Manages modal dialogs."""

    @staticmethod
    def show_source_selection_modal(screen) -> None:
        """Show package manager source selection modal."""
        if not screen.pm_interaction._primary_pm:
            return

        def on_source_selected(source_url: str) -> None:
            """Callback when a source is selected."""
            from ....modules.package_manager import PackageManagerDetector

            detector = PackageManagerDetector(screen.config_manager)

            try:
                success, message = detector.change_mirror(screen.pm_interaction._primary_pm.name, source_url)

                if success:
                    screen.pm_interaction._primary_pm.current_source = source_url

                    state = screen.segment_states.get_state("package_manager")
                    if state and state.cache:
                        state.cache["primary"] = screen.pm_interaction._primary_pm

                    screen._show_message(f"✓ {message}")
                else:
                    screen._show_message(f"✗ {message}")

                screen.update_settings_panel()
            except Exception as e:
                screen._show_message(f"Error: {str(e)}")

        from ..package_mirror_picker import PackageMirrorPicker
        modal = PackageMirrorPicker(screen.pm_interaction._primary_pm, on_source_selected, screen.config_manager)
        screen.app.push_screen(modal)

    @staticmethod
    def show_single_app_confirmation(screen, actions: list) -> None:
        """Show confirmation modal for single app change."""
        if not actions:
            return

        def on_confirm_callback(confirmed: bool, sudo_manager=None) -> None:
            """Callback when user confirms or cancels."""
            if confirmed:
                from ..app_install_progress import AppInstallProgress
                # Pass sudo_manager from callback, not config_manager
                progress_screen = AppInstallProgress(
                    actions, screen.app_installer, sudo_manager
                )
                screen.app.push_screen(progress_screen, screen._on_install_complete)

        try:
            from ..app_install_confirm import AppInstallConfirm
            modal = AppInstallConfirm(actions, on_confirm_callback, screen.app_installer)
            screen.app.push_screen(modal)
        except Exception as e:
            from ....utils.logger import get_ui_logger
            logger = get_ui_logger("main_menu")
            logger.error(f"Failed to show confirmation modal: {e}", exc_info=True)
            screen._show_message("Failed to show confirmation dialog")