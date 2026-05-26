# GIS Agent Harness Instructions

- Install with `python3 -m pip install -r requirements.txt`.
- Generate local fixtures with `python3 scripts/generate_sample_data.py` if `tests/fixtures/` is missing.
- Prefer isolated fixture roots for ad hoc runs, for example `python3 scripts/generate_sample_data.py --output-dir .local-fixtures`.
- Use `python3 scripts/clean_local_state.py` to reset local runtime artifacts before creating a fresh checkpoint.
- Run the full offline validation suite with `pytest -q`.
- Use `python3 scripts/demo_task.py` for the smoke test; it must stay offline and default to mock routing.
- Use `python3 scripts/demo_failures.py` to verify guardrail-blocked and timeout failure paths locally.
- Keep tests and demo runs from mutating the shared `tests/fixtures/` directory.
- Use `python3 -m gis_agent_harness.cli resume-hint` to inspect the latest failed run before retrying manually.
- Use `python3 -m gis_agent_harness.cli show-failure-files` to jump straight to failed scripts and log JSON files.
- Use `python3 -m gis_agent_harness.cli show-replay` to reconstruct a recommended local rerun command.
- Keep CLI help fast: avoid importing GeoPandas, Fiona, or Rasterio in module scope for `cli.py`.
- Do not add external services, databases, or web servers to the MVP path.
- Preserve append-only state logging in `AGENT_STATE.md` and `.runs/state.jsonl`.
