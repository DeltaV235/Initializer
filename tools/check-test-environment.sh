#!/usr/bin/env bash
set -euo pipefail

# Environment Check for Direct App Execution
# This script determines if Claude can directly run the application locally
# Based on the distribution type (Ubuntu vs others)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check if running on Ubuntu
is_ubuntu() {
    if command -v lsb_release >/dev/null 2>&1; then
        local distrib_id=$(lsb_release -si 2>/dev/null || echo "")
        [[ "$distrib_id" == "Ubuntu" ]]
    elif [[ -f /etc/os-release ]]; then
        grep -q "^ID=ubuntu" /etc/os-release 2>/dev/null
    else
        false
    fi
}

# Function to get distribution info
get_distro_info() {
    if command -v lsb_release >/dev/null 2>&1; then
        echo "$(lsb_release -d | cut -f2- 2>/dev/null || echo 'Unknown')"
    elif [[ -f /etc/os-release ]]; then
        grep "^PRETTY_NAME=" /etc/os-release 2>/dev/null | cut -d'"' -f2 || echo "Unknown"
    else
        echo "Unknown Linux Distribution"
    fi
}

# Main logic
main() {
    local quiet_mode=false
    local exit_code_only=false
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -q|--quiet)
                quiet_mode=true
                shift
                ;;
            -e|--exit-code-only)
                exit_code_only=true
                shift
                ;;
            -h|--help)
                cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Check if Claude can directly run the application locally.

Options:
  -q, --quiet           Only output the result (yes/no)
  -e, --exit-code-only  Only return exit code (0=can run locally, 1=use remote)
  -h, --help           Show this help message

Exit Codes:
  0  Can run application directly (Ubuntu environment)
  1  Should sync to remote server (non-Ubuntu environment)

Examples:
  $(basename "$0")                    # Show detailed information
  $(basename "$0") --quiet            # Only show yes/no
  $(basename "$0") --exit-code-only   # Only return exit code
EOF
                exit 0
                ;;
            *)
                echo "Unknown option: $1" >&2
                exit 1
                ;;
        esac
    done
    
    local distro_info=$(get_distro_info)
    
    if is_ubuntu; then
        # Ubuntu environment - Claude can run app directly
        if $exit_code_only; then
            exit 0
        elif $quiet_mode; then
            echo "yes"
        else
            echo -e "${GREEN}✅ Direct App Execution Allowed${NC}"
            echo -e "   Distribution: ${BLUE}$distro_info${NC}"
            echo -e "   Reason: Ubuntu environment detected"
            echo -e "   Action: Claude can run './run.sh' or 'python main.py' directly"
        fi
        exit 0
    else
        # Non-Ubuntu environment - should sync to remote
        if $exit_code_only; then
            exit 1
        elif $quiet_mode; then
            echo "no"
        else
            echo -e "${YELLOW}⚠️  Remote Execution Required${NC}"
            echo -e "   Distribution: ${BLUE}$distro_info${NC}"
            echo -e "   Reason: Non-Ubuntu environment detected"
            echo -e "   Action: Claude should use ${BLUE}tools/sync-to-remote.sh${NC} then run remotely"
        fi
        exit 1
    fi
}

# Run main function with all arguments
main "$@"