#!/bin/bash

### description: get package manager
### create time: 2020-10-02 (yyyy-MM-dd)
### author: DeltaV235

if [[ $(echo "${OS_NAME}" | awk '{print tolower($0)}' | grep "^ubuntu") ]]; then
  PACKAGE_MANAGER="apt"
elif [[ $(echo "${OS_NAME}" | awk '{print tolower($0)}' | grep "^centos") ]]; then
  PACKAGE_MANAGER="yum"
elif [ "$(command -v brew)" ]; then
  PACKAGE_MANAGER="brew"
fi

echo -e "${LIGHT_CYAN}Package Manager: ${NC}${PACKAGE_MANAGER}"
