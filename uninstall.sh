#!/bin/bash

### Linux System Initializer Uninstall Script
### Safely removes the application and its virtual environment

set -e

VENV_NAME=".venv"
PROJECT_NAME="Linux System Initializer"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

### Ask for user confirmation
ask_confirmation() {
    local prompt="$1"
    local default="${2:-n}"
    
    while true; do
        if [ "$default" = "y" ]; then
            printf "${YELLOW}$prompt [Y/n]: ${NC}"
            read -r answer
            answer=${answer:-y}
        else
            printf "${YELLOW}$prompt [y/N]: ${NC}"
            read -r answer
            answer=${answer:-n}
        fi
        
        case $answer in
            [Yy]|[Yy][Ee][Ss]) return 0 ;;
            [Nn]|[Nn][Oo]) return 1 ;;
            *) echo "Please answer yes or no" ;;
        esac
    done
}

### Display banner
echo -e "${BLUE}🗑️  $PROJECT_NAME Uninstaller${NC}"
echo "================================="
echo ""

### Check current status
echo -e "${BLUE}📋 Current installation status:${NC}"

# Check if virtual environment exists
if [ -d "$VENV_NAME" ]; then
    echo -e "  ✅ Virtual environment: ${GREEN}Found${NC} ($VENV_NAME)"
    venv_exists=true
else
    echo -e "  ❌ Virtual environment: ${RED}Not found${NC}"
    venv_exists=false
fi

# Check if package is installed (if venv exists)
package_installed=false
if [ "$venv_exists" = true ]; then
    if source "$VENV_NAME/bin/activate" 2>/dev/null && pip show initializer &>/dev/null; then
        echo -e "  ✅ Python package: ${GREEN}Installed${NC}"
        package_installed=true
        # Get package info
        package_version=$(pip show initializer | grep "Version:" | cut -d' ' -f2)
        echo -e "  📦 Package version: ${BLUE}$package_version${NC}"
    else
        echo -e "  ❌ Python package: ${RED}Not installed${NC}"
    fi
fi

# Check if command is available
if command -v initializer &>/dev/null; then
    echo -e "  ✅ Command 'initializer': ${GREEN}Available${NC}"
    command_available=true
else
    echo -e "  ❌ Command 'initializer': ${RED}Not available${NC}"
    command_available=false
fi

echo ""

### Check if anything needs to be uninstalled
if [ "$venv_exists" = false ] && [ "$package_installed" = false ] && [ "$command_available" = false ]; then
    echo -e "${GREEN}✅ Nothing to uninstall. The system is already clean.${NC}"
    exit 0
fi

### Display what will be removed
echo -e "${YELLOW}⚠️  The following items will be removed:${NC}"
echo ""

if [ "$package_installed" = true ]; then
    echo -e "  🗑️  Python package: ${RED}initializer v$package_version${NC}"
fi

if [ "$command_available" = true ]; then
    echo -e "  🗑️  Command line tool: ${RED}initializer${NC}"
fi

if [ "$venv_exists" = true ]; then
    echo -e "  🗑️  Virtual environment: ${RED}$VENV_NAME/${NC}"
    echo -e "     - All installed Python packages"
    echo -e "     - Virtual environment directory (~$(du -sh "$VENV_NAME" 2>/dev/null | cut -f1 || echo "unknown size"))"
fi

echo ""
echo -e "${BLUE}📁 The following will be preserved:${NC}"
echo -e "  ✅ Project source code"
echo -e "  ✅ Configuration files"
echo -e "  ✅ Documentation"
echo -e "  ✅ Legacy scripts"
echo ""

### Main confirmation
if ! ask_confirmation "🤔 Do you want to proceed with uninstallation?" "n"; then
    echo -e "${GREEN}✅ Uninstallation cancelled.${NC}"
    exit 0
fi

echo ""
echo -e "${BLUE}🔄 Starting uninstallation process...${NC}"

### Step 1: Uninstall Python package
if [ "$package_installed" = true ]; then
    echo ""
    echo -e "${BLUE}📦 Step 1: Uninstalling Python package...${NC}"
    
    if source "$VENV_NAME/bin/activate" && pip uninstall initializer -y; then
        echo -e "  ✅ Python package uninstalled successfully"
    else
        echo -e "  ⚠️  Failed to uninstall Python package (continuing anyway)"
    fi
fi

### Step 2: Remove virtual environment
if [ "$venv_exists" = true ]; then
    echo ""
    echo -e "${BLUE}🗂️  Step 2: Removing virtual environment...${NC}"
    
    if ask_confirmation "   Remove virtual environment directory '$VENV_NAME'?" "y"; then
        if rm -rf "$VENV_NAME"; then
            echo -e "  ✅ Virtual environment removed successfully"
        else
            echo -e "  ❌ Failed to remove virtual environment"
            exit 1
        fi
    else
        echo -e "  ⏭️  Virtual environment preserved"
    fi
fi

### Step 3: Optional project cleanup
echo ""
echo -e "${BLUE}🧹 Step 3: Optional cleanup...${NC}"

# Clean up Python cache
if [ -d "__pycache__" ] || find . -name "*.pyc" -o -name "__pycache__" | grep -q .; then
    if ask_confirmation "   Remove Python cache files (__pycache__, *.pyc)?" "y"; then
        find . -name "*.pyc" -delete 2>/dev/null || true
        find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
        echo -e "  ✅ Python cache files removed"
    fi
fi

# Clean up logs
if [ -d "logs" ] && [ "$(ls -A logs 2>/dev/null)" ]; then
    if ask_confirmation "   Remove log files (logs/)?" "n"; then
        if rm -rf logs/*; then
            echo -e "  ✅ Log files removed"
        fi
    fi
fi

# Optional: Remove entire project
echo ""
echo -e "${RED}⚠️  DANGEROUS OPERATION${NC}"
if ask_confirmation "   Remove entire project directory? (THIS CANNOT BE UNDONE!)" "n"; then
    echo ""
    echo -e "${RED}🚨 FINAL WARNING: This will delete ALL project files!${NC}"
    echo -e "${RED}   Including: source code, configuration, documentation, legacy scripts${NC}"
    echo ""
    
    if ask_confirmation "   Are you ABSOLUTELY SURE you want to delete everything?" "n"; then
        cd ..
        project_dir=$(basename "$PWD")
        if rm -rf "$project_dir"; then
            echo -e "${GREEN}✅ Project directory removed completely${NC}"
            echo -e "${GREEN}🎉 Uninstallation completed successfully${NC}"
            exit 0
        else
            echo -e "${RED}❌ Failed to remove project directory${NC}"
            exit 1
        fi
    fi
fi

### Summary
echo ""
echo -e "${GREEN}🎉 Uninstallation completed successfully!${NC}"
echo ""
echo -e "${BLUE}📋 Summary:${NC}"

if [ "$package_installed" = true ]; then
    echo -e "  ✅ Python package removed"
fi

if [ "$venv_exists" = true ]; then
    echo -e "  ✅ Virtual environment removed"
fi

echo -e "  ✅ Project files preserved"
echo ""
echo -e "${BLUE}💡 To reinstall in the future:${NC}"
echo -e "  1. Run: ${GREEN}./install.sh${NC}"
echo -e "  2. Run: ${GREEN}./run.sh${NC}"
echo ""