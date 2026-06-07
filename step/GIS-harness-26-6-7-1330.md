# GIS Agent Harness 2026-06-07 13:30 整改记录

## 调用的 skill 与 MCP

- `karpathy-guidelines`: 控制改动聚焦为本地、可验证、不过度抽象的增量。
- `python-patterns`: 新增 Python 模块使用 dataclass、显式类型和只读路径检查。
- `python-testing`: 先新增 `tests/test_health_report.py` 作为 RED，再实现命令使测试转 GREEN。
- `terminal-ops`: 以命令输出作为验证证据，区分本地修改、测试通过和提交状态。
- `verification-loop`: 改动完成后运行目标测试、完整离线测试和验收脚本。
- Context7 MCP: 查询 `/websites/pytest_en_stable`，确认 `tmp_path` 适合隔离临时文件、CLI 输出可用 pytest 断言验证。

## 一次性整改实现

- 新增 `src/gis_agent_harness/health_report.py`，提供 72 项本地项目健康检查，覆盖 CLI、测试、打包、文档、配置、安全、运维、架构和功能能力。
- 新增 `python3 -m gis_agent_harness.cli health-report`，支持 JSON/Markdown 输出、类别过滤、`--output-file` 写入。
- 新增 `tests/test_health_report.py`，覆盖检查数量、类别过滤、Markdown 渲染、CLI 写文件、CLI Markdown 输出、重型 GIS 依赖懒加载。
- 将 `health-report` 加入 `scripts/verify_acceptance.py` 的交付物、验收项和 evidence。
- 更新 `README.md`，加入 `health-report` 命令示例和功能说明。
- 更新 `.env.example`，显式加入 `GIS_AGENT_HARNESS_QGIS_REQUIRE_CONFIRM=true`。

## 至少 50 项整改/改进/功能增加清单

