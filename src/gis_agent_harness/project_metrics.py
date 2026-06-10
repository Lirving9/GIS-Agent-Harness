from __future__ import annotations

import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path


_IGNORED_FALLBACK_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".runs",
    ".venv",
    "__pycache__",
    "node_modules",
    "reports",
    "venv",
}


@dataclass(frozen=True, slots=True)
class GitMetrics:
    is_repository: bool
    branch: str | None
    head: str | None
    head_commit_count: int | None
    upstream_ref: str | None
    upstream_commit_count: int | None
    ahead: int | None
    behind: int | None
    worktree_clean: bool | None
    status_entries: list[str]
    status_summary: dict[str, int]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ProjectMetrics:
    root: Path
    git: GitMetrics
    line_counts: dict[str, object]
    targets: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "root": str(self.root),
            "git": self.git.to_dict(),
            "line_counts": self.line_counts,
            "targets": self.targets,
        }


def _run_git(root: Path, *args: str) -> tuple[bool, str]:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        check=False,
        text=True,
    )
    return result.returncode == 0, result.stdout.strip()


def _parse_count(value: str) -> int | None:
    try:
        return int(value.strip())
    except ValueError:
        return None


def _tracked_files(root: Path, is_repository: bool) -> list[Path]:
    if is_repository:
        ok, stdout = _run_git(root, "ls-files")
        if not ok:
            return []
        return [Path(line) for line in stdout.splitlines() if line.strip()]

    if not root.exists():
        return []
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative_path = path.relative_to(root)
        if any(part in _IGNORED_FALLBACK_DIRS for part in relative_path.parts):
            continue
        files.append(relative_path)
    return sorted(files)


def _count_lines(path: Path) -> int:
    with path.open("rb") as handle:
        return sum(1 for _ in handle)


def _python_bucket(relative_path: Path) -> str:
    first_part = relative_path.parts[0] if relative_path.parts else ""
    if first_part in {"src", "tests", "scripts"}:
        return first_part
    return "other"


def _extension_key(relative_path: Path) -> str:
    return relative_path.suffix.lower() or "[none]"


def _summarize_status_entries(status_entries: list[str]) -> dict[str, int]:
    summary = {
        "added": 0,
        "deleted": 0,
        "modified": 0,
        "renamed": 0,
        "untracked": 0,
        "other": 0,
    }
    for entry in status_entries:
        code = entry[:2]
        if code == "??":
            summary["untracked"] += 1
        elif "R" in code:
            summary["renamed"] += 1
        elif "A" in code:
            summary["added"] += 1
        elif "D" in code:
            summary["deleted"] += 1
        elif "M" in code:
            summary["modified"] += 1
        else:
            summary["other"] += 1
    return summary


def _build_line_counts(
    root: Path,
    files: list[Path],
    *,
    file_source: str,
    top_files_limit: int = 10,
) -> dict[str, object]:
    python_counts = {"src": 0, "tests": 0, "scripts": 0, "other": 0, "total": 0}
    python_files = 0
    total_lines = 0
    python_file_counts: list[dict[str, object]] = []
    file_type_counts: dict[str, dict[str, int]] = {}
    for relative_path in files:
        absolute_path = root / relative_path
        if not absolute_path.is_file():
            continue
        line_count = _count_lines(absolute_path)
        total_lines += line_count
        extension = _extension_key(relative_path)
        file_type_counts.setdefault(extension, {"files": 0, "lines": 0})
        file_type_counts[extension]["files"] += 1
        file_type_counts[extension]["lines"] += line_count
        if relative_path.suffix != ".py":
            continue
        python_counts[_python_bucket(relative_path)] += line_count
        python_counts["total"] += line_count
        python_files += 1
        python_file_counts.append({"path": relative_path.as_posix(), "lines": line_count})

    python_file_counts.sort(key=lambda item: (-int(item["lines"]), str(item["path"])))

    return {
        "file_source": file_source,
        "tracked_files": len(files),
        "python_files": python_files,
        "total_lines": total_lines,
        "file_types": dict(sorted(file_type_counts.items())),
        "python": python_counts,
        "top_python_files": python_file_counts[:top_files_limit],
    }


