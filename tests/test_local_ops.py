from __future__ import annotations

from pathlib import Path

from gis_agent_harness.local_ops import cleanup_local_state


def test_cleanup_local_state_prunes_runtime_directories(tmp_path: Path) -> None:
    for dirname in (".demo-runs", ".pytest-smoke", ".local-fixtures"):
        path = tmp_path / dirname
        path.mkdir(parents=True, exist_ok=True)
        (path / "artifact.txt").write_text("x", encoding="utf-8")

    run_root = tmp_path / ".runs"
    for dirname in ("logs", "failed", "artifacts"):
        subdir = run_root / dirname
        subdir.mkdir(parents=True, exist_ok=True)
        (subdir / ".gitkeep").write_text("", encoding="utf-8")
        (subdir / "old.txt").write_text("y", encoding="utf-8")
    (run_root / "state.jsonl").write_text("{}", encoding="utf-8")

    payload = cleanup_local_state(tmp_path)

    assert sorted(payload["removed_roots"]) == [".demo-runs", ".local-fixtures", ".pytest-smoke"]
    assert not (tmp_path / ".demo-runs").exists()
    assert not (tmp_path / ".pytest-smoke").exists()
    assert not (tmp_path / ".local-fixtures").exists()
    assert not (run_root / "state.jsonl").exists()
    assert (run_root / "logs" / ".gitkeep").exists()
    assert not (run_root / "logs" / "old.txt").exists()


def test_cleanup_local_state_can_remove_generated_fixtures(tmp_path: Path) -> None:
    fixtures_root = tmp_path / "tests" / "fixtures" / "vector"
    fixtures_root.mkdir(parents=True, exist_ok=True)
    (fixtures_root / "sample.gpkg").write_text("fixture", encoding="utf-8")

    payload = cleanup_local_state(tmp_path, include_fixtures=True)

    assert payload["fixtures_removed"] is True
    assert not (tmp_path / "tests" / "fixtures").exists()
