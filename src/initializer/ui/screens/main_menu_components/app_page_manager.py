"""Application installation page manager.

This module handles all logic related to the application installation page,
including app selection, state management, and installation actions.
"""

from typing import List, Dict, Set, Optional
from textual.containers import ScrollableContainer
from textual.widgets import Label, Static, Checkbox
from textual import work

from ....modules.app_installer import AppInstaller
from ....modules.software_models import Application, ApplicationSuite
from ....utils.logger import get_ui_logger

logger = get_ui_logger("app_page_manager")


class AppPageManager:
    """Manages the application installation page logic."""

    def __init__(self, screen, app_installer: AppInstaller):
        """Initialize the app page manager.

        Args:
            screen: Reference to the main menu screen
            app_installer: AppInstaller instance
        """
        self.screen = screen
        self.app_installer = app_installer
        
        # App selection state
        self.app_selection_state: Dict[str, bool] = {}
        self.app_focused_index: int = 0
        self.app_expanded_suites: Set[str] = set()
        
    def build_display_items(self) -> List[Dict]:
        """Build a flat list of items for display (suites and apps).
        
        Returns:
            List of display item dictionaries
        """
        display_items = []
        software_items = self.app_installer.software_items
        
        for item in software_items:
            if isinstance(item, ApplicationSuite):
                # Add suite header
                display_items.append({
                    "type": "suite",
                    "name": item.name,
                    "description": item.description,
                    "category": item.category,
                    "suite": item,
                    "expanded": item.name in self.app_expanded_suites
                })
                
                # Add components if expanded
                if item.name in self.app_expanded_suites:
                    for component in item.components:
                        display_items.append({
                            "type": "component",
                            "name": component.name,
                            "description": component.description,
                            "app": component,
                            "suite": item
                        })
            else:
                # Standalone application
                display_items.append({
                    "type": "standalone",
                    "name": item.name,
                    "description": item.description,
                    "app": item
                })
        
        return display_items

    def calculate_app_changes(self) -> dict:
        """Calculate which apps need to be installed or uninstalled.
        
        Returns:
            Dictionary with 'install' and 'uninstall' lists
        """
        changes = {"install": [], "uninstall": []}
        
        for app in self.app_installer.applications:
            selected = self.app_selection_state.get(app.name, app.installed)
            
            if selected and not app.installed:
                changes["install"].append(app)
            elif not selected and app.installed:
                changes["uninstall"].append(app)
        
        return changes

    def toggle_current_app(self, display_items: List[Dict]) -> Optional[str]:
        """Toggle the selection state of the currently focused app.
        
        Args:
            display_items: List of display items
            
        Returns:
            Message string or None
        """
        if not display_items or self.app_focused_index >= len(display_items):
            return None
            
        current_item = display_items[self.app_focused_index]
        
        if current_item["type"] == "suite":
            # Toggle suite expansion
            suite_name = current_item["name"]
            if suite_name in self.app_expanded_suites:
                self.app_expanded_suites.remove(suite_name)
            else:
                self.app_expanded_suites.add(suite_name)
            return "expanded" if suite_name in self.app_expanded_suites else "collapsed"
        else:
            # Toggle app selection
            app = current_item["app"]
            current_state = self.app_selection_state.get(app.name, app.installed)
            self.app_selection_state[app.name] = not current_state
            return "toggled"

    def reset_selection_state(self):
        """Reset app selection state to match installed state."""
        self.app_selection_state = {}
        self.app_focused_index = 0
        logger.debug("Reset app selection state")

    def ensure_valid_focus_index(self, display_items: List[Dict]):
        """Ensure the focused index is within valid range.
        
        Args:
            display_items: List of display items
        """
        if display_items:
            self.app_focused_index = max(0, min(self.app_focused_index, len(display_items) - 1))
        else:
            self.app_focused_index = 0

    def navigate_apps(self, direction: str, display_items: List[Dict]) -> bool:
        """Navigate through app items.
        
        Args:
            direction: "up" or "down"
            display_items: List of display items
            
        Returns:
            True if navigation was successful
        """
        if not display_items:
            return False
            
        if direction == "down":
            if self.app_focused_index < len(display_items) - 1:
                self.app_focused_index += 1
                return True
        elif direction == "up":
            if self.app_focused_index > 0:
                self.app_focused_index -= 1
                return True
                
        return False
