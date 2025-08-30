# Linux System Initializer

A modern Terminal User Interface (TUI) application for Linux system initialization and configuration.

## 🌟 Features

- **Modern TUI Interface**: Built with Python Rich/Textual for beautiful terminal interfaces
- **Configuration-Driven**: YAML-based configuration system with presets
- **Modular Design**: Pluggable modules for different system components
- **Cross-Platform**: Works on various Linux distributions
- **Headless Server Support**: Optimized for SSH and headless environments

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- Linux operating system

### Installation

1. **Clone the repository:**

```bash
git clone https://github.com/DeltaV235/Initializer.git
cd Initializer
```

2. **Run the setup script:**

```bash
./install.sh
```

3. **Launch the application:**

```bash
./run.sh
```

**Or manually:**

```bash
source .venv/bin/activate
python main.py
```

### Command Line Options

```bash
python main.py --help

Options:
  -p, --preset TEXT       Use a configuration preset
  -c, --config-dir TEXT   Configuration directory path
  --headless              Run in headless mode (no animations)
  --debug                 Enable debug mode
  --help                  Show this message and exit
```

## 🔗 Remote Sync and Execution

- Non-WSL/macOS/Windows: execute scripts on the remote server.
- Use `tools/sync-to-remote.sh` to sync to `root@192.168.0.33:~/Initializer`.

```bash
# Sync with defaults
tools/sync-to-remote.sh

# Dry run
tools/sync-to-remote.sh -n

# Custom host/user/destination
tools/sync-to-remote.sh -H 192.168.0.33 -u root -D ~/Initializer
```

Then on the remote:

```bash
ssh root@192.168.0.33
cd ~/Initializer
./install.sh
./run.sh
```

WSL users may test locally, but verify on remote.

## 📋 Modules

### System Information

- View detailed system information
- Export data in multiple formats (JSON, YAML, Text)
- Real-time system monitoring

### Homebrew Management

- Install and configure Homebrew
- Change package sources/mirrors
- Install essential packages

### Package Manager

- Auto-detect available package managers
- Configure mirror sources
- Install system packages

### User Management

- Create and configure users
- Set up SSH keys
- Manage user permissions

## ⚙️ Configuration

Configuration files are located in the `config/` directory:

- `app.yaml`: Main application settings
- `modules.yaml`: Module-specific configuration  
- `themes.yaml`: UI themes and colors
- `presets/`: Predefined configuration templates

### Example Preset Usage

```bash
# Use server preset for headless environments
python main.py --preset server

# Use desktop preset for workstation setup
python main.py --preset desktop
```

## 🎨 Themes

The application supports multiple themes:

- `default`: Standard blue theme
- `dark`: Dark mode theme  
- `light`: Light theme for bright terminals

## 🖥️ Screenshots

*TUI screenshots coming soon...*

## 🔧 Development

### Project Structure

```text
├── config/           # YAML configuration files
├── src/             # Python source code
│   ├── modules/     # Feature modules
│   ├── ui/          # User interface components
│   └── utils/       # Utility functions
├── legacy/          # Original bash scripts (backup)
└── main.py          # Application entry point
```

### Adding New Modules

1. Create module in `src/modules/`
2. Add configuration to `config/modules.yaml`
3. Create UI screen in `src/ui/screens/`
4. Register in main menu

## 📜 Legacy Scripts

The original bash scripts are preserved in the `legacy/` directory and can still be used:

```bash
cd legacy/01-linux-initial-scripts
./00-main.sh
```

## 📄 License

MIT License - see LICENSE file for details.

## 👨‍💻 Author

Created by DeltaV235

---

## 🎯 Project Vision

Modernizing Linux system initialization, one terminal at a time. 🚀
