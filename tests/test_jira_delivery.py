"""Hermetic tests for zero-Agent Jira trigger detection."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

import pytest

from lumon.errors import PreflightError
from lumon.tools.jira_delivery import JiraDeliveryTrigger


def _issue(key: str = "TEST-1") -> dict[str, object]:
    return {"key": key, "fields": {"summary": "A small Story without a Technical Plan"}}


def _fake_twg(
    tmp_path: Path, pages: list[dict[str, object]], *, mode: str = "success"
) -> JiraDeliveryTrigger:
    script = tmp_path / "fake-twg"
    script.write_text(
        f"#!{sys.executable}\n"
        "import json, os, sys, time\n"
        "from pathlib import Path\n"
        f"root = Path({str(tmp_path)!r})\n"
        f"pages = json.loads({json.dumps(pages)!r})\n"
        f"mode = {mode!r}\n"
        "(root / 'pid').write_text(str(os.getpid()))\n"
        "query = json.load(sys.stdin)\n"
        "with (root / 'requests').open('a') as log:\n"
        "    log.write(json.dumps({'args': sys.argv[1:], 'query': query}) + '\\n')\n"
        "if mode == 'timeout':\n"
        "    time.sleep(60)\n"
        "if mode == 'exit':\n"
        "    print('app_secret=secret-value', file=sys.stderr)\n"
        "    sys.exit(7)\n"
        "if mode == 'invalid':\n"
        "    print('secret-value invalid JSON')\n"
        "elif mode == 'oversized':\n"
        "    print('x' * (1024 * 1024 + 1))\n"
        "else:\n"
        "    page = pages[1 if query.get('nextPageToken') else 0]\n"
        "    reply = {'data': {'status': 403 if mode == 'denied' else 200, 'body': page}}\n"
        "    print(json.dumps(reply))\n",
        encoding="utf-8",
    )
    script.chmod(0o700)
    return JiraDeliveryTrigger(binary=str(script), timeout_seconds=5, environment={})


def test_read_only_detection_paginates_past_existing_receipts(tmp_path: Path) -> None:
    trigger = _fake_twg(
        tmp_path,
        [
            {"issues": [_issue()], "isLast": False, "nextPageToken": "next"},
            {"issues": [_issue("TEST-2")], "isLast": True},
        ],
    )
    jql = 'project = TEST AND Flagged = Impediment AND summary ~ "$(untrusted)"'
    candidate = asyncio.run(
        trigger.find_candidate("test.atlassian.net", jql, excluded_keys=frozenset({"TEST-1"}))
    )
    assert candidate is not None
    assert candidate.key == "TEST-2"
    assert candidate.url == "https://test.atlassian.net/browse/TEST-2"
    requests = [json.loads(line) for line in (tmp_path / "requests").read_text().splitlines()]
    assert len(requests) == 2
    assert requests[0]["query"] == {"jql": jql, "fields": ["summary"], "maxResults": 100}
    assert requests[1]["query"]["nextPageToken"] == "next"
    assert requests[0]["args"] == [
        "api",
        "jira:/rest/api/3/search/jql",
        "--method",
        "POST",
        "--input",
        "-",
        "--site",
        "test.atlassian.net",
        "--output",
        "json",
        "--output-summary",
        "none",
    ]


@pytest.mark.parametrize("issues", [[], [_issue()]])
def test_empty_or_previously_claimed_search_is_idle(
    tmp_path: Path, issues: list[dict[str, object]]
) -> None:
    trigger = _fake_twg(tmp_path, [{"issues": issues, "isLast": True}])
    assert (
        asyncio.run(
            trigger.find_candidate(
                "test.atlassian.net", "project = TEST", excluded_keys=frozenset({"TEST-1"})
            )
        )
        is None
    )


@pytest.mark.parametrize("mode", ["denied", "invalid", "exit", "oversized"])
def test_detection_errors_are_safe_and_never_return_idle(tmp_path: Path, mode: str) -> None:
    trigger = _fake_twg(tmp_path, [{"issues": [], "isLast": True}], mode=mode)
    with pytest.raises(PreflightError) as error:
        asyncio.run(
            trigger.find_candidate(
                "test.atlassian.net", "project = TEST", excluded_keys=frozenset()
            )
        )
    assert "secret-value" not in str(error.value)
    with pytest.raises(ProcessLookupError):
        os.kill(int((tmp_path / "pid").read_text()), 0)


@pytest.mark.parametrize(
    "page",
    [
        {"issues": [], "isLast": False},
        {"issues": [], "isLast": False, "nextPageToken": "loop"},
        {"issues": []},
        {"issues": [_issue("../../TEST-1")], "isLast": True},
    ],
)
def test_incomplete_or_invalid_search_is_not_idle(tmp_path: Path, page: dict[str, object]) -> None:
    trigger = _fake_twg(tmp_path, [page, page])
    with pytest.raises(PreflightError):
        asyncio.run(
            trigger.find_candidate(
                "test.atlassian.net", "project = TEST", excluded_keys=frozenset()
            )
        )


@pytest.mark.parametrize("cancel", [False, True])
def test_timeout_and_cancellation_reap_twg(tmp_path: Path, cancel: bool) -> None:
    trigger = _fake_twg(tmp_path, [], mode="timeout")
    trigger.timeout_seconds = 5 if cancel else 0.5

    async def detect() -> None:
        task = asyncio.create_task(
            trigger.find_candidate(
                "test.atlassian.net", "project = TEST", excluded_keys=frozenset()
            )
        )
        if cancel:
            for _ in range(100):
                if (tmp_path / "requests").exists():
                    break
                await asyncio.sleep(0.01)
            assert (tmp_path / "requests").exists()
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        else:
            with pytest.raises(PreflightError, match="timed out"):
                await task

    asyncio.run(detect())
    with pytest.raises(ProcessLookupError):
        os.kill(int((tmp_path / "pid").read_text()), 0)


def test_missing_configuration_or_binary_is_reported_safely(tmp_path: Path) -> None:
    trigger = JiraDeliveryTrigger(binary=str(tmp_path / "secret-value"))
    for site, jql in [
        ("", ""),
        ("test.atlassian.net", ""),
        ("test.atlassian.net", "project = TEST"),
    ]:
        with pytest.raises(PreflightError) as error:
            asyncio.run(trigger.find_candidate(site, jql, excluded_keys=frozenset()))
        assert "secret-value" not in str(error.value)
