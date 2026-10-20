"""Hermetic native protocol tests: no accounts, model calls, Git pushes or Feishu."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import cast

import pytest

from lumon.agents.agent.steering_policy import steering_policy
from lumon.tools.codex import CodexRequest, CodexTool
from lumon.tools.codex_app_server import execute_steerable
from lumon.tools.steering import SteeringControl, SteeringInput

_SERVER = r"""
import json, os, subprocess, sys
from pathlib import Path
root = Path(os.environ['TEST_ROOT'])
mode = os.environ.get('TEST_MODE', 'steer')
turn = 0
child = None
def send(data):
    print(json.dumps(data), flush=True)
def reply(req, result):
    send({'id': req['id'], 'result': result})
def done(status='completed'):
    send({'method': 'turn/completed', 'params': {
        'threadId': 'thread-1', 'turn': {'id': 'turn-'+str(turn), 'status': status}}})
def finish(text):
    send({'method': 'item/completed', 'params': {'threadId':'thread-1',
        'turnId': 'turn-'+str(turn), 'item': {
        'type':'agentMessage', 'id':'answer', 'text':text, 'phase':'final_answer'}}})
    done()
for line in sys.stdin:
    req = json.loads(line)
    with (root/'requests').open('a') as f:
        f.write(json.dumps(req)+'\n')
    method = req['method']
    if method == 'initialized': continue
    if mode == 'invalid':
        print('private token=do-not-expose', flush=True)
        sys.exit(1)
    if method == 'initialize': reply(req, {})
    elif method in ('thread/start', 'thread/resume'):
        reply(req, {'thread': {'id':'thread-1'}})
    elif method == 'turn/start':
        turn += 1
        if mode == 'early':
            finish('early answer')
            reply(req, {'turn': {'id':'turn-'+str(turn)}})
            continue
        if mode == 'unrelated':
            send({'method':'turn/completed','params':{'threadId':'thread-1',
                'turn':{'id':'other-turn','status':'failed'}}})
        reply(req, {'turn': {'id':'turn-'+str(turn)}})
        if mode == 'eof': sys.exit(0)
        if turn > 1 or mode in ('immediate','unrelated'): finish('updated answer')
        else:
            if mode in ('child', 'ignore_interrupt'):
                child = subprocess.Popen([sys.executable, '-c',
                    "import time; from pathlib import Path; time.sleep(2); "
                    + "Path("+repr(str(root/'would-push'))+").write_text('stale push')"])
                (root/'child-pid').write_text(str(child.pid))
            send({'method':'item/started','params':{'threadId':'thread-1',
                'turnId':'turn-1','item':{'type':'commandExecution','id':'cmd-1',
                'command':'prepare then publish'}}})
    elif method == 'turn/steer':
        if mode == 'rpc_error':
            send({'id':req['id'],'error':{'code':-32601,'message':'token=do-not-expose'}})
        elif mode == 'stale':
            send({'id':req['id'],'error':{'code':-32600,'message':'turn ended'}})
            finish('first answer')
        elif mode == 'wrong_turn': reply(req, {'turnId':'other-turn'})
        else:
            reply(req, {'turnId':'turn-'+str(turn)})
            finish('updated answer')
    elif method == 'turn/interrupt':
        if mode == 'ignore_interrupt':
            reply(req, {})
            continue
        if child is not None:
            child.kill()
            child.wait()
        reply(req, {})
        done('interrupted')
