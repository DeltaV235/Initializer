#!/bin/bash

### Linux System Initializer Run Script
### Activates virtual environment and runs the application

VENV_NAME="initializer-venv"

# Check if virtual environment exists
if [ ! -d "$VENV_NAME" ]; then
    echo "❌ Virtual environment not found. Please run ./setup.sh first"
    exit 1
fi

# Activate virtual environment
source "$VENV_NAME/bin/activate"

# Run the application
python main.py "$@"