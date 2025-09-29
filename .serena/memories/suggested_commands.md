# 常用命令
- 安装依赖：`./install.sh`
- 启动应用：`./run.sh` 或 `python -m initializer.main --preset server`
- 静态检查：`flake8 src`
- 代码格式化检查：`black --check src`
- 运行单元测试：`pytest -q` 或 `pytest --maxfail=1 --disable-warnings -q`
- 远程同步：`tools/sync-to-remote.sh -n`（Dry Run），`tools/sync-to-remote.sh`（实际同步）。