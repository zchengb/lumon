"""Contract tests for Workspace-scoped Markdown capabilities."""

from __future__ import annotations

from pathlib import Path

import pytest

from lumon.capabilities.catalog import CapabilityCatalog, CapabilityValidationError
from lumon.workspace.layout import WorkspaceLayout


def _capability_content(
    capability_id: str = "custom-capability",
    *,
    enabled: bool = True,
    brief: str = "Handle a custom capability.",
) -> str:
    enabled_value = "true" if enabled else "false"
    return (
        "---\n"
        f'id = "{capability_id}"\n'
        'name = "Custom capability"\n'
        f"enabled = {enabled_value}\n"
        f'brief = "{brief}"\n'
        "---\n\n"
        "# Custom capability\n\n"
        "Follow the custom capability guidance.\n"
    )


def test_capability_is_valid_and_briefs_do_not_include_the_body(tmp_path: Path) -> None:
    catalog = CapabilityCatalog(tmp_path)
    definition = catalog.create(_capability_content("aws-cli", brief="Inspect AWS resources."))

    snapshot = catalog.discover()

    assert definition.capability_id == "aws-cli"
    assert definition.path == Path("lumon/capabilities/aws-cli.md")
    assert snapshot.diagnostics == ()
    assert snapshot.briefs[0].capability_id == "aws-cli"
    assert snapshot.briefs[0].path == "lumon/capabilities/aws-cli.md"
    assert snapshot.briefs[0].brief == "Inspect AWS resources."
    assert "Follow the custom capability guidance." in definition.body


def test_catalog_exposes_disabled_capabilities_but_excludes_them_from_briefs(
    tmp_path: Path,
) -> None:
    catalog = CapabilityCatalog(tmp_path)
    catalog.create(_capability_content(enabled=False))

    snapshot = catalog.discover()

    assert len(snapshot.definitions) == 1
    assert snapshot.definitions[0].enabled is False
    assert snapshot.briefs == ()


def test_catalog_reports_invalid_and_duplicate_capabilities(tmp_path: Path) -> None:
    capabilities_dir = WorkspaceLayout.from_root(tmp_path).capabilities_dir
    capabilities_dir.mkdir(parents=True)
    (capabilities_dir / "invalid.md").write_text("broken", encoding="utf-8")
    (capabilities_dir / "first.md").write_text(
        _capability_content("same-capability"),
        encoding="utf-8",
    )
    (capabilities_dir / "second.md").write_text(
        _capability_content("same-capability"),
        encoding="utf-8",
    )

    snapshot = CapabilityCatalog(tmp_path).discover()

    assert snapshot.definitions == ()
    messages = {diagnostic.message for diagnostic in snapshot.diagnostics}
    assert messages == {
        "Capability must start with TOML frontmatter.",
        "duplicate capability id: same-capability",
    }


def test_capability_edits_can_rename_the_file_inside_the_workspace(
    tmp_path: Path,
) -> None:
    catalog = CapabilityCatalog(tmp_path)

    with pytest.raises(CapabilityValidationError, match="Capability id"):
        catalog.create(_capability_content("../outside"))

    created = catalog.create(_capability_content())
    catalog.create(_capability_content("existing-capability"))
    with pytest.raises(CapabilityValidationError, match="already exists"):
        catalog.save(
            _capability_content("existing-capability"),
            expected_id=created.capability_id,
        )

    renamed = catalog.save(
        _capability_content("renamed-capability", brief="Renamed capability."),
        expected_id=created.capability_id,
    )

    assert renamed.capability_id == "renamed-capability"
    assert renamed.path == Path("lumon/capabilities/renamed-capability.md")
    assert not (tmp_path / "lumon" / "capabilities" / "custom-capability.md").exists()
    updated = catalog.save(
        _capability_content("renamed-capability", brief="Updated capability."),
        expected_id=renamed.capability_id,
    )

    assert updated.brief == "Updated capability."
    assert updated.path == Path("lumon/capabilities/renamed-capability.md")
