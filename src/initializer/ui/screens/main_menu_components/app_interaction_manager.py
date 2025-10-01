"""Application install interaction management.

This module handles core app_install interaction logic including
focus management, navigation, and selection state.
"""

from typing import List, Dict, Set, Optional


class AppInstallInteractionManager:
    """Manages app_install interaction state and basic operations."""

    def __init__(self, screen):
        """Initialize the app install interaction manager.

        Args:
            screen: Reference to the main menu screen
        """
        self.screen = screen

    def build_display_items(self, software_items) -> List[tuple]:
        """Build display items list based on expansion state.

        Args:
            software_items: List of software items

        Returns:
            List of (type, item, indent_level) tuples
        """
        from ....modules.software_models import ApplicationSuite

        display_items = []
        for item in software_items:
            display_items.append(("suite_or_app", item, 0))

            # If it's an expanded suite, add its components
            if isinstance(item, ApplicationSuite) and item.name in self.screen.app_expanded_suites:
                for component in item.components:
                    display_items.append(("component", component, 1))

        return display_items

    def ensure_valid_focus_index(self, display_items: List[tuple]) -> None:
        """Ensure focused index is within valid range.

        Args:
            display_items: List of display items
        """
        if display_items:
            max_index = len(display_items) - 1
            if self.screen.app_focused_index > max_index:
                self.screen.app_focused_index = max_index
            elif self.screen.app_focused_index < 0:
                self.screen.app_focused_index = 0
        else:
            self.screen.app_focused_index = 0

    def navigate_items(self, direction: str, display_items: List[tuple]) -> bool:
        """Navigate through app items.

        Args:
            direction: "up" or "down"
            display_items: List of display items

        Returns:
            True if navigation successful
        """
        if not display_items:
            return False

        if direction == "down":
            if self.screen.app_focused_index < len(display_items) - 1:
                self.screen.app_focused_index += 1
                return True
        elif direction == "up":
            if self.screen.app_focused_index > 0:
                self.screen.app_focused_index -= 1
                return True

        return False

    def toggle_current_item(self, display_items: List[tuple]) -> Optional[str]:
        """Toggle current item (suite expansion or app selection).

        Args:
            display_items: List of display items

        Returns:
            Action performed: "expanded", "collapsed", "selected", "deselected", or None
        """
        from ....modules.software_models import ApplicationSuite

        if not display_items or self.screen.app_focused_index >= len(display_items):
            return None

        item_type, item, _ = display_items[self.screen.app_focused_index]

        if item_type == "suite_or_app" and isinstance(item, ApplicationSuite):
            # Toggle suite expansion
            if item.name in self.screen.app_expanded_suites:
                self.screen.app_expanded_suites.remove(item.name)
                return "collapsed"
            else:
                self.screen.app_expanded_suites.add(item.name)
                return "expanded"
        else:
            # Toggle app selection
            app = item
            current_state = self.screen.app_selection_state.get(app.name, app.installed)
            self.screen.app_selection_state[app.name] = not current_state
            return "selected" if not current_state else "deselected"

    def calculate_changes(self, app_installer) -> dict:
        """Calculate which apps need to be installed/uninstalled.

        Args:
            app_installer: AppInstaller instance

        Returns:
            Dict with 'install' and 'uninstall' lists
        """
        changes = {"install": [], "uninstall": []}

        for app in app_installer.applications:
            selected = self.screen.app_selection_state.get(app.name, app.installed)

            if selected and not app.installed:
                changes["install"].append(app)
            elif not selected and app.installed:
                changes["uninstall"].append(app)

        return changes

    def reset_selection_state(self) -> None:
        """Reset app selection state."""
        self.screen.app_selection_state = {}
        self.screen.app_focused_index = 0
        self.screen.app_expanded_suites = set()