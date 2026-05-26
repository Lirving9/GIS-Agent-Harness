# Architecture

## Core Modules

- `cli.py`: Click entrypoints and JSON output
- `config.py`: environment-backed runtime settings
- `llm_router.py`: mock-first routing with retry and fallback bookkeeping
- `spatial_tools.py`: vector and raster inspection helpers
- `guardrails.py`: CRS checks, invalid-geometry checks, and AST inspection
- `sandbox.py`: subprocess wrapper with timeout and failed-script capture
- `agent_loop.py`: minimal ReAct loop with repeated-error detection
- `state_store.py`: append-only Markdown and JSONL state snapshots
- `list-runs`: recent run discovery entrypoint for local recovery workflows
- `list-runs` filters: status, stage, and substring filtering for local run discovery
- `resume-hint`: compact summary of the latest failed run for local recovery
- `show-failure-files`: latest failed-run log/script locator for local debugging
- `show-replay`: suggested rerun command built from the latest failed run context
- `show-report`: local report-bundle reader for exported recovery snapshots
- `replay-last`: execute a new run from the latest failed task context with optional overrides
- `run_id` filters on replay/summary commands let local recovery target any recorded run, not just the latest failure
- `replay-last --dry-run`: inspect the reconstructed replay task before executing it
- `replay-last --confirm`: explicit execution gate for real local replays

## Flow

1. CLI or demo script builds an `AgentTask`.
2. `AgentLoop` inspects the current inputs.
3. `guardrails.preflight_dataset_checks()` emits structured observations.
4. `LLMRouter` produces a repair plan and Python script.
5. `SandboxRunner` validates the script AST, then executes it with timeout.
6. `StateStore` appends each stage into `AGENT_STATE.md` and `.runs/state.jsonl`.
7. The loop repeats until inputs are safe or the retry budget is exhausted.

## Data Strategy

- Sample fixtures are generated locally with `scripts/generate_sample_data.py`.
- Raster inspection reads metadata only and never calls `read()` for full-array inspection.
- Vector inspection returns `driver`, `crs`, `bounds`, `schema`, feature count, and sample properties.

## Guardrail Semantics

- `set_crs(...)` is only suggested when CRS metadata is missing.
- `to_crs(...)` is only suggested when CRS values differ.
- `make_valid()` is preferred for invalid geometry.
- Unsafe imports and shell-oriented calls are blocked before sandbox execution.
