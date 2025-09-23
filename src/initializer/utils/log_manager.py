"""Installation Log Manager for the Linux System Initializer."""

import os
import json
import yaml
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class LogLevel(Enum):
    """Log level enumeration."""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    SUCCESS = "SUCCESS"
    DEBUG = "DEBUG"


@dataclass
class LogEntry:
    """Represents a single log entry."""
    timestamp: str
    level: LogLevel
    message: str
    command: Optional[str] = None
    output: Optional[str] = None
    error: Optional[str] = None
    application: Optional[str] = None
    action: Optional[str] = None  # install, uninstall, retry


@dataclass
class InstallationSession:
    """Represents a complete installation session."""
    session_id: str
    start_time: str
    end_time: Optional[str] = None
    total_apps: int = 0
    successful_apps: int = 0
    failed_apps: int = 0
    package_manager: Optional[str] = None
    system_info: Optional[Dict[str, Any]] = None
    log_entries: List[LogEntry] = None

    def __post_init__(self):
        if self.log_entries is None:
            self.log_entries = []


class InstallationLogManager:
    """Manages installation logs and provides export functionality."""

    def __init__(self, config_dir: Path = Path("config")):
        """Initialize the log manager.

        Args:
            config_dir: Configuration directory path
        """
        self.config_dir = config_dir
        self.logs_dir = config_dir / "logs"
        self.logs_dir.mkdir(exist_ok=True)

        # Current session
        self.current_session: Optional[InstallationSession] = None

        # Log file paths
        self.current_log_file = None

    def start_session(self, package_manager: str, system_info: Dict[str, Any] = None) -> str:
        """Start a new installation session.

        Args:
            package_manager: Package manager being used
            system_info: System information dictionary

        Returns:
            Session ID
        """
        timestamp = datetime.now()
        session_id = timestamp.strftime("%Y%m%d_%H%M%S")

        self.current_session = InstallationSession(
            session_id=session_id,
            start_time=timestamp.isoformat(),
            package_manager=package_manager,
            system_info=system_info or {}
        )

        # Create log file for this session
        self.current_log_file = self.logs_dir / f"install_session_{session_id}.json"

        self.log(LogLevel.INFO, f"安装会话开始 - 包管理器: {package_manager}")

        return session_id

    def end_session(self) -> None:
        """End the current installation session."""
        if not self.current_session:
            return

        self.current_session.end_time = datetime.now().isoformat()

        # Calculate statistics
        success_count = sum(1 for entry in self.current_session.log_entries
                          if entry.level == LogLevel.SUCCESS and entry.action in ["install", "uninstall"])

        self.current_session.successful_apps = success_count
        self.current_session.failed_apps = self.current_session.total_apps - success_count

        self.log(LogLevel.INFO,
                f"安装会话结束 - 成功: {self.current_session.successful_apps}, "
                f"失败: {self.current_session.failed_apps}")

        # Save final session data
        self._save_session()

        self.current_session = None
        self.current_log_file = None

    def log(self, level: LogLevel, message: str, command: str = None,
            output: str = None, error: str = None, application: str = None,
            action: str = None) -> None:
        """Add a log entry to the current session.

        Args:
            level: Log level
            message: Log message
            command: Command that was executed
            output: Command output
            error: Error message if any
            application: Application name
            action: Action performed (install/uninstall/retry)
        """
        if not self.current_session:
            return

        entry = LogEntry(
            timestamp=datetime.now().isoformat(),
            level=level,
            message=message,
            command=command,
            output=output,
            error=error,
            application=application,
            action=action
        )

        self.current_session.log_entries.append(entry)

        # Auto-save every few entries to prevent data loss
        if len(self.current_session.log_entries) % 10 == 0:
            self._save_session()

    def set_total_apps(self, count: int) -> None:
        """Set the total number of applications to be processed.

        Args:
            count: Total application count
        """
        if self.current_session:
            self.current_session.total_apps = count

    def _save_session(self) -> None:
        """Save the current session to file."""
        if not self.current_session or not self.current_log_file:
            return

        try:
            # Convert to dictionary for JSON serialization
            session_dict = asdict(self.current_session)

            # Convert LogLevel enums to strings
            for entry in session_dict["log_entries"]:
                entry["level"] = entry["level"].value

            with open(self.current_log_file, 'w', encoding='utf-8') as f:
                json.dump(session_dict, f, indent=2, ensure_ascii=False)

        except Exception as e:
            print(f"保存日志会话失败: {e}")

    def export_logs(self, session_id: str = None, format: str = "json",
                   output_file: str = None) -> str:
        """Export logs to specified format.

        Args:
            session_id: Session ID to export (current session if None)
            format: Export format ('json', 'yaml', 'txt', 'html')
            output_file: Output file path (auto-generated if None)

        Returns:
            Path to exported file
        """
        # Get session data
        if session_id is None and self.current_session:
            session_data = asdict(self.current_session)
            session_id = self.current_session.session_id
        else:
            session_data = self._load_session(session_id)

        if not session_data:
            raise ValueError(f"会话 {session_id} 未找到")

        # Convert LogLevel enums to strings if needed
        if "log_entries" in session_data:
            for entry in session_data["log_entries"]:
                if isinstance(entry.get("level"), LogLevel):
                    entry["level"] = entry["level"].value

        # Generate output filename if not provided
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self.logs_dir / f"install_log_{session_id}_{timestamp}.{format}"
        else:
            output_file = Path(output_file)

        # Export based on format
        if format.lower() == "json":
            return self._export_json(session_data, output_file)
        elif format.lower() == "yaml":
            return self._export_yaml(session_data, output_file)
        elif format.lower() == "txt":
            return self._export_txt(session_data, output_file)
        elif format.lower() == "html":
            return self._export_html(session_data, output_file)
        else:
            raise ValueError(f"不支持的导出格式: {format}")

    def _load_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load a session from file.

        Args:
            session_id: Session ID to load

        Returns:
            Session data dictionary or None if not found
        """
        log_file = self.logs_dir / f"install_session_{session_id}.json"

        if not log_file.exists():
            return None

        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载日志会话失败: {e}")
            return None

    def _export_json(self, session_data: Dict[str, Any], output_file: Path) -> str:
        """Export session data to JSON format."""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)
        return str(output_file)

    def _export_yaml(self, session_data: Dict[str, Any], output_file: Path) -> str:
        """Export session data to YAML format."""
        with open(output_file, 'w', encoding='utf-8') as f:
            yaml.dump(session_data, f, default_flow_style=False,
                     allow_unicode=True, indent=2)
        return str(output_file)

    def _export_txt(self, session_data: Dict[str, Any], output_file: Path) -> str:
        """Export session data to human-readable text format."""
        with open(output_file, 'w', encoding='utf-8') as f:
            # Header
            f.write("=" * 60 + "\n")
            f.write("Linux 系统初始化器 - 安装日志\n")
            f.write("=" * 60 + "\n\n")

            # Session info
            f.write(f"会话 ID: {session_data['session_id']}\n")
            f.write(f"开始时间: {session_data['start_time']}\n")
            if session_data.get('end_time'):
                f.write(f"结束时间: {session_data['end_time']}\n")
            f.write(f"包管理器: {session_data.get('package_manager', '未知')}\n")
            f.write(f"总应用数: {session_data.get('total_apps', 0)}\n")
            f.write(f"成功数: {session_data.get('successful_apps', 0)}\n")
            f.write(f"失败数: {session_data.get('failed_apps', 0)}\n\n")

            # System info
            if session_data.get('system_info'):
                f.write("系统信息:\n")
                f.write("-" * 30 + "\n")
                for key, value in session_data['system_info'].items():
                    f.write(f"{key}: {value}\n")
                f.write("\n")

            # Log entries
            f.write("安装日志:\n")
            f.write("-" * 30 + "\n")

            for entry in session_data.get('log_entries', []):
                timestamp = entry['timestamp']
                level = entry['level']
                message = entry['message']

                f.write(f"[{timestamp}] [{level}] {message}\n")

                if entry.get('application'):
                    f.write(f"  应用: {entry['application']}\n")
                if entry.get('action'):
                    f.write(f"  操作: {entry['action']}\n")
                if entry.get('command'):
                    f.write(f"  命令: {entry['command']}\n")
                if entry.get('output'):
                    f.write(f"  输出: {entry['output'][:200]}...\n")
                if entry.get('error'):
                    f.write(f"  错误: {entry['error']}\n")
                f.write("\n")

        return str(output_file)

    def _export_html(self, session_data: Dict[str, Any], output_file: Path) -> str:
        """Export session data to HTML format."""
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>安装日志 - {session_data['session_id']}</title>
    <style>
        body {{ font-family: 'Arial', sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .header {{ border-bottom: 2px solid #007acc; padding-bottom: 15px; margin-bottom: 20px; }}
        .session-info {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px; }}
        .info-card {{ background: #f8f9fa; padding: 15px; border-radius: 6px; border-left: 4px solid #007acc; }}
        .log-entry {{ margin-bottom: 15px; padding: 15px; border-radius: 6px; border-left: 4px solid #ddd; }}
        .level-INFO {{ border-left-color: #17a2b8; background: #e1f7fd; }}
        .level-SUCCESS {{ border-left-color: #28a745; background: #d4edda; }}
        .level-WARNING {{ border-left-color: #ffc107; background: #fff3cd; }}
        .level-ERROR {{ border-left-color: #dc3545; background: #f8d7da; }}
        .timestamp {{ color: #6c757d; font-size: 0.9em; }}
        .command {{ background: #f8f9fa; padding: 8px; border-radius: 4px; font-family: monospace; margin: 5px 0; }}
        .output {{ background: #f1f3f4; padding: 8px; border-radius: 4px; font-family: monospace; margin: 5px 0; max-height: 100px; overflow-y: auto; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Linux 系统初始化器 - 安装日志</h1>
            <h2>会话 ID: {session_data['session_id']}</h2>
        </div>

        <div class="session-info">
            <div class="info-card">
                <h3>⏰ 时间信息</h3>
                <p><strong>开始:</strong> {session_data['start_time']}</p>
                {'<p><strong>结束:</strong> ' + session_data['end_time'] + '</p>' if session_data.get('end_time') else ''}
            </div>
            <div class="info-card">
                <h3>📊 统计信息</h3>
                <p><strong>总应用:</strong> {session_data.get('total_apps', 0)}</p>
                <p><strong>成功:</strong> <span style="color: #28a745;">{session_data.get('successful_apps', 0)}</span></p>
                <p><strong>失败:</strong> <span style="color: #dc3545;">{session_data.get('failed_apps', 0)}</span></p>
            </div>
            <div class="info-card">
                <h3>🔧 系统信息</h3>
                <p><strong>包管理器:</strong> {session_data.get('package_manager', '未知')}</p>
        """

        # Add system info if available
        if session_data.get('system_info'):
            for key, value in list(session_data['system_info'].items())[:3]:  # Show first 3 items
                html_content += f"<p><strong>{key}:</strong> {value}</p>"

        html_content += """
            </div>
        </div>

        <h3>📝 详细日志</h3>
        """

        # Add log entries
        for entry in session_data.get('log_entries', []):
            level = entry['level']
            html_content += f"""
        <div class="log-entry level-{level}">
            <div class="timestamp">{entry['timestamp']}</div>
            <strong>[{level}]</strong> {entry['message']}
            """

            if entry.get('application'):
                html_content += f"<br><strong>应用:</strong> {entry['application']}"
            if entry.get('action'):
                html_content += f" <strong>操作:</strong> {entry['action']}"
            if entry.get('command'):
                html_content += f'<div class="command">命令: {entry["command"]}</div>'
            if entry.get('output'):
                output = entry['output'][:500]  # Limit output length
                html_content += f'<div class="output">输出: {output}{"..." if len(entry["output"]) > 500 else ""}</div>'
            if entry.get('error'):
                html_content += f'<div class="output" style="background: #f8d7da;">错误: {entry["error"]}</div>'

            html_content += "</div>"

        html_content += """
    </div>
</body>
</html>
        """

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

        return str(output_file)

    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all available log sessions.

        Returns:
            List of session summary dictionaries
        """
        sessions = []

        for log_file in self.logs_dir.glob("install_session_*.json"):
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)

                sessions.append({
                    'session_id': session_data['session_id'],
                    'start_time': session_data['start_time'],
                    'end_time': session_data.get('end_time'),
                    'package_manager': session_data.get('package_manager'),
                    'total_apps': session_data.get('total_apps', 0),
                    'successful_apps': session_data.get('successful_apps', 0),
                    'failed_apps': session_data.get('failed_apps', 0),
                    'log_entries_count': len(session_data.get('log_entries', []))
                })

            except Exception as e:
                print(f"加载会话文件 {log_file} 失败: {e}")

        # Sort by start time (newest first)
        sessions.sort(key=lambda x: x['start_time'], reverse=True)
        return sessions

    def cleanup_old_logs(self, keep_days: int = 30) -> int:
        """Clean up old log files.

        Args:
            keep_days: Number of days to keep logs

        Returns:
            Number of files deleted
        """
        cutoff_time = datetime.now().timestamp() - (keep_days * 24 * 60 * 60)
        deleted_count = 0

        for log_file in self.logs_dir.glob("install_session_*.json"):
            try:
                if log_file.stat().st_mtime < cutoff_time:
                    log_file.unlink()
                    deleted_count += 1
            except Exception as e:
                print(f"删除日志文件 {log_file} 失败: {e}")

        return deleted_count