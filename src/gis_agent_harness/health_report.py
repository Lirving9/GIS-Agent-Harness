from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(slots=True)
class HealthCheck:
    check_id: str
    category: str
    title: str
    status: str
    severity: str
    evidence: str
    recommendation: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(slots=True)
class HealthReport:
    root: Path
    checks: list[HealthCheck]
    category_filter: str | None = None

    @property
    def summary(self) -> dict[str, object]:
        by_status = Counter(check.status for check in self.checks)
        by_category = Counter(check.category for check in self.checks)
        by_severity = Counter(check.severity for check in self.checks)
        return {
            "total": len(self.checks),
            "by_status": dict(sorted(by_status.items())),
            "by_category": dict(sorted(by_category.items())),
            "by_severity": dict(sorted(by_severity.items())),
            "passed": by_status.get("passed", 0),
            "warnings": by_status.get("warning", 0),
            "failed": by_status.get("failed", 0),
        }

    def to_dict(self) -> dict[str, object]:
        return {
            "root": str(self.root),
            "category_filter": self.category_filter,
            "check_count": len(self.checks),
            "summary": self.summary,
            "checks": [check.to_dict() for check in self.checks],
        }


@dataclass(frozen=True, slots=True)
class _CheckSpec:
    check_id: str
    category: str
    title: str
    severity: str
    path: str | None
    tokens: tuple[str, ...]
    recommendation: str


