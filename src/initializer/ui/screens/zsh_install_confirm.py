"""Zsh Installation Confirmation Modal."""

from typing import Optional

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Label, Rule, Static

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
        padding: 0 1;
    }

    .note-text {
        color: $text-muted;
        margin: 1 0;
        padding: 1;
        border: solid $warning;
    }

    #option-container {
        height: auto;
        align: center middle;
        margin: 1 0 0 0;
        padding: 1 0;
    }

    .option-item {
        text-align: center;
        color: $text;
        margin: 0 0 1 0;
    }

    #help-box {
        dock: bottom;
        width: 100%;
        height: 3;
        border: round white;
        background: $surface;
        padding: 0 1;
        margin: 0;
    }

    .help-text {
        width: 100%;
        height: 1;
        content-align: center middle;
        text-align: center;
        color: $text-muted;
    }
    """

    selected_option: reactive[int] = reactive(0)  # 0=Confirm, 1=Cancel

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
                        # Display specific command
                        if self.package_manager in ["apt", "apt-get"]:
                            cmd = "sudo apt install -y zsh"
                        elif self.package_manager == "dnf":
                            cmd = "sudo dnf install -y zsh"
                        elif self.package_manager == "yum":
                            cmd = "sudo yum install -y zsh"
                        elif self.package_manager == "pacman":
                            cmd = "sudo pacman -S --noconfirm zsh"
                        elif self.package_manager == "zypper":
                            cmd = "sudo zypper install -y zsh"
                        elif self.package_manager == "brew":
                            cmd = "brew install zsh"  # Homebrew does not need sudo
                        else:
                            # Unknown package manager - show generic message
                            cmd = f"Install zsh using your system's package manager ({self.package_manager})"
                        yield Static(
                            f"Command: {cmd}",
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
                        # Display specific command
                        if self.package_manager in ["apt", "apt-get"]:
                            cmd = "sudo apt remove -y zsh"
                        elif self.package_manager == "dnf":
                            cmd = "sudo dnf remove -y zsh"
                        elif self.package_manager == "yum":
                            cmd = "sudo yum remove -y zsh"
                        elif self.package_manager == "pacman":
                            cmd = "sudo pacman -R --noconfirm zsh"
                        elif self.package_manager == "zypper":
                            cmd = "sudo zypper remove -y zsh"
                        elif self.package_manager == "brew":
                            cmd = "brew uninstall zsh"  # Homebrew does not need sudo
                        else:
                            # Unknown package manager - show generic message
                            cmd = f"Uninstall zsh using your system's package manager ({self.package_manager})"
                        yield Static(
                            f"Command: {cmd}",
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
                        # Display specific command
                        yield Static(
                            "Command: sh -c \"$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)\"",
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
                        # Display specific command
                        yield Static(
                            "Command: mv ~/.oh-my-zsh ~/.oh-my-zsh.removed.<timestamp>",
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
                            # Display package manager install command
                            pkg_name = self.plugin.get("package_name", plugin_name) if self.plugin else plugin_name
                            if self.package_manager in ["apt", "apt-get"]:
                                cmd = f"sudo apt install -y {pkg_name}"
                            elif self.package_manager == "dnf":
                                cmd = f"sudo dnf install -y {pkg_name}"
                            elif self.package_manager == "yum":
                                cmd = f"sudo yum install -y {pkg_name}"
                            elif self.package_manager == "pacman":
                                cmd = f"sudo pacman -S --noconfirm {pkg_name}"
                            elif self.package_manager == "zypper":
                                cmd = f"sudo zypper install -y {pkg_name}"
                            elif self.package_manager == "brew":
                                cmd = f"brew install {pkg_name}"  # Homebrew does not need sudo
                            else:
                                # Unknown package manager - show generic message
                                cmd = f"Install {pkg_name} using your system's package manager"
                            yield Static(
                                f"Command: {cmd}",
                                classes="action-list",
                            )
                            yield Static(
                                "⚠️  This plugin will be installed via system package manager.",
                                classes="note-text",
                            )
                        else:
                            # Display git clone command
                            repo_url = self.plugin.get("repo_url", "") if self.plugin else ""
                            if repo_url:
                                yield Static(
                                    f"Command: git clone {repo_url} ~/.oh-my-zsh/custom/plugins/{plugin_name}",
                                    classes="action-list",
                                )
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
                        # Display rm command
                        yield Static(
                            f"Command: rm -rf ~/.oh-my-zsh/custom/plugins/{plugin_name}",
                            classes="action-list",
                        )
                        yield Static(
                            "⚠️  Plugin directory will be permanently deleted.",
                            classes="note-text",
                        )

            yield Rule()

            with Vertical(id="option-container"):
                yield Static("", id="confirm-option", classes="option-item")
                yield Static("", id="cancel-option", classes="option-item")

            with Container(id="help-box"):
                yield Label("J/K=Navigate | Enter=Select | ESC=Cancel", classes="help-text")

    def on_mount(self) -> None:
        """Handle mount event to set initial selection."""
        try:
            self.selected_option = 0
            self.call_after_refresh(self._update_option_display)
            logger.debug("Zsh install confirm modal mounted")
        except Exception as e:
            logger.debug(f"Failed to initialize modal: {e}")

    def watch_selected_option(self, old_value: int, new_value: int) -> None:
        """Watch for changes to selected_option and update display."""
        self._update_option_display()

    def _update_option_display(self) -> None:
        """Update option display with arrow indicators."""
        try:
            confirm_option = self.query_one("#confirm-option", Static)
            cancel_option = self.query_one("#cancel-option", Static)

            confirm_arrow = "▶ " if self.selected_option == 0 else "  "
            cancel_arrow = "▶ " if self.selected_option == 1 else "  "

            confirm_option.update(f"{confirm_arrow}✓ Confirm")
            cancel_option.update(f"{cancel_arrow}✗ Cancel")
        except Exception as e:
            logger.debug(f"Failed to update option display: {e}")

    def on_key(self, event) -> None:  # type: ignore[override]
        """Handle key events."""
        if event.key == "escape":
            logger.debug("User pressed ESC to cancel")
            self.dismiss(False)
        elif event.key == "enter":
            logger.debug("User pressed Enter to select")
            result = (self.selected_option == 0)
            action = "confirmed" if result else "cancelled"
            logger.info(f"User {action} {self.target} {self.operation}")
            self.dismiss(result)
        elif event.key == "j":
            self.selected_option = (self.selected_option + 1) % 2
            event.prevent_default()
            event.stop()
        elif event.key == "k":
            self.selected_option = (self.selected_option - 1) % 2
            event.prevent_default()
            event.stop()
