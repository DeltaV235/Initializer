#!/bin/bash

### Linux System Initializer Run Script
### Activates virtual environment and runs the application
### Automatically resets terminal state after exit

VENV_NAME=".venv"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Function to reset terminal
reset_terminal() {
    if [ -f "$SCRIPT_DIR/tools/reset-terminal.sh" ]; then
        "$SCRIPT_DIR/tools/reset-terminal.sh" >/dev/null 2>&1
    fi
}

# Ensure terminal is reset on exit
trap reset_terminal EXIT

# Check if virtual environment exists
if [ ! -d "$VENV_NAME" ]; then
    echo "❌ Virtual environment not found. Please run ./install.sh first"
    exit 1
fi

# Activate virtual environment
source "$VENV_NAME/bin/activate"

# Run the application
python main.py "$@"
EXIT_CODE=$?

# Reset terminal state (also triggered by trap, but explicit for safety)
reset_terminal

exit $EXIT_CODE