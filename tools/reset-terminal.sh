#!/bin/bash
# Terminal Reset Script
# Purpose: Clean up terminal state after TUI application exits
# This ensures terminal returns to normal state even after abnormal exit

# Reset terminal to normal state
reset_terminal() {
    # Exit alternate screen buffer
    printf '\033[?1049l'
    
    # Disable all mouse tracking modes
    printf '\033[?1000l'  # Basic mouse tracking
    printf '\033[?1002l'  # Cell motion tracking
    printf '\033[?1003l'  # All motion tracking
    printf '\033[?1006l'  # SGR extended mode
    printf '\033[?1015l'  # URXVT mode
    
    # Disable other features
    printf '\033[?1004l'  # Focus tracking
    printf '\033[?2004l'  # Bracketed paste mode
    
    # Show cursor
    printf '\033[?25h'
    
    # Reset colors and attributes
    printf '\033[0m'
    
    # Clear any remaining escape sequences
    printf '\033c'
    
    # Ensure changes are flushed
    tput sgr0 2>/dev/null || true
}

# Execute reset
reset_terminal

# Optional: clear screen if passed --clear flag
if [[ "$1" == "--clear" ]]; then
    clear
fi

exit 0