"""Package manager detection and source management module."""

import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import Optional, Dict, List, Tuple
from pathlib import Path
from datetime import datetime


@dataclass
class PackageManager:
    """Package manager information."""
    name: str
    command: str
    current_source: Optional[str] = None
    available: bool = False


class PackageManagerDetector:
    """Detect and manage system package managers."""
    
    MIRROR_SOURCES = {
        "apt": {
            "default": "http://archive.ubuntu.com/ubuntu/",
            "aliyun": "http://mirrors.aliyun.com/ubuntu/",
            "tuna": "https://mirrors.tuna.tsinghua.edu.cn/ubuntu/",
            "ustc": "http://mirrors.ustc.edu.cn/ubuntu/",
            "163": "http://mirrors.163.com/ubuntu/",
            "huawei": "https://repo.huaweicloud.com/ubuntu/",
            "sohu": "http://mirrors.sohu.com/ubuntu/",
            "tencent": "http://mirrors.cloud.tencent.com/ubuntu/",
            "bfsu": "https://mirrors.bfsu.edu.cn/ubuntu/",
            "nju": "https://mirror.nju.edu.cn/ubuntu/",
            "sjtu": "https://mirror.sjtu.edu.cn/ubuntu/",
            "zju": "http://mirrors.zju.edu.cn/ubuntu/",
            "hit": "http://mirrors.hit.edu.cn/ubuntu/",
            "neu": "http://mirror.neu.edu.cn/ubuntu/",
            "bit": "http://mirror.bit.edu.cn/ubuntu/",
            "cqu": "http://mirrors.cqu.edu.cn/ubuntu/",
            "bjtu": "https://mirror.bjtu.edu.cn/ubuntu/",
            "bupt": "http://mirrors.bupt.edu.cn/ubuntu/",
        },
        "yum": {
            "default": "http://mirror.centos.org/centos/",
            "aliyun": "http://mirrors.aliyun.com/centos/",
            "tuna": "https://mirrors.tuna.tsinghua.edu.cn/centos/",
            "ustc": "http://mirrors.ustc.edu.cn/centos/",
            "163": "http://mirrors.163.com/centos/",
            "huawei": "https://repo.huaweicloud.com/centos/",
        },
        "dnf": {
            "default": "http://download.fedoraproject.org/pub/fedora/",
            "aliyun": "http://mirrors.aliyun.com/fedora/",
            "tuna": "https://mirrors.tuna.tsinghua.edu.cn/fedora/",
            "ustc": "http://mirrors.ustc.edu.cn/fedora/",
            "163": "http://mirrors.163.com/fedora/",
        },
        "pacman": {
            "default": "https://archlinux.org/mirrorlist/",
            "aliyun": "Server = http://mirrors.aliyun.com/archlinux/$repo/os/$arch",
            "tuna": "Server = https://mirrors.tuna.tsinghua.edu.cn/archlinux/$repo/os/$arch",
            "ustc": "Server = http://mirrors.ustc.edu.cn/archlinux/$repo/os/$arch",
            "163": "Server = http://mirrors.163.com/archlinux/$repo/os/$arch",
        },
        "zypper": {
            "default": "http://download.opensuse.org/",
            "aliyun": "http://mirrors.aliyun.com/opensuse/",
            "tuna": "https://mirrors.tuna.tsinghua.edu.cn/opensuse/",
            "ustc": "http://mirrors.ustc.edu.cn/opensuse/",
        },
        "brew": {
            "default": "https://github.com/Homebrew/brew.git",
            "tuna": "https://mirrors.tuna.tsinghua.edu.cn/git/homebrew/brew.git",
            "ustc": "https://mirrors.ustc.edu.cn/brew.git",
            "aliyun": "https://mirrors.aliyun.com/homebrew/brew.git",
        },
        "apk": {
            "default": "http://dl-cdn.alpinelinux.org/alpine/",
            "aliyun": "http://mirrors.aliyun.com/alpine/",
            "tuna": "https://mirrors.tuna.tsinghua.edu.cn/alpine/",
            "ustc": "http://mirrors.ustc.edu.cn/alpine/",
        }
    }
    
    def __init__(self):
        self.package_managers = self._detect_package_managers()
    
    def _detect_package_managers(self) -> List[PackageManager]:
        """Detect available package managers on the system."""
        managers = []
        
        # Common package managers to check
        pm_commands = [
            ("apt", "apt-get"),
            ("yum", "yum"),
            ("dnf", "dnf"),
            ("pacman", "pacman"),
            ("zypper", "zypper"),
            ("brew", "brew"),
            ("apk", "apk"),
            ("snap", "snap"),
            ("flatpak", "flatpak"),
        ]
        
        for name, command in pm_commands:
            if shutil.which(command):
                pm = PackageManager(
                    name=name,
                    command=command,
                    available=True,
                    current_source=self._get_current_source(name)
                )
                managers.append(pm)
        
        return managers
    
    def _get_current_source(self, pm_name: str) -> Optional[str]:
        """Get the current source/mirror for a package manager."""
        try:
            if pm_name == "apt":
                sources_file = "/etc/apt/sources.list"
                if os.path.exists(sources_file):
                    with open(sources_file, 'r') as f:
                        for line in f:
                            if line.strip() and not line.startswith('#'):
                                # Extract the URL from the line
                                parts = line.split()
                                if len(parts) >= 2 and parts[0] == 'deb':
                                    return parts[1]
                                    
            elif pm_name == "yum":
                # Check CentOS repo files
                repo_dir = "/etc/yum.repos.d/"
                if os.path.exists(repo_dir):
                    for repo_file in Path(repo_dir).glob("*.repo"):
                        with open(repo_file, 'r') as f:
                            for line in f:
                                if line.startswith('baseurl='):
                                    return line.split('=', 1)[1].strip()
                                    
            elif pm_name == "dnf":
                # Similar to yum
                repo_dir = "/etc/yum.repos.d/"
                if os.path.exists(repo_dir):
                    for repo_file in Path(repo_dir).glob("*.repo"):
                        with open(repo_file, 'r') as f:
                            for line in f:
                                if line.startswith('baseurl='):
                                    return line.split('=', 1)[1].strip()
                                    
            elif pm_name == "pacman":
                mirrorlist = "/etc/pacman.d/mirrorlist"
                if os.path.exists(mirrorlist):
                    with open(mirrorlist, 'r') as f:
                        for line in f:
                            if line.startswith('Server ='):
                                return line.split('=', 1)[1].strip()
                                
            elif pm_name == "brew":
                # Check Homebrew remote
                result = subprocess.run(
                    ["git", "-C", "/usr/local/Homebrew", "remote", "get-url", "origin"],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    return result.stdout.strip()
                    
            elif pm_name == "apk":
                repos_file = "/etc/apk/repositories"
                if os.path.exists(repos_file):
                    with open(repos_file, 'r') as f:
                        for line in f:
                            if line.strip() and not line.startswith('#'):
                                return line.strip()
                                
        except Exception:
            pass
            
        return None
    
    def get_primary_package_manager(self) -> Optional[PackageManager]:
        """Get the primary package manager for the system."""
        # Priority order for primary package manager
        priority = ["apt", "yum", "dnf", "pacman", "zypper", "apk", "brew"]
        
        for pm_name in priority:
            for pm in self.package_managers:
                if pm.name == pm_name:
                    return pm
        
        # Return first available if none in priority list
        return self.package_managers[0] if self.package_managers else None
    
    def get_available_mirrors(self, pm_name: str) -> Dict[str, str]:
        """Get available mirror sources for a package manager."""
        return self.MIRROR_SOURCES.get(pm_name, {})
    
    def change_mirror(self, pm_name: str, mirror_url: str, backup_suffix: Optional[str] = None) -> Tuple[bool, str]:
        """Change the mirror source for a package manager.
        
        Args:
            pm_name: Package manager name
            mirror_url: New mirror URL
            backup_suffix: Optional backup suffix (if None, will generate timestamp)
        
        Returns:
            Tuple of (success, message)
        """
        if backup_suffix is None:
            backup_suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
            
        try:
            if pm_name == "apt":
                # Backup current sources.list
                sources_file = "/etc/apt/sources.list"
                backup_file = f"{sources_file}.bak_{backup_suffix}"
                
                if os.path.exists(sources_file):
                    shutil.copy2(sources_file, backup_file)
                
                # Write new sources.list
                # This is a simplified example - real implementation would need proper parsing
                with open(sources_file, 'w') as f:
                    # Detect distribution codename
                    codename = subprocess.run(
                        ["lsb_release", "-cs"],
                        capture_output=True,
                        text=True
                    ).stdout.strip()
                    
                    f.write(f"deb {mirror_url} {codename} main restricted universe multiverse\n")
                    f.write(f"deb {mirror_url} {codename}-updates main restricted universe multiverse\n")
                    f.write(f"deb {mirror_url} {codename}-backports main restricted universe multiverse\n")
                    f.write(f"deb {mirror_url} {codename}-security main restricted universe multiverse\n")
                
                # Update package index using apt instead of apt-get
                subprocess.run(["apt", "update"], check=True)
                return True, f"Successfully changed APT mirror to {mirror_url}"
                
            elif pm_name == "brew":
                # Change Homebrew repository remote
                brew_repo = "/usr/local/Homebrew"
                config_file = f"{brew_repo}/.git/config"
                backup_file = f"{config_file}.bak_{backup_suffix}"
                
                # Backup git config if it exists
                if os.path.exists(config_file):
                    shutil.copy2(config_file, backup_file)
                
                if os.path.exists(brew_repo):
                    subprocess.run(
                        ["git", "-C", brew_repo, "remote", "set-url", "origin", mirror_url],
                        check=True
                    )
                    return True, f"Successfully changed Homebrew mirror to {mirror_url}"
                else:
                    return False, "Homebrew repository not found"
                    
            # Add more package manager implementations as needed
            else:
                return False, f"Mirror change not implemented for {pm_name}"
                
        except Exception as e:
            return False, f"Failed to change mirror: {str(e)}"