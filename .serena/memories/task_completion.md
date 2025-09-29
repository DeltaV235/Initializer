# 任务收尾指引
- 保证 `black --check src`、`flake8 src`、`pytest -q` 全部通过。
- 若修改了配置或主题，验证 `python -m initializer.main --preset <preset>` 能正常加载。
- 发布前运行 `tools/sync-to-remote.sh -n` 进行 Dry Run；必要时记录实际部署步骤。
- 变更说明需包含迁移/回滚方案及验证证据，遵循中文沟通。