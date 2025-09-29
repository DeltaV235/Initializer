# 项目概览
- 目标：提供 Linux 系统初始化与配置的现代化终端界面（Python Rich/Textual TUI）。
- 技术栈：Python 3.8+，Rich，Textual，PyYAML，部分模块计划使用 psutil、distro 等。
- 结构：`src/initializer/` 下拆分 `modules/`（业务逻辑）、`ui/`（Textual 界面）、`utils/`（工具）；配置位于 `config/`；入口为 `main.py` 与 `run.sh`。