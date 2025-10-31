"""通用 CLI 工具检测器模块。

提供统一的 CLI 工具安装状态和版本检测功能，消除重复代码。
"""

import re
import shutil
import subprocess
from typing import Optional, Tuple

from .logger import get_module_logger


class CLIDetector:
    """通用 CLI 工具检测器。

    提供统一的接口检测 CLI 工具的安装状态、版本号和路径。
    """

    @staticmethod
    async def detect_cli_tool(
        tool_name: str,
        version_pattern: str = r'v?(\d+\.\d+(?:\.\d+)?)',
        timeout: int = 5
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """检测 CLI 工具的安装状态和版本。

        Args:
            tool_name: 工具命令名（如 "claude", "codex", "nvim"）
            version_pattern: 版本号正则表达式，默认匹配 X.Y.Z 格式
            timeout: 命令超时时间（秒），默认 5 秒

        Returns:
            (installed, version, path) 元组：
            - installed: 是否已安装
            - version: 版本号字符串，未检测到则为 "Unknown"
            - path: 工具的完整路径，未安装则为 None

        Examples:
            >>> installed, version, path = await CLIDetector.detect_cli_tool("nvim")
            >>> print(f"NeoVim {version} installed at {path}")
        """
        logger = get_module_logger("cli_detector")
        logger.debug(f"Detecting {tool_name} installation")

        # Step 1: 检查工具是否在 PATH 中
        tool_path = shutil.which(tool_name)
        if not tool_path:
            logger.info(f"{tool_name} not found in PATH")
            return (False, None, None)

        logger.debug(f"{tool_name} found at: {tool_path}")

        # Step 2: 尝试获取版本号
        version = "Unknown"
        try:
            result = subprocess.run(
                [tool_name, "--version"],
                capture_output=True,
                text=True,
                timeout=timeout
            )

            # Step 3: 解析版本号
            if result.returncode == 0:
                match = re.search(version_pattern, result.stdout, re.IGNORECASE)
                if match:
                    version = match.group(1)
                    logger.debug(f"{tool_name} version: {version}")
                else:
                    logger.warning(
                        f"Could not parse version from output: {result.stdout[:100]}"
                    )
            else:
                logger.warning(
                    f"{tool_name} --version command failed: {result.stderr[:100]}"
                )

        except subprocess.TimeoutExpired:
            logger.warning(f"{tool_name} --version command timed out after {timeout}s")
        except FileNotFoundError:
            # 理论上不会到这里，因为已经检查了 which
            logger.error(f"{tool_name} command not found")
            return (False, None, None)
        except Exception as e:
            logger.error(f"Error detecting {tool_name} version: {e}")

        logger.info(
            f"{tool_name} detection complete: version={version}, path={tool_path}"
        )

        return (True, version, tool_path)
