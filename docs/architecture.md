# Architecture

## Control Surfaces

- `cli.py`: Click entrypoints for inspection, `run-task`, recovery, report export, templates, goal runs, config doctor, and TUI launch
- `tui/app.py`: Textual application shell and worker-driven run orchestration
- `tui/screens.py`: Home, goal entry, run monitor, recovery, and config screens
- `tui/widgets.py`: JSON, log, and risk-preview panels used by the TUI

## Core Runtime

- `agent_loop.py`: minimal ReAct loop with repeated-error detection
- `task_templates.py`: YAML template loader and `AgentTask` renderer
- `goal_runner.py`: `GoalSpec -> AgentTask -> AgentLoop` execution bridge
- `llm_router.py`: retry and fallback bookkeeping for repair planning
- `llm_adapters.py`: mock, LiteLLM, OpenAI-compatible, and Anthropic-facing completion adapters
- `auth_config.py`: provider profile loading, env/YAML merge helpers, and `config doctor`
- `config.py`: environment-backed runtime settings, sandbox, and telemetry defaults

## Safety And State

- `spatial_tools.py`: vector and raster inspection helpers
- `guardrails.py`: CRS checks, invalid-geometry checks, and AST inspection
- `sandbox.py`: subprocess wrapper with timeout, failed-script capture, output-path policy, and risk preview
- `state_store.py`: append-only Markdown and JSONL state snapshots
- `state_hooks.py`: snapshot hook protocol plus callback/in-memory helpers
- `telemetry.py`: local JSONL telemetry with simple secret redaction

## Templates

Built-in templates live under `goals/`:

- `align_vector_to_raster.yaml`
- `declare_source_crs.yaml`
- `repair_invalid_geometry.yaml`

Each template renders into the existing `AgentTask` model. The goal layer is intentionally thin; it does not create a second execution object model.

## Flow

1. CLI or TUI resolves runtime config from env and optional profile data.
2. A user either creates an `AgentTask` directly or renders one from a goal template.
3. `AgentLoop` inspects current inputs.
4. `guardrails.preflight_dataset_checks()` emits structured observations.
5. `LLMRouter` calls the configured adapter to produce a repair plan and Python script.
6. `SandboxRunner` validates the script AST, applies the output-path policy, then executes it with timeout.
7. `StateStore` appends each stage into `AGENT_STATE.md` and `.runs/state.jsonl`.
8. Optional hooks mirror snapshots into local telemetry and the TUI.
9. Recovery commands and the TUI replay view use the recorded task and failure artifacts to reconstruct the next run.

## Recovery Surface

- `list-runs`: recent run discovery entrypoint for local recovery workflows
- `resume-hint`: compact summary of the latest failed run
- `show-failure-files`: failed log/script locator for local debugging
- `show-replay`: suggested rerun command built from stored task context
- `show-report`: local report-bundle reader for exported recovery snapshots
- `replay-last`: execute a new run from the latest failed task context with optional overrides

## Default Guarantees

- local files only
- append-only state history
- mock-first, offline-by-default tests
- no web service and no database
- no GeoPandas, Fiona, or Rasterio imports at `cli.py` module scope
