#!/usr/bin/env python3
"""
Linux System Initializer - Main Entry Point
Convenience script to run the application from the project root.
"""

import sys
from pathlib import Path

# Add src to Python path
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# Import and run the main function from the package to avoid circular import
from initializer.main import main

if __name__ == "__main__":
    main()