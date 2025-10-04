"""Event handlers for main menu screen.

This module contains all event handling logic delegated from the main screen.
All methods receive the screen instance as first parameter for state access.
"""


class EventHandlers:
    """Handles all keyboard and action events for the main menu screen."""

    @staticmethod
    def action_switch_panel(screen) -> None:
        """Switch focus between left and right panels."""
        from ....utils.logger import get_ui_logger
        logger = get_ui_logger("main_menu")

        logger.debug("action_switch_panel called")

        if screen.current_panel_focus == "unset":
            screen.current_panel_focus = "left"
            logger.debug("Initial focus set to 'left'")
            # Focus on current segment button
            try:
                button_id = f"#segment-{screen.selected_segment}"
                button = screen.query_one(button_id)
                button.focus()
                logger.debug(f"Focused button: {button_id}")
            except Exception as e:
                logger.error(f"Failed to focus button: {e}")
        elif screen.current_panel_focus == "left":
            screen.current_panel_focus = "right"
            logger.debug("Switched focus from 'left' to 'right'")
            # Focus on right panel content
            try:
                from textual.containers import ScrollableContainer
                settings_container = screen.query_one("#settings-scroll", ScrollableContainer)
                settings_container.focus()
                logger.debug("Focused settings-scroll container")
            except Exception as e:
                logger.error(f"Failed to focus container: {e}")
        elif screen.current_panel_focus == "right":
            screen.current_panel_focus = "left"
            logger.debug("Switched focus from 'right' to 'left'")
            # Focus on current segment button
            try:
                button_id = f"#segment-{screen.selected_segment}"
                button = screen.query_one(button_id)
                button.focus()
                logger.debug(f"Focused button: {button_id}")
            except Exception as e:
                logger.error(f"Failed to focus button: {e}")

    @staticmethod
    def action_nav_left(screen) -> None:
        """Navigate left (switch to left panel)."""
        from ....utils.logger import get_ui_logger
        logger = get_ui_logger("event_handlers")

        if screen.current_panel_focus != "left":
            screen.current_panel_focus = "left"
            # Move actual Textual focus to the current segment button
            try:
                button_id = f"#segment-{screen.selected_segment}"
                logger.debug(f"Attempting to focus button: {button_id}")
                button = screen.query_one(button_id)
                button.focus()
                logger.debug(f"Successfully focused button: {button_id}")
            except Exception as e:
                logger.error(f"Failed to focus button {button_id}: {e}")

    @staticmethod
    def action_nav_right(screen) -> None:
        """Navigate right (switch to right panel)."""
        from ....utils.logger import get_ui_logger
        logger = get_ui_logger("event_handlers")

        if screen.current_panel_focus != "right":
            screen.current_panel_focus = "right"
            # Move actual Textual focus to the right panel content
            try:
                from textual.containers import ScrollableContainer
                settings_container = screen.query_one("#settings-scroll", ScrollableContainer)
                logger.debug("Attempting to focus settings-scroll container")
                settings_container.focus()
                logger.debug("Successfully focused settings-scroll container")
            except Exception as e:
                logger.error(f"Failed to focus settings container: {e}")

    @staticmethod
    def action_nav_down(screen) -> None:
        """Navigate down in current panel."""
        if screen.current_panel_focus == "left":
            from .navigation_manager import NavigationManager
            NavigationManager.navigate_segments_down(screen)
        elif screen.current_panel_focus == "right":
            if screen.selected_segment == "app_install":
                screen.app_manager.navigate_items("down")
            elif screen.selected_segment == "package_manager":
                screen.pm_interaction.navigate_items("down")
            elif screen.selected_segment == "vim_management":
                panel = getattr(screen, "vim_management_panel", None)
                if panel:
                    panel.navigate("down")
            else:
                # For other segments (system_info, etc.), scroll the content
                try:
                    from textual.containers import ScrollableContainer
                    settings_container = screen.query_one("#settings-scroll", ScrollableContainer)
                    settings_container.scroll_down(animate=False)
                except Exception:
                    pass  # Silently fail if container not found

    @staticmethod
    def action_nav_up(screen) -> None:
        """Navigate up in current panel."""
        if screen.current_panel_focus == "left":
            from .navigation_manager import NavigationManager
            NavigationManager.navigate_segments_up(screen)
        elif screen.current_panel_focus == "right":
            if screen.selected_segment == "app_install":
                screen.app_manager.navigate_items("up")
            elif screen.selected_segment == "package_manager":
                screen.pm_interaction.navigate_items("up")
            elif screen.selected_segment == "vim_management":
                panel = getattr(screen, "vim_management_panel", None)
                if panel:
                    panel.navigate("up")
            else:
                # For other segments (system_info, etc.), scroll the content
                try:
                    from textual.containers import ScrollableContainer
                    settings_container = screen.query_one("#settings-scroll", ScrollableContainer)
                    settings_container.scroll_up(animate=False)
                except Exception:
                    pass  # Silently fail if container not found

    @staticmethod
    def action_select_item(screen) -> None:
        """Select current item (Enter key)."""
        from ....utils.logger import get_ui_logger
        logger = get_ui_logger("event_handlers")

        logger.info(f"[ENTER KEY] action_select_item: panel_focus={screen.current_panel_focus}, "
                    f"segment={screen.selected_segment}")

        if screen.current_panel_focus == "left":
            # Do nothing on left panel Enter
            logger.debug("Left panel focused, ignoring Enter key")
            pass
        elif screen.current_panel_focus == "right":
            logger.info(f"[ENTER KEY] Right panel focused, segment={screen.selected_segment}")
            if screen.selected_segment == "app_install":
                logger.debug("Calling app_manager.handle_enter_key()")
                screen.app_manager.handle_enter_key()
            elif screen.selected_segment == "package_manager":
                logger.debug("Calling pm_interaction.handle_item_selection()")
                screen.pm_interaction.handle_item_selection()
            elif screen.selected_segment == "vim_management":
                panel = getattr(screen, "vim_management_panel", None)
                logger.info(f"[ENTER KEY] vim_management segment: panel exists={panel is not None}")
                if panel:
                    logger.info("[ENTER KEY] Calling panel.handle_enter()")
                    panel.handle_enter()
                else:
                    logger.error("[ENTER KEY] vim_management_panel is None!")
        else:
            logger.warning(f"Unknown panel focus state: {screen.current_panel_focus}")

    @staticmethod
    def action_select_segment(screen) -> None:
        """Quick select Settings segment (S key)."""
        screen.selected_segment = "settings"
        screen.current_panel_focus = "left"

    @staticmethod
    def action_refresh_current_page(screen) -> None:
        """Refresh current page (R key)."""
        from .navigation_manager import RefreshManager

        if screen.selected_segment == "system_info":
            screen.refresh_system_info()
        elif screen.selected_segment == "package_manager":
            RefreshManager.refresh_package_manager_page(screen)
        elif screen.selected_segment == "app_install":
            RefreshManager.refresh_app_install_page(screen)
        elif screen.selected_segment == "homebrew":
            RefreshManager.refresh_homebrew_page(screen)
        elif screen.selected_segment == "vim_management":
            panel = getattr(screen, "vim_management_panel", None)
            if panel:
                panel.action_refresh()

    @staticmethod
    def action_homebrew(screen) -> None:
        """Quick jump to Homebrew segment."""
        screen.selected_segment = "homebrew"

    @staticmethod
    def action_package_manager(screen) -> None:
        """Quick jump to Package Manager segment."""
        screen.selected_segment = "package_manager"

    @staticmethod
    def action_user_management(screen) -> None:
        """Quick jump to User Management segment."""
        screen.selected_segment = "user_management"

    @staticmethod
    def action_settings(screen) -> None:
        """Quick jump to Settings segment."""
        screen.selected_segment = "settings"

    @staticmethod
    def action_help(screen) -> None:
        """Quick jump to Help segment."""
        screen.selected_segment = "help"

    @staticmethod
    def action_quit(screen) -> None:
        """Quit the application."""
        screen.app.exit()

    @staticmethod
    def action_apply_app_changes(screen) -> None:
        """Apply app installation changes."""
        screen._apply_app_changes_internal()
