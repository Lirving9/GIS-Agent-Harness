# GIS Agent Harness Instructions

- Install with `python3 -m pip install -r requirements.txt`.
- Generate local fixtures with `python3 scripts/generate_sample_data.py` if `tests/fixtures/` is missing.
- Prefer isolated fixture roots for ad hoc runs, for example `python3 scripts/generate_sample_data.py --output-dir .local-fixtures`.
- Run the full offline suite with `pytest -q`.
- Use `pytest -q tests/test_tui_smoke.py` when you need an explicit headless TUI check.
- Use `python3 -m gis_agent_harness.cli templates list`, `goal run`, and `config doctor` for the template-driven path.
- Use `python3 -m gis_agent_harness.cli tui` for the Textual UI; keep it local-only.
- Use `python3 scripts/demo_task.py`, `python3 scripts/demo_recovery.py`, and `python3 scripts/demo_readme_workflow.py` for offline smoke coverage.
- Use `python3 scripts/verify_acceptance.py` before final delivery for a single local JSON audit.
- Use `python3 scripts/demo_failures.py` to verify guardrail-blocked and timeout paths locally.
- Use `docker build -t gis-agent-harness .` only for local packaging checks; keep runtime behavior local-first.
- Use `python3 scripts/clean_local_state.py` before creating a fresh checkpoint.
- Keep tests and demos from mutating the shared `tests/fixtures/` directory.
- Keep CLI help fast: avoid importing GeoPandas, Fiona, or Rasterio in module scope for `cli.py`.
- Do not add external services, databases, or web servers to the MVP path.
- Preserve append-only state logging in `AGENT_STATE.md` and `.runs/state.jsonl`.
