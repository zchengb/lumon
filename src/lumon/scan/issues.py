"""Recheck policy and history projections without rewriting discovery receipts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from typing import cast

from lumon.scan.matching import IssueKey, canonical_issue, issue_aliases
from lumon.scan.model import (
    IssueReviewStatus,
    ScanFinding,
    ScanIssueMatch,
    ScanIssueReview,
    ScanRun,
    ScanState,
)


def latest_findings(runs: tuple[ScanRun, ...]) -> tuple[ScanFinding, ...]:
    """Deduplicate known issues independently of the new-change lookback window."""

    latest: dict[tuple[str, str], ScanFinding] = {}
    for run in sorted(runs, key=lambda item: item.started_at, reverse=True):
        if run.state in {ScanState.RUNNING, ScanState.FAILED}:
            continue
        for finding in run.findings:
            latest.setdefault((finding.repository, finding.issue_id), finding)
    # shortcut: legacy untracked occurrences stay unchanged until they have stable issue IDs.
    return tuple(
        finding for finding in latest.values() if finding.issue_id.strip() not in {"", "untracked"}
    )


def review_existing_issues(
    payload: object,
    existing: tuple[ScanFinding, ...],
    findings: tuple[ScanFinding, ...],
    *,
    failed: bool,
    branches: Mapping[str, str],
    matches: tuple[ScanIssueMatch, ...] = (),
) -> tuple[ScanIssueReview, ...]:
    """Require evidence for non-ignored issues; ignored identities remain matchable."""

    items = cast(list[object], payload) if isinstance(payload, list) else []
    grouped: dict[tuple[str, str], list[ScanIssueReview]] = {}
    for item in items:
        if (review := ScanIssueReview.from_payload(item)) is not None:
            grouped.setdefault((review.repository, review.issue_id), []).append(review)
    aliases = issue_aliases(matches)
    ignored = {
        canonical_issue((finding.repository, finding.issue_id), aliases)
        for finding in existing
        if finding.issue_status.strip().lower() in {"ignored", "ignore"}
    }
    discovered = {
        canonical_issue((finding.repository, finding.issue_id), aliases) for finding in findings
    }
    known = {(finding.repository, finding.issue_id) for finding in existing}
    for match in matches:
        source = (match.repository, match.issue_id)
        target = (match.repository, match.canonical_issue_id)
        if source not in known or source == target:
            discovered.add(canonical_issue(source, aliases))
    reviews: list[ScanIssueReview] = []
    for finding in existing:
        key = (finding.repository, finding.issue_id)
        if canonical_issue(key, aliases) in ignored:
            continue
        candidates = grouped.get(key, [])
        if failed or len(candidates) != 1:
            reason = "Scan failed." if failed else "Missing or duplicate issue recheck."
            reviews.append(
                ScanIssueReview(
                    repository=finding.repository,
                    issue_id=finding.issue_id,
                    status=IssueReviewStatus.UNVERIFIED,
                    evidence=reason,
                )
            )
            continue
        review = candidates[0]
        if (
            review.status != IssueReviewStatus.UNVERIFIED
            and branches.get(review.repository) != review.branch
        ):
            review = replace(
                review,
                status=IssueReviewStatus.UNVERIFIED,
                evidence="Recheck did not inspect the repository's configured branch.",
            )
        if (
            review.status == IssueReviewStatus.RESOLVED
            and canonical_issue(key, aliases) in discovered
        ):
            review = replace(
                review,
                status=IssueReviewStatus.UNVERIFIED,
                evidence="Issue is also reported as an active finding; resolution rejected.",
            )
        reviews.append(review)
    return _consistent_reviews(tuple(reviews), aliases)


def _consistent_reviews(
    reviews: tuple[ScanIssueReview, ...], aliases: Mapping[IssueKey, IssueKey]
) -> tuple[ScanIssueReview, ...]:
    incomplete = {
        canonical_issue((review.repository, review.issue_id), aliases)
        for review in reviews
        if review.status != IssueReviewStatus.RESOLVED
    }
    return tuple(
        replace(
            review,
            status=IssueReviewStatus.UNVERIFIED,
            evidence=(
                "An equivalent issue has an open or unverified assessment; resolution rejected."
            ),
        )
        if review.status == IssueReviewStatus.RESOLVED
        and canonical_issue((review.repository, review.issue_id), aliases) in incomplete
        else review
        for review in reviews
    )


def with_issue_reviews(runs: tuple[ScanRun, ...]) -> tuple[ScanRun, ...]:
    """Project latest verified status and detailed check evidence onto issue history."""

    settled = tuple(
        run
        for run in sorted(runs, key=lambda item: item.started_at)
        if run.state not in {ScanState.RUNNING, ScanState.FAILED}
    )
    matches = tuple(match for run in settled for match in run.issue_matches)
    aliases = issue_aliases(matches)
    states, notes = _review_states(settled, aliases)
    for run in settled:
        for finding in run.findings:
            if finding.issue_status.strip().lower() in {"ignored", "ignore"}:
                states[canonical_issue((finding.repository, finding.issue_id), aliases)] = "ignored"
    for match in matches:
        key = canonical_issue((match.repository, match.issue_id), aliases)
        notes[key] = (
            f"{notes.get(key, '')}\nSemantic identity: {match.issue_id} -> "
            f"{key[1]}\n{match.evidence}"
        )
    return tuple(
        replace(
            run,
            findings=tuple(
                _project_finding(finding, states, notes, aliases) for finding in run.findings
            ),
        )
        for run in runs
    )


def _review_states(
    runs: tuple[ScanRun, ...], aliases: Mapping[IssueKey, IssueKey]
) -> tuple[dict[IssueKey, str], dict[IssueKey, str]]:
    states: dict[IssueKey, str] = {}
    notes: dict[IssueKey, str] = {}
    for run in runs:
        for finding in run.findings:
            if finding.issue_id.strip() in {"", "untracked"}:
                continue
            key = canonical_issue((finding.repository, finding.issue_id), aliases)
            state = finding.issue_status.strip().lower()
            states[key] = "reopened" if states.get(key) == "resolved" and state == "open" else state
            notes.pop(key, None)
        for review in run.issue_reviews:
            key = canonical_issue((review.repository, review.issue_id), aliases)
            if key not in states:
                continue
            if review.status == IssueReviewStatus.RESOLVED:
                states[key] = "resolved"
            elif review.status == IssueReviewStatus.OPEN:
                states[key] = "reopened" if states[key] == "resolved" else "open"
            notes[key] = (
                f"Latest issue recheck: {run.started_at.isoformat()} (scan {run.run_id})\n"
                f"Outcome: {review.status.value}\nBranch: {review.branch or 'unverified'}\n"
                f"Commit: {review.revision or 'unverified'}\n{review.evidence}"
            )
    return states, notes


def _project_finding(
    finding: ScanFinding,
    states: dict[IssueKey, str],
    notes: dict[IssueKey, str],
    aliases: Mapping[IssueKey, IssueKey],
) -> ScanFinding:
    if finding.issue_id.strip() in {"", "untracked"}:
        return finding
    key = canonical_issue((finding.repository, finding.issue_id), aliases)
    return replace(
        finding,
        issue_id=key[1],
        issue_status=states.get(key, finding.issue_status),
        validation=f"{finding.validation}\n\n{notes[key]}" if key in notes else finding.validation,
    )
