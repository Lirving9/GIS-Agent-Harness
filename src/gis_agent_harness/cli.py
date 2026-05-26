from __future__ import annotations

import json
from pathlib import Path

import click

from .config import HarnessConfig
from .errors import DataInspectionError


def _dump(payload: object) -> None:
    click.echo(json.dumps(payload, indent=2, ensure_ascii=False))


@click.group()
def main() -> None:
    """GIS Agent Harness CLI."""


@main.command("inspect-vector")
@click.argument("path", type=click.Path(path_type=Path))
@click.option("--sample-size", default=3, show_default=True, type=int)
def inspect_vector_command(path: Path, sample_size: int) -> None:
    """Inspect vector dataset metadata."""
    from .spatial_tools import inspect_vector

    try:
        result = inspect_vector(path, sample_size=sample_size)
    except DataInspectionError as exc:
        raise click.ClickException(str(exc)) from exc
    _dump(result.to_dict())


@main.command("inspect-raster")
@click.argument("path", type=click.Path(path_type=Path))
def inspect_raster_command(path: Path) -> None:
    """Inspect raster dataset metadata."""
    from .spatial_tools import inspect_raster

    try:
        result = inspect_raster(path)
    except DataInspectionError as exc:
        raise click.ClickException(str(exc)) from exc
    _dump(result.to_dict())


@main.command("run-task")
@click.option("--task-summary", required=True, help="Short task description.")
@click.option("--vector", "vector_path", required=True, type=click.Path(path_type=Path))
@click.option("--raster", "raster_path", type=click.Path(path_type=Path))
@click.option("--source-crs", help="Declare the source CRS when vector metadata is missing.")
@click.option("--max-iterations", default=None, type=int, help="Override the configured retry budget.")
@click.option("--mock/--live", "use_mock", default=None, help="Use mock or live LiteLLM routing.")
@click.option("--run-root", type=click.Path(path_type=Path), default=None)
@click.option("--state-file", type=click.Path(path_type=Path), default=None)
def run_task_command(
    task_summary: str,
    vector_path: Path,
    raster_path: Path | None,
    source_crs: str | None,
    max_iterations: int | None,
    use_mock: bool | None,
    run_root: Path | None,
    state_file: Path | None,
) -> None:
    """Run the guarded mock-first repair loop."""
    from .agent_loop import AgentLoop, AgentTask
    from .llm_router import LLMRouter

    config = HarnessConfig.from_env()
    if use_mock is not None:
        config.use_mock = use_mock
    if max_iterations is not None:
        config.max_iterations = max_iterations
    if run_root is not None:
        config.run_root = run_root
    if state_file is not None:
        config.state_file = state_file

    router = LLMRouter(
        primary_model=config.primary_model,
        fallback_model=config.fallback_model,
        use_mock=config.use_mock,
    )
    loop = AgentLoop(config=config, router=router)
    task = AgentTask(
        task_summary=task_summary,
        vector_path=str(vector_path),
        raster_path=str(raster_path) if raster_path else None,
        source_crs=source_crs,
        max_iterations=config.max_iterations,
    )
    result = loop.run(task)
    _dump(result.to_dict())
    if result.status != "succeeded":
        raise click.exceptions.Exit(1)


@main.command("show-state")
@click.option("--limit", default=5, show_default=True, type=int)
@click.option("--format", "output_format", type=click.Choice(["json", "markdown"]), default="json", show_default=True)
@click.option("--run-id", default=None, help="Filter JSON output to a specific run id.")
@click.option("--status", default=None, help="Filter JSON output by snapshot status.")
@click.option("--stage", default=None, help="Filter JSON output by snapshot stage.")
@click.option("--failed-only", is_flag=True, help="Only include failed snapshots in JSON output.")
@click.option("--state-file", type=click.Path(path_type=Path), default=None)
@click.option("--run-root", type=click.Path(path_type=Path), default=None)
def show_state_command(
    limit: int,
    output_format: str,
    run_id: str | None,
    status: str | None,
    stage: str | None,
    failed_only: bool,
    state_file: Path | None,
    run_root: Path | None,
) -> None:
    """Show recent state snapshots."""
    from .state_store import StateStore

    config = HarnessConfig.from_env()
    if state_file is not None:
        config.state_file = state_file
    if run_root is not None:
        config.run_root = run_root
    store = StateStore(config.state_file, config.run_root)
    if output_format == "markdown" and any(value is not None for value in (run_id, status, stage)) or (
        output_format == "markdown" and failed_only
    ):
        raise click.ClickException("Filtering options are only supported with --format json.")
    if output_format == "markdown":
        click.echo(store.render_markdown())
        return
    click.echo(store.render_recent(limit=limit, run_id=run_id, status=status, stage=stage, failed_only=failed_only))


