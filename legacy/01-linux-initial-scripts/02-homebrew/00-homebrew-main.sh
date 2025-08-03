#!/bin/bash

### description: check if the system can install homebrew
### create time: 2024-04-07 (yyyy-MM-dd)
### author: DeltaV235

while true; do
  clear

  echo -e "${BLUE}${DIVIDING_LINE}${NC}"
  echo -e "1. Install Homebrew""${BREW_INSTALLED_LABEL}"
  echo "2. Change Source of Homebrew"
  echo "3. Install Package by Homebrew"
  echo -e "${BLUE}${DIVIDING_LINE}${NC}"
  echo "0. Return to Main Menu"
  echo -e "${BLUE}${DIVIDING_LINE}${NC}"
  read -p "Please enter the number you want to execute: " choice

  case $choice in
    1)
      clear
      # if brew is not been install then execute the installation script
      if [ ! "$(command -v brew)" ]; then
          source 02-install-homebrew/01-install-homebrew.sh
      else
          echo -e "${LIGHT_GREEN}Homebrew has been installed${NC}"
      fi
      complete_break
      ;;
    2)
      clear
      source 02-install-homebrew/02-change-homebrew-source.sh
      complete_break
      ;;
    0)
      clear
      break
      ;;
    *)
      echo "Invalid input!"
      ;;
  esac

done