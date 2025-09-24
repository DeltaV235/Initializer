"""Application Manager Selection Modal."""

from textual import on, work
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.screen import ModalScreen
from textual.widgets import Button, Static, Rule, Label
from textual.events import Key
from typing import Callable, Optional, List, Dict
from textual.reactive import reactive

from ...modules.app_installer import AppInstaller


class AppManagerModal(ModalScreen):
    """Modal screen for selecting applications to install/uninstall."""

    BINDINGS = [
        ("escape", "dismiss", "Cancel"),
        ("a", "apply_changes", "Apply Changes"),
    ]

    # CSS styles for the modal
    CSS = """
    AppManagerModal {
        align: center middle;
    }

    #modal-container {
        width: 85%;
        height: 85%;
        max-height: 35;
        background: $surface;
        border: round #7dd3fc;
        padding: 1;
        layout: vertical;
    }

    #modal-content {
        height: 1fr;
        overflow-y: auto;
        padding: 0 1;
    }

    #app-list {
        height: auto;
        min-height: 1;
        margin: 0 0 1 0;
    }

    .app-item {
        height: auto;
        min-height: 2;
        padding: 0 0;
        layout: horizontal;
        align: left middle;
    }

    .app-item-selected {
        background: $primary;
    }

    .app-content {
        width: auto;
        height: 1;
        padding: 0;
        margin: 0;
    }

    .app-status {
        color: $text-muted;
        text-style: dim;
    }

    .help-text {
        text-align: center;
        color: $text-muted;
        height: 1;
        min-height: 1;
        max-height: 1;
        margin: 0 0 0 0;
        padding: 0 0 0 0;
        background: $surface;
        text-style: none;
    }

    .bottom-spacer {
        height: 1;
        background: transparent;
    }

    .changes-summary {
        background: $surface;
        border: round $primary;
        padding: 1;
        margin: 1 0;
    }

    .change-item {
        color: $text;
        height: 1;
    }
    """

    # Reactive properties
    selected_index = reactive(0)

    def __init__(self, callback: Callable[[List[Dict]], None], app_installer: AppInstaller):
        super().__init__()
        self.callback = callback
        self.app_installer = app_installer
        self.applications = self.app_installer.get_all_applications()

        # Track selection state for each application
        # Initialize: installed apps are checked, uninstalled are unchecked
        self.selection_state = {
            app.name: app.installed for app in self.applications
        }

        self.selected_index = 0

    def on_mount(self) -> None:
        """Initialize the screen."""
        self._update_display()
        self.focus()

    def can_focus(self) -> bool:
        """Return True to allow this modal to receive focus."""
        return True

    @property
    def is_modal(self) -> bool:
        """Mark this as a modal screen."""
        return True

    @on(Key)
    def handle_key_event(self, event: Key) -> None:
        """Handle key events using @on decorator."""
        if event.key == "enter" or event.key == "space":
            self.action_toggle_current()
            event.prevent_default()
            event.stop()
        elif event.key == "j" or event.key == "down":
            self.action_nav_down()
            event.prevent_default()
            event.stop()
        elif event.key == "k" or event.key == "up":
            self.action_nav_up()
            event.prevent_default()
            event.stop()
        elif event.key == "a":
            self.action_apply_changes()
            event.prevent_default()
            event.stop()
        elif event.key == "escape":
            self.dismiss()
            event.prevent_default()
            event.stop()

    def compose(self) -> ComposeResult:
        """Compose the modal interface."""
        with Container(id="modal-container"):
            yield Static("Application Manager", id="modal-title")
            yield Rule()

            with ScrollableContainer(id="modal-content"):
                yield Label("Select Applications to Install/Uninstall:", classes="section-header")
                with Vertical(id="app-list"):
                    for i, app in enumerate(self.applications):
                        with Horizontal(id=f"app-item-{i}", classes="app-item"):
                            # Create full content with arrow, checkbox symbol and text
                            arrow = "▶ " if i == self.selected_index else "  "
                            checkbox_symbol = "■" if self.selection_state.get(app.name, False) else "□"

                            # Application info - name and description on same line
                            app_text = f"{arrow}{checkbox_symbol} {app.name}"
                            if app.description:
                                app_text += f" - {app.description}"

                            # Status indicator
                            if app.installed:
                                app_text += " (Installed)"
                            else:
                                app_text += " (Available)"

                            yield Static(app_text, classes="app-content", id=f"app-content-{i}")

                    yield Static("", classes="bottom-spacer")

                # Changes summary section
                yield Rule()
                yield Label("Changes to Apply:", classes="section-header")
                with Container(id="changes-container", classes="changes-summary"):
                    self._build_changes_summary()

            # Bottom shortcuts area
            yield Rule()
            yield Label("J/K=Up/Down | SPACE/Enter=Toggle | A=Apply Changes | Esc=Cancel", classes="help-text")

    def _build_changes_summary(self) -> None:
        """Build the changes summary section."""
        changes = self._calculate_changes()

        if changes["install"]:
            install_text = "Install: " + ", ".join(changes["install"])
            yield Static(f"• {install_text}", classes="change-item")

        if changes["uninstall"]:
            uninstall_text = "Uninstall: " + ", ".join(changes["uninstall"])
            yield Static(f"• {uninstall_text}", classes="change-item")

        if not changes["install"] and not changes["uninstall"]:
            yield Static("• No changes to apply", classes="change-item")

    def _calculate_changes(self) -> Dict:
        """Calculate what changes need to be applied."""
        changes = {"install": [], "uninstall": []}

        for app in self.applications:
            is_selected = self.selection_state.get(app.name, False)

            if app.installed and not is_selected:
                # Installed but unchecked - uninstall
                changes["uninstall"].append(app.name)
            elif not app.installed and is_selected:
                # Not installed but checked - install
                changes["install"].append(app.name)

        return changes

    def _update_display(self) -> None:
        """Update the application list display."""
        try:
            # Update each item's complete content
            for i, app in enumerate(self.applications):
                # Create full content with arrow, checkbox symbol and text
                arrow = "▶ " if i == self.selected_index else "  "
                checkbox_symbol = "■" if self.selection_state.get(app.name, False) else "□"

                # Application info - name and description on same line
                app_text = f"{arrow}{checkbox_symbol} {app.name}"
                if app.description:
                    app_text += f" - {app.description}"

                # Status indicator
                if app.installed:
                    app_text += " (Installed)"
                else:
                    app_text += " (Available)"

                try:
                    content_item = self.query_one(f"#app-content-{i}", Static)
                    content_item.update(app_text)
                except:
                    pass

            # Update changes summary
            self._update_changes_summary()

        except Exception as e:
            # Fallback if update fails
            pass

    def _update_changes_summary(self) -> None:
        """Update the changes summary section."""
        try:
            changes_container = self.query_one("#changes-container", Container)

            # Clear existing content
            children = list(changes_container.children)
            for child in children:
                try:
                    child.remove()
                except Exception:
                    pass

            # Add updated changes
            changes = self._calculate_changes()

            if changes["install"]:
                install_text = "Install: " + ", ".join(changes["install"])
                changes_container.mount(Static(f"• {install_text}", classes="change-item"))

            if changes["uninstall"]:
                uninstall_text = "Uninstall: " + ", ".join(changes["uninstall"])
                changes_container.mount(Static(f"• {uninstall_text}", classes="change-item"))

            if not changes["install"] and not changes["uninstall"]:
                changes_container.mount(Static("• No changes to apply", classes="change-item"))

        except Exception:
            pass

    def action_nav_down(self) -> None:
        """Navigate down in the list."""
        if self.selected_index < len(self.applications) - 1:
            self.selected_index += 1
            self._update_display()
            self._scroll_to_current()

    def action_nav_up(self) -> None:
        """Navigate up in the list."""
        if self.selected_index > 0:
            self.selected_index -= 1
            self._update_display()
            self._scroll_to_current()

    def action_toggle_current(self) -> None:
        """Toggle the current application selection."""
        if 0 <= self.selected_index < len(self.applications):
            app = self.applications[self.selected_index]
            # Toggle the selection state
            new_value = not self.selection_state.get(app.name, False)
            self.selection_state[app.name] = new_value

            # Update the display to reflect the change
            self._update_display()

    def action_apply_changes(self) -> None:
        """Process the selected applications for installation/uninstallation."""
        # Determine what actions to take
        actions = []

        for app in self.applications:
            is_selected = self.selection_state.get(app.name, False)

            if app.installed and not is_selected:
                # Installed but unchecked - uninstall
                actions.append({
                    "action": "uninstall",
                    "application": app,
                })
            elif not app.installed and is_selected:
                # Not installed but checked - install
                actions.append({
                    "action": "install",
                    "application": app,
                })

        if actions:
            # Pass actions to callback
            self.callback(actions)
            self.dismiss()
        else:
            # No changes to make
            self.dismiss()

    def _scroll_to_current(self) -> None:
        """Scroll to ensure current selection is visible."""
        try:
            scrollable_container = self.query_one("#modal-content", ScrollableContainer)
            current_item = self.query_one(f"#app-item-{self.selected_index}", Horizontal)

            if hasattr(scrollable_container, 'scroll_to_widget'):
                scrollable_container.scroll_to_widget(current_item, animate=True, speed=60, center=True)
            else:
                # Manual scrolling fallback
                header_height = 2
                visible_height = 20
                current_position = header_height + self.selected_index * 2
                current_scroll = scrollable_container.scroll_y

                if current_position < current_scroll:
                    scrollable_container.scroll_y = current_position
                elif current_position > current_scroll + visible_height:
                    scrollable_container.scroll_y = current_position - visible_height + 2

        except Exception:
            pass

    def action_dismiss(self) -> None:
        """Dismiss the modal."""
        self.dismiss()