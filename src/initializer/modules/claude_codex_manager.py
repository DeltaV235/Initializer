"""Claude Code and Codex CLI management module."""

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


class ClaudeCodexManager:
    """Claude Code and Codex CLI management."""

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
            version_pattern=r'claude\s+v?(\d+\.\d+\.\d+)'
        )

        if not installed:
            logger.info("Claude Code not installed")
            return ClaudeCodeInfo(installed=False)

        logger.debug(f"Claude Code detected: version={version}, path={path}")

        # Step 2: Check config path
        config_path = Path.home() / ".claude"
        if not config_path.exists():
            logger.warning("Claude Code config directory not found")
            return ClaudeCodeInfo(installed=True, version=version)

        # Step 3: Read API Endpoint from settings.json
        api_endpoint = ClaudeCodexManager._read_api_endpoint(
            config_path / "settings.json"
        )

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
            f"mcp={mcp_count}, agents={agent_count}, commands={command_count}"
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
            global_memory_path=global_memory_path
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
            version_pattern=r'codex\s+v?(\d+\.\d+\.\d+)'
        )

        if not installed:
            logger.info("Codex not installed")
            return CodexInfo(installed=False)

        logger.debug(f"Codex detected: version={version}, path={path}")

        # Step 2: Check config path
        config_path = Path.home() / ".codex"
        if not config_path.exists():
            logger.warning("Codex config directory not found")
            return CodexInfo(installed=True, version=version)

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

                    # Extract API endpoint
                    api_endpoint = config.get("api_endpoint", None)

                    # Extract current model
                    current_model = config.get("model", None)

                    # Extract reasoning effort
                    reasoning_effort = config.get("reasoning_effort", None)

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
            f"model={current_model}, mcp={mcp_count}"
        )

        return CodexInfo(
            installed=True,
            version=version,
            api_endpoint=api_endpoint,
            mcp_count=mcp_count,
            agents_md_path=agents_md_path,
            current_model=current_model,
            reasoning_effort=reasoning_effort
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
    def _read_api_endpoint(settings_json_path: Path) -> Optional[str]:
        """Read API endpoint from settings.json.

        Args:
            settings_json_path: Path to settings.json file

        Returns:
            API endpoint URL or None if not found
        """
        try:
            if not settings_json_path.exists():
                return None

            with open(settings_json_path, "r", encoding="utf-8") as f:
                settings = json.load(f)

            return settings.get("apiEndpoint", None)

        except Exception as e:
            logger.warning(f"Failed to read API endpoint: {e}")
            return None

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
