from __future__ import annotations

from typing import Any, TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Static

from .widgets import JsonPanel, LogPanel, RiskPreviewPanel

if TYPE_CHECKING:
    from .app import GISAgentApp


class HomeScreen(Screen[None]):
    def compose(self) -> ComposeResult:
        app = self.app
        yield Header(show_clock=False)
        yield Static("GIS Agent Harness TUI", id="home-title")
        with Vertical():
            yield Static("Templates", id="templates-title")
            for template in app.registry.list():
                yield Button(template.title, id=f"template-{template.template_id}")
        with Horizontal():
            yield Button("Recovery", id="home-recovery")
            yield Button("Config", id="home-config")
            yield Button("Refresh", id="home-refresh")
        yield JsonPanel("Latest Failed Run", app.get_latest_failed_summary(), id="home-recovery-panel")
        yield JsonPanel("Config Doctor", app.get_config_doctor(), id="home-config-panel")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id or ""
        app = self.app
        if button_id.startswith("template-"):
            app.open_goal(button_id.removeprefix("template-"))
        elif button_id == "home-recovery":
            app.open_recovery()
        elif button_id == "home-config":
            app.open_config()
        elif button_id == "home-refresh":
            self.query_one("#home-recovery-panel", JsonPanel).update_payload(app.get_latest_failed_summary())
            self.query_one("#home-config-panel", JsonPanel).update_payload(app.get_config_doctor())


class GoalScreen(Screen[None]):
    def __init__(self, template_id: str) -> None:
        super().__init__()
        self.template_id = template_id

    def compose(self) -> ComposeResult:
        app = self.app
        template = app.registry.get(self.template_id)
        yield Header(show_clock=False)
        yield Static(f"{template.title}\n{template.description}", id="goal-description")
        for field in template.fields:
            yield Input(value=field.default or "", placeholder=field.label, id=f"input-{field.name}")
        yield Input(value="", placeholder="Optional task summary override", id="input-task-summary")
        yield Input(value="", placeholder="Optional max iterations override", id="input-max-iterations")
        with Horizontal():
            yield Button("Dry Run", id="goal-preview")
            yield Button("Run", id="goal-run")
            yield Button("Recovery", id="goal-recovery")
            yield Button("Home", id="goal-home")
        yield JsonPanel("Goal Preview", None, id="goal-preview-panel")
        yield Footer()

    def _collect_inputs(self) -> dict[str, Any]:
        app = self.app
        template = app.registry.get(self.template_id)
        payload: dict[str, Any] = {}
        for field in template.fields:
            payload[field.name] = self.query_one(f"#input-{field.name}", Input).value.strip()
        return payload

    def on_button_pressed(self, event: Button.Pressed) -> None:
        app = self.app
        if event.button.id == "goal-home":
            app.pop_screen()
            return
        if event.button.id == "goal-recovery":
            app.open_recovery()
            return
        max_iterations_input = self.query_one("#input-max-iterations", Input).value.strip()
        max_iterations = int(max_iterations_input) if max_iterations_input else None
        task_summary = self.query_one("#input-task-summary", Input).value.strip() or None
        if event.button.id == "goal-preview":
            preview = app.preview_goal(
                self.template_id,
                self._collect_inputs(),
                max_iterations=max_iterations,
                task_summary=task_summary,
            )
            self.query_one("#goal-preview-panel", JsonPanel).update_payload(preview)
        elif event.button.id == "goal-run":
            spec = app.build_goal_spec(
                self.template_id,
                self._collect_inputs(),
                max_iterations=max_iterations,
                task_summary=task_summary,
            )
            preview = app.preview_goal(
                self.template_id,
                self._collect_inputs(),
                max_iterations=max_iterations,
                task_summary=task_summary,
            )
            app.push_screen(RunScreen(spec.to_dict(), preview))


class RunScreen(Screen[None]):
    def __init__(self, spec: dict[str, Any], preview: dict[str, Any]) -> None:
        super().__init__()
        self.spec = spec
        self.preview = preview
        self.snapshots: list[dict[str, Any]] = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield JsonPanel("Goal Preview", self.preview, id="run-preview-panel")
        yield JsonPanel("State Tail", [], id="run-state-panel")
        yield RiskPreviewPanel("Risk Preview", None, id="run-risk-panel")
        yield LogPanel("Run Result", "Starting worker...", id="run-result-panel")
        with Horizontal():
            yield Button("Recovery", id="run-recovery")
            yield Button("Home", id="run-home")
        yield Footer()

    def on_mount(self) -> None:
        app = self.app
        app.start_goal_run(self.spec, self)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        app = self.app
        if event.button.id == "run-home":
            app.pop_screen()
        elif event.button.id == "run-recovery":
            app.open_recovery()

    def record_snapshot(self, payload: dict[str, Any]) -> None:
        self.snapshots.append(payload)
        self.query_one("#run-state-panel", JsonPanel).update_payload(self.snapshots[-8:])
        artifacts = payload.get("artifacts") or {}
        if "risk_preview" in artifacts:
            self.query_one("#run-risk-panel", RiskPreviewPanel).update_payload(artifacts["risk_preview"])

    def show_result(self, payload: dict[str, Any]) -> None:
        self.query_one("#run-result-panel", LogPanel).set_text(str(payload))


class RecoveryScreen(Screen[None]):
    def compose(self) -> ComposeResult:
        app = self.app
        yield Header(show_clock=False)
        yield Input(value="", placeholder="Optional source CRS override for replay", id="recovery-source-crs")
        with Horizontal():
            yield Button("Refresh", id="recovery-refresh")
            yield Button("Dry Run Replay", id="recovery-dry-run")
            yield Button("Replay", id="recovery-replay")
            yield Button("Home", id="recovery-home")
        yield JsonPanel("Failed Summary", app.get_latest_failed_summary(), id="recovery-summary")
        yield JsonPanel("Failure Files", app.get_failure_files(), id="recovery-files")
        yield JsonPanel("Replay", app.get_replay_payload(), id="recovery-replay-panel")
        yield LogPanel("Replay Result", "", id="recovery-result")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        app = self.app
        source_crs = self.query_one("#recovery-source-crs", Input).value.strip() or None
        if event.button.id == "recovery-home":
            app.pop_screen()
        elif event.button.id == "recovery-refresh":
            self.query_one("#recovery-summary", JsonPanel).update_payload(app.get_latest_failed_summary())
            self.query_one("#recovery-files", JsonPanel).update_payload(app.get_failure_files())
            self.query_one("#recovery-replay-panel", JsonPanel).update_payload(app.get_replay_payload())
        elif event.button.id == "recovery-dry-run":
            self.query_one("#recovery-result", LogPanel).set_text(str(app.build_replay_preview(source_crs=source_crs)))
        elif event.button.id == "recovery-replay":
            app.start_replay(source_crs=source_crs, screen=self)

    def show_result(self, payload: dict[str, Any]) -> None:
        self.query_one("#recovery-result", LogPanel).set_text(str(payload))


class ConfigScreen(Screen[None]):
    def compose(self) -> ComposeResult:
        app = self.app
        yield Header(show_clock=False)
        with Horizontal():
            yield Button("Refresh", id="config-refresh")
            yield Button("Home", id="config-home")
        yield JsonPanel("Config Doctor", app.get_config_doctor(), id="config-panel")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        app = self.app
        if event.button.id == "config-home":
            app.pop_screen()
        elif event.button.id == "config-refresh":
            self.query_one("#config-panel", JsonPanel).update_payload(app.get_config_doctor())
