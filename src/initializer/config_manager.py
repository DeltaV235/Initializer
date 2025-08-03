"""Configuration management for the Linux System Initializer."""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class AppConfig:
    """Application configuration data class."""
    name: str
    version: str
    author: str
    description: str
    theme: str
    animation: bool
    min_width: int
    min_height: int
    features: Dict[str, bool]


@dataclass
class ModuleConfig:
    """Module configuration data class."""
    enabled: bool
    settings: Dict[str, Any]


class ConfigManager:
    """Manages application configuration from YAML files."""
    
    def __init__(self, config_dir: Path = Path("config")):
        self.config_dir = config_dir
        self._config_cache = {}
        
    def load_config(self, config_name: str) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if config_name in self._config_cache:
            return self._config_cache[config_name]
            
        config_path = self.config_dir / f"{config_name}.yaml"
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
            
        with open(config_path, 'r', encoding='utf-8') as file:
            config = yaml.safe_load(file)
            
        self._config_cache[config_name] = config
        return config
        
    def get_app_config(self) -> AppConfig:
        """Get application configuration."""
        config = self.load_config("app")
        app_section = config["app"]
        ui_section = config["ui"]
        
        return AppConfig(
            name=app_section["name"],
            version=app_section["version"],
            author=app_section["author"],
            description=app_section["description"],
            theme=ui_section["theme"],
            animation=ui_section["animation"],
            min_width=ui_section["terminal"]["min_width"],
            min_height=ui_section["terminal"]["min_height"],
            features=config.get("features", {})
        )
        
    def get_modules_config(self) -> Dict[str, ModuleConfig]:
        """Get modules configuration."""
        config = self.load_config("modules")
        modules = {}
        
        for module_name, module_config in config["modules"].items():
            modules[module_name] = ModuleConfig(
                enabled=module_config.get("enabled", True),
                settings=module_config
            )
            
        return modules
        
    def get_theme_config(self, theme_name: str = None) -> Dict[str, str]:
        """Get theme configuration."""
        config = self.load_config("themes")
        
        if theme_name is None:
            app_config = self.get_app_config()
            theme_name = app_config.theme
            
        if theme_name not in config["themes"]:
            theme_name = "default"
            
        return config["themes"][theme_name]
        
    def load_preset(self, preset_name: str) -> Dict[str, Any]:
        """Load a configuration preset."""
        preset_path = self.config_dir / "presets" / f"{preset_name}.yaml"
        
        if not preset_path.exists():
            raise FileNotFoundError(f"Preset not found: {preset_name}")
            
        with open(preset_path, 'r', encoding='utf-8') as file:
            return yaml.safe_load(file)
            
    def save_config(self, config_name: str, config_data: Dict[str, Any]) -> None:
        """Save configuration to YAML file."""
        config_path = self.config_dir / f"{config_name}.yaml"
        
        with open(config_path, 'w', encoding='utf-8') as file:
            yaml.dump(config_data, file, default_flow_style=False, indent=2)
            
        # Clear cache for this config
        if config_name in self._config_cache:
            del self._config_cache[config_name]