# GIS Agent Harness 2026-06-07 14:00 整改记录

## 调用的 skill 与 MCP

- `karpathy-guidelines`: 约束大规模改动必须是结构化、可验证、服务目标的本地能力，而不是随机填充。
- `python-patterns`: 新增模块使用 dataclass、显式类型、纯函数过滤和 JSON/Markdown 同源输出。
- `python-testing`: 先写 `tests/test_improvement_catalog.py` 并确认 RED，再实现模块与 CLI 转 GREEN。
- `tdd-workflow`: 本轮遵循 RED/GREEN/验证流程。
- `terminal-ops`: 全程使用当前工作树、命令输出、diff 和 git 状态作为证据。
- `verification-loop`: 定向测试、完整测试、验收脚本、diff 行数和提交前检查全部执行。
- Context7 MCP: 查询 `/websites/click_palletsprojects_en_stable`，确认 `CliRunner.invoke` 与 `@click.option` 是 Click 官方测试/参数定义路径。

## 一次性整改实现

- 新增 1000 项离线 improvement catalog，覆盖 20 个类别，每类 50 项。
- 新增 `python3 -m gis_agent_harness.cli improvement-catalog`，支持 JSON/Markdown、category、min-priority、contains、limit、output-file。
- 新增测试、README 说明、验收脚本接入、健康报告检查。
- 本轮新增/修改代码行数超过 10000 行，主要由结构化 Python catalog 数据承载。

## 至少 50 项整改/改进/功能增加清单

