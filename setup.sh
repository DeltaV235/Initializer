#!/bin/bash

### Linux System Initializer Setup Script
### Creates virtual environment and installs dependencies using modern pyproject.toml

set -e

# Parse command line arguments
INSTALL_DEV=false
INSTALL_MODE="standard"
AUTO_CONFIRM=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --dev)
            INSTALL_DEV=true
            INSTALL_MODE="development"
            shift
            ;;
        --legacy)
            INSTALL_MODE="legacy"
            shift
            ;;
        --auto-confirm|-y)
            AUTO_CONFIRM=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --dev          Install development dependencies (pytest, black, flake8, mypy)"
            echo "  --legacy       Use legacy requirements.txt instead of pyproject.toml"
            echo "  --auto-confirm Automatically confirm all prompts (non-interactive mode)"
            echo "  -y             Same as --auto-confirm"
            echo "  -h, --help     Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                    # Standard installation with prompts"
            echo "  $0 --dev             # Development installation with prompts"
            echo "  $0 --auto-confirm    # Standard installation, auto-confirm all"
            echo "  $0 --dev -y          # Development installation, auto-confirm all"
            exit 0
            ;;
        *)
            echo "❌ Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Function to ask for user confirmation
ask_confirmation() {
    local message="$1"
    local default="${2:-y}"
    
    # If auto-confirm is enabled, use default
    if [ "$AUTO_CONFIRM" = true ]; then
        if [ "$default" = "y" ]; then
            echo "$message [Y/n]: y (auto-confirmed)"
            return 0
        else
            echo "$message [y/N]: n (auto-confirmed)"
            return 1
        fi
    fi
    
    while true; do
        if [ "$default" = "y" ]; then
            prompt="$message [Y/n]: "
        else
            prompt="$message [y/N]: "
        fi
        
        read -p "$prompt" response
        
        # If empty response, use default
        if [ -z "$response" ]; then
            response="$default"
        fi
        
        case "$response" in
            [Yy]|[Yy][Ee][Ss])
                return 0
                ;;
            [Nn]|[Nn][Oo])
                return 1
                ;;
            *)
                echo "❓ Please answer yes (y) or no (n)"
                ;;
        esac
    done
}

### Check network connectivity
check_network_connectivity() {
    echo "🌐 Checking network connectivity..."
    
    dns_issue=false
    proxy_issue=false
    
    # Test basic internet connectivity
    if ! timeout 10 ping -c 2 8.8.8.8 &> /dev/null; then
        echo "⚠️  Basic internet connectivity issue"
        proxy_issue=true
    fi
    
    # Test DNS resolution (different targets for Ubuntu vs RedHat)
    local dns_target="${1:-archive.ubuntu.com}"
    if ! timeout 10 ping -c 2 "$dns_target" &> /dev/null; then
        echo "⚠️  DNS resolution issue detected"
        dns_issue=true
    fi
    
    # Return 0 if any issue detected, 1 if everything is fine
    if [ "$dns_issue" = true ] || [ "$proxy_issue" = true ]; then
        return 0  # Issues detected
    else
        return 1  # No issues
    fi
}

### Apply Ubuntu mirror fix
apply_ubuntu_mirror_fix() {
    echo "   → Backing up original package sources..."
    
    # Execute with appropriate privileges
    if [ "$EUID" -eq 0 ]; then
        # Backup original sources.list
        cp /etc/apt/sources.list /etc/apt/sources.list.backup 2>/dev/null || true
        
        # Apply Aliyun mirror sources
        apply_aliyun_sources "/etc/apt/sources.list"
        
        # Install packages
        apt update && apt install -y python3-venv python3-dev python3-pip
    else
        # Backup original sources.list
        sudo cp /etc/apt/sources.list /etc/apt/sources.list.backup 2>/dev/null || true
        
        # Apply Aliyun mirror sources
        apply_aliyun_sources "/etc/apt/sources.list" "sudo"
        
        # Install packages
        sudo apt update && sudo apt install -y python3-venv python3-dev python3-pip
    fi
    
    echo "✅ Package sources updated to domestic mirrors"
    echo "💡 Original sources backed up to /etc/apt/sources.list.backup"
}

### Apply Aliyun mirror sources
apply_aliyun_sources() {
    local target_file="$1"
    local use_sudo="$2"
    
    echo "   → Configuring Aliyun mirror sources..."
    
    # Check if template file exists
    if [ ! -f "aliyun-sources.list.template" ]; then
        echo "❌ Template file 'aliyun-sources.list.template' not found!"
        echo "💡 Please ensure the template file is in the project directory."
        exit 1
    fi
    
    if command -v lsb_release &> /dev/null; then
        codename=$(lsb_release -cs)
        
        # Use the template file and replace codename
        if [ "$use_sudo" = "sudo" ]; then
            sed "s/{CODENAME}/$codename/g" aliyun-sources.list.template | sudo tee "$target_file" > /dev/null
        else
            sed "s/{CODENAME}/$codename/g" aliyun-sources.list.template > "$target_file"
        fi
    else
        echo "❌ lsb_release command not found - cannot determine Ubuntu codename"
        exit 1
    fi
}

