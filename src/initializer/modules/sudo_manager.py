"""Sudo权限管理模块 - 提供会话级sudo权限验证和密码缓存功能."""

import subprocess
import base64
import os
import asyncio
from typing import Optional, Tuple
from ..utils.logger import get_module_logger


class SudoManager:
    """Sudo权限管理器 - 处理密码验证、缓存和命令执行."""

    def __init__(self):
        """初始化sudo权限管理器."""
        self.logger = get_module_logger("sudo_manager")

        # 密码和验证状态
        self._password: Optional[str] = None
        self._verified: bool = False
        self._retry_count: int = 0
        self._max_retries: int = 3

        # 用于密码加密的简单密钥（基于用户ID和进程ID）
        self._cipher_key = self._generate_cipher_key()

    def _generate_cipher_key(self) -> int:
        """生成用于密码加密的简单密钥.

        Returns:
            基于用户ID和进程ID的整数密钥
        """
        try:
            # 使用用户ID和进程ID生成简单密钥
            user_id = os.getuid() if hasattr(os, 'getuid') else 1000
            process_id = os.getpid()
            return (user_id * 13 + process_id * 7) % 255
        except Exception:
            # 回退到固定密钥
            return 42

    def _encrypt_password(self, password: str) -> str:
        """使用简单异或加密密码.

        Args:
            password: 明文密码

        Returns:
            加密后的base64编码字符串
        """
        try:
            # 简单的异或加密
            encrypted_bytes = bytearray()
            for i, char in enumerate(password.encode('utf-8')):
                key_byte = (self._cipher_key + i) % 255
                encrypted_bytes.append(char ^ key_byte)

            # Base64编码
            return base64.b64encode(encrypted_bytes).decode('ascii')
        except Exception as e:
            self.logger.error(f"密码加密失败: {e}")
            return ""

    def _decrypt_password(self, encrypted_password: str) -> str:
        """解密密码.

        Args:
            encrypted_password: 加密的base64编码字符串

        Returns:
            解密后的明文密码
        """
        try:
            # Base64解码
            encrypted_bytes = base64.b64decode(encrypted_password.encode('ascii'))

            # 异或解密
            decrypted_bytes = bytearray()
            for i, byte_val in enumerate(encrypted_bytes):
                key_byte = (self._cipher_key + i) % 255
                decrypted_bytes.append(byte_val ^ key_byte)

            return decrypted_bytes.decode('utf-8')
        except Exception as e:
            self.logger.error(f"密码解密失败: {e}")
            return ""

    def is_sudo_required(self, command: str) -> bool:
        """检查命令是否需要sudo权限.

        Args:
            command: 要执行的命令字符串

        Returns:
            True如果命令包含sudo，False否则
        """
        return 'sudo' in command.lower()

    def is_verified(self) -> bool:
        """检查当前是否已通过sudo验证.

        Returns:
            True如果已验证，False否则
        """
        return self._verified and self._password is not None

    def get_retry_count(self) -> int:
        """获取当前重试次数.

        Returns:
            当前重试次数
        """
        return self._retry_count

    def get_remaining_retries(self) -> int:
        """获取剩余重试次数.

        Returns:
            剩余重试次数
        """
        return max(0, self._max_retries - self._retry_count)

    def is_retry_available(self) -> bool:
        """检查是否还可以重试.

        Returns:
            True如果可以重试，False如果已达到最大重试次数
        """
        return self._retry_count < self._max_retries

    def verify_sudo_access(self, password: str) -> Tuple[bool, str]:
        """验证sudo权限并缓存密码.

        Args:
            password: 用户输入的密码

        Returns:
            (成功状态, 错误信息)
        """
        self.logger.info("开始验证sudo权限")

        if not password or not password.strip():
            return False, "密码不能为空"

        try:
            # 使用sudo -v验证密码
            process = subprocess.Popen(
                ['sudo', '-S', '-v'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            stdout, stderr = process.communicate(input=f"{password}\n", timeout=10)

            if process.returncode == 0:
                # 验证成功，缓存密码
                self._password = self._encrypt_password(password)
                self._verified = True
                self._retry_count = 0  # 重置重试计数

                self.logger.info("sudo权限验证成功")
                return True, "验证成功"
            else:
                # 验证失败
                self._retry_count += 1
                error_msg = "密码错误"

                # 解析具体错误信息
                if stderr:
                    if "incorrect password" in stderr.lower():
                        error_msg = "密码错误"
                    elif "not in the sudoers file" in stderr.lower():
                        error_msg = "当前用户不在sudoers列表中"
                    elif "command not found" in stderr.lower():
                        error_msg = "sudo命令未找到"
                    else:
                        error_msg = f"验证失败: {stderr.strip()}"

                remaining = self.get_remaining_retries()
                if remaining > 0:
                    error_msg += f"，还可以重试 {remaining} 次"
                else:
                    error_msg += "，已达到最大重试次数"

                self.logger.warning(f"sudo权限验证失败: {error_msg}")
                return False, error_msg

        except subprocess.TimeoutExpired:
            self._retry_count += 1
            error_msg = "验证超时，请重试"
            self.logger.error("sudo权限验证超时")
            return False, error_msg
        except FileNotFoundError:
            error_msg = "sudo命令未找到，请确保系统已安装sudo"
            self.logger.error("sudo命令未找到")
            return False, error_msg
        except Exception as e:
            self._retry_count += 1
            error_msg = f"验证过程出错: {str(e)}"
            self.logger.error(f"sudo权限验证异常: {e}")
            return False, error_msg

    def execute_with_sudo(self, command: str) -> Tuple[bool, str]:
        """使用缓存的密码执行sudo命令.

        Args:
            command: 要执行的命令（应该包含sudo）

        Returns:
            (成功状态, 输出信息或错误信息)
        """
        # 如果是root用户，直接执行命令（去掉sudo前缀）
        if self.is_root_user():
            # 如果命令包含sudo，移除sudo部分
            if self.is_sudo_required(command):
                # 移除sudo部分，保留实际命令
                clean_command = self._remove_sudo_from_command(command)
                self.logger.debug(f"root用户直接执行命令: {clean_command}")
                return self._execute_command_direct(clean_command)
            else:
                # 命令不包含sudo，直接执行
                return self._execute_command_direct(command)

        # 非root用户，继续原有逻辑
        if not self.is_verified():
            return False, "未验证sudo权限，请先进行权限验证"

        if not self.is_sudo_required(command):
            # 如果命令不需要sudo，直接执行
            return self._execute_command_direct(command)

        try:
            # 解密密码
            password = self._decrypt_password(self._password)
            if not password:
                return False, "密码解密失败"

            self.logger.debug(f"使用sudo执行命令: {command}")

            # 构建带密码的命令
            # 对于包含sudo的命令，使用echo password | 的方式
            full_command = f"echo '{password}' | {command}"

            result = subprocess.run(
                full_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )

            if result.returncode == 0:
                output = result.stdout.strip() if result.stdout.strip() else "命令执行成功"
                self.logger.debug("sudo命令执行成功")
                return True, output
            else:
                error_msg = result.stderr.strip() if result.stderr.strip() else "命令执行失败"
                if result.returncode:
                    error_msg += f" (退出码: {result.returncode})"

                # 检查是否是权限相关的错误
                if "incorrect password" in error_msg.lower() or "authentication failure" in error_msg.lower():
                    # 密码可能已过期，清理缓存
                    self.clear_password()
                    error_msg += " - 权限已过期，请重新验证"

                self.logger.warning(f"sudo命令执行失败: {error_msg}")
                return False, error_msg

        except subprocess.TimeoutExpired:
            return False, "命令执行超时（5分钟）"
        except Exception as e:
            error_msg = f"执行错误: {str(e)}"
            self.logger.error(f"sudo命令执行异常: {e}")
            return False, error_msg

    def _remove_sudo_from_command(self, command: str) -> str:
        """从命令中移除sudo部分.

        Args:
            command: 包含sudo的命令字符串

        Returns:
            移除sudo后的命令字符串
        """
        try:
            # 处理各种sudo命令格式
            import shlex

            # 首先尝试用shell解析来处理复杂的命令
            parts = shlex.split(command)

            # 移除sudo及其参数
            clean_parts = []
            skip_next = False
            for i, part in enumerate(parts):
                if skip_next:
                    skip_next = False
                    continue

                if part == 'sudo':
                    # 跳过sudo，检查是否有参数（如-S, -u等）
                    continue
                elif part.startswith('-') and i > 0 and parts[i-1] == 'sudo':
                    # 跳过sudo的参数，如-S, -u user等
                    if part in ['-u', '-g', '-H', '-P']:
                        skip_next = True  # 这些参数后面还有值
                    continue
                else:
                    clean_parts.append(part)

            # 重新组合命令
            if clean_parts:
                clean_command = ' '.join(clean_parts)
                self.logger.debug(f"移除sudo后的命令: {clean_command}")
                return clean_command
            else:
                return command

        except Exception as e:
            self.logger.warning(f"解析sudo命令失败，使用简单替换: {e}")
            # 回退到简单的字符串替换
            clean_command = command.replace('sudo ', '', 1).strip()
            return clean_command if clean_command else command

    def _execute_command_direct(self, command: str) -> Tuple[bool, str]:
        """直接执行不需要sudo的命令.

        Args:
            command: 要执行的命令

        Returns:
            (成功状态, 输出信息或错误信息)
        """
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode == 0:
                output = result.stdout.strip() if result.stdout.strip() else "命令执行成功"
                return True, output
            else:
                error_msg = result.stderr.strip() if result.stderr.strip() else "命令执行失败"
                if result.returncode:
                    error_msg += f" (退出码: {result.returncode})"
                return False, error_msg

        except subprocess.TimeoutExpired:
            return False, "命令执行超时（5分钟）"
        except Exception as e:
            return False, f"执行错误: {str(e)}"

    async def execute_with_sudo_async(self, command: str) -> Tuple[bool, str]:
        """异步执行sudo命令（用于UI线程）.

        Args:
            command: 要执行的命令

        Returns:
            (成功状态, 输出信息或错误信息)
        """
        # 如果是root用户，直接执行命令（去掉sudo前缀）
        if self.is_root_user():
            # 如果命令包含sudo，移除sudo部分
            if self.is_sudo_required(command):
                # 移除sudo部分，保留实际命令
                clean_command = self._remove_sudo_from_command(command)
                self.logger.debug(f"root用户异步直接执行命令: {clean_command}")
                return await self._execute_command_direct_async(clean_command)
            else:
                # 命令不包含sudo，直接执行
                return await self._execute_command_direct_async(command)

        # 非root用户，继续原有逻辑
        if not self.is_verified():
            return False, "未验证sudo权限，请先进行权限验证"

        if not self.is_sudo_required(command):
            # 如果命令不需要sudo，直接执行
            return await self._execute_command_direct_async(command)

        try:
            # 解密密码
            password = self._decrypt_password(self._password)
            if not password:
                return False, "密码解密失败"

            self.logger.debug(f"异步使用sudo执行命令: {command}")

            # 创建subprocess
            process = await asyncio.create_subprocess_shell(
                command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                text=True
            )

            # 发送密码到stdin
            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=f"{password}\n"),
                timeout=300.0
            )

            if process.returncode == 0:
                output = stdout.strip() if stdout and stdout.strip() else "命令执行成功"
                self.logger.debug("异步sudo命令执行成功")
                return True, output
            else:
                error_msg = stderr.strip() if stderr and stderr.strip() else "命令执行失败"
                if process.returncode:
                    error_msg += f" (退出码: {process.returncode})"

                # 检查是否是权限相关的错误
                if "incorrect password" in error_msg.lower() or "authentication failure" in error_msg.lower():
                    self.clear_password()
                    error_msg += " - 权限已过期，请重新验证"

                self.logger.warning(f"异步sudo命令执行失败: {error_msg}")
                return False, error_msg

        except asyncio.TimeoutError:
            return False, "命令执行超时（5分钟）"
        except Exception as e:
            error_msg = f"异步执行错误: {str(e)}"
            self.logger.error(f"异步sudo命令执行异常: {e}")
            return False, error_msg

    async def _execute_command_direct_async(self, command: str) -> Tuple[bool, str]:
        """异步执行不需要sudo的命令.

        Args:
            command: 要执行的命令

        Returns:
            (成功状态, 输出信息或错误信息)
        """
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                text=True
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=300.0
            )

            if process.returncode == 0:
                output = stdout.strip() if stdout and stdout.strip() else "命令执行成功"
                return True, output
            else:
                error_msg = stderr.strip() if stderr and stderr.strip() else "命令执行失败"
                if process.returncode:
                    error_msg += f" (退出码: {process.returncode})"
                return False, error_msg

        except asyncio.TimeoutError:
            return False, "命令执行超时（5分钟）"
        except Exception as e:
            return False, f"异步执行错误: {str(e)}"

    def is_root_user(self) -> bool:
        """检查当前用户是否为 root 用户.

        Returns:
            True如果是root用户，False否则
        """
        try:
            # 使用 os.getuid() 检查用户ID，root用户的UID是0
            user_id = os.getuid() if hasattr(os, 'getuid') else None
            is_root = user_id == 0

            if is_root:
                self.logger.info("当前用户是 root 用户，无需 sudo 权限")
            else:
                self.logger.debug(f"当前用户 UID: {user_id}，非 root 用户")

            return is_root
        except Exception as e:
            self.logger.error(f"检查root用户状态失败: {e}")
            return False

    def check_sudo_available(self) -> bool:
        """检查系统是否支持sudo（不需要密码的基本检查）.

        Returns:
            True如果sudo可用，False否则
        """
        try:
            # 如果是root用户，直接返回True（不需要sudo）
            if self.is_root_user():
                self.logger.info("当前是root用户，无需sudo命令")
                return True

            # 检查sudo命令是否存在
            result = subprocess.run(
                ["which", "sudo"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0:
                self.logger.warning("sudo命令未找到")
                return False

            # 尝试使用-n参数检查是否有缓存的认证
            result = subprocess.run(
                ["sudo", "-n", "true"],
                capture_output=True,
                text=True,
                timeout=5
            )

            # 不管结果如何，sudo命令本身是可用的
            return True

        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            self.logger.error(f"检查sudo可用性失败: {e}")
            return False

    def clear_password(self) -> None:
        """清理内存中的密码和验证状态."""
        if self._password:
            # 清理加密密码
            self._password = None

        self._verified = False
        self._retry_count = 0

        self.logger.info("已清理sudo密码缓存")

    def __del__(self):
        """析构函数，确保清理敏感数据."""
        try:
            self.clear_password()
        except:
            pass  # 忽略析构过程中的异常
