#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from agents.dylan.conversation import handle_conversation
from agents.dylan.guard import validate_response
from agents.dylan.normalizer import normalize_message
from agents.dylan.router import route_message
from risk.alerts import deliver_alerts, evaluate_alerts
from risk.ingestion import ingest_scan_risk
from risk.lifecycle import apply_seen, invalidate_ignore_if_needed, upsert_ignore_policy
from risk.migrations import SCHEMA_VERSION, connect
from risk.models import STATUS_IGNORED, STATUS_OPEN, STATUS_REOPENED, STATUS_RESOLVED, RiskConfig
from risk.store import GlobalAgentStore, RiskStore


class NormalizerTests(unittest.TestCase):
    def test_traditional_simplified_status(self) -> None:
        a = normalize_message("完成了吗")
        b = normalize_message("完成了嗎")
        self.assertIn("完成了吗", a.normalized_text)
        self.assertIn("完成了吗", b.normalized_text)
        self.assertEqual(b.language, "zh-Hant")

    def test_scan_project_extract(self) -> None:
        msg = normalize_message("掃描 mbpass 最近七天", known_slugs={"mbpass"})
        self.assertEqual(msg.project_slug, "mbpass")
        msg2 = normalize_message("扫描 mbpass 最近七天", known_slugs={"mbpass"})
        self.assertEqual(msg2.project_slug, "mbpass")


class RouterTests(unittest.TestCase):
    def test_intents(self) -> None:
        self.assertEqual(route_message(normalize_message("你好")).intent, "conversation.greeting")
        self.assertEqual(route_message(normalize_message("你是誰？")).intent, "conversation.agent_identity")
        self.assertEqual(
            route_message(normalize_message("你和 Mark 關係好嗎？")).intent,
            "conversation.agent_relationship",
        )
        self.assertEqual(route_message(normalize_message("最近最大的風險是什麼？")).intent, "risk.top")
        self.assertEqual(route_message(normalize_message("剛才完成了嗎？")).intent, "scan.status")
        self.assertNotEqual(route_message(normalize_message("你好")).intent, "scan.help")

    def test_follow_up_uses_context(self) -> None:
        ctx = {"last_result_ids": ["FIND-aaa", "FIND-bbb", "FIND-ccc"], "last_finding_id": "FIND-aaa"}
        result = route_message(normalize_message("第二個呢？"), context=ctx)
        self.assertEqual(result.intent, "conversation.follow_up")
        self.assertEqual(result.finding_id, "FIND-bbb")


