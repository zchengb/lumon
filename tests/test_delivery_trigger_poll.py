"""The CLI records trigger checks without paying for empty Agent turns."""

from dataclasses import replace
from pathlib import Path
from typing import NoReturn
from uuid import UUID

import pytest

from lumon.agents.agent.config import AgentConfig
from lumon.cli.app import main
from lumon.delivery.store import DeliveryRunStore
from lumon.errors import PreflightError
from lumon.skills.installer import SkillInstaller
from lumon.tools.jira_delivery import JiraDeliveryCandidate, JiraDeliveryTrigger
from lumon.workspace.initializer import WorkspaceInitializer
from lumon.workspace.model import InitRequest
from lumon.workspace.registry import WorkspaceRegistry
from lumon.workspace.settings import AutoDeliverySettings, WorkspaceSettings, WorkspaceSettingsStore


@pytest.fixture
def workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, UUID, WorkspaceSettingsStore]:
    state = tmp_path / "state"
    root = tmp_path / "workspace"
    monkeypatch.setenv("LUMON_HOME", str(state))
    registry = WorkspaceRegistry(state)
    store = WorkspaceSettingsStore(state)
    WorkspaceInitializer(
        skill_installer=SkillInstaller(tmp_path / "skills"), registry=registry, settings_store=store
    ).initialize(InitRequest(root, name="Trigger test"))
    workspace_id = registry.list()[0].workspace_id
    store.save(
        WorkspaceSettings(
            workspace_id,
            auto_delivery=AutoDeliverySettings(
                enabled=True, jira_site="test.atlassian.net", trigger_jql="project = TEST"
            ),
        )
    )

    def forbidden_runner(_config: AgentConfig) -> NoReturn:
        pytest.fail("No Codex runner may be created for this trigger check.")

    monkeypatch.setattr("lumon.cli.commands.delivery.create_agent_runner", forbidden_runner)
    return root, workspace_id, store


@pytest.mark.parametrize("detection", ["empty", "failed", "paused", "unconfigured"])
def test_detection_does_not_start_codex(
    workspace: tuple[Path, UUID, WorkspaceSettingsStore],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    detection: str,
) -> None:
    root, workspace_id, store = workspace
    if detection == "unconfigured":
        store.save(
            WorkspaceSettings(workspace_id, auto_delivery=AutoDeliverySettings(enabled=True))
        )
    else:

        async def find(
            self: JiraDeliveryTrigger,
            jira_site: str,
            trigger_jql: str,
            *,
            excluded_keys: frozenset[str],
        ) -> JiraDeliveryCandidate | None:
            assert jira_site == "test.atlassian.net" and trigger_jql == "project = TEST"
            assert not excluded_keys
            if detection == "failed":
                raise PreflightError("Jira detection failed; Codex was not started.")
            if detection == "paused":
                current = store.load(workspace_id)
                store.save(
                    replace(current, auto_delivery=replace(current.auto_delivery, enabled=False))
                )
                return JiraDeliveryCandidate(
                    "TEST-1", "Small fix", "https://test.atlassian.net/browse/TEST-1"
                )
            return None

        monkeypatch.setattr(JiraDeliveryTrigger, "find_candidate", find)

    exit_code = main(["delivery", "poll", "--workspace", str(root), "--json"])
    output = capsys.readouterr()
    poll = DeliveryRunStore().list_polls(root)[0]
    assert poll.finished_at is not None
    assert poll.duration_seconds is not None
    assert DeliveryRunStore().list(root) == ()
    if detection == "empty":
        assert exit_code == 0 and poll.state == "idle"
        assert '"status": "idle"' in output.out
        assert "Codex was not started" in DeliveryRunStore().activity(root, poll.run_id)[0].detail
    else:
        assert exit_code == PreflightError.exit_code and poll.state == "failed"
        assert "Error:" in output.err


def test_disabled_poll_does_not_query_jira_or_create_a_receipt(
    workspace: tuple[Path, UUID, WorkspaceSettingsStore],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root, workspace_id, store = workspace
    current = store.load(workspace_id)
    store.save(replace(current, auto_delivery=replace(current.auto_delivery, enabled=False)))

    async def forbidden_query(
        self: JiraDeliveryTrigger,
        jira_site: str,
        trigger_jql: str,
        *,
        excluded_keys: frozenset[str],
    ) -> NoReturn:
        pytest.fail("A disabled poll must not query Jira.")

    monkeypatch.setattr(JiraDeliveryTrigger, "find_candidate", forbidden_query)
    assert main(["delivery", "poll", "--workspace", str(root), "--json"]) == 0
    assert '"status": "disabled"' in capsys.readouterr().out
    assert DeliveryRunStore().list_polls(root) == ()
