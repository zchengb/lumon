"""Contract tests for scheduled Auto Delivery configuration."""

from __future__ import annotations

from pathlib import Path

import pytest

from lumon.agents.agent.config import AgentConfig, AgentConfigStore
from lumon.agents.agent.model import (
    AgentEvent,
    AgentProgress,
    AgentResult,
    AgentResultStatus,
    ProgressPhase,
)
from lumon.agents.agent.runner import AgentEventCallback, ProgressCallback
from lumon.cli.app import main
from lumon.delivery.model import DeliveryRun, DeliveryState
from lumon.delivery.scheduler import launchd_timing
from lumon.delivery.service import DeliveryService
from lumon.delivery.store import DeliveryRunStore
from lumon.errors import AgentRuntimeError, InvalidInputError, PreflightError
from lumon.skills.installer import SkillInstaller
from lumon.tools.jira_delivery import JiraDeliveryCandidate, JiraDeliveryTrigger
from lumon.workspace.initializer import WorkspaceInitializer
from lumon.workspace.model import InitRequest
from lumon.workspace.registry import WorkspaceRegistry
from lumon.workspace.settings import (
    AutoDeliverySettings,
    WorkspaceSettings,
    WorkspaceSettingsStore,
    normalize_trigger_hooks,
    validate_schedule_expression,
)


def _candidate(monkeypatch: pytest.MonkeyPatch) -> None:
    async def find(
        self: JiraDeliveryTrigger,
        jira_site: str,
        trigger_jql: str,
        *,
        excluded_keys: frozenset[str],
    ) -> JiraDeliveryCandidate | None:
        assert jira_site == "test.atlassian.net"
        assert trigger_jql == "project = MBPAS"
        if "MBPAS-1" in excluded_keys:
            return None
        return JiraDeliveryCandidate(
            "MBPAS-1", "Version bump", "https://test.atlassian.net/browse/MBPAS-1"
        )

    monkeypatch.setattr(JiraDeliveryTrigger, "find_candidate", find)


def test_trigger_hooks_are_normalized_and_deduplicated() -> None:
    assert normalize_trigger_hooks("jira.delivery_ready\njira.delivery_ready\n") == (
        "jira.delivery_ready",
    )


def test_trigger_prompt_preserves_paragraphs_and_normalizes_line_endings() -> None:
    assert normalize_trigger_hooks(
        "  Check approved Stories.\r\n\r\n  1. Verify before delivery.\r\n"
    ) == ("Check approved Stories.\n\n  1. Verify before delivery.",)
    with pytest.raises(InvalidInputError, match="control characters"):
        normalize_trigger_hooks("jira.delivery_ready\x0bmail.delivery_ready")
    with pytest.raises(InvalidInputError, match="strings"):
        normalize_trigger_hooks([123])


@pytest.mark.parametrize(
    "hooks",
    [
        ("jira.delivery_ready", "mail.delivery_ready"),
        ("Check approved Stories.\n\n1. Verify before delivery.\n2. Follow the workflow.",),
    ],
)
@pytest.mark.parametrize("status", ["succeeded", "failed"])
def test_scheduled_poll_runs_saved_instructions_and_loads_edits_on_next_poll(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    hooks: tuple[str, ...],
    status: AgentResultStatus,
) -> None:
    state_root = tmp_path / "state"
    workspace = tmp_path / "workspace"
    monkeypatch.setenv("LUMON_HOME", str(state_root))
    registry = WorkspaceRegistry(state_root)
    settings_store = WorkspaceSettingsStore(state_root)
    WorkspaceInitializer(
        skill_installer=SkillInstaller(tmp_path / "skills"),
        registry=registry,
        settings_store=settings_store,
    ).initialize(InitRequest(workspace, name="delivery-lab"))
    workspace_id = registry.list()[0].workspace_id
    AgentConfigStore(state_root).save(
        AgentConfig(enabled=True, feishu_app_id="test-app", feishu_app_secret="test-secret")
    )
    prompts: list[str] = []

    class PollRunner:
        async def run(
            self,
            root: Path,
            prompt: str,
            *,
            on_progress: ProgressCallback | None = None,
            on_event: AgentEventCallback | None = None,
        ) -> AgentResult:
            assert root == workspace
            prompts.append(prompt)
            assert on_progress is not None and on_event is not None
            await on_progress(
                AgentProgress(ProgressPhase.EXECUTING, "Check active sprint Stories.")
            )
            await on_event(
                AgentEvent(
                    kind="command_execution",
                    lifecycle="completed",
                    exit_code=0,
                    command="echo secret-command",
                    output="secret raw output",
                )
            )
            return AgentResult(
                status=status,
                final_text="AUTO_DELIVERY_IDLE",
                failure_diagnostic="Agent poll failed" if status == "failed" else None,
            )

    def create_runner(config: AgentConfig) -> PollRunner:
        assert config.enabled
        return PollRunner()

    monkeypatch.setattr("lumon.cli.commands.delivery.create_agent_runner", create_runner)
    _candidate(monkeypatch)
    for instructions in (hooks, ("Check the newly approved Stories.\n\nVerify before delivery.",)):
        settings_store.save(
            WorkspaceSettings(
                workspace_id,
                auto_delivery=AutoDeliverySettings(
                    enabled=True,
                    trigger_hooks=instructions,
                    jira_site="test.atlassian.net",
                    trigger_jql="project = MBPAS",
                ),
            )
        )
        exit_code = main(["delivery", "poll", "--workspace", str(workspace), "--json"])
        output = capsys.readouterr()
        assert "\n\n".join(instructions) in prompts[-1]
        assert "lumon delivery start" in prompts[-1]
        assert "AUTO_DELIVERY_IDLE" in prompts[-1]
        assert "exactly one terminal command" in prompts[-1]
        polls = DeliveryRunStore().list_polls(workspace)
        latest = polls[0]
        assert latest.state == ("idle" if status == "succeeded" else "failed")
        assert latest.phase == "discover"
        assert latest.duration_seconds is not None
        activity = DeliveryRunStore().activity(workspace, latest.run_id)
        assert activity[0].detail == "Jira matched MBPAS-1; starting Agent for this Story only."
        assert activity[1].detail == "Check active sprint Stories."
        assert activity[2].detail == "command execution: completed (exit 0)"
        assert "secret raw output" not in str(activity)
        assert "\n\n".join(instructions) not in output.out + output.err
        if status == "succeeded":
            assert exit_code == 0
            assert '"status": "idle"' in output.out
        else:
            assert exit_code == AgentRuntimeError.exit_code
            assert "Agent poll failed" in output.err


