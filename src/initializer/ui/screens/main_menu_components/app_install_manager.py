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
        """Navigate through app items, skipping hidden (collapsed) components."""
        if not self.screen.app_install_cache:
            return

        display_items = self._build_display_items()

        if direction == "down":
            # Move down, skipping hidden items
            new_index = self.screen.app_focused_index + 1
            while new_index < len(display_items):
                item_data = display_items[new_index]
                # Check if this is a visible item
                if len(item_data) == 3:  # suite_or_app
                    break
                elif len(item_data) == 4 and item_data[3]:  # component with is_expanded=True
                    break
                new_index += 1

            if new_index < len(display_items):
                self.screen.app_focused_index = new_index
                self.update_focus_indicators()
                self.scroll_to_current("down")

        elif direction == "up":
            # Move up, skipping hidden items
            new_index = self.screen.app_focused_index - 1
            while new_index >= 0:
                item_data = display_items[new_index]
                # Check if this is a visible item
                if len(item_data) == 3:  # suite_or_app
                    break
                elif len(item_data) == 4 and item_data[3]:  # component with is_expanded=True
                    break
                new_index -= 1

            if new_index >= 0:
                self.screen.app_focused_index = new_index
                self.update_focus_indicators()
                self.scroll_to_current("up")

    def _build_display_items(self) -> List[tuple]:
        """Build display items list - includes all items, even collapsed ones.

        This matches the renderer behavior where all components are pre-rendered
        but hidden with display:none. Navigation logic will skip hidden items.
        """
        display_items = []
        for item in self.screen.app_install_cache:
            display_items.append(("suite_or_app", item, 0))
            # Always include all components, mark visibility for navigation
            if isinstance(item, ApplicationSuite):
                is_expanded = item.name in self.screen.app_expanded_suites
                for component in item.components:
                    display_items.append(("component", component, 1, is_expanded))
        return display_items

    @staticmethod
    def _unpack_display_item(item_data: tuple) -> tuple:
        """Safely unpack a display item tuple.

        Returns: (item_type, item, indent_level, is_visible)
        """
        if len(item_data) == 3:
            item_type, item, indent_level = item_data
            return item_type, item, indent_level, True
        else:  # len == 4
            item_type, item, indent_level, is_visible = item_data
            return item_type, item, indent_level, is_visible

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

        item_type, item, _, _ = self._unpack_display_item(display_items[self.screen.app_focused_index])
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
                    sub_type, sub_item, _, is_visible = self._unpack_display_item(display_items[idx])
                    if sub_type != "component":
                        break
                    if sub_item in components and is_visible:
                        visible_component_indices.append((idx, sub_item))

            for component in components:
                self.screen.app_selection_state[component.name] = target_state

            for idx, component in visible_component_indices:
                self._update_single_item_status(idx, component, target_state)

            # 更新组合应用包自身的状态显示
            self._update_single_item_status(self.screen.app_focused_index, item, target_state)

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
        """Toggle expansion state for the currently focused suite without full refresh."""
        from ....utils.logger import get_ui_logger
        logger = get_ui_logger("app_install")

        display_items = self._build_display_items()
        if not display_items or self.screen.app_focused_index >= len(display_items):
            logger.warning("[APP_INSTALL] Cannot toggle suite expansion: invalid focus index")
            return False

        item_type, item, _, _ = self._unpack_display_item(display_items[self.screen.app_focused_index])
        if not (item_type == "suite_or_app" and isinstance(item, ApplicationSuite)):
            logger.debug("[APP_INSTALL] Focused item is not a suite, skipping expansion toggle")
            return False

        is_expanding = item.name not in self.screen.app_expanded_suites

        if is_expanding:
            logger.info(f"[APP_INSTALL] Expanding suite: {item.name}")
            self.screen.app_expanded_suites.add(item.name)
        else:
            logger.info(f"[APP_INSTALL] Collapsing suite: {item.name}")
            self.screen.app_expanded_suites.remove(item.name)

        # Use incremental update instead of full refresh
        self._update_suite_expansion_incremental(item, is_expanding)
        return True

    def _update_suite_expansion_incremental(self, suite: ApplicationSuite, is_expanding: bool) -> None:
        """Incrementally update suite expansion without page refresh.

        This method only updates the expansion icon and toggles CSS display property,
        avoiding any DOM insertion/removal that would cause visual flicker.
        """
        from ....utils.logger import get_ui_logger
        logger = get_ui_logger("app_install")

        try:
            # Find all app containers with current suffix
            if not hasattr(self.screen, '_app_unique_suffix') or self.screen._app_unique_suffix is None:
                logger.warning("[APP_INSTALL] No unique suffix, using full refresh")
                self._refresh_app_install_view()
                return

            suffix = self.screen._app_unique_suffix

            # 1. Update the expansion icon on the suite container
            containers = list(self.screen.query(f"Horizontal.app-item-container"))
            matching_containers = [c for c in containers if f"-{suffix}" in str(c.id)]

            if self.screen.app_focused_index >= len(matching_containers):
                logger.warning("[APP_INSTALL] Focus index out of range")
                self._refresh_app_install_view()
                return

            suite_container = matching_containers[self.screen.app_focused_index]
            content_widgets = suite_container.query(".app-item-content")

            if content_widgets:
                content_widget = content_widgets[0]
                expansion_icon = "▼" if is_expanding else "▶"
                current_text = str(content_widget.renderable)

                if current_text.startswith("▼ ") or current_text.startswith("▶ "):
                    new_text = expansion_icon + current_text[1:]
                    content_widget.update(new_text)
                    logger.info(f"[APP_INSTALL] Updated expansion icon to {expansion_icon}")

            # 2. Toggle display property of component containers (they're already in DOM)
            suite_class = f"suite-{suite.name.replace(' ', '-')}"
            component_containers = self.screen.query(f".{suite_class}")

            display_value = "block" if is_expanding else "none"
            for comp_container in component_containers:
                comp_container.styles.display = display_value

            logger.info(f"[APP_INSTALL] Toggled {len(component_containers)} components to display={display_value}")

        except Exception as e:
            logger.error(f"[APP_INSTALL] Error in incremental update: {e}", exc_info=True)
            self._refresh_app_install_view()

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

            containers = list(self.screen.query("Horizontal.app-item-container"))
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
            existing_without_arrow = getattr(status_widget, "_text_without_arrow", "")
            leading_spaces = len(existing_without_arrow) - len(existing_without_arrow.lstrip(" "))
            indent_prefix = existing_without_arrow[:leading_spaces] if leading_spaces > 0 else ""

            if isinstance(item, ApplicationSuite):
                status_text_core = self._determine_suite_status_text(item)
                status_text_with_indent = status_text_core
            else:
                if not indent_prefix:
                    for software_item in self.screen.app_install_cache or []:
                        if isinstance(software_item, ApplicationSuite) and item in getattr(software_item, "components", []):
                            indent_prefix = "  "
                            break

                if getattr(item, "installed", False) and not is_selected:
                    status_text_core = "[red]- To Uninstall[/red]"
                elif getattr(item, "installed", False) and is_selected:
                    status_text_core = "[green]\u2713 Installed[/green]"
                elif not getattr(item, "installed", False) and is_selected:
                    status_text_core = "[yellow]+ To Install[/yellow]"
                else:
                    status_text_core = "[bright_black]\u25cb Available[/bright_black]"

                status_text_with_indent = f"{indent_prefix}{status_text_core}"

            status_widget._text_without_arrow = status_text_with_indent

            if index == self.screen.app_focused_index and is_right_focused:
                new_text = f"[#7dd3fc]\u25b6[/#7dd3fc] {status_text_with_indent}"
            else:
                new_text = f"  {status_text_with_indent}"

            status_widget.update(new_text)
            logger.info(
                f"[APP_INSTALL] Updated status for {getattr(item, 'name', 'unknown')} at index {index}, stored text: {status_text_with_indent[:30]}"
            )

        except Exception as e:
            logger.error(f"[APP_INSTALL] Error updating single item: {e}", exc_info=True)

    def _determine_suite_status_text(self, suite: ApplicationSuite) -> str:
        """根据套件内部组件的选择状态生成状态文本。"""
        selection_state = self.screen.app_selection_state or {}
        components = list(getattr(suite, "components", []) or [])

        install_targets = 0
        uninstall_targets = 0
        for component in components:
            selected = selection_state.get(component.name, component.installed)
            if component.installed and not selected:
                uninstall_targets += 1
            elif not component.installed and selected:
                install_targets += 1

        if install_targets > 0 and uninstall_targets == 0:
            return "[yellow]+ Install All[/yellow]"
        if uninstall_targets > 0 and install_targets == 0:
            return "[red]- Uninstall All[/red]"
        if install_targets > 0 and uninstall_targets > 0:
            return "[magenta]* Mixed Suite Changes[/magenta]"

        try:
            return suite.get_install_status()
        except Exception:
            total_components = len(components)
            installed_components = sum(1 for component in components if component.installed)
            if total_components == 0:
                return "[bright_black]\u25cb 0/0[/bright_black]"
            if installed_components == total_components:
                return f"[green]\u25cf {total_components}/{total_components}[/green]"
            return f"[yellow]\u25d0 {installed_components}/{total_components}[/yellow]"

    def handle_enter_key(self) -> bool:
        """Handle Enter key in app install section."""
        from ....utils.logger import get_ui_logger
        logger = get_ui_logger("app_install")

        display_items = self._build_display_items()
        logger.info(f"[APP_INSTALL] handle_enter_key: display_items={len(display_items)}, focused_index={self.screen.app_focused_index}")

        if not display_items or self.screen.app_focused_index >= len(display_items):
            logger.warning("[APP_INSTALL] Invalid state in handle_enter_key")
            return False

        item_type, item, _, _ = self._unpack_display_item(display_items[self.screen.app_focused_index])
        item_name = getattr(item, "name", str(item))
        logger.info(f"[APP_INSTALL] Enter pressed on item_type={item_type}, item={item_name}")

        self.apply_single_change()
        return True

    def apply_single_change(self) -> None:
        """Apply change for single focused item or suite."""
        display_items = self._build_display_items()

        if not display_items or self.screen.app_focused_index >= len(display_items):
            return

        _, item, _, _ = self._unpack_display_item(display_items[self.screen.app_focused_index])

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