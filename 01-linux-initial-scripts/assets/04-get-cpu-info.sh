#!/bin/bash

### description: get cpu information
### create time: 2020-10-02 (yyyy-MM-dd)
### author: deltaV235

CPU_PROCESSORS=$(cat /proc/cpuinfo | grep -c "model name")
CPU_MODEL_NAME=$(cat /proc/cpuinfo | grep "model name" | awk 'NR==1{print}' | cut -d ":" -f2 | cut -c2-)

echo -e "${LIGHT_CYAN}CPU Model Name : ${NC}${CPU_MODEL_NAME}"
echo -e "${LIGHT_CYAN}CPU Processors : ${NC}${CPU_PROCESSORS}"