@pytest.mark.parametrize(
    "outcome", ["completed", "blocked", "unfinished", "runner-failed", "invented", "wrong-story"]
)
def test_poll_requires_a_durable_story_outcome(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    outcome: str,
) -> None:
    state = tmp_path / "state"
    workspace = tmp_path / "workspace"
    monkeypatch.setenv("LUMON_HOME", str(state))
    registry = WorkspaceRegistry(state)
    settings = WorkspaceSettingsStore(state)
    WorkspaceInitializer(
        skill_installer=SkillInstaller(tmp_path / "skills"),
        registry=registry,
        settings_store=settings,
    ).initialize(InitRequest(workspace, name="Delivery test"))
    workspace_id = registry.list()[0].workspace_id
    settings.save(
        WorkspaceSettings(
            workspace_id,
            auto_delivery=AutoDeliverySettings(
                enabled=True, jira_site="test.atlassian.net", trigger_jql="project = MBPAS"
            ),
        )
    )
    AgentConfigStore(state).save(
        AgentConfig(enabled=True, feishu_app_id="test-app", feishu_app_secret="test-secret")
    )
    service = DeliveryService(settings_store=settings)

    class StoryRunner:
        async def run(
            self,
            root: Path,
            prompt: str,
            *,
            on_progress: ProgressCallback | None = None,
            on_event: AgentEventCallback | None = None,
        ) -> AgentResult:
            poll = service.run_store.list_polls(root)[0]
            assert f"--poll-id {poll.run_id}" in prompt
            if outcome != "invented":
                run = DeliveryRun.claim(
                    "story-1",
                    "MBPAS-2" if outcome == "wrong-story" else "MBPAS-1",
                    "Version bump",
                    workspace_id=workspace_id,
                    poll_id=poll.run_id,
                )
                service.start(root, workspace_id, run)
                run = service.progress(root, run, phase="verification", detail="Version checked.")
                if outcome == "completed":
                    service.complete(root, workspace_id, run, "Local handoff.", phase="handoff")
                elif outcome == "blocked":
                    service.block(
                        root, workspace_id, run, "Tooling unavailable.", phase="verification"
                    )
            return AgentResult(
                status="failed" if outcome == "runner-failed" else "succeeded",
                final_text="Local version bump verified.",
                failure_diagnostic="Agent exited." if outcome == "runner-failed" else None,
            )

    def create_runner(config: AgentConfig) -> StoryRunner:
        assert config.enabled
        return StoryRunner()

    monkeypatch.setattr("lumon.cli.commands.delivery.create_agent_runner", create_runner)
    _candidate(monkeypatch)
    exit_code = main(["delivery", "poll", "--workspace", str(workspace), "--json"])
    output = capsys.readouterr()
    poll = service.run_store.list_polls(workspace)[0]
    assert poll.finished_at is not None
    assert poll.state == ("completed" if outcome == "completed" else "failed")
    assert exit_code == (0 if outcome == "completed" else AgentRuntimeError.exit_code)
    if outcome != "invented":
        run = service.run_store.load(workspace, "story-1")
        assert run.poll_id == poll.run_id
        expected = {"completed": DeliveryState.COMPLETED, "blocked": DeliveryState.BLOCKED}
        assert run.state == expected.get(outcome, DeliveryState.FAILED)
        assert run.finished_at is not None
    else:
        assert service.run_store.list(workspace) == ()
        assert "claimed Story receipt" in output.err

    if outcome in {"completed", "blocked"}:

        def unexpected_runner(_config: AgentConfig) -> StoryRunner:
            pytest.fail("A Story with an existing receipt must not start Codex again.")

        monkeypatch.setattr("lumon.cli.commands.delivery.create_agent_runner", unexpected_runner)
        assert main(["delivery", "poll", "--workspace", str(workspace), "--json"]) == 0
        assert '"status": "idle"' in capsys.readouterr().out
        assert service.run_store.list_polls(workspace)[0].state == "idle"


def test_schedule_expression_supports_interval_and_weekdays() -> None:
    assert launchd_timing("*/5 * * * *") == {"StartInterval": 300}
    assert launchd_timing("0 9 * * 1-5") == {
        "StartCalendarInterval": [
            {"Hour": 9, "Minute": 0, "Weekday": 1},
            {"Hour": 9, "Minute": 0, "Weekday": 2},
            {"Hour": 9, "Minute": 0, "Weekday": 3},
            {"Hour": 9, "Minute": 0, "Weekday": 4},
            {"Hour": 9, "Minute": 0, "Weekday": 5},
        ]
    }


def test_schedule_expression_rejects_unsupported_values() -> None:
    with pytest.raises(InvalidInputError):
        validate_schedule_expression("every five minutes")
    with pytest.raises(PreflightError, match="numeric minute"):
        launchd_timing("0 9-17 * * *")
