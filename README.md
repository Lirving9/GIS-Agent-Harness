# GIS Agent Harness

GIS Agent Harness is a local-first Python MVP for guarded GIS task execution. It now provides:

- Click CLI commands for vector and raster inspection
- goal templates that compile into the existing `AgentTask` loop
- declarative YAML/Markdown execution plans that can supply template defaults and action constraints
- a Textual TUI for template-driven runs, monitoring, and recovery
- a mock-first LiteLLM routing layer with profile-based provider config
- CRS, geometry, and AST guardrails before execution
- a reviewer gate that scores proposed repairs before sandbox execution and can force replanning
- compressed spatial repo maps for vector/raster metadata without dumping full geometries
- progressive spatial detail lookup for one dataset plus explicit schema truncation markers
- JSON-first `qgis_process` request previews for deterministic QGIS CLI execution
- explicit local approval checkpoints before live `qgis_process` execution
- MCP-style progressive tool manifests and parameter alignment helpers
- local visual artifact capture plus deterministic map-product review feedback
- dry-run STAC, FaaS, QGIS plugin, benchmark, COG viewer, and resource-routing manifests
- local MCP dispatch, DAG execution helpers, repeated-failure context compaction, requirement matrix, and narrative report generation
- adversarial method review and geospatial exception explanation helpers
- sandboxed Python execution with timeout, stdout, stderr, failed-script capture, and output-path policy
- append-only state snapshots plus local telemetry event journals, lineage-rich adoption reports, and recovery audit bundles

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
python3 -m gis_agent_harness.cli goal run \
  --plan-file plans/declare_source_crs.yaml \
  --mock
python3 -m gis_agent_harness.cli config doctor
python3 -m gis_agent_harness.cli tui
```

Built-in templates:

- `align_vector_to_raster`
- `declare_source_crs`
- `repair_invalid_geometry`

`goal run` renders a template into the existing `AgentTask` model, then executes the existing `AgentLoop`. `--dry-run` prints the rendered task and template metadata without executing anything.

If you need stronger task alignment, pass `--plan-file` with a YAML file or a Markdown file that starts with YAML frontmatter. The execution plan can provide the template id, default inputs, retry budget, and an allowlist of repair actions.

## Core CLI

```bash
python3 -m gis_agent_harness.cli --help
python3 -m gis_agent_harness.cli inspect-vector tests/fixtures/vector/sample.gpkg
python3 -m gis_agent_harness.cli inspect-raster tests/fixtures/raster/sample.tif
python3 -m gis_agent_harness.cli spatial-map tests/fixtures
python3 -m gis_agent_harness.cli spatial-map tests/fixtures --dataset vector/sample.gpkg
python3 -m gis_agent_harness.cli qgis-run native:buffer \
  --payload-json '{"inputs":{"INPUT":"data/urban_roads.shp","DISTANCE":500}}' \
  --dry-run
python3 -m gis_agent_harness.cli qgis-run native:buffer \
  --payload-json '{"inputs":{"INPUT":"data/urban_roads.shp","DISTANCE":500}}' \
  --execute \
  --confirm
python3 -m gis_agent_harness.cli mcp-tools --domain raster
python3 -m gis_agent_harness.cli mcp-call inspect-vector \
  --params-json '{"path":"tests/fixtures/vector/sample.gpkg","sample_size":1}'
python3 -m gis_agent_harness.cli align-params \
  --params-json '{"target_crs":4326,"bbox":"-1,-2,3,4","distance":"500"}'
python3 -m gis_agent_harness.cli stac-plan \
  --collection sentinel-2-l2a \
  --bbox -60,-4,-59,-3 \
  --datetime 2023-06-01/2023-08-31 \
  --max-cloud-cover 20
python3 -m gis_agent_harness.cli route-resource --script-text "import torch"
python3 -m gis_agent_harness.cli faas-manifest \
  --function-name segment-cog \
  --image gis-agent-harness:local \
  --handler functions.segment:handler \
  --script-text "import torch"
python3 -m gis_agent_harness.cli qgis-plugin-manifest
python3 -m gis_agent_harness.cli cog-viewer \
  --output-html .runs/cog-viewer.html \
  --cog-url file:///tmp/result.tif
python3 -m gis_agent_harness.cli benchmark-manifest --junit-file .runs/geoai-benchmarks.xml
python3 -m gis_agent_harness.cli benchmark-run
python3 -m gis_agent_harness.cli method-review \
  --analysis-json '{"method":"ordinary least squares on polygons","crs":"EPSG:4326"}'
