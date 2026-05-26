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
@click.option("--state-file", type=click.Path(path_type=Path), default=None)
@click.option("--run-root", type=click.Path(path_type=Path), default=None)
def show_state_command(limit: int, output_format: str, state_file: Path | None, run_root: Path | None) -> None:
    """Show recent state snapshots."""
    from .state_store import StateStore

    config = HarnessConfig.from_env()
    if state_file is not None:
        config.state_file = state_file
    if run_root is not None:
        config.run_root = run_root
    store = StateStore(config.state_file, config.run_root)
    if output_format == "markdown":
        click.echo(store.render_markdown())
        return
    click.echo(store.render_recent(limit=limit))


if __name__ == "__main__":
    main()
