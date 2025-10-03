"""Vim Installation Confirmation Modal."""

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Static, Rule, Label
from typing import Optional

from ...modules.vim_manager import VimManager, NeoVimInfo, LazyVimInfo
from ...utils.logger import get_ui_logger

logger = get_ui_logger("vim_install_confirm")


class VimInstallConfirm(ModalScreen[bool]):
    """Confirmation modal for Vim install/uninstall operations."""

    CSS = """
    VimInstallConfirm {
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
        target: str,  # "neovim" or "lazyvim"
        operation: str,  # "install" or "uninstall"
        package_manager: str,
        nvim_info: Optional[NeoVimInfo] = None,
        lazyvim_info: Optional[LazyVimInfo] = None
    ):
        super().__init__()
        self.target = target
        self.operation = operation
        self.package_manager = package_manager
        self.nvim_info = nvim_info
        self.lazyvim_info = lazyvim_info

    def compose(self) -> ComposeResult:
        """Compose the confirmation modal."""
        with Container(classes="modal-container-md"):
            title_map = {
                ("neovim", "install"): "⚠️ Confirm NeoVim Installation",
                ("neovim", "uninstall"): "⚠️ Confirm NeoVim Removal",
                ("lazyvim", "install"): "⚠️ Confirm LazyVim Installation",
                ("lazyvim", "uninstall"): "⚠️ Confirm LazyVim Removal",
            }
            yield Static(
                title_map.get((self.target, self.operation), "⚠️ Confirm Operation"),
                id="confirm-title",
            )

            yield Rule()

            with Vertical(classes="confirm-content"):
                if self.target == "neovim":
                    if self.operation == "install":
                        yield Static("This will install:", classes="info-text")
                        yield Static(
                            f"  • NeoVim (via {self.package_manager})\n"
                            "  • Version from system repository",
                            classes="action-list",
                        )
                        yield Static(
                            f"⚠️  Note: Repository version must be >= {VimManager.MIN_NVIM_VERSION}.\n"
                            "    If installation succeeds but version is incompatible,\n"
                            "    manual upgrade will be required.",
                            classes="note-text",
                        )
                    else:  # uninstall
                        yield Static("This will remove:", classes="info-text")
                        yield Static(
                            f"  • NeoVim package via {self.package_manager}\n"
                            "  • Related binaries installed by the package manager",
                            classes="action-list",
                        )
                        yield Static(
                            "⚠️  User configuration in ~/.config/nvim will not be touched.",
                            classes="note-text",
                        )
                else:  # LazyVim
                    if self.operation == "install":
                        yield Static("This will install:", classes="info-text")
                        yield Static(
                            "  • LazyVim configuration framework\n"
                            "  • Starter template from GitHub",
                            classes="action-list",
                        )
                        if self.lazyvim_info and self.lazyvim_info.config_path:
                            from datetime import datetime

                            timestamp = int(datetime.now().timestamp())
                            yield Static(
                                "⚠️  Existing configuration will be backed up:\n"
                                f"    From: {self.lazyvim_info.config_path}\n"
                                f"    To: {self.lazyvim_info.config_path}.backup.{timestamp}",
                                classes="note-text",
                            )
                        yield Static(
                            "📝 After installation:\n"
                            "  • Run 'nvim' to complete plugin installation\n"
                            "  • First launch will download plugins (~5-10 minutes)",
                            classes="info-text",
                        )
                    else:
                        yield Static("This will remove:", classes="info-text")
                        yield Static(
                            "  • LazyVim configuration directory (~/.config/nvim)",
                            classes="action-list",
                        )
                        yield Static(
                            "⚠️  The directory will be renamed with a .removed timestamp for rollback.",
                            classes="note-text",
                        )

            yield Rule()

            with Horizontal(id="button-container"):
                yield Button("✓ Confirm", id="confirm", variant="primary", classes="confirm-button")
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

    def on_key(self, event) -> None:
        """Handle key events."""
        if event.key == "escape":
            logger.debug("User pressed ESC to cancel")
            self.dismiss(False)
        elif event.key == "enter":
            logger.debug("User pressed Enter to confirm")
            self.dismiss(True)
