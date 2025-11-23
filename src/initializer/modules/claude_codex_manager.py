"""Claude Code and Codex CLI management module."""

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ..utils.cli_detector import CLIDetector
from ..utils.logger import get_module_logger

logger = get_module_logger("claude_codex_manager")


@dataclass
class ClaudeCodeInfo:
    """Claude Code CLI installation and configuration information."""
    installed: bool
    version: Optional[str] = None
    api_endpoint: Optional[str] = None
    mcp_count: int = 0
    agent_count: int = 0
    command_count: int = 0
    output_style_count: int = 0
    plugin_count: int = 0
    hook_count: int = 0
    global_memory_path: Optional[str] = None
    installation_method: Optional[str] = None  # npm_global, manual, script, unknown


@dataclass
class CodexInfo:
    """Codex CLI installation and configuration information."""
    installed: bool
    version: Optional[str] = None
    api_endpoint: Optional[str] = None
    mcp_count: int = 0
    agents_md_path: Optional[str] = None
    current_model: Optional[str] = None
    reasoning_effort: Optional[str] = None
    installation_method: Optional[str] = None  # npm_global, manual, script, unknown


class ClaudeCodexManager:
    """Claude Code and Codex CLI management."""

    @staticmethod
    async def _detect_installation_method(tool_name: str, cli_path: Optional[str]) -> str:
        """检测工具的安装方式。

        Args:
            tool_name: 工具名称（claude 或 codex）
            cli_path: CLI 可执行文件路径

        Returns:
            安装方式：npm_global, manual, script, unknown
        """
        if not cli_path:
            return "unknown"

        # npm 包名映射（CLI 名称 -> npm 包名）
        npm_package_map = {
            "claude": "@anthropic-ai/claude-code",
            "codex": "@anthropics/codex"  # 注：需确认实际包名
        }

        # 检查是否通过 npm 全局安装
        npm_package = npm_package_map.get(tool_name, tool_name)
        try:
            process = await asyncio.create_subprocess_exec(
                "npm", "list", "-g", npm_package, "--depth=0",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await process.communicate()
            output = stdout.decode()
            if process.returncode == 0 and npm_package in output:
                logger.debug(f"{tool_name} installed via npm global ({npm_package})")
                return "npm_global"
        except Exception as e:
            logger.debug(f"npm check failed: {e}")

        # 检查路径是否在 node_modules 中
        if "node_modules" in cli_path or "pnpm" in cli_path:
            logger.debug(f"{tool_name} path contains node_modules/pnpm")
            return "npm_global"

        # 其他情况标记为手动安装
        return "manual"

    @staticmethod
    async def detect_claude_code() -> ClaudeCodeInfo:
        """Detect Claude Code CLI installation status and configuration.

        Returns:
            ClaudeCodeInfo object with installation details and configuration stats
        """
        logger.debug("Detecting Claude Code installation")

        # Step 1: Detect CLI tool
        installed, version, path = await CLIDetector.detect_cli_tool(
            "claude",
            version_pattern=r'v?(\d+\.\d+(?:\.\d+)?)'
        )

        if not installed:
            logger.info("Claude Code not installed")
            return ClaudeCodeInfo(installed=False)

        logger.debug(f"Claude Code detected: version={version}, path={path}")

        # Step 2: Detect installation method (before config check)
        installation_method = await ClaudeCodexManager._detect_installation_method("claude", path)

        # Step 3: Check config path
        config_path = Path.home() / ".claude"
        if not config_path.exists():
            logger.warning("Claude Code config directory not found")
            return ClaudeCodeInfo(
                installed=True,
                version=version,
                installation_method=installation_method
            )

        # Step 3: Read API Endpoint from settings.json
        api_endpoint = None
        try:
            settings_json_path = config_path / "settings.json"
            if settings_json_path.exists():
                with open(settings_json_path, "r", encoding="utf-8") as f:
                    settings = json.load(f)

                # Try to read from env section first (nested structure)
                if "env" in settings and isinstance(settings["env"], dict):
                    api_endpoint = ClaudeCodexManager._read_config_value(
                        settings["env"],
                        ["ANTHROPIC_BASE_URL", "ANTHROPIC_API_URL", "apiEndpoint"],
                        None
                    )

                # Fallback to top-level keys if not found in env
                if not api_endpoint:
                    api_endpoint = ClaudeCodexManager._read_config_value(
                        settings,
                        ["apiEndpoint", "api_endpoint", "endpoint"],
                        "Not configured"
                    )
            else:
                api_endpoint = "Not configured"
        except Exception as e:
            logger.warning(f"Failed to read Claude Code settings: {e}")
            api_endpoint = "Parse error"

        # Step 4: Count configuration items
        mcp_count = ClaudeCodexManager._count_mcp_servers(config_path)
        agent_count = ClaudeCodexManager._count_files(config_path / "agents", "**/*.md")
        command_count = ClaudeCodexManager._count_files(config_path / "commands", "**/*.md")
        output_style_count = ClaudeCodexManager._count_files(
            config_path / "output-styles", "**/*.md"
        )
        plugin_count = ClaudeCodexManager._read_plugin_count(
            config_path / "plugins" / "config.json"
        )
        hook_count = ClaudeCodexManager._count_files(config_path, "*-hook.sh")

        # Step 5: Check for global memory (CLAUDE.md)
        claude_md_path = config_path / "CLAUDE.md"
        global_memory_path = str(claude_md_path) if claude_md_path.exists() else None

        logger.info(
            f"Claude Code detection complete: version={version}, "
            f"mcp={mcp_count}, agents={agent_count}, commands={command_count}, "
            f"install_method={installation_method}"
        )

        return ClaudeCodeInfo(
            installed=True,
            version=version,
            api_endpoint=api_endpoint,
            mcp_count=mcp_count,
            agent_count=agent_count,
            command_count=command_count,
            output_style_count=output_style_count,
            plugin_count=plugin_count,
            hook_count=hook_count,
            global_memory_path=global_memory_path,
            installation_method=installation_method
        )

    @staticmethod
    async def detect_codex() -> CodexInfo:
        """Detect Codex CLI installation status and configuration.

        Returns:
            CodexInfo object with installation details and configuration stats
        """
        logger.debug("Detecting Codex installation")

        # Step 1: Detect CLI tool
        installed, version, path = await CLIDetector.detect_cli_tool(
            "codex",
            version_pattern=r'v?(\d+\.\d+(?:\.\d+)?)'
        )

        if not installed:
            logger.info("Codex not installed")
            return CodexInfo(installed=False)

        logger.debug(f"Codex detected: version={version}, path={path}")

        # Step 2: Detect installation method (before config check)
        installation_method = await ClaudeCodexManager._detect_installation_method("codex", path)

        # Step 3: Check config path
        config_path = Path.home() / ".codex"
        if not config_path.exists():
            logger.warning("Codex config directory not found")
            return CodexInfo(
                installed=True,
                version=version,
                installation_method=installation_method
            )

        # Step 3: Read configuration from config.toml
        api_endpoint = None
        current_model = None
        reasoning_effort = None
        mcp_count = 0

        try:
            # Try to import tomllib (Python 3.11+)
            try:
                import tomllib
            except ImportError:
                # Fallback to tomli for older Python versions
                try:
                    import tomli as tomllib
                except ImportError:
                    logger.warning("Neither tomllib nor tomli available, cannot parse TOML")
                    tomllib = None

            if tomllib:
                config_toml_path = config_path / "config.toml"
                if config_toml_path.exists():
                    with open(config_toml_path, "rb") as f:
                        config = tomllib.load(f)

                    # Extract current model
                    current_model = ClaudeCodexManager._read_config_value(
                        config,
                        ["model", "default_model"],
                        "Not configured"
                    )

                    # Extract reasoning effort (note: field name is model_reasoning_effort)
                    reasoning_effort = ClaudeCodexManager._read_config_value(
                        config,
                        ["model_reasoning_effort", "reasoning_effort", "reasoningEffort"],
                        "Not configured"
                    )

                    # Extract API endpoint from nested model_providers structure
                    api_endpoint = None
                    try:
                        # Try to read from nested model_providers first
                        model_provider = config.get("model_provider", None)
                        if model_provider and "model_providers" in config:
                            model_providers = config.get("model_providers", {})
                            if isinstance(model_providers, dict) and model_provider in model_providers:
                                provider_config = model_providers[model_provider]
                                if isinstance(provider_config, dict):
                                    api_endpoint = ClaudeCodexManager._read_config_value(
                                        provider_config,
                                        ["base_url", "baseUrl", "url"],
                                        None
                                    )

                        # Fallback to top-level keys if not found in model_providers
                        if not api_endpoint:
                            api_endpoint = ClaudeCodexManager._read_config_value(
                                config,
                                ["api_endpoint", "apiEndpoint", "base_url", "endpoint"],
                                "Not configured"
                            )
                    except Exception as e:
                        logger.warning(f"Failed to extract Codex API endpoint: {e}")
                        api_endpoint = "Parse error"

                    # Count MCP servers
                    mcp_servers = config.get("mcp_servers", {})
                    mcp_count = len(mcp_servers)

                    logger.debug(
                        f"Parsed Codex config: model={current_model}, "
                        f"reasoning_effort={reasoning_effort}, mcp_count={mcp_count}"
                    )

        except Exception as e:
            logger.warning(f"Failed to read Codex config.toml: {e}")

        # Step 4: Check for AGENTS.md
        agents_md_path_obj = config_path / "AGENTS.md"
        agents_md_path = str(agents_md_path_obj) if agents_md_path_obj.exists() else None

        logger.info(
            f"Codex detection complete: version={version}, "
            f"model={current_model}, mcp={mcp_count}, "
            f"install_method={installation_method}"
        )

        return CodexInfo(
            installed=True,
            version=version,
            api_endpoint=api_endpoint,
            mcp_count=mcp_count,
            agents_md_path=agents_md_path,
            current_model=current_model,
            reasoning_effort=reasoning_effort,
            installation_method=installation_method
        )

    @staticmethod
    def _count_files(directory: Path, pattern: str) -> int:
        """Count files matching a glob pattern in a directory.

        Args:
            directory: Directory to search in
            pattern: Glob pattern (e.g., "*.md", "**/*.py")

        Returns:
            Number of matching files
        """
        if not directory.exists():
            return 0

        try:
            return len(list(directory.glob(pattern)))
        except Exception as e:
            logger.warning(f"Failed to count files in {directory}: {e}")
            return 0

    @staticmethod
    def _count_mcp_servers(config_path: Path) -> int:
        """Count MCP servers from config.toml.

        Args:
            config_path: Path to .claude or .codex directory

        Returns:
            Number of configured MCP servers
        """
        try:
            # Try to import tomllib (Python 3.11+)
            try:
                import tomllib
            except ImportError:
                # Fallback to tomli
                try:
                    import tomli as tomllib
                except ImportError:
                    logger.warning("Neither tomllib nor tomli available")
                    return 0

            config_toml_path = config_path / "config.toml"
            if not config_toml_path.exists():
                return 0

            with open(config_toml_path, "rb") as f:
                config = tomllib.load(f)

            mcp_servers = config.get("mcp_servers", {})
            return len(mcp_servers)

        except Exception as e:
            logger.warning(f"Failed to count MCP servers: {e}")
            return 0

    @staticmethod
    def _read_config_value(
        config: dict,
        possible_keys: list[str],
        default: Optional[str] = None
    ) -> Optional[str]:
        """从配置字典中尝试多个可能的键名读取值。

        Args:
            config: 配置字典
            possible_keys: 按优先级排序的键名列表
            default: 未找到时的默认值

        Returns:
            第一个找到的非空值，或 default
        """
        for key in possible_keys:
            if key in config and config[key]:
                return str(config[key])
        return default

    @staticmethod
    def _read_plugin_count(plugin_config_path: Path) -> int:
        """Read plugin count from plugins/config.json.

        Args:
            plugin_config_path: Path to plugins/config.json file

        Returns:
            Number of configured plugins
        """
        try:
            if not plugin_config_path.exists():
                return 0

            with open(plugin_config_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            # Assume plugins are stored as a list or dict
            plugins = config.get("plugins", [])
            if isinstance(plugins, list):
                return len(plugins)
            elif isinstance(plugins, dict):
                return len(plugins)
            else:
                return 0

        except Exception as e:
            logger.warning(f"Failed to read plugin count: {e}")
            return 0

    @staticmethod
    def get_mcp_configs(config_path: str) -> list[dict]:
        """Get MCP server configurations.

        Args:
            config_path: Path to config directory (e.g., ~/.claude or ~/.codex)

        Returns:
            List of MCP server configurations
        """
        try:
            # Try to import tomllib (Python 3.11+)
            try:
                import tomllib
            except ImportError:
                try:
                    import tomli as tomllib
                except ImportError:
                    logger.warning("Neither tomllib nor tomli available")
                    return []

            config_toml_path = Path(config_path) / "config.toml"
            if not config_toml_path.exists():
                return []

            with open(config_toml_path, "rb") as f:
                config = tomllib.load(f)

            mcp_servers = config.get("mcp_servers", {})

            result = []
            for name, server_config in mcp_servers.items():
                result.append({
                    "name": name,
                    "command": server_config.get("command", "N/A"),
                    "env": server_config.get("env", {})
                })

            return result

        except Exception as e:
            logger.warning(f"Failed to read MCP configs: {e}")
            return []

    @staticmethod
    def get_agents(config_path: str) -> list[dict]:
        """Get Agent configurations from agents/ directory.

        Args:
            config_path: Path to config directory

        Returns:
            List of agent configurations with name and description
        """
        try:
            agents_dir = Path(config_path) / "agents"
            if not agents_dir.exists():
                return []

            result = []
            for md_file in agents_dir.glob("**/*.md"):
                try:
                    content = md_file.read_text(encoding="utf-8")

                    # Simple frontmatter parsing
                    name = md_file.stem
                    description = "N/A"

                    if content.startswith("---"):
                        parts = content.split("---", 2)
                        if len(parts) >= 3:
                            frontmatter = parts[1]

                            # Extract name
                            import re
                            name_match = re.search(r'name:\s*["\']?(.+?)["\']?\s*$', frontmatter, re.MULTILINE)
                            if name_match:
                                name = name_match.group(1).strip()

                            # Extract description
                            desc_match = re.search(r'description:\s*["\']?(.+?)["\']?\s*$', frontmatter, re.MULTILINE)
                            if desc_match:
                                description = desc_match.group(1).strip()

                    result.append({
                        "name": name,
                        "description": description
                    })

                except Exception as e:
                    logger.warning(f"Failed to parse agent file {md_file}: {e}")
                    continue

            return result

        except Exception as e:
            logger.warning(f"Failed to read agents: {e}")
            return []

    @staticmethod
    def get_commands(config_path: str) -> list[dict]:
        """Get Command configurations from commands/ directory.

        Args:
            config_path: Path to config directory

        Returns:
            List of command configurations
        """
        # Same implementation as get_agents
        try:
            commands_dir = Path(config_path) / "commands"
            if not commands_dir.exists():
                return []

            result = []
            for md_file in commands_dir.glob("**/*.md"):
                try:
                    content = md_file.read_text(encoding="utf-8")

                    name = md_file.stem
                    description = "N/A"

                    if content.startswith("---"):
                        parts = content.split("---", 2)
                        if len(parts) >= 3:
                            frontmatter = parts[1]

                            import re
                            name_match = re.search(r'name:\s*["\']?(.+?)["\']?\s*$', frontmatter, re.MULTILINE)
                            if name_match:
                                name = name_match.group(1).strip()

                            desc_match = re.search(r'description:\s*["\']?(.+?)["\']?\s*$', frontmatter, re.MULTILINE)
                            if desc_match:
                                description = desc_match.group(1).strip()

                    result.append({
                        "name": name,
                        "description": description
                    })

                except Exception as e:
                    logger.warning(f"Failed to parse command file {md_file}: {e}")
                    continue

            return result

        except Exception as e:
            logger.warning(f"Failed to read commands: {e}")
            return []

    @staticmethod
    def get_output_styles(config_path: str) -> list[dict]:
        """Get Output Style configurations.

        Args:
            config_path: Path to config directory

        Returns:
            List of output style configurations
        """
        try:
            output_styles_dir = Path(config_path) / "output-styles"
            if not output_styles_dir.exists():
                return []

            result = []
            for md_file in output_styles_dir.glob("**/*.md"):
                try:
                    content = md_file.read_text(encoding="utf-8")

                    name = md_file.stem
                    description = "N/A"

                    if content.startswith("---"):
                        parts = content.split("---", 2)
                        if len(parts) >= 3:
                            frontmatter = parts[1]

                            import re
                            name_match = re.search(r'name:\s*["\']?(.+?)["\']?\s*$', frontmatter, re.MULTILINE)
                            if name_match:
                                name = name_match.group(1).strip()

                            desc_match = re.search(r'description:\s*["\']?(.+?)["\']?\s*$', frontmatter, re.MULTILINE)
                            if desc_match:
                                description = desc_match.group(1).strip()

                    result.append({
                        "name": name,
                        "description": description
                    })

                except Exception as e:
                    logger.warning(f"Failed to parse output style file {md_file}: {e}")
                    continue

            return result

        except Exception as e:
            logger.warning(f"Failed to read output styles: {e}")
            return []

    @staticmethod
    def get_hooks(config_path: str) -> list[dict]:
        """Get Hook configurations.

        Args:
            config_path: Path to config directory

        Returns:
            List of hook configurations
        """
        try:
            config_dir = Path(config_path)
            if not config_dir.exists():
                return []

            result = []
            for hook_file in config_dir.glob("*-hook.sh"):
                hook_name = hook_file.stem  # Remove .sh extension
                hook_type = hook_name.replace("-hook", "")  # e.g., "pre-commit"

                result.append({
                    "name": hook_name,
                    "type": hook_type,
                    "path": str(hook_file)
                })

            return result

        except Exception as e:
            logger.warning(f"Failed to read hooks: {e}")
            return []
