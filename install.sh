#!/bin/bash

### Linux System Initializer Install Script
### Creates virtual environment and installs dependencies using modern pyproject.toml

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

VENV_NAME="initializer-venv"
PROJECT_NAME="Linux System Initializer"

# Global variable to track if mirror fix has been applied
MIRROR_FIX_APPLIED=false

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

### Check network connectivity and handle package manager issues
check_and_handle_package_manager_connectivity() {
    local os_type="$1"  # "ubuntu" or "redhat"
    local dns_target="archive.ubuntu.com"
    
    if [ "$os_type" = "redhat" ]; then
        dns_target="mirrors.aliyun.com"
    fi
    
    echo -e "${BLUE}🌐 Checking package manager connectivity...${NC}"
    
    dns_issue=false
    proxy_issue=false
    
    # Test basic internet connectivity
    if ! timeout 10 ping -c 2 8.8.8.8 &> /dev/null; then
        echo -e "${YELLOW}⚠️  Basic internet connectivity issue${NC}"
        proxy_issue=true
    fi
    
    # Test DNS resolution
    if ! timeout 10 ping -c 2 "$dns_target" &> /dev/null; then
        echo -e "${YELLOW}⚠️  DNS resolution issue detected${NC}"
        dns_issue=true
    fi
    
    # If any network issues detected, offer mirror solution
    if [ "$dns_issue" = true ] || [ "$proxy_issue" = true ]; then
        echo -e "${YELLOW}💡 Network issues detected - possibly transparent proxy (Clash, etc.)${NC}"
        echo ""
        
        if [ "$os_type" = "ubuntu" ]; then
            echo -e "${BLUE}🔧 Network fixes available using domestic mirrors${NC}"
            echo ""
            echo -e "${BLUE}📋 This will:${NC}"
            echo -e "  - Backup current ${YELLOW}/etc/apt/sources.list${NC} to ${GREEN}/etc/apt/sources.list.backup${NC}"
            echo -e "  - Replace with ${GREEN}Aliyun mirror sources${NC}"
            echo -e "  - Install required packages"
            echo -e "  - Keep the new mirror configuration"
            echo ""
            
            if ask_confirmation "🔧 Do you want to update to domestic mirror sources?"; then
                # Backup and apply mirror fix
                echo -e "${BLUE}   → Backing up original package sources...${NC}"
                if [ "$EUID" -eq 0 ]; then
                    cp /etc/apt/sources.list /etc/apt/sources.list.backup 2>/dev/null || true
                    apply_aliyun_sources "/etc/apt/sources.list"
                else
                    sudo cp /etc/apt/sources.list /etc/apt/sources.list.backup 2>/dev/null || true
                    apply_aliyun_sources "/etc/apt/sources.list"
                fi
                return 0  # Use mirror fix
            else
                echo -e "${YELLOW}⚠️  Mirror update cancelled. Proceeding with original package sources...${NC}"
                echo -e "${YELLOW}💡 Note: Package installation may fail due to network issues.${NC}"
                return 1  # Use original sources
            fi
        else
            # RedHat systems - just warn and continue
            echo -e "${YELLOW}💡 Network issues detected but will attempt installation anyway${NC}"
            echo ""
            
            if ask_confirmation "🔧 Continue with package installation despite network issues?"; then
                return 1  # Continue with installation
            else
                echo -e "${RED}❌ Installation cancelled. Please fix network issues and retry.${NC}"
                exit 1
            fi
        fi
    else
        echo -e "${GREEN}✅ Package manager connectivity is good${NC}"
        return 1  # No network issues, use normal installation
    fi
}

