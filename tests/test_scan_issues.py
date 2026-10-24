"""Evidence-gated historical issue rechecks and immutable history projections."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from lumon.scan.issues import latest_findings, review_existing_issues
from lumon.scan.matching import canonical_issue, issue_aliases, validate_issue_matches
from lumon.scan.model import (
    IssueReviewStatus,
    ScanFinding,
    ScanIssueMatch,
    ScanIssueReview,
    ScanRun,
    ScanState,
)
from lumon.scan.store import ScanRunStore


def _finding(**changes: str) -> ScanFinding:
    finding = ScanFinding.from_payload(
        {
            "repository": "app",
            "issue_id": "ISSUE-1",
            "title": "Original bug",
            "validation": "Original static review.",
            **changes,
        },
        1,
    )
    assert finding is not None
    return finding


def _review(**changes: object) -> dict[str, object]:
    return {
        "repository": "app",
        "issue_id": "ISSUE-1",
        "status": "resolved",
        "branch": "master",
        "revision": "a" * 40,
        "fresh": True,
        "evidence": "src/app.py:10-20 now guards null input in both callers; static review only.",
        **changes,
    }


def _run(
    day: int,
    *,
    findings: tuple[ScanFinding, ...] = (),
    reviews: tuple[ScanIssueReview, ...] = (),
    matches: tuple[ScanIssueMatch, ...] = (),
) -> ScanRun:
    return replace(
        ScanRun.start(f"scan-{day}", 7),
        state=ScanState.COMPLETED,
        started_at=datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=day),
        findings=findings,
        issue_reviews=reviews,
        issue_matches=matches,
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"fresh": False},
        {"fresh": "true"},
        {"branch": ""},
        {"revision": "abc123"},
        {"revision": ""},
        {"evidence": ""},
        {"status": "fixed"},
    ],
)
def test_incomplete_evidence_never_resolves(changes: dict[str, object]) -> None:
    review = ScanIssueReview.from_payload(_review(**changes))
    assert review is not None
    assert review.status == IssueReviewStatus.UNVERIFIED
    assert review.evidence


@pytest.mark.parametrize(
    "payload", [None, [], [None], [_review(), _review()], [_review(issue_id="OTHER")]]
)
def test_missing_duplicate_and_unrelated_checks_are_not_fixes(payload: object) -> None:
    reviews = review_existing_issues(
        payload, (_finding(),), (), failed=False, branches={"app": "master"}
    )
    assert len(reviews) == 1
    assert reviews[0].status == IssueReviewStatus.UNVERIFIED


@pytest.mark.parametrize(
    "failed,branches,findings",
    [
        (True, {"app": "master"}, ()),
        (False, {"app": "release"}, ()),
        (False, {}, ()),
        (False, {"app": "master"}, (_finding(),)),
    ],
)
def test_failed_wrong_branch_and_conflicting_reviews_cannot_close(
    failed: bool,
    branches: dict[str, str],
    findings: tuple[ScanFinding, ...],
) -> None:
    reviews = review_existing_issues(
        [_review()], (_finding(),), findings, failed=failed, branches=branches
    )
    assert reviews[0].status == IssueReviewStatus.UNVERIFIED


def test_resolution_round_trips_and_preserves_discovery_and_ignore_choice(tmp_path: Path) -> None:
    store = ScanRunStore()
    original = _run(0, findings=(_finding(), _finding(repository="other")))
    store.save(tmp_path, original)
    original_path = store.path_for(tmp_path, original.run_id) / "run.json"
    original_bytes = original_path.read_bytes()
    reviews = review_existing_issues(
        [_review()], (_finding(),), (), failed=False, branches={"app": "master"}
    )
    checked = _run(10, reviews=reviews)
    store.save(tmp_path, checked)
    assert store.load(tmp_path, checked.run_id) == checked
    visible = store.with_ignored_findings(tmp_path, store.list(tmp_path))
    issue = visible[1].findings[0]
    assert issue.issue_status == "resolved"
    assert "Original static review." in issue.validation
    assert reviews[0].evidence in issue.validation
    assert "a" * 40 in issue.validation
    assert "scan-10" in issue.validation
    assert visible[1].findings[1].issue_status == "open"
    assert original_path.read_bytes() == original_bytes
    assert store.load(tmp_path, original.run_id) == original
    store.ignore_finding(tmp_path, original.run_id, 0)
    assert (
        store.with_ignored_findings(tmp_path, store.list(tmp_path))[1].findings[0].issue_status
        == "ignored"
    )


def test_missing_recheck_retains_last_state_and_successful_recheck_can_reopen(
    tmp_path: Path,
) -> None:
    store = ScanRunStore()
    original = _run(0, findings=(_finding(),))
    resolved = ScanIssueReview.from_payload(_review())
    assert resolved is not None
    for run in (original, _run(1, reviews=(resolved,)), _run(2)):
        store.save(tmp_path, run)
    assert (
        store.with_ignored_findings(tmp_path, store.list(tmp_path))[-1].findings[0].issue_status
        == "resolved"
    )
    unverified = ScanIssueReview.from_payload(
        _review(status="unverified", evidence="Fetch failed.", fresh=False)
    )
    assert unverified is not None
    store.save(tmp_path, _run(3, reviews=(unverified,)))
    issue = store.with_ignored_findings(tmp_path, store.list(tmp_path))[-1].findings[0]
    assert issue.issue_status == "resolved"
    assert "Fetch failed." in issue.validation
    reopened = ScanIssueReview.from_payload(_review(status="open"))
    assert reopened is not None
    store.save(tmp_path, _run(4, reviews=(reopened,)))
    assert (
        store.with_ignored_findings(tmp_path, store.list(tmp_path))[-1].findings[0].issue_status
        == "reopened"
    )


@pytest.mark.parametrize("state", [ScanState.RUNNING, ScanState.FAILED])
def test_unfinished_or_failed_receipts_do_not_change_history(
    tmp_path: Path, state: ScanState
) -> None:
    store = ScanRunStore()
    review = ScanIssueReview.from_payload(_review())
    assert review is not None
    runs = (_run(0, findings=(_finding(),)), replace(_run(1, reviews=(review,)), state=state))
    assert store.with_ignored_findings(tmp_path, runs)[0].findings[0].issue_status == "open"


def test_old_deduplicated_resolved_and_ignored_issues_are_reviewed() -> None:
    oldest = _run(
        0,
        findings=(
            _finding(),
            _finding(issue_id="SECOND"),
            _finding(issue_id="IGNORED", issue_status="ignored"),
        ),
    )
    newer = _run(100, findings=(_finding(title="Newest evidence", issue_status="resolved"),))
    known = latest_findings((oldest, newer))
    assert [item.title for item in known] == ["Newest evidence", "Original bug", "Original bug"]
    assert {item.issue_id for item in known} == {"ISSUE-1", "SECOND", "IGNORED"}


def test_old_receipts_and_untracked_occurrences_remain_compatible(tmp_path: Path) -> None:
    run = _run(
        0,
        findings=(
            _finding(issue_id="untracked"),
            _finding(issue_id="untracked", issue_status="resolved"),
        ),
    )
    payload = run.as_payload()
    del payload["issue_reviews"]
    del payload["issue_matches"]
    loaded = ScanRun.from_payload(payload)
    assert loaded.issue_reviews == ()
    assert loaded.issue_matches == ()
    assert ScanRunStore().with_ignored_findings(tmp_path, (loaded,)) == (loaded,)


def test_partial_recheck_closes_only_the_verified_repository(tmp_path: Path) -> None:
    store = ScanRunStore()
    findings = (_finding(), _finding(repository="unavailable"))
    original = _run(0, findings=findings)
    reviews = review_existing_issues(
        [_review()],
        findings,
        (),
        failed=False,
        branches={"app": "master", "unavailable": "master"},
    )
    incomplete = replace(_run(1, reviews=reviews), state=ScanState.COMPLETED_WITH_FAILURES)
    projected = store.with_ignored_findings(tmp_path, (incomplete, original))
    assert [finding.issue_status for finding in projected[1].findings] == ["resolved", "open"]
    assert "Missing or duplicate" in projected[1].findings[1].validation


@pytest.mark.parametrize(
    "changes", [{"evidence": True}, {"revision": 123}, {"repository": ["app"]}]
)
def test_non_text_evidence_is_not_coerced_into_a_resolution(changes: dict[str, object]) -> None:
    reviews = review_existing_issues(
        [_review(**changes)],
        (_finding(),),
        (),
        failed=False,
        branches={"app": "master"},
    )
    assert reviews[0].status == IssueReviewStatus.UNVERIFIED


def test_review_evidence_is_redacted_and_bounded() -> None:
    review = ScanIssueReview.from_payload(_review(evidence="token: secret-value\n" + "x" * 10_000))
    assert review is not None
    assert "secret-value" not in review.evidence
    assert len(review.evidence) <= 8_000


def _match(**changes: object) -> dict[str, object]:
    return {
        **_review(issue_id="SECOND"),
        "canonical_issue_id": "ISSUE-1",
        "evidence": (
            "src/app.py:10-20: both descriptions identify the same missing null guard "
            "and caller trigger."
        ),
        **changes,
    }


@pytest.mark.parametrize(
    "changes",
    [
        {"canonical_issue_id": "UNKNOWN"},
        {"repository": "other"},
        {"branch": "feature"},
        {"fresh": False},
        {"fresh": "true"},
        {"revision": "short"},
        {"evidence": ""},
        {"evidence": True},
        {"canonical_issue_id": "x" * 101},
        {"issue_id": "UNKNOWN"},
    ],
)
def test_invalid_semantic_decisions_never_suppress_findings(changes: dict[str, object]) -> None:
    matches, failures = validate_issue_matches(
        [_match(**changes)], (_finding(),), (_finding(issue_id="SECOND"),), {"app": "master"}
    )
    assert matches == ()
    assert failures


@pytest.mark.parametrize(
    "payload",
    [
        None,
        {},
        [None],
        [_match(), _match()],
        [_match(), _match(issue_id="ISSUE-1", canonical_issue_id="SECOND")],
        [_match(issue_id="ISSUE-1", canonical_issue_id="NEW")],
    ],
)
def test_missing_conflicting_cyclic_or_identity_replacing_matches_are_rejected(
    payload: object,
) -> None:
    matches, failures = validate_issue_matches(
        payload,
        (_finding(), _finding(issue_id="SECOND")),
        (_finding(issue_id="NEW"),),
        {"app": "master"},
    )
    assert matches == ()
    assert failures


def test_identity_is_decided_by_agent_not_titles_files_or_ids() -> None:
    old = _finding(file="same.py")
    candidate = _finding(issue_id="SECOND", file="same.py", title=old.title)
    assert validate_issue_matches([], (old,), (candidate,), {"app": "master"}) == ((), ())
    matches, failures = validate_issue_matches([_match()], (old,), (candidate,), {"app": "master"})
    assert len(matches) == 1
    assert not failures
    assert validate_issue_matches([], (old,), (old,), {"app": "master"})[1]
    self_match, failures = validate_issue_matches(
        [_match(issue_id="ISSUE-1")], (old,), (old,), {"app": "master"}
    )
    assert len(self_match) == 1
    assert not failures


@pytest.mark.parametrize("ignored_index", [None, 0, 1])
def test_semantic_history_merges_and_preserves_any_ignore_after_restart(
    tmp_path: Path,
    ignored_index: int | None,
) -> None:
    store = ScanRunStore()
    discoveries = (
        _run(0, findings=(_finding(title="Invalid primary suppresses fallback"),)),
        _run(1, findings=(_finding(issue_id="SECOND", title="Placeholder blocks valid identity"),)),
    )
    for run in discoveries:
        store.save(tmp_path, run)
    original_bytes = [
        (store.path_for(tmp_path, run.run_id) / "run.json").read_bytes() for run in discoveries
    ]
    if ignored_index is not None:
        store.ignore_finding(tmp_path, discoveries[ignored_index].run_id, 0)
    matches, failures = validate_issue_matches(
        [_match()], tuple(run.findings[0] for run in discoveries), (), {"app": "master"}
    )
    assert not failures
    reviews = review_existing_issues(
        [_review(), _review(issue_id="SECOND")],
        tuple(run.findings[0] for run in discoveries),
        (),
        failed=False,
        branches={"app": "master"},
        matches=matches,
    )
    reconciled = _run(2, reviews=reviews, matches=matches)
    store.save(tmp_path, reconciled)
    reloaded = ScanRunStore()
    assert reloaded.load(tmp_path, reconciled.run_id) == reconciled
    visible = reloaded.with_ignored_findings(tmp_path, reloaded.list(tmp_path))
    known = latest_findings(visible)
    assert len(known) == 1
    assert known[0].issue_id == "ISSUE-1"
    assert known[0].issue_status == ("resolved" if ignored_index is None else "ignored")
    assert "same missing null guard" in known[0].validation
    for index, run in enumerate(discoveries):
        assert (store.path_for(tmp_path, run.run_id) / "run.json").read_bytes() == original_bytes[
            index
        ]
    reopened = ScanIssueReview.from_payload(_review(status="open"))
    assert reopened is not None
    reloaded.save(tmp_path, _run(3, reviews=(reopened,)))
    known = latest_findings(reloaded.with_ignored_findings(tmp_path, reloaded.list(tmp_path)))
    assert known[0].issue_status == ("reopened" if ignored_index is None else "ignored")


@pytest.mark.parametrize("second", ["open", "unverified", "missing"])
def test_equivalent_issues_cannot_resolve_with_inconsistent_or_missing_rechecks(
    second: str,
) -> None:
    existing = (_finding(), _finding(issue_id="SECOND"))
    matches, _ = validate_issue_matches([_match()], existing, (), {"app": "master"})
    payload = [_review()]
    if second != "missing":
        payload.append(_review(issue_id="SECOND", status=second))
    reviews = review_existing_issues(
        payload,
        existing,
        (),
        failed=False,
        branches={"app": "master"},
        matches=matches,
    )
    assert all(review.status != IssueReviewStatus.RESOLVED for review in reviews)


def test_matched_active_finding_cannot_be_resolved() -> None:
    candidate = _finding(issue_id="SECOND")
    matches, _ = validate_issue_matches([_match()], (_finding(),), (candidate,), {"app": "master"})
    reviews = review_existing_issues(
        [_review()],
        (_finding(),),
        (candidate,),
        failed=False,
        branches={"app": "master"},
        matches=matches,
    )
    assert reviews[0].status == IssueReviewStatus.UNVERIFIED


def test_new_candidates_can_share_one_agent_chosen_identity() -> None:
    findings = (_finding(), _finding(issue_id="SECOND"), _finding(issue_id="THIRD"))
    matches, failures = validate_issue_matches(
        [_match(), _match(issue_id="THIRD", canonical_issue_id="SECOND")],
        (),
        findings,
        {"app": "master"},
    )
    assert not failures
    aliases = issue_aliases(matches)
    assert canonical_issue(("app", "THIRD"), aliases) == ("app", "ISSUE-1")
    assert canonical_issue(("other", "THIRD"), aliases) == ("other", "THIRD")
    # A later reversed association cannot create a cross-run cycle or split the group.
    reverse = ScanIssueMatch.from_payload(_match(issue_id="ISSUE-1", canonical_issue_id="THIRD"))
    assert reverse is not None
    assert issue_aliases((*matches, reverse)) == aliases


def test_ignore_action_on_merged_history_uses_original_receipt_index(tmp_path: Path) -> None:
    store = ScanRunStore()
    original = _run(0, findings=(_finding(), _finding(issue_id="SECOND")))
    matches, _ = validate_issue_matches([_match()], original.findings, (), {"app": "master"})
    for run in (original, _run(1, matches=matches)):
        store.save(tmp_path, run)
    visible = store.with_ignored_findings(tmp_path, store.list(tmp_path))
    assert visible[-1].findings[1].issue_id == "ISSUE-1"
    store.ignore_finding(tmp_path, original.run_id, 1)
    known = latest_findings(store.with_ignored_findings(tmp_path, store.list(tmp_path)))
    assert len(known) == 1
    assert known[0].issue_status == "ignored"
