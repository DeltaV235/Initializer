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
from textual.events import Key
from typing import Callable, Optional, List

from ...modules.package_manager import PackageManagerDetector
from .mirror_source_processor import APTMirrorProcessor
from .apt_update_log_modal import APTUpdateLogModal


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
    
    def __init__(self, package_manager, new_source: str, callback: Callable[[bool, str], None], config_manager=None):
        super().__init__()
        self.package_manager = package_manager
        self.new_source = new_source
        self.callback = callback
        self.detector = PackageManagerDetector(config_manager)
        
        # State management
        self.is_executing = False
        
        # Initialize APT mirror processor for complete handling
        if self.package_manager.name == "apt":
            self.apt_processor = APTMirrorProcessor(new_source)
            self.affected_files = self.apt_processor.get_affected_files_list()
        else:
            self.apt_processor = None
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
                
                # Backup information - simplified to show only backup filenames
                yield Label("Files to be backed up:", classes="info-key")
                backup_suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                # Show specific backup file examples - only filenames
                if self.package_manager.name == "apt":
                    if self.apt_processor:
                        # Use the processor to get accurate backup file names
                        main_file_path, file_format = self.apt_processor._detect_main_sources_file()
                        if file_format == "deb822":
                            yield Static(f"  • ubuntu.sources.bak_{backup_suffix}", classes="backup-info")
                        else:
                            yield Static(f"  • sources.list.bak_{backup_suffix}", classes="backup-info")
                        
                        # Check for additional files that would be backed up
                        sources_d_path = "/etc/apt/sources.list.d"
                        if os.path.exists(sources_d_path):
                            ubuntu_files_count = 0
                            for filename in os.listdir(sources_d_path):
                                if not filename.endswith(('.list', '.sources')) or filename == 'ubuntu.sources':
                                    continue
                                file_path = os.path.join(sources_d_path, filename)
                                try:
                                    with open(file_path, 'r') as f:
                                        content = f.read()
                                    if self.apt_processor._contains_ubuntu_sources(content):
                                        ubuntu_files_count += 1
                                except:
                                    continue
                            
                            if ubuntu_files_count > 0:
                                yield Static(f"  • {ubuntu_files_count} additional .list files (sources.list.d/)", classes="backup-info")
                    else:
                        yield Static(f"  • sources.list.bak_{backup_suffix}", classes="backup-info")
                elif self.package_manager.name == "brew":
                    yield Static(f"  • config.bak_{backup_suffix}", classes="backup-info")
                elif self.package_manager.name in ["yum", "dnf"]:
                    yield Static(f"  • *.repo.bak_{backup_suffix}", classes="backup-info")
                elif self.package_manager.name == "pacman":
                    yield Static(f"  • mirrorlist.bak_{backup_suffix}", classes="backup-info")
                elif self.package_manager.name == "apk":
                    yield Static(f"  • repositories.bak_{backup_suffix}", classes="backup-info")
                
                yield Rule()
                
                # Execution log area (initially empty)
                yield Label("Execution Log:", classes="info-key")
                with Vertical(id="log-output"):
                    yield Static("Waiting for confirmation...", id="log-content", classes="log-content")
            
            # Fixed action help at the bottom - single line format like main menu
            with Container(id="confirmation-actions"):
                yield Static("J/K=Up/Down | ENTER=Confirm | ESC=Cancel", classes="help-text")
    
    
    def on_mount(self) -> None:
        """Initialize the modal and ensure it can receive focus."""
        self.focus()
    
    @on(Key)
    def handle_key_event(self, event: Key) -> None:
        """Handle key events using @on decorator for reliable event processing."""
        if event.key == "enter":
            self.action_confirm_change()
            event.prevent_default()
            event.stop()
        elif event.key == "escape":
            self.action_cancel_operation()
            event.prevent_default()
            event.stop()
        elif event.key == "y":
            self.action_confirm_change()
            event.prevent_default()
            event.stop()
        elif event.key == "n":
            self.action_cancel_operation()
            event.prevent_default()
            event.stop()
    
    def can_focus(self) -> bool:
        """Return True to allow this modal to receive focus."""
        return True
    
    @property
    def is_modal(self) -> bool:
        """Mark this as a modal screen."""
        return True
    
    def action_confirm_change(self) -> None:
        """Confirm the mirror change."""
        if self.is_executing:
            return
        
        self._log_message("Starting mirror source change...")
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
        def debug_start():
            self._log_message("DEBUG: _execute_mirror_change started")
        
        self.app.call_from_thread(debug_start)
        
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
        """Change APT mirror source with complete backup and replacement."""
        if not self.apt_processor:
            return False, "APT processor not initialized"
            
        try:
            def log_start():
                self._log_message("Starting complete APT mirror source change...")
                self._log_message("DEBUG: About to call apt_processor.process_complete_mirror_change")
            self.app.call_from_thread(log_start)
            
            # Use the complete processor for mirror change
            result = self.apt_processor.process_complete_mirror_change(backup_suffix)
            
            def log_results():
                self._log_message("DEBUG: Mirror change completed, preparing to show APT log modal")
                if result['modified_main']:
                    for file in result['modified_main']:
                        self._log_message(f"✅ Updated main config: {file}")
                        
                if result['modified_sources_d']:
                    self._log_message(f"✅ Updated {len(result['modified_sources_d'])} files in sources.list.d/")
                    for file in result['modified_sources_d']:
                        self._log_message(f"  • {file}")
                else:
                    self._log_message("ℹ️  No additional Ubuntu sources found in sources.list.d/")
                
                self._log_message("🚀 Starting APT update in full-screen mode...")
            
            self.app.call_from_thread(log_results)
            
            # Show the APT update log modal through main thread
            def on_apt_update_complete(success: bool, message: str):
                # This callback is called when APT update completes
                if success:
                    total_files = len(result['modified_main']) + len(result['modified_sources_d'])
                    final_message = f"Successfully updated {total_files} configuration files and refreshed package index"
                    self.callback(True, final_message)
                else:
                    self.callback(False, f"Mirror changed but apt update failed: {message}")
                
                # NOW dismiss the confirmation modal after APT is complete
                self.set_timer(1.0, self._dismiss_after_success)
            
            def show_apt_log_modal():
                # Push the APT update log modal from main thread  
                self._log_message("DEBUG: About to push_screen APTUpdateLogModal")
                self.app.push_screen(APTUpdateLogModal(on_apt_update_complete))
                self._log_message("DEBUG: push_screen called successfully")
                # DO NOT dismiss this modal yet - let APT complete first
            
            # Call from thread to show modal in main thread
            self.app.call_from_thread(show_apt_log_modal)
            
            # Return success for the mirror change itself
            total_files = len(result['modified_main']) + len(result['modified_sources_d'])
            return True, f"Mirror configuration updated ({total_files} files). APT update started in full-screen mode."
                
        except Exception as e:
            def log_error():
                self._log_message(f"❌ Error during complete mirror change: {str(e)}")
            self.app.call_from_thread(log_error)
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