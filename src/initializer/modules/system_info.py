"""System information module for gathering and displaying system details."""

import platform
import subprocess
import shutil
from pathlib import Path
from typing import Dict, Any

try:
    import psutil
    import distro
    EXTENDED_INFO_AVAILABLE = True
except ImportError:
    EXTENDED_INFO_AVAILABLE = False

from ..config_manager import ConfigManager
from ..utils.logger import get_module_logger


class SystemInfoModule:
    """Module for gathering comprehensive system information."""

    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        # Load raw configuration directly
        modules_config = config_manager.load_config("modules")
        self.config = modules_config.get('modules', {}).get('system_info', {})
        self.logger = get_module_logger("system_info")
        self.logger.info("系统信息模块初始化完成")

    def get_distribution_info(self) -> Dict[str, str]:
        """Get Linux distribution information."""
        self.logger.debug("开始获取发行版信息")
        info = {
            "System": platform.system(),
            "Release": platform.release(),
            "Version": platform.version(),
            "Machine": platform.machine(),
            "Architecture": platform.architecture()[0],
        }

        if EXTENDED_INFO_AVAILABLE:
            info.update({
                "Distribution": distro.name(),
                "Distro Version": distro.version(),
                "Distro Codename": distro.codename(),
            })
            self.logger.debug(f"使用 distro 库获取发行版信息: {distro.name()}")
        else:
            # Fallback method
            self.logger.debug("distro 库不可用，使用 /etc/os-release 获取信息")
            try:
                with open("/etc/os-release", "r") as f:
                    for line in f:
                        if line.startswith("PRETTY_NAME="):
                            info["Distribution"] = line.split("=")[1].strip().strip('"')
                            break
                self.logger.debug(f"从 /etc/os-release 读取成功: {info.get('Distribution', 'Unknown')}")
            except FileNotFoundError:
                self.logger.warning("/etc/os-release 文件不存在")
                info["Distribution"] = "Unknown"
            except Exception as e:
                self.logger.error(f"读取 /etc/os-release 失败: {e}")
                info["Distribution"] = "Unknown"

        return info

    def get_package_manager_info(self) -> Dict[str, str]:
        """Detect available package managers and their sources."""
        self.logger.info("开始检测包管理器")
        package_managers = {
            "apt": "APT (Debian/Ubuntu)",
            "yum": "YUM (RHEL/CentOS)",
            "dnf": "DNF (Fedora)",
            "pacman": "Pacman (Arch)",
            "zypper": "Zypper (openSUSE)",
            "brew": "Homebrew",
            "pkg": "FreeBSD pkg",
            "portage": "Portage (Gentoo)",
        }

        detected = {}

        for pm, description in package_managers.items():
            if shutil.which(pm):
                try:
                    # Get version information
                    result = subprocess.run(
                        [pm, "--version"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )

                    if result.returncode == 0:
                        version_line = result.stdout.split('\n')[0]
                        # Extract just the version number for cleaner display
                        if pm == "apt":
                            version = version_line.split()[1] if len(version_line.split()) > 1 else "Installed"
                            detected[description] = f"✓ {version}"
                            self.logger.debug(f"检测到 {pm}: {version}")

                            # Add APT sources information
                            apt_sources = self._get_apt_sources()
                            if apt_sources:
                                detected[f"{description} - Sources"] = apt_sources

                        elif pm == "pacman":
                            version = version_line.split()[2] if len(version_line.split()) > 2 else "Installed"
                            detected[description] = f"✓ {version}"
                            self.logger.debug(f"检测到 {pm}: {version}")

                            # Add Pacman mirror information
                            pacman_mirrors = self._get_pacman_mirrors()
                            if pacman_mirrors:
                                detected[f"{description} - Mirrors"] = pacman_mirrors

                        elif pm in ["yum", "dnf"]:
                            version = version_line[:50]  # Limit length
                            detected[description] = f"✓ {version}"
                            self.logger.debug(f"检测到 {pm}: {version[:30]}")

                            # Add YUM/DNF repository information
                            repos = self._get_yum_dnf_repos(pm)
                            if repos:
                                detected[f"{description} - Repos"] = repos

                        elif pm == "brew":
                            version = version_line[:50]
                            detected[description] = f"✓ {version}"
                            self.logger.debug(f"检测到 {pm}: {version[:30]}")

                            # Add Homebrew sources information
                            brew_sources = self._get_homebrew_sources()
                            if brew_sources:
                                detected[f"{description} - Sources"] = brew_sources

                        else:
                            version = version_line[:50]  # Limit length
                            detected[description] = f"✓ {version}"
                            self.logger.debug(f"检测到 {pm}")
                    else:
                        detected[description] = "✓ Installed"
                        self.logger.debug(f"检测到 {pm} (无版本信息)")

                except subprocess.TimeoutExpired:
                    detected[description] = "✓ Detected"
                    self.logger.warning(f"{pm} 版本检测超时")
                except subprocess.CalledProcessError as e:
                    detected[description] = "✓ Detected"
                    self.logger.debug(f"{pm} 命令执行失败: {e}")
                except FileNotFoundError:
                    self.logger.debug(f"{pm} 命令未找到")

        # If no package managers detected, try to guess from the distribution
        if not detected:
            self.logger.warning("未检测到任何包管理器，尝试从发行版文件推测")
            try:
                if Path("/etc/debian_version").exists():
                    detected["APT (Debian/Ubuntu)"] = "? Possibly available but not detected"
                    self.logger.info("发现 /etc/debian_version，可能是 Debian 系发行版")
                elif Path("/etc/redhat-release").exists():
                    detected["YUM/DNF (Red Hat)"] = "? Possibly available but not detected"
                    self.logger.info("发现 /etc/redhat-release，可能是 Red Hat 系发行版")
                elif Path("/etc/arch-release").exists():
                    detected["Pacman (Arch)"] = "? Possibly available but not detected"
                    self.logger.info("发现 /etc/arch-release，可能是 Arch 系发行版")
                else:
                    detected["Unknown"] = "No package managers available"
                    self.logger.warning("无法识别发行版类型")
            except Exception as e:
                detected["Detection Failed"] = "Unable to detect package managers"
                self.logger.error(f"检测发行版文件时出错: {e}")

        self.logger.info(f"包管理器检测完成: {len(detected)} 项")
        return detected

    def _get_apt_sources(self) -> str:
        """Get APT sources information."""
        self.logger.debug("获取 APT 源信息")
        try:
            # Check main sources.list
            sources_files = ["/etc/apt/sources.list"]

            # Check sources.list.d directory
            sources_d = Path("/etc/apt/sources.list.d")
            if sources_d.exists():
                sources_files.extend([str(f) for f in sources_d.glob("*.list")])

            apt_sources = []
            for sources_file in sources_files:
                try:
                    with open(sources_file, 'r') as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#') and line.startswith('deb'):
                                parts = line.split()
                                if len(parts) >= 2:
                                    url = parts[1]
                                    # Extract domain from URL
                                    if '://' in url:
                                        domain = url.split('://')[1].split('/')[0]
                                        if domain not in apt_sources:
                                            apt_sources.append(domain)
                except PermissionError:
                    self.logger.warning(f"无权限读取 APT 源文件: {sources_file}")
                    continue
                except FileNotFoundError:
                    self.logger.debug(f"APT 源文件不存在: {sources_file}")
                    continue

            if apt_sources:
                self.logger.debug(f"找到 {len(apt_sources)} 个 APT 源")
                return ", ".join(apt_sources[:3])  # Show first 3
        except Exception as e:
            self.logger.error(f"获取 APT 源信息失败: {e}")
        return ""

    def _get_pacman_mirrors(self) -> str:
        """Get Pacman mirror information."""
        self.logger.debug("获取 Pacman 镜像信息")
        try:
            pacman_conf = "/etc/pacman.conf"
            mirrorlist = "/etc/pacman.d/mirrorlist"

            mirrors = []
            for conf_file in [pacman_conf, mirrorlist]:
                try:
                    with open(conf_file, 'r') as f:
                        for line in f:
                            line = line.strip()
                            if line.startswith('Server =') and not line.startswith('#'):
                                url = line.split('=', 1)[1].strip()
                                if '://' in url:
                                    domain = url.split('://')[1].split('/')[0]
                                    if domain not in mirrors:
                                        mirrors.append(domain)
                except PermissionError:
                    self.logger.warning(f"无权限读取 Pacman 配置: {conf_file}")
                    continue
                except FileNotFoundError:
                    self.logger.debug(f"Pacman 配置不存在: {conf_file}")
                    continue

            if mirrors:
                self.logger.debug(f"找到 {len(mirrors)} 个 Pacman 镜像")
                return ", ".join(mirrors[:3])  # Show first 3
        except Exception as e:
            self.logger.error(f"获取 Pacman 镜像信息失败: {e}")
        return ""
    
    def _get_yum_dnf_repos(self, cmd: str) -> str:
        """Get YUM/DNF repository information."""
        self.logger.debug(f"获取 {cmd} 仓库列表")
        try:
            result = subprocess.run(
                [cmd, "repolist", "enabled"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                lines = result.stdout.split('\n')[2:]  # Skip header
                repos = []
                for line in lines:
                    if line.strip():
                        parts = line.split()
                        if parts:
                            repo_name = parts[0]
                            if repo_name not in repos:
                                repos.append(repo_name)

                if repos:
                    self.logger.debug(f"找到 {len(repos)} 个 {cmd} 仓库")
                    return ", ".join(repos[:3])  # Show first 3
        except subprocess.TimeoutExpired:
            self.logger.warning(f"{cmd} repolist 超时")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            self.logger.debug(f"{cmd} repolist 执行失败: {e}")
        return ""

    def _get_homebrew_sources(self) -> str:
        """Get Homebrew source information."""
        self.logger.debug("获取 Homebrew 源信息")
        try:
            # Check Homebrew core tap
            result = subprocess.run(
                ["brew", "tap"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                taps = result.stdout.strip().split('\n')
                core_taps = [tap for tap in taps if 'core' in tap or 'homebrew' in tap]
                if core_taps:
                    return ", ".join(core_taps[:2])

            # Check HOMEBREW_BOTTLE_DOMAIN environment variable
            result = subprocess.run(
                ["brew", "config"],
                capture_output=True,
                text=True,
                timeout=5
            )

            for line in result.stdout.split('\n'):
                if 'HOMEBREW_BOTTLE_DOMAIN' in line and ':' in line:
                    domain = line.split(':', 1)[1].strip()
                    if domain:
                        return f"Bottles: {domain}"
                    break

        except subprocess.TimeoutExpired:
            self.logger.warning("Homebrew 命令超时")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            self.logger.debug(f"Homebrew 命令执行失败: {e}")
        return ""
    
    def get_cpu_info(self) -> Dict[str, str]:
        """Get CPU information."""
        info = {
            "Processor": platform.processor() or "Unknown",
        }
        
        if EXTENDED_INFO_AVAILABLE:
            info.update({
                "CPU Count": str(psutil.cpu_count(logical=False)),
                "Logical CPUs": str(psutil.cpu_count(logical=True)),
                "Current Usage": f"{psutil.cpu_percent(interval=1):.1f}%",
            })
            
            # Get CPU frequency if available
            try:
                freq = psutil.cpu_freq()
                if freq:
                    info["CPU Frequency"] = f"{freq.current:.0f} MHz"
            except:
                pass
        else:
            # Fallback method
            try:
                with open("/proc/cpuinfo", "r") as f:
                    lines = f.readlines()
                    for line in lines:
                        if "model name" in line:
                            info["CPU Model"] = line.split(":")[1].strip()
                            break
                        if "cpu cores" in line:
                            info["CPU Cores"] = line.split(":")[1].strip()
            except FileNotFoundError:
                pass
                
        return info
    
    def get_memory_info(self) -> Dict[str, str]:
        """Get memory information."""
        info = {}
        
        if EXTENDED_INFO_AVAILABLE:
            mem = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            info.update({
                "Total RAM": self._format_bytes(mem.total),
                "Available RAM": self._format_bytes(mem.available),
                "Used RAM": self._format_bytes(mem.used),
                "RAM Usage": f"{mem.percent:.1f}%",
                "Total Swap": self._format_bytes(swap.total),
                "Used Swap": self._format_bytes(swap.used),
                "Swap Usage": f"{swap.percent:.1f}%",
            })
        else:
            # Fallback method
            try:
                with open("/proc/meminfo", "r") as f:
                    for line in f:
                        if "MemTotal:" in line:
                            total_kb = int(line.split()[1])
                            info["Total RAM"] = self._format_bytes(total_kb * 1024)
                        elif "MemAvailable:" in line:
                            avail_kb = int(line.split()[1])
                            info["Available RAM"] = self._format_bytes(avail_kb * 1024)
            except FileNotFoundError:
                info["Memory Info"] = "Unavailable"
                
        return info
    
    def get_disk_info(self) -> Dict[str, str]:
        """Get disk usage information."""
        info = {}
        
        if EXTENDED_INFO_AVAILABLE:
            # Get disk usage for root partition
            disk_usage = psutil.disk_usage('/')
            info.update({
                "Root Partition Total": self._format_bytes(disk_usage.total),
                "Root Partition Used": self._format_bytes(disk_usage.used),
                "Root Partition Free": self._format_bytes(disk_usage.free),
                "Root Partition Usage": f"{disk_usage.percent:.1f}%",
            })
            
            # Get all disk partitions
            partitions = psutil.disk_partitions()
            for i, partition in enumerate(partitions[:3]):  # Limit to first 3
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    # Shorten mountpoint display for better formatting
                    mount_display = partition.mountpoint
                    if len(mount_display) > 15:
                        mount_display = mount_display[:12] + "..."
                    
                    info[f"Mount {mount_display}"] = (
                        f"{self._format_bytes(usage.used)} / {self._format_bytes(usage.total)} "
                        f"({usage.percent:.1f}%)"
                    )
                except:
                    continue
        else:
            # Fallback method - get more detailed disk information
            try:
                # Get all mounted filesystems
                result = subprocess.run(
                    ["df", "-h"], 
                    capture_output=True, 
                    text=True, 
                    timeout=5
                )
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')[1:]  # Skip header
                    partition_count = 0
                    root_processed = False
                    
                    for line in lines:
                        fields = line.split()
                        if len(fields) >= 6:
                            filesystem = fields[0]
                            total = fields[1]
                            used = fields[2]
                            avail = fields[3]
                            use_percent = fields[4]
                            mountpoint = fields[5]
                            
                            # Skip special filesystems
                            if any(skip in filesystem for skip in ['/dev/loop', 'tmpfs', 'udev', 'devpts', 'sysfs', 'proc']):
                                continue
                            
                            # Handle root partition specially
                            if mountpoint == '/' and not root_processed:
                                info["Root Partition Total"] = total
                                info["Root Partition Used"] = used
                                info["Root Partition Free"] = avail
                                info["Root Partition Usage"] = use_percent
                                root_processed = True
                            else:
                                # Format mountpoint for display
                                if len(mountpoint) > 15:
                                    mount_display = mountpoint[:12] + "..."
                                else:
                                    mount_display = mountpoint
                                    
                                info[f"Mount {mount_display}"] = f"{used} / {total} ({use_percent})"
                            
                            partition_count += 1
                            if partition_count >= 4:  # Limit total partitions
                                break
                                
                if not info:
                    # Simple fallback
                    result = subprocess.run(
                        ["df", "-h", "/"], 
                        capture_output=True, 
                        text=True, 
                        timeout=5
                    )
                    if result.returncode == 0:
                        lines = result.stdout.strip().split('\n')
                        if len(lines) > 1:
                            fields = lines[1].split()
                            if len(fields) >= 5:
                                info["Root Partition"] = f"{fields[2]} / {fields[1]} ({fields[4]})"
            except:
                info["Disk Info"] = "Unavailable"
                
        return info
    
    def get_network_info(self) -> Dict[str, str]:
        """Get network interface information."""
        info = {}
        
        if EXTENDED_INFO_AVAILABLE:
            # Get network interfaces
            interfaces = psutil.net_if_addrs()
            for interface, addrs in interfaces.items():
                if interface != 'lo':  # Skip loopback
                    for addr in addrs:
                        if addr.family.name == 'AF_INET':  # IPv4
                            info[f"Interface {interface}"] = addr.address
                            
            # Get network stats
            try:
                stats = psutil.net_io_counters()
                info.update({
                    "Bytes Sent": self._format_bytes(stats.bytes_sent),
                    "Bytes Received": self._format_bytes(stats.bytes_recv),
                })
            except:
                pass
        else:
            # Fallback method
            try:
                result = subprocess.run(
                    ["hostname", "-I"], 
                    capture_output=True, 
                    text=True, 
                    timeout=5
                )
                if result.returncode == 0:
                    ips = result.stdout.strip().split()
                    for i, ip in enumerate(ips[:3]):  # Limit to first 3
                        info[f"IP Address {i+1}"] = ip
            except:
                info["Network Info"] = "Unavailable"
                
        return info
    
    def get_repository_sources(self) -> Dict[str, str]:
        """Get additional repository sources not covered by package managers."""
        sources = {}
        
        # Only add sources that aren't already covered in package manager info
        # This can be used for additional or custom repository sources
        
        return sources
    
    def get_all_info(self) -> Dict[str, Dict[str, str]]:
        """Get all system information."""
        return {
            "distribution": self.get_distribution_info(),
            "package_manager": self.get_package_manager_info(),
            "repository_sources": self.get_repository_sources(),
            "cpu": self.get_cpu_info(),
            "memory": self.get_memory_info(),
            "disk": self.get_disk_info(),
            "network": self.get_network_info(),
        }
    

    
    def _format_bytes(self, bytes_value: int) -> str:
        """Format bytes into human readable format using binary units."""
        for unit in ['B', 'KiB', 'MiB', 'GiB', 'TiB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} PiB"