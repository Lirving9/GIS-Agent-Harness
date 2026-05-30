# GIS Agent Harness

GIS Agent Harness is a local-first Python MVP for guarded GIS task execution. It now provides:

- Click CLI commands for vector and raster inspection
- goal templates that compile into the existing `AgentTask` loop
- a Textual TUI for template-driven runs, monitoring, and recovery
- a mock-first LiteLLM routing layer with profile-based provider config
- CRS, geometry, and AST guardrails before execution
- compressed spatial repo maps for vector/raster metadata without dumping full geometries
- JSON-first `qgis_process` request previews for deterministic QGIS CLI execution
- explicit local approval checkpoints before live `qgis_process` execution
- sandboxed Python execution with timeout, stdout, stderr, failed-script capture, and output-path policy
- append-only state snapshots plus local telemetry, lineage-rich adoption reports, and recovery audit bundles

## Scope

This MVP is intentionally narrow:

- local files only
- local CLI and TUI only
- no web service
- no database
- mock routing by default, live provider profiles optional

## Python Version

The target baseline is Python 3.11. The package metadata allows `>=3.11,<3.13`, and the current repository is validated on Python 3.12 in this environment.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

## Generate Sample Data

```bash
python3 scripts/generate_sample_data.py
python3 scripts/generate_sample_data.py --output-dir .local-fixtures
```

This creates local vector and raster fixtures, including:

- `sample.gpkg`
- `sample_3857.gpkg`
- `invalid_geometry.gpkg`
- `missing_crs.shp`
- `sample.tif`

## TUI And Goal Templates

```bash
python3 -m gis_agent_harness.cli templates list
python3 -m gis_agent_harness.cli goal run \
  --template align_vector_to_raster \
  --vector tests/fixtures/vector/sample_3857.gpkg \
  --raster tests/fixtures/raster/sample.tif \
  --mock
python3 -m gis_agent_harness.cli goal run \
  --template declare_source_crs \
  --vector tests/fixtures/vector/missing_crs.shp \
  --source-crs EPSG:4326 \
  --dry-run
python3 -m gis_agent_harness.cli config doctor
python3 -m gis_agent_harness.cli tui
```

Built-in templates:

- `align_vector_to_raster`
- `declare_source_crs`
- `repair_invalid_geometry`

`goal run` renders a template into the existing `AgentTask` model, then executes the existing `AgentLoop`. `--dry-run` prints the rendered task and template metadata without executing anything.

## Core CLI

```bash
python3 -m gis_agent_harness.cli --help
python3 -m gis_agent_harness.cli inspect-vector tests/fixtures/vector/sample.gpkg
python3 -m gis_agent_harness.cli inspect-raster tests/fixtures/raster/sample.tif
python3 -m gis_agent_harness.cli spatial-map tests/fixtures
python3 -m gis_agent_harness.cli qgis-run native:buffer \
  --payload-json '{"inputs":{"INPUT":"data/urban_roads.shp","DISTANCE":500}}' \
  --dry-run
python3 -m gis_agent_harness.cli qgis-run native:buffer \
  --payload-json '{"inputs":{"INPUT":"data/urban_roads.shp","DISTANCE":500}}' \
  --execute \
  --confirm
python3 -m gis_agent_harness.cli run-task \
  --task-summary "Align vector CRS to raster CRS" \
  --vector tests/fixtures/vector/sample_3857.gpkg \
  --raster tests/fixtures/raster/sample.tif
python3 -m gis_agent_harness.cli show-state
python3 -m gis_agent_harness.cli show-state --format table
python3 -m gis_agent_harness.cli list-runs --failed-only
python3 -m gis_agent_harness.cli list-runs --status failed --stage stop --contains geometry
python3 -m gis_agent_harness.cli resume-hint
python3 -m gis_agent_harness.cli show-failure-files
python3 -m gis_agent_harness.cli show-replay
python3 -m gis_agent_harness.cli adoption-report RUN_ID --format text
python3 -m gis_agent_harness.cli export-report --latest-failed --print-index
python3 -m gis_agent_harness.cli show-report --latest
python3 -m gis_agent_harness.cli replay-last --run-id RUN_ID --source-crs EPSG:4326 --dry-run
python3 -m gis_agent_harness.cli replay-last --run-id RUN_ID --source-crs EPSG:4326 --confirm
```

## Provider Profiles

The default path is still offline mock mode. For live routing, use `.env.example`, `litellm-config.yaml`, or explicit environment variables.

```bash
GIS_AGENT_HARNESS_USE_MOCK=false
GIS_AGENT_HARNESS_PROVIDER=litellm
GIS_AGENT_HARNESS_PRIMARY_MODEL=gis-openai
GIS_AGENT_HARNESS_FALLBACK_MODEL=gis-claude
LITELLM_CONFIG_PATH=litellm-config.yaml
```

For a third-party OpenAI-compatible endpoint:

