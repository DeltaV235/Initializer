#!/bin/bash

### description: get distribution name
### create time: 2020-10-02 (yyyy-MM-dd)
### author: deltaV235

KERNEL_NAME=$(uname -s)
if [ "$KERNEL_NAME" == "Darwin" ]; then
  OS_NAME=$(sw_vers | grep ProductName | cut -d ':' -f2 | xargs)" "$(sw_vers | grep ProductVersion| cut -d ':' -f2 | xargs)
else
  OS_NAME=$(grep "^PRETTY_NAME" /etc/os-release | cut -d '=' -f2 | cut -d '"' -f2)
fi

echo -e "${LIGHT_CYAN}OS Name: ${NC}${OS_NAME}"
