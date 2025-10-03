# Repository Guidelines

## Project Structure & Module Organization
Core Python sources live in `src/initializer/`, split into `modules/` for backend logic, `ui/` for Textual screens and components, and `utils/` for helpers. Configuration YAML sits under `config/` (app, modules, themes, presets). Executable entry points are `main.py` for local runs and `run.sh` for virtualenv bootstrapping. Legacy Bash scripts remain in `legacy/` for reference only; do not modify them without a migration plan.

## Build, Test, and Development Commands
Bootstrap dependencies with `./install.sh` (creates `.venv` and installs extras). Launch the TUI via `./run.sh` or `python -m initializer.main --preset server` for preset validation. Install editable dev tooling using `pip install -e .[dev]`. Run static checks with `flake8 src` and `black --check src`. Execute fast smoke tests using `pytest -q`. Use `tools/sync-to-remote.sh -n` to dry-run remote sync before deployments.

## Coding Style & Naming Conventions
Follow PEP 8 with 4-space indentation and an 88-character line width (enforced by Black). Modules and packages use lowercase underscores (`system_info.py`), classes use PascalCase (`HomebrewScreen`), and functions plus variables use snake_case. Keep Rich/Textual view code declarative and move heavy logic into `modules/`. Run `black src` and `flake8` before submitting changes.

## Testing Guidelines
Adopt `pytest` for unit and integration coverage; place new suites under `tests/` mirroring the `src/initializer/` structure. Name files `test_<feature>.py` and functions `test_<case>()`. Aim to exercise new module logic plus UI screen controller methods and include fixtures for configuration samples in `config/`. Run `pytest --maxfail=1 --disable-warnings -q` locally and add regression tests whenever fixing bugs.

## Commit & Pull Request Guidelines
Match existing history by prefixing commits with an emoji plus Conventional-style type, e.g. `✨ feat: add progress overlay screen`. Keep messages in imperative mood and reference issues with `refs #123` when available. Pull requests should describe scope, call out configuration changes, list validation commands, and include screenshots or terminal recordings for UI tweaks. Request review once CI (formatters, lint, pytest) passes and ensure remote sync instructions are updated when deployment behavior changes.

## Configuration & Safety Notes
Keep sensitive values out of YAML presets; use environment variables when needed. Validate new configuration keys in `config/modules.yaml` and update `ConfigManager` defaults. When touching installer logic, test both `.venv` workflows (`install.sh`, `run.sh`) and `python main.py` entry points. For remote automation, prefer the provided sync script and confirm the target host before running destructive operations.

## 0. 阅读须知
- 本指南适用于仓库全部目录，除非子目录另有 AGENTS.md 覆盖。
- 坚持“强制优先、结果导向、可审计”，所有流程需可追溯。
- 如与本指南冲突的用户显式指令出现，必须遵循并在“前置说明”记录偏差原因，同时在 Serena 知识记忆中补录变更记录。

## 1. 治理总则
### 1.1 适用范围
- 覆盖整个仓库；若子目录另有 `AGENTS.md`，以子目录指南为准。
- 新建文件编码统一为 UTF-8（无 BOM），沟通、注释与文档统一使用中文。

### 1.2 执行优先级（更新）
- 用户命令优先（新增）：当用户在当前会话中以明确的自然语言、脚本或命令形式下达指令，且与本指南或任一 AGENTS.md 存在冲突时，应以用户命令为准；同时需遵守“2. 强制约束（MUST）”之安全与合规条款。
  - 冲突处置：遵从用户命令执行，并在“前置说明”记录偏差原因、影响范围与回滚思路；同步在 Serena 知识记忆补录时间戳、文件清单与变更摘要。
  - 优先级顺序：用户显式命令 > 子目录 AGENTS.md > 根目录 AGENTS.md > 其他项目文档/默认约定。
- 禁用一切远端 CI/CD 自动化；构建、测试、发布、验证优先通过本地 AI 驱动流程执行。
- Serena 优先：研究、检索、结构化编辑与知识记录优先使用 Serena 工具链。
- 受阻降级：当出现以下任一条件时，允许降级到 Codex CLI 的 `apply_patch` 或安全 `shell` 编辑（仅限仓库内）：
  - Serena 无法对非符号文件（如 Markdown/配置/纯文本/新建源文件）执行插入、替换或创建操作。
  - Serena 返回 “File or directory not found / symbol not found / Not supported for this file type”等不可恢复错误。
  - Serena 无法在目标目录创建新文件或多次重试后仍失败。