1. 增加 AGENTS 安装命令检查，确保 `requirements.txt` 安装路径可审计。
2. 增加 AGENTS fixture 生成命令检查，避免缺 fixture 时无明确恢复路径。
3. 增加 AGENTS 隔离 fixture 根检查，减少 ad hoc 运行污染共享 fixture。
4. 增加 AGENTS 全量 `pytest -q` 检查，确保离线测试入口可追踪。
5. 增加 AGENTS TUI smoke 命令检查，保留 headless TUI 显式验证。
6. 增加 AGENTS 模板 CLI 路径检查，确保 `templates list`、`goal run`、`config doctor` 被记录。
7. 增加 AGENTS TUI local-only 约束检查，防止 TUI 被扩展成外部服务入口。
8. 增加 AGENTS smoke demo 命令检查，保留 demo_task、demo_recovery、demo_readme_workflow 证据。
9. 增加 AGENTS 验收脚本检查，确保最终交付前有 JSON 审计入口。
10. 增加 AGENTS failure demo 检查，确保 guardrail-blocked 和 timeout 路径可验。
11. 增加 AGENTS 清理命令检查，支持创建 fresh checkpoint 前清理本地状态。
12. 增加 fixture mutation guard 检查，约束测试和 demo 不改共享 `tests/fixtures/`。
13. 增加 CLI help fast import guard 检查，守住 CLI 模块级不导入 GeoPandas/Fiona/Rasterio。
14. 增加 MVP external service guard 检查，防止引入外部服务、数据库或 web server。
15. 增加 append-only state logging 检查，保护 `AGENT_STATE.md` 和 `.runs/state.jsonl` 追加式日志。
16. 增加 README local-files scope 检查，确认用户文档仍限定 local files。
17. 增加 README no web service 检查，避免文档遗漏 MVP 边界。
18. 增加 README no database 检查，避免引入数据库假设。
19. 增加 README mock routing default 检查，确认 mock-first 默认行为。
20. 增加 README Python baseline 检查，确认 Python 3.11 与 package metadata 一致。
21. 增加 README install section 检查，确保安装命令可复制。
22. 增加 README sample data commands 检查，确保 fixture 生成命令同步。
23. 增加 README goal template commands 检查，确保模板路径文档同步。
24. 增加 README command catalog 检查，确保 core CLI 命令被列出。
25. 增加 README qgis_process approval guard 检查，确认 live QGIS 执行仍需确认。
26. 增加 README MCP progressive manifest 检查，确认 MCP progressive-disclosure 文档存在。
27. 增加 README visual review features 检查，确认 capture/judge 命令说明存在。
28. 增加 README advanced dry-run manifests 检查，确认 STAC/FaaS/QGIS plugin/COG viewer 命令同步。
29. 增加 README failure compaction 检查，确认 repeated failure replanning 文档存在。
30. 增加 README acceptance command 检查，确保验收脚本在 README 测试流程中。
31. 增加 README health report command 检查，记录新增健康报告命令。
32. 增加 pyproject Python bounds 检查，确认 `>=3.11,<3.13`。
33. 增加 Click dependency bound 检查，确认 CLI 依赖上界。
34. 增加 Textual dependency bound 检查，确认 TUI 依赖上界。
35. 增加 GeoPandas dependency bound 检查，确认核心 GIS 依赖边界。
36. 增加 Rasterio dependency bound 检查，确认 raster 依赖边界。
37. 增加 pytest dev dependency 检查，确认测试依赖可安装。
38. 增加 console script entry point 检查，确认 installed CLI 入口存在。
39. 增加 pytest testpaths 检查，确认 pytest discovery 限定到 tests。
40. 增加 requirements editable dev 检查，确认 `-e .[dev]` 简化本地安装。
41. 增加 CI offline pytest 检查，确认 CI 运行完整离线 suite。
42. 增加 CI TUI smoke 检查，确认 CI 单独验证 TUI。
43. 增加 CI demo scripts 检查，确认 smoke demo 在 CI 中执行。
44. 增加 CI acceptance audit 检查，确认 CI 执行 `verify_acceptance.py`。
45. 增加 CI package build 检查，确认 sdist/wheel 构建仍在 CI。
46. 增加 Docker local CLI entrypoint 检查，确认容器入口仍是本地 CLI。
47. 增加 Docker workspace runtime 检查，确认容器运行目录是 `/workspace`。
48. 增加 env mock default 检查，确认 `.env.example` 默认 mock/offline。
49. 增加 env state paths 检查，确认 `.runs` 和 `AGENT_STATE.md` 可配置。
50. 增加 env local telemetry 检查，确认 telemetry local-only 默认。
51. 增加 env qgis confirmation 检查，并补齐 `GIS_AGENT_HARNESS_QGIS_REQUIRE_CONFIRM=true`。
52. 增加 config mock provider default 检查，确认 runtime 默认 provider/use_mock。
53. 增加 config timeout/retry budget 检查，确认本地执行有边界。
54. 增加 config qgis guard 检查，确认 QGIS 执行保护默认开启。
55. 增加 CLI lazy spatial imports 检查，确认 spatial tools 仍在命令内导入。
56. 增加 CLI output-file helper 检查，确认 JSON/Markdown 输出复用写文件逻辑。
57. 增加 CLI config doctor 检查，确认 provider readiness 可离线检查。
58. 新增 CLI health-report 命令检查，确认本次健康报告功能可从 CLI 访问。
59. 增加 state markdown header 检查，确认状态日志保持人类可读头。
60. 增加 state JSONL write 检查，确认结构化状态写入使用 append。
61. 增加 telemetry secret redaction 检查，确认 secret-like key 会脱敏。
62. 增加 telemetry summary 检查，确认事件聚合仍可用。
63. 增加 MCP progressive registry 检查，确认 MCP manifest 保持 progressive disclosure。
64. 增加 MCP runtime dispatch 检查，确认本地 MCP tool 可执行且支持短横线规范化。
65. 增加 qgis dry-run default 检查，确认 QGIS 请求 preview-first。
66. 增加 sandbox timeout enforcement 检查，确认生成代码执行有 timeout。
67. 增加 AST guardrail scan 检查，确认 Python 脚本执行前有 AST 安全扫描。
68. 增加 built-in goal templates 检查，确认三个内置模板在文档/仓库中可见。
69. 增加 execution plan markdown support 检查，确认 YAML/Markdown frontmatter 计划路径存在。
70. 增加 CLI heavy import test 检查，确认懒加载 regression test 存在。
71. 新增 health report tests 检查，确认本次新功能有测试覆盖。
72. 增加 acceptance script smoke test 检查，确认验收脚本自身被 pytest 覆盖。

## 当前验证证据

- `pytest -q tests/test_health_report.py`: 通过。
- `pytest -q tests/test_health_report.py tests/test_cli.py tests/test_config.py`: 通过，59 个测试通过。
- `python3 -m gis_agent_harness.cli health-report --root .`: 72 项检查，72 项通过。
- `python3 scripts/verify_acceptance.py --skip-pytest`: 通过，新增 `health_report` acceptance 为 true。
- `pytest -q`: 通过。
- `python3 scripts/verify_acceptance.py`: 通过，`stop_conditions` 全部为 true。
- `git diff --check`: 通过。
- `python3 -m gis_agent_harness.cli --help`: 通过，命令列表包含 `health-report`。
