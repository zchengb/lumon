"""Validate and retain Agent semantic decisions without guessing issue identity."""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from lumon.scan.model import ScanFinding, ScanIssueMatch

IssueKey = tuple[str, str]


def canonical_issue(key: IssueKey, aliases: Mapping[IssueKey, IssueKey]) -> IssueKey:
    """Follow validated associations without allowing corrupt history to loop."""

    visited: set[IssueKey] = set()
    current = key
    while current in aliases:
        if current in visited:
            return key
        visited.add(current)
        current = aliases[current]
    return current


def issue_aliases(matches: tuple[ScanIssueMatch, ...]) -> dict[IssueKey, IssueKey]:
    """Keep existing associations stable; self-matches only attest rediscovery."""

    aliases: dict[IssueKey, IssueKey] = {}
    for match in matches:
        source = (match.repository, match.issue_id)
        target = canonical_issue((match.repository, match.canonical_issue_id), aliases)
        if source != target and source not in aliases:
            aliases[source] = target
    return aliases


def validate_issue_matches(
    payload: object,
    existing: tuple[ScanFinding, ...],
    findings: tuple[ScanFinding, ...],
    branches: Mapping[str, str],
) -> tuple[tuple[ScanIssueMatch, ...], tuple[str, ...]]:
    """Reject ambiguous, unknown, cross-branch or cyclic Agent associations."""

    if payload is None:
        if existing:
            return (), ("Semantic comparison of existing issues is missing.",)
        return (), ()
    if not isinstance(payload, list):
        return (), ("Semantic issue matching is invalid; no duplicates suppressed.",)
    items = cast(list[object], payload)
    matches = tuple(ScanIssueMatch.from_payload(item) for item in items)
    known = {(finding.repository, finding.issue_id) for finding in existing}
    observed = {(finding.repository, finding.issue_id) for finding in findings}
    accepted: dict[IssueKey, ScanIssueMatch] = {}
    for match in matches:
        if match is None or not _valid_match(match, known, observed, branches):
            return (), ("Semantic issue matching lacks valid references or fresh evidence.",)
        key = (match.repository, match.issue_id)
        if key in accepted:
            return (), ("Semantic issue matching contains conflicting or duplicate decisions.",)
        accepted[key] = match
    links = {
        key: (match.repository, match.canonical_issue_id)
        for key, match in accepted.items()
        if key != (match.repository, match.canonical_issue_id)
    }
    if any(_has_cycle(key, links) for key in links):
        return (), ("Semantic issue matching contains a cycle; no duplicates suppressed.",)
    if (known & observed) - accepted.keys():
        return (), ("Reused historical issue IDs lack an explicit semantic decision.",)
    return tuple(accepted.values()), ()


def _valid_match(
    match: ScanIssueMatch,
    known: set[IssueKey],
    observed: set[IssueKey],
    branches: Mapping[str, str],
) -> bool:
    source = (match.repository, match.issue_id)
    target = (match.repository, match.canonical_issue_id)
    if target not in known | observed:
        return False
    if source in known and target not in known:
        return False
    if source == target and source not in known:
        return False
    return match.branch == branches.get(match.repository)


def _has_cycle(key: IssueKey, links: Mapping[IssueKey, IssueKey]) -> bool:
    visited: set[IssueKey] = set()
    while key in links:
        if key in visited:
            return True
        visited.add(key)
        key = links[key]
    return False
