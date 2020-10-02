#!/bin/bash

### description: get distribution name
### create time: 2020-10-02 (yyyy-MM-dd)
### author: deltaV235

OS_NAME=$(cat /etc/os-release | grep ^PRETTY_NAME | cut -d '=' -f2 | cut -d '"' -f2)

echo -e "${LIGHT_CYAN}OS Name : ${NC}${OS_NAME}"