@main.command("list-runs")
@click.option("--limit", default=20, show_default=True, type=int)
@click.option("--failed-only", is_flag=True, help="Only include failed runs.")
@click.option("--status", default=None, help="Filter runs by terminal status, for example failed or succeeded.")
@click.option("--stage", default=None, help="Filter runs by terminal stage, for example stop or complete.")
@click.option("--contains", default=None, help="Filter by run id or task summary substring.")
@click.option("--state-file", type=click.Path(path_type=Path), default=None)
@click.option("--run-root", type=click.Path(path_type=Path), default=None)
def list_runs_command(
    limit: int,
    failed_only: bool,
    status: str | None,
    stage: str | None,
    contains: str | None,
    state_file: Path | None,
    run_root: Path | None,
) -> None:
    """List recent runs as compact JSON summaries."""
    from .state_store import StateStore

    config = HarnessConfig.from_env()
    if state_file is not None:
        config.state_file = state_file
    if run_root is not None:
        config.run_root = run_root
    store = StateStore(config.state_file, config.run_root)
    _dump(store.query_runs(limit=limit, failed_only=failed_only, status=status, stage=stage, contains=contains))


@main.command("resume-hint")
@click.option("--run-id", default=None, help="Show the summary for a specific run id instead of the latest failed run.")
@click.option("--state-file", type=click.Path(path_type=Path), default=None)
@click.option("--run-root", type=click.Path(path_type=Path), default=None)
def resume_hint_command(run_id: str | None, state_file: Path | None, run_root: Path | None) -> None:
    """Show a compact summary of the latest failed run."""
    from .state_store import StateStore

    config = HarnessConfig.from_env()
    if state_file is not None:
        config.state_file = state_file
    if run_root is not None:
        config.run_root = run_root
    store = StateStore(config.state_file, config.run_root)
    payload = store.run_summary(run_id) if run_id is not None else store.latest_failed_run_summary()
    if payload is None:
        raise click.ClickException("No matching run snapshots are available.")
    _dump(payload)


@main.command("show-failure-files")
@click.option("--run-id", default=None, help="Show failure files for a specific run id instead of the latest failed run.")
@click.option("--state-file", type=click.Path(path_type=Path), default=None)
@click.option("--run-root", type=click.Path(path_type=Path), default=None)
def show_failure_files_command(run_id: str | None, state_file: Path | None, run_root: Path | None) -> None:
    """Show log and failed-script paths for the latest failed run."""
    from .state_store import StateStore

    config = HarnessConfig.from_env()
    if state_file is not None:
        config.state_file = state_file
    if run_root is not None:
        config.run_root = run_root
    store = StateStore(config.state_file, config.run_root)
    if run_id is not None:
        summary = store.run_summary(run_id)
        if summary is None:
            payload = None
        else:
            log_dir = Path(config.run_root) / "logs" / run_id
            failed_dir = Path(config.run_root) / "failed"
            payload = {
                **summary,
                "log_dir": str(log_dir),
                "log_json_files": sorted(str(path) for path in log_dir.glob("*.json")) if log_dir.exists() else [],
                "log_py_files": sorted(str(path) for path in log_dir.glob("*.py")) if log_dir.exists() else [],
                "failed_scripts": (
                    sorted(str(path) for path in failed_dir.glob(f"{run_id}-*.py")) if failed_dir.exists() else []
                ),
            }
    else:
        payload = store.latest_failed_run_files()
    if payload is None:
        raise click.ClickException("No matching run snapshots are available.")
    _dump(payload)


