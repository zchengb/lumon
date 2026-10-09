"""Read Jira trigger candidates through TWG, without starting an Agent turn."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from lumon.errors import PreflightError
from lumon.workspace.settings import validate_delivery_jira_site, validate_delivery_jql


@dataclass(frozen=True, slots=True)
class JiraDeliveryCandidate:
    """One validated Story identity; Jira content does not authorize additional work."""

    key: str
    title: str
    url: str


class _Fields(BaseModel):
    model_config = ConfigDict(strict=True)

    summary: str = Field(min_length=1, max_length=500)


class _Issue(BaseModel):
    model_config = ConfigDict(strict=True)

    key: str = Field(pattern=r"^[A-Z][A-Z0-9_]*-[1-9][0-9]*$", max_length=128)
    fields: _Fields


class _Page(BaseModel):
    model_config = ConfigDict(strict=True)

    issues: list[_Issue] = Field(max_length=100)
    is_last: bool = Field(alias="isLast")
    next_token: str | None = Field(default=None, alias="nextPageToken", max_length=4096)


class _ResponseData(BaseModel):
    model_config = ConfigDict(strict=True)

    status: int
    body: dict[str, object]


class _Response(BaseModel):
    model_config = ConfigDict(strict=True)

    data: _ResponseData


class JiraDeliveryTrigger:
    """Bounded read-only Jira search, reusing the locally authenticated TWG CLI."""

    def __init__(
        self,
        binary: str = "twg",
        *,
        timeout_seconds: float = 30,
        environment: Mapping[str, str] | None = None,
    ) -> None:
        self.binary = binary
        self.timeout_seconds = timeout_seconds
        self.environment = dict(environment) if environment is not None else None

    async def find_candidate(
        self,
        jira_site: str,
        trigger_jql: str,
        *,
        excluded_keys: frozenset[str],
    ) -> JiraDeliveryCandidate | None:
        """Return the first unclaimed match, never treating an incomplete search as idle."""

        site = validate_delivery_jira_site(jira_site)
        jql = validate_delivery_jql(trigger_jql)
        if not site or not jql:
            raise PreflightError("Configure Auto Delivery's Jira site and trigger JQL in Settings.")
        try:
            return await asyncio.wait_for(
                self._find(site, jql, excluded_keys), timeout=self.timeout_seconds
            )
        except TimeoutError as exc:
            raise PreflightError(
                "Auto Delivery Jira detection timed out; Codex was not started."
            ) from exc
        except OSError as exc:
            raise PreflightError(
                "Cannot start TWG for Jira detection. Check the local TWG installation."
            ) from exc
        except (ValidationError, ValueError) as exc:
            raise PreflightError(
                "Jira detection returned an invalid response; Codex was not started."
            ) from exc

    async def _find(
        self, site: str, jql: str, excluded_keys: frozenset[str]
    ) -> JiraDeliveryCandidate | None:
        token: str | None = None
        seen_tokens: set[str] = set()
        for _ in range(20):
            query: dict[str, object] = {"jql": jql, "fields": ["summary"], "maxResults": 100}
            if token is not None:
                query["nextPageToken"] = token
            page = await self._search(site, query)
            for issue in page.issues:
                if issue.key not in excluded_keys:
                    return JiraDeliveryCandidate(
                        issue.key, issue.fields.summary, f"https://{site}/browse/{issue.key}"
                    )
            if page.is_last:
                return None
            token = page.next_token
            if not token or token in seen_tokens:
                break
            seen_tokens.add(token)
        raise PreflightError("Jira detection was incomplete; Codex was not started.")

    async def _search(self, site: str, query: dict[str, object]) -> _Page:
        # The native query wrapper omits pagination; raw search preserves isLast/nextPageToken.
        process = await asyncio.create_subprocess_exec(
            self.binary,
            "api",
            "jira:/rest/api/3/search/jql",
            "--method",
            "POST",
            "--input",
            "-",
            "--site",
            site,
            "--output",
            "json",
            "--output-summary",
            "none",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            env=self.environment,
        )
        try:
            assert process.stdin is not None and process.stdout is not None
            process.stdin.write(json.dumps(query).encode("utf-8"))
            await process.stdin.drain()
            process.stdin.close()
            payload = bytearray()
            while chunk := await process.stdout.read(64 * 1024):
                payload.extend(chunk)
                if len(payload) > 1024 * 1024:
                    raise ValueError("Jira response is too large.")
            await process.wait()
            if process.returncode != 0:
                raise PreflightError(
                    "Jira detection failed. Check TWG access and the trigger JQL; "
                    "Codex was not started."
                )
            response = _Response.model_validate_json(payload)
            if response.data.status != 200:
                raise PreflightError("Jira detection failed; Codex was not started.")
            return _Page.model_validate(response.data.body)
        finally:
            if process.returncode is None:
                try:
                    process.kill()
                except ProcessLookupError:
                    pass
            await process.wait()
