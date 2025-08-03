#!/bin/bash

### description: check if the system can install homebrew and install it
### create time: 2024-04-06 (yyyy-MM-dd)
### author: DeltaV235

# if brew is not been install then execute the installation script
if [ ! "$(command -v brew)" ]; then
  echo -e "${LIGHT_BLUE}Installing Homebrew...${NC}"
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  # if install success, print the message, otherwise, print the error message
  if [ $? -ne 0 ]; then
    echo -e "${LIGHT_RED}Failed to install Homebrew!${NC}"
  else
    echo -e "${LIGHT_GREEN}Homebrew installed successfully!${NC}"
  fi
else
  echo -e "${LIGHT_GREEN}Homebrew has been installed${NC}"
fi
