#!/usr/bin/env bash

### description: change the source of homebrew
### create time: 2024-04-07 (yyyy-MM-dd)
### author: DeltaV235

# backup current source of homebrew and change the source to the Tsinghua mirror site
echo -e "${LIGHT_BLUE}Changing the source of Homebrew...${NC}"
cd "$(brew --repo)"
git remote set-url origin https://mirrors.tuna.tsinghua.edu.cn/git/homebrew/brew.git
cd "$(brew --repo)/Library/Taps/homebrew/homebrew-core"
git remote set-url origin https://mirrors.tuna.tsinghua.edu.cn/git/homebrew/homebrew-core.git
echo -e "${LIGHT_GREEN}Homebrew source changed successfully!${NC}"

complete_break
