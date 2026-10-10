"""Built-in automation workflows are packaged documents, not Dashboard settings."""

from pathlib import Path

import pytest

from lumon.agents.agent.prompt import render_automation_prompt
from lumon.errors import AgentConfigError
from lumon.workspace.settings import DeliveryPublishMode


def test_delivery_document_preserves_literal_hook_text_and_lifecycle() -> None:
    instructions = "Check approved Stories.\n\nKeep $variables and {braces} literal."
    prompt = render_automation_prompt(
        "auto_delivery.md",
        instructions=instructions,
        poll_id="poll-123",
        candidate='{"key": "TEST-1"}',
        jira_site="test.atlassian.net",
        trigger_jql='"project = TEST"',
        publish_mode="local",
        target_branch="registered branch",
    )
    assert instructions in prompt
    assert "--poll-id poll-123" in prompt
    assert "AUTO_DELIVERY_IDLE" in prompt
    assert "exactly one terminal command" in prompt
    assert "$instructions" not in prompt


@pytest.mark.parametrize("mode", list(DeliveryPublishMode))
def test_delivery_uses_explicit_policy_and_selected_story(mode: DeliveryPublishMode) -> None:
    prompt = render_automation_prompt(
        "auto_delivery.md",
        instructions="Legacy local-only instructions.",
        poll_id="poll-123",
        candidate='{"key": "TEST-1"}',
        jira_site="test.atlassian.net",
        trigger_jql='"project = TEST AND Flagged = Impediment"',
        publish_mode=mode,
        target_branch='"release"',
    )
    assert f"Saved publish mode: {mode}" in prompt
    assert 'Target/base branch: "release"' in prompt
    assert "Technical Plan is optional" in prompt
    assert "Preserve the opt-in Flag" in prompt
    assert "supersedes older hook text" in prompt
    assert "normal fast-forward push" in prompt
    assert "lumon/delivery-<Story-key>" in prompt
    assert "codex/delivery-" not in prompt
    assert "Do not scan the entire backlog again" in " ".join(prompt.split())
    assert '"key": "TEST-1"' in prompt


@pytest.mark.parametrize("contents", [None, " \n ", "$missing", "$invalid-placeholder"])
def test_unavailable_or_invalid_document_fails_safely(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, contents: str | None
) -> None:
    if contents is not None:
        (tmp_path / "auto_scan.md").write_text(contents, encoding="utf-8")

    def template_directory(_package: str) -> Path:
        return tmp_path

    monkeypatch.setattr("lumon.agents.agent.prompt.files", template_directory)
    with pytest.raises(AgentConfigError, match="Packaged") as failure:
        render_automation_prompt("auto_scan.md", lookback_days="14", result_path="private-path")
    assert "private-path" not in str(failure.value)
