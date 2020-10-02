#!/bin/bash

### description: create user by input username
### create time: 2020-10-01 (yyyy-MM-dd)
### author: deltaV235

# import terminal color
source assets/00-assets-index.sh

clear

echo -e "${YELLOW}------------------ create user (need root permision) ------------------${NC}"
read -p "please enter username: " username
sudo useradd -m $username &&
  echo -e "${LIGHT_GREEN}create user success${NC}" ||
  echo -e "${RED}create user failed${NC}"
echo -e "${YELLOW}------------------ create user finish ------------------${NC}"
read -n1 "${LIGHT_CYAN}press any key to continue${NC}"
