# GIS Agent Harness

GIS Agent Harness is a local-first Python MVP for guarded GIS task execution. It provides:

- Click CLI commands for vector and raster inspection
- a mock-first LiteLLM routing layer with fallback support
- CRS, geometry, and AST guardrails before execution
- sandboxed Python execution with timeout, stdout, stderr, and failed-script capture
- append-only state snapshots for recovery and audit

The project follows the requirements in [GIS-harness.md](GIS-harness.md) and keeps all tests offline by default.

## Scope

This MVP is intentionally narrow:

- local files only
- CLI only
- no web service
- no database
- mock routing by default, live LiteLLM optional

## Python Version

The target baseline is Python 3.11. The package metadata allows `>=3.11,<3.13`, and the current repository was validated on Python 3.12 because that is the available interpreter in this environment.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Generate Sample Data

```bash
python3 scripts/generate_sample_data.py
python3 scripts/generate_sample_data.py --output-dir .local-fixtures
```

This creates:

- `tests/fixtures/vector/sample.gpkg`
- `tests/fixtures/vector/sample.shp`
- `tests/fixtures/vector/sample_3857.gpkg`
- `tests/fixtures/vector/invalid_geometry.gpkg`
- `tests/fixtures/vector/missing_crs.shp`
- `tests/fixtures/raster/sample.tif`

## CLI

```bash
python3 -m gis_agent_harness.cli --help
python3 -m gis_agent_harness.cli inspect-vector tests/fixtures/vector/sample.gpkg
python3 -m gis_agent_harness.cli inspect-raster tests/fixtures/raster/sample.tif
python3 -m gis_agent_harness.cli run-task \
  --task-summary "Align vector CRS to raster CRS" \
  --vector tests/fixtures/vector/sample_3857.gpkg \
  --raster tests/fixtures/raster/sample.tif
python3 -m gis_agent_harness.cli show-state
python3 -m gis_agent_harness.cli show-state --format table
python3 -m gis_agent_harness.cli show-state --format table --output-file reports/state.txt
python3 -m gis_agent_harness.cli list-runs --failed-only
python3 -m gis_agent_harness.cli list-runs --format table
python3 -m gis_agent_harness.cli list-runs --format table --output-file reports/runs.txt
python3 -m gis_agent_harness.cli list-runs --status failed --stage stop --contains geometry
python3 -m gis_agent_harness.cli resume-hint
python3 -m gis_agent_harness.cli show-failure-files
python3 -m gis_agent_harness.cli show-failure-files --format table
python3 -m gis_agent_harness.cli show-failure-files --format table --output-file reports/failure-files.txt
python3 -m gis_agent_harness.cli show-replay
python3 -m gis_agent_harness.cli show-replay --format table
python3 -m gis_agent_harness.cli show-replay --format table --output-file reports/replay.txt
python3 -m gis_agent_harness.cli export-report --latest-failed
python3 -m gis_agent_harness.cli export-report --run-id RUN_ID
python3 -m gis_agent_harness.cli export-report --run-id RUN_ID --output-dir reports/run-report
python3 -m gis_agent_harness.cli replay-last --source-crs EPSG:4326 --confirm
python3 -m gis_agent_harness.cli replay-last --run-id RUN_ID --source-crs EPSG:4326 --confirm
python3 -m gis_agent_harness.cli replay-last --run-id RUN_ID --source-crs EPSG:4326 --dry-run
```

## Tests

```bash
pytest -q
python3 scripts/demo_task.py
python3 scripts/demo_failures.py
python3 scripts/clean_local_state.py
```

`demo_task.py` writes its own runtime fixtures under `.demo-runs/fixtures` by default, so it does not need to mutate `tests/fixtures/`.

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
For a bundled snapshot, use `export-report` to write state, summary, failure, replay, and index files in one step. If `--output-dir` is omitted, the bundle is written under `reports/<run_id>-<timestamp>/`.

## Rollback Strategy

- Use one Git commit per major stage.
- If a stage fails validation, revert only that stage and keep previously passing modules intact.
- If live LiteLLM integration fails, keep mock routing as the required MVP path.
- If a feature expands beyond the MVP boundary, downgrade it to documentation instead of blocking the core flow.

## Stop Conditions

The repository is considered complete when:

- CLI help works for the top-level and required subcommands
- `pytest -q` passes offline
- `python3 scripts/demo_task.py` completes a failure -> repair -> success loop
- `README.md`, `docs/architecture.md`, `docs/operations.md`, `AGENTS.md`, and `.codex/config.toml` are present