python3 -m gis_agent_harness.cli explain-exception "GEOSException: TopologyException: Self-intersection"
python3 -m gis_agent_harness.cli compact-failures \
  --history-json '[{"action":"gdalwarp","parameters":{"s_srs":"bad"},"status":"failed"},{"action":"gdalwarp","parameters":{"s_srs":"bad"},"status":"failed"},{"action":"gdalwarp","parameters":{"s_srs":"bad"},"status":"failed"}]'
python3 -m gis_agent_harness.cli requirement-matrix
python3 -m gis_agent_harness.cli narrative-report \
  --adoption-json-file .runs/adoption.json \
  --output-file .runs/NARRATIVE_REPORT.md
python3 -m gis_agent_harness.cli run-task \
  --task-summary "Align vector CRS to raster CRS" \
  --vector tests/fixtures/vector/sample_3857.gpkg \
  --raster tests/fixtures/raster/sample.tif
python3 -m gis_agent_harness.cli show-state
python3 -m gis_agent_harness.cli show-state --format table
python3 -m gis_agent_harness.cli show-telemetry --summary
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

By default, large vector schemas are truncated to keep the context packet small; the payload records `schema_field_count` plus `schema_truncated` so the model knows more detail exists. Use `spatial-map ROOT --dataset relative/path.gpkg` to fetch the full detail for one dataset on demand.

`qgis-run` accepts a QGIS algorithm id plus a JSON object and defaults to `--dry-run`, returning the `qgis_process run <algorithm> -` request and stdin payload that would be made. Use `--execute` only when QGIS is installed locally and you want the harness to call `qgis_process`.

Live `qgis_process` execution is gated by an explicit local approval checkpoint. The command returns a risk summary with payload size, parameter count, and detected input paths; add `--confirm` after review to allow execution. Set `GIS_AGENT_HARNESS_QGIS_REQUIRE_CONFIRM=false` only if you intentionally want to disable this local guardrail.

## Advanced GeoAI Manifests

The architecture blueprint features are exposed as deterministic local contracts first:

- `mcp-tools` returns a progressive-disclosure MCP-style tool catalog for vector, raster, discovery, and desktop domains.
- `mcp-call` executes supported local MCP tools such as `inspect-vector` and `inspect-raster` through a dispatcher, so the protocol surface is not only declarative.
- `align-params` performs last-attempt alignment for common CRS, bbox, and numeric parameter formats before tool execution.
- `capture-artifact` and `judge-map` record map images with hashes/thumbnails and produce local review findings for missing layers or legends.
- `stac-plan`, `faas-manifest`, `qgis-plugin-manifest`, and `cog-viewer` create dry-run manifests for data discovery, serverless compute, QGIS desktop bridging, and browser-side COG review.
- `route-resource` classifies generated scripts into CPU/GPU container tracks from imports such as `torch`, `cupy`, or `rasterio`.
- `benchmark-manifest` emits GeoAgentBench, GeoBenchX, and GIS-Bench task manifests and optional JUnit XML for CI, while `benchmark-run` executes local sanity checks over those suites.
- `method-review` and `explain-exception` provide adversarial methodology checks and GIS-specific exception repair guidance.
- `compact-failures` collapses repeated failed actions into a compact replanning warning instead of replaying the same failing history.
- `requirement-matrix` publishes blueprint-to-implementation coverage evidence.
- `narrative-report` turns adoption-report JSON into `NARRATIVE_REPORT.md` for provenance and handoff.

These commands do not deploy cloud infrastructure, start a web server, or call external APIs by default.

## Declarative Plans And Review Gates

Execution plans let you pin task intent outside the raw prompt. A plan can provide:

- the template id to render
- default input paths and CRS declarations
- a retry budget
- an allowlist of repair actions that the reviewer will enforce

Before any generated Python reaches the sandbox, the reviewer scores the decision on action fit, provenance, safety, and clarity. If the plan violates the current observations or the declared action policy, the harness records a `review` stage and asks the router to replan.

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

Use `show-telemetry` to inspect the event journal directly. `--summary` returns compact event counts per run, which is useful when you want a control-plane style view of review rejections, sandbox runs, and final outcomes without reopening the full state log.

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
- `pytest -q tests/test_advanced_geoai.py` passes for MCP, PEA alignment, visual review, STAC/FaaS/QGIS/COG manifests, benchmarks, adversarial review, and exception parsing
- `pytest -q tests/test_blueprint_execution.py` passes for MCP dispatch, DAG execution, failure compaction, narrative reporting, runnable benchmarks, and the requirement matrix
- `Dockerfile` builds a local CLI image without adding any external service dependency
- `.github/workflows/ci.yml` keeps the offline suite, smoke scripts, and package build wired into CI
- `README.md`, `docs/architecture.md`, `docs/operations.md`, `AGENTS.md`, and `.codex/config.toml` stay in sync with the current commands and constraints
