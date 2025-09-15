#!/usr/bin/env python3
"""
Linux System Initializer - Modern TUI Application
Author: DeltaV235
Description: A modern terminal user interface for Linux system initialization
"""

import sys
import signal
import atexit
from pathlib import Path
import click
from rich.console import Console

from .app import InitializerApp
from .config_manager import ConfigManager


console = Console()


def cleanup_terminal():
    """Clean up terminal state on exit - comprehensive reset matching reset-terminal.sh."""
    try:
        # Exit alternate screen buffer
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

        # Show cursor
        sys.stdout.write('\033[?25h')

        # Reset colors and attributes
        sys.stdout.write('\033[0m')

        # Clear any remaining escape sequences
        sys.stdout.write('\033c')

        # Ensure changes are flushed
        sys.stdout.flush()

        # Critical: Reset terminal to sane state - restore echo and proper input
        import subprocess
        try:
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


def signal_handler(signum, frame):
    """Handle signals and ensure proper cleanup."""
    cleanup_terminal()
    sys.exit(0)


# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Register atexit handler for additional safety
atexit.register(cleanup_terminal)


@click.command()
@click.option('--preset', '-p', help='Use a configuration preset')
@click.option('--config-dir', '-c', default='config', help='Configuration directory path')
@click.option('--headless', is_flag=True, help='Run in headless mode (no animations)')
@click.option('--debug', is_flag=True, help='Enable debug mode')
def main(preset: str, config_dir: str, headless: bool, debug: bool):
    """Launch the Linux System Initializer TUI application."""
    
    try:
        # Initialize configuration manager
        config_manager = ConfigManager(Path(config_dir))
        
        # Load application configuration
        app_config = config_manager.get_app_config()
        
        if debug:
            console.print(f"[blue]Starting {app_config.name} v{app_config.version}[/blue]")
            console.print(f"[dim]Config directory: {config_dir}[/dim]")
            if preset:
                console.print(f"[dim]Using preset: {preset}[/dim]")
        
        # Create and run the application
        app = InitializerApp(config_manager, preset=preset, headless=headless, debug=debug)
        app.run()
        
        # Always cleanup on normal exit
        cleanup_terminal()
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Application interrupted by user[/yellow]")
        cleanup_terminal()
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]Error starting application: {e}[/red]")
        if debug:
            console.print_exception()
        cleanup_terminal()
        sys.exit(1)


if __name__ == "__main__":
    main()