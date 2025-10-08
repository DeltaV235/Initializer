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

        # Build display list - always include all components (even if collapsed)
        # We'll control visibility via CSS instead of DOM insertion/removal
        display_items = []
        for item in software_items:
            display_items.append(("suite_or_app", item, 0))

            # Always add components, we'll hide them with CSS if collapsed
            if isinstance(item, ApplicationSuite):
                for component in item.components:
                    is_expanded = item.name in screen.app_expanded_suites
                    display_items.append(("component", component, 1, item.name, is_expanded))

        # Display each item
        for i, item_data in enumerate(display_items):
            # Unpack based on item type
            if len(item_data) == 3:
                item_type, item, indent_level = item_data
                suite_name = None
                is_visible = True
            else:  # len == 5, it's a component
                item_type, item, indent_level, suite_name, is_visible = item_data

            is_right_focused = (screen.current_panel_focus == "right")
            arrow = "[#7dd3fc]\u25b6[/#7dd3fc] " if (i == screen.app_focused_index and is_right_focused) else "  "
            indent = "  " * indent_level

            if item_type == "suite_or_app" and isinstance(item, ApplicationSuite):
                status_display, content_text = AppInstallRenderer._render_suite(
                    item,
                    screen.app_selection_state,
                    screen.app_expanded_suites,
                    arrow,
                    indent,
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

            # Add suite name as data attribute for components
            if suite_name:
                app_container.add_class(f"suite-{suite_name.replace(' ', '-')}")
                if not is_visible:
                    app_container.styles.display = "none"

            status_widget = Static(status_display, classes="app-item-status")
            content_widget = Static(content_text, classes="app-item-content")

            # Store the text without arrow for later updates
            # status_display format: "{arrow}{indent}{status_text}"
            # Extract text after arrow (first 2 or ~20 chars)
            if status_display.startswith("[#7dd3fc]\u25b6[/#7dd3fc] "):
                text_without_arrow = status_display[len("[#7dd3fc]\u25b6[/#7dd3fc] "):]
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
    def _render_suite(
        item: ApplicationSuite,
        selection_state: dict,
        expanded_suites: set,
        arrow: str,
        indent: str,
    ) -> tuple:
        """Render a suite item, reflecting pending install/uninstall actions."""
        expansion_icon = "\u25bc" if item.name in expanded_suites else "\u25b6"
        suite_name = f"{expansion_icon} {item.name}"

        components = list(getattr(item, "components", []) or [])
        selection_state = selection_state or {}

        total_count = len(components)
        installed_count = 0
        install_targets = 0
        uninstall_targets = 0

        for component in components:
            if getattr(component, "installed", False):
                installed_count += 1
            selected = selection_state.get(component.name, component.installed)
            if component.installed and not selected:
                uninstall_targets += 1
            elif not component.installed and selected:
                install_targets += 1

        if install_targets > 0 and uninstall_targets == 0:
            status_text = "[yellow]+ Install All[/yellow]"
        elif uninstall_targets > 0 and install_targets == 0:
            status_text = "[red]- Uninstall All[/red]"
        elif install_targets > 0 and uninstall_targets > 0:
            status_text = "[magenta]* Mixed Suite Changes[/magenta]"
        else:
            if total_count == 0:
                status_text = "[bright_black]\u25cb 0/0[/bright_black]"
            elif installed_count == total_count:
                status_text = f"[green]\u25cf {total_count}/{total_count}[/green]"
            elif installed_count == 0:
                status_text = f"[bright_black]\u25cb {installed_count}/{total_count}[/bright_black]"
            else:
                status_text = f"[yellow]\u25d0 {installed_count}/{total_count}[/yellow]"

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
