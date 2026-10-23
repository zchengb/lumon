"""Recheck policy and history projections without rewriting discovery receipts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from typing import cast

from lumon.scan.model import IssueReviewStatus, ScanFinding, ScanIssueReview, ScanRun, ScanState


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
        finding
        for finding in latest.values()
        if finding.issue_id.strip() not in {"", "untracked"}
        and finding.issue_status.strip().lower() not in {"ignored", "ignore"}
    )


def review_existing_issues(
    payload: object,
    existing: tuple[ScanFinding, ...],
    findings: tuple[ScanFinding, ...],
    *,
    failed: bool,
    branches: Mapping[str, str],
) -> tuple[ScanIssueReview, ...]:
    """Require exactly one explicit assessment per known issue; absence is not a fix."""

    items = cast(list[object], payload) if isinstance(payload, list) else []
    grouped: dict[tuple[str, str], list[ScanIssueReview]] = {}
    for item in items:
        if (review := ScanIssueReview.from_payload(item)) is not None:
            grouped.setdefault((review.repository, review.issue_id), []).append(review)
    discovered = {(finding.repository, finding.issue_id) for finding in findings}
    reviews: list[ScanIssueReview] = []
    for finding in existing:
        key = (finding.repository, finding.issue_id)
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
        if review.status == IssueReviewStatus.RESOLVED and key in discovered:
            review = replace(
                review,
                status=IssueReviewStatus.UNVERIFIED,
                evidence="Issue is also reported as an active finding; resolution rejected.",
            )
        reviews.append(review)
    return tuple(reviews)


def with_issue_reviews(runs: tuple[ScanRun, ...]) -> tuple[ScanRun, ...]:
    """Project latest verified status and detailed check evidence onto issue history."""

    states: dict[tuple[str, str], str] = {}
    notes: dict[tuple[str, str], str] = {}
    for run in sorted(runs, key=lambda item: item.started_at):
        if run.state in {ScanState.RUNNING, ScanState.FAILED}:
            continue
        for finding in run.findings:
            if finding.issue_id.strip() in {"", "untracked"}:
                continue
            key = (finding.repository, finding.issue_id)
            state = finding.issue_status.strip().lower()
            states[key] = "reopened" if states.get(key) == "resolved" and state == "open" else state
            notes.pop(key, None)
        for review in run.issue_reviews:
            key = (review.repository, review.issue_id)
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
    return tuple(
        replace(
            run,
            findings=tuple(_project_finding(finding, states, notes) for finding in run.findings),
        )
        for run in runs
    )


def _project_finding(
    finding: ScanFinding,
    states: dict[tuple[str, str], str],
    notes: dict[tuple[str, str], str],
) -> ScanFinding:
    if finding.issue_id.strip() in {"", "untracked"}:
        return finding
    key = (finding.repository, finding.issue_id)
    return replace(
        finding,
        issue_status=states.get(key, finding.issue_status),
        validation=f"{finding.validation}\n\n{notes[key]}" if key in notes else finding.validation,
    )