### Legacy network check function (for backward compatibility)
check_network_connectivity() {
    local dns_target="${1:-archive.ubuntu.com}"
    if ! timeout 10 ping -c 2 8.8.8.8 &> /dev/null; then
        return 0  # Issues detected
    fi
    if ! timeout 10 ping -c 2 "$dns_target" &> /dev/null; then
        return 0  # Issues detected
    fi
    return 1  # No issues
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



### Display banner
echo -e "${BLUE}🚀 $PROJECT_NAME Installer${NC}"
echo "================================="
echo ""

### Check current status
echo -e "${BLUE}📋 Current installation status:${NC}"

# Step 1: Check Python version
python_ok=false
if command -v python3 &>/dev/null; then
    python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
    python_major=$(echo "$python_version" | cut -d'.' -f1)
    python_minor=$(echo "$python_version" | cut -d'.' -f2)
    
    if [ "$python_major" -ge 3 ] && [ "$python_minor" -ge 8 ]; then
        echo -e "  ✅ Python: ${GREEN}$python_version${NC} (compatible)"
        python_ok=true
    else
        echo -e "  ❌ Python: ${RED}$python_version${NC} (requires 3.8+)"
    fi
else
    echo -e "  ❌ Python: ${RED}Not found${NC}"
fi

# Step 2: Check if venv can be created (functional test)
venv_functional=false
if [ "$python_ok" = true ]; then
    echo -e "  🧪 Testing virtual environment creation..."
    test_venv="test-venv-$$"
    if python3 -m venv "$test_venv" &>/dev/null; then
        rm -rf "$test_venv" &>/dev/null
        echo -e "  ✅ Virtual environment creation: ${GREEN}Working${NC}"
        venv_functional=true
    else
        rm -rf "$test_venv" &>/dev/null
        echo -e "  ❌ Virtual environment creation: ${RED}Failed${NC}"
        echo -e "     ${YELLOW}(missing python3-venv or system dependencies)${NC}"
    fi
fi

# Step 3: Check if project virtual environment exists
if [ -d "$VENV_NAME" ]; then
    echo -e "  ✅ Project virtual environment: ${GREEN}Found${NC} ($VENV_NAME)"
    venv_exists=true
else
    echo -e "  ❌ Project virtual environment: ${RED}Not found${NC}"
    venv_exists=false
fi

# Step 4: Check if project package is installed
package_installed=false
if [ "$venv_exists" = true ]; then
    # Check in virtual environment
    if source "$VENV_NAME/bin/activate" 2>/dev/null && pip show initializer &>/dev/null; then
        package_version=$(pip show initializer | grep "Version:" | cut -d' ' -f2)
        echo -e "  ✅ Project package: ${GREEN}Installed${NC} (v$package_version) [venv]"
        package_installed=true
    else
        echo -e "  ❌ Project package: ${RED}Not installed in venv${NC}"
    fi
else
    # Check in global environment if venv doesn't exist
    if command -v python3 &>/dev/null && python3 -m pip show initializer &>/dev/null 2>&1; then
        package_version=$(python3 -m pip show initializer | grep "Version:" | cut -d' ' -f2)
        echo -e "  ✅ Project package: ${GREEN}Installed${NC} (v$package_version) [global]"
        package_installed=true
    else
        echo -e "  ❌ Project package: ${RED}Not installed${NC}"
    fi
fi

# Step 5: Check if command line tool is available
if command -v initializer &>/dev/null; then
    echo -e "  ✅ Command line tool (initializer): ${GREEN}Available in PATH${NC}"
    command_line_tool_available=true
else
    echo -e "  ❌ Command line tool (initializer): ${RED}Not available in PATH${NC}"
    command_line_tool_available=false
fi

echo ""

### Check if everything is already installed
if [ "$python_ok" = true ] && [ "$venv_exists" = true ] && [ "$package_installed" = true ] && [ "$command_line_tool_available" = true ]; then
    echo -e "${GREEN}✅ Everything is already installed and working!${NC}"
    echo ""
    echo -e "${BLUE}💡 You can now run:${NC}"
    echo -e "  ${GREEN}./run.sh${NC}              # Start the application"
    echo -e "  ${GREEN}initializer${NC}           # Or run directly"
    echo -e "  ${GREEN}./uninstall.sh${NC}       # If you want to uninstall"
    echo ""
    if ! ask_confirmation "🤔 Do you want to reinstall anyway?" "n"; then
        echo -e "${GREEN}✅ Installation skipped.${NC}"
        exit 0
    fi
    echo ""
fi

### Display what will be installed/updated
echo -e "${YELLOW}📦 The following will be installed/updated:${NC}"
echo ""

if [ "$python_ok" = false ]; then
    echo -e "  🔧 Python installation: ${YELLOW}Python 3.8+ will be installed${NC}"
fi

if [ "$venv_functional" = false ]; then
    echo -e "  🔧 System packages: ${YELLOW}python3-venv, python3-dev, python3-pip${NC}"
fi

if [ "$venv_exists" = false ]; then
    echo -e "  📦 Virtual environment: ${YELLOW}$VENV_NAME/${NC}"
fi

if [ "$package_installed" = false ]; then
    if [ "$INSTALL_DEV" = true ]; then
        echo -e "  🐍 Python package: ${YELLOW}initializer (development mode)${NC}"
        echo -e "  🛠️  Development tools: ${YELLOW}pytest, black, flake8, mypy${NC}"
    else
        echo -e "  🐍 Python package: ${YELLOW}initializer${NC}"
    fi
fi

if [ "$command_line_tool_available" = false ]; then
    echo -e "  🔗 Command line tool: ${YELLOW}initializer${NC}"
fi

echo ""

### Main confirmation
if ! ask_confirmation "🤔 Do you want to proceed with installation?" "y"; then
    echo -e "${GREEN}✅ Installation cancelled.${NC}"
    exit 0
fi

echo ""

echo -e "${BLUE}🚀 Installing Linux System Initializer ($INSTALL_MODE mode)...${NC}"
if [ "$AUTO_CONFIRM" = true ]; then
    echo -e "${YELLOW}🤖 Auto-confirm mode enabled - all prompts will be automatically accepted${NC}"
fi

# Check if any installation is needed and perform network connectivity check once
NEEDS_INSTALLATION=false
if [ "$python_ok" = false ] || [ "$venv_functional" = false ]; then
    NEEDS_INSTALLATION=true
    echo ""
    echo -e "${BLUE}🔍 Checking package manager connectivity before installation...${NC}"
    
    # Detect OS type for connectivity check
    if [ -f /etc/debian_version ]; then
        # Ubuntu/Debian system
        if check_and_handle_package_manager_connectivity "ubuntu"; then
            MIRROR_FIX_APPLIED=true
            echo -e "${GREEN}✅ Mirror configuration applied successfully${NC}"
        else
            echo -e "${BLUE}💡 Using original package sources${NC}"
        fi
    elif [ -f /etc/redhat-release ]; then
        # RedHat/CentOS/Fedora system
        check_and_handle_package_manager_connectivity "redhat"
        echo -e "${BLUE}💡 Network check completed for RedHat system${NC}"
    fi
    echo ""
fi

# Skip redundant checks - status was already verified above

# Install Python3 if needed (Step 1: Python interpreter only)
if [ "$python_ok" = false ]; then
    echo -e "${BLUE}🐍 Installing Python 3 interpreter...${NC}"
    echo ""
    
    # Detect OS and install Python3 only
    if [ -f /etc/debian_version ]; then
        # Debian/Ubuntu
        echo -e "${BLUE}📋 Detected Debian/Ubuntu system${NC}"
        
        echo ""
        echo -e "${BLUE}📦 Required package:${NC}"
        echo -e "  - ${GREEN}python3${NC} (Python interpreter)"
        echo ""
        
        if ask_confirmation "🔧 Do you want to install Python 3 now?"; then
            echo -e "${BLUE}🔧 Installing Python 3...${NC}"
            
            # Check if we have root or sudo access
            if [ "$EUID" -eq 0 ]; then
                # Running as root
                apt update && apt install -y python3
            elif sudo -n true 2>/dev/null; then
                # Have passwordless sudo access
                sudo apt update && sudo apt install -y python3
            else
                # No sudo access, try with password prompt
                echo -e "${YELLOW}🔑 Sudo access required. You may be prompted for your password.${NC}"
                if sudo apt update && sudo apt install -y python3; then
                    echo -e "${GREEN}✅ Installation completed with sudo${NC}"
                else
                    echo -e "${RED}❌ Failed to install Python 3${NC}"
                    echo -e "${YELLOW}💡 You can install Python 3 manually and re-run this script:${NC}"
                    echo -e "    ${GREEN}sudo apt update${NC}"
                    echo -e "    ${GREEN}sudo apt install python3${NC}"
                    exit 1
                fi
            fi
            
            if [ $? -eq 0 ]; then
                echo -e "${GREEN}✅ Python 3 installed successfully${NC}"
                # Re-check Python version
                if command -v python3 &>/dev/null; then
                    python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
                    echo -e "${GREEN}✅ Python $python_version is now available${NC}"
                    python_ok=true
                    # Re-check venv functionality after Python installation
                    test_venv_recheck="test-venv-recheck-$$"
                    if python3 -m venv "$test_venv_recheck" &>/dev/null; then
                        rm -rf "$test_venv_recheck" &>/dev/null
                        venv_functional=true
                    else
                        rm -rf "$test_venv_recheck" &>/dev/null
                    fi
                fi
            else
                echo -e "${RED}❌ Failed to install Python 3${NC}"
                exit 1
            fi
        else
            echo -e "${RED}❌ Python 3 installation cancelled by user${NC}"
            echo -e "${YELLOW}💡 You can install Python 3 manually and re-run this script:${NC}"
            echo -e "    ${GREEN}sudo apt update${NC}"
            echo -e "    ${GREEN}sudo apt install python3${NC}"
            exit 1
        fi
        
    elif [ -f /etc/redhat-release ]; then
        # RHEL/CentOS/Fedora
        echo -e "${BLUE}📋 Detected Red Hat/CentOS/Fedora system${NC}"
        
        if [ "$EUID" -eq 0 ] || sudo -n true 2>/dev/null; then
            echo ""
            echo -e "${BLUE}📦 Required package:${NC}"
            echo -e "  - ${GREEN}python3${NC} (Python interpreter)"
            echo ""
            
            if ask_confirmation "🔧 Do you want to install Python 3 now?"; then
                echo -e "${BLUE}🔧 Installing Python 3...${NC}"
                
                # Install Python3
                if command -v dnf &> /dev/null; then
                    if [ "$EUID" -eq 0 ]; then
                        dnf install -y python3
                    else
                        sudo dnf install -y python3
                    fi
                elif command -v yum &> /dev/null; then
                    if [ "$EUID" -eq 0 ]; then
                        yum install -y python3
                    else
                        sudo yum install -y python3
                    fi
                fi
                
                if [ $? -eq 0 ]; then
                    echo -e "${GREEN}✅ Python 3 installed successfully${NC}"
                    # Re-check Python version
                    if command -v python3 &>/dev/null; then
                        python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
                        echo -e "${GREEN}✅ Python $python_version is now available${NC}"
                        python_ok=true
                        # Re-check venv functionality after Python installation
                        test_venv_recheck2="test-venv-recheck2-$$"
                        if python3 -m venv "$test_venv_recheck2" &>/dev/null; then
                            rm -rf "$test_venv_recheck2" &>/dev/null
                            venv_functional=true
                        else
                            rm -rf "$test_venv_recheck2" &>/dev/null
                        fi
                    fi
                else
                    echo -e "${RED}❌ Failed to install Python 3${NC}"
                    exit 1
                fi
            else
                echo -e "${RED}❌ Python 3 installation cancelled by user${NC}"
                echo -e "${YELLOW}💡 You can install Python 3 manually and re-run this script:${NC}"
                if command -v dnf &> /dev/null; then
                    echo -e "    ${GREEN}sudo dnf install python3${NC}"
                else
                    echo -e "    ${GREEN}sudo yum install python3${NC}"
                fi
                exit 1
            fi
        else
            echo -e "${YELLOW}🔑 Root/sudo access required to install Python 3. Please run:${NC}"
            if command -v dnf &> /dev/null; then
                echo -e "    ${GREEN}sudo dnf install python3${NC}"
            else
                echo -e "    ${GREEN}sudo yum install python3${NC}"
            fi
            echo -e "${YELLOW}Then re-run this script.${NC}"
            exit 1
        fi
        
    else
        # Unsupported OS
        echo -e "${RED}❌ Unsupported operating system for automatic Python installation${NC}"
        echo ""
        echo -e "${YELLOW}💡 Please install Python 3.8+ manually:${NC}"
        echo -e "  - Visit: ${BLUE}https://www.python.org/downloads/${NC}"
        echo -e "  - Or use your system's package manager"
        echo ""
        exit 1
    fi
    
    echo ""
fi

# Install system dependencies if needed (Step 2: venv, dev, pip packages)
if [ "$python_ok" = true ] && [ "$venv_functional" = false ]; then
    echo -e "${BLUE}🔍 Installing system dependencies...${NC}"
    echo ""
    
    # Detect OS and install required packages
    if [ -f /etc/debian_version ]; then
        # Debian/Ubuntu
        echo -e "${BLUE}📋 Detected Debian/Ubuntu system${NC}"
        echo -e "${BLUE}💡 Installing required packages...${NC}"
        
        echo ""
        echo -e "${BLUE}📦 Required system packages:${NC}"
        echo -e "  - ${GREEN}python3-venv${NC} (virtual environment support)"
        echo -e "  - ${GREEN}python3-dev${NC} (Python development headers)"
        echo -e "  - ${GREEN}python3-pip${NC} (Python package installer)"
        echo ""
        
        if ask_confirmation "🔧 Do you want to install these system packages now?"; then
            echo -e "${BLUE}🔧 Installing python3-venv and related packages...${NC}"
            
            # Install packages using pre-configured sources with proper privilege handling
            if [ "$EUID" -eq 0 ]; then
                # Running as root
                install_ubuntu_packages
            elif sudo -n true 2>/dev/null; then
                # Have passwordless sudo access
                install_ubuntu_packages
            else
                # No sudo access, try with password prompt
                echo -e "${YELLOW}🔑 Sudo access required. You may be prompted for your password.${NC}"
                install_ubuntu_packages
            fi
            
            if [ $? -eq 0 ]; then
                echo -e "${GREEN}✅ System packages installed successfully${NC}"
            else
                echo -e "${RED}❌ Failed to install system packages${NC}"
                echo -e "${YELLOW}💡 You can install the packages manually and re-run this script:${NC}"
                echo -e "    ${GREEN}sudo apt update${NC}"
                echo -e "    ${GREEN}sudo apt install python3-venv python3-dev python3-pip${NC}"
                exit 1
            fi
        else
            echo -e "${RED}❌ Installation cancelled by user${NC}"
            echo -e "${YELLOW}💡 You can install the packages manually and re-run this script:${NC}"
            echo -e "    ${GREEN}sudo apt update${NC}"
            echo -e "    ${GREEN}sudo apt install python3-venv python3-dev python3-pip${NC}"
            exit 1
        fi
        
    elif [ -f /etc/redhat-release ]; then
        # RHEL/CentOS/Fedora
        echo -e "${BLUE}📋 Detected Red Hat/CentOS/Fedora system${NC}"
        echo -e "${BLUE}💡 Installing required packages...${NC}"
        
        if [ "$EUID" -eq 0 ] || sudo -n true 2>/dev/null; then
            echo ""
            echo "📦 Required system packages:"
            echo "  - python3-venv (virtual environment support)"
            echo "  - python3-devel (Python development headers)"
            echo "  - python3-pip (Python package installer)"
            echo ""
            
            if ask_confirmation "🔧 Do you want to install these system packages now?"; then
                echo -e "${BLUE}🔧 Installing python3-venv and related packages...${NC}"
                
                # Install packages
                install_redhat_packages
                
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
        echo -e "${RED}❌ Unknown Linux distribution${NC}"
        echo -e "${YELLOW}💡 Please install the python3-venv package for your system:${NC}"
        echo -e "  - ${GREEN}Debian/Ubuntu:${NC} apt install python3-venv python3-dev"
        echo -e "  - ${GREEN}RHEL/CentOS:${NC}   yum install python3-venv python3-devel"
        echo -e "  - ${GREEN}Fedora:${NC}        dnf install python3-venv python3-devel"
        exit 1
    fi
fi

# Final verification after potential package installation
echo -e "${BLUE}🧪 Final verification of virtual environment functionality...${NC}"
final_test_venv="final-test-venv-$$"
if python3 -m venv "$final_test_venv" &> /dev/null; then
    rm -rf "$final_test_venv" &> /dev/null
    echo "✅ Virtual environment functionality confirmed"
else
    # Clean up any partially created directory
    rm -rf "$final_test_venv" &> /dev/null
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
        # Clean up any partially created directory
        rm -rf "$VENV_NAME" &> /dev/null
        echo "❌ Failed to create virtual environment"
        echo "💡 Try running: ./install.sh"
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