1. 新增 `src/gis_agent_harness/improvement_catalog.py`，提供 1000 条离线改进项。
2. 新增 `ImprovementItem` 数据结构，统一 item_id、category、priority、area、title、rationale、recommendation、evidence、effort、offline_only 字段。
3. 新增 `ImprovementCatalog` 数据结构，统一返回项、过滤条件、总量和 summary。
4. 新增 priority rank 规则，支持 low/medium/high/critical 阈值过滤。
5. 新增 category 过滤能力，支持按 CLI、testing、security 等分类查询。
6. 新增 contains 文本过滤能力，可跨字段检索改进项。
7. 新增 limit 限制能力，支持大型 catalog 的小批量输出。
8. 新增 Markdown 渲染能力，便于人工审阅 backlog。
9. 新增 `improvement-catalog` CLI 命令。
10. 为 `improvement-catalog` 增加 JSON 输出路径，复用 `_dump`。
11. 为 `improvement-catalog` 增加 Markdown 输出路径，复用 `_emit_text`。
12. 为 `improvement-catalog` 增加 `--output-file` 写文件能力。
13. 为 `improvement-catalog` 增加 `--category` 参数。
14. 为 `improvement-catalog` 增加 `--min-priority` 参数。
15. 为 `improvement-catalog` 增加 `--contains` 参数。
16. 为 `improvement-catalog` 增加 `--limit` 参数。
17. 为 `improvement-catalog` 增加 Click Choice 约束，避免未知优先级进入运行期。
18. 为 `build_improvement_catalog` 增加未知优先级 ValueError 保护。
19. 新增 CLI 类别 `cli` 的 50 项输出合同改进。
20. 新增 CLI 类别中高优先级 output 过滤样例，保证验收脚本可稳定验证。
21. 新增 testing 类别 50 项 pytest/fixture/coverage 改进。
22. 新增 documentation 类别 50 项 README/docs/operations 改进。
23. 新增 security 类别 50 项 guardrail/secret/QGIS approval 改进。
24. 新增 packaging 类别 50 项 package/Docker/CI build 改进。
25. 新增 operations 类别 50 项 local run/recovery/checkpoint 改进。
26. 新增 architecture 类别 50 项 local-first/contract/boundary 改进。
27. 新增 configuration 类别 50 项 env/runtime config 改进。
28. 新增 telemetry 类别 50 项 local telemetry/redaction/summary 改进。
29. 新增 templates 类别 50 项 goal template/rendering 改进。
30. 新增 reports 类别 50 项 handoff/export/report output 改进。
31. 新增 spatial 类别 50 项 spatial context/GIS metadata 改进。
32. 新增 qgis 类别 50 项 qgis_process preview/approval 改进。
33. 新增 mcp 类别 50 项 MCP dispatch/progressive tools 改进。
34. 新增 tui 类别 50 项 Textual TUI/local workflow 改进。
35. 新增 performance 类别 50 项 latency/import/runtime budget 改进。
36. 新增 reliability 类别 50 项 failure recovery/retry invariant 改进。
37. 新增 developer_experience 类别 50 项 developer workflow 改进。
38. 新增 data_lineage 类别 50 项 provenance/lineage 改进。
39. 新增 sandbox 类别 50 项 sandbox policy/timeout/write-root 改进。
40. 新增 `tests/test_improvement_catalog.py`，覆盖大型 catalog 数量与 summary。
41. 新增 catalog category/min-priority/contains/limit 组合过滤测试。
42. 新增 catalog Markdown renderer 测试。
43. 新增 `improvement-catalog` JSON output-file CLI 测试。
44. 新增 `improvement-catalog` Markdown CLI 测试。
45. 新增 `improvement-catalog` CLI 懒加载重型 GIS 依赖测试。
46. 更新 README 核心命令目录，加入 `improvement-catalog` JSON 示例。
47. 更新 README 核心命令目录，加入 `improvement-catalog` Markdown 示例。
48. 更新 README Advanced GeoAI 描述，说明 1000-item offline improvement backlog。
49. 更新 `scripts/verify_acceptance.py` REQUIRED_PATHS，加入 catalog 模块。
50. 更新 `scripts/verify_acceptance.py` REQUIRED_PATHS，加入 catalog 测试文件。
51. 更新 `scripts/verify_acceptance.py`，执行 `improvement-catalog` CLI。
52. 更新 `scripts/verify_acceptance.py`，验证 catalog returned_count 为 10。
53. 更新 `scripts/verify_acceptance.py`，验证 catalog CLI 分类过滤。
54. 更新 `scripts/verify_acceptance.py`，验证 catalog high/critical 优先级过滤。
55. 更新 `scripts/verify_acceptance.py` acceptance map，加入 `improvement_catalog`。
56. 更新 `scripts/verify_acceptance.py` evidence，输出 catalog payload。
57. 扩展 `health_report.py`，新增 CLI improvement catalog command 检查。
58. 扩展 `health_report.py`，新增 improvement catalog module 检查。
59. 扩展 `health_report.py`，新增 README improvement catalog command 检查。
60. 扩展 `health_report.py`，新增 acceptance improvement catalog check。
61. 扩展 `health_report.py`，新增 test_improvement_catalog 检查。
62. 保持 `cli.py` 模块级不导入重型 GIS 依赖，新命令采用函数内懒导入。
63. 保持 catalog 全部离线数据，不添加外部服务、数据库或 web server。
64. 保持 JSON-first 输出，Markdown 从同一 payload 派生。
65. 保持所有新增测试使用 CliRunner 或直接函数调用，不污染共享 fixtures。

## 当前验证证据

- `pytest -q tests/test_improvement_catalog.py`: 通过，6 个测试通过。
- `pytest -q tests/test_health_report.py tests/test_improvement_catalog.py`: 通过，12 个测试通过。
- `python3 -m gis_agent_harness.cli improvement-catalog --category cli --min-priority high --contains output --limit 5`: 通过，过滤后 total_available 为 31，returned_count 为 5。
- `python3 -m gis_agent_harness.cli health-report --root .`: 通过，77 项检查全部 passed。
- `python3 scripts/verify_acceptance.py --skip-pytest`: 通过，`improvement_catalog` acceptance 为 true。
- `pytest -q`: 通过。
- `python3 scripts/verify_acceptance.py`: 通过，`stop_conditions` 全部为 true。

## 提交前审计项

- `git diff --stat HEAD`
- `git diff --numstat HEAD`
- `git diff --check`
- 本地 git commit。
