"""Hermetic update checks: no account access, upgrades, or real registry traffic."""

from __future__ import annotations

import asyncio
import json
import os
import sys
import urllib.error
from collections.abc import Callable
from email.message import Message
from pathlib import Path
from typing import Self
from urllib.request import Request

import pytest

from lumon.tools.codex_status import CodexCliStatus, CodexCliUpdateChecker, CodexCliUpdateStatus


@pytest.mark.parametrize(
    ("installed", "latest", "status"),
    [
        ("0.9.0", "0.10.0", "update_available"),
        ("0.156.1", "0.160.0", "update_available"),
        ("0.160.0", "0.160.0", "up_to_date"),
        ("0.161.0", "0.160.0", "up_to_date"),
        ("0.160.0-alpha.12.1", "0.160.0", "update_available"),
        ("0.161.0-alpha.12.1", "0.160.0", "up_to_date"),
        ("0.160.0+build.123", "0.160.0", "up_to_date"),
        ("0.160.0-alpha.1+build.123", "0.160.0", "update_available"),
    ],
)
def test_versions_are_compared_numerically_without_prerelease_downgrades(
    installed: str, latest: str, status: str
) -> None:
    checker = CodexCliUpdateChecker(
        binary="/test/codex", version_reader=lambda _: installed, latest_reader=lambda: latest
    )
    checked = asyncio.run(checker.check())
    assert checked == CodexCliStatus(CodexCliUpdateStatus(status), "/test/codex", installed, latest)


def test_latest_is_cached_but_installed_version_is_always_rechecked() -> None:
    now = [0.0]
    installed = ["0.1.0"]
    calls: list[str] = []

    def latest() -> str:
        calls.append("latest")
        return "0.2.0"

    checker = CodexCliUpdateChecker(
        binary="/test/codex",
        version_reader=lambda _: installed[0],
        latest_reader=latest,
        clock=lambda: now[0],
    )
    assert asyncio.run(checker.check()).status == "update_available"
    installed[0] = "0.2.0"
    now[0] = 599
    assert asyncio.run(checker.check()).status == "up_to_date"
    assert len(calls) == 1
    now[0] = 600
    asyncio.run(checker.check())
    assert len(calls) == 2
    asyncio.run(checker.check(refresh=True))
    assert len(calls) == 3


def test_registry_failure_has_a_short_cache_and_never_claims_cli_is_current() -> None:
    now = [0.0]
    calls: list[str] = []

    def latest() -> str:
        calls.append("latest")
        if len(calls) == 1:
            raise TimeoutError("secret-value")
        return "0.2.0"

    checker = CodexCliUpdateChecker(
        binary="/test/codex",
        version_reader=lambda _: "0.1.0",
        latest_reader=latest,
        clock=lambda: now[0],
    )
    checked = asyncio.run(checker.check())
    assert checked.status == "check_failed"
    assert checked.installed_version == "0.1.0"
    assert checked.latest_version is None
    assert "secret-value" not in repr(checked)
    now[0] = 59
    assert asyncio.run(checker.check()).status == "check_failed"
    assert len(calls) == 1
    now[0] = 60
    assert asyncio.run(checker.check()).status == "update_available"
    assert len(calls) == 2


def test_failed_forced_refresh_does_not_reuse_an_old_success() -> None:
    calls: list[str] = []

    def latest() -> str:
        calls.append("latest")
        if len(calls) > 1:
            raise urllib.error.URLError("secret-value")
        return "0.2.0"

    checker = CodexCliUpdateChecker(
        binary="/test/codex", version_reader=lambda _: "0.1.0", latest_reader=latest
    )
    assert asyncio.run(checker.check()).status == "update_available"
    assert asyncio.run(checker.check(refresh=True)).status == "check_failed"


def test_simultaneous_automatic_checks_share_one_registry_request() -> None:
    calls: list[str] = []

    def latest() -> str:
        calls.append("latest")
        return "0.2.0"

    checker = CodexCliUpdateChecker(
        binary="/test/codex", version_reader=lambda _: "0.1.0", latest_reader=latest
    )

    async def check_all() -> list[CodexCliStatus]:
        return await asyncio.gather(*(checker.check() for _ in range(5)))

    assert all(checked.status == "update_available" for checked in asyncio.run(check_all()))
    assert len(calls) == 1


def _fake_codex(tmp_path: Path, *, output: str, exit_code: int = 0, slow: bool = False) -> str:
    script = tmp_path / "codex"
    script.write_text(
        f"#!{sys.executable}\n"
        "import json, os, sys, time\n"
        "from pathlib import Path\n"
        f"root = Path({str(tmp_path)!r})\n"
        "(root / 'pid').write_text(str(os.getpid()))\n"
        "(root / 'args').write_text(json.dumps(sys.argv[1:]))\n"
        f"if {slow!r}: time.sleep(60)\n"
        "print('secret-value', file=sys.stderr)\n"
        f"print({output!r})\n"
        f"sys.exit({exit_code})\n",
        encoding="utf-8",
    )
    script.chmod(0o700)
    return str(script)


