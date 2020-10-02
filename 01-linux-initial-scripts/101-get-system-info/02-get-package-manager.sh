#!/bin/bash

### description: get distribution name
### create time: 2020-10-02 (yyyy-MM-dd)
### author: deltaV235

if [[ $(echo "${OS_NAME}" | awk '{print tolower($0)}' | grep "^ubuntu") ]]; then
  PACKAGE_MANAGER="apt"
elif [[ $(echo "${OS_NAME}" | awk '{print tolower($0)}' | grep "^centos") ]]; then
  PACKAGE_MANAGER="yum"
fi

echo -e "${LIGHT_CYAN}Package Manager : ${NC}${PACKAGE_MANAGER}"