class LifecycleCorrectnessTests(unittest.TestCase):
    def test_incremental_absence_does_not_resolve(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "config").mkdir()
            (workspace / "state").mkdir()
            common = {
                "project": {"slug": "demo"},
                "agents": {"dylan": {"risk_analyst": {"enabled": True}}},
            }
            finding = {
                "title": "Payment retry race",
                "severity": "High",
                "repository": "pay",
                "file": "payment/Retry.java",
                "trigger": "unlocked flip",
                "root_cause": "payment race",
                "issue_id": "ISSUE-1",
            }
            ingest_scan_risk(
                workspace=workspace,
                scan={"scan_status": "completed", "finished_at": "2026-08-01T01:00:00Z", "findings": [finding]},
                registry={"issues": []},
                common=common,
                result_path=workspace / "results" / "a.json",
            )
            ingest_scan_risk(
                workspace=workspace,
                scan={"scan_status": "completed", "finished_at": "2026-08-08T01:00:00Z", "findings": []},
                registry={"issues": []},
                common=common,
                result_path=workspace / "results" / "b.json",
            )
            store = RiskStore(workspace)
            row = store.list_findings("demo")[0]
            self.assertEqual(row["status"], STATUS_OPEN)
            self.assertEqual(row["verification_status"], "not_observed")
            self.assertEqual(int(row["occurrence_count"]), 1)
            self.assertEqual(int(row["recurrence_count"]), 0)
            store.close()

    def test_observation_does_not_inflate_recurrence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "config").mkdir()
            (workspace / "state").mkdir()
            common = {
                "project": {"slug": "demo"},
                "agents": {"dylan": {"risk_analyst": {"enabled": True}}},
            }
            finding = {
                "title": "Null deref",
                "severity": "Medium",
                "repository": "app",
                "file": "a.py",
                "trigger": "x is null",
                "root_cause": "null",
            }
            for day in ("01", "02", "03"):
                ingest_scan_risk(
                    workspace=workspace,
                    scan={
                        "scan_status": "completed",
                        "finished_at": f"2026-08-{day}T01:00:00Z",
                        "findings": [finding],
                    },
                    registry={"issues": []},
                    common=common,
                    result_path=workspace / "results" / f"{day}.json",
                )
            store = RiskStore(workspace)
            row = store.list_findings("demo")[0]
            self.assertEqual(int(row["occurrence_count"]), 3)
            self.assertEqual(int(row["recurrence_count"]), 0)
            self.assertEqual(int(row["consecutive_seen_count"]), 3)
            store.close()

    def test_resolved_reappears_as_reopened(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            store = RiskStore(workspace)
            store.execute(
                """
                INSERT INTO finding(
                    id, project_slug, canonical_fingerprint, title, status, source_severity,
                    effective_severity, recurrence_count, reopened_count, occurrence_count,
                    consecutive_seen_count, verification_status, remediation_status
                ) VALUES ('FIND-1', 'demo', 'fp1', 'x', 'Resolved', 'High', 'High', 0, 0, 1, 0, 'verified_clean', 'remediated')
                """
            )
            store.commit()
            status = apply_seen(store, "FIND-1", STATUS_RESOLVED, "2026-08-05T00:00:00Z", scan_run_id="scan-1")
            self.assertEqual(status, STATUS_REOPENED)
            row = store.get_finding("FIND-1")
            self.assertEqual(int(row["recurrence_count"]), 1)
            self.assertEqual(int(row["reopened_count"]), 1)
            store.close()

    def test_ignore_invalidation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            store = RiskStore(workspace)
            store.execute(
                """
                INSERT INTO finding(
                    id, project_slug, canonical_fingerprint, title, status, source_severity,
                    effective_severity, recurrence_count, reopened_count, occurrence_count,
                    consecutive_seen_count, verification_status, remediation_status, current_risk_score
                ) VALUES ('FIND-2', 'demo', 'fp2', 'y', 'Ignored', 'Medium', 'Medium', 0, 0, 1, 1, 'observed', 'none', 10)
                """
            )
            upsert_ignore_policy(store, "FIND-2", reason="accepted")
            store.commit()
            changed = invalidate_ignore_if_needed(
                store,
                "FIND-2",
                severity_upgraded=True,
                score_delta=20,
                reopened=False,
            )
            self.assertTrue(changed)
            row = store.get_finding("FIND-2")
            self.assertEqual(row["status"], STATUS_OPEN)
            store.close()

    def test_migration_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            conn = connect(Path(tmp) / "risk.sqlite3")
            version = conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0]
            self.assertEqual(int(version), SCHEMA_VERSION)
            cols = {row[1] for row in conn.execute("PRAGMA table_info(finding)").fetchall()}
            self.assertIn("occurrence_count", cols)
            self.assertIn("verification_status", cols)
            conn.close()


class AlertRetryTests(unittest.TestCase):
    def test_failed_send_not_deduped_as_sent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            store = RiskStore(workspace)
            store.execute(
                """
                INSERT INTO finding(
                    id, project_slug, canonical_fingerprint, title, status, source_severity,
                    effective_severity, first_seen_at, current_risk_score, current_risk_band,
                    occurrence_count, consecutive_seen_count, verification_status, remediation_status
                ) VALUES ('FIND-H', 'demo', 'fph', 'High issue', 'Open', 'High', 'High',
                          '2026-08-04T00:00:00Z', 80, 'High', 1, 1, 'observed', 'none')
                """
            )
            store.commit()
            alerts = evaluate_alerts(
                store,
                project_slug="demo",
                events=[{"type": "new_finding", "finding_id": "FIND-H", "severity": "High"}],
                config=RiskConfig(enabled=True, alert_chat_id="oc_test", overdue_days=30),
            )
            self.assertEqual(len(alerts), 1)

            class Boom:
                def send_card(self, chat_id, card):
                    raise RuntimeError("feishu down")

            with patch("feishu.messenger.FeishuMessenger", return_value=Boom()):
                with patch.dict("sys.modules", {"feishu.risk_cards": MagicMock(risk_alert_card=lambda *a, **k: {})}):
                    delivered = deliver_alerts(
                        store,
                        project_slug="demo",
                        alerts=alerts,
                        config=RiskConfig(enabled=True, alert_chat_id="oc_test"),
                    )
            self.assertEqual(delivered[0]["status"], "failed")
            self.assertFalse(store.alert_already_sent("demo", alerts[0]["event_key"]))
            row = store.get_alert("demo", alerts[0]["event_key"])
            self.assertEqual(row["status"], "failed")
            store.close()


