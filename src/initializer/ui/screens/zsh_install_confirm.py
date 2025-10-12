"""Zsh Installation Confirmation Modal."""

from typing import Optional

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Rule, Static

from ...modules.zsh_manager import OhMyZshInfo, ZshInfo
from ...utils.logger import get_ui_logger

logger = get_ui_logger("zsh_install_confirm")


class ZshInstallConfirm(ModalScreen[bool]):
    """Confirmation modal for Zsh install/uninstall operations."""

    CSS = """
    ZshInstallConfirm {
        align: center middle;
    }

    #confirm-title {
        text-style: bold;
        color: $text;
        margin: 0 0 1 0;
        text-align: center;
    }

    .confirm-content {
        padding: 1;
        margin: 0 0 1 0;
    }

    .info-text {
        color: $text;
        margin: 0 0 1 0;
    }

    .warning-text {
        color: $warning;
        text-style: bold;
        margin: 0 0 1 0;
    }

    .action-list {
        color: $primary;
        margin: 0 0 1 0;
    }

    .note-text {
        color: $text-muted;
        margin: 1 0;
        padding: 1;
        border: solid $warning;
    }

    #button-container {
        height: auto;
        align: center middle;
        margin: 1 0 0 0;
    }

    .confirm-button {
        margin: 0 1;
    }

    .help-text {
        text-align: center;
        color: $text-muted;
        margin: 1 0 0 0;
    }
    """

    def __init__(
        self,
        target: str,  # "zsh", "ohmyzsh", "plugin"
        operation: str,  # "install", "uninstall"
        package_manager: str,
        zsh_info: Optional[ZshInfo] = None,
        ohmyzsh_info: Optional[OhMyZshInfo] = None,
        plugin: Optional[dict] = None,
    ):
        super().__init__()
        self.target = target
        self.operation = operation
        self.package_manager = package_manager
        self.zsh_info = zsh_info
        self.ohmyzsh_info = ohmyzsh_info
        self.plugin = plugin

    def compose(self) -> ComposeResult:
        """Compose the confirmation modal."""
        with Container(classes="modal-container-md"):
            title_map = {
                ("zsh", "install"): "⚠️ Confirm Zsh Installation",
                ("zsh", "uninstall"): "⚠️ Confirm Zsh Removal",
                ("ohmyzsh", "install"): "⚠️ Confirm Oh-my-zsh Installation",
                ("ohmyzsh", "uninstall"): "⚠️ Confirm Oh-my-zsh Removal",
                ("plugin", "install"): "⚠️ Confirm Plugin Installation",
                ("plugin", "uninstall"): "⚠️ Confirm Plugin Removal",
            }
            yield Static(
                title_map.get((self.target, self.operation), "⚠️ Confirm Operation"),
                id="confirm-title",
            )

            yield Rule()

            with Vertical(classes="confirm-content"):
                if self.target == "zsh":
                    if self.operation == "install":
                        yield Static("This will install:", classes="info-text")
                        yield Static(
                            f"  • Zsh (via {self.package_manager})\n"
                            "  • Version from system repository",
                            classes="action-list",
                        )
                        yield Static(
                            "⚠️  Note: After installation, you can set Zsh as your default shell.",
                            classes="note-text",
                        )
                    else:  # uninstall
                        yield Static("This will remove:", classes="info-text")
                        yield Static(
                            f"  • Zsh package via {self.package_manager}\n"
                            "  • Related binaries installed by the package manager",
                            classes="action-list",
                        )
                        yield Static(
                            "⚠️  User configuration in ~/.zshrc will not be touched.",
                            classes="note-text",
                        )

                elif self.target == "ohmyzsh":
                    if self.operation == "install":
                        yield Static("This will install:", classes="info-text")
                        yield Static(
                            "  • Oh-my-zsh configuration framework\n"
                            "  • Starter template from GitHub",
                            classes="action-list",
                        )
                        if self.ohmyzsh_info and self.ohmyzsh_info.config_path:
                            from datetime import datetime

                            timestamp = int(datetime.now().timestamp())
                            yield Static(
                                "⚠️  Existing configuration will be backed up:\n"
                                f"    From: {self.ohmyzsh_info.config_path}\n"
                                f"    To: {self.ohmyzsh_info.config_path}.backup.{timestamp}",
                                classes="note-text",
                            )
                        yield Static(
                            "📝 After installation:\n"
                            "  • Run 'zsh' to start using Oh-my-zsh\n"
                            "  • First launch will apply configuration",
                            classes="info-text",
                        )
                    else:  # uninstall
                        yield Static("This will remove:", classes="info-text")
                        yield Static(
                            "  • Oh-my-zsh configuration directory (~/.oh-my-zsh)",
                            classes="action-list",
                        )
                        yield Static(
                            "⚠️  The directory will be renamed with a .removed timestamp for rollback.",
                            classes="note-text",
                        )

                elif self.target == "plugin":
                    plugin_name = self.plugin.get("name", "Unknown") if self.plugin else "Unknown"
                    plugin_desc = self.plugin.get("description", "") if self.plugin else ""

                    if self.operation == "install":
                        yield Static("This will install:", classes="info-text")
                        yield Static(
                            f"  • Plugin: {plugin_name}\n"
                            f"  • Description: {plugin_desc}",
                            classes="action-list",
                        )
                        install_method = self.plugin.get("install_method", "git") if self.plugin else "git"
                        if install_method == "package_manager":
                            yield Static(
                                "⚠️  This plugin will be installed via system package manager.",
                                classes="note-text",
                            )
                        else:
                            yield Static(
                                "⚠️  Plugin will be cloned to ~/.oh-my-zsh/custom/plugins/",
                                classes="note-text",
                            )
                    else:  # uninstall
                        yield Static("This will remove:", classes="info-text")
                        yield Static(
                            f"  • Plugin: {plugin_name}",
                            classes="action-list",
                        )
                        yield Static(
                            "⚠️  Plugin directory will be permanently deleted.",
                            classes="note-text",
                        )

            yield Rule()

            with Horizontal(id="button-container"):
                yield Button(
                    "✓ Confirm", id="confirm", variant="primary", classes="confirm-button"
                )
                yield Button("✗ Cancel", id="cancel", classes="confirm-button")

            yield Static("Enter=Confirm | ESC=Cancel", classes="help-text")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "confirm":
            logger.info(f"User confirmed {self.target} {self.operation}")
            self.dismiss(True)
        elif event.button.id == "cancel":
            logger.info(f"User cancelled {self.target} {self.operation}")
            self.dismiss(False)

    def on_key(self, event) -> None:  # type: ignore[override]
        """Handle key events."""
        if event.key == "escape":
            logger.debug("User pressed ESC to cancel")
            self.dismiss(False)
        elif event.key == "enter":
            logger.debug("User pressed Enter to confirm")
            self.dismiss(True)
