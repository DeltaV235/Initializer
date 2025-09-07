"""Mirror Confirmation Modal for Package Manager."""

import os
import shutil
import subprocess
from datetime import datetime
from textual import on, work
from textual.app import ComposeResult
from textual.containers import Container, Vertical, ScrollableContainer
from textual.screen import ModalScreen
from textual.widgets import Button, Static, Rule, Label
from typing import Callable, Optional, List

from ...modules.package_manager import PackageManagerDetector


class MirrorConfirmationModal(ModalScreen):
    """Modal screen for confirming mirror source change."""
    
    BINDINGS = [
        ("escape", "cancel_operation", "Cancel"),
        ("enter", "confirm_change", "Confirm"),
        ("y", "confirm_change", "Yes"),
        ("n", "cancel_operation", "No"),
        ("j", "scroll_down", "Scroll Down"),
        ("k", "scroll_up", "Scroll Up"),
        ("down", "scroll_down", "Scroll Down"),
        ("up", "scroll_up", "Scroll Up"),
        ("pagedown", "scroll_page_down", "Page Down"),
        ("pageup", "scroll_page_up", "Page Up"),
    ]
    
    def __init__(self, package_manager, new_source: str, callback: Callable[[bool, str], None]):
        super().__init__()
        self.package_manager = package_manager
        self.new_source = new_source
        self.callback = callback
        self.detector = PackageManagerDetector()
        
        # State management
        self.is_executing = False
        
        # Files that will be affected
        self.affected_files = self._get_affected_files()
        
    def _get_affected_files(self) -> List[str]:
        """Get list of files that will be modified."""
        files = []
        
        if self.package_manager.name == "apt":
            files.extend([
                "/etc/apt/sources.list",
                "/etc/apt/sources.list.d/ (directory contents)"
            ])
        elif self.package_manager.name == "yum":
            files.extend([
                "/etc/yum.repos.d/ (repo files)"
            ])
        elif self.package_manager.name == "dnf":
            files.extend([
                "/etc/yum.repos.d/ (repo files)"
            ])
        elif self.package_manager.name == "pacman":
            files.extend([
                "/etc/pacman.d/mirrorlist"
            ])
        elif self.package_manager.name == "brew":
            files.extend([
                "/usr/local/Homebrew/.git/config",
                "Homebrew repository remote URL"
            ])
        elif self.package_manager.name == "apk":
            files.extend([
                "/etc/apk/repositories"
            ])
        
        return files
    
    def compose(self) -> ComposeResult:
        """Compose the confirmation interface."""
        with Container(id="confirmation-container"):
            yield Static(f"Confirm Mirror Change - {self.package_manager.name.upper()}", id="confirmation-title")
            yield Rule()
            
            with ScrollableContainer(id="confirmation-content"):
                # Warning message
                yield Label("⚠️  Mirror Source Change Confirmation", classes="warning-title")
                yield Rule()
                
                # Current and new source info
                yield Label("Current Source:", classes="info-key")
                current = self.package_manager.current_source or "Not configured"
                if len(current) > 80:
                    current = current[:77] + "..."
                yield Static(f"  {current}", classes="current-source")
                
                yield Label("New Source:", classes="info-key")
                new = self.new_source
                if len(new) > 80:
                    new = new[:77] + "..."
                yield Static(f"  {new}", classes="new-source")
                
                yield Rule()
                
                # Files to be modified
                yield Label("Files that will be modified:", classes="info-key")
                for file_path in self.affected_files:
                    yield Static(f"  • {file_path}", classes="file-item")
                
                yield Rule()
                
                # Backup information
                yield Label("Backup Information:", classes="info-key")
                backup_time = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
                backup_suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
                yield Static(f"  • Backup date: {backup_time}", classes="backup-info")
                yield Static(f"  • Backup suffix: .bak_{backup_suffix}", classes="backup-info")
                
                # Show specific backup file examples
                if self.package_manager.name == "apt":
                    yield Static(f"  • Example: /etc/apt/sources.list.bak_{backup_suffix}", classes="backup-info")
                elif self.package_manager.name == "brew":
                    yield Static(f"  • Example: /usr/local/Homebrew/.git/config.bak_{backup_suffix}", classes="backup-info")
                elif self.package_manager.name in ["yum", "dnf"]:
                    yield Static(f"  • Example: /etc/yum.repos.d/*.repo.bak_{backup_suffix}", classes="backup-info")
                elif self.package_manager.name == "pacman":
                    yield Static(f"  • Example: /etc/pacman.d/mirrorlist.bak_{backup_suffix}", classes="backup-info")
                elif self.package_manager.name == "apk":
                    yield Static(f"  • Example: /etc/apk/repositories.bak_{backup_suffix}", classes="backup-info")
                
                yield Rule()
                
                # Execution log area (initially empty)
                yield Label("Execution Log:", classes="info-key")
                with Vertical(id="log-output"):
                    yield Static("Waiting for confirmation...", id="log-content", classes="log-content")
            
            # Fixed action help at the bottom - single line format like main menu
            with Container(id="confirmation-actions"):
                yield Static("Keyboard Shortcuts: j/k=Scroll | Enter=Confirm | Esc=Cancel", classes="help-text")
    
    def action_confirm_change(self) -> None:
        """Confirm the mirror change."""
        if self.is_executing:
            return
        self._execute_mirror_change()
    
    def action_cancel_operation(self) -> None:
        """Cancel the operation."""
        self._cancel_operation()
    
    def action_scroll_down(self) -> None:
        """Scroll content down."""
        try:
            content = self.query_one("#confirmation-content", ScrollableContainer)
            content.scroll_down()
        except:
            pass
    
    def action_scroll_up(self) -> None:
        """Scroll content up."""
        try:
            content = self.query_one("#confirmation-content", ScrollableContainer)
            content.scroll_up()
        except:
            pass
    
    def action_scroll_page_down(self) -> None:
        """Scroll content page down."""
        try:
            content = self.query_one("#confirmation-content", ScrollableContainer)
            content.scroll_page_down()
        except:
            pass
    
    def action_scroll_page_up(self) -> None:
        """Scroll content page up."""
        try:
            content = self.query_one("#confirmation-content", ScrollableContainer)
            content.scroll_page_up()
        except:
            pass
    
    def _cancel_operation(self) -> None:
        """Cancel the operation and dismiss modal."""
        if not self.is_executing:
            self.callback(False, "Cancelled by user")
            self.dismiss()
    
    def _dismiss_after_success(self) -> None:
        """Dismiss modal after successful operation."""
        self.dismiss()
    
    @work(exclusive=True, thread=True)  
    async def _execute_mirror_change(self) -> None:
        """Execute the mirror change in background thread."""
        self.is_executing = True
        
        def update_ui_start():
            self._log_message("Starting mirror source change...")
        
        self.app.call_from_thread(update_ui_start)
        
        try:
            # Create backup
            backup_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            def log_backup():
                self._log_message(f"Creating backup with suffix: .bak_{backup_time}")
            
            self.app.call_from_thread(log_backup)
            
            # Perform the actual mirror change
            success, message = self._change_mirror_with_backup(backup_time)
            
            def update_ui_complete():
                if success:
                    self._log_message(f"✅ {message}")
                    self.callback(True, message)
                    # Auto-dismiss after a short delay using a wrapper function
                    self.set_timer(2.0, self._dismiss_after_success)
                else:
                    self._log_message(f"❌ {message}")
                    self.callback(False, message)
                
                self.is_executing = False
            
            self.app.call_from_thread(update_ui_complete)
            
        except Exception as e:
            def show_error():
                self._log_message(f"❌ Error: {str(e)}")
                self.callback(False, f"Error: {str(e)}")
                self.is_executing = False
            
            self.app.call_from_thread(show_error)
    
    def _change_mirror_with_backup(self, backup_suffix: str) -> tuple[bool, str]:
        """Change mirror source with backup creation."""
        try:
            if self.package_manager.name == "apt":
                return self._change_apt_mirror(backup_suffix)
            elif self.package_manager.name == "brew":
                return self._change_brew_mirror(backup_suffix)
            else:
                # Use existing implementation from PackageManagerDetector with backup suffix
                return self.detector.change_mirror(self.package_manager.name, self.new_source, backup_suffix)
        except Exception as e:
            return False, f"Failed to change mirror: {str(e)}"
    
    def _change_apt_mirror(self, backup_suffix: str) -> tuple[bool, str]:
        """Change APT mirror source with backup."""
        sources_file = "/etc/apt/sources.list"
        backup_file = f"{sources_file}.bak_{backup_suffix}"
        
        try:
            # Create backup
            if os.path.exists(sources_file):
                shutil.copy2(sources_file, backup_file)
                
                def log_backup():
                    self._log_message(f"Backup created: {backup_file}")
                self.app.call_from_thread(log_backup)
            
            # Write new sources.list
            with open(sources_file, 'w') as f:
                # Detect distribution codename
                try:
                    codename = subprocess.run(
                        ["lsb_release", "-cs"],
                        capture_output=True,
                        text=True,
                        check=True
                    ).stdout.strip()
                except:
                    codename = "focal"  # Default fallback
                
                def log_codename():
                    self._log_message(f"Detected distribution: {codename}")
                self.app.call_from_thread(log_codename)
                
                # Write repository entries
                f.write(f"deb {self.new_source} {codename} main restricted universe multiverse\n")
                f.write(f"deb {self.new_source} {codename}-updates main restricted universe multiverse\n")
                f.write(f"deb {self.new_source} {codename}-backports main restricted universe multiverse\n")
                f.write(f"deb {self.new_source} {codename}-security main restricted universe multiverse\n")
            
            def log_write():
                self._log_message(f"Updated {sources_file}")
            self.app.call_from_thread(log_write)
            
            # Update package index with real-time output
            # Run apt update and capture output in real-time
            try:
                def log_update_start():
                    self._log_message("Running apt update...")
                self.app.call_from_thread(log_update_start)
                
                process = subprocess.Popen(
                    ["apt", "update"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,  # Combine stderr with stdout
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )
                
                # Read output line by line in real-time
                line_count = 0
                while True:
                    output = process.stdout.readline()
                    if output == '' and process.poll() is not None:
                        break
                    if output:
                        line = output.strip()
                        # Show all significant lines, not just filtered ones
                        if line and len(line) > 2:  # Skip very short lines
                            line_count += 1
                            def log_line(msg=line):
                                self._log_message(f"  {msg}")
                            self.app.call_from_thread(log_line)
                
                return_code = process.poll()
                
                def log_completion():
                    if return_code == 0:
                        self._log_message(f"✅ apt update completed successfully ({line_count} lines)")
                    else:
                        self._log_message(f"❌ apt update failed with return code: {return_code}")
                
                self.app.call_from_thread(log_completion)
                
                if return_code != 0:
                    return False, f"apt update failed with return code: {return_code}"
                    
            except Exception as e:
                def log_error():
                    self._log_message(f"❌ Error running apt update: {str(e)}")
                self.app.call_from_thread(log_error)
                return False, f"Error running apt update: {str(e)}"
            
            return True, f"Successfully changed APT mirror to {self.new_source}"
            
        except Exception as e:
            return False, f"Failed to change APT mirror: {str(e)}"
    
    def _change_brew_mirror(self, backup_suffix: str) -> tuple[bool, str]:
        """Change Homebrew mirror source with backup."""
        brew_repo = "/usr/local/Homebrew"
        config_file = f"{brew_repo}/.git/config"
        backup_file = f"{config_file}.bak_{backup_suffix}"
        
        try:
            if os.path.exists(config_file):
                shutil.copy2(config_file, backup_file)
                
                def log_backup():
                    self._log_message(f"Backup created: {backup_file}")
                self.app.call_from_thread(log_backup)
            
            if os.path.exists(brew_repo):
                def log_change():
                    self._log_message("Changing Homebrew remote URL...")
                self.app.call_from_thread(log_change)
                
                result = subprocess.run(
                    ["git", "-C", brew_repo, "remote", "set-url", "origin", self.new_source],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    return True, f"Successfully changed Homebrew mirror to {self.new_source}"
                else:
                    return False, f"Failed to change Homebrew remote: {result.stderr}"
            else:
                return False, "Homebrew repository not found"
                
        except Exception as e:
            return False, f"Failed to change Homebrew mirror: {str(e)}"
    
    def _log_message(self, message: str) -> None:
        """Add a message to the execution log."""
        try:
            log_content = self.query_one("#log-content", Static)
            current_content = log_content.renderable
            
            # Get current content as string
            if hasattr(current_content, '__str__'):
                current_text = str(current_content)
            else:
                current_text = ""
            
            # Add timestamp
            timestamp = datetime.now().strftime("%H:%M:%S")
            new_line = f"[{timestamp}] {message}"
            
            if current_text:
                updated_content = current_text + "\n" + new_line
            else:
                updated_content = new_line
            
            # Keep only last 20 lines
            lines = updated_content.split('\n')
            if len(lines) > 20:
                lines = lines[-20:]
                updated_content = '\n'.join(lines)
            
            log_content.update(updated_content)
            
            # Auto-scroll to bottom
            log_container = self.query_one("#confirmation-content", ScrollableContainer)
            log_container.scroll_end(animate=False)
            
        except Exception:
            pass
    
    def action_dismiss(self) -> None:
        """Dismiss the modal."""
        self._cancel_operation()