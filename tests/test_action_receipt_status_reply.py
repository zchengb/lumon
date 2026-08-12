from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from agents.runtime.final_response import format_action_receipts_summary, is_planning_reply, prefer_action_summary


def test_planning_reply_detects_status_placeholder() -> None:
    assert is_planning_reply(
        "I'll pull the job status for MBPAS-1491 and report back with a clear owner and next step."
        "Checking Mark’s queue for the MBPAS-1491 test-case job now."
    )
    assert not is_planning_reply("**Job status**: completed\n- Mark failed on Bitable config")


def test_unexecuted_delegation_claim_stripped_without_receipts() -> None:
    claim = (
        "已將 MBPAS-1503 的 Technical Plan 派給 Mark。"
        "他會讀取 Jira 卡片與 workspace 內容並開始推進，後續進度我再回報。"
    )
    assert prefer_action_summary(claim, []) == ""


def test_unexecuted_delegation_claim_strips_line_but_keeps_other_text() -> None:
    text = "已將 MBPAS-1503 的 Technical Plan 派給 Mark。\n\n我會在進度更新後回報。"
    result = prefer_action_summary(text, [])
    assert "派給" not in result
    assert "進度更新後回報" in result


def test_successful_job_create_replaces_claim_with_host_summary() -> None:
    claim = "已將 MBPAS-1503 的 Technical Plan 派給 Mark。"
    receipts = [
        {
            "action": "agent.job.create",
            "status": "succeeded",
            "result": {"handoff_text": "Mark is running Technical Loop for MBPAS-1503."},
        }
    ]
    text = prefer_action_summary(claim, receipts)
    assert "Mark is running Technical Loop for MBPAS-1503." in text
    assert "派給" not in text


def test_job_list_receipt_becomes_status_reply() -> None:
    receipts = [
        {
            "action": "agent.job.list",
            "status": "succeeded",
            "result": {
                "jobs": [
                    {
                        "job_id": "job_mark_94ccf628fb20",
                        "status": "completed",
                        "target_agent": "mark",
                        "capability": "test_case.generate",
                        "input": {"issue_key": "MBPAS-1491"},
                        "result": {
                            "result": {
                                "status": "failed",
                                "code": "TEST_CASE_CONFIG_MISSING",
                                "message": "No Feishu Bitable app token configured for project mbpass",
                            }
                        },
                    }
                ]
            },
        }
    ]
    placeholder = (
        "I'll pull the job status for MBPAS-1491 and report back with a clear owner and next step."
        "Checking Mark’s queue now."
    )
    text = prefer_action_summary(placeholder, receipts)
    assert "job_mark_94ccf628fb20" not in text
    assert "Mark failed test case generation for MBPAS-1491." in text
    assert "TEST_CASE_CONFIG_MISSING" in text
    assert "I'll pull" not in text
    assert "Action results:" not in format_action_receipts_summary(receipts)


def test_job_list_outranks_agent_list_for_status_asks() -> None:
    receipts = [
        {
            "action": "agent.health",
            "status": "succeeded",
            "result": {"agents": [{"id": "dylan"}, {"id": "mark"}, {"id": "milchick"}, {"id": "irving"}]},
        },
        {
            "action": "agent.job.list",
            "status": "succeeded",
            "result": {
                "jobs": [
                    {
                        "job_id": "job_mark_bdb66f270fd0",
                        "status": "completed",
                        "target_agent": "mark",
                        "capability": "test_case.generate",
                        "input": {"issue_key": "MBPAS-1491"},
                        "result": {"result": {"status": "completed", "summary": "Generated 3 test cases"}},
                    }
                ]
            },
        },
    ]
    text = prefer_action_summary("**Agents:** dylan, mark, milchick, irving", receipts)
    assert "job_mark_bdb66f270fd0" not in text
    assert "Mark finished test case generation for MBPAS-1491." in text
    assert "Generated 3 test cases" in text
    assert text.startswith("**Job status**")
    assert "**Agents:**" not in text


def test_denied_mutation_surfaces_instead_of_planning_lie() -> None:
    receipts = [
        {
            "action": "agent.job.list",
            "status": "succeeded",
            "result": {
                "jobs": [
                    {
                        "job_id": "job_mark_94ccf628fb20",
                        "status": "completed",
                        "target_agent": "mark",
                        "capability": "test_case.generate",
                        "input": {"issue_key": "MBPAS-1491"},
                    }
                ]
            },
        },
        {
            "action": "agent.job.create",
            "status": "denied",
            "error": "mutation denied for zone=RESTRICTED action=agent.job.create",
            "error_code": "AUTHORIZATION_DENIED",
            "result": {},
        },
    ]
    invented = (
        "**MBPAS-1491** test-case job check:\n\n"
        "- **Status (last confirmed):** queued — still **no running/completed/failed payload**"
    )
    text = prefer_action_summary(invented, receipts)
    assert "job_mark_94ccf628fb20" not in text
    assert "Mark finished test case generation for MBPAS-1491." in text
    assert "queued" not in text.lower()
    assert "Action blocked" in text
    assert "agent.job.create" in text


