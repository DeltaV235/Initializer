#!/bin/bash

### description: assets index, import all assets file
### create time: 2020-10-02 (yyyy-MM-dd)
### author: deltaV235

# shellcheck source=./01-ansi-escape-code.sh
source "${PWD}"/assets/01-ansi-escape-code.sh

echo -e "${LIGHT_BLUE}--------------------------- SYSTEM INFORMATION ---------------------------${NC}"

source "${PWD}"/assets/02-get-distribution-name.sh
source "${PWD}"/assets/03-get-package-manager.sh
source "${PWD}"/assets/04-get-cpu-info.sh
source "${PWD}"/assets/05-get-memory-info.sh

echo -e "${LIGHT_BLUE}--------------------------------------------------------------------------${NC}"
