#!/bin/bash

### description: get system information
### create time: 2020-10-03 (yyyy-MM-dd)
### author: DeltaV235

echo -e "${LIGHT_BLUE}--------------------------- SYSTEM INFORMATION ---------------------------${NC}"

# shellcheck source=./01-get-distribution-name.sh
source "${PWD}"/101-get-system-info/01-get-distribution-name.sh

# shellcheck source=./02-get-package-manager.sh
source "${PWD}"/101-get-system-info/02-get-package-manager.sh

# shellcheck source=./03-get-cpu-info.sh
source "${PWD}"/101-get-system-info/03-get-cpu-info.sh

# shellcheck source=./04-get-memory-info.sh
source "${PWD}"/101-get-system-info/04-get-memory-info.sh

echo -e "${LIGHT_BLUE}${DIVIDING_LINE}${NC}"