def test_version_probe_only_executes_version_and_reaps_the_process(tmp_path: Path) -> None:
    binary = _fake_codex(tmp_path, output="codex-cli 0.1.0")
    checker = CodexCliUpdateChecker(binary=binary, latest_reader=lambda: "0.2.0")
    assert asyncio.run(checker.check()).status == "update_available"
    assert json.loads((tmp_path / "args").read_text()) == ["--version"]
    with pytest.raises(ProcessLookupError):
        os.kill(int((tmp_path / "pid").read_text()), 0)


@pytest.mark.parametrize(
    ("output", "exit_code"),
    [("secret-value", 0), ("codex-cli secret-value", 0), ("codex-cli 0.1.0", 1)],
)
def test_invalid_cli_version_is_safe_and_does_not_request_registry(
    tmp_path: Path, output: str, exit_code: int
) -> None:
    binary = _fake_codex(tmp_path, output=output, exit_code=exit_code)

    def forbidden_latest() -> str:
        pytest.fail("Unavailable CLI must not request release metadata.")

    checked = asyncio.run(
        CodexCliUpdateChecker(binary=binary, latest_reader=forbidden_latest).check()
    )
    assert checked.status == "cli_unavailable"
    assert checked.installed_version is None
    assert "secret-value" not in repr(checked)


def test_missing_cli_does_not_attempt_model_discovery_or_registry(tmp_path: Path) -> None:
    def forbidden_latest() -> str:
        pytest.fail("Missing CLI must not request release metadata.")

    checked = asyncio.run(
        CodexCliUpdateChecker(
            binary=str(tmp_path / "missing-codex"), latest_reader=forbidden_latest
        ).check()
    )
    assert checked.status == "cli_unavailable"


def test_version_timeout_reaps_the_probe(tmp_path: Path) -> None:
    binary = _fake_codex(tmp_path, output="codex-cli 0.1.0", slow=True)
    checked = asyncio.run(CodexCliUpdateChecker(binary=binary).check())
    assert checked.status == "cli_unavailable"
    with pytest.raises(ProcessLookupError):
        os.kill(int((tmp_path / "pid").read_text()), 0)


class _Response:
    def __init__(self, payload: bytes, status: int = 200) -> None:
        self.payload = payload
        self.status = status
        self.closed = False
        self.read_limit = 0

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        self.closed = True

    def read(self, amount: int) -> bytes:
        self.read_limit = amount
        return self.payload[:amount]


def _registry_checker(
    monkeypatch: pytest.MonkeyPatch, opener: Callable[[Request, float], _Response]
) -> CodexCliUpdateChecker:
    def open_metadata(request: Request, *, timeout: float) -> _Response:
        return opener(request, timeout)

    monkeypatch.setattr("lumon.tools.codex_status.urllib.request.urlopen", open_metadata)
    return CodexCliUpdateChecker(binary="/test/codex", version_reader=lambda _: "0.1.0")


def test_registry_uses_only_fixed_public_package_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    response = _Response(b'{"version": "0.2.0", "extra_npm_metadata": {}}')

    def opener(request: Request, timeout: float) -> _Response:
        assert request.full_url == "https://registry.npmjs.org/@openai/codex/latest"
        assert request.get_method() == "GET"
        assert request.get_header("Authorization") is None
        assert request.data is None
        assert timeout == 5
        return response

    checked = asyncio.run(_registry_checker(monkeypatch, opener).check())
    assert checked.latest_version == "0.2.0"
    assert response.closed
    assert response.read_limit == 65_537


@pytest.mark.parametrize(
    "payload",
    [
        b"secret-value",
        b"{}",
        b"[]",
        b'{"version": null}',
        b'{"version": 2}',
        b'{"version": "0.2.0-alpha.1"}',
        b'{"version": "secret-value"}',
        b"x" * 65_537,
    ],
    ids=["invalid-json", "missing", "array", "null", "number", "prerelease", "unsafe", "oversized"],
)
def test_invalid_registry_metadata_is_safely_unknown(
    monkeypatch: pytest.MonkeyPatch, payload: bytes
) -> None:
    response = _Response(payload)
    checker = _registry_checker(monkeypatch, lambda _request, _timeout: response)
    checked = asyncio.run(checker.check())
    assert checked.status == "check_failed"
    assert checked.installed_version == "0.1.0"
    assert checked.latest_version is None
    assert "secret-value" not in repr(checked)
    assert response.closed


@pytest.mark.parametrize("http_status", [201, 403, 429, 500])
def test_registry_http_errors_leave_models_and_settings_independent(
    monkeypatch: pytest.MonkeyPatch, http_status: int
) -> None:
    response = _Response(b"secret-value", status=http_status)
    checked = asyncio.run(
        _registry_checker(monkeypatch, lambda _request, _timeout: response).check()
    )
    assert checked.status == "check_failed"
    assert response.closed


def test_registry_transport_error_is_safely_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    def opener(_: Request, timeout: float) -> _Response:
        del timeout
        raise urllib.error.HTTPError("secret-value", 403, "secret-value", Message(), None)

    checked = asyncio.run(_registry_checker(monkeypatch, opener).check())
    assert checked.status == "check_failed"
    assert "secret-value" not in repr(checked)
