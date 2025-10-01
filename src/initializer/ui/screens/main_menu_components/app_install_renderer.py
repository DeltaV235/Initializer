"""Application install display rendering.

This module handles the complex display logic for the app install page,
including hierarchical display of suites and applications.
"""

from textual.containers import ScrollableContainer, Horizontal
from textual.widgets import Label, Static, Rule
from ....modules.software_models import ApplicationSuite


class AppInstallRenderer:
    """Renders app install UI components."""

    @staticmethod
    def display_app_install_list(screen, container: ScrollableContainer, software_items) -> None:
        """Display hierarchical software items list in the container.

        Args:
            screen: Reference to the screen (for accessing state)
            container: Container to mount widgets into
            software_items: List of software items to display
        """
        # Handle error case
        if isinstance(software_items, dict) and "error" in software_items:
            container.mount(Label(f"Error loading App info: {software_items['error']}", classes="info-display"))
            return

        container.mount(Label("Available Applications:", classes="section-header"))
        container.mount(Rule())

        # Generate unique suffix to avoid ID conflicts
        import time
        unique_suffix = str(int(time.time() * 1000))[-6:]
        screen._app_unique_suffix = unique_suffix

        # Build display list based on expansion state
        display_items = []
        for item in software_items:
            display_items.append(("suite_or_app", item, 0))

            # If it's an expanded suite, add its components
            if isinstance(item, ApplicationSuite) and item.name in screen.app_expanded_suites:
                for component in item.components:
                    display_items.append(("component", component, 1))

        # Display each item
        for i, (item_type, item, indent_level) in enumerate(display_items):
            is_right_focused = (screen.current_panel_focus == "right")
            arrow = "[#7dd3fc]▶[/#7dd3fc] " if (i == screen.app_focused_index and is_right_focused) else "  "
            indent = "  " * indent_level

            if item_type == "suite_or_app" and isinstance(item, ApplicationSuite):
                status_display, content_text = AppInstallRenderer._render_suite(
                    item, screen.app_expanded_suites, arrow, indent
                )
            elif item_type == "component":
                status_display, content_text = AppInstallRenderer._render_component(
                    item, screen.app_selection_state, display_items, i, arrow, indent
                )
            else:
                status_display, content_text = AppInstallRenderer._render_standalone(
                    item, screen.app_selection_state, arrow, indent
                )

            # Create horizontal container
            app_container = Horizontal(classes="app-item-container", id=f"app-container-{i}-{unique_suffix}")
            status_widget = Static(status_display, classes="app-item-status")
            content_widget = Static(content_text, classes="app-item-content")

            # Store the text without arrow for later updates
            # status_display format: "{arrow}{indent}{status_text}"
            # Extract text after arrow (first 2 or ~20 chars)
            if status_display.startswith("[#7dd3fc]▶[/#7dd3fc] "):
                text_without_arrow = status_display[len("[#7dd3fc]▶[/#7dd3fc] "):]
            elif status_display.startswith("  "):
                text_without_arrow = status_display[2:]
            else:
                text_without_arrow = status_display

            status_widget._text_without_arrow = text_without_arrow

            container.mount(app_container)
            app_container.mount(status_widget)
            app_container.mount(content_widget)

        container.mount(Static("", classes="bottom-spacer"))

    @staticmethod
    def _render_suite(item: ApplicationSuite, expanded_suites: set, arrow: str, indent: str) -> tuple:
        """Render a suite item."""
        expansion_icon = "▼" if item.name in expanded_suites else "▶"
        suite_name = f"{expansion_icon} {item.name}"

        installed_count = sum(1 for c in item.components if c.installed)
        total_count = len(item.components)

        if installed_count == 0:
            status_text = f"[bright_black]○ {installed_count}/{total_count}[/bright_black]"
        elif installed_count == total_count:
            status_text = f"[green]● {installed_count}/{total_count}[/green]"
        else:
            status_text = f"[yellow]◐ {installed_count}/{total_count}[/yellow]"

        status_display = f"{arrow}{indent}{status_text}"
        content_text = f"{suite_name}"
        if item.description:
            content_text += f" - {item.description}"

        return status_display, content_text

    @staticmethod
    def _render_component(item, selection_state: dict, display_items: list, current_index: int,
                         arrow: str, indent: str) -> tuple:
        """Render a component item."""
        # Determine tree prefix
        tree_prefix = "├─ "
        suite_start_index = -1
        for j in range(current_index - 1, -1, -1):
            if display_items[j][0] == "suite_or_app":
                suite_start_index = j
                break

        if suite_start_index >= 0:
            suite_components = []
            for k in range(suite_start_index + 1, len(display_items)):
                if display_items[k][0] == "component":
                    suite_components.append(k)
                elif display_items[k][0] == "suite_or_app":
                    break

            if suite_components and current_index == suite_components[-1]:
                tree_prefix = "└─ "

        is_selected = selection_state.get(item.name, False)
        if item.installed and not is_selected:
            status_text = "[red]- To Uninstall[/red]"
        elif item.installed and is_selected:
            status_text = "[green]✓ Installed[/green]"
        elif not item.installed and is_selected:
            status_text = "[yellow]+ To Install[/yellow]"
        else:
            status_text = "[bright_black]○ Available[/bright_black]"

        status_display = f"{arrow}{indent}{status_text}"
        content_text = f"{tree_prefix}{item.name}"
        if item.description:
            content_text += f" - {item.description}"

        return status_display, content_text

    @staticmethod
    def _render_standalone(item, selection_state: dict, arrow: str, indent: str) -> tuple:
        """Render a standalone application."""
        is_selected = selection_state.get(item.name, False)
        if item.installed and not is_selected:
            status_text = "[red]- To Uninstall[/red]"
        elif item.installed and is_selected:
            status_text = "[green]✓ Installed[/green]"
        elif not item.installed and is_selected:
            status_text = "[yellow]+ To Install[/yellow]"
        else:
            status_text = "[bright_black]○ Available[/bright_black]"

        status_display = f"{arrow}{indent}{status_text}"
        content_text = item.name
        if item.description:
            content_text += f" - {item.description}"

        return status_display, content_text