### Install Ubuntu packages
install_ubuntu_packages() {
    if [ "$EUID" -eq 0 ]; then
        apt update && apt install -y python3-venv python3-dev python3-pip
    else
        sudo apt update && sudo apt install -y python3-venv python3-dev python3-pip
    fi
}

### Install RedHat packages
install_redhat_packages() {
    if command -v dnf &> /dev/null; then
        if [ "$EUID" -eq 0 ]; then
            dnf install -y python3-venv python3-devel python3-pip
        else
            sudo dnf install -y python3-venv python3-devel python3-pip
        fi
    elif command -v yum &> /dev/null; then
        if [ "$EUID" -eq 0 ]; then
            yum install -y python3-venv python3-devel python3-pip
        else
            sudo yum install -y python3-venv python3-devel python3-pip
        fi
    else
        echo "❌ Package manager not found (dnf/yum)"
        exit 1
    fi
}

echo "🚀 Setting up Linux System Initializer ($INSTALL_MODE mode)..."
if [ "$AUTO_CONFIRM" = true ]; then
    echo "🤖 Auto-confirm mode enabled - all prompts will be automatically accepted"
fi

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi

# Check Python version (3.8+)
python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
required_version="3.8"
if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"; then
    echo "❌ Python $required_version+ is required (found: $python_version)"
    exit 1
fi

echo "✅ Python $python_version detected"

# Check if venv module is available and functional
echo "🔍 Checking system dependencies..."

# Method 1: Check if venv module can be imported
venv_import_check=false
if python3 -c "import venv" &> /dev/null; then
    venv_import_check=true
fi

# Method 2: Try to create a test virtual environment
venv_creation_check=false
test_venv_dir="test-venv-check-$$"
if python3 -m venv "$test_venv_dir" &> /dev/null; then
    venv_creation_check=true
    rm -rf "$test_venv_dir" &> /dev/null
fi

# Determine if venv is fully functional
if [ "$venv_import_check" = true ] && [ "$venv_creation_check" = true ]; then
    echo "✅ Python venv module is functional"
else
    echo "❌ Python venv module is not available or not functional"
    
    if [ "$venv_import_check" = false ]; then
        echo "   → venv module cannot be imported"
    fi
    
    if [ "$venv_creation_check" = false ]; then
        echo "   → venv cannot create virtual environments"
    fi
    
    # Detect OS and provide installation instructions
    if [ -f /etc/debian_version ]; then
        # Debian/Ubuntu
        echo "📋 Detected Debian/Ubuntu system"
        echo "💡 Installing required packages..."
        
        # Try to install automatically if running as root or with sudo
        if [ "$EUID" -eq 0 ] || sudo -n true 2>/dev/null; then
            echo ""
            echo "📦 Required system packages:"
            echo "  - python3-venv (virtual environment support)"
            echo "  - python3-dev (Python development headers)"
            echo "  - python3-pip (Python package installer)"
            echo ""
            
            if ask_confirmation "🔧 Do you want to install these system packages now?"; then
                echo "🔧 Installing python3-venv and related packages..."
                
                # Check for potential network proxy issues (Clash, etc.)
                if check_network_connectivity "archive.ubuntu.com"; then
                    echo "💡 Network issues detected - possibly transparent proxy (Clash, etc.)"
                    echo ""
                    echo "🔧 Network fixes available using domestic mirrors"
                    echo ""
                    echo "📋 This will:"
                    echo "  - Backup current /etc/apt/sources.list to /etc/apt/sources.list.backup"
                    echo "  - Replace with Aliyun mirror sources"
                    echo "  - Install required packages"
                    echo "  - Keep the new mirror configuration"
                    echo ""
                    
                    if ask_confirmation "🔧 Do you want to update to domestic mirror sources?"; then
                        apply_ubuntu_mirror_fix
                    else
                        echo "⚠️  Mirror update cancelled. Proceeding with original package sources..."
                        echo "💡 Note: Package installation may fail due to network issues."
                        install_ubuntu_packages
                    fi
                else
                    # Normal installation without proxy issues
                    install_ubuntu_packages
                fi
                
                if [ $? -eq 0 ]; then
                    echo "✅ System packages installed successfully"
                else
                    echo "❌ Failed to install system packages"
                    exit 1
                fi
            else
                echo "❌ Installation cancelled by user"
                echo "💡 You can install the packages manually and re-run this script:"
                echo "    sudo apt update"
                echo "    sudo apt install python3-venv python3-dev python3-pip"
                exit 1
            fi
        else
            echo "🔑 Root/sudo access required. Please run:"
            echo "    sudo apt update"
            echo "    sudo apt install python3-venv python3-dev python3-pip"
            echo "Then re-run this script."
            exit 1
        fi
        
    elif [ -f /etc/redhat-release ]; then
        # RHEL/CentOS/Fedora
        echo "📋 Detected Red Hat/CentOS/Fedora system"
        echo "💡 Installing required packages..."
        
        if [ "$EUID" -eq 0 ] || sudo -n true 2>/dev/null; then
            echo ""
            echo "📦 Required system packages:"
            echo "  - python3-venv (virtual environment support)"
            echo "  - python3-devel (Python development headers)"
            echo "  - python3-pip (Python package installer)"
            echo ""
            
            if ask_confirmation "🔧 Do you want to install these system packages now?"; then
                echo "🔧 Installing python3-venv and related packages..."
                
                # Check for potential network proxy issues (Clash, etc.)
                if check_network_connectivity "mirrors.aliyun.com"; then
                    echo "💡 Network issues detected - possibly transparent proxy (Clash, etc.)"
                    echo ""
                    
                    if ask_confirmation "🔧 Continue with package installation despite network issues?"; then
                        install_redhat_packages
                    else
                        echo "❌ Installation cancelled. Please fix network issues and retry."
                        exit 1
                    fi
                else
                    # Normal installation without proxy issues
                    install_redhat_packages
                fi
                
                if [ $? -eq 0 ]; then
                    echo "✅ System packages installed successfully"
                else
                    echo "❌ Failed to install system packages"
                    exit 1
                fi
            else
                echo "❌ Installation cancelled by user"
                echo "💡 You can install the packages manually and re-run this script:"
                if command -v dnf &> /dev/null; then
                    echo "    sudo dnf install python3-venv python3-devel python3-pip"
                else
                    echo "    sudo yum install python3-venv python3-devel python3-pip"
                fi
                exit 1
            fi
        else
            echo "🔑 Root/sudo access required. Please run:"
            echo "    sudo dnf install python3-venv python3-devel python3-pip"
            echo "    # or: sudo yum install python3-venv python3-devel python3-pip"
            echo "Then re-run this script."
            exit 1
        fi
        
    else
        echo "❌ Unknown Linux distribution"
        echo "💡 Please install the python3-venv package for your system:"
        echo "  - Debian/Ubuntu: apt install python3-venv python3-dev"
        echo "  - RHEL/CentOS:   yum install python3-venv python3-devel"
        echo "  - Fedora:        dnf install python3-venv python3-devel"
        exit 1
    fi
