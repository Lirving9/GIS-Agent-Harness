# GIS Agent Harness Instructions

- Install with `python -m pip install -r requirements.txt`.
- Generate local fixtures with `python3 scripts/generate_sample_data.py` if `tests/fixtures/` is missing.
- Prefer isolated fixture roots for ad hoc runs, for example `python3 scripts/generate_sample_data.py --output-dir .local-fixtures`.
- Use `python3 scripts/clean_local_state.py` to reset local runtime artifacts before creating a fresh checkpoint.
- Run the full offline validation suite with `pytest -q`.
- Use `python scripts/demo_task.py` for the smoke test; it must stay offline and default to mock routing.
- Keep tests and demo runs from mutating the shared `tests/fixtures/` directory.
- Keep CLI help fast: avoid importing GeoPandas, Fiona, or Rasterio in module scope for `cli.py`.
- Do not add external services, databases, or web servers to the MVP path.
- Preserve append-only state logging in `AGENT_STATE.md` and `.runs/state.jsonl`.
