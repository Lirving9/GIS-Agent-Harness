from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, TYPE_CHECKING

from .errors import Observation
from .guardrails import validate_python_script
from .llm_router import AgentDecision

if TYPE_CHECKING:
    from .agent_loop import AgentTask

WEIGHTED_SCORE_THRESHOLD = 7.5

OBSERVATION_ACTION_MAP = {
    "missing_crs": {"set_crs"},
    "crs_mismatch": {"to_crs"},
    "invalid_geometry": {"make_valid"},
}


@dataclass(slots=True)
class ReviewMetric:
    name: str
    score: float
    weight: float
    floor: float
    passed: bool
    details: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class DecisionReview:
    allowed: bool
    route: str
    summary: str
    weighted_score: float
    metrics: list[ReviewMetric] = field(default_factory=list)
    observations: list[Observation] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "route": self.route,
            "summary": self.summary,
            "weighted_score": self.weighted_score,
            "metrics": [metric.to_dict() for metric in self.metrics],
            "observations": [item.to_dict() for item in self.observations],
        }


def review_decision(
    *,
    task: AgentTask,
    observations: list[Observation],
    decision: AgentDecision,
    artifact_dir: str | Path,
    review_attempt: int,
) -> DecisionReview:
    artifact_root = Path(artifact_dir).resolve()
    expected_actions = _expected_actions(observations)
    review_observations: list[Observation] = []

    expected_action_ok = not expected_actions or decision.action in expected_actions
    if not expected_action_ok:
        review_observations.append(
            Observation(
                code="review_action_mismatch",
                message=f"Reviewer expected one of {sorted(expected_actions)} but received action {decision.action}.",
                suggested_fix="Regenerate the repair plan with an action that matches the current observations.",
                details={"expected_actions": sorted(expected_actions), "actual_action": decision.action},
            )
        )

    allowed_action_ok = not task.allowed_actions or decision.action in task.allowed_actions
    if not allowed_action_ok:
        review_observations.append(
            Observation(
                code="review_action_not_allowed",
                message=f"Action {decision.action} is outside the allowed plan actions {task.allowed_actions}.",
                suggested_fix="Regenerate the repair plan using one of the allowed actions from the execution plan.",
                details={"allowed_actions": list(task.allowed_actions), "actual_action": decision.action},
            )
        )

    output_path_ok = _output_path_within_artifacts(decision.output_vector_path, artifact_root)
    if not output_path_ok:
        review_observations.append(
            Observation(
                code="review_output_path_invalid",
                message="Repair output path must be written under the run artifact directory.",
                suggested_fix="Write repaired outputs under the artifact_dir supplied by the harness.",
                details={
                    "artifact_dir": str(artifact_root),
                    "output_vector_path": decision.output_vector_path,
                },
            )
        )

    guardrail_report = validate_python_script(decision.script)
    if not guardrail_report.allowed:
        for item in guardrail_report.observations:
            review_observations.append(
                Observation(
                    code="review_script_policy",
                    message=item.message,
                    suggested_fix=item.suggested_fix,
                    details=item.to_dict(),
                )
            )

    clarity_ok = bool(decision.summary.strip()) and bool(decision.script.strip())

    metrics = [
        _metric(
            name="methodological_rigor",
            score=9.0 if expected_action_ok else 3.0,
            weight=30.0,
            floor=7.0,
            details="Action matches the observation-specific repair expectation.",
        ),
        _metric(
            name="spatial_data_provenance",
            score=9.0 if output_path_ok else 2.0,
            weight=25.0,
            floor=6.5,
            details="Output path stays inside the run artifact directory.",
        ),
        _metric(
            name="action_alignment",
            score=9.0 if allowed_action_ok else 2.0,
            weight=20.0,
            floor=6.5,
            details="Action respects the execution-plan allowlist when one is present.",
        ),
        _metric(
            name="execution_safety",
            score=8.5 if guardrail_report.allowed else 0.0,
            weight=15.0,
            floor=6.0,
            details="Script passes the AST safety and import policy checks.",
        ),
        _metric(
            name="analytical_clarity",
            score=8.0 if clarity_ok else 4.0,
            weight=10.0,
            floor=6.0,
            details="Summary and script are both present for traceable execution.",
        ),
    ]

    weighted_score = round(sum(metric.score * metric.weight for metric in metrics) / 100.0, 2)
    floors_ok = all(metric.passed for metric in metrics)
    allowed = weighted_score >= WEIGHTED_SCORE_THRESHOLD and floors_ok and not review_observations
    route = "approve" if allowed else ("escalate" if review_attempt >= 2 else "revise")
    summary = (
        f"Reviewer approved the repair plan with weighted score {weighted_score:.2f}."
        if allowed
        else f"Reviewer rejected the repair plan with weighted score {weighted_score:.2f}."
    )

    return DecisionReview(
        allowed=allowed,
        route=route,
        summary=summary,
        weighted_score=weighted_score,
        metrics=metrics,
        observations=review_observations,
    )


def _metric(*, name: str, score: float, weight: float, floor: float, details: str) -> ReviewMetric:
    return ReviewMetric(
        name=name,
        score=score,
        weight=weight,
        floor=floor,
        passed=score >= floor,
        details=details,
    )


def _expected_actions(observations: list[Observation]) -> set[str]:
    expected: set[str] = set()
    for item in observations:
        expected.update(OBSERVATION_ACTION_MAP.get(item.code, set()))
    return expected


def _output_path_within_artifacts(output_vector_path: str | None, artifact_dir: Path) -> bool:
    if not output_vector_path:
        return False
    try:
        Path(output_vector_path).resolve().relative_to(artifact_dir)
    except ValueError:
        return False
    return True
