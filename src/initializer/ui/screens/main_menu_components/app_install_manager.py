"""Complete app install management logic.

This module contains all app_install related business logic including
focus management, navigation, execution, and state management.
"""

from typing import List, Dict, Optional
from textual.widgets import Static
from ....modules.software_models import ApplicationSuite


from textual.containers import ScrollableContainer

from .app_install_renderer import AppInstallRenderer

class AppInstallManager:
    """Complete manager for app install functionality."""

    def __init__(self, screen):
        """Initialize the app install manager."""
        self.screen = screen

    def clear_focus_indicators(self) -> None:
        """Clear all app focus indicators."""
        from ....utils.logger import get_ui_logger
        logger = get_ui_logger("app_install")

        if not hasattr(self.screen, '_app_unique_suffix') or self.screen._app_unique_suffix is None:
            logger.info("[APP_INSTALL] clear_focus_indicators: No unique suffix")
            return

        try:
            suffix = self.screen._app_unique_suffix
            logger.info(f"[APP_INSTALL] Clearing arrows for suffix {suffix}")

            for i, container in enumerate(self.screen.query(f"Horizontal.app-item-container")):
                if f"-{suffix}" not in str(container.id):
                    continue

                status_widgets = container.query(".app-item-status")
                for status_widget in status_widgets:
                    if hasattr(status_widget, 'update') and hasattr(status_widget, '_text_without_arrow'):
                        # Use stored text without arrow
                        text_without_arrow = status_widget._text_without_arrow
                        status_widget.update(f"  {text_without_arrow}")
                        logger.info(f"[APP_INSTALL] Cleared arrow from widget {i}")

            logger.info(f"[APP_INSTALL] clear_focus_indicators completed")
        except Exception as e:
            logger.error(f"[APP_INSTALL] Exception in clear_focus_indicators: {e}", exc_info=True)

    def update_focus_indicators(self) -> None:
        """Update app focus indicators based on current index."""
        from ....utils.logger import get_ui_logger
        logger = get_ui_logger("app_install")

        if not hasattr(self.screen, '_app_unique_suffix') or self.screen._app_unique_suffix is None:
            logger.info("[APP_INSTALL] No unique suffix, returning")
            return

        try:
            suffix = self.screen._app_unique_suffix
            is_right_focused = (self.screen.current_panel_focus == "right")
            logger.info(
                f"[APP_INSTALL] update_focus_indicators: suffix={suffix}, is_right_focused={is_right_focused}, app_focused_index={self.screen.app_focused_index}"
            )

            all_containers = list(self.screen.query("Horizontal.app-item-container"))
            matching_containers = [
                container for container in all_containers if f"-{suffix}" in str(container.id)
            ]
            logger.info(
                f"[APP_INSTALL] Matching containers: total={len(all_containers)}, current_segment={len(matching_containers)}"
            )

            for visible_index, container in enumerate(matching_containers):
                status_widgets = container.query(".app-item-status")
                logger.info(
                    f"[APP_INSTALL] Container visible_index={visible_index}: found {len(status_widgets)} status widgets"
                )

                for status_widget in status_widgets:
                    if not hasattr(status_widget, 'update'):
                        continue

                    if not hasattr(status_widget, '_text_without_arrow'):
                        logger.warning(
                            f"[APP_INSTALL] Widget {visible_index}: NO _text_without_arrow attribute"
                        )
                        continue

                    text_without_arrow = status_widget._text_without_arrow
                    logger.info(
                        f"[APP_INSTALL] Widget {visible_index}: using stored text: {text_without_arrow[:40]}"
                    )

                    if visible_index == self.screen.app_focused_index and is_right_focused:
                        new_text = "[#7dd3fc]\u25b6[/#7dd3fc] " + text_without_arrow
                        logger.info(f"[APP_INSTALL] \u2713 Adding arrow to widget {visible_index}")
                    else:
                        new_text = "  " + text_without_arrow

                    status_widget.update(new_text)
                    logger.info(
                        f"[APP_INSTALL] Widget {visible_index} updated to: {new_text[:40]}"
                    )
        except Exception as e:
            logger.error(f"[APP_INSTALL] Exception: {e}", exc_info=True)

    def scroll_to_current(self, direction: Optional[str] = None) -> None:
        """Scroll to show current focused app."""
        try:
            settings_scroll = self.screen.query_one("#settings-scroll")
            if direction:
                if direction == "down":
                    settings_scroll.scroll_page_down()
                elif direction == "up":
                    settings_scroll.scroll_page_up()
        except Exception:
            pass

    def navigate_items(self, direction: str) -> None:
        """Navigate through app items."""
        if not self.screen.app_install_cache:
            return

        display_items = self._build_display_items()

        if direction == "down":
            if self.screen.app_focused_index < len(display_items) - 1:
                self.screen.app_focused_index += 1
                self.update_focus_indicators()
                self.scroll_to_current("down")
        elif direction == "up":
            if self.screen.app_focused_index > 0:
                self.screen.app_focused_index -= 1
                self.update_focus_indicators()
                self.scroll_to_current("up")

    def _build_display_items(self) -> List[tuple]:
        """Build display items list."""
        display_items = []
        for item in self.screen.app_install_cache:
            display_items.append(("suite_or_app", item, 0))
            if isinstance(item, ApplicationSuite) and item.name in self.screen.app_expanded_suites:
                for component in item.components:
                    display_items.append(("component", component, 1))
        return display_items

    def _refresh_app_install_view(self) -> None:
        """在保持焦点的情况下刷新应用列表，避免整页刷新。"""
        from ....utils.logger import get_ui_logger
        logger = get_ui_logger("app_install")

        try:
            settings_container = self.screen.query_one("#settings-scroll", ScrollableContainer)

            # 清空旧组件后重新渲染，避免整页刷新造成的闪烁
            for child in list(settings_container.children):
                try:
                    child.remove()
                except Exception as exc:
                    logger.debug(f"[APP_INSTALL] 清理旧组件失败: {exc}")

            settings_container.styles.scrollbar_size = 1

            if not getattr(self.screen, "app_install_cache", None):
                logger.debug("[APP_INSTALL] 无应用缓存可刷新")
                return

            AppInstallRenderer.display_app_install_list(
                self.screen,
                settings_container,
                self.screen.app_install_cache,
            )

            if self.screen.current_panel_focus == "right":
                settings_container.focus()
                self.update_focus_indicators()
        except Exception as exc:
            logger.error(f"[APP_INSTALL] 刷新应用列表失败: {exc}", exc_info=True)

    def toggle_current_item(self) -> None:
        """Toggle selection state for the currently focused item."""
        from ....utils.logger import get_ui_logger
        logger = get_ui_logger("app_install")

        display_items = self._build_display_items()
        logger.info(f"[APP_INSTALL] toggle_current_item: display_items={len(display_items)}, focused_index={self.screen.app_focused_index}")

        if not display_items or self.screen.app_focused_index >= len(display_items):
            logger.warning("[APP_INSTALL] Invalid state: no items or index out of range")
            return

        item_type, item, _ = display_items[self.screen.app_focused_index]
        item_name = getattr(item, "name", str(item))
        logger.info(f"[APP_INSTALL] Toggle selection for item_type={item_type}, item={item_name}")

        if item_type == "suite_or_app" and isinstance(item, ApplicationSuite):
            components = list(getattr(item, "components", []))
            if not components:
                logger.info(f"[APP_INSTALL] Suite '{item.name}' has no components, skipping selection toggle")
                return

            all_selected = all(
                self.screen.app_selection_state.get(component.name, component.installed)
                for component in components
            )
            target_state = not all_selected
            logger.info(
                f"[APP_INSTALL] Toggling suite '{item.name}' components to {target_state} (all_selected={all_selected})"
            )

            expanded = item.name in self.screen.app_expanded_suites
            visible_component_indices = []
            if expanded:
                for idx in range(self.screen.app_focused_index + 1, len(display_items)):
                    sub_type, sub_item, _ = display_items[idx]
                    if sub_type != "component":
                        break
                    if sub_item in components:
                        visible_component_indices.append((idx, sub_item))

            for component in components:
                self.screen.app_selection_state[component.name] = target_state

            for idx, component in visible_component_indices:
                self._update_single_item_status(idx, component, target_state)

            if self.screen.current_panel_focus == "right":
                self.update_focus_indicators()
            return

        # 常规应用或组件，直接切换选中状态
        app = item
        current_state = self.screen.app_selection_state.get(app.name, app.installed)
        new_state = not current_state
        logger.info(f"[APP_INSTALL] Toggling selection for {app.name}: {current_state} -> {new_state}")
        self.screen.app_selection_state[app.name] = new_state

        # Update only the status text of current widget, keep arrow
        self._update_single_item_status(self.screen.app_focused_index, app, new_state)

    def toggle_current_suite_expansion(self) -> bool:
        """Toggle expansion state for the currently focused suite."""
        from ....utils.logger import get_ui_logger
        logger = get_ui_logger("app_install")

        display_items = self._build_display_items()
        if not display_items or self.screen.app_focused_index >= len(display_items):
            logger.warning("[APP_INSTALL] Cannot toggle suite expansion: invalid focus index")
            return False

        item_type, item, _ = display_items[self.screen.app_focused_index]
        if not (item_type == "suite_or_app" and isinstance(item, ApplicationSuite)):
            logger.debug("[APP_INSTALL] Focused item is not a suite, skipping expansion toggle")
            return False

        if item.name in self.screen.app_expanded_suites:
            logger.info(f"[APP_INSTALL] Collapsing suite: {item.name}")
            self.screen.app_expanded_suites.remove(item.name)
        else:
            logger.info(f"[APP_INSTALL] Expanding suite: {item.name}")
            self.screen.app_expanded_suites.add(item.name)

        self._refresh_app_install_view()
        return True

    def _update_single_item_status(self, index: int, item, is_selected: bool) -> None:
        """Update status text for a single item without full refresh."""
        from ....utils.logger import get_ui_logger
        logger = get_ui_logger("app_install")

        if not hasattr(self.screen, '_app_unique_suffix') or self.screen._app_unique_suffix is None:
            logger.warning("[APP_INSTALL] No unique suffix, cannot update single item")
            return

        try:
            suffix = self.screen._app_unique_suffix
            is_right_focused = (self.screen.current_panel_focus == "right")

            # Find the container for this index
            containers = list(self.screen.query(f"Horizontal.app-item-container"))
            matching_containers = [c for c in containers if f"-{suffix}" in str(c.id)]

            if index >= len(matching_containers):
                logger.warning(f"[APP_INSTALL] Index {index} out of range for containers")
                return

            container = matching_containers[index]
            status_widgets = container.query(".app-item-status")

            if not status_widgets:
                logger.warning(f"[APP_INSTALL] No status widget found for index {index}")
                return

            status_widget = status_widgets[0]

            # Determine new status text
            if item.installed and not is_selected:
                status_text = "[red]- To Uninstall[/red]"
            elif item.installed and is_selected:
                status_text = "[green]\u2713 Installed[/green]"
            elif not item.installed and is_selected:
                status_text = "[yellow]+ To Install[/yellow]"
            else:
                status_text = "[bright_black]\u25cb Available[/bright_black]"

            # 保留缩进：优先复用现有文本前缀，无则按层级推断
            existing_without_arrow = getattr(status_widget, "_text_without_arrow", "")
            leading_spaces = len(existing_without_arrow) - len(existing_without_arrow.lstrip(" "))
            indent_prefix = existing_without_arrow[:leading_spaces] if leading_spaces > 0 else ""

            if not indent_prefix and not isinstance(item, ApplicationSuite):
                for software_item in self.screen.app_install_cache or []:
                    if isinstance(software_item, ApplicationSuite) and item in getattr(software_item, "components", []):
                        indent_prefix = "  "
                        break

            status_text_with_indent = f"{indent_prefix}{status_text}"

            # 更新不带箭头的缓存文本，保留缩进用于后续刷新
            status_widget._text_without_arrow = status_text_with_indent

            # Add arrow if this is the focused item
            if index == self.screen.app_focused_index and is_right_focused:
                new_text = f"[#7dd3fc]\u25b6[/#7dd3fc] {status_text_with_indent}"
            else:
                new_text = f"  {status_text_with_indent}"

            status_widget.update(new_text)
            logger.info(f"[APP_INSTALL] Updated status for {item.name} at index {index}, stored text: {status_text[:30]}")

        except Exception as e:
            logger.error(f"[APP_INSTALL] Error updating single item: {e}", exc_info=True)

    def handle_enter_key(self) -> bool:
        """Handle Enter key in app install section."""
        from ....utils.logger import get_ui_logger
        logger = get_ui_logger("app_install")

        display_items = self._build_display_items()
        logger.info(f"[APP_INSTALL] handle_enter_key: display_items={len(display_items)}, focused_index={self.screen.app_focused_index}")

        if not display_items or self.screen.app_focused_index >= len(display_items):
            logger.warning("[APP_INSTALL] Invalid state in handle_enter_key")
            return False

        item_type, item, _ = display_items[self.screen.app_focused_index]
        item_name = getattr(item, "name", str(item))
        logger.info(f"[APP_INSTALL] Enter pressed on item_type={item_type}, item={item_name}")

        self.apply_single_change()
        return True

    def apply_single_change(self) -> None:
        """Apply change for single focused item or suite."""
        display_items = self._build_display_items()

        if not display_items or self.screen.app_focused_index >= len(display_items):
            return

        _, item, _ = display_items[self.screen.app_focused_index]

        from ....utils.logger import get_ui_logger
        logger = get_ui_logger("app_install")

        if isinstance(item, ApplicationSuite):
            actions = []
            for component in item.components:
                is_selected = self.screen.app_selection_state.get(component.name, component.installed)
                if component.installed and not is_selected:
                    actions.append({"action": "uninstall", "application": component})
                elif not component.installed and is_selected:
                    actions.append({"action": "install", "application": component})

            if not actions:
                logger.info(f"[APP_INSTALL] Suite '{item.name}' has no pending changes")
                return

            from .modal_manager import ModalManager
            ModalManager.show_single_app_confirmation(self.screen, actions)
            return

        is_selected = self.screen.app_selection_state.get(item.name, item.installed)

        if item.installed and not is_selected:
            action = {"action": "uninstall", "application": item}
        elif not item.installed and is_selected:
            action = {"action": "install", "application": item}
        else:
            return

        # Call ModalManager to show confirmation
        from .modal_manager import ModalManager
        ModalManager.show_single_app_confirmation(self.screen, [action])

    def execute_changes(self, changes: dict) -> None:
        """Execute app installation changes."""
        actions = []

        for item in self.screen.app_install_cache:
            if not isinstance(item, ApplicationSuite):
                is_selected = self.screen.app_selection_state.get(item.name, item.installed)
                if item.installed and not is_selected:
                    actions.append({"action": "uninstall", "application": item})
                elif not item.installed and is_selected:
                    actions.append({"action": "install", "application": item})
            else:
                for component in item.components:
                    is_selected = self.screen.app_selection_state.get(component.name, component.installed)
                    if component.installed and not is_selected:
                        actions.append({"action": "uninstall", "application": component})
                    elif not component.installed and is_selected:
                        actions.append({"action": "install", "application": component})

        if not actions:
            return

        from ..modals.app_install_progress import AppInstallProgressScreen
        progress_screen = AppInstallProgressScreen(actions, self.screen.app_installer, self.screen.config_manager)
        self.screen.app.push_screen(progress_screen, self.screen._on_install_complete)