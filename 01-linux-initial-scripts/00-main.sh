#!/bin/bash

### description: main script, the entry point of program
### create time: 2020-10-02 (yyyy-MM-dd)
### author: DeltaV235

PWD=$(pwd)

complete_break() {
#  echo -e "\n${LIGHT_GREEN}Completed${NC}"
  echo "Press any key to continue..."
  read -n 1 -s -r -p ""
  echo ""
  clear
}

# import terminal color and constants
source 00-assets/00-assets-index.sh

# init check
if [ "$(command -v brew)" ]; then
  BREW_INSTALLED_LABEL=" ${LIGHT_GREEN}(Homebrew Installed)${NC}"
fi

while true; do
  clear

  echo -e "${BLUE}${DIVIDING_LINE}${NC}"
  echo "1. System Information"
  echo -e "2. Homebrew Related""${BREW_INSTALLED_LABEL}"
  echo "3. Change Package Manager Source"
  echo "4. Create User"
  echo "5. Install Package by Package Manager"
  echo "6. Personal Configurations"
  echo -e "${BLUE}${DIVIDING_LINE}${NC}"
  echo "0. Update Shell Script"
  echo -e "${BLUE}${DIVIDING_LINE}${NC}"
  echo "x. Exit Script"
  echo -e "${BLUE}${DIVIDING_LINE}${NC}"
  read -p "Please enter the number you want to execute: " choice

  case $choice in
    1)
      clear
      source 01-get-system-info/00-get-system-info-main.sh
      ;;
    2)
      clear
      source 02-homebrew/00-homebrew-main.sh
      ;;
    x)
      clear
      exit
      ;;
    *)
      echo "Invalid input!"
      ;;
  esac

done