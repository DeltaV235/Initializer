"""Package Manager interaction management.

This module handles all Package Manager interaction logic including
focus management, navigation, and item selection.
"""

from typing import Optional
from textual.widgets import Static


class PackageManagerInteractionManager:
    """Manages Package Manager interaction state and operations."""

    def __init__(self, screen):
        """Initialize the PM interaction manager.

        Args:
            screen: Reference to the main menu screen
        """
        self.screen = screen
        self._pm_focused_item: Optional[str] = None  # "manager" or "source"
        self._primary_pm = None
        self._pm_unique_suffix: Optional[str] = None

    def update_focus_indicators(self, clear_left_arrows: bool = False) -> None:
        """Update arrow indicators for package manager items.

        Args:
            clear_left_arrows: If True, clear all left-side arrows
        """
        # Import at the top to avoid any issues
        from textual.widgets import Static
        from ....utils.logger import get_ui_logger

        logger = get_ui_logger("pm_interaction")

        try:
            logger.info(f"[PM_INTERACTION] update_focus_indicators called: clear_left_arrows={clear_left_arrows}")
            logger.info(f"[PM_INTERACTION] _pm_unique_suffix: {self._pm_unique_suffix}")
            logger.info(f"[PM_INTERACTION] _pm_focused_item: {self._pm_focused_item}")
            logger.info(f"[PM_INTERACTION] current_panel_focus: {self.screen.current_panel_focus}")

            if not hasattr(self, '_pm_unique_suffix') or self._pm_unique_suffix is None:
                logger.warning("[PM_INTERACTION] update_focus_indicators: No _pm_unique_suffix, returning")
                return

            suffix = self._pm_unique_suffix
            logger.info(f"[PM_INTERACTION] Using suffix: {suffix}")

            # Get the two items
            manager_item = self.screen.query_one(f"#pm-manager-item-{suffix}", Static)
            source_item = self.screen.query_one(f"#pm-source-item-{suffix}", Static)
            logger.info(f"[PM_INTERACTION] Found widgets: manager={manager_item.id}, source={source_item.id}")

            # Determine if right panel has focus
            is_right_focused = (self.screen.current_panel_focus == "right")
            logger.info(f"[PM_INTERACTION] is_right_focused: {is_right_focused}, _pm_focused_item: {self._pm_focused_item}")

            # Clear all arrows first if requested
            if clear_left_arrows:
                logger.info("[PM_INTERACTION] Clearing left arrows")
                if manager_item and hasattr(manager_item, 'update'):
                    manager_text = self._manager_text if hasattr(self, '_manager_text') else "UNKNOWN"
                    manager_item.update(f"  {manager_text}")
                    logger.info(f"[PM_INTERACTION] Cleared manager arrow")
                if source_item and hasattr(source_item, 'update'):
                    source_text = self._source_text if hasattr(self, '_source_text') else "UNKNOWN"
                    source_item.update(f"  {source_text}")
                    logger.info(f"[PM_INTERACTION] Cleared source arrow")
                return

            # Update arrows based on focus
            if manager_item and hasattr(manager_item, 'update'):
                # Use stored text content instead of trying to read from widget
                manager_text = self._manager_text if hasattr(self, '_manager_text') else "UNKNOWN"
                logger.info(f"[PM_INTERACTION] Manager text from storage: {manager_text}")

                # Add arrow if this item is focused
                if self._pm_focused_item == "manager" and is_right_focused:
                    new_text = f"[#7dd3fc]▶[/#7dd3fc] {manager_text}"
                    logger.info(f"[PM_INTERACTION] ✓ Adding arrow to manager item")
                else:
                    new_text = f"  {manager_text}"
                    logger.info(f"[PM_INTERACTION] ✗ NOT adding arrow (_pm_focused_item={self._pm_focused_item}, is_right_focused={is_right_focused})")

                manager_item.update(new_text)
                logger.info(f"[PM_INTERACTION] Manager item updated to: {new_text[:60]}")

            if source_item and hasattr(source_item, 'update'):
                # Use stored text content instead of trying to read from widget
                source_text = self._source_text if hasattr(self, '_source_text') else "UNKNOWN"
                logger.info(f"[PM_INTERACTION] Source text from storage: {source_text[:60]}")

                # Add arrow if this item is focused
                if self._pm_focused_item == "source" and is_right_focused:
                    new_text = f"[#7dd3fc]▶[/#7dd3fc] {source_text}"
                    logger.info(f"[PM_INTERACTION] ✓ Adding arrow to source item")
                else:
                    new_text = f"  {source_text}"

                source_item.update(new_text)
                logger.info(f"[PM_INTERACTION] Source item updated to: {new_text[:60]}")

            logger.info("[PM_INTERACTION] update_focus_indicators completed successfully")
        except Exception as e:
            logger.error(f"[PM_INTERACTION] Exception in update_focus_indicators: {e}", exc_info=True)

    def clear_focus_indicators(self) -> None:
        """Clear all PM focus indicators."""
        self.update_focus_indicators(clear_left_arrows=True)

    def handle_item_selection(self) -> None:
        """Handle Enter key on PM items - show source selection modal."""
        from ....utils.logger import get_ui_logger
        logger = get_ui_logger("pm_interaction")

        logger.info(f"[PM_INTERACTION] handle_item_selection called: _pm_focused_item={self._pm_focused_item}")

        # Both manager and source items can open the source selection modal
        if self._pm_focused_item in ["manager", "source"] and hasattr(self, '_primary_pm') and self._primary_pm:
            logger.info("[PM_INTERACTION] Opening source selection modal")
            self.screen._open_source_selection_modal()
        else:
            logger.warning(f"[PM_INTERACTION] Cannot open modal: focused_item={self._pm_focused_item}, has_primary_pm={hasattr(self, '_primary_pm')}")

    def navigate_items(self, direction: str) -> None:
        """Navigate between PM items.

        Args:
            direction: "up" or "down"
        """
        if not self.is_in_pm_section():
            return

        # Initialize focus if not set
        if self._pm_focused_item is None:
            self._pm_focused_item = "manager"
            self.update_focus_indicators()
            return

        # Navigate
        if direction == "down":
            if self._pm_focused_item == "manager":
                self._pm_focused_item = "source"
        elif direction == "up":
            if self._pm_focused_item == "source":
                self._pm_focused_item = "manager"

        self.update_focus_indicators()

    def is_in_pm_section(self) -> bool:
        """Check if currently in package manager section."""
        return (self.screen.selected_segment == "package_manager" and
                self.screen.current_panel_focus == "right" and
                hasattr(self, '_primary_pm') and
                self._primary_pm is not None)

    def reset_state(self) -> None:
        """Reset PM interaction state."""
        self._pm_focused_item = None
        self._primary_pm = None
        self._pm_unique_suffix = None

    def set_primary_pm(self, primary_pm, unique_suffix: str) -> None:
        """Set the primary package manager and unique suffix.

        Args:
            primary_pm: Primary package manager object
            unique_suffix: Unique suffix for widget IDs
        """
        self._primary_pm = primary_pm
        self._pm_unique_suffix = unique_suffix

        # Store the text content for update operations
        self._manager_text = primary_pm.name.upper() if primary_pm else ""
        if primary_pm and primary_pm.current_source:
            source = primary_pm.current_source
            if len(source) > 60:
                source = source[:57] + "..."
            self._source_text = source
        else:
            self._source_text = "Not configured"

        # Only reset focused_item if suffix changed (data reloaded)
        # This preserves focus state when just switching panels
        if not hasattr(self, '_last_suffix') or self._last_suffix != unique_suffix:
            self._pm_focused_item = None
            self._last_suffix = unique_suffix