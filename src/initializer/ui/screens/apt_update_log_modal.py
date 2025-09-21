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
    
    # CSS styles for progress modal
    CSS = """
    APTUpdateLogModal {
        align: center middle;
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
    """
    
    def __init__(self, callback: Callable[[bool, str], None], close_source_selection: bool = False, source_modal_ref=None, main_menu_ref=None):
        super().__init__()
        self.callback = callback
        self.close_source_selection = close_source_selection  # Flag to close source selection modal
        self.source_modal_ref = source_modal_ref  # Direct reference to source modal
        self.main_menu_ref = main_menu_ref  # Reference to main menu for refreshing package manager page
        self.apt_is_running = False
        self.is_completed = False
        self.current_progress = 0
        self.total_packages = 0
        self.current_package = 0
        self.log_lines = []
        self._estimated_total = 0  # Track estimated total for progress calculation
        
    def compose(self) -> ComposeResult:
        """Compose the progress log modal using extra large modal container."""
        with Container(classes="modal-container-xl"):
            yield Static("APT Update Progress", id="modal-title")
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
            
            # Help section at bottom - use public styles from styles.css
            with Container(id="help-box"):
                yield Static("J/K=Scroll | Esc=Exit | Progress continues in background", classes="help-text")
    
    @on(Key)
    def handle_key_event(self, event: Key) -> None:
        """Handle key events for the log modal."""
        if event.key == "escape":
            self.action_dismiss()
            event.prevent_default()
            event.stop()
        elif event.key == "j":
            self.action_scroll_down()
            event.prevent_default()
            event.stop()
        elif event.key == "k":
            self.action_scroll_up()
            event.prevent_default()
            event.stop()
    
    def on_mount(self) -> None:
        """Initialize the modal and start APT update."""
        self.focus()
        # Start the APT update process
        self.start_apt_update()

    def _close_source_selection_modal(self) -> None:
        """Close the source selection modal using multiple strategies."""
        try:
            # Method 1: Use direct reference if available
            if self.source_modal_ref and hasattr(self.source_modal_ref, 'dismiss'):
                try:
                    # Use call_later to ensure it's executed in the correct context
                    self.call_later(self.source_modal_ref.dismiss)
                    return
                except Exception:
                    pass

            # Method 2: Use a delayed approach with app.call_later
            def delayed_close():
                try:
                    # Search for the source modal and close it
                    for screen in list(self.app.screen_stack):
                        if screen.__class__.__name__ == 'SourceSelectionModal':
                            try:
                                screen.dismiss()
                                break
                            except Exception:
                                # If dismiss fails, try removing from stack
                                try:
                                    if screen in self.app.screen_stack:
                                        self.app.screen_stack.remove(screen)
                                except Exception:
                                    pass
                                break
                except Exception:
                    pass

            # Call the close function after a small delay to ensure proper timing
            self.call_later(delayed_close)

        except Exception:
            pass

    def _refresh_package_manager_page(self) -> None:
        """Refresh the package manager page in main menu after progress modal closes."""
        try:
            if self.main_menu_ref and hasattr(self.main_menu_ref, 'refresh_package_manager_page'):
                # Use call_later to ensure it's executed in the correct context
                self.call_later(self.main_menu_ref.refresh_package_manager_page)
        except Exception:
            # Silently fail if refresh is not available
            pass
    
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
            # APT process will continue running in background
            self.add_log_line("⚠️ APT update continues in background", "warning")
            self.callback(False, "Update running in background")

        # Close source selection modal when user dismisses this progress modal
        if self.close_source_selection:
            self._close_source_selection_modal()

        # Refresh package manager page in main menu after closing
        self._refresh_package_manager_page()

        self.dismiss()

    def action_scroll_down(self) -> None:
        """Scroll log content down."""
        try:
            content = self.query_one("#log-content-area", ScrollableContainer)
            content.scroll_down()
        except Exception:
            pass

    def action_scroll_up(self) -> None:
        """Scroll log content up."""
        try:
            content = self.query_one("#log-content-area", ScrollableContainer)
            content.scroll_up()
        except Exception:
            pass
    
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

        # Pattern for "Get:X/Y" format - this gives us accurate progress
        get_match = re.search(r'Get:(\d+)/(\d+)', line)
        if get_match:
            current = int(get_match.group(1))
            total = int(get_match.group(2))
            return current, total, "Downloading packages"

        # Pattern for "Hit:X" or "Ign:X" format - also indicates progress
        hit_ign_match = re.search(r'(?:Hit|Ign):(\d+)', line)
        if hit_ign_match and hasattr(self, '_estimated_total') and self._estimated_total > 0:
            current = int(hit_ign_match.group(1))
            return current, self._estimated_total, "Updating repositories"

        # Pattern for percentage in output
        percent_match = re.search(r'(\d+)%', line)
        if percent_match:
            percent = int(percent_match.group(1))
            # Use the percentage directly
            return percent, 100, "Processing"

        # Detect total repository count for better progress estimation
        if "packages" in line and "updated" in line:
            packages_match = re.search(r'(\d+)\s+packages', line)
            if packages_match:
                self._estimated_total = int(packages_match.group(1))
                return 0, self._estimated_total, "Starting update"

        # Check for completion indicators
        if "Reading package lists" in line:
            return 95, 100, "Reading package lists"
        elif "Building dependency tree" in line:
            return 97, 100, "Building dependency tree"
        elif "Reading state information" in line:
            return 99, 100, "Reading state information"

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
                            else:
                                # Fallback: use line count as rough progress indicator
                                # Estimate 50-100 lines for typical APT update
                                estimated_progress = min(int((count / 80) * 90), 90)  # Cap at 90%
                                if estimated_progress > self.current_progress:
                                    self.update_progress(estimated_progress, 100, f"Processing line {count}")

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
                    self.update_progress(100, 100, f"Failed (code: {return_code})")
                    self.callback(False, f"APT update failed with return code: {return_code}")

                # Close source selection modal when APT update completes
                if self.close_source_selection:
                    self._close_source_selection_modal()

                self.add_log_line("Press Esc to close this window", "normal")
            
            self.app.call_from_thread(update_completion)
            
        except Exception as e:
            def show_error():
                self.apt_is_running = False
                self.add_log_line(f"❌ Error during APT update: {str(e)}", "error")
                self.update_progress(100, 100, f"Error: {str(e)}")
                self.callback(False, f"Error during APT update: {str(e)}")

                # Close source selection modal when APT update encounters error
                if self.close_source_selection:
                    self._close_source_selection_modal()

                self.add_log_line("Press Esc to close this window", "normal")
            
            self.app.call_from_thread(show_error)