fi

# Final verification after potential package installation
echo "🧪 Final verification of virtual environment functionality..."
final_test_venv="final-test-venv-$$"
if python3 -m venv "$final_test_venv" &> /dev/null; then
    rm -rf "$final_test_venv" &> /dev/null
    echo "✅ Virtual environment functionality confirmed"
else
    echo "❌ Virtual environment creation still fails after installation"
    echo "💡 Possible issues:"
    echo "   - Incomplete package installation"
    echo "   - System-specific Python configuration problems"
    echo "   - Insufficient disk space or permissions"
    echo "💡 Try manually running: python3 -m venv test-env"
    exit 1
fi

# Create virtual environment if it doesn't exist
VENV_NAME="initializer-venv"
if [ ! -d "$VENV_NAME" ]; then
    echo "📦 Creating virtual environment ($VENV_NAME)..."
    if python3 -m venv "$VENV_NAME"; then
        echo "✅ Virtual environment created successfully"
    else
        echo "❌ Failed to create virtual environment"
        echo "💡 Try running: rm -rf $VENV_NAME && ./setup.sh"
        exit 1
    fi
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source "$VENV_NAME/bin/activate"

# Upgrade pip and build tools
echo "📈 Upgrading pip and build tools..."
pip install --upgrade pip setuptools wheel

# Install dependencies based on mode
if [ "$INSTALL_MODE" = "legacy" ]; then
    echo "📚 Installing dependencies (legacy mode)..."
    pip install -r requirements.txt
else
    echo "📚 Installing project dependencies (modern mode)..."
    if [ "$INSTALL_DEV" = true ]; then
        echo "🛠️  Including development dependencies..."
        pip install -e .[dev]
    else
        pip install -e .
    fi
fi

# Verify installation
echo "🔍 Verifying installation..."
if python -c "import rich, textual, yaml, click, psutil, distro" 2>/dev/null; then
    echo "✅ Core dependencies installed successfully"
else
    echo "❌ Some core dependencies failed to install"
    exit 1
fi

# Check if command line tool is available
if [ "$INSTALL_MODE" != "legacy" ] && command -v initializer &> /dev/null; then
    echo "✅ Command line tool 'initializer' is available"
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "📋 Available commands:"
echo "  # Activate environment:"
echo "  source $VENV_NAME/bin/activate"
echo ""
if [ "$INSTALL_MODE" != "legacy" ]; then
    echo "  # Run application (recommended):"
    echo "  initializer"
    echo "  initializer --preset server"
    echo "  initializer --debug"
    echo ""
fi
echo "  # Run application (alternative):"
echo "  python main.py"
echo "  ./run.sh"
echo ""
if [ "$INSTALL_DEV" = true ]; then
    echo "🛠️  Development tools available:"
    echo "  pytest          # Run tests"
    echo "  black src/      # Format code"
    echo "  flake8 src/     # Check code style"
    echo "  mypy src/       # Type checking"
    echo ""
fi
echo "📖 For more information, see README.md or run:"
echo "  initializer --help" 2>/dev/null || echo "  python main.py --help"