from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any


def _remove_path(path: Path) -> bool:
    if not path.exists():
        return False
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()
    return True


def cleanup_local_state(project_root: str | Path, *, include_fixtures: bool = False) -> dict[str, Any]:
    root = Path(project_root)
    removed_roots: list[str] = []

    for name in (".demo-runs", ".pytest-smoke", ".local-fixtures"):
        if _remove_path(root / name):
            removed_roots.append(name)

    run_root = root / ".runs"
    pruned_run_entries: list[str] = []
    if run_root.exists():
        for subdir_name in ("logs", "failed", "artifacts"):
            subdir = run_root / subdir_name
            if not subdir.exists():
                continue
            for child in list(subdir.iterdir()):
                if child.name == ".gitkeep":
                    continue
                if child.is_dir():
                    shutil.rmtree(child)
                else:
                    child.unlink()
                pruned_run_entries.append(str(child.relative_to(root)))
        state_jsonl = run_root / "state.jsonl"
        if state_jsonl.exists():
            state_jsonl.unlink()
            pruned_run_entries.append(str(state_jsonl.relative_to(root)))

    fixtures_removed = False
    if include_fixtures:
        fixtures_removed = _remove_path(root / "tests" / "fixtures")

    return {
        "project_root": str(root),
        "removed_roots": removed_roots,
        "pruned_run_entries": pruned_run_entries,
        "fixtures_removed": fixtures_removed,
    }