- 降级使用须在回复“前置说明”中标注原因、影响范围与回滚思路，并将操作摘要写入 Serena 知识记忆。

### 1.3 治理原则
1. 标准化生态优先：能用主流稳定库或官方 SDK 时不得自研，并记录替换进度。
2. 质量优先：出现报错先修复；所有结论需具备证据支撑。
3. 工具优先：优先 Serena；受阻可降级，但必须留痕与事后补录。
4. 全景洞察：结合代码上下文与多来源数据形成决策。
5. 透明留痕：关键决策、证据、变更写入 Serena，保持可审计性。
6. 结果导向：以量化目标、SLO/SLI 与交付衡量成效。
7. 持续改进：任务收尾复盘并刷新知识库/最佳实践。

## 2. 强制约束（MUST）
### 2.1 工作执行
- 仅可运行安全命令，严禁 `rm -rf` 等破坏性操作或泄露敏感信息。
- 新增或修改代码需补齐中文文档/必要注释，禁止占位或 `NotImplemented`。
- 输出中断（stream error）需基于已写内容无缝续写。

### 2.2 交互与文档
- 在记录中明确假设、数据时效、输入来源与不确定性。
- 使用规范化模板，确保回复与文档可追溯。
- 所有偏差说明与关键结论需同步登记至 Serena 知识记忆。

### 2.3 安全与合规
- 网络仅用于读取公开资料，优先官方与权威来源；禁止上传敏感信息。
- HTTP 429 固定退避 20s；HTTP 5xx/超时退避 2s 后最多重试一次；仍失败需提供保守离线答案与下一步建议。
- 默认无安全基线，任何多余的安全性设计需拒绝或拆除，并在 Serena 中记录处理结果。

### 2.4 变更策略
- 优先复用标准化生态能力；能用主流库/官方 SDK 的场景禁止自研。
- 默认允许不兼容改动以清理过时代码/接口与文档，但须在交付说明中明确迁移或“无迁移，直接替换”。
- 交付必须完整具体，禁止提交 MVP 或占位方案。

### 2.5 操作留痕（更新）
- 文件读写与制品留存“Serena 优先”。当 Serena 不可用或不适用时，可降级到 Codex CLI 的 `apply_patch` 或安全 `shell` 编辑。
- 每次降级必须：
  1) 在回复“前置说明”记录触发条件、操作范围、回滚方式；
  2) 在 Serena 知识记忆创建条目，包含时间戳、文件清单、变更摘要与证据链接；
  3) Serena 恢复后补录最终状态与验证结果。
- 严禁在仓库外新增本地目录或使用线下介质存放制品。

## 3. 工具与调研平台
### 3.0 工具矩阵概览
| 工具 | 核心职责 | Serena 联动要求 |
| --- | --- | --- |
| Serena MCP | 统一调度代码/知识工具、维护知识记忆、结构化检索 | 指令由 Serena 发起并登记留痕 |
| Sequential Thinking MCP | 产出可追溯思考链 | 思考结论回写 Serena 并驱动计划 |
| Context7 MCP | 官方文档与权威资料首选 | 记录关键词、版本与访问日期 |
| DeepWiki MCP | 社区实践与框架洞见补充 | 记录降级原因与检索摘要 |

### 3.1 Serena MCP（更新）
- 接入校验：每次会话先调用 `serena__activate_project`/`serena__check_onboarding_performed` 并在“前置说明”记录结果。
- 结构化检索主线：`serena__find_symbol` → `serena__search_for_pattern` →（若支持）编辑工具；必要时使用 `serena__find_referencing_symbols` 评估影响面。
- 失败处置与降级：出现文件/符号不支持、路径不存在或多次重试失败时，允许降级到 Codex `apply_patch`/安全 `shell`。降级后仍需将变更摘要与证据写回 Serena 知识记忆。
- 索引维护、工具巡检、知识治理同原规范执行。

