#!/bin/bash

### description: get cpu information
### create time: 2020-10-02 (yyyy-MM-dd)
### author: deltaV235

if [[ ${OS_NAME} == *"macOS"* ]]; then
  CPU_INFO_STRING_FOR_MACOS=$(sysctl -a | grep machdep.cpu)
  CPU_MODEL_NAME=$(echo "${CPU_INFO_STRING_FOR_MACOS}" | grep machdep.cpu.brand_string | cut -d ":" -f2 | cut -c2-)
  CPU_PROCESSORS=$(echo "${CPU_INFO_STRING_FOR_MACOS}" | grep machdep.cpu.core_count | cut -d ":" -f2 | cut -c2-)
else
  CPU_MODEL_NAME=$(cat /proc/cpuinfo | grep "model name" | awk 'NR==1{print}' | cut -d ":" -f2 | cut -c2-)
  CPU_PROCESSORS=$(cat /proc/cpuinfo | grep -c "model name")
fi
echo -e "${LIGHT_CYAN}CPU Model Name: ${NC}${CPU_MODEL_NAME}"
echo -e "${LIGHT_CYAN}CPU Processors: ${NC}${CPU_PROCESSORS}"
