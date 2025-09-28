"""Universal logging configuration for the Linux System Initializer."""

import logging
import logging.config
import logging.handlers
from pathlib import Path
from typing import Optional, Dict, Any

import yaml
from rich.logging import RichHandler
from rich.console import Console


class LoggerManager:
    """Manages application-wide logging configuration."""

    _instance: Optional['LoggerManager'] = None
    _initialized: bool = False

    def __new__(cls) -> 'LoggerManager':
        """Singleton pattern to ensure single logger manager instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize logger manager (singleton safe)."""
        if not self._initialized:
            self.config_dir: Optional[Path] = None
            self.debug_mode: bool = False
            self.console: Optional[Console] = None
            self._loggers: Dict[str, logging.Logger] = {}
            LoggerManager._initialized = True

    def initialize(self, config_dir: Path, debug: bool = False, console: Optional[Console] = None) -> None:
        """Initialize the logging system.

        Args:
            config_dir: Configuration directory path
            debug: Enable debug mode
            console: Rich console instance for consistent output
        """
        self.config_dir = config_dir
        self.debug_mode = debug
        self.console = console or Console()

        # Create logs directory in project root
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)

        # Load logging configuration
        self._load_logging_config()

        # Configure root logger
        self._configure_root_logger(logs_dir)

        # Log initialization
        logger = self.get_logger("initializer.logger")
        logger.info("Logging system initialized successfully")
        if debug:
            logger.debug("Debug mode enabled")

    def _load_logging_config(self) -> Dict[str, Any]:
        """Load logging configuration from YAML file.

        Returns:
            Logging configuration dictionary
        """
        config_file = self.config_dir / "logging.yaml"

        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    return config
            except Exception as e:
                # Fallback to default if config file is invalid
                print(f"Warning: Failed to load logging config, using default: {e}")

        return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default logging configuration.

        Returns:
            Default logging configuration dictionary
        """
        return {
            'level': 'DEBUG' if self.debug_mode else 'INFO',
            'console_level': 'DEBUG' if self.debug_mode else 'INFO',
            'file_level': 'DEBUG',
            'format': {
                'console': '%(message)s',
                'file': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            },
            'modules': {
                'initializer.app': 'INFO',
                'initializer.modules': 'INFO',
                'initializer.ui': 'WARNING' if not self.debug_mode else 'INFO',
                'initializer.utils': 'WARNING' if not self.debug_mode else 'DEBUG'
            }
        }

    def _configure_root_logger(self, logs_dir: Path) -> None:
        """Configure the root logger with handlers.

        Args:
            logs_dir: Directory for log files
        """
        config = self._load_logging_config()

        # Clear existing handlers
        root_logger = logging.getLogger()
        root_logger.handlers.clear()

        # Set root level
        root_logger.setLevel(getattr(logging, config['level']))

        # Console handler with Rich
        console_handler = RichHandler(
            console=self.console,
            rich_tracebacks=True,
            markup=True,
            show_path=self.debug_mode,
            show_time=False,  # Rich console handles time display
            enable_link_path=True
        )
        console_handler.setLevel(getattr(logging, config['console_level']))
        console_formatter = logging.Formatter(config['format']['console'])
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

        # File handler for persistent logging
        log_file = logs_dir / "initializer.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(getattr(logging, config['file_level']))
        file_formatter = logging.Formatter(config['format']['file'])
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

        # Configure module-specific loggers
        for module_name, level in config.get('modules', {}).items():
            module_logger = logging.getLogger(module_name)
            module_logger.setLevel(getattr(logging, level))

    def get_logger(self, name: str) -> logging.Logger:
        """Get a logger instance for the specified name.

        Args:
            name: Logger name (typically module name)

        Returns:
            Logger instance
        """
        if name not in self._loggers:
            self._loggers[name] = logging.getLogger(name)
        return self._loggers[name]

    def set_debug_mode(self, debug: bool) -> None:
        """Dynamically change debug mode.

        Args:
            debug: Enable/disable debug mode
        """
        self.debug_mode = debug

        # Update console handler level
        root_logger = logging.getLogger()
        for handler in root_logger.handlers:
            if isinstance(handler, RichHandler):
                handler.setLevel(logging.DEBUG if debug else logging.INFO)

        # Update module loggers
        if debug:
            for logger_name in self._loggers:
                if 'ui' in logger_name or 'utils' in logger_name:
                    self._loggers[logger_name].setLevel(logging.DEBUG)

        logger = self.get_logger("initializer.logger")
        logger.info(f"Debug mode {'enabled' if debug else 'disabled'}")


# Global logger manager instance
logger_manager = LoggerManager()


def init_logging(config_dir: Path, debug: bool = False, console: Optional[Console] = None) -> None:
    """Initialize the logging system.

    Args:
        config_dir: Configuration directory path
        debug: Enable debug mode
        console: Rich console instance
    """
    logger_manager.initialize(config_dir, debug, console)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    return logger_manager.get_logger(name)


def set_debug_mode(debug: bool) -> None:
    """Set debug mode dynamically.

    Args:
        debug: Enable/disable debug mode
    """
    logger_manager.set_debug_mode(debug)


# Convenience loggers for common use cases
def get_app_logger() -> logging.Logger:
    """Get the main application logger."""
    return get_logger("initializer.app")


def get_module_logger(module_name: str) -> logging.Logger:
    """Get a module-specific logger.

    Args:
        module_name: Module name

    Returns:
        Module logger
    """
    return get_logger(f"initializer.modules.{module_name}")


def get_ui_logger(screen_name: str) -> logging.Logger:
    """Get a UI screen-specific logger.

    Args:
        screen_name: Screen/component name

    Returns:
        UI logger
    """
    return get_logger(f"initializer.ui.{screen_name}")


def get_utils_logger(util_name: str) -> logging.Logger:
    """Get a utility-specific logger.

    Args:
        util_name: Utility name

    Returns:
        Utils logger
    """
    return get_logger(f"initializer.utils.{util_name}")