@main.command("show-replay")
@click.option("--run-id", default=None, help="Show the rerun command for a specific run id instead of the latest failed run.")
@click.option("--state-file", type=click.Path(path_type=Path), default=None)
@click.option("--run-root", type=click.Path(path_type=Path), default=None)
def show_replay_command(run_id: str | None, state_file: Path | None, run_root: Path | None) -> None:
    """Show a suggested rerun command for the latest failed run."""
    from .state_store import StateStore

    config = HarnessConfig.from_env()
    if state_file is not None:
        config.state_file = state_file
    if run_root is not None:
        config.run_root = run_root
    store = StateStore(config.state_file, config.run_root)
    if run_id is not None:
        summary = store.run_summary(run_id)
        task = store.task_for_run(run_id)
        if summary is None or task is None:
            payload = None
        else:
            parts = ["python3", "-m", "gis_agent_harness.cli", "run-task"]
            if task.get("task_summary"):
                parts.extend(["--task-summary", task["task_summary"]])
            if task.get("vector_path"):
                parts.extend(["--vector", task["vector_path"]])
            if task.get("raster_path"):
                parts.extend(["--raster", task["raster_path"]])
            if task.get("source_crs"):
                parts.extend(["--source-crs", task["source_crs"]])
            payload = {
                **summary,
                "rerun_command": " ".join(json.dumps(part, ensure_ascii=False) for part in parts),
                "suggested_fix": summary.get("next_step_hint"),
            }
    else:
        payload = store.latest_failed_run_replay()
    if payload is None:
        raise click.ClickException("No matching run snapshots are available.")
    _dump(payload)


@main.command("replay-last")
@click.option("--run-id", default=None, help="Replay a specific run id instead of the latest failed run.")
@click.option("--state-file", type=click.Path(path_type=Path), default=None)
@click.option("--run-root", type=click.Path(path_type=Path), default=None)
@click.option("--source-crs", default=None, help="Override source CRS when replaying a failed run.")
@click.option("--max-iterations", default=None, type=int, help="Override max iterations for the replayed run.")
@click.option("--mock/--live", "use_mock", default=None, help="Use mock or live LiteLLM routing.")
@click.option("--dry-run", is_flag=True, help="Print the reconstructed replay task without executing it.")
def replay_last_command(
    run_id: str | None,
    state_file: Path | None,
    run_root: Path | None,
    source_crs: str | None,
    max_iterations: int | None,
    use_mock: bool | None,
    dry_run: bool,
) -> None:
    """Replay the latest failed run using its stored task context."""
    from .agent_loop import AgentLoop, AgentTask
    from .llm_router import LLMRouter
    from .state_store import StateStore

    config = HarnessConfig.from_env()
    if state_file is not None:
        config.state_file = state_file
    if run_root is not None:
        config.run_root = run_root
    if use_mock is not None:
        config.use_mock = use_mock
    if max_iterations is not None:
        config.max_iterations = max_iterations

    store = StateStore(config.state_file, config.run_root)
    task_payload = store.task_for_run(run_id) if run_id is not None else store.latest_failed_task()
    if task_payload is None:
        raise click.ClickException("No matching run snapshots are available.")

    task = AgentTask(
        task_summary=task_payload["task_summary"],
        vector_path=task_payload["vector_path"],
        raster_path=task_payload.get("raster_path"),
        source_crs=source_crs if source_crs is not None else task_payload.get("source_crs"),
        max_iterations=max_iterations if max_iterations is not None else task_payload.get("max_iterations", config.max_iterations),
    )
    if dry_run:
        parts = ["python3", "-m", "gis_agent_harness.cli", "run-task"]
        if task.task_summary:
            parts.extend(["--task-summary", task.task_summary])
        if task.vector_path:
            parts.extend(["--vector", task.vector_path])
        if task.raster_path:
            parts.extend(["--raster", task.raster_path])
        if task.source_crs:
            parts.extend(["--source-crs", task.source_crs])
        _dump(
            {
                "mode": "dry-run",
                "run_id": run_id,
                "task": task.to_dict(),
                "rerun_command": " ".join(json.dumps(part, ensure_ascii=False) for part in parts),
            }
        )
        return
    router = LLMRouter(
        primary_model=config.primary_model,
        fallback_model=config.fallback_model,
        use_mock=config.use_mock,
    )
    loop = AgentLoop(config=config, router=router)
    result = loop.run(task)
    _dump(result.to_dict())
    if result.status != "succeeded":
        raise click.exceptions.Exit(1)


if __name__ == "__main__":
    main()