```bash
GIS_AGENT_HARNESS_USE_MOCK=false
GIS_AGENT_HARNESS_PROVIDER=openai_compatible
GIS_AGENT_HARNESS_PRIMARY_MODEL=gis-thirdparty
GIS_AGENT_HARNESS_API_BASE=https://your-provider.example/v1
GIS_AGENT_HARNESS_API_KEY=your-key
```

`config doctor` validates the merged runtime config and reports missing provider/profile inputs without making a live network request.

`litellm-config.yaml` accepts both `${ENV_VAR}` and `os.environ/ENV_VAR` references so the local examples stay compatible with common LiteLLM YAML styles.

## Spatial Context And QGIS CLI

`spatial-map` builds a compact metadata map for local spatial datasets. It records format, CRS, bounds, geometry type, feature counts, attribute schema, and raster shape without loading full coordinate arrays into model context.

`qgis-run` accepts a QGIS algorithm id plus a JSON object and defaults to `--dry-run`, returning the `qgis_process run <algorithm> -` request and stdin payload that would be made. Use `--execute` only when QGIS is installed locally and you want the harness to call `qgis_process`.

Live `qgis_process` execution is gated by an explicit local approval checkpoint. The command returns a risk summary with payload size, parameter count, and detected input paths; add `--confirm` after review to allow execution. Set `GIS_AGENT_HARNESS_QGIS_REQUIRE_CONFIRM=false` only if you intentionally want to disable this local guardrail.

## Tests

```bash
pytest -q
pytest -q tests/test_tui_smoke.py
python3 scripts/demo_task.py
python3 scripts/demo_recovery.py
python3 scripts/demo_readme_workflow.py
python3 scripts/verify_acceptance.py
python3 scripts/demo_failures.py
python3 scripts/clean_local_state.py
```

`demo_task.py` writes its own runtime fixtures under `.demo-runs/fixtures` by default, so it does not mutate `tests/fixtures/`.

`demo_recovery.py` exercises the local recovery workflow end to end: fail a run, inspect it, export a bundle, preview replay, and then recover it with an explicit override.

`demo_readme_workflow.py` replays the documented CLI workflow with real local `run_id` values so the README command path stays copyable.

`verify_acceptance.py` runs a local acceptance audit against the current deliverables, including templates, config doctor, recovery commands, and the headless TUI test file.

## Container And CI

```bash
docker build -t gis-agent-harness .
docker run --rm -it -v "$PWD":/workspace gis-agent-harness --help
docker run --rm -it -v "$PWD":/workspace gis-agent-harness templates list
docker run --rm -it -v "$PWD":/workspace gis-agent-harness config doctor
```

The repository also includes [`.github/workflows/ci.yml`](/home/spiderli/GIS-Agent-Harness/.github/workflows/ci.yml) for cross-platform offline pytest, explicit TUI smoke, demo scripts, package build, and the local acceptance audit.

## What `run-task` Does

`run-task` executes a minimal ReAct loop:

1. Inspect input datasets.
2. Block on missing CRS, CRS mismatch, invalid geometry, or unsafe Python.
3. Ask the router for a repair action.
4. Execute the generated repair script inside a subprocess sandbox.
5. Re-inspect and stop on success, repeated failures, or max iterations.

The default mock router can repair:

- missing CRS via `set_crs(...)`
- CRS mismatch via `to_crs(...)`
- invalid geometry via `make_valid()`

## Local Hygiene

```bash
python3 scripts/clean_local_state.py
python3 scripts/clean_local_state.py --include-fixtures
```

This removes local runtime directories such as `.demo-runs/`, `.pytest-smoke/`, and stale `.runs/` artifacts. Use `--include-fixtures` if you also want to remove generated `tests/fixtures/`.

## Local Reports

State and recovery inspection commands support `--output-file` so the same local diagnostics can be written to review files before you create a Git checkpoint.

Use `adoption-report` for a structured handoff with source hashes, CRS transformations, action history, derived-data lineage, qgis_process payloads, and omitted-step reasons.

For a bundled snapshot, use `export-report` to write state, summary, failure, replay, adoption, and index files in one step. If `--output-dir` is omitted, the bundle is written under `reports/<run_id>-<timestamp>/`. Use `--profile quick|full|debug` for presets or `--only` for a custom subset. Add `--print-index` if you want the generated index echoed directly in the terminal after export.

## Stop Conditions

The repository is considered complete when:

- CLI help works for the top-level and required subcommands
- `pytest -q` passes offline
- `python3 scripts/demo_task.py` completes a failure -> repair -> success loop
- `python3 scripts/demo_recovery.py` completes a failed-run discovery -> export -> replay recovery loop
- `python3 scripts/demo_readme_workflow.py` proves the documented local CLI and goal workflow is copyable
- `python3 scripts/verify_acceptance.py` reports all acceptance items and stop conditions as satisfied
- `Dockerfile` builds a local CLI image without adding any external service dependency
- `.github/workflows/ci.yml` keeps the offline suite, smoke scripts, and package build wired into CI
- `README.md`, `docs/architecture.md`, `docs/operations.md`, `AGENTS.md`, and `.codex/config.toml` stay in sync with the current commands and constraints
