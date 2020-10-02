#!/bin/bash

### description: main script, the entry point of program
### create time: 2020-10-02 (yyyy-MM-dd)
### author: deltaV235

PWD=$(pwd)

source 100-assets/00-assets-index.sh

source 101-get-system-info/00-get-system-info-main.sh

bash ./01-change-package-download-mirror-to-local.sh
