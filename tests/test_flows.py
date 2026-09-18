"""Contract tests for Workspace-scoped Markdown flows."""

from __future__ import annotations

from pathlib import Path

import pytest

from lumon.flows.catalog import FlowCatalog, FlowValidationError
from lumon.flows.protocol import extract_flow_selection
from lumon.workspace.layout import WorkspaceLayout


def _flow_content(
    flow_id: str = "custom-flow",
    *,
    enabled: bool = True,
    brief: str = "Handle a custom request.",
) -> str:
    enabled_value = "true" if enabled else "false"
    return (
        "---\n"
        f'id = "{flow_id}"\n'
        'name = "Custom flow"\n'
        f"enabled = {enabled_value}\n"
        f'brief = "{brief}"\n'
        "---\n\n"
        "# Custom flow\n\n"
        "Follow the custom request steps.\n"
    )


def test_flow_is_valid_and_briefs_do_not_include_the_body(tmp_path: Path) -> None:
    catalog = FlowCatalog(tmp_path)
    definition = catalog.create(_flow_content("test-case-generation", brief="Generate test cases."))

    snapshot = catalog.discover()

    assert definition.flow_id == "test-case-generation"
    assert definition.path == Path("lumon/flows/test-case-generation.md")
    assert snapshot.diagnostics == ()
    assert snapshot.briefs[0].flow_id == "test-case-generation"
    assert snapshot.briefs[0].path == "lumon/flows/test-case-generation.md"
    assert snapshot.briefs[0].brief == "Generate test cases."
    assert not hasattr(snapshot.briefs[0], "name")
    assert not hasattr(snapshot.briefs[0], "match_hints")
    assert "Follow the custom request steps." in definition.body


def test_catalog_exposes_disabled_flows_but_excludes_them_from_briefs(tmp_path: Path) -> None:
    catalog = FlowCatalog(tmp_path)
    catalog.create(_flow_content(enabled=False))

    snapshot = catalog.discover()

    assert len(snapshot.definitions) == 1
    assert snapshot.definitions[0].enabled is False
    assert snapshot.briefs == ()


def test_catalog_reports_invalid_and_duplicate_flow_definitions(tmp_path: Path) -> None:
    flows_dir = WorkspaceLayout.from_root(tmp_path).flows_dir
    flows_dir.mkdir(parents=True)
    (flows_dir / "invalid.md").write_text("not frontmatter", encoding="utf-8")
    (flows_dir / "first.md").write_text(_flow_content("same-flow"), encoding="utf-8")
    (flows_dir / "second.md").write_text(_flow_content("same-flow"), encoding="utf-8")

    snapshot = FlowCatalog(tmp_path).discover()

    assert snapshot.definitions == ()
    messages = {diagnostic.message for diagnostic in snapshot.diagnostics}
    assert "Flow must start with TOML frontmatter." in messages
    assert messages == {
        "Flow must start with TOML frontmatter.",
        "duplicate flow id: same-flow",
    }


def test_catalog_resolves_a_valid_id_from_a_workspace_relative_filename(tmp_path: Path) -> None:
    flows_dir = WorkspaceLayout.from_root(tmp_path).flows_dir
    flows_dir.mkdir(parents=True)
    named_path = flows_dir / "descriptive-name.md"
    named_path.write_text(_flow_content("descriptive-flow"), encoding="utf-8")
    catalog = FlowCatalog(tmp_path)

    definition = catalog.read("descriptive-flow")
    updated = catalog.save(
        _flow_content("descriptive-flow", brief="Updated in place."),
        expected_id="descriptive-flow",
    )

    assert definition.path == Path("lumon/flows/descriptive-name.md")
    assert updated.path == definition.path
    assert updated.brief == "Updated in place."
    assert not (flows_dir / "descriptive-flow.md").exists()


def test_catalog_validates_ids_and_renames_inside_workspace(tmp_path: Path) -> None:
    catalog = FlowCatalog(tmp_path)

    with pytest.raises(FlowValidationError, match="Flow id"):
        catalog.create(_flow_content("../outside"))

    created = catalog.create(_flow_content())
    catalog.create(_flow_content("existing-flow"))
    with pytest.raises(FlowValidationError, match="already exists"):
        catalog.save(_flow_content("existing-flow"), expected_id=created.flow_id)

    renamed = catalog.save(
        _flow_content("renamed-flow", brief="Renamed request."),
        expected_id=created.flow_id,
    )

    assert renamed.flow_id == "renamed-flow"
    assert renamed.path == Path("lumon/flows/renamed-flow.md")
    assert not (tmp_path / "lumon" / "flows" / "custom-flow.md").exists()
    updated = catalog.save(
        _flow_content("renamed-flow", brief="Updated custom request."),
        expected_id=renamed.flow_id,
    )

    assert updated.brief == "Updated custom request."
    assert updated.path == Path("lumon/flows/renamed-flow.md")
    assert tuple(tmp_path.glob("**/.renamed-flow.md.*")) == ()
    assert (
        (tmp_path / "lumon" / "flows" / "renamed-flow.md")
        .read_text(encoding="utf-8")
        .startswith("---\n")
    )


def test_flow_selection_marker_is_removed_and_invalid_markers_are_ignored() -> None:
    selected, status, cleaned = extract_flow_selection(
        '<lumon-flow>{"flow_id":"test-case-generation","status":"selected"}</lumon-flow>\nDone'
    )

    assert selected == "test-case-generation"
    assert status == "selected"
    assert cleaned == "Done"

    invalid, invalid_status, invalid_cleaned = extract_flow_selection(
        '<lumon-flow>{"flow_id":"../outside","status":"selected"}</lumon-flow>Done'
    )
    assert invalid is None
    assert invalid_status == "selected"
    assert invalid_cleaned == "Done"