### 3.5 外部检索与降级（保留）
- Context7 → DeepWiki → `web.run` 的降级顺序保持不变，并记录检索语句、筛选条件与访问日期。

### 3.9 编辑与文件操作降级矩阵（新增）
| 触发条件 | 允许的降级动作 | 必填留痕 |
| --- | --- | --- |
| Serena 不支持非符号文件编辑/新建 | 使用 `apply_patch` 创建/替换/插入；必要时安全 `shell` | 前置说明+Serena 记忆条目 |
| Serena 报 `symbol not found` 但需改 Markdown/配置 | 同上 | 同上 |
| 目录创建或跨目录移动失败 | `apply_patch` + 结构化变更摘要 | 同上 |

## 4. 标准工作流（更新）
1) Research：先用 Sequential Thinking 输出可追溯思考链；由 Serena 协调本地检索与结构化分析；若需外部证据按 Context7 → DeepWiki → 其他渠道，并记录降级原因。
2) Plan：通过 `update_plan` 维护步骤、状态与验收标准。
3) Implement：优先 Serena；若受阻，按 3.9 矩阵安全降级到 `apply_patch`/shell，小步提交并补齐中文文档/注释。
4) Verify：本地自动执行构建/测试/回归；记录结果至 Serena。
5) Deliver：总结变更、风险、验证证据，并在 Serena 知识记忆归档，覆盖过期记录。

## 5. 质量与安全门槛（保留）
- 构建/静态检查零报错；测试矩阵通过；覆盖率 ≥ 90%；依赖无高危 CVE；流程可重复、版本锁定、可回滚。
- 测试与观测：单元/集成/契约/E2E/性能/压力/容量/混沌与回归覆盖关键路径；采用轻量观测方案，禁止 Prometheus/OpenTelemetry 体系。

## 6. 交付与存档（保留）
- 发布需含迁移脚本、割接窗口、回滚方案并归档；图表与快照以文本或附件形式存入 Serena；条目标注“最后验证日期”。

## 7. 模板与清单（保留）
### 7.1 证据表（CSV 头）
#### ```
id,type,source,title,version,publish_date,access_date,link,applies_to
#### ```
### 7.2 技术选型对比矩阵（CSV 头）
#### ```
option,version,maturity,community_health,performance,security,maintainability,learning_cost,ecosystem,compatibility,cost,risk,score,notes,evidences
#### ```
### 7.3 性能基准配置（YAML 示例）
#### ```
target: service-x
workload:
  rps: [100, 500, 1000]
  duration: 5m
metrics:
  - p50_latency_ms
  - p95_latency_ms
  - p99_latency_ms
  - throughput_rps
  - cpu_pct
  - mem_mb
pass_thresholds:
  p99_latency_ms: 200
  throughput_rps: 800
#### ```
### 7.4 风险登记表（CSV 头）
#### ```
id,description,category,likelihood,impact,mitigation,owner,status
#### ```
### 7.5 ADR 模板（Markdown）
#### ```
# ADR-NN: <决策标题>
日期：YYYY-MM-DD  | 状态：提议/通过/废弃

## 背景
<业务背景与问题描述>

## 备选方案
- 方案A：优缺点
- 方案B：优缺点

## 决策
<选定方案与理由（含权衡矩阵得分）>

## 后果
<正/负面影响、迁移/回滚影响>

## 引用
- [证据#] ...
#### ```
### 7.6 SDS 目录（保留）
- 概述与目标（含 SLO/SLI 与成功标准）
- 架构与部署（Mermaid/PlantUML）
- 数据流/时序与错误路径
- 接口契约、错误码、限流策略
- 数据模型与一致性/事务策略
- 观测性与容量规划
- 安全与合规
- 风险与缓解措施
- 验收与发布计划

## 8. 工程师行为准则（更新）
- 求证先行，确认胜过假设；关键结论需标注明确证据或工具结果。
- 标准优先，能复用主流生态不得自研。
- 质量共担，测试充分并主动补齐验证证据。
- 透明反馈：Serena 优先；若降级，须记录触发原因与事后补录。
- 持续精进：复盘沉淀改进点，推动流程与知识库迭代。
