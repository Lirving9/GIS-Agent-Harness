# Architecture

## Control Surfaces

- `cli.py`: Click entrypoints for inspection, `run-task`, recovery, report export, templates, goal runs, config doctor, and TUI launch
- `tui/app.py`: Textual application shell and worker-driven run orchestration
- `tui/screens.py`: Home, goal entry, run monitor, recovery, and config screens
- `tui/widgets.py`: JSON, log, and risk-preview panels used by the TUI
- `Dockerfile`: local container entrypoint for CLI and smoke-friendly packaging
- `.github/workflows/ci.yml`: offline CI matrix plus smoke and package jobs

## Core Runtime

- `agent_loop.py`: minimal ReAct loop with repeated-error detection
- `execution_plan.py`: declarative YAML/Markdown plan loader for template defaults and action constraints
- `task_templates.py`: YAML template loader and `AgentTask` renderer
- `goal_runner.py`: `GoalSpec -> AgentTask -> AgentLoop` execution bridge
- `llm_router.py`: retry and fallback bookkeeping for repair planning
- `review.py`: reviewer gate that scores and approves/rejects repair plans before sandbox execution
- `llm_adapters.py`: mock, LiteLLM, OpenAI-compatible, and Anthropic-facing completion adapters
- `auth_config.py`: provider profile loading, env/YAML merge helpers, and `config doctor`
- `config.py`: environment-backed runtime settings, sandbox, and telemetry defaults

## Safety And State

- `spatial_tools.py`: vector and raster inspection helpers
- `spatial_context.py`: compressed spatial repo map generator for vector/raster metadata
- `mcp_registry.py`: progressive-disclosure MCP-style GIS tool manifest
- `parameter_alignment.py`: last-attempt CRS, bbox, and numeric argument normalization
- `qgis_process.py`: JSON-first wrapper for previewing or running `qgis_process` algorithms
- `qgis_process.py`: JSON-first wrapper for previewing or running `qgis_process` algorithms with a local approval gate for live execution
- `guardrails.py`: CRS checks, invalid-geometry checks, and AST inspection
- `sandbox.py`: subprocess wrapper with timeout, failed-script capture, output-path policy, and risk preview
- `state_store.py`: append-only Markdown and JSONL state snapshots
- `state_hooks.py`: snapshot hook protocol plus callback/in-memory helpers
- `telemetry.py`: local JSONL telemetry with simple secret redaction plus event-journal helpers
- `visual_artifacts.py` / `visual_judge.py`: map artifact hashing, thumbnail capture, and deterministic visual review feedback
- `stac_discovery.py`: dry-run STAC search plans for spatiotemporal asset discovery
- `resource_router.py`: CPU/GPU track selection from static import analysis
- `faas_planner.py`: function-as-a-service manifests without deployment side effects
- `qgis_plugin.py`: QGIS MCP bridge plugin manifest
- `cog_viewer.py`: static browser-side COG review page generator
- `benchmarking.py` / `pipeline_reporting.py`: GeoAgentBench, GeoBenchX, GIS-Bench manifests plus JUnit XML
- `adversarial_review.py`: deterministic methodology review for spatial analysis assumptions
- `geo_exception_parser.py`: GDAL/GEOS/OGR error translation into repair guidance

## Templates

Built-in templates live under `goals/`:

- `align_vector_to_raster.yaml`
- `declare_source_crs.yaml`
- `repair_invalid_geometry.yaml`

Each template renders into the existing `AgentTask` model. The goal layer is intentionally thin; it does not create a second execution object model.

## Flow

1. CLI or TUI resolves runtime config from env and optional profile data.
2. A user either creates an `AgentTask` directly or renders one from a goal template or execution plan.
3. `AgentLoop` inspects current inputs.
4. `guardrails.preflight_dataset_checks()` emits structured observations.
5. `LLMRouter` calls the configured adapter to produce a repair plan and Python script.
6. `review.py` scores the decision against current observations and any plan allowlist, then either approves it, requests replanning, or escalates a failure.
7. `SandboxRunner` validates the script AST, applies the output-path policy, then executes it with timeout.
8. `StateStore` appends each stage into `AGENT_STATE.md` and `.runs/state.jsonl`.
9. Optional hooks mirror snapshots and explicit event types into local telemetry and the TUI.
10. Recovery commands and the TUI replay view use the recorded task and failure artifacts to reconstruct the next run.

## Spatial ACI

- `spatial-map` gives the model an Aider-style map for GIS data: dataset kind, driver, CRS, bounds, geometry type, feature count, schema, and raster dimensions without raw geometry dumps.
- `spatial-map --dataset` is the progressive-disclosure path: fetch full detail for one dataset only after the compressed repo map identifies it as relevant.
- `qgis-run` provides a deterministic QGIS command surface: the agent emits JSON and the harness previews or executes `qgis_process run <algorithm> -` with that payload on stdin.
- `adoption-report` records source hashes, CRS transformations, action lineage, QGIS payloads, and omitted-step reasons so future sessions can recover context without replaying full logs.
- `mcp-tools` exposes only relevant tool domains on demand instead of loading the entire tool registry into context.
- `align-params` normalizes common PEA failure modes such as integer EPSG codes, lowercase CRS strings, comma-separated bboxes, and numeric strings.
- `stac-plan`, `faas-manifest`, `qgis-plugin-manifest`, `cog-viewer`, and `benchmark-manifest` turn cloud/desktop/browser/baseline integrations into local reviewable manifests before any external execution path is considered.
- `capture-artifact`, `judge-map`, `method-review`, and `explain-exception` add the visual, adversarial, and self-correction loops from the architecture blueprint while remaining offline by default.

## Recovery Surface

- `list-runs`: recent run discovery entrypoint for local recovery workflows
- `resume-hint`: compact summary of the latest failed run
- `show-failure-files`: failed log/script locator for local debugging
- `show-replay`: suggested rerun command built from stored task context
- `adoption-report`: structured per-run audit and context handoff report
- `show-telemetry`: event-journal summary or raw event stream for one run
- `show-report`: local report-bundle reader for exported recovery snapshots
- `replay-last`: execute a new run from the latest failed task context with optional overrides

## Default Guarantees

- local files only
- append-only state history
- mock-first, offline-by-default tests
- cross-platform CI stays centered on offline commands and local fixtures
- no web service and no database
- no GeoPandas, Fiona, or Rasterio imports at `cli.py` module scope
