# 代码与文档规范
- 语言：源代码遵循 PEP 8（4 空格缩进、88 列宽），模块/包用小写下划线命名，类用 PascalCase，函数与变量用 snake_case。
- 格式化：使用 Black 与 Flake8（`black --check src`，`flake8 src`）。
- 注释/文档：仓库要求中文沟通与必要中文注释；新增代码需补充说明，禁止占位实现。
- 测试：单元测试采用 pytest，测试文件命名 `tests/test_<feature>.py`，函数 `test_<case>`。