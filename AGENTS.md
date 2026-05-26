# GIS Agent Harness Instructions

- Install with `python -m pip install -r requirements.txt`.
- Generate local fixtures with `python scripts/generate_sample_data.py` if `tests/fixtures/` is missing.
- Run the full offline validation suite with `pytest -q`.
- Use `python scripts/demo_task.py` for the smoke test; it must stay offline and default to mock routing.
- Keep CLI help fast: avoid importing GeoPandas, Fiona, or Rasterio in module scope for `cli.py`.
- Do not add external services, databases, or web servers to the MVP path.
- Preserve append-only state logging in `AGENT_STATE.md` and `.runs/state.jsonl`.
