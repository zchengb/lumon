"""Command previews redact before truncating or persisting."""

import pytest

from lumon.tools.safety import sanitize_command


@pytest.mark.parametrize(
    "command, hidden",
    [
        ("tool --password 'two word secret' --verbose", "two word secret"),
        ('tool --api-key="hidden"', "hidden"),
        ('API_TOKEN="hidden with spaces" npm test', "hidden with spaces"),
        ('curl -H "Authorization: Bearer hidden" https://example.com', "hidden"),
        ("curl https://user:hidden@example.com", "hidden"),
        ("curl -u user:hidden https://example.com", "hidden"),
        ('curl -H "Authorization: Basic hidden" https://example.com', "hidden"),
        ("python -c \"print('private prompt')\"", "private prompt"),
        ('tool --prompt "private prompt contents"', "private prompt contents"),
        ('tool --data \'{"password":"hidden"}\'', "hidden"),
        ("cat <<'EOF'\nprivate prompt\nEOF", "private prompt"),
        ("cat -----BEGIN PRIVATE KEY-----\nhidden\n-----END PRIVATE KEY-----", "hidden"),
        ("curl https://open.feishu.cn/open-apis/bot/v2/hook/hidden", "hidden"),
    ],
)
def test_command_preview_redacts_sensitive_arguments(command: str, hidden: str) -> None:
    assert hidden not in sanitize_command(command)


def test_command_preview_preserves_commands_and_marks_truncation() -> None:
    assert sanitize_command("git status --short; npm test") == "git status --short; npm test"
    preview = sanitize_command("驗" * 1000)
    assert preview.endswith(" … [truncated]")
    assert len(preview.encode("utf-8")) < 1100
    assert sanitize_command(preview) == preview
