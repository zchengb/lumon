"""Hermetic tests for Codex catalog discovery and its subprocess boundary."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

import pytest

from lumon.errors import AgentRuntimeError
from lumon.tools.codex_models import CodexModelCatalog


def _model(model: str = "future-model", *, hidden: bool = False) -> dict[str, object]:
    return {
        "model": model,
        "displayName": f"Display {model}",
        "description": "A model from the local catalog.",
        "hidden": hidden,
        "defaultReasoningEffort": "adaptive",
        "supportedReasoningEfforts": [
            {"reasoningEffort": "none", "description": "No reasoning"},
            {"reasoningEffort": "adaptive", "description": "Provider-defined effort"},
        ],
        "isDefault": True,
    }


def _fake_codex(
    tmp_path: Path,
    pages: list[dict[str, object]],
    *,
    mode: str = "success",
) -> CodexModelCatalog:
    script = tmp_path / "fake-codex"
    script.write_text(
        f"#!{sys.executable}\n"
        "import json, os, sys, time\n"
        "from pathlib import Path\n"
        f"root = Path({str(tmp_path)!r})\n"
        "(root / 'pid').write_text(str(os.getpid()))\n"
        f"pages = json.loads({json.dumps(pages)!r})\n"
        f"mode = {mode!r}\n"
        "page_number = 0\n"
        "for line in sys.stdin:\n"
        "    request = json.loads(line)\n"
        "    with (root / 'requests').open('a') as log:\n"
        "        log.write(json.dumps(request) + '\\n')\n"
        "    if mode == 'timeout':\n"
        "        time.sleep(60)\n"
        "    if request['method'] == 'initialized':\n"
        "        continue\n"
        "    if request['method'] == 'initialize':\n"
        "        reply = {'id': request['id'], 'result': {}}\n"
        "    elif mode == 'provider_error':\n"
        "        print('app_secret=secret-value', file=sys.stderr, flush=True)\n"
        "        reply = {'id': request['id'], 'error': {'message': 'secret-value'}}\n"
        "    elif mode == 'invalid_json':\n"
        "        print('secret-value invalid json', flush=True)\n"
        "        continue\n"
        "    elif mode == 'exit':\n"
        "        sys.exit(7)\n"
        "    else:\n"
        "        print(json.dumps({'method': 'notice'}), flush=True)\n"
        "        print(json.dumps({'id': 'unrelated', 'result': {}}), flush=True)\n"
        "        reply = {'id': request['id'], 'result': pages[page_number]}\n"
        "        page_number += 1\n"
        "    print(json.dumps(reply), flush=True)\n",
        encoding="utf-8",
    )
    script.chmod(0o700)
    return CodexModelCatalog(binary=str(script), timeout_seconds=5, environment={})


def test_catalog_paginates_filters_hidden_and_retains_provider_efforts(tmp_path: Path) -> None:
    catalog = _fake_codex(
        tmp_path,
        [
            {"data": [_model(), _model("hidden", hidden=True)], "nextCursor": "next"},
            {"data": [_model(), _model("second")], "nextCursor": None},
        ],
    )

    models = asyncio.run(catalog.list_models())

    assert [model.model for model in models] == ["future-model", "second"]
    assert models[0].display_name == "Display future-model"
    assert models[0].description == "A model from the local catalog."
    assert models[0].default_reasoning_effort == "adaptive"
    assert models[0].supported_reasoning_efforts == ("none", "adaptive")
    requests = [json.loads(line) for line in (tmp_path / "requests").read_text().splitlines()]
    assert [request["method"] for request in requests] == [
        "initialize",
        "initialized",
        "model/list",
        "model/list",
    ]
    assert requests[0]["params"]["clientInfo"]["name"] == "lumon"
    assert requests[2]["params"] == {"limit": 100, "includeHidden": False, "cursor": None}
    assert requests[3]["params"]["cursor"] == "next"
    with pytest.raises(ProcessLookupError):
        os.kill(int((tmp_path / "pid").read_text()), 0)


def test_catalog_can_be_empty(tmp_path: Path) -> None:
    catalog = _fake_codex(tmp_path, [{"data": [], "nextCursor": None}])
    assert asyncio.run(catalog.list_models()) == ()


@pytest.mark.parametrize("mode", ["provider_error", "invalid_json", "exit"])
def test_catalog_errors_do_not_expose_provider_diagnostics(tmp_path: Path, mode: str) -> None:
    catalog = _fake_codex(tmp_path, [], mode=mode)
    with pytest.raises(AgentRuntimeError) as error:
        asyncio.run(catalog.list_models())
    assert "secret-value" not in str(error.value)
    assert "Codex" in str(error.value)


@pytest.mark.parametrize(
    "changes",
    [
        {"defaultReasoningEffort": "unsupported"},
        {"supportedReasoningEfforts": []},
        {"defaultReasoningEffort": "unsafe token"},
        {"supportedReasoningEfforts": [{"reasoningEffort": "unsafe token"}]},
        {"model": "unsafe\nmodel"},
    ],
)
def test_invalid_model_metadata_is_rejected_safely(
    tmp_path: Path, changes: dict[str, object]
) -> None:
    catalog = _fake_codex(tmp_path, [{"data": [{**_model(), **changes}]}])
    with pytest.raises(AgentRuntimeError, match="invalid model catalog"):
        asyncio.run(catalog.list_models())


def test_repeated_cursor_is_bounded(tmp_path: Path) -> None:
    catalog = _fake_codex(tmp_path, [{"data": [], "nextCursor": "loop"}] * 2)
    with pytest.raises(AgentRuntimeError, match="repeated catalog pages"):
        asyncio.run(catalog.list_models())


def test_missing_binary_has_an_actionable_safe_error(tmp_path: Path) -> None:
    catalog = CodexModelCatalog(binary=str(tmp_path / "secret-value"))
    with pytest.raises(AgentRuntimeError, match="local Codex installation") as error:
        asyncio.run(catalog.list_models())
    assert "secret-value" not in str(error.value)


@pytest.mark.parametrize("cancel", [False, True])
def test_timeout_and_cancellation_reap_the_catalog_process(tmp_path: Path, cancel: bool) -> None:
    catalog = _fake_codex(tmp_path, [], mode="timeout")
    catalog.timeout_seconds = 5 if cancel else 0.5

    async def discover() -> None:
        task = asyncio.create_task(catalog.list_models())
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
            with pytest.raises(AgentRuntimeError, match="timed out"):
                await task

    asyncio.run(discover())
    with pytest.raises(ProcessLookupError):
        os.kill(int((tmp_path / "pid").read_text()), 0)
