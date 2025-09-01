# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Communication Language
- **Primary Language**: Respond in Chinese (中文) for all interactions
- **Technical Terms**: Keep technical terms, programming keywords, and proper nouns in English
- **Code Comments**: Follow existing code comment language conventions in the project

## Development Philosophy
- **Simplicity First**: Use simple, straightforward implementations over complex designs
- **Avoid Over-engineering**: Implement only what is needed, avoid premature optimization
- **Readability**: Prefer clear, readable code over clever solutions

## Project Overview

Linux System Initializer is a modern Terminal User Interface (TUI) application for Linux system initialization and configuration. The project has been refactored from legacy bash scripts to a Python-based TUI using Rich/Textual framework.

## Development Commands

### Installation & Setup
```bash
# Install with all dependencies
./install.sh

# Install with development dependencies
./install.sh --dev

# Install in auto-confirm mode (non-interactive)
./install.sh --auto-confirm
```

### Running the Application
```bash
# Primary run method
./run.sh

# Direct execution
python main.py

# With command-line tool (after installation)
initializer

# With options
./run.sh --preset server
./run.sh --debug
./run.sh --headless
```

### Development Tools (when installed with --dev)
```bash
# Code formatting
black src/

# Linting
flake8 src/

# Type checking
mypy src/

# Testing
pytest
```

### Remote Deployment
```bash
# Sync to remote server (default: root@192.168.0.33:~/Initializer)
tools/sync-to-remote.sh

# Dry run
tools/sync-to-remote.sh -n

# With custom settings
tools/sync-to-remote.sh -H 192.168.0.33 -u root -D ~/Initializer
```

## Architecture

### Project Structure
- `src/initializer/` - Main Python package
  - `app.py` - Main TUI application class
  - `config_manager.py` - YAML configuration management
  - `ui/screens/` - Screen components (main_menu, system_info, homebrew, settings, help)
  - `modules/` - Business logic modules
  - `utils/` - Utility functions
- `config/` - YAML configuration files
  - `app.yaml` - Main application settings
  - `modules.yaml` - Module-specific configuration
  - `themes.yaml` - UI themes and colors
  - `presets/` - Predefined configuration templates
- `legacy/` - Original bash scripts (preserved for reference)
- `main.py` - Application entry point

### Key Technologies
- **Rich/Textual**: Terminal UI framework
- **PyYAML**: Configuration file handling
- **Click**: Command-line interface
- **psutil**: System information gathering
- **distro**: Linux distribution detection

## Configuration System

The application uses a YAML-based configuration system with support for:
- **Presets**: server, desktop, minimal configurations
- **Themes**: default, dark, light UI themes
- **Module settings**: per-module configuration options

### Using Presets
```bash
python main.py --preset server    # Headless server environment
python main.py --preset desktop   # Workstation setup
python main.py --preset minimal   # Basic installation
```

## Environment-Specific Execution

### WSL Environments
- Local execution is allowed for testing: `./install.sh`, `./run.sh`, `python main.py`
- Remote verification still recommended via `tools/sync-to-remote.sh`

### Non-WSL Environments  
- **Must execute on remote server** (192.168.0.33)
- Use `tools/sync-to-remote.sh` to deploy and run remotely
- Local execution is restricted per project instructions

## Adding New Modules

1. Create module in `src/initializer/modules/`
2. Add configuration to `config/modules.yaml`
3. Create UI screen in `src/initializer/ui/screens/`
4. Register in main menu (`src/initializer/ui/screens/main_menu.py`)

## Current Implementation Status

### Completed Features ✅
- Core TUI architecture with Rich/Textual
- Configuration management system
- System information module with export capabilities
- Main menu, system info, homebrew, settings, help screens
- Theme system with multiple color schemes
- Preset configuration system
- Automated installation and deployment scripts

### In Development 🚧
- Complete Homebrew module implementation
- Package manager module (auto-detect, mirror management)
- User management module (user creation, SSH keys)
- Enhanced UI components (progress bars, confirmation dialogs)