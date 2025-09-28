"""Main application class for the Linux System Initializer."""

import sys
import subprocess
from typing import Optional

from rich.console import Console
from textual.app import App, ComposeResult
from textual.widgets import Footer, Header
from textual.binding import Binding

from .config_manager import ConfigManager
from .utils.logger import init_logging, get_app_logger
from .modules.sudo_manager import SudoManager


def cleanup_terminal_state():
    """Comprehensive terminal state cleanup matching reset-terminal.sh."""
    try:
        # Force flush any pending output first
        sys.stdout.flush()
        sys.stderr.flush()

        # Exit alternate screen buffer (most critical for visibility)
        sys.stdout.write('\033[?1049l')

        # Disable all mouse tracking modes
        sys.stdout.write('\033[?1000l')  # Basic mouse tracking
        sys.stdout.write('\033[?1002l')  # Cell motion tracking
        sys.stdout.write('\033[?1003l')  # All motion tracking
        sys.stdout.write('\033[?1006l')  # SGR extended mode
        sys.stdout.write('\033[?1015l')  # URXVT mode

        # Disable other features
        sys.stdout.write('\033[?1004l')  # Focus tracking
        sys.stdout.write('\033[?2004l')  # Bracketed paste mode

        # Show cursor (critical for input visibility)
        sys.stdout.write('\033[?25h')

        # Reset colors and attributes
        sys.stdout.write('\033[0m')

        # Clear any remaining escape sequences and reset terminal
        sys.stdout.write('\033c')

        # Force immediate flush
        sys.stdout.flush()

        # Additional sleep to ensure terminal processes the commands
        import time
        time.sleep(0.1)

        # Critical: Reset terminal input/output settings using stty if available
        import subprocess
        try:
            # Reset terminal to sane state - this should restore echo and proper input
            # Use /dev/tty to ensure we're operating on the actual terminal
            with open('/dev/tty', 'w') as tty:
                subprocess.run(['stty', 'sane'], check=False, timeout=1, stdin=tty, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except (FileNotFoundError, subprocess.SubprocessError, subprocess.TimeoutExpired, OSError):
            pass

        # Additional reset using tput if available
        try:
            subprocess.run(['tput', 'sgr0'], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=1)
        except (FileNotFoundError, subprocess.SubprocessError, subprocess.TimeoutExpired):
            pass

        # Final reset attempt with direct terminal command
        try:
            subprocess.run(['reset'], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2)
        except (FileNotFoundError, subprocess.SubprocessError, subprocess.TimeoutExpired):
            pass

    except Exception:
        pass


class InitializerApp(App):
    """Linux System Initializer TUI Application."""
    
    CSS_PATH = "styles.css"
    TITLE = "Linux System Initializer"
    SUB_TITLE = "Modern TUI for System Setup"
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("s", "settings", "Settings"),
        ("h", "help", "Help"),
        ("ctrl+c", "quit", "Quit"),
        Binding("f10", "reload_app", "", show=False, priority=True),    # Hidden shortcut for testing
        Binding("f12", "force_quit", "", show=False, priority=True),    # Hidden shortcut for testing
    ]
    
    def __init__(self, config_manager: ConfigManager, preset: str = None,
                 headless: bool = False, debug: bool = False):
        super().__init__()

        self.config_manager = config_manager
        self.preset = preset
        self.headless = headless
        self.debug_mode = debug
        self.console = Console()

        # Initialize logging system first
        init_logging(config_manager.config_dir, debug, self.console)
        self.logger = get_app_logger()

        # Load configuration
        self.app_config = config_manager.get_app_config()
        self.modules_config = config_manager.get_modules_config()
        self.theme_config = config_manager.get_theme_config()

        self.logger.info(f"Application initialized - version: {self.app_config.version}")
        if debug:
            self.logger.debug("Debug mode enabled")

        # Apply preset if specified
        if preset:
            self._apply_preset(preset)

        # Update title
        self.title = self.app_config.name
        self.sub_title = f"v{self.app_config.version}"

        # 初始化sudo管理器（全局实例，用于整个应用生命周期）
        self.sudo_manager: Optional[SudoManager] = None
        
    def _apply_preset(self, preset_name: str) -> None:
        """Apply a configuration preset."""
        try:
            preset_config = self.config_manager.load_preset(preset_name)
            self.logger.info(f"Preset configuration applied: {preset_name}")
        except FileNotFoundError:
            self.logger.warning(f"Preset configuration not found: {preset_name}")
            if self.debug_mode:
                self.console.print(f"[yellow]Preset not found: {preset_name}[/yellow]")

    def get_sudo_manager(self) -> Optional[SudoManager]:
        """获取sudo管理器实例.

        Returns:
            SudoManager实例，如果未设置则返回None
        """
        return self.sudo_manager

    def set_sudo_manager(self, sudo_manager: SudoManager) -> None:
        """设置sudo管理器实例.

        Args:
            sudo_manager: SudoManager实例
        """
        self.sudo_manager = sudo_manager
        self.logger.info("已设置应用级sudo管理器")

    def _cleanup_sudo_manager(self) -> None:
        """清理sudo管理器中的敏感数据."""
        if self.sudo_manager:
            try:
                self.sudo_manager.clear_password()
                self.logger.info("sudo管理器密码已清理")
            except Exception as e:
                self.logger.error(f"清理sudo管理器时出错: {e}")

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield Footer()
        
    def on_mount(self) -> None:
        """Called when app starts."""
        # Push the main screen
        from .ui.screens.main_menu import MainMenuScreen
        self.push_screen(MainMenuScreen(self.config_manager))
        
    async def action_settings(self) -> None:
        """Show settings screen."""
        from .ui.screens.settings import SettingsScreen
        self.push_screen(SettingsScreen(self.config_manager))
        
    async def action_help(self) -> None:
        """Show help screen."""
        from .ui.screens.help import HelpScreen
        self.push_screen(HelpScreen(self.config_manager))
        
    def action_quit(self) -> None:
        """Quit the application with comprehensive terminal cleanup."""
        # 首先清理sudo管理器中的敏感数据
        self._cleanup_sudo_manager()
        # 然后进行终端清理
        cleanup_terminal_state()
        self.exit()
        
    def action_force_quit(self) -> None:
        """Force quit the application (F12) - hidden testing shortcut."""
        self.action_quit()
        
    def action_reload_app(self) -> None:
        """Reload the application (F10) - hidden testing shortcut."""
        import os

        # Determine restart strategy first
        script_path = None
        if os.getenv('RUN_VIA_SCRIPT'):
            try:
                script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'run.sh')
                if not os.path.exists(script_path):
                    script_path = None
            except Exception:
                script_path = None

        # Set up restart command
        if script_path:
            # Restart via run.sh to maintain trap protection
            os.environ['RUN_VIA_SCRIPT'] = '1'  # Ensure environment is set
            original_args = [arg for arg in sys.argv[1:] if not arg.endswith('main.py')]
            restart_cmd = [script_path] + original_args
            restart_exec = script_path
        else:
            # Fallback: restart python process
            restart_cmd = [sys.executable] + sys.argv
            restart_exec = sys.executable

        # Perform comprehensive terminal cleanup BEFORE any Textual operations
        # 首先清理sudo管理器中的敏感数据
        self._cleanup_sudo_manager()
        cleanup_terminal_state()

        # Force additional cleanup - this is critical
        try:
            # Double-flush to ensure all escape sequences are sent
            sys.stdout.flush()
            sys.stderr.flush()

            # Additional terminal reset using system command
            os.system('printf "\\033[?1049l\\033[?25h\\033[0m" > /dev/tty 2>/dev/null')

        except Exception:
            pass

        # Replace current process immediately with new one
        os.execv(restart_exec, restart_cmd)
        
    def key_f10(self) -> None:
        """Handle F10 key directly - reload app."""
        self.action_reload_app()
        
    def key_f12(self) -> None:
        """Handle F12 key directly - force quit."""
        self.action_force_quit()
        
    def on_unmount(self) -> None:
        """Called when app is unmounted - ensure comprehensive cleanup."""
        cleanup_terminal_state()