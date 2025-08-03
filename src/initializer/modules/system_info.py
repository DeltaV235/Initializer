"""System information module for gathering and displaying system details."""

import platform
import subprocess
import shutil
from pathlib import Path
from typing import Dict, Any, Optional

try:
    import psutil
    import distro
    EXTENDED_INFO_AVAILABLE = True
except ImportError:
    EXTENDED_INFO_AVAILABLE = False

from ..config_manager import ConfigManager


class SystemInfoModule:
    """Module for gathering comprehensive system information."""
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.config = config_manager.get_modules_config().get("system_info", {})
        
    def get_distribution_info(self) -> Dict[str, str]:
        """Get Linux distribution information."""
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
        else:
            # Fallback method
            try:
                with open("/etc/os-release", "r") as f:
                    for line in f:
                        if line.startswith("PRETTY_NAME="):
                            info["Distribution"] = line.split("=")[1].strip().strip('"')
                            break
            except FileNotFoundError:
                info["Distribution"] = "Unknown"
                
        return info
    
    def get_package_manager_info(self) -> Dict[str, str]:
        """Detect available package managers."""
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
                    if pm == "apt":
                        result = subprocess.run(
                            ["apt", "--version"], 
                            capture_output=True, 
                            text=True, 
                            timeout=5
                        )
                    elif pm == "yum":
                        result = subprocess.run(
                            ["yum", "--version"], 
                            capture_output=True, 
                            text=True, 
                            timeout=5
                        )
                    elif pm == "pacman":
                        result = subprocess.run(
                            ["pacman", "--version"], 
                            capture_output=True, 
                            text=True, 
                            timeout=5
                        )
                    else:
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
                            version = version_line.split()[1] if len(version_line.split()) > 1 else "已安装"
                        elif pm == "pacman":
                            version = version_line.split()[2] if len(version_line.split()) > 2 else "已安装"
                        else:
                            version = version_line[:50]  # Limit length
                        detected[description] = f"✓ {version}"
                    else:
                        detected[description] = "✓ 已安装"
                        
                except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
                    detected[description] = "✓ 已检测到"
        
        # If no package managers detected, try to guess from the distribution
        if not detected:
            try:
                if Path("/etc/debian_version").exists():
                    detected["APT (Debian/Ubuntu)"] = "? 可能存在但未检测到"
                elif Path("/etc/redhat-release").exists():
                    detected["YUM/DNF (Red Hat)"] = "? 可能存在但未检测到"
                elif Path("/etc/arch-release").exists():
                    detected["Pacman (Arch)"] = "? 可能存在但未检测到"
                else:
                    detected["未知"] = "无可用包管理器"
            except Exception:
                detected["检测失败"] = "无法检测包管理器"
                    
        return detected
    
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
                    info[f"Partition {i+1} ({partition.mountpoint})"] = (
                        f"{self._format_bytes(usage.used)} / {self._format_bytes(usage.total)} "
                        f"({usage.percent:.1f}%)"
                    )
                except:
                    continue
        else:
            # Fallback method
            try:
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
    
    def get_all_info(self) -> Dict[str, Dict[str, str]]:
        """Get all system information."""
        return {
            "distribution": self.get_distribution_info(),
            "package_manager": self.get_package_manager_info(),
            "cpu": self.get_cpu_info(),
            "memory": self.get_memory_info(),
            "disk": self.get_disk_info(),
            "network": self.get_network_info(),
        }
    
    def get_quick_status(self) -> str:
        """Get a quick status summary for display."""
        lines = []
        
        try:
            # Distribution
            dist_info = self.get_distribution_info()
            os_name = dist_info.get('Distribution', 'Unknown')
            os_version = dist_info.get('Distro Version', '')
            if os_name == 'Unknown':
                os_name = dist_info.get('System', 'Linux')
            lines.append(f"OS: {os_name} {os_version}".strip())
            
            # Architecture
            arch = dist_info.get('Architecture', dist_info.get('Machine', 'Unknown'))
            lines.append(f"架构: {arch}")
            
            # CPU and Memory
            if EXTENDED_INFO_AVAILABLE:
                try:
                    cpu_count = psutil.cpu_count() or 'Unknown'
                    cpu_usage = psutil.cpu_percent(interval=0.1)
                    lines.append(f"CPU: {cpu_count} 核心 ({cpu_usage:.1f}% 使用中)")
                    
                    mem = psutil.virtual_memory()
                    mem_total = self._format_bytes(mem.total)
                    mem_used = self._format_bytes(mem.used)
                    lines.append(f"内存: {mem_used}/{mem_total} ({mem.percent:.1f}%)")
                    
                    disk_usage = psutil.disk_usage('/').percent
                    lines.append(f"磁盘: {disk_usage:.1f}% 使用中")
                except Exception as e:
                    lines.append(f"系统资源: 获取失败 ({str(e)[:30]})")
            else:
                # Fallback methods
                try:
                    # Try to get CPU info from /proc/cpuinfo
                    with open("/proc/cpuinfo", "r") as f:
                        cpu_lines = f.readlines()
                        cpu_count = len([line for line in cpu_lines if line.startswith("processor")])
                        lines.append(f"CPU: {cpu_count} 核心")
                        
                        # Try to get CPU model
                        for line in cpu_lines:
                            if "model name" in line:
                                model = line.split(":")[1].strip()
                                if len(model) > 40:
                                    model = model[:37] + "..."
                                lines.append(f"型号: {model}")
                                break
                except Exception:
                    lines.append("CPU: 信息无法获取")
                
                try:
                    # Try to get memory info from /proc/meminfo
                    with open("/proc/meminfo", "r") as f:
                        for line in f:
                            if "MemTotal:" in line:
                                total_kb = int(line.split()[1])
                                total_mb = total_kb // 1024
                                lines.append(f"内存: {total_mb} MB")
                                break
                except Exception:
                    lines.append("内存: 信息无法获取")
                
                try:
                    # Try to get disk info using df command
                    result = subprocess.run(
                        ["df", "-h", "/"], 
                        capture_output=True, 
                        text=True, 
                        timeout=5
                    )
                    if result.returncode == 0:
                        disk_lines = result.stdout.strip().split('\n')
                        if len(disk_lines) > 1:
                            fields = disk_lines[1].split()
                            if len(fields) >= 5:
                                lines.append(f"磁盘: {fields[2]}/{fields[1]} ({fields[4]})")
                except Exception:
                    lines.append("磁盘: 信息无法获取")
            
        except Exception as e:
            lines = [f"系统信息获取失败: {str(e)}"]
            
        return "\n".join(lines) if lines else "无系统信息可显示"
    
    def _format_bytes(self, bytes_value: int) -> str:
        """Format bytes into human readable format using binary units."""
        for unit in ['B', 'KiB', 'MiB', 'GiB', 'TiB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} PiB"