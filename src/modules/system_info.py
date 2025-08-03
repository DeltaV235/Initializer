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
            "apt": "Debian/Ubuntu APT",
            "yum": "Red Hat YUM",
            "dnf": "Fedora DNF", 
            "pacman": "Arch Pacman",
            "zypper": "openSUSE Zypper",
            "brew": "Homebrew",
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
                    version = result.stdout.split('\n')[0] if result.returncode == 0 else "Unknown"
                    detected[description] = version
                except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
                    detected[description] = "Detected (version unknown)"
                    
        return detected if detected else {"None": "No package managers detected"}
    
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
                            info["Model"] = line.split(":")[1].strip()
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
        
        # Distribution
        dist_info = self.get_distribution_info()
        lines.append(f"OS: {dist_info.get('Distribution', 'Unknown')} {dist_info.get('Distro Version', '')}")
        
        # CPU and Memory
        if EXTENDED_INFO_AVAILABLE:
            cpu_usage = psutil.cpu_percent(interval=0.1)
            mem_usage = psutil.virtual_memory().percent
            lines.append(f"CPU: {psutil.cpu_count()} cores ({cpu_usage:.1f}% used)")
            lines.append(f"Memory: {mem_usage:.1f}% used")
            
            disk_usage = psutil.disk_usage('/').percent
            lines.append(f"Disk: {disk_usage:.1f}% used")
        else:
            lines.append("CPU: Information unavailable")
            lines.append("Memory: Information unavailable")
            lines.append("Disk: Information unavailable")
            
        return "\n".join(lines)
    
    def _format_bytes(self, bytes_value: int) -> str:
        """Format bytes into human readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} PB"