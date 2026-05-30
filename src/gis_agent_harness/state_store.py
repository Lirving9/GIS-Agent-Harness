from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .errors import Observation
from .logging_utils import ensure_run_dirs, utc_now
from .state_hooks import StateHook

VECTOR_SUFFIXES = {".gpkg", ".shp", ".geojson", ".json"}
RASTER_SUFFIXES = {".tif", ".tiff"}


@dataclass(slots=True)
class StateSnapshot:
    run_id: str
    iteration: int
    stage: str
    status: str
    summary: str
    observations: list[Observation] = field(default_factory=list)
    artifacts: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["observations"] = [item.to_dict() for item in self.observations]
        return payload


class StateStore:
    def __init__(
        self,
        state_file: str | Path,
        run_root: str | Path,
        *,
        hooks: list[StateHook] | None = None,
    ) -> None:
        self.state_file = Path(state_file)
        self.run_root = Path(run_root)
        self.hooks = hooks or []
        ensure_run_dirs(self.run_root)
        self.state_jsonl = self.run_root / "state.jsonl"
        self._ensure_markdown_header()

    def _ensure_markdown_header(self) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.state_file.exists():
            self.state_file.write_text(
                "# Agent State\n\nAppend-only run history for the GIS Agent Harness.\n",
                encoding="utf-8",
            )

    def append(self, snapshot: StateSnapshot) -> None:
        self._ensure_markdown_header()
        with self.state_jsonl.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(snapshot.to_dict(), ensure_ascii=False) + "\n")

        lines = [
            f"\n## {snapshot.timestamp} | {snapshot.run_id} | {snapshot.stage} | {snapshot.status}\n",
            f"- Iteration: {snapshot.iteration}\n",
            f"- Summary: {snapshot.summary}\n",
        ]
        if snapshot.observations:
            lines.append("- Observations:\n")
            for item in snapshot.observations:
                lines.append(
                    f"  - `{item.code}`: {item.message}"
                    + (f" Suggested fix: {item.suggested_fix}" if item.suggested_fix else "")
                    + "\n"
                )
        if snapshot.artifacts:
            lines.append(f"- Artifacts: `{json.dumps(snapshot.artifacts, ensure_ascii=False)}`\n")

        with self.state_file.open("a", encoding="utf-8") as handle:
            handle.writelines(lines)
        for hook in self.hooks:
            hook.handle_snapshot(snapshot)

    def _load_rows(self) -> list[dict[str, Any]]:
        if not self.state_jsonl.exists():
            return []
        return [json.loads(line) for line in self.state_jsonl.read_text(encoding="utf-8").splitlines() if line.strip()]

    def recent(
        self,
        limit: int = 5,
        *,
        run_id: str | None = None,
        status: str | None = None,
        stage: str | None = None,
        failed_only: bool = False,
    ) -> list[dict[str, Any]]:
        rows = self._load_rows()
        if run_id is not None:
            rows = [row for row in rows if row.get("run_id") == run_id]
        if status is not None:
            rows = [row for row in rows if row.get("status") == status]
        if stage is not None:
            rows = [row for row in rows if row.get("stage") == stage]
        if failed_only:
            rows = [row for row in rows if row.get("status") == "failed"]
        return rows[-limit:]

    def tail(self, limit: int = 10, *, run_id: str | None = None) -> list[dict[str, Any]]:
        return self.recent(limit=limit, run_id=run_id)

    def rows_for_run(self, run_id: str) -> list[dict[str, Any]]:
        return [row for row in self._load_rows() if row.get("run_id") == run_id]

    def render_recent(
        self,
        limit: int = 5,
        *,
        run_id: str | None = None,
        status: str | None = None,
        stage: str | None = None,
        failed_only: bool = False,
    ) -> str:
        snapshots = self.recent(limit=limit, run_id=run_id, status=status, stage=stage, failed_only=failed_only)
        if not snapshots:
            return self.state_file.read_text(encoding="utf-8")
        return json.dumps(snapshots, indent=2, ensure_ascii=False)

    def render_markdown(self) -> str:
        self._ensure_markdown_header()
        return self.state_file.read_text(encoding="utf-8")

    def latest_failed_run_summary(self) -> dict[str, Any] | None:
        rows = self._load_rows()
        failed_rows = [row for row in rows if row.get("status") == "failed"]
        if not failed_rows:
            return None

        stop_row = failed_rows[-1]
        run_id = stop_row.get("run_id")
        run_rows = [row for row in rows if row.get("run_id") == run_id]
        task_row = next((row for row in run_rows if row.get("stage") == "start"), None)
        failed_stage_row = next(
            (
                row
                for row in reversed(run_rows)
                if row.get("status") == "failed" and row.get("stage") in {"thought", "action", "stop"}
            ),
            stop_row,
        )
        task_payload = dict(((task_row or {}).get("artifacts") or {}).get("task") or {})
        observations = list(stop_row.get("observations") or [])

        return {
            "run_id": run_id,
            "status": stop_row.get("status"),
            "summary": stop_row.get("summary"),
            "failed_stage": failed_stage_row.get("stage"),
            "task": task_payload,
            "observations": observations,
            "artifacts": dict(stop_row.get("artifacts") or {}),
            "next_step_hint": observations[0].get("suggested_fix") if observations else None,
        }

    def latest_failed_run_files(self) -> dict[str, Any] | None:
        summary = self.latest_failed_run_summary()
        if summary is None:
            return None

        run_id = summary["run_id"]
        log_dir = self.run_root / "logs" / run_id
        failed_prefix = f"{run_id}-"
        failed_dir = self.run_root / "failed"

        log_json_files = sorted(str(path) for path in log_dir.glob("*.json")) if log_dir.exists() else []
        log_py_files = sorted(str(path) for path in log_dir.glob("*.py")) if log_dir.exists() else []
        failed_scripts = (
            sorted(str(path) for path in failed_dir.glob(f"{failed_prefix}*.py")) if failed_dir.exists() else []
        )

        return {
            **summary,
            "log_dir": str(log_dir),
            "log_json_files": log_json_files,
            "log_py_files": log_py_files,
            "failed_scripts": failed_scripts,
        }

    def latest_failed_run_replay(self) -> dict[str, Any] | None:
        summary = self.latest_failed_run_summary()
        if summary is None:
            return None

        task = dict(summary.get("task") or {})
        vector_path = task.get("vector_path")
        raster_path = task.get("raster_path")
        source_crs = task.get("source_crs")
        task_summary = task.get("task_summary")

        command_parts = [
            "python3",
            "-m",
            "gis_agent_harness.cli",
            "run-task",
        ]
        if task_summary:
            command_parts.extend(["--task-summary", task_summary])
        if vector_path:
            command_parts.extend(["--vector", vector_path])
        if raster_path:
            command_parts.extend(["--raster", raster_path])
        if source_crs:
            command_parts.extend(["--source-crs", source_crs])

        rerun_command = " ".join(json.dumps(part, ensure_ascii=False) for part in command_parts)

        return {
            **summary,
            "rerun_command": rerun_command,
            "suggested_fix": summary.get("next_step_hint"),
        }

    def latest_failed_task(self) -> dict[str, Any] | None:
        summary = self.latest_failed_run_summary()
        if summary is None:
            return None
        return dict(summary.get("task") or {})

    def run_summary(self, run_id: str) -> dict[str, Any] | None:
        rows = self._load_rows()
        run_rows = [row for row in rows if row.get("run_id") == run_id]
        if not run_rows:
            return None

        start_row = next((row for row in run_rows if row.get("stage") == "start"), None)
        terminal_row = next(
            (row for row in reversed(run_rows) if row.get("status") in {"failed", "succeeded"}),
            run_rows[-1],
        )
        observations = list(terminal_row.get("observations") or [])

        return {
            "run_id": run_id,
            "status": terminal_row.get("status"),
            "summary": terminal_row.get("summary"),
            "failed_stage": terminal_row.get("stage"),
            "task": dict(((start_row or {}).get("artifacts") or {}).get("task") or {}),
            "observations": observations,
            "artifacts": dict(terminal_row.get("artifacts") or {}),
            "next_step_hint": observations[0].get("suggested_fix") if observations else None,
        }

    def _hash_file(self, path: Path) -> str | None:
        if not path.exists() or not path.is_file():
            return None
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _dataset_hashes(self, path: Path) -> dict[str, Any]:
        if path.suffix.lower() == ".shp":
            parts = {
                str(part): self._hash_file(part)
                for part in sorted(path.parent.glob(f"{path.stem}.*"))
                if part.is_file()
            }
            return {"sha256": parts.get(str(path)), "parts": parts}
        return {"sha256": self._hash_file(path)}

    def _dataset_report(self, path_text: str, role: str) -> dict[str, Any]:
        path = Path(path_text)
        payload: dict[str, Any] = {
            "role": role,
            "path": path_text,
            "exists": path.exists(),
            "hashes": self._dataset_hashes(path) if path.exists() else {},
        }
        suffix = path.suffix.lower()
        if not path.exists():
            return payload

        try:
            if suffix in VECTOR_SUFFIXES:
                from .spatial_tools import inspect_vector

                info = inspect_vector(path, sample_size=0)
                schema = dict(info.schema or {})
                payload.update(
                    {
                        "kind": "vector",
                        "driver": info.driver,
                        "crs": info.crs,
                        "bounds": info.bounds,
                        "geometry_type": schema.get("geometry"),
                        "feature_count": info.feature_count,
                        "schema": dict(schema.get("properties") or {}),
                    }
                )
            elif suffix in RASTER_SUFFIXES:
                from .spatial_tools import inspect_raster

                info = inspect_raster(path)
                payload.update(
                    {
                        "kind": "raster",
                        "driver": info.driver,
                        "crs": info.crs,
                        "bounds": info.bounds,
                        "width": info.width,
                        "height": info.height,
                        "band_count": info.count,
                        "dtypes": info.dtypes,
                        "nodatavals": info.nodatavals,
                    }
                )
            else:
                payload["kind"] = "file"
        except Exception as exc:
            payload["inspection_error"] = str(exc)
        return payload

    def adoption_report(self, run_id: str) -> dict[str, Any] | None:
        run_rows = self.rows_for_run(run_id)
        if not run_rows:
            return None

        start_row = next((row for row in run_rows if row.get("stage") == "start"), None)
        terminal_row = next(
            (row for row in reversed(run_rows) if row.get("status") in {"failed", "succeeded"}),
            run_rows[-1],
        )
        task = dict(((start_row or {}).get("artifacts") or {}).get("task") or {})

        dataset_roles: list[tuple[str, str]] = []
        if task.get("vector_path"):
            dataset_roles.append(("input_vector", str(task["vector_path"])))
        if task.get("raster_path"):
            dataset_roles.append(("input_raster", str(task["raster_path"])))
        terminal_artifacts = dict(terminal_row.get("artifacts") or {})
        final_path = terminal_artifacts.get("final_vector_path") or terminal_artifacts.get("current_vector_path")
        if final_path and final_path != task.get("vector_path"):
            dataset_roles.append(("final_vector", str(final_path)))

        seen_dataset_keys: set[tuple[str, str]] = set()
        source_data: list[dict[str, Any]] = []
        for role, path_text in dataset_roles:
            key = (role, path_text)
            if key in seen_dataset_keys:
                continue
            seen_dataset_keys.add(key)
            source_data.append(self._dataset_report(path_text, role))

        actions: list[dict[str, Any]] = []
        qgis_payloads: list[dict[str, Any]] = []
        crs_transformations: list[dict[str, Any]] = []
        for row in run_rows:
            artifacts = dict(row.get("artifacts") or {})
            if artifacts.get("action"):
                actions.append(
                    {
                        "iteration": row.get("iteration"),
                        "stage": row.get("stage"),
                        "action": artifacts.get("action"),
                        "model_used": artifacts.get("model_used"),
                        "fallback_used": artifacts.get("fallback_used"),
                        "output_vector_path": artifacts.get("output_vector_path"),
                    }
                )
            if artifacts.get("qgis_process"):
                qgis_payloads.append(
                    {
                        "iteration": row.get("iteration"),
                        "stage": row.get("stage"),
                        "request": artifacts["qgis_process"],
                    }
                )
            for observation in row.get("observations") or []:
                if observation.get("code") == "crs_mismatch":
                    details = dict(observation.get("details") or {})
                    transformation = {
                        "iteration": row.get("iteration"),
                        "source_crs": details.get("vector_crs"),
                        "target_crs": details.get("raster_crs"),
                        "reason": observation.get("message"),
                    }
                    if transformation not in crs_transformations:
                        crs_transformations.append(transformation)

        terminal_observations = list(terminal_row.get("observations") or [])
        omitted_steps = []
        if terminal_row.get("status") != "succeeded":
            omitted_steps = [
                {
                    "code": item.get("code"),
                    "reason": item.get("message"),
                    "suggested_fix": item.get("suggested_fix"),
                }
                for item in terminal_observations
            ]

        return {
            "run_id": run_id,
            "status": terminal_row.get("status"),
            "summary": terminal_row.get("summary"),
            "task": task,
            "source_data": source_data,
            "crs_transformations": crs_transformations,
            "actions": actions,
            "qgis_process_payloads": qgis_payloads,
            "omitted_steps": omitted_steps,
            "snapshot_count": len(run_rows),
        }

    def task_for_run(self, run_id: str) -> dict[str, Any] | None:
        summary = self.run_summary(run_id)
        if summary is None:
            return None
        return dict(summary.get("task") or {})

    def list_runs(self, *, failed_only: bool = False, limit: int = 20) -> list[dict[str, Any]]:
        return self.query_runs(limit=limit, failed_only=failed_only)

    def query_runs(
        self,
        *,
        limit: int = 20,
        failed_only: bool = False,
        status: str | None = None,
        stage: str | None = None,
        contains: str | None = None,
    ) -> list[dict[str, Any]]:
        rows = self._load_rows()
        if not rows:
            return []

        ordered_run_ids: list[str] = []
        seen: set[str] = set()
        for row in reversed(rows):
            run_id = row["run_id"]
            if run_id in seen:
                continue
            seen.add(run_id)
            ordered_run_ids.append(run_id)

        payload: list[dict[str, Any]] = []
        for run_id in ordered_run_ids:
            summary = self.run_summary(run_id)
            if summary is None:
                continue
            if failed_only and summary.get("status") != "failed":
                continue
            if status is not None and summary.get("status") != status:
                continue
            if stage is not None and summary.get("failed_stage") != stage:
                continue
            if contains is not None:
                text = " ".join(
                    filter(
                        None,
                        [
                            str(summary.get("run_id", "")),
                            str(summary.get("summary", "")),
                            str(summary.get("task", {}).get("task_summary", "")),
                        ],
                    )
                ).lower()
                if contains.lower() not in text:
                    continue
            payload.append(summary)
            if len(payload) >= limit:
                break
        return payload