def test_denied_job_create_does_not_claim_job_was_created() -> None:
    text = prefer_action_summary(
        "已確認需求。\n\n已建立 Mark job。完成後會回報 PR／結果。",
        [
            {
                "action": "agent.job.create",
                "status": "denied",
                "error": "mutation denied for zone=RESTRICTED action=agent.job.create",
            }
        ],
    )
    assert "已建立 Mark job" not in text
    assert "已確認需求" in text
    assert "Action blocked" in text
    assert "was not executed" in text


def test_job_list_keeps_latest_per_issue_only() -> None:
    receipts = [
        {
            "action": "agent.job.list",
            "status": "succeeded",
            "result": {
                "jobs": [
                    {
                        "job_id": "job_mark_new",
                        "status": "completed",
                        "created_at": "2026-08-08T11:54:21Z",
                        "target_agent": "mark",
                        "capability": "test_case.generate",
                        "input": {"issue_key": "MBPAS-1491"},
                        "result": {
                            "status": "completed",
                            "summary": "Generated 5 test cases for MBPAS-1491.",
                            "sheet_url": "https://inspiregroup.feishu.cn/sheets/OG4Js7cIlh7d0QtHOEnc1kDfnvf?sheet=3LwiOc",
                        },
                    },
                    {
                        "job_id": "job_parent_old",
                        "status": "completed",
                        "created_at": "2026-08-08T08:06:11Z",
                        "input": {"issue_key": "MBPAS-1491"},
                    },
                    {
                        "job_id": "job_mark_old",
                        "status": "completed",
                        "created_at": "2026-08-08T08:06:11Z",
                        "target_agent": "mark",
                        "capability": "test_case.generate",
                        "input": {"issue_key": "MBPAS-1491"},
                        "result": {
                            "status": "completed",
                            "summary": "Generated 3 test cases for MBPAS-1491.",
                            "sheet_url": "https://inspiregroup.feishu.cn/base/old",
                        },
                    },
                    {
                        "job_id": "job_mark_failed",
                        "status": "failed",
                        "created_at": "2026-08-08T06:42:21Z",
                        "target_agent": "mark",
                        "capability": "test_case.generate",
                        "input": {"issue_key": "MBPAS-1491"},
                        "result": {
                            "status": "failed",
                            "code": "TEST_CASE_CONFIG_MISSING",
                            "message": "No Feishu Bitable app token configured for project mbpass",
                        },
                    },
                ]
            },
        }
    ]
    text = prefer_action_summary("how's MBPAS-1491 going?", receipts)
    assert "Generated 5 test cases" in text
    assert "Generated 3 test cases" not in text
    assert "TEST_CASE_CONFIG_MISSING" not in text
    assert "/sheets/" in text
    assert "/base/old" not in text


def test_job_create_completed_overrides_queued_lie() -> None:
    receipts = [
        {
            "action": "agent.job.create",
            "status": "succeeded",
            "result": {
                "child": {
                    "job_id": "job_mark_1",
                    "status": "completed",
                    "target_agent": "mark",
                    "capability": "test_case.generate",
                    "input": {"issue_key": "MBPAS-1491"},
                },
                "handoff_text": "Mark finished test case generation for MBPAS-1491.",
                "result_delivered": True,
            },
        }
    ]
    text = prefer_action_summary("Test case generation for MBPAS-1491 is queued with Mark.", receipts)
    assert "Mark finished test case generation for MBPAS-1491." in text
    assert "queued" not in text.lower()


def test_job_create_handoff_text_for_completed_child() -> None:
    from agents.jobs.broker import _job_create_handoff_text
    from agents.jobs.store import AgentJob

    child = AgentJob(
        job_id="job_1",
        type="child",
        status="completed",
        target_agent="mark",
        capability="test_case.generate",
        input={"issue_key": "MBPAS-1491"},
    )
    assert _job_create_handoff_text("mark", "test_case.generate", child) == (
        "Mark finished test case generation for MBPAS-1491."
    )
    child.status = "queued"
    assert "queued with Mark" in _job_create_handoff_text("mark", "test_case.generate", child)


if __name__ == "__main__":
    test_planning_reply_detects_status_placeholder()
    test_job_list_receipt_becomes_status_reply()
    test_job_list_outranks_agent_list_for_status_asks()
    test_denied_mutation_surfaces_instead_of_planning_lie()
    test_job_list_keeps_latest_per_issue_only()
    test_job_create_completed_overrides_queued_lie()
    test_job_create_handoff_text_for_completed_child()
    print("ok")