CHECK_SPECS: tuple[_CheckSpec, ...] = (
    _CheckSpec(
        "agents_install_command",
        "operations",
        "AGENTS install command",
        "medium",
        "AGENTS.md",
        ("python3 -m pip install -r requirements.txt",),
        "Keep the shared setup command explicit for future agent runs.",
    ),
    _CheckSpec(
        "agents_fixture_generation",
        "operations",
        "AGENTS fixture generation",
        "medium",
        "AGENTS.md",
        ("scripts/generate_sample_data.py", "tests/fixtures/"),
        "Document the fixture generation path so local checks remain reproducible.",
    ),
    _CheckSpec(
        "agents_isolated_fixture_guidance",
        "operations",
        "AGENTS isolated fixture guidance",
        "medium",
        "AGENTS.md",
        ("--output-dir .local-fixtures",),
        "Prefer isolated fixture roots for ad hoc commands.",
    ),
    _CheckSpec(
        "agents_pytest_command",
        "testing",
        "AGENTS full pytest command",
        "medium",
        "AGENTS.md",
        ("pytest -q",),
        "Keep the full offline suite command visible.",
    ),
    _CheckSpec(
        "agents_tui_smoke_command",
        "testing",
        "AGENTS TUI smoke command",
        "medium",
        "AGENTS.md",
        ("pytest -q tests/test_tui_smoke.py",),
        "Retain an explicit headless TUI smoke test path.",
    ),
    _CheckSpec(
        "agents_template_cli_path",
        "cli",
        "AGENTS template CLI path",
        "medium",
        "AGENTS.md",
        ("templates list", "goal run", "config doctor"),
        "Document the template-driven path as the preferred workflow.",
    ),
    _CheckSpec(
        "agents_tui_local_only",
        "cli",
        "AGENTS TUI local-only constraint",
        "high",
        "AGENTS.md",
        ("python3 -m gis_agent_harness.cli tui", "local-only"),
        "Keep the TUI scoped to local execution only.",
    ),
    _CheckSpec(
        "agents_demo_scripts",
        "testing",
        "AGENTS smoke demo commands",
        "medium",
        "AGENTS.md",
        ("demo_task.py", "demo_recovery.py", "demo_readme_workflow.py"),
        "Preserve the offline smoke coverage commands.",
    ),
    _CheckSpec(
        "acceptance_audit_script",
        "testing",
        "AGENTS acceptance command",
        "high",
        "AGENTS.md",
        ("scripts/verify_acceptance.py",),
        "Use the acceptance script before final delivery.",
    ),
    _CheckSpec(
        "agents_failure_demo",
        "testing",
        "AGENTS failure demo command",
        "medium",
        "AGENTS.md",
        ("scripts/demo_failures.py",),
        "Keep guardrail and timeout demos available.",
    ),
    _CheckSpec(
        "agents_clean_state",
        "operations",
        "AGENTS local cleanup command",
        "medium",
        "AGENTS.md",
        ("scripts/clean_local_state.py",),
        "Clean local runtime state before fresh checkpoints.",
    ),
    _CheckSpec(
        "fixture_mutation_guard",
        "testing",
        "fixture mutation guard",
        "high",
        "AGENTS.md",
        ("Keep tests and demos from mutating", "tests/fixtures/"),
        "Keep demos and tests writing into isolated fixture roots.",
    ),
    _CheckSpec(
        "cli_help_fast",
        "cli",
        "CLI help fast import guard",
        "high",
        "AGENTS.md",
        ("avoid importing GeoPandas, Fiona, or Rasterio in module scope for `cli.py`",),
        "Keep heavyweight GIS imports inside command bodies.",
    ),
    _CheckSpec(
        "no_external_service_mvp",
        "architecture",
        "MVP external service guard",
        "high",
        "AGENTS.md",
        ("Do not add external services", "databases", "web servers"),
        "Keep the MVP local-first and file-based.",
    ),
    _CheckSpec(
        "state_jsonl_append_only",
        "operations",
        "append-only state logging",
        "high",
        "AGENTS.md",
        ("Preserve append-only state logging", "AGENT_STATE.md", ".runs/state.jsonl"),
        "Continue writing state as append-only markdown and JSONL.",
    ),
    _CheckSpec(
        "readme_scope_local_files",
        "documentation",
        "README local-files scope",
        "high",
        "README.md",
        ("local files only",),
        "Keep user-facing scope explicit.",
    ),
    _CheckSpec(
        "readme_no_web_service",
        "documentation",
        "README no web service scope",
        "high",
        "README.md",
        ("no web service",),
        "Avoid adding web runtime assumptions to the MVP.",
    ),
    _CheckSpec(
        "readme_no_database",
        "documentation",
        "README no database scope",
        "high",
        "README.md",
        ("no database",),
        "Avoid adding persistent database requirements.",
    ),
    _CheckSpec(
        "readme_mock_default",
        "documentation",
        "README mock routing default",
        "high",
        "README.md",
        ("mock routing by default",),
        "Keep live providers optional and disabled by default.",
    ),
    _CheckSpec(
        "readme_python_baseline",
        "packaging",
        "README Python baseline",
        "medium",
        "README.md",
        ("Python 3.11", ">=3.11,<3.13"),
        "Keep README and package metadata aligned on Python support.",
    ),
    _CheckSpec(
        "readme_install_section",
        "documentation",
        "README install section",
        "medium",
        "README.md",
        ("python3 -m pip install -r requirements.txt",),
        "Document the supported local install command.",
    ),
    _CheckSpec(
        "readme_generate_sample_data",
        "documentation",
        "README sample data commands",
        "medium",
        "README.md",
        ("scripts/generate_sample_data.py", "--output-dir .local-fixtures"),
        "Keep fixture generation examples copyable.",
    ),
    _CheckSpec(
        "readme_template_commands",
        "documentation",
        "README goal template commands",
        "medium",
        "README.md",
        ("templates list", "goal run", "--dry-run"),
        "Keep template commands discoverable.",
    ),
    _CheckSpec(
        "readme_core_cli_catalog",
        "documentation",
        "README command catalog",
        "medium",
        "README.md",
        ("inspect-vector", "inspect-raster", "spatial-map", "run-task"),
        "Keep the core command catalog in sync with the CLI.",
    ),
    _CheckSpec(
        "readme_qgis_confirmation",
        "security",
        "README qgis_process approval guard",
        "high",
        "README.md",
        ("--confirm", "GIS_AGENT_HARNESS_QGIS_REQUIRE_CONFIRM=false"),
        "Keep live qgis_process execution gated by explicit approval.",
    ),
    _CheckSpec(
        "readme_mcp_manifest",
        "architecture",
        "README MCP progressive manifest",
        "medium",
        "README.md",
        ("mcp-tools", "progressive-disclosure"),
        "Document MCP-style progressive tool exposure.",
    ),
    _CheckSpec(
        "readme_visual_review",
        "features",
        "README visual review features",
        "medium",
        "README.md",
        ("capture-artifact", "judge-map"),
        "Keep deterministic visual artifact review documented.",
    ),
    _CheckSpec(
        "readme_advanced_manifests",
        "features",
        "README advanced dry-run manifests",
        "medium",
        "README.md",
        ("stac-plan", "faas-manifest", "qgis-plugin-manifest", "cog-viewer"),
        "Keep dry-run manifest commands visible.",
    ),
    _CheckSpec(
        "readme_failure_compaction",
        "features",
        "README failure compaction",
        "medium",
        "README.md",
        ("compact-failures",),
        "Document repeated-failure compaction for replanning.",
    ),
    _CheckSpec(
        "readme_acceptance_command",
        "testing",
        "README acceptance command",
        "high",
        "README.md",
        ("scripts/verify_acceptance.py",),
        "Keep the acceptance audit in the README test workflow.",
    ),
    _CheckSpec(
        "readme_health_report_command",
        "documentation",
        "README health report command",
        "medium",
        "README.md",
        ("health-report",),
        "Document the project health report command.",
    ),
    _CheckSpec(
        "readme_health_report_strict_command",
        "documentation",
        "README health report strict command",
        "medium",
        "README.md",
        ("health-report", "--fail-on-failed", "--category testing"),
        "Document the nonzero exit gate for failed project health checks.",
    ),
    _CheckSpec(
        "pyproject_python_bounds",
        "packaging",
        "package Python bounds",
        "medium",
        "pyproject.toml",
        ('requires-python = ">=3.11,<3.13"',),
        "Keep package metadata constrained to supported Python versions.",
    ),
    _CheckSpec(
        "pyproject_click_dependency",
        "packaging",
        "Click dependency bound",
        "medium",
        "pyproject.toml",
        ('"click>=8.1,<9"',),
        "Keep CLI dependency bounded.",
    ),
    _CheckSpec(
        "pyproject_textual_dependency",
        "packaging",
        "Textual dependency bound",
        "medium",
        "pyproject.toml",
        ('"textual>=0.70,<1"',),
        "Keep the TUI dependency bounded.",
    ),
    _CheckSpec(
        "pyproject_geopandas_dependency",
        "packaging",
        "GeoPandas dependency bound",
        "medium",
        "pyproject.toml",
        ('"geopandas>=1.0,<2"',),
        "Keep GIS dependency versions explicit.",
    ),
    _CheckSpec(
        "pyproject_rasterio_dependency",
        "packaging",
        "Rasterio dependency bound",
        "medium",
        "pyproject.toml",
        ('"rasterio>=1.4,<2"',),
        "Keep raster dependency versions explicit.",
    ),
    _CheckSpec(
        "pyproject_dev_pytest",
        "testing",
        "pytest dev dependency",
        "medium",
        "pyproject.toml",
        ('"pytest>=8.2,<9"',),
        "Keep pytest available through the dev extra.",
    ),
    _CheckSpec(
        "pyproject_script_entrypoint",
        "packaging",
        "console script entry point",
        "medium",
        "pyproject.toml",
        ('gis-agent-harness = "gis_agent_harness.cli:main"',),
        "Keep the installed CLI entry point wired to Click.",
    ),
    _CheckSpec(
        "pyproject_pytest_testpaths",
        "testing",
        "pytest testpaths",
        "medium",
        "pyproject.toml",
        ('testpaths = ["tests"]',),
        "Keep pytest discovery constrained to the tests directory.",
    ),
    _CheckSpec(
        "requirements_editable_dev",
        "packaging",
        "editable dev requirements",
        "medium",
        "requirements.txt",
        ("-e .[dev]",),
        "Keep local installs simple for agents and CI.",
    ),
    _CheckSpec(
        "ci_offline_pytest",
        "testing",
        "CI offline pytest",
        "high",
        ".github/workflows/ci.yml",
        ("Run offline pytest suite", "pytest -q"),
        "Keep CI running the full offline suite.",
    ),
    _CheckSpec(
        "ci_tui_smoke",
        "testing",
        "CI TUI smoke",
        "medium",
        ".github/workflows/ci.yml",
        ("Run explicit TUI smoke", "tests/test_tui_smoke.py"),
        "Keep headless TUI validation in CI.",
    ),
    _CheckSpec(
        "ci_demo_scripts",
        "testing",
        "CI demo scripts",
        "high",
        ".github/workflows/ci.yml",
        ("demo_task.py", "demo_recovery.py", "demo_readme_workflow.py", "demo_failures.py"),
        "Keep smoke demos wired into CI.",
    ),
    _CheckSpec(
        "ci_acceptance_audit",
        "testing",
        "CI acceptance audit",
        "high",
        ".github/workflows/ci.yml",
        ("Run acceptance audit", "verify_acceptance.py"),
        "Run the JSON acceptance audit in CI.",
    ),
    _CheckSpec(
        "ci_package_build",
        "packaging",
        "CI package build",
        "medium",
        ".github/workflows/ci.yml",
        ("Build sdist and wheel", "python -m build"),
        "Keep packaging checked after smoke and acceptance.",
    ),
    _CheckSpec(
        "docker_local_cli_entrypoint",
        "packaging",
        "Docker CLI entrypoint",
        "medium",
        "Dockerfile",
        ('ENTRYPOINT ["python3", "-m", "gis_agent_harness.cli"]',),
        "Keep container use scoped to the local CLI.",
    ),
    _CheckSpec(
        "docker_workspace_runtime",
        "packaging",
        "Docker workspace runtime",
        "medium",
        "Dockerfile",
        ("WORKDIR /workspace",),
        "Keep container runtime behavior local-first.",
    ),
    _CheckSpec(
        "env_mock_default",
        "configuration",
        "env mock default",
        "high",
        ".env.example",
        ("GIS_AGENT_HARNESS_USE_MOCK=true", "GIS_AGENT_HARNESS_PROVIDER=mock"),
        "Keep the example environment offline by default.",
    ),
    _CheckSpec(
        "env_state_paths",
        "configuration",
        "env state paths",
        "medium",
        ".env.example",
        ("GIS_AGENT_HARNESS_RUN_ROOT=.runs", "GIS_AGENT_HARNESS_STATE_FILE=AGENT_STATE.md"),
        "Expose local state paths in the environment example.",
    ),
    _CheckSpec(
        "env_telemetry_local",
        "configuration",
        "env local telemetry",
        "high",
        ".env.example",
        ("GIS_AGENT_HARNESS_TELEMETRY_LOCAL_ONLY=true",),
        "Keep telemetry local-only by default.",
    ),
    _CheckSpec(
        "env_qgis_confirmation",
        "configuration",
        "env qgis confirmation",
        "high",
        ".env.example",
        ("GIS_AGENT_HARNESS_QGIS_REQUIRE_CONFIRM=true",),
        "Expose the qgis_process confirmation guard in local config.",
    ),
    _CheckSpec(
        "config_mock_provider",
        "configuration",
        "config mock provider default",
        "high",
        "src/gis_agent_harness/config.py",
        ('provider: str = "mock"', "use_mock: bool = True"),
        "Keep mock routing as the default runtime configuration.",
    ),
    _CheckSpec(
        "config_timeout_budget",
        "configuration",
        "config timeout and retry budget",
        "medium",
        "src/gis_agent_harness/config.py",
        ("timeout_seconds: int = 20", "max_iterations: int = 3"),
        "Keep bounded runtime defaults for local execution.",
    ),
    _CheckSpec(
        "config_qgis_guard",
        "configuration",
        "config qgis confirmation guard",
        "high",
        "src/gis_agent_harness/config.py",
        ("qgis_require_confirm: bool = True", "GIS_AGENT_HARNESS_QGIS_REQUIRE_CONFIRM"),
        "Keep live qgis_process execution protected by default.",
    ),
    _CheckSpec(
        "cli_lazy_spatial_tools",
        "cli",
        "CLI lazy spatial imports",
        "high",
        "src/gis_agent_harness/cli.py",
        ("from .spatial_tools import inspect_vector", "from .spatial_tools import inspect_raster"),
        "Keep GIS imports inside command handlers.",
    ),
    _CheckSpec(
        "cli_output_file_helper",
        "cli",
        "CLI output-file helper",
        "medium",
        "src/gis_agent_harness/cli.py",
        ("def _emit_text", "output_file"),
        "Reuse the shared output writer for JSON and Markdown commands.",
    ),
    _CheckSpec(
        "cli_config_doctor",
        "cli",
        "CLI config doctor command",
        "medium",
        "src/gis_agent_harness/cli.py",
        ('@main.group("config")', 'doctor_config'),
        "Keep provider readiness checks available without network calls.",
    ),
    _CheckSpec(
        "cli_health_report",
        "cli",
        "CLI health report command",
        "medium",
        "src/gis_agent_harness/cli.py",
        ('@main.command("health-report")', "build_health_report"),
        "Expose the local project health report from the CLI.",
    ),
    _CheckSpec(
        "cli_improvement_catalog",
        "cli",
        "CLI improvement catalog command",
        "medium",
        "src/gis_agent_harness/cli.py",
        ('@main.command("improvement-catalog")', "build_improvement_catalog"),
        "Expose the offline improvement backlog from the CLI.",
    ),
    _CheckSpec(
        "cli_project_metrics",
        "cli",
        "CLI project metrics command",
        "medium",
        "src/gis_agent_harness/cli.py",
        ('@main.command("project-metrics")', "build_project_metrics"),
        "Expose local Git and code-size progress metrics from the CLI.",
    ),
    _CheckSpec(
        "state_markdown_header",
        "operations",
        "state markdown header",
        "medium",
        "src/gis_agent_harness/state_store.py",
        ("# Agent State", "Append-only run history"),
        "Keep state logs human-readable and append-only.",
    ),
    _CheckSpec(
        "state_jsonl_write",
        "operations",
        "state JSONL write",
        "high",
        "src/gis_agent_harness/state_store.py",
        ('self.state_jsonl.open("a"',),
        "Keep structured state appends in JSONL form.",
    ),
    _CheckSpec(
        "telemetry_redaction",
        "security",
        "telemetry secret redaction",
        "high",
        "src/gis_agent_harness/telemetry.py",
        ("REDACTED_SUFFIXES", "***redacted***"),
        "Continue redacting secret-like telemetry keys.",
    ),
    _CheckSpec(
        "telemetry_summary",
        "operations",
        "telemetry summary",
        "medium",
        "src/gis_agent_harness/telemetry.py",
        ("summarize_telemetry", "event_counts"),
        "Keep compact event count reporting available.",
    ),
    _CheckSpec(
        "mcp_registry_progressive",
        "architecture",
        "MCP progressive registry",
        "medium",
        "src/gis_agent_harness/mcp_registry.py",
        ("progressive_disclosure", "mcp-json-rpc"),
        "Keep local MCP manifests explicit and progressive.",
    ),
    _CheckSpec(
        "improvement_catalog_module",
        "architecture",
        "improvement catalog module",
        "medium",
        "src/gis_agent_harness/improvement_catalog.py",
        ("ImprovementItem", "CATALOG_ITEMS", "build_improvement_catalog"),
        "Keep the large offline improvement catalog queryable from Python.",
    ),
    _CheckSpec(
        "improvement_catalog_readme",
        "documentation",
        "README improvement catalog command",
        "medium",
        "README.md",
        ("improvement-catalog", "1000-item offline improvement backlog"),
        "Document the large improvement backlog command for operators.",
    ),
    _CheckSpec(
        "improvement_catalog_acceptance",
        "testing",
        "acceptance improvement catalog check",
        "medium",
        "scripts/verify_acceptance.py",
        ("improvement_catalog", "improvement-catalog"),
        "Keep the improvement catalog wired into acceptance evidence.",
    ),
    _CheckSpec(
        "readme_project_metrics_command",
        "documentation",
        "README project metrics command",
        "medium",
        "README.md",
        ("project-metrics", "--target-commits 100", "--target-python-lines 10000"),
        "Document the progress-audit command for local and cloud commit goals.",
    ),
    _CheckSpec(
        "readme_project_metrics_markdown_command",
        "documentation",
        "README project metrics Markdown command",
        "medium",
        "README.md",
        ("project-metrics --format markdown", "--target-commits 100", "--target-python-lines 10000"),
        "Document the human-readable project metrics view for handoff reports.",
    ),
    _CheckSpec(
        "readme_project_metrics_strict_command",
        "documentation",
        "README project metrics strict command",
        "medium",
        "README.md",
        ("project-metrics", "--fail-on-unmet-targets", "--target-commits 100"),
        "Document the optional nonzero exit gate for unmet progress targets.",
    ),
    _CheckSpec(
        "readme_project_metrics_top_files_command",
        "documentation",
        "README project metrics top files command",
        "medium",
        "README.md",
        ("project-metrics", "--top-files 3", "--target-python-lines 10000"),
        "Document the largest-file audit for explaining code-size distribution.",
    ),
    _CheckSpec(
        "readme_project_metrics_total_lines_command",
        "documentation",
        "README project metrics total lines command",
        "medium",
        "README.md",
        ("project-metrics", "--target-total-lines 10000"),
        "Document the total line target audit for handoff checks.",
    ),
    _CheckSpec(
        "readme_project_metrics_clean_gate_command",
        "documentation",
        "README project metrics clean gate command",
        "medium",
        "README.md",
        ("project-metrics", "--require-clean", "--target-total-lines 10000"),
        "Document the clean-worktree gate for final handoff checks.",
    ),
    _CheckSpec(
        "acceptance_project_metrics",
        "testing",
        "acceptance project metrics check",
        "medium",
        "scripts/verify_acceptance.py",
        ("project_metrics", "project-metrics", "target-python-lines"),
        "Keep project metrics wired into acceptance evidence.",
    ),
    _CheckSpec(
        "acceptance_project_metrics_markdown",
        "testing",
        "acceptance project metrics Markdown check",
        "medium",
        "scripts/verify_acceptance.py",
        ("project_metrics_markdown", "format", "markdown"),
        "Keep the Markdown metrics report wired into acceptance evidence.",
    ),
    _CheckSpec(
        "acceptance_project_metrics_strict_gate",
        "testing",
        "acceptance project metrics strict gate",
        "medium",
        "scripts/verify_acceptance.py",
        ("project_metrics_strict_gate", "fail-on-unmet-targets", "expect_success=False"),
        "Keep the strict metrics gate covered by acceptance evidence.",
    ),
    _CheckSpec(
        "acceptance_project_metrics_top_files",
        "testing",
        "acceptance project metrics top files check",
        "medium",
        "scripts/verify_acceptance.py",
        ("project_metrics_top_files", "top-files", "top_python_files"),
        "Keep the largest-file metrics audit covered by acceptance evidence.",
    ),
    _CheckSpec(
        "acceptance_project_metrics_total_lines",
        "testing",
        "acceptance project metrics total lines check",
        "medium",
        "scripts/verify_acceptance.py",
        ("target-total-lines", "total_lines", "line_counts"),
        "Keep the total line target covered by acceptance evidence.",
    ),
    _CheckSpec(
        "acceptance_health_report_strict_gate",
        "testing",
        "acceptance health report strict gate",
        "medium",
        "scripts/verify_acceptance.py",
        ("health_report_strict_gate", "fail-on-failed", "failed_returncode"),
        "Keep the strict health-report gate covered by acceptance evidence.",
    ),
    _CheckSpec(
        "mcp_runtime_dispatch",
        "features",
        "MCP runtime dispatch",
        "medium",
        "src/gis_agent_harness/mcp_runtime.py",
        ("call_mcp_tool", "inspect_vector", "inspect_raster", "replace(\"-\", \"_\")"),
        "Keep local MCP tools executable, not just declarative.",
    ),
    _CheckSpec(
        "qgis_dry_run_default",
        "security",
        "qgis dry-run default",
        "high",
        "src/gis_agent_harness/qgis_process.py",
        ("dry_run", "approval_required"),
        "Keep qgis_process preview-first behavior.",
    ),
    _CheckSpec(
        "sandbox_timeout",
        "security",
        "sandbox timeout enforcement",
        "high",
        "src/gis_agent_harness/sandbox.py",
        ("timeout", "timed_out"),
        "Keep generated code bounded by timeout.",
    ),
    _CheckSpec(
        "guardrails_ast_scan",
        "security",
        "AST guardrail scan",
        "high",
        "src/gis_agent_harness/guardrails.py",
        ("ast", "blocked"),
        "Keep generated Python scanned before execution.",
    ),
    _CheckSpec(
        "templates_builtin_ids",
        "features",
        "built-in goal templates",
        "medium",
        "README.md",
        ("align_vector_to_raster", "declare_source_crs", "repair_invalid_geometry"),
        "Keep built-in templates covering core GIS repair goals.",
    ),
    _CheckSpec(
        "execution_plan_markdown",
        "features",
        "execution plan markdown support",
        "medium",
        "src/gis_agent_harness/execution_plan.py",
        ("frontmatter", "yaml"),
        "Keep plans loadable from YAML and Markdown-frontmatter inputs.",
    ),
    _CheckSpec(
        "test_cli_heavy_import_guard",
        "testing",
        "CLI heavy import test",
        "high",
        "tests/test_cli.py",
        ("test_cli_import_does_not_load_heavy_gis_dependencies",),
        "Retain a regression test for lazy GIS imports.",
    ),
    _CheckSpec(
        "test_health_report",
        "testing",
        "health report tests",
        "medium",
        "tests/test_health_report.py",
        ("test_health_report_builds_at_least_fifty_local_checks",),
        "Keep the health-report feature covered by unit and CLI tests.",
    ),
    _CheckSpec(
        "test_improvement_catalog",
        "testing",
        "improvement catalog tests",
        "medium",
        "tests/test_improvement_catalog.py",
        ("test_improvement_catalog_contains_large_offline_backlog",),
        "Keep the large improvement catalog covered by unit and CLI tests.",
    ),
    _CheckSpec(
        "test_acceptance_smoke",
        "testing",
        "acceptance script smoke test",
        "high",
        "tests/test_e2e_smoke.py",
        ("test_verify_acceptance_script_smoke",),
        "Keep the acceptance verifier covered from pytest.",
    ),
)


def _contains_all(text: str, tokens: tuple[str, ...]) -> bool:
    return all(token in text for token in tokens)


def _evaluate_spec(root: Path, spec: _CheckSpec) -> HealthCheck:
    if spec.path is None:
        exists = True
        text = ""
        evidence = "repository-level check"
    else:
        path = root / spec.path
        exists = path.exists()
        text = path.read_text(encoding="utf-8") if exists and path.is_file() else ""
        evidence = f"{spec.path} exists" if exists else f"{spec.path} missing"

    token_match = _contains_all(text, spec.tokens)
    passed = exists and token_match
    if passed:
        evidence = f"{evidence}; matched {len(spec.tokens)} token(s)"
    elif exists:
        missing = [token for token in spec.tokens if token not in text]
        evidence = f"{evidence}; missing token(s): {', '.join(missing)}"

    return HealthCheck(
        check_id=spec.check_id,
        category=spec.category,
        title=spec.title,
        status="passed" if passed else "failed",
        severity=spec.severity,
        evidence=evidence,
        recommendation=spec.recommendation,
    )


def build_health_report(root: str | Path = Path("."), *, category: str | None = None) -> HealthReport:
    resolved_root = Path(root).resolve()
    checks = [_evaluate_spec(resolved_root, spec) for spec in CHECK_SPECS]
    if category is not None:
        checks = [check for check in checks if check.category == category]
    return HealthReport(root=resolved_root, checks=checks, category_filter=category)


def _escape_markdown_cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_health_report_markdown(report: HealthReport) -> str:
    payload = report.to_dict()
    summary = payload["summary"]
    lines = [
        "# GIS Agent Harness Health Report",
        "",
        "## Summary",
        f"- Root: {payload['root']}",
        f"- Category filter: {payload['category_filter'] or 'all'}",
        f"- Total checks: {summary['total']}",
        f"- Status counts: {summary['by_status']}",
        f"- Category counts: {summary['by_category']}",
        "",
        "## Checks",
        "| Check | Status | Severity | Evidence | Recommendation |",
        "| --- | --- | --- | --- | --- |",
    ]
    for check in report.checks:
        lines.append(
            "| "
            + " | ".join(
                [
                    _escape_markdown_cell(check.title),
                    _escape_markdown_cell(check.status),
                    _escape_markdown_cell(check.severity),
                    _escape_markdown_cell(check.evidence),
                    _escape_markdown_cell(check.recommendation),
                ]
            )
            + " |"
        )
    return "\n".join(lines)