class ContextIsolationTests(unittest.TestCase):
    def test_context_and_recent_run_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["LUMEN_AGENTS_HOME"] = tmp
            gs = GlobalAgentStore(Path(tmp) / "agents.sqlite3")
            gs.save_agent_run(
                {
                    "run_id": "scan-thread-a",
                    "agent_id": "dylan",
                    "project_slug": "mbpass",
                    "chat_id": "chat1",
                    "thread_id": "t1",
                    "user_id": "u1",
                    "action": "scan.run",
                    "status": "completed",
                }
            )
            gs.save_agent_run(
                {
                    "run_id": "scan-thread-b",
                    "agent_id": "dylan",
                    "project_slug": "other",
                    "chat_id": "chat1",
                    "thread_id": "t2",
                    "user_id": "u1",
                    "action": "scan.run",
                    "status": "completed",
                }
            )
            row = gs.resolve_recent_run(chat_id="chat1", thread_id="t1", user_id="u1")
            self.assertEqual(row["run_id"], "scan-thread-a")
            gs.upsert_conversation_context(
                {
                    "chat_id": "chat1",
                    "thread_id": "t1",
                    "user_id": "u1",
                    "project_slug": "mbpass",
                    "last_intent": "risk.top",
                    "last_result_ids": ["FIND-1", "FIND-2"],
                    "last_finding_id": "FIND-1",
                }
            )
            ctx = gs.get_conversation_context(chat_id="chat1", thread_id="t1", user_id="u1")
            self.assertEqual(ctx["project_slug"], "mbpass")
            other = gs.get_conversation_context(chat_id="chat1", thread_id="t2", user_id="u1")
            self.assertTrue(other is None or other["project_slug"] != "mbpass" or other["id"] != ctx["id"])
            gs.close()
            os.environ.pop("LUMEN_AGENTS_HOME", None)


class GroundingTests(unittest.TestCase):
    def test_rejects_invented_finding(self) -> None:
        result = validate_response(
            "看 FIND-deadbeef01",
            [{"tool": "query_top_risks", "data": {"items": [{"id": "FIND-aaaaaaaaaaaa"}]}}],
        )
        self.assertFalse(result["valid"])
        self.assertEqual(result["violations"][0]["type"], "unknown_finding")


class ConversationIntegrationTests(unittest.TestCase):
    def test_greeting_and_relationship_without_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["LUMEN_AGENTS_HOME"] = tmp
            common = {
                "agents": {
                    "dylan": {
                        "risk_analyst": {
                            "enabled": True,
                            "conversation_v2": {"enabled": True, "grounding_guard_enabled": True},
                        }
                    }
                }
            }
            hello = handle_conversation(
                text="你好",
                meta={"chat_id": "c1", "thread_id": "t1", "user_id": "u1"},
                common=common,
                agents_config=common["agents"],
            )
            self.assertEqual(hello["action"], "conversation.greeting")
            self.assertIn("Dylan", hello["text"])
            self.assertNotIn("扫描 mbpass", hello["text"])

            rel = handle_conversation(
                text="你和 Mark 關係好嗎？",
                meta={"chat_id": "c1", "thread_id": "t1", "user_id": "u1"},
                common=common,
                agents_config=common["agents"],
            )
            self.assertEqual(rel["action"], "conversation.agent_relationship")
            self.assertIn("Mark", rel["text"])
            os.environ.pop("LUMEN_AGENTS_HOME", None)


if __name__ == "__main__":
    unittest.main()
