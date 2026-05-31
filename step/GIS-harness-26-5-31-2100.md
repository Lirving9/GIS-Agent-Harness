# GIS Agent Harness Code Review - 2026-05-31 21:00

## Review Scope

- Reviewed the whole current workspace with the `reviewer` code-reviewer agent plus local static and test-driven checks.
- Focus areas: guardrails, sandbox containment, CLI/TUI behavior, state/recovery flows, local-first constraints, and AGENTS.md requirements.

## Findings And Fix Plan

1. High - Sandbox write-root policy only checked declared output paths.
   - Evidence: `SandboxRunner.run_python()` validated `expected_output_path`, but generated scripts could still call `Path(...).write_text()`, `unlink()`, `mkdir()`, or GIS writer APIs against arbitrary local paths.
   - Risk: live or generated repair code could mutate files outside `.runs/artifacts`.
   - Fix: add runtime write containment inside the sandbox subprocess, block writes outside the configured artifact root, and add a regression test for an undeclared `pathlib` write escape.

2. Medium - `show-state` returned unrelated data when JSON filters had no matches.
   - Evidence: filtered empty rows fell back to `store.render_recent()`, which could emit unrelated recent rows or markdown while the command defaulted to JSON.
   - Risk: recovery automation can act on the wrong run.
   - Fix: return `[]` for empty JSON/table result sets and add tests for missing filters and empty state.

3. Medium - TUI replay bypassed the CLI confirmation boundary.
   - Evidence: CLI replay requires `--confirm`, while the TUI `Replay` button directly started replay execution.
   - Risk: local state and artifacts can be changed from recovery UI after a single click.
   - Fix: require an explicit second confirmation click after showing a replay confirmation message, and cover the behavior in a headless TUI test.

4. Low/Medium - TUI goal form crashed on invalid max-iteration input.
   - Evidence: `GoalScreen` directly called `int()` on the text field.
   - Risk: non-numeric input breaks the TUI flow instead of showing a recoverable validation error.
   - Fix: validate positive integer input, render an error in the preview panel, and add a TUI regression test.

5. Low - CLI help/import path needed explicit protection against heavy GIS imports.
   - Evidence: `cli.py` imported `goal_runner` at module scope, which indirectly imported guardrails/spatial tooling. This risks loading GeoPandas/Fiona/Rasterio on `--help`, contrary to AGENTS.md.
   - Fix: move goal-runner imports into command handlers and add a subprocess-level import test proving `gis_agent_harness.cli` does not load `fiona`, `geopandas`, or `rasterio`.

## Implementation Status

- Fixed sandbox runtime containment so script writes through `open`, `pathlib.Path`, GeoPandas, Fiona, and Rasterio writer entry points are blocked unless they target the configured artifact root.
- Fixed sandbox result handling so a caught write violation still marks the run as guardrail-blocked.
- Fixed `show-state` JSON/table empty-result behavior to return an empty list instead of unrelated fallback state.
- Added TUI replay confirmation gating before executing replay from recovery.
- Added TUI max-iterations validation that reports recoverable input errors in the preview panel.
- Kept CLI help/import lightweight by moving goal-runner imports into command handlers.

## Verification

- `pytest -q` passed.
- `python3 scripts/verify_acceptance.py` passed with all acceptance and stop-condition checks true.
