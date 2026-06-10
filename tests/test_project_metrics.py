from __future__ import annotations

import json
import subprocess
from pathlib import Path

from click.testing import CliRunner

from gis_agent_harness.cli import main
from gis_agent_harness.project_metrics import build_project_metrics


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        check=True,
        text=True,
    )
    return result.stdout.strip()


def _make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "agent@example.com")
    _git(repo, "config", "user.name", "GIS Agent")

    (repo / "src" / "pkg").mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / "scripts").mkdir()
    (repo / "README.md").write_text("# Demo\n", encoding="utf-8")
    (repo / "src" / "pkg" / "app.py").write_text(
        "def area(width: float, height: float) -> float:\n"
        "    return width * height\n",
        encoding="utf-8",
    )
    (repo / "tests" / "test_app.py").write_text(
        "def test_area() -> None:\n"
        "    assert 2 * 3 == 6\n",
        encoding="utf-8",
    )
    (repo / "scripts" / "run.py").write_text("print('run')\n", encoding="utf-8")
    (repo / "src" / "pkg" / "untracked.py").write_text("print('ignored by metrics')\n" * 20, encoding="utf-8")

    _git(repo, "add", "README.md", "src/pkg/app.py", "tests/test_app.py", "scripts/run.py")
    _git(repo, "commit", "-m", "initial")
    return repo


def test_project_metrics_counts_tracked_python_lines_and_targets(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)

    metrics = build_project_metrics(repo, target_commits=2, target_python_lines=8)
    payload = metrics.to_dict()

    assert payload["root"] == str(repo.resolve())
    assert payload["git"]["is_repository"] is True
    assert payload["git"]["head_commit_count"] == 1
    assert payload["git"]["worktree_clean"] is False
    assert payload["line_counts"]["tracked_files"] == 4
    assert payload["line_counts"]["python"] == {
        "src": 2,
        "tests": 2,
        "scripts": 1,
        "other": 0,
        "total": 5,
    }
    assert payload["targets"]["commits"] == {
        "required": 2,
        "current": 1,
        "remaining": 1,
        "met": False,
        "basis": "HEAD",
    }
    assert payload["targets"]["python_lines"] == {
        "required": 8,
        "current": 5,
        "remaining": 3,
        "met": False,
    }


def test_project_metrics_cli_outputs_json(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "project-metrics",
            "--root",
            str(repo),
            "--target-commits",
            "2",
            "--target-python-lines",
            "8",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["git"]["head_commit_count"] == 1
    assert payload["line_counts"]["python"]["total"] == 5
    assert payload["targets"]["commits"]["remaining"] == 1
    assert payload["targets"]["python_lines"]["remaining"] == 3


def test_project_metrics_command_is_in_cli_help() -> None:
    runner = CliRunner()

    result = runner.invoke(main, ["--help"])

    assert result.exit_code == 0
    assert "project-metrics" in result.output
