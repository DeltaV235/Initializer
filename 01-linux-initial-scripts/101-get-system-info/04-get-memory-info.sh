#!/bin/bash

### description: get memory information
### create time: 2020-10-02 (yyyy-MM-dd)
### author: DeltaV235

if [[ ${OS_NAME} == *"macOS"* ]]; then
  MEMORY_SIZE=$(sysctl hw.memsize | cut -d " " -f2)
  SWAP_SIZE=$(sysctl vm.swapusage | cut -d " " -f4 | tr "M" " ")
  MEMORY_SIZE_WITH_GIGABYTE=$(echo "${MEMORY_SIZE}/1024/1024/1024" | bc -l | xargs printf "%.2f")
  SWAP_SIZE_WITH_GIGABYTE=$(echo "${SWAP_SIZE}/1024" | bc -l | xargs printf "%.2f")
else
  MEMORY_SIZE=$(/usr/bin/free | grep "^Mem" | awk '{print $2}')
  SWAP_SIZE=$(/usr/bin/free | grep "^Swap" | awk '{print $2}')
  MEMORY_SIZE_WITH_GIGABYTE=$(echo "${MEMORY_SIZE}/1024/1024" | bc -l | xargs printf "%.2f")
  SWAP_SIZE_WITH_GIGABYTE=$(echo "${SWAP_SIZE}/1024/1024" | bc -l | xargs printf "%.2f")
fi

echo -e "${LIGHT_CYAN}Memory Size: ${NC}${MEMORY_SIZE_WITH_GIGABYTE} GiB"
echo -e "${LIGHT_CYAN}Swap Size: ${NC}${SWAP_SIZE_WITH_GIGABYTE} GiB"
