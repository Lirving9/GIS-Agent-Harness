# Operations

## Common Commands

```bash
python3 scripts/generate_sample_data.py
python3 scripts/generate_sample_data.py --output-dir .local-fixtures
python3 -m gis_agent_harness.cli inspect-vector tests/fixtures/vector/sample.gpkg
python3 -m gis_agent_harness.cli inspect-raster tests/fixtures/raster/sample.tif
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
python3 -m gis_agent_harness.cli run-task \
  --task-summary "Align vector CRS to raster CRS" \
  --vector tests/fixtures/vector/sample_3857.gpkg \
  --raster tests/fixtures/raster/sample.tif
python3 -m gis_agent_harness.cli show-state --limit 3
python3 -m gis_agent_harness.cli show-state --format table
python3 -m gis_agent_harness.cli list-runs --failed-only
python3 -m gis_agent_harness.cli list-runs --status failed --stage stop --contains geometry
python3 -m gis_agent_harness.cli resume-hint
python3 -m gis_agent_harness.cli show-failure-files
python3 -m gis_agent_harness.cli show-replay
python3 -m gis_agent_harness.cli export-report --latest-failed --print-index
python3 -m gis_agent_harness.cli show-report --latest
python3 -m gis_agent_harness.cli replay-last --run-id RUN_ID --source-crs EPSG:4326 --dry-run
python3 -m gis_agent_harness.cli replay-last --run-id RUN_ID --source-crs EPSG:4326 --confirm
pytest -q
pytest -q tests/test_tui_smoke.py
python3 scripts/demo_task.py
python3 scripts/demo_recovery.py
python3 scripts/demo_readme_workflow.py
python3 scripts/verify_acceptance.py
python3 scripts/demo_failures.py
python3 scripts/clean_local_state.py
docker build -t gis-agent-harness .
docker run --rm -it -v "$PWD":/workspace gis-agent-harness --help
```

## Provider Profiles

Mock mode stays the default. For live profiles:

```bash
export GIS_AGENT_HARNESS_USE_MOCK=false
export GIS_AGENT_HARNESS_PROVIDER=litellm
export GIS_AGENT_HARNESS_PRIMARY_MODEL=gis-openai
export GIS_AGENT_HARNESS_FALLBACK_MODEL=gis-claude
export LITELLM_CONFIG_PATH=litellm-config.yaml
```

For a third-party OpenAI-compatible endpoint:

```bash
export GIS_AGENT_HARNESS_USE_MOCK=false
export GIS_AGENT_HARNESS_PROVIDER=openai_compatible
export GIS_AGENT_HARNESS_PRIMARY_MODEL=gis-thirdparty
export GIS_AGENT_HARNESS_API_BASE=https://your-provider.example/v1
export GIS_AGENT_HARNESS_API_KEY=your-key
```

Use `python3 -m gis_agent_harness.cli config doctor` to validate profile wiring without making a live request.

`litellm-config.yaml` may use `${ENV_VAR}` or `os.environ/ENV_VAR` placeholders. The local config loader resolves both forms before adapter selection.

## Logs And Recovery

- `AGENT_STATE.md`: human-readable append-only log
- `.runs/state.jsonl`: machine-readable append-only snapshots
- `.runs/telemetry.jsonl`: local telemetry mirror of snapshots
- `.runs/logs/<run_id>/`: per-step scripts and sandbox results
- `.runs/failed/`: copies of blocked or failed scripts
- `show-state --format table`: terminal-friendly snapshot view
- `list-runs`: compact run discovery view before replaying
- `resume-hint`: latest failed-run summary with task context and next-step hint
- `show-failure-files`: latest failed-run log/script paths for direct inspection
- `show-replay`: suggested rerun command for the latest failed run
- `export-report`: one-shot report bundle with state, summary, failure-file, replay outputs, and an index file
- `show-report`: reopen an exported report bundle from `reports/`
- `replay-last --dry-run`: preview the reconstructed replay task and command
- `replay-last --confirm`: required before replay execution

## Failure Triage

- missing path: check fixture generation or command arguments
- missing CRS: declare the source CRS with `set_crs(...)`
- CRS mismatch: reproject with `to_crs(...)`
- invalid geometry: repair with `make_valid()`
- AST block: remove unsafe imports or dangerous calls
- output-path block: keep generated artifacts under `.runs/artifacts`
- timeout: inspect `.runs/logs/<run_id>/` and tighten the generated script
- `python3 scripts/demo_failures.py` exercises both a guardrail-blocked script and a timeout path

## Cleanup

- Run `python3 scripts/clean_local_state.py` to remove local runtime directories and prune `.runs/` artifacts while preserving tracked `.gitkeep` files.
- Run `python3 scripts/clean_local_state.py --include-fixtures` to also remove generated `tests/fixtures/`.

## CI And Packaging

- GitHub Actions workflow: [`.github/workflows/ci.yml`](/home/spiderli/GIS-Agent-Harness/.github/workflows/ci.yml)
- Container image entrypoint: [`Dockerfile`](/home/spiderli/GIS-Agent-Harness/Dockerfile)
- Package build check: `python -m build`