def _build_git_metrics(root: Path) -> GitMetrics:
    ok, stdout = _run_git(root, "rev-parse", "--is-inside-work-tree")
    is_repository = ok and stdout == "true"
    if not is_repository:
        return GitMetrics(
            is_repository=False,
            branch=None,
            head=None,
            head_commit_count=None,
            upstream_ref=None,
            upstream_commit_count=None,
            ahead=None,
            behind=None,
            worktree_clean=None,
            status_entries=[],
            status_summary={},
        )

    _, branch = _run_git(root, "branch", "--show-current")
    _, head = _run_git(root, "rev-parse", "--short", "HEAD")
    _, head_count_text = _run_git(root, "rev-list", "--count", "HEAD")
    head_commit_count = _parse_count(head_count_text)

    upstream_ref: str | None = None
    upstream_commit_count: int | None = None
    ahead: int | None = None
    behind: int | None = None
    ok, upstream_text = _run_git(root, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    if ok and upstream_text:
        upstream_ref = upstream_text
        ok, upstream_count_text = _run_git(root, "rev-list", "--count", upstream_ref)
        if ok:
            upstream_commit_count = _parse_count(upstream_count_text)
        ok, ahead_behind_text = _run_git(root, "rev-list", "--left-right", "--count", f"HEAD...{upstream_ref}")
        if ok:
            parts = ahead_behind_text.split()
            if len(parts) == 2:
                ahead = _parse_count(parts[0])
                behind = _parse_count(parts[1])

    _, status_text = _run_git(root, "status", "--short", "--untracked-files=all")
    status_entries = [line for line in status_text.splitlines() if line.strip()]
    return GitMetrics(
        is_repository=True,
        branch=branch or None,
        head=head or None,
        head_commit_count=head_commit_count,
        upstream_ref=upstream_ref,
        upstream_commit_count=upstream_commit_count,
        ahead=ahead,
        behind=behind,
        worktree_clean=not status_entries,
        status_entries=status_entries,
        status_summary=_summarize_status_entries(status_entries),
    )


def _build_targets(
    *,
    git: GitMetrics,
    line_counts: dict[str, object],
    target_commits: int | None,
    target_python_lines: int | None,
    target_total_lines: int | None,
) -> dict[str, object]:
    targets: dict[str, object] = {}
    if target_commits is not None:
        current = git.upstream_commit_count if git.upstream_commit_count is not None else git.head_commit_count
        current_count = current or 0
        targets["commits"] = {
            "required": target_commits,
            "current": current_count,
            "remaining": max(target_commits - current_count, 0),
            "met": current_count >= target_commits,
            "basis": git.upstream_ref or "HEAD",
        }
    if target_python_lines is not None:
        python_counts = line_counts.get("python")
        current_count = python_counts.get("total", 0) if isinstance(python_counts, dict) else 0
        targets["python_lines"] = {
            "required": target_python_lines,
            "current": current_count,
            "remaining": max(target_python_lines - current_count, 0),
            "met": current_count >= target_python_lines,
        }
    if target_total_lines is not None:
        current_count = line_counts.get("total_lines", 0)
        current_total = current_count if isinstance(current_count, int) else 0
        targets["total_lines"] = {
            "required": target_total_lines,
            "current": current_total,
            "remaining": max(target_total_lines - current_total, 0),
            "met": current_total >= target_total_lines,
        }
    return targets


def _markdown_bool(value: object) -> str:
    return "yes" if value is True else "no" if value is False else ""


def render_project_metrics_markdown(metrics: ProjectMetrics) -> str:
    payload = metrics.to_dict()
    git = payload["git"] if isinstance(payload["git"], dict) else {}
    line_counts = payload["line_counts"] if isinstance(payload["line_counts"], dict) else {}
    python_counts = line_counts.get("python", {}) if isinstance(line_counts.get("python"), dict) else {}
    targets = payload["targets"] if isinstance(payload["targets"], dict) else {}

    lines = [
        "# GIS Agent Harness Project Metrics",
        "",
        "## Repository",
        f"- Root: {payload['root']}",
        f"- Branch: {git.get('branch') or ''}",
        f"- HEAD: {git.get('head') or ''}",
        f"- Upstream: {git.get('upstream_ref') or ''}",
        f"- File source: {line_counts.get('file_source') or ''}",
        f"- Worktree clean: {_markdown_bool(git.get('worktree_clean'))}",
        f"- Ahead/behind: {git.get('ahead') if git.get('ahead') is not None else ''}/{git.get('behind') if git.get('behind') is not None else ''}",
        "",
        "## Git Status",
        "| State | Files |",
        "| --- | ---: |",
    ]
    status_summary = git.get("status_summary", {}) if isinstance(git.get("status_summary"), dict) else {}
    for status_name in ("added", "deleted", "modified", "renamed", "untracked", "other"):
        lines.append(f"| {status_name} | {status_summary.get(status_name, 0)} |")

    lines.extend(
        [
        "",
        "## File Types",
        "| Extension | Files | Lines |",
        "| --- | ---: | ---: |",
        ]
    )
    file_types = line_counts.get("file_types", {}) if isinstance(line_counts.get("file_types"), dict) else {}
    for extension, counts in file_types.items():
        item = counts if isinstance(counts, dict) else {}
        lines.append(f"| {extension} | {item.get('files', 0)} | {item.get('lines', 0)} |")

    lines.extend(
        [
        "",
        "## Python Lines",
        "| Bucket | Lines |",
        "| --- | ---: |",
        ]
    )
    for bucket in ("src", "tests", "scripts", "other", "total"):
        lines.append(f"| {bucket} | {python_counts.get(bucket, 0)} |")

    lines.extend(
        [
            "",
            "## Largest Python Files",
            "| Path | Lines |",
            "| --- | ---: |",
        ]
    )
    for item in line_counts.get("top_python_files", []):
        file_item = item if isinstance(item, dict) else {}
        lines.append(f"| {file_item.get('path', '')} | {file_item.get('lines', '')} |")

    lines.extend(
        [
            "",
            "## Targets",
            "| Target | Required | Current | Remaining | Met | Basis |",
            "| --- | ---: | ---: | ---: | --- | --- |",
        ]
    )
    for target_name, target in targets.items():
        item = target if isinstance(target, dict) else {}
        lines.append(
            "| "
            + " | ".join(
                [
                    str(target_name),
                    str(item.get("required", "")),
                    str(item.get("current", "")),
                    str(item.get("remaining", "")),
                    _markdown_bool(item.get("met")),
                    str(item.get("basis", "")),
                ]
            )
            + " |"
        )
    return "\n".join(lines)


def build_project_metrics(
    root: str | Path = Path("."),
    *,
    target_commits: int | None = None,
    target_python_lines: int | None = None,
    target_total_lines: int | None = None,
    top_files_limit: int = 10,
) -> ProjectMetrics:
    resolved_root = Path(root).resolve()
    git = _build_git_metrics(resolved_root)
    files = _tracked_files(resolved_root, git.is_repository)
    line_counts = _build_line_counts(
        resolved_root,
        files,
        file_source="git" if git.is_repository else "filesystem",
        top_files_limit=top_files_limit,
    )
    targets = _build_targets(
        git=git,
        line_counts=line_counts,
        target_commits=target_commits,
        target_python_lines=target_python_lines,
        target_total_lines=target_total_lines,
    )
    return ProjectMetrics(root=resolved_root, git=git, line_counts=line_counts, targets=targets)
