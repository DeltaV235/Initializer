"""Zsh Installation Confirmation Modal."""

from typing import Optional

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.events import Key
from textual.screen import ModalScreen
from textual.widgets import Label, Rule, Static

from ...modules.zsh_manager import OhMyZshInfo, OhMyTmuxInfo, TmuxInfo, ZshInfo
from ...utils.logger import get_ui_logger

logger = get_ui_logger("zsh_install_confirm")


class ZshInstallConfirm(ModalScreen[bool]):
    """Confirmation modal for Zsh install/uninstall operations."""

    BINDINGS = [
        ("y", "confirm", "Yes"),
        ("n", "cancel", "No"),
        ("enter", "confirm", "Confirm"),
        ("escape", "cancel", "Cancel"),
    ]

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

    def __init__(
        self,
        target: str,  # "zsh", "ohmyzsh", "tmux", "ohmytmux", "plugin"
        operation: str,  # "install", "uninstall"
        package_manager: str,
        zsh_info: Optional[ZshInfo] = None,
        ohmyzsh_info: Optional[OhMyZshInfo] = None,
        tmux_info: Optional[TmuxInfo] = None,
        ohmytmux_info: Optional[OhMyTmuxInfo] = None,
        plugin: Optional[dict] = None,
    ):
        super().__init__()
        self.target = target
        self.operation = operation
        self.package_manager = package_manager
        self.zsh_info = zsh_info
        self.ohmyzsh_info = ohmyzsh_info
        self.tmux_info = tmux_info
        self.ohmytmux_info = ohmytmux_info
        self.plugin = plugin

    def compose(self) -> ComposeResult:
        """Compose the confirmation modal."""
        with Container(classes="modal-container-md"):
            title_map = {
                ("zsh", "install"): "⚠️ Confirm Zsh Installation",
                ("zsh", "uninstall"): "⚠️ Confirm Zsh Removal",
                ("ohmyzsh", "install"): "⚠️ Confirm Oh-my-zsh Installation",
                ("ohmyzsh", "uninstall"): "⚠️ Confirm Oh-my-zsh Removal",
                ("tmux", "install"): "⚠️ Confirm Tmux Installation",
                ("tmux", "uninstall"): "⚠️ Confirm Tmux Removal",
                ("ohmytmux", "install"): "⚠️ Confirm oh-my-tmux Installation",
                ("ohmytmux", "uninstall"): "⚠️ Confirm oh-my-tmux Removal",
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

                elif self.target == "tmux":
                    if self.operation == "install":
                        yield Static("This will install:", classes="info-text")
                        yield Static(
                            f"  • Tmux (via {self.package_manager})\n"
                            "  • Version from system repository",
                            classes="action-list",
                        )
                        # Display specific command
                        if self.package_manager in ["apt", "apt-get"]:
                            cmd = "sudo apt install -y tmux"
                        elif self.package_manager == "dnf":
                            cmd = "sudo dnf install -y tmux"
                        elif self.package_manager == "yum":
                            cmd = "sudo yum install -y tmux"
                        elif self.package_manager == "pacman":
                            cmd = "sudo pacman -S --noconfirm tmux"
                        elif self.package_manager == "zypper":
                            cmd = "sudo zypper install -y tmux"
                        elif self.package_manager == "brew":
                            cmd = "brew install tmux"
                        else:
                            cmd = f"Install tmux using your system's package manager ({self.package_manager})"
                        yield Static(
                            f"Command: {cmd}",
                            classes="action-list",
                        )
                        yield Static(
                            "⚠️  Note: Tmux is a terminal multiplexer that lets you switch easily between several programs in one terminal.",
                            classes="note-text",
                        )
                    else:  # uninstall
                        yield Static("This will remove:", classes="info-text")
                        yield Static(
                            f"  • Tmux package via {self.package_manager}\n"
                            "  • Related binaries installed by the package manager",
                            classes="action-list",
                        )
                        # Display specific command
                        if self.package_manager in ["apt", "apt-get"]:
                            cmd = "sudo apt remove -y tmux"
                        elif self.package_manager == "dnf":
                            cmd = "sudo dnf remove -y tmux"
                        elif self.package_manager == "yum":
                            cmd = "sudo yum remove -y tmux"
                        elif self.package_manager == "pacman":
                            cmd = "sudo pacman -R --noconfirm tmux"
                        elif self.package_manager == "zypper":
                            cmd = "sudo zypper remove -y tmux"
                        elif self.package_manager == "brew":
                            cmd = "brew uninstall tmux"
                        else:
                            cmd = f"Uninstall tmux using your system's package manager ({self.package_manager})"
                        yield Static(
                            f"Command: {cmd}",
                            classes="action-list",
                        )
                        yield Static(
                            "⚠️  User configuration in ~/.tmux.conf will not be touched.",
                            classes="note-text",
                        )

                elif self.target == "ohmytmux":
                    if self.operation == "install":
                        yield Static("This will install:", classes="info-text")
                        yield Static(
                            "  • oh-my-tmux configuration framework\n"
                            "  • Starter template from GitHub",
                            classes="action-list",
                        )
                        # Display specific command
                        yield Static(
                            "Command: git clone https://github.com/gpakosz/.tmux.git ~/.tmux",
                            classes="action-list",
                        )
                        yield Static(
                            "⚠️  Existing .tmux directory and .tmux.conf will be backed up with a timestamp.",
                            classes="note-text",
                        )
                    else:  # uninstall
                        yield Static("This will remove:", classes="info-text")
                        yield Static(
                            "  • oh-my-tmux configuration directory (~/.tmux)\n"
                            "  • Symbolic link (~/.tmux.conf)\n"
                            "  • Local configuration (~/.tmux.conf.local)",
                            classes="action-list",
                        )
                        # Display specific command
                        yield Static(
                            "Command: rm -rf ~/.tmux ~/.tmux.conf ~/.tmux.conf.local",
                            classes="action-list",
                        )
                        yield Static(
                            "⚠️  All oh-my-tmux files will be permanently removed.",
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

            with Container(id="help-box"):
                yield Label("Y/Enter=Confirm | N/ESC=Cancel", classes="help-text")

    def on_mount(self) -> None:
        """Handle mount event and set focus."""
        try:
            self.focus()
            logger.debug("Zsh install confirm modal mounted and focused")
        except Exception as e:
            logger.debug(f"Failed to initialize modal: {e}")

    def action_confirm(self) -> None:
        """Confirm action."""
        logger.info(f"User confirmed {self.target} {self.operation}")
        self.dismiss(True)

    def action_cancel(self) -> None:
        """Cancel action."""
        logger.info(f"User cancelled {self.target} {self.operation}")
        self.dismiss(False)

    @on(Key)
    def handle_key_event(self, event: Key) -> None:
        """Handle keyboard shortcuts."""
        if event.key in ("y", "enter"):
            self.action_confirm()
            event.prevent_default()
            event.stop()
        elif event.key in ("n", "escape"):
            self.action_cancel()
            event.prevent_default()
            event.stop()
