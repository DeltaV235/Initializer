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

from .app import InitializerApp, cleanup_terminal_state
from .config_manager import ConfigManager


console = Console()


def signal_handler(signum, frame):
    """Handle signals and ensure proper cleanup."""
    cleanup_terminal_state()
    sys.exit(0)


# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Register atexit handler for additional safety
atexit.register(cleanup_terminal_state)


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
        cleanup_terminal_state()

    except KeyboardInterrupt:
        console.print("\n[yellow]Application interrupted by user[/yellow]")
        cleanup_terminal_state()
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]Error starting application: {e}[/red]")
        if debug:
            console.print_exception()
        cleanup_terminal_state()
        sys.exit(1)


if __name__ == "__main__":
    main()