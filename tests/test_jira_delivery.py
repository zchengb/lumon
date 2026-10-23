"""Hermetic tests for zero-Agent Jira trigger detection."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

from lumon.errors import PreflightError
from lumon.tools.jira_delivery import JiraDeliveryTrigger


def _issue(key: str = "TEST-1") -> dict[str, object]:
    return {"key": key, "summary": "A small Story without a Technical Plan"}


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
        "query = sys.argv[sys.argv.index('--jql') + 1]\n"
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
        "    reply = {'data': pages[0]}\n"
        "    if mode == 'denied': reply['errors'] = ['secret-value']\n"
        "    print(json.dumps(reply))\n",
        encoding="utf-8",
    )
    script.chmod(0o700)
    return JiraDeliveryTrigger(binary=str(script), timeout_seconds=5, environment={})


def test_read_only_detection_excludes_receipts_on_server(tmp_path: Path) -> None:
    trigger = _fake_twg(
        tmp_path,
        [
            {"issues": [_issue("TEST-2")]},
        ],
    )
    jql = 'project = TEST AND summary ~ "order by $(untrusted)" ORDER BY Rank ASC'
    candidate = asyncio.run(
        trigger.find_candidate("test.atlassian.net", jql, excluded_keys=frozenset({"TEST-1"}))
    )
    assert candidate is not None
    assert candidate.key == "TEST-2"
    assert candidate.url == "https://test.atlassian.net/browse/TEST-2"
    requests = [json.loads(line) for line in (tmp_path / "requests").read_text().splitlines()]
    assert len(requests) == 1
    expected = (
        '(project = TEST AND summary ~ "order by $(untrusted)") '
        "AND key NOT IN (TEST-1) ORDER BY Rank ASC"
    )
    assert requests[0]["query"] == expected
    assert requests[0]["args"] == [
        "jira",
        "workitem",
        "query",
        "--jql",
        expected,
        "--fields",
        "summary",
        "--first",
        "1",
        "--site",
        "test.atlassian.net",
        "--output",
        "json",
        "--output-summary",
        "none",
    ]


def test_empty_server_filtered_search_is_idle(tmp_path: Path) -> None:
    trigger = _fake_twg(tmp_path, [{"issues": []}])
    assert (
        asyncio.run(
            trigger.find_candidate(
                "test.atlassian.net", "project = TEST", excluded_keys=frozenset({"TEST-1"})
            )
        )
        is None
    )


@pytest.mark.parametrize(
    ("jql", "expected"),
    [
        (
            "project = TEST OR project = OTHER",
            "(project = TEST OR project = OTHER) AND key NOT IN (TEST-1)",
        ),
        (
            'summary ~ "say \\"order by\\"" order by updated DESC',
            '(summary ~ "say \\"order by\\"") AND key NOT IN (TEST-1) order by updated DESC',
        ),
        (
            "summary ~ 'order by' ORDER BY Rank",
            "(summary ~ 'order by') AND key NOT IN (TEST-1) ORDER BY Rank",
        ),
    ],
)
def test_receipt_exclusion_preserves_jql_precedence_and_quotes(
    tmp_path: Path, jql: str, expected: str
) -> None:
    trigger = _fake_twg(tmp_path, [{"issues": []}])
    asyncio.run(
        trigger.find_candidate("test.atlassian.net", jql, excluded_keys=frozenset({"TEST-1"}))
    )
    assert json.loads((tmp_path / "requests").read_text())["query"] == expected


def test_excluded_result_is_rejected(tmp_path: Path) -> None:
    trigger = _fake_twg(tmp_path, [{"issues": [_issue()]}])
    with pytest.raises(PreflightError):
        asyncio.run(
            trigger.find_candidate(
                "test.atlassian.net", "project = TEST", excluded_keys=frozenset({"TEST-1"})
            )
        )


def test_invalid_receipt_does_not_start_query(tmp_path: Path) -> None:
    trigger = _fake_twg(tmp_path, [{"issues": []}])
    with pytest.raises(PreflightError):
        asyncio.run(
            trigger.find_candidate(
                "test.atlassian.net",
                "project = TEST",
                excluded_keys=frozenset({"TEST-1) OR key = TEST-2"}),
            )
        )
    assert not (tmp_path / "requests").exists()


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
        {},
        {"issues": [_issue("../../TEST-1")]},
        {"issues": [_issue(), _issue("TEST-2")]},
        {"issues": [{"key": "TEST-1", "summary": ""}]},
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
    trigger.timeout_seconds = 5 if cancel else 2

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


@pytest.mark.parametrize(
    "mode,expected",
    [
        ("new", True),
        ("old", False),
        ("unrelated", False),
        ("app", False),
        ("ineligible", False),
        ("same-status", False),
        ("next-page", True),
        ("consumed", False),
    ],
)
def test_jira_reentry_requires_new_status_event_and_all_current_gates(
    tmp_path: Path, mode: str, expected: bool
) -> None:
    fake = tmp_path / "twg-reentry"
    fake.write_text(
        f"#!{sys.executable}\n"
        "import json,sys\n"
        f"mode = {mode!r}\n"
        "if sys.argv[3] == 'get':\n"
        "    reply = {'data': [{'key': 'TEST-1', 'status': {'id': '10036'}}]}\n"
        "elif sys.argv[3] == 'query':\n"
        "    jql = sys.argv[sys.argv.index('--jql')+1]\n"
        "    expected = '(project = TEST AND status = 10036 AND Flagged = Impediment)'\n"
        "    assert jql == expected + ' AND key = TEST-1'\n"
        "    issues = [] if mode == 'ineligible' else [{'key': 'TEST-1', 'summary': 'Test'}]\n"
        "    reply = {'data': {'issues': issues}}\n"
        "else:\n"
        "    created = '2026-10-23T11:00:00+0800' if mode == 'old' "
        "else '2026-10-23T13:00:00+0800'\n"
        "    item = {'field': 'summary' if mode == 'unrelated' else 'status', "
        "'from': '10036' if mode == 'same-status' else '10269', 'to': '10036'}\n"
        "    author = {'accountType': 'app' if mode == 'app' else 'atlassian'}\n"
        "    entry = {'id': '1', 'created': created, 'items': [item], 'author': author}\n"
        "    more = mode == 'next-page' and '--after' not in sys.argv\n"
        "    info = {'hasNextPage': more, 'nextCursor': '100' if more else None}\n"
        "    reply = {'data': [] if more else [entry], 'pageInfo': info}\n"
        "print(json.dumps(reply))\n",
        encoding="utf-8",
    )
    fake.chmod(0o700)
    trigger = JiraDeliveryTrigger(str(fake), environment={})
    result = asyncio.run(
        trigger.reentered(
            "test.atlassian.net",
            "project = TEST AND status = 10036 AND Flagged = Impediment ORDER BY Rank ASC",
            "TEST-1",
            finished_at=datetime(2026, 10, 23, 4, tzinfo=UTC),
            consumed_event_id="1" if mode == "consumed" else None,
        )
    )
    assert (result is not None) == expected
    if result is not None:
        assert result.reentry_id == "1"


def test_partial_jira_reentry_history_fails_closed(tmp_path: Path) -> None:
    fake = tmp_path / "partial-twg"
    fake.write_text(
        f"#!{sys.executable}\n"
        "import json,sys\n"
        "if sys.argv[3] == 'query':\n"
        "    print(json.dumps({'data': {'issues': [{'key': 'TEST-1', 'summary': 'Test'}]}}))\n"
        "elif sys.argv[3] == 'get':\n"
        "    print(json.dumps({'data': [{'key': 'TEST-1','status': {'id': '10036'}}]}))\n"
        "else:\n"
        "    print(json.dumps({'data': [], 'pageInfo': "
        "{'hasNextPage': True, 'nextCursor': None}}))\n",
        encoding="utf-8",
    )
    fake.chmod(0o700)
    trigger = JiraDeliveryTrigger(str(fake), environment={})
    with pytest.raises(PreflightError, match="not resumed"):
        asyncio.run(
            trigger.reentered(
                "test.atlassian.net",
                "project = TEST AND status = 10036",
                "TEST-1",
                finished_at=datetime(2026, 10, 23, tzinfo=UTC),
            )
        )
