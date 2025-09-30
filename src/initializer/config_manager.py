"""Configuration management for the Linux System Initializer."""

import yaml
from pathlib import Path
from typing import Dict, Any
from dataclasses import dataclass

from .utils.logger import get_utils_logger


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
        self.logger = get_utils_logger("config_manager")
        self.logger.info(f"配置管理器初始化完成: config_dir={config_dir}")
        
    def load_config(self, config_name: str) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if config_name in self._config_cache:
            self.logger.debug(f"使用缓存配置: {config_name}")
            return self._config_cache[config_name]

        config_path = self.config_dir / f"{config_name}.yaml"
        self.logger.info(f"加载配置文件: {config_path}")

        if not config_path.exists():
            self.logger.error(f"配置文件不存在: {config_path}")
            raise FileNotFoundError(f"Config file not found: {config_path}")

        try:
            with open(config_path, 'r', encoding='utf-8') as file:
                config = yaml.safe_load(file)

            if config is None:
                self.logger.warning(f"配置文件为空: {config_name}")
                config = {}

            self.logger.debug(f"配置解析成功: {config_name} ({len(config)} 个顶级键)")
            self._config_cache[config_name] = config
            return config

        except yaml.YAMLError as e:
            self.logger.error(f"YAML解析失败 [{config_name}]: {e}")
            raise
        except IOError as e:
            self.logger.error(f"读取配置文件失败 [{config_path}]: {e}")
            raise
        
    def get_app_config(self) -> AppConfig:
        """Get application configuration."""
        self.logger.debug("获取应用配置")
        try:
            config = self.load_config("app")
            app_section = config["app"]
            ui_section = config["ui"]

            app_config = AppConfig(
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
            self.logger.debug(f"应用配置加载成功: {app_config.name} v{app_config.version}")
            return app_config

        except KeyError as e:
            self.logger.error(f"应用配置缺少必需字段: {e}")
            raise
        except Exception as e:
            self.logger.error(f"获取应用配置失败: {e}")
            raise
        
    def get_modules_config(self) -> Dict[str, ModuleConfig]:
        """Get modules configuration."""
        self.logger.debug("获取模块配置")
        try:
            config = self.load_config("modules")
            modules = {}

            for module_name, module_config in config["modules"].items():
                modules[module_name] = ModuleConfig(
                    enabled=module_config.get("enabled", True),
                    settings=module_config
                )

            self.logger.debug(f"模块配置加载成功: {len(modules)} 个模块")
            return modules

        except KeyError as e:
            self.logger.error(f"模块配置缺少必需字段: {e}")
            raise
        except Exception as e:
            self.logger.error(f"获取模块配置失败: {e}")
            raise
        
    def get_theme_config(self, theme_name: str = None) -> Dict[str, str]:
        """Get theme configuration."""
        config = self.load_config("themes")

        if theme_name is None:
            app_config = self.get_app_config()
            theme_name = app_config.theme

        if theme_name not in config["themes"]:
            self.logger.warning(f"主题 '{theme_name}' 不存在，回退到 'default'")
            theme_name = "default"

        self.logger.debug(f"使用主题: {theme_name}")
        return config["themes"][theme_name]

    def load_preset(self, preset_name: str) -> Dict[str, Any]:
        """Load a configuration preset."""
        preset_path = self.config_dir / "presets" / f"{preset_name}.yaml"
        self.logger.info(f"加载预设配置: {preset_name}")

        if not preset_path.exists():
            self.logger.error(f"预设配置不存在: {preset_path}")
            raise FileNotFoundError(f"Preset not found: {preset_name}")

        try:
            with open(preset_path, 'r', encoding='utf-8') as file:
                preset_config = yaml.safe_load(file)

            self.logger.debug(f"预设配置加载成功: {preset_name}")
            return preset_config

        except yaml.YAMLError as e:
            self.logger.error(f"预设配置解析失败 [{preset_name}]: {e}")
            raise
        except IOError as e:
            self.logger.error(f"读取预设配置失败 [{preset_path}]: {e}")
            raise

    def save_config(self, config_name: str, config_data: Dict[str, Any]) -> None:
        """Save configuration to YAML file."""
        config_path = self.config_dir / f"{config_name}.yaml"
        self.logger.info(f"保存配置文件: {config_path}")

        try:
            with open(config_path, 'w', encoding='utf-8') as file:
                yaml.dump(config_data, file, default_flow_style=False, indent=2)

            # Clear cache for this config
            if config_name in self._config_cache:
                del self._config_cache[config_name]
                self.logger.debug(f"已清除配置缓存: {config_name}")

            self.logger.info(f"配置文件保存成功: {config_name}")

        except IOError as e:
            self.logger.error(f"保存配置文件失败 [{config_path}]: {e}")
            raise
        except Exception as e:
            self.logger.error(f"保存配置时发生错误: {e}")
            raise