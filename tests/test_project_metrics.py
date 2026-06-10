from __future__ import annotations

import json
import subprocess
from pathlib import Path

from click.testing import CliRunner

from gis_agent_harness.cli import main
from gis_agent_harness.project_metrics import build_project_metrics, render_project_metrics_markdown


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


def _add_tracked_python_file(repo: Path, relative_path: str, line_count: int) -> None:
    path = repo / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("print('line')\n" * line_count, encoding="utf-8")
    _git(repo, "add", relative_path)
    _git(repo, "commit", "-m", f"add {relative_path}")


def test_project_metrics_counts_tracked_python_lines_and_targets(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)

    metrics = build_project_metrics(repo, target_commits=2, target_python_lines=8, target_total_lines=6)
    payload = metrics.to_dict()

    assert payload["root"] == str(repo.resolve())
    assert payload["git"]["is_repository"] is True
    assert payload["git"]["head_commit_count"] == 1
    assert payload["git"]["worktree_clean"] is False
    assert payload["git"]["status_summary"] == {
        "added": 0,
        "deleted": 0,
        "modified": 0,
        "renamed": 0,
        "untracked": 1,
        "other": 0,
    }
    assert payload["line_counts"]["tracked_files"] == 4
    assert payload["line_counts"]["file_types"] == {
        ".md": {"files": 1, "lines": 1},
        ".py": {"files": 3, "lines": 5},
    }
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
    assert payload["targets"]["total_lines"] == {
        "required": 6,
        "current": 6,
        "remaining": 0,
        "met": True,
    }


def test_project_metrics_counts_python_lines_without_git_repo(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    (source_root / "src" / "pkg").mkdir(parents=True)
    (source_root / "tests").mkdir()
    (source_root / "src" / "pkg" / "app.py").write_text("print('src')\n" * 3, encoding="utf-8")
    (source_root / "tests" / "test_app.py").write_text("print('test')\n" * 2, encoding="utf-8")
    (source_root / "README.md").write_text("# Source\n", encoding="utf-8")

    metrics = build_project_metrics(source_root, target_python_lines=5)
    payload = metrics.to_dict()

    assert payload["git"]["is_repository"] is False
    assert payload["line_counts"]["file_source"] == "filesystem"
    assert payload["line_counts"]["tracked_files"] == 3
    assert payload["line_counts"]["file_types"] == {
        ".md": {"files": 1, "lines": 1},
        ".py": {"files": 2, "lines": 5},
    }
    assert payload["line_counts"]["python"] == {
        "src": 3,
        "tests": 2,
        "scripts": 0,
        "other": 0,
        "total": 5,
    }
    assert payload["targets"]["python_lines"]["met"] is True


def test_project_metrics_reports_top_tracked_python_files(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    _add_tracked_python_file(repo, "src/pkg/big.py", 4)

    metrics = build_project_metrics(repo, top_files_limit=2)
    payload = metrics.to_dict()

    assert payload["line_counts"]["file_source"] == "git"
    assert payload["line_counts"]["top_python_files"] == [
        {"path": "src/pkg/big.py", "lines": 4},
        {"path": "src/pkg/app.py", "lines": 2},
    ]


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
            "--target-total-lines",
            "6",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["git"]["head_commit_count"] == 1
    assert payload["line_counts"]["python"]["total"] == 5
    assert payload["targets"]["commits"]["remaining"] == 1
    assert payload["targets"]["python_lines"]["remaining"] == 3
    assert payload["targets"]["total_lines"]["met"] is True


def test_project_metrics_cli_limits_top_python_files(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    _add_tracked_python_file(repo, "src/pkg/big.py", 4)
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "project-metrics",
            "--root",
            str(repo),
            "--top-files",
            "1",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["line_counts"]["top_python_files"] == [
        {"path": "src/pkg/big.py", "lines": 4},
    ]


def test_project_metrics_clamps_negative_top_file_limit(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    _add_tracked_python_file(repo, "src/pkg/big.py", 4)

    metrics = build_project_metrics(repo, top_files_limit=-1)
    payload = metrics.to_dict()

    assert payload["line_counts"]["top_python_files"] == []


def test_project_metrics_markdown_renderer_summarizes_targets(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    metrics = build_project_metrics(repo, target_commits=2, target_python_lines=8)

    markdown = render_project_metrics_markdown(metrics)

    assert markdown.startswith("# GIS Agent Harness Project Metrics")
    assert "- Root:" in markdown
    assert "- File source: git" in markdown
    assert "## Git Status" in markdown
    assert "| untracked | 1 |" in markdown
    assert "## File Types" in markdown
    assert "| .py | 3 | 5 |" in markdown
    assert "| Target | Required | Current | Remaining | Met | Basis |" in markdown
    assert "| commits | 2 | 1 | 1 | no | HEAD |" in markdown
    assert "| python_lines | 8 | 5 | 3 | no |  |" in markdown
    assert "| src | 2 |" in markdown
    assert "| tests | 2 |" in markdown


def test_project_metrics_cli_renders_markdown(tmp_path: Path) -> None:
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
            "--format",
            "markdown",
        ],
    )

    assert result.exit_code == 0
    assert "# GIS Agent Harness Project Metrics" in result.output
    assert "| python_lines | 8 | 5 | 3 | no |  |" in result.output


def test_project_metrics_cli_can_fail_when_targets_are_unmet(tmp_path: Path) -> None:
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
            "--fail-on-unmet-targets",
        ],
    )

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["targets"]["commits"]["met"] is False
    assert payload["targets"]["python_lines"]["met"] is False


def test_project_metrics_cli_strict_mode_passes_when_targets_are_met(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "project-metrics",
            "--root",
            str(repo),
            "--target-commits",
            "1",
            "--target-python-lines",
            "5",
            "--fail-on-unmet-targets",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["targets"]["commits"]["met"] is True
    assert payload["targets"]["python_lines"]["met"] is True


def test_project_metrics_cli_can_fail_when_worktree_is_dirty(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "project-metrics",
            "--root",
            str(repo),
            "--require-clean",
        ],
    )

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["git"]["worktree_clean"] is False
    assert payload["git"]["status_summary"]["untracked"] == 1


def test_project_metrics_command_is_in_cli_help() -> None:
    runner = CliRunner()

    result = runner.invoke(main, ["--help"])

    assert result.exit_code == 0
    assert "project-metrics" in result.output