"""


def fake_tool(tmp_path: Path, mode: str = "steer", timeout: float = 5) -> CodexTool:
    script = tmp_path / "fake-codex"
    script.write_text(f"#!{sys.executable}\n" + _SERVER, encoding="utf-8")
    script.chmod(0o700)
    return CodexTool(
        binary=str(script),
        timeout_seconds=timeout,
        environment={
            "TEST_ROOT": str(tmp_path),
            "TEST_MODE": mode,
        },
    )


def requests(tmp_path: Path) -> list[dict[str, object]]:
    return [
        cast(dict[str, object], json.loads(line))
        for line in (tmp_path / "requests").read_text().splitlines()
    ]


def test_native_steering_updates_same_turn_and_accepts_images(tmp_path: Path) -> None:
    tool = fake_tool(tmp_path)

    async def run() -> None:
        control = SteeringControl()
        started = asyncio.Event()

        async def observe(_event: object) -> None:
            started.set()

        execution = asyncio.create_task(
            execute_steerable(
                tool,
                CodexRequest(tmp_path, "original request"),
                control,
                observe,
            )
        )
        await asyncio.wait_for(started.wait(), 3)
        receipt = control.submit(SteeringInput("new instruction", (tmp_path / "image.png",)))
        assert receipt is not None and await asyncio.wait_for(receipt, 3)
        result = await execution
        assert result.status == "succeeded"
        assert result.final_text == "updated answer"
        assert result.agent_session_id == "thread-1"
        assert control.closed

    asyncio.run(run())
    calls = requests(tmp_path)
    assert len([r for r in calls if r["method"] == "turn/start"]) == 1
    steer = next(r for r in calls if r["method"] == "turn/steer")
    params = cast(dict[str, object], steer["params"])
    assert params["expectedTurnId"] == "turn-1"
    assert params["threadId"] == "thread-1"
    assert params["input"] == [
        {"type": "text", "text": "new instruction"},
        {"type": "localImage", "path": str(tmp_path / "image.png")},
    ]


@pytest.mark.parametrize("policy", ["pause", "resume"])
def test_safety_control_interrupts_before_starting_replacement(tmp_path: Path, policy: str) -> None:
    tool = fake_tool(tmp_path, "child")

    async def run() -> None:
        control = SteeringControl()
        started = asyncio.Event()

        async def observe(_event: object) -> None:
            started.set()

        task = asyncio.create_task(
            execute_steerable(
                tool,
                CodexRequest(tmp_path, "commit and push later"),
                control,
                observe,
            )
        )
        await asyncio.wait_for(started.wait(), 3)
        receipt = control.submit(
            SteeringInput("先不要 commit/push", policy="pause" if policy == "pause" else "resume")
        )
        assert receipt is not None and await asyncio.wait_for(receipt, 3)
        assert (await task).status == "succeeded"
        await asyncio.sleep(2.1)
        assert not (tmp_path / "would-push").exists()

    asyncio.run(run())
    calls = requests(tmp_path)
    methods = [r["method"] for r in calls]
    starts = [r for r in calls if r["method"] == "turn/start"]
    assert len(starts) == 2
    assert methods.index("turn/interrupt") < len(methods) - 1
    replacement = cast(dict[str, object], starts[1]["params"])
    assert replacement["sandboxPolicy"] == (
        {"type": "readOnly", "networkAccess": False}
        if policy == "pause"
        else {"type": "dangerFullAccess"}
    )


@pytest.mark.parametrize("mode", ["rpc_error", "wrong_turn", "invalid", "eof"])
def test_protocol_failure_is_safe_and_releases_pending_inputs(tmp_path: Path, mode: str) -> None:
    tool = fake_tool(tmp_path, mode)

    async def run() -> None:
        control = SteeringControl()
        receipt = control.submit(SteeringInput("new input"))
        result = await execute_steerable(tool, CodexRequest(tmp_path, "request"), control)
        assert result.status == "failed"
        assert receipt is not None and receipt.done()
        assert "do-not-expose" not in str(result)

    asyncio.run(run())


def test_turn_completion_race_returns_unaccepted_input_for_next_turn(tmp_path: Path) -> None:
    async def run() -> None:
        control = SteeringControl()
        receipt = control.submit(SteeringInput("next"))
        result = await execute_steerable(
            fake_tool(tmp_path, "stale"), CodexRequest(tmp_path, "first"), control
        )
        assert result.status == "succeeded"
        assert receipt is not None and not await receipt

    asyncio.run(run())


def test_timeout_kills_owned_tools(tmp_path: Path) -> None:
    async def run() -> None:
        result = await execute_steerable(
            fake_tool(tmp_path, "child", timeout=0.3),
            CodexRequest(tmp_path, "wait"),
            SteeringControl(),
        )
        assert result.status == "timed_out"
        await asyncio.sleep(2.1)
        assert not (tmp_path / "would-push").exists()

    asyncio.run(run())


def test_unconfirmed_interrupt_fails_closed_and_kills_stale_tool(tmp_path: Path) -> None:
    async def run() -> None:
        control = SteeringControl()
        started = asyncio.Event()

        async def observe(_event: object) -> None:
            started.set()

        task = asyncio.create_task(
            execute_steerable(
                fake_tool(tmp_path, "ignore_interrupt"),
                CodexRequest(tmp_path, "wait"),
                control,
                observe,
            )
        )
        await asyncio.wait_for(started.wait(), 3)
        receipt = control.submit(SteeringInput("/pause", policy="pause"))
        result = await asyncio.wait_for(task, 4)
        assert result.status != "succeeded"
        assert receipt is not None and not await receipt
        await asyncio.sleep(2.1)
        assert not (tmp_path / "would-push").exists()

    asyncio.run(run())


@pytest.mark.parametrize(
    "text",
    [
        "先不要 commit／push",
        "不要提交和推送",
        "Don't push yet",
        "commit 和 push 先別做",
        "/pause",
        "停止",
    ],
)
def test_publication_hold_detection(text: str) -> None:
    assert steering_policy(text) == "pause"


@pytest.mark.parametrize("text", ["Also add tests", "請使用綠色按鈕", "Please commit and push"])
def test_ordinary_followups_do_not_change_permissions(text: str) -> None:
    assert steering_policy(text) is None


def test_resume_requires_explicit_command() -> None:
    assert steering_policy("/resume 繼續目前任務") == "resume"


def test_mailbox_close_and_saturation_do_not_falsely_acknowledge() -> None:
    async def run() -> None:
        control = SteeringControl()
        receipts = [control.submit(SteeringInput(str(i))) for i in range(32)]
        assert control.submit(SteeringInput("overflow")) is None
        control.close()
        assert all(r is not None and r.done() and not r.result() for r in receipts)
        assert control.submit(SteeringInput("closed")) is None

    asyncio.run(run())


@pytest.mark.parametrize("mode", ["early", "unrelated"])
def test_notifications_are_matched_to_exact_turn_even_before_start_reply(
    tmp_path: Path, mode: str
) -> None:
    result = asyncio.run(
        execute_steerable(
            fake_tool(tmp_path, mode),
            CodexRequest(tmp_path, "inspect"),
            SteeringControl(),
        )
    )
    assert result.status == "succeeded"
    assert result.final_text == ("early answer" if mode == "early" else "updated answer")


def test_callback_failure_does_not_leave_execution_running_or_leak_text(tmp_path: Path) -> None:
    async def run() -> None:
        async def failing(_event: object) -> None:
            raise RuntimeError("private content must not appear")

        result = await execute_steerable(
            fake_tool(tmp_path), CodexRequest(tmp_path, "inspect"), SteeringControl(), failing
        )
        assert result.status == "failed"
        assert "private content" not in str(result)

    asyncio.run(run())


def test_paused_session_resume_preserves_permissions_in_protocol(tmp_path: Path) -> None:
    result = asyncio.run(
        execute_steerable(
            fake_tool(tmp_path, "immediate"),
            CodexRequest(tmp_path, "inspect only", resume_session_id="thread-1"),
            SteeringControl(policy="pause"),
        )
    )
    assert result.status == "succeeded"
    calls = requests(tmp_path)
    resume = next(c for c in calls if c["method"] == "thread/resume")
    assert cast(dict[str, object], resume["params"])["threadId"] == "thread-1"
    turn = next(c for c in calls if c["method"] == "turn/start")
    assert cast(dict[str, object], turn["params"])["sandboxPolicy"] == {
        "type": "readOnly",
        "networkAccess": False,
    }
