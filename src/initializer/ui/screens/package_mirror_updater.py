"""
Package mirror updater module for handling APT mirror configuration updates.
Used for complete sources.list.d directory processing logic.
"""

import os
import re
import shutil
import subprocess
from typing import List, Tuple, Dict

from ...utils.logger import get_ui_logger

class PackageMirrorUpdater:
    """Package mirror updater for APT mirror configuration."""
    
    def __init__(self, new_mirror_url: str):
        self.new_mirror_url = new_mirror_url.rstrip('/')
        self.backup_suffix = ""
        self.logger = get_ui_logger("package_mirror_updater")

        # Log initialization
        self.logger.info(f"APT mirror processor initialized with URL: {new_mirror_url}")

    def _detect_main_sources_file(self) -> tuple[str, str]:
        """检测主要的APT源文件及其格式类型

        Returns:
            tuple[str, str]: (file_path, format_type)
            format_types: 'deb822' for .sources files, 'traditional' for .list files
        """
        self.logger.debug("Detecting main APT sources file")

        # 优先检查实际存在的文件，而不是依赖版本号

        # 1. 检查是否存在deb822格式的ubuntu.sources文件
        ubuntu_sources_path = "/etc/apt/sources.list.d/ubuntu.sources"
        if os.path.exists(ubuntu_sources_path):
            self.logger.info(f"Found deb822 format sources file: {ubuntu_sources_path}")
            return ubuntu_sources_path, "deb822"

        # 2. 检查传统的sources.list文件
        sources_list_path = "/etc/apt/sources.list"
        if os.path.exists(sources_list_path):
            self.logger.info(f"Found traditional sources file: {sources_list_path}")
            return sources_list_path, "traditional"

        # 3. 如果都不存在，返回默认的sources.list路径
        self.logger.warning(f"No sources file found, using default: {sources_list_path}")
        return sources_list_path, "traditional"
    
    def _update_sources_list_d_directory(self, backup_suffix: str) -> List[str]:
        """
        处理 sources.list.d 目录的核心逻辑

        这个函数的具体作用：
        1. 扫描 /etc/apt/sources.list.d/ 目录
        2. 识别可以替换镜像的文件
        3. 将其中的Ubuntu相关源替换为新镜像
        4. 保留第三方源不变
        """
        self.logger.info("Starting sources.list.d directory update")
        modified_files = []
        sources_d_path = "/etc/apt/sources.list.d"

        if not os.path.exists(sources_d_path):
            self.logger.warning(f"Sources directory does not exist: {sources_d_path}")
            return modified_files

        self.logger.debug(f"Scanning directory: {sources_d_path}")

        for filename in os.listdir(sources_d_path):
            if not filename.endswith(('.list', '.sources')):
                self.logger.debug(f"Skipping non-sources file: {filename}")
                continue

            file_path = os.path.join(sources_d_path, filename)
            self.logger.debug(f"Processing sources file: {filename}")

            # 读取文件内容
            try:
                with open(file_path, 'r') as f:
                    content = f.read()

                # 检查是否包含Ubuntu官方源
                if self._contains_ubuntu_sources(content):
                    self.logger.info(f"Found Ubuntu sources in file: {filename}")

                    # 备份原文件
                    backup_path = f"{file_path}.bak_{backup_suffix}"
                    shutil.copy2(file_path, backup_path)
                    self.logger.debug(f"Created backup: {backup_path}")

                    # 替换Ubuntu镜像URL
                    modified_content = self._replace_ubuntu_mirrors(content)

                    # 写回文件
                    with open(file_path, 'w') as f:
                        f.write(modified_content)

                    modified_files.append(filename)
                    self.logger.info(f"Successfully updated mirror sources in: {filename}")
                else:
                    self.logger.debug(f"No Ubuntu sources found in: {filename}")

            except Exception as e:
                self.logger.error(f"Error processing file {filename}: {e}")

        self.logger.info(f"Sources.list.d update completed. Modified {len(modified_files)} files: {modified_files}")
        return modified_files
    
    def _contains_ubuntu_sources(self, content: str) -> bool:
        """
        检查文件是否包含Ubuntu官方源
        
        需要替换镜像的源：
        - archive.ubuntu.com
        - security.ubuntu.com  
        - ports.ubuntu.com (ARM架构)
        """
        ubuntu_domains = [
            'archive.ubuntu.com',
            'security.ubuntu.com',
            'ports.ubuntu.com',
            # 一些地区镜像也可能需要替换
            r'\w+\.archive\.ubuntu\.com',
        ]
        
        for domain in ubuntu_domains:
            if re.search(domain, content):
                return True
        return False
    
    def _replace_ubuntu_mirrors(self, content: str) -> str:
        """
        替换Ubuntu镜像URL的具体逻辑
        
        处理两种格式：
        1. 传统格式: deb http://archive.ubuntu.com/ubuntu/ focal main
        2. deb822格式: URIs: http://archive.ubuntu.com/ubuntu/
        """
        
        # 1. 处理传统deb行格式
        content = re.sub(
            r'deb(-src)?\s+(https?://[^/]*\.?ubuntu\.com/[^\s]*)',
            rf'deb\1 {self.new_mirror_url}',
            content
        )
        
        # 2. 处理deb822格式的URIs行
        content = re.sub(
            r'(URIs:\s*)(https?://[^/]*\.?ubuntu\.com/[^\s]*)',
            rf'\1{self.new_mirror_url}',
            content
        )
        
        return content

    def process_complete_mirror_change(self, backup_suffix: str) -> Dict[str, List[str]]:
        """
        完整的镜像源更换流程 - 基于实际文件存在情况
        """
        self.logger.info(f"Starting complete mirror change process with backup suffix: {backup_suffix}")
        self.backup_suffix = backup_suffix
        result = {
            'modified_main': [],
            'modified_sources_d': [],
            'skipped_third_party': []
        }

        # 1. 检测并处理主配置文件
        self.logger.info("Processing main sources configuration file")
        main_file_path, file_format = self._detect_main_sources_file()

        if file_format == "deb822":
            self.logger.info("Processing deb822 format (ubuntu.sources)")
            if self._update_ubuntu_sources_deb822(backup_suffix):
                result['modified_main'].append('ubuntu.sources')
                self.logger.info("Successfully updated ubuntu.sources")
            else:
                self.logger.warning("Failed to update ubuntu.sources")
        else:  # traditional format
            self.logger.info("Processing traditional format (sources.list)")
            if self._update_sources_list_traditional(backup_suffix):
                result['modified_main'].append('sources.list')
                self.logger.info("Successfully updated sources.list")
            else:
                self.logger.warning("Failed to update sources.list")

        # 2. 处理 sources.list.d 目录 - 这是关键步骤！
        self.logger.info("Processing sources.list.d directory")
        result['modified_sources_d'] = self._update_sources_list_d_directory(backup_suffix)

        self.logger.info(f"Mirror change process completed. Results: {result}")
        return result
        
    def _update_ubuntu_sources_deb822(self, backup_suffix: str) -> bool:
        """处理Ubuntu 24.04+的deb822格式"""
        ubuntu_sources_path = "/etc/apt/sources.list.d/ubuntu.sources"

        if not os.path.exists(ubuntu_sources_path):
            self.logger.warning(f"Ubuntu sources file not found: {ubuntu_sources_path}")
            return False

        self.logger.debug(f"Processing deb822 format file: {ubuntu_sources_path}")

        try:
            # 备份原文件
            backup_path = f"{ubuntu_sources_path}.bak_{backup_suffix}"
            shutil.copy2(ubuntu_sources_path, backup_path)
            self.logger.debug(f"Created backup: {backup_path}")

            # 读取并修改内容
            with open(ubuntu_sources_path, 'r') as f:
                content = f.read()

            self.logger.debug(f"Original content length: {len(content)} characters")

            # 替换URIs行
            modified_content = re.sub(
                r'(URIs:\s*)(https?://[^/]*\.?ubuntu\.com/[^\s]*)',
                rf'\1{self.new_mirror_url}/ubuntu/',
                content
            )

            self.logger.debug(f"Modified content length: {len(modified_content)} characters")

            # 写回文件
            with open(ubuntu_sources_path, 'w') as f:
                f.write(modified_content)

            self.logger.info(f"Successfully updated deb822 sources with new mirror: {self.new_mirror_url}")
            return True

        except Exception as e:
            self.logger.error(f"Error processing ubuntu.sources: {e}")
            return False

    def _update_sources_list_traditional(self, backup_suffix: str) -> bool:
        """处理传统sources.list格式"""
        sources_path = "/etc/apt/sources.list"

        if not os.path.exists(sources_path):
            self.logger.warning(f"Traditional sources file not found: {sources_path}")
            return False

        self.logger.debug(f"Processing traditional format file: {sources_path}")

        try:
            # 备份原文件
            backup_path = f"{sources_path}.bak_{backup_suffix}"
            shutil.copy2(sources_path, backup_path)
            self.logger.debug(f"Created backup: {backup_path}")

            # 获取发行版代号
            codename = self._get_distribution_codename()
            self.logger.debug(f"Detected distribution codename: {codename}")

            # 生成新的sources.list内容
            new_content = self._generate_sources_list_content(codename)
            self.logger.debug(f"Generated new sources.list content: {len(new_content)} characters")

            # 写入文件
            with open(sources_path, 'w') as f:
                f.write(new_content)

            self.logger.info(f"Successfully updated traditional sources.list with new mirror: {self.new_mirror_url}")
            return True

        except Exception as e:
            self.logger.error(f"Error processing sources.list: {e}")
            return False
    
    def _get_distribution_codename(self) -> str:
        """获取Ubuntu发行版代号"""
        try:
            result = subprocess.run(
                ["lsb_release", "-cs"],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except:
            return "focal"  # 默认fallback
    
    def _generate_sources_list_content(self, codename: str) -> str:
        """生成标准的sources.list内容"""
        base_url = f"{self.new_mirror_url}/ubuntu"
        
        content = f"""# Ubuntu {codename} - Generated by Linux System Initializer
deb {base_url} {codename} main restricted universe multiverse
deb {base_url} {codename}-updates main restricted universe multiverse
deb {base_url} {codename}-backports main restricted universe multiverse
deb {base_url} {codename}-security main restricted universe multiverse

# Source packages (uncomment if needed)
# deb-src {base_url} {codename} main restricted universe multiverse
# deb-src {base_url} {codename}-updates main restricted universe multiverse
# deb-src {base_url} {codename}-backports main restricted universe multiverse
# deb-src {base_url} {codename}-security main restricted universe multiverse
"""
        return content
    
    def get_affected_files_list(self) -> List[str]:
        """获取会被影响的文件列表（用于确认页面显示）"""
        affected_files = []
        
        # 检查主配置文件 - 基于实际存在的文件
        main_file_path, file_format = self._detect_main_sources_file()
        
        if os.path.exists(main_file_path):
            if file_format == "deb822":
                affected_files.append('/etc/apt/sources.list.d/ubuntu.sources')
            else:
                affected_files.append('/etc/apt/sources.list')
        
        # sources.list.d目录中的Ubuntu相关文件
        sources_d_path = "/etc/apt/sources.list.d"
        if os.path.exists(sources_d_path):
            ubuntu_files = []
            for filename in os.listdir(sources_d_path):
                if not filename.endswith(('.list', '.sources')) or filename == 'ubuntu.sources':
                    continue
                    
                file_path = os.path.join(sources_d_path, filename)
                try:
                    with open(file_path, 'r') as f:
                        content = f.read()
                    if self._contains_ubuntu_sources(content):
                        ubuntu_files.append(filename)
                except:
                    continue
            
            if ubuntu_files:
                affected_files.append(f"/etc/apt/sources.list.d/ ({len(ubuntu_files)} Ubuntu-related files)")
        
        return affected_files