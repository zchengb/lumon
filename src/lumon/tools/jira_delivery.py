"""Read Jira trigger candidates through TWG, without starting an Agent turn."""

from __future__ import annotations

import asyncio
import re
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


class _Issue(BaseModel):
    model_config = ConfigDict(strict=True)

    key: str = Field(pattern=r"^[A-Z][A-Z0-9_]*-[1-9][0-9]*$", max_length=128)
    summary: str = Field(min_length=1, max_length=500)


class _Page(BaseModel):
    model_config = ConfigDict(strict=True)

    issues: list[_Issue] = Field(max_length=1)


class _Response(BaseModel):
    model_config = ConfigDict(strict=True)

    data: _Page
    errors: list[object] = Field(default_factory=list[object], max_length=0)


def _exclude_claimed(jql: str, keys: frozenset[str]) -> str:
    if not keys:
        return jql
    if any(not re.fullmatch(r"[A-Z][A-Z0-9_]*-[1-9][0-9]*", key) for key in keys):
        raise ValueError("Invalid receipt key")
    # Ignore ORDER BY inside quoted JQL values, including escaped quotes.
    tokens = re.finditer(
        r"'[^'\\]*(?:\\.[^'\\]*)*'|\"[^\"\\]*(?:\\.[^\"\\]*)*\"|\border\s+by\b", jql, re.I
    )
    order = next((token.start() for token in tokens if token.group()[0] not in "'\""), len(jql))
    clause, sorting = jql[:order].strip(), jql[order:]
    excluded = ", ".join(sorted(keys))
    return validate_delivery_jql(f"({clause}) AND key NOT IN ({excluded}) {sorting}".strip())


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
                self._find(site, _exclude_claimed(jql, excluded_keys), excluded_keys),
                timeout=self.timeout_seconds,
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
        page = await self._search(site, jql)
        if not page.issues:
            return None
        issue = page.issues[0]
        if issue.key in excluded_keys:
            raise ValueError("Jira returned an excluded key")
        return JiraDeliveryCandidate(issue.key, issue.summary, f"https://{site}/browse/{issue.key}")

    async def _search(self, site: str, jql: str) -> _Page:
        # TWG strips pagination metadata; server-side receipt exclusion needs only one result.
        process = await asyncio.create_subprocess_exec(
            self.binary,
            "jira",
            "workitem",
            "query",
            "--jql",
            jql,
            "--fields",
            "summary",
            "--first",
            "1",
            "--site",
            site,
            "--output",
            "json",
            "--output-summary",
            "none",
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            env=self.environment,
        )
        try:
            assert process.stdout is not None
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
            return response.data
        finally:
            if process.returncode is None:
                try:
                    process.kill()
                except ProcessLookupError:
                    pass
            await process.wait()
