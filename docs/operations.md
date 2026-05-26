# Operations

## Common Commands

```bash
python3 scripts/generate_sample_data.py
python3 scripts/generate_sample_data.py --output-dir .local-fixtures
python3 -m gis_agent_harness.cli inspect-vector tests/fixtures/vector/sample.gpkg
python3 -m gis_agent_harness.cli inspect-raster tests/fixtures/raster/sample.tif
python3 -m gis_agent_harness.cli run-task \
  --task-summary "Align vector CRS to raster CRS" \
  --vector tests/fixtures/vector/sample_3857.gpkg \
  --raster tests/fixtures/raster/sample.tif
python3 -m gis_agent_harness.cli show-state --limit 3
python3 -m gis_agent_harness.cli show-state --format table
python3 -m gis_agent_harness.cli list-runs --failed-only
python3 -m gis_agent_harness.cli list-runs --format table
python3 -m gis_agent_harness.cli list-runs --status failed --stage stop --contains geometry
python3 -m gis_agent_harness.cli resume-hint
python3 -m gis_agent_harness.cli show-failure-files
python3 -m gis_agent_harness.cli show-failure-files --format table
python3 -m gis_agent_harness.cli show-replay
python3 -m gis_agent_harness.cli replay-last --source-crs EPSG:4326 --confirm
python3 -m gis_agent_harness.cli replay-last --run-id RUN_ID --source-crs EPSG:4326 --confirm
python3 -m gis_agent_harness.cli replay-last --run-id RUN_ID --source-crs EPSG:4326 --dry-run
pytest -q
python3 scripts/demo_task.py
python3 scripts/demo_failures.py
python3 scripts/clean_local_state.py
```

## Logs and Recovery

- `AGENT_STATE.md`: human-readable append-only log
- `.runs/state.jsonl`: machine-readable append-only snapshots
- `.runs/logs/<run_id>/`: per-step scripts and sandbox results
- `.runs/failed/`: copies of blocked or failed scripts
- `.demo-runs/fixtures/`: default isolated fixture root for `scripts/demo_task.py`
- `show-state --format table`: terminal-friendly snapshot view
- `list-runs`: compact run discovery view before filtering or replaying a specific `run_id`
- `--format table`: terminal-friendly summary for quick scanning
- `--status`, `--stage`, `--contains`: narrow the run list to the exact recovery candidate you need
- `resume-hint`: latest failed-run summary with task context and next-step hint
- `show-failure-files`: latest failed-run log/script paths for direct inspection
- `show-failure-files --format table`: terminal-friendly failed artifact summary
- `show-replay`: suggested rerun command for the latest failed run
- `replay-last`: execute a fresh run based on the latest failed task context
- `--run-id RUN_ID`: target a specific recorded run when summarizing, locating files, or replaying
- `--dry-run`: preview the reconstructed replay task and command without executing it
- `--confirm`: required before `replay-last` actually executes

## Failure Triage

- missing path: check fixture generation or command arguments
- missing CRS: declare the source CRS with `set_crs(...)`
- CRS mismatch: reproject with `to_crs(...)`
- invalid geometry: repair with `make_valid()`
- AST block: remove unsafe imports or dangerous calls
- timeout: inspect `.runs/logs/<run_id>/` and tighten the generated script
- `python3 scripts/demo_failures.py` exercises both a guardrail-blocked script and a timeout path

## Cleanup

- Run `python3 scripts/clean_local_state.py` to remove local runtime directories and prune `.runs/` artifacts while preserving tracked `.gitkeep` files.
- Run `python3 scripts/clean_local_state.py --include-fixtures` to also remove generated `tests/fixtures/`.
