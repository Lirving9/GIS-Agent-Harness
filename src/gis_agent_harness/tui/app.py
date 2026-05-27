from __future__ import annotations

from pathlib import Path
from typing import Any

from textual.app import App
try:
    from textual.worker import work
except ImportError:  # textual>=0.89 exposes the decorator via a private module
    from textual._work_decorator import work

from ..agent_loop import AgentTask
from ..auth_config import doctor_config
from ..config import HarnessConfig
from ..goal_runner import GoalRunner, GoalSpec, run_agent_task
from ..state_hooks import CallbackStateHook
from ..state_store import StateStore
from ..task_templates import TemplateRegistry
from .screens import ConfigScreen, GoalScreen, HomeScreen, RecoveryScreen


class GISAgentApp(App[None]):
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("h", "show_home", "Home"),
        ("f", "show_recovery", "Recovery"),
        ("c", "show_config", "Config"),
    ]

    def __init__(
        self,
        *,
        config: HarnessConfig | None = None,
        registry: TemplateRegistry | None = None,
    ) -> None:
        super().__init__()
        self.config = config or HarnessConfig.from_env()
        self.registry = registry or TemplateRegistry()
        self.goal_runner = GoalRunner(self.config, registry=self.registry)

    def on_mount(self) -> None:
        self.push_screen(HomeScreen())

    def action_show_home(self) -> None:
        self.push_screen(HomeScreen())

    def action_show_recovery(self) -> None:
        self.open_recovery()

    def action_show_config(self) -> None:
        self.open_config()

    def _store(self) -> StateStore:
        return StateStore(self.config.state_file, self.config.run_root)

    def get_latest_failed_summary(self) -> dict[str, Any] | None:
        return self._store().latest_failed_run_summary()

    def get_failure_files(self) -> dict[str, Any] | None:
        return self._store().latest_failed_run_files()

    def get_replay_payload(self) -> dict[str, Any] | None:
        return self._store().latest_failed_run_replay()

    def get_config_doctor(self) -> dict[str, Any]:
        return doctor_config(self.config.copy())

    def open_goal(self, template_id: str) -> None:
        self.push_screen(GoalScreen(template_id))

    def open_recovery(self) -> None:
        self.push_screen(RecoveryScreen())

    def open_config(self) -> None:
        self.push_screen(ConfigScreen())

    def build_goal_spec(
        self,
        template_id: str,
        values: dict[str, Any],
        *,
        max_iterations: int | None = None,
        task_summary: str | None = None,
    ) -> GoalSpec:
        return GoalSpec(
            template_id=template_id,
            inputs=values,
            max_iterations=max_iterations,
            task_summary=task_summary,
        )

    def preview_goal(
        self,
        template_id: str,
        values: dict[str, Any],
        *,
        max_iterations: int | None = None,
        task_summary: str | None = None,
    ) -> dict[str, Any]:
        spec = self.build_goal_spec(
            template_id,
            values,
            max_iterations=max_iterations,
            task_summary=task_summary,
        )
        return self.goal_runner.preview(spec)

    def _goal_spec_from_dict(self, payload: dict[str, Any]) -> GoalSpec:
        return GoalSpec(
            template_id=payload["template_id"],
            inputs=dict(payload.get("inputs") or {}),
            task_summary=payload.get("task_summary"),
            max_iterations=payload.get("max_iterations"),
            use_mock=payload.get("use_mock"),
            run_root=Path(payload["run_root"]) if payload.get("run_root") else None,
            state_file=Path(payload["state_file"]) if payload.get("state_file") else None,
        )

    def _publish_snapshot(self, payload: dict[str, Any]) -> None:
        screen = self.screen
        handler = getattr(screen, "record_snapshot", None)
        if callable(handler):
            handler(payload)

    def _publish_result(self, payload: dict[str, Any]) -> None:
        screen = self.screen
        handler = getattr(screen, "show_result", None)
        if callable(handler):
            handler(payload)

    def start_goal_run(self, spec: dict[str, Any], _screen: Any) -> None:
        self.run_goal_worker(spec)

    @work(thread=True)
    def run_goal_worker(self, spec_payload: dict[str, Any]) -> None:
        spec = self._goal_spec_from_dict(spec_payload)
        hook = CallbackStateHook(lambda payload: self.call_from_thread(self._publish_snapshot, payload))
        result = self.goal_runner.run(spec, extra_hooks=[hook])
        self.call_from_thread(self._publish_result, result.to_dict())

    def _build_replay_task(self, *, source_crs: str | None = None) -> AgentTask:
        store = self._store()
        task_payload = store.latest_failed_task()
        if task_payload is None:
            raise RuntimeError("No failed run is available for replay.")
        return AgentTask(
            task_summary=task_payload["task_summary"],
            vector_path=task_payload["vector_path"],
            raster_path=task_payload.get("raster_path"),
            source_crs=source_crs if source_crs is not None else task_payload.get("source_crs"),
            max_iterations=task_payload.get("max_iterations", self.config.max_iterations),
            template_id=task_payload.get("template_id"),
            template_title=task_payload.get("template_title"),
        )

    def build_replay_preview(self, *, source_crs: str | None = None) -> dict[str, Any]:
        task = self._build_replay_task(source_crs=source_crs)
        replay = self.get_replay_payload() or {}
        return {
            "task": task.to_dict(),
            "replay": replay,
        }

    def start_replay(self, *, source_crs: str | None = None, screen: Any) -> None:
        self.run_replay_worker(source_crs)

    @work(thread=True)
    def run_replay_worker(self, source_crs: str | None) -> None:
        task = self._build_replay_task(source_crs=source_crs)
        hook = CallbackStateHook(lambda payload: self.call_from_thread(self._publish_snapshot, payload))
        result = run_agent_task(task, self.config.copy(), extra_hooks=[hook])
        self.call_from_thread(self._publish_result, result.to_dict())
