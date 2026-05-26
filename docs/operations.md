# Operations

## Common Commands

```bash
python scripts/generate_sample_data.py
python scripts/generate_sample_data.py --output-dir .local-fixtures
python -m gis_agent_harness.cli inspect-vector tests/fixtures/vector/sample.gpkg
python -m gis_agent_harness.cli inspect-raster tests/fixtures/raster/sample.tif
python -m gis_agent_harness.cli run-task \
  --task-summary "Align vector CRS to raster CRS" \
  --vector tests/fixtures/vector/sample_3857.gpkg \
  --raster tests/fixtures/raster/sample.tif
python -m gis_agent_harness.cli show-state --limit 3
pytest -q
python scripts/demo_task.py
```

## Logs and Recovery

- `AGENT_STATE.md`: human-readable append-only log
- `.runs/state.jsonl`: machine-readable append-only snapshots
- `.runs/logs/<run_id>/`: per-step scripts and sandbox results
- `.runs/failed/`: copies of blocked or failed scripts
- `.demo-runs/fixtures/`: default isolated fixture root for `scripts/demo_task.py`

## Failure Triage

- missing path: check fixture generation or command arguments
- missing CRS: declare the source CRS with `set_crs(...)`
- CRS mismatch: reproject with `to_crs(...)`
- invalid geometry: repair with `make_valid()`
- AST block: remove unsafe imports or dangerous calls
- timeout: inspect `.runs/logs/<run_id>/` and tighten the generated script
