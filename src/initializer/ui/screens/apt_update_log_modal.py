"""APT Update Log Modal for full-screen progress and log display."""

import re
import subprocess
from datetime import datetime
from textual import on, work
from textual.app import ComposeResult
from textual.containers import Container, Vertical, ScrollableContainer
from textual.screen import ModalScreen
from textual.widgets import Static, Rule, ProgressBar
from textual.events import Key
from typing import Callable, Optional


class APTUpdateLogModal(ModalScreen):
    """Full-screen modal for displaying APT update progress and logs."""
    
    # CSS styles for full-screen modal
    CSS = """
    APTUpdateLogModal {
        align: center middle;
    }
    
    #log-modal-container {
        width: 95%;
        height: 95%;
        background: $surface;
        border: round #7dd3fc;
        padding: 1;
        layout: vertical;
    }
    
    #log-title {
        height: 1;
        text-align: center;
        color: $text;
        text-style: bold;
        background: $surface;
    }
    
    #progress-container {
        height: 3;
        padding: 1 0;
        background: $surface;
    }
    
    #progress-bar {
        height: 1;
        margin: 0 1;
    }
    
    #progress-text {
        height: 1;
        text-align: center;
        color: $text-muted;
        background: $surface;
    }
    
    #log-content-area {
        height: 1fr;
        overflow-y: auto;
        padding: 0 1;
        scrollbar-size: 1 1;
        background: $surface;
    }
    
    #log-output {
        height: auto;
        min-height: 1;
        background: $surface;
    }
    
    .log-line {
        height: auto;
        min-height: 1;
        color: $text;
        background: transparent;
    }
    
    .log-line-success {
        color: $success;
        text-style: bold;
    }
    
    .log-line-error {
        color: $error;
        text-style: bold;
    }
    
    .log-line-warning {
        color: $warning;
    }
    
    #help-container {
        height: 2;
        background: $surface;
        layout: vertical;
        padding: 0;
    }
    
    .help-text {
        height: 1;
        text-align: center;
        color: $text-muted;
        background: $surface;
    }
    """
    
    def __init__(self, callback: Callable[[bool, str], None]):
        super().__init__()
        self.callback = callback
        self.apt_is_running = False
        self.is_completed = False
        self.current_progress = 0
        self.total_packages = 0
        self.current_package = 0
        self.log_lines = []
        
    def compose(self) -> ComposeResult:
        """Compose the full-screen log modal."""
        with Container(id="log-modal-container"):
            yield Static("APT Update Progress", id="log-title")
            yield Rule()
            
            # Progress section
            with Container(id="progress-container"):
                yield ProgressBar(total=100, show_eta=False, id="progress-bar")
                yield Static("Initializing...", id="progress-text")
            
            yield Rule()
            
            # Log content area
            with ScrollableContainer(id="log-content-area"):
                with Vertical(id="log-output"):
                    yield Static("Starting APT update...", classes="log-line")
            
            # Help section at bottom
            with Container(id="help-container"):
                yield Rule()
                yield Static("Esc=Exit | Auto-scroll enabled", classes="help-text")
    
    @on(Key)
    def handle_key_event(self, event: Key) -> None:
        """Handle key events for the log modal."""
        if event.key == "escape":
            self.action_dismiss()
            event.prevent_default()
            event.stop()
    
    def on_mount(self) -> None:
        """Initialize the modal and start APT update."""
        self.focus()
        # Start the APT update process
        self.start_apt_update()
    
    def can_focus(self) -> bool:
        """Return True to allow this modal to receive focus."""
        return True
    
    @property
    def is_modal(self) -> bool:
        """Mark this as a modal screen."""
        return True
    
    def action_dismiss(self) -> None:
        """Handle modal dismissal."""
        if self.apt_is_running and not self.is_completed:
            # If update is still running, show warning but allow exit
            self.add_log_line("⚠️ APT update was interrupted by user", "warning")
            self.callback(False, "Update interrupted by user")
        self.dismiss()
    
    def add_log_line(self, message: str, log_type: str = "normal") -> None:
        """Add a line to the log display."""
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_line = f"[{timestamp}] {message}"
            self.log_lines.append(log_line)
            
            # Determine CSS class based on log type
            css_class = "log-line"
            if log_type == "success":
                css_class = "log-line-success"
            elif log_type == "error":
                css_class = "log-line-error"
            elif log_type == "warning":
                css_class = "log-line-warning"
            
            # Add to log output
            log_container = self.query_one("#log-output", Vertical)
            log_container.mount(Static(log_line, classes=css_class))
            
            # Keep only last 100 lines to prevent memory issues
            if len(self.log_lines) > 100:
                self.log_lines = self.log_lines[-100:]
                # Remove old log widgets
                log_widgets = log_container.children
                if len(log_widgets) > 100:
                    log_widgets[0].remove()
            
            # Auto-scroll to bottom
            content_area = self.query_one("#log-content-area", ScrollableContainer)
            content_area.scroll_end(animate=False)
            
        except Exception:
            # Fail silently if UI update fails
            pass
    
    def update_progress(self, current: int, total: int, status: str = "") -> None:
        """Update the progress bar and status text."""
        try:
            if total > 0:
                progress = min(int((current / total) * 100), 100)
                progress_bar = self.query_one("#progress-bar", ProgressBar)
                progress_bar.update(progress=progress)
                
                self.current_progress = progress
                self.current_package = current
                self.total_packages = total
                
                # Update progress text
                progress_text = self.query_one("#progress-text", Static)
                if status:
                    progress_text.update(f"{current}/{total} packages - {status} ({progress}%)")
                else:
                    progress_text.update(f"{current}/{total} packages ({progress}%)")
        except Exception:
            # Fail silently if UI update fails
            pass
    
    def parse_apt_progress(self, line: str) -> tuple[Optional[int], Optional[int], str]:
        """Parse APT output to extract progress information."""
        line = line.strip()
        
        # Pattern for "Get:X/Y" format
        get_match = re.search(r'Get:(\d+)/(\d+)', line)
        if get_match:
            current = int(get_match.group(1))
            total = int(get_match.group(2))
            return current, total, "Downloading"
        
        # Pattern for percentage
        percent_match = re.search(r'(\d+)%', line)
        if percent_match and self.total_packages > 0:
            percent = int(percent_match.group(1))
            current = int((percent / 100) * self.total_packages)
            return current, self.total_packages, "Processing"
        
        # Check for completion indicators
        if "Reading package lists" in line:
            return None, None, "Reading package lists"
        elif "Building dependency tree" in line:
            return None, None, "Building dependency tree"
        elif "Reading state information" in line:
            return None, None, "Reading state information"
        
        return None, None, ""
    
    @work(exclusive=True, thread=True)
    async def start_apt_update(self) -> None:
        """Start the APT update process in a background thread."""
        self.apt_is_running = True
        
        def log_start():
            self.add_log_line("🚀 Starting APT repository update...")
            self.update_progress(0, 100, "Initializing")
        
        self.app.call_from_thread(log_start)
        
        try:
            # Start apt update process
            process = subprocess.Popen(
                ["apt", "update"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            line_count = 0
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                
                if output:
                    line = output.strip()
                    if line and len(line) > 2:  # Skip very short lines
                        line_count += 1
                        
                        # Parse progress information
                        current, total, status = self.parse_apt_progress(line)
                        
                        def update_ui(msg=line, curr=current, tot=total, stat=status, count=line_count):
                            # Add log line
                            self.add_log_line(f"  {msg}")
                            
                            # Update progress if we have progress info
                            if curr is not None and tot is not None:
                                self.update_progress(curr, tot, stat)
                            elif stat:
                                # Update status without changing progress
                                progress_text = self.query_one("#progress-text", Static)
                                progress_text.update(f"Line {count} - {stat}")
                        
                        self.app.call_from_thread(update_ui)
            
            return_code = process.poll()
            
            def update_completion():
                self.apt_is_running = False
                self.is_completed = True
                
                if return_code == 0:
                    self.add_log_line("✅ APT update completed successfully!", "success")
                    self.update_progress(100, 100, "Completed successfully")
                    self.callback(True, f"APT update completed successfully ({line_count} operations)")
                else:
                    self.add_log_line(f"❌ APT update failed with return code: {return_code}", "error")
                    self.update_progress(self.current_progress, 100, f"Failed (code: {return_code})")
                    self.callback(False, f"APT update failed with return code: {return_code}")
                
                self.add_log_line("Press Esc to close this window", "normal")
            
            self.app.call_from_thread(update_completion)
            
        except Exception as e:
            def show_error():
                self.apt_is_running = False
                self.add_log_line(f"❌ Error during APT update: {str(e)}", "error")
                self.update_progress(self.current_progress, 100, f"Error: {str(e)}")
                self.callback(False, f"Error during APT update: {str(e)}")
                self.add_log_line("Press Esc to close this window", "normal")
            
            self.app.call_from_thread(show_error)