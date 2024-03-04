#!/bin/bash

### description: main script, the entry point of program
### create time: 2020-10-02 (yyyy-MM-dd)
### author: DeltaV235

PWD=$(pwd)

complete_break() {
  echo -e "\n${LIGHT_GREEN}Completed${NC}"
  echo "Press any key to continue..."
  read -n 1 -s -r -p ""
  echo ""
  clear
}

source 100-assets/00-assets-index.sh

bash ./01-change-package-download-mirror-to-local.sh


while true; do
clear

echo -e "${BLUE}${DIVIDING_LINE}${NC}"
echo "1. System Information"
echo -e "${BLUE}${DIVIDING_LINE}${NC}"
echo "0. Update Shell Script"
echo -e "${BLUE}${DIVIDING_LINE}${NC}"
echo "x. Exit Script"
echo -e "${BLUE}${DIVIDING_LINE}${NC}"
read -p "Please enter the number you want to execute: " choice

case $choice in
  1)
    clear
    source 101-get-system-info/00-get-system-info-main.sh
    ;;
  x)
    clear
    exit
    ;;
  *)
    echo "Invalid input!"
    ;;
esac

complete_break

done