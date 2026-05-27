from __future__ import annotations

import pytest

from gis_agent_harness.task_templates import TemplateRegistry


def test_template_registry_lists_builtin_templates() -> None:
    registry = TemplateRegistry()
    template_ids = {template.template_id for template in registry.list()}
    assert {
        "align_vector_to_raster",
        "declare_source_crs",
        "repair_invalid_geometry",
    }.issubset(template_ids)


def test_template_renders_agent_task(fixture_paths: dict[str, str]) -> None:
    registry = TemplateRegistry()
    task = registry.render_task(
        "align_vector_to_raster",
        values={
            "vector": fixture_paths["sample_3857"],
            "raster": fixture_paths["sample_raster"],
        },
    )
    assert task.vector_path == fixture_paths["sample_3857"]
    assert task.raster_path == fixture_paths["sample_raster"]
    assert task.template_id == "align_vector_to_raster"


def test_template_requires_expected_inputs(fixture_paths: dict[str, str]) -> None:
    registry = TemplateRegistry()
    with pytest.raises(ValueError):
        registry.render_task(
            "declare_source_crs",
            values={"vector": fixture_paths["missing_crs"]},
        )
