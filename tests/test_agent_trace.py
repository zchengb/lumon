import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "lib" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from agent_trace import Redactor, cleanup_retention, run_agent, trace_config
from dashboard_server import DashboardServer, agent_activity_payload, delivery_trace_payload
from risk.migrations import connect_global


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


class AgentTraceTest(unittest.TestCase):
    def workspace(self, root: Path, mode: str = "full") -> tuple[Path, Path]:
        repo = root / "lumen" / "worktrees" / "DEMO-1" / "app"
        repo.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.com"], check=True)
        subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
        (repo / "README.md").write_text("before\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repo), "add", "README.md"], check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-qm", "init"], check=True)
        story = root / "stories" / "DEMO-1-trace"
        story.mkdir(parents=True)
        (story / "story.md").write_text("# Trace story\n\nCapture agent evidence safely while preserving provider output, timing, and file changes for local debugging.\n", encoding="utf-8")
        (story / "technical-plan.md").write_text("# Plan\n\nRun a controlled documentation change, capture structured provider events, redact secrets, and verify the complete local trace.\n", encoding="utf-8")
        write_json(story / "metadata.json", {"jiraKey": "DEMO-1", "linkedRepos": ["app"], "businessStatus": "ready", "technicalStatus": "approved"})
        write_json(root / "lumen" / "config" / "workspace.json", {"layout": "nested", "workspace_root": ".", "repos_dir": "repos", "repositories": [{"name": "app", "path": "repos/app"}]})
        write_json(root / "lumen" / "config" / "delivery.json", {"observability": {"agent_trace": {"enabled": True, "capture_mode": mode, "retention_days": 14}}})
        # load_story_context resolves the configured source, then derives this Story worktree.
        source = root / "repos" / "app"
        source.parent.mkdir(parents=True)
        subprocess.run(["git", "clone", "-q", str(repo), str(source)], check=True)
        return repo, story

    def args(self, root: Path, command: list[str], stage: str = "implementation", attempt: int = 1):
        return type("Args", (), {
            "workspace_root": str(root), "docs_dir": str(root), "story": "DEMO-1", "run_id": "20260719-120000",
            "stage": stage, "attempt": attempt, "provider": "fake", "model": "test", "output_format": "stream-json",
            "sandbox": "workspace-write", "lumen_version": "test", "provider_version": "test", "timeout": 5, "idle_timeout": 0,
            "command": command,
        })()

    def test_safe_defaults_and_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.assertEqual("metadata", trace_config(root)["capture_mode"])
            write_json(root / "lumen" / "config" / "delivery.json", {"observability": {"agent_trace": {"capture_mode": "bad"}}})
            with self.assertRaisesRegex(ValueError, "capture_mode"):
                trace_config(root)

    def test_redacts_common_and_workspace_secrets(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "lumen").mkdir()
            (root / "lumen" / ".env.local").write_text("CURSOR_API_KEY=exact-secret\n", encoding="utf-8")
            output = Redactor(root).text('Authorization: Bearer abc password=hunter2 {"access_token":"json-secret"} postgres://u:pass@host/db exact-secret\n-----BEGIN PRIVATE KEY-----\nsecret\n-----END PRIVATE KEY-----')
            for secret in ("abc", "hunter2", "json-secret", ":pass@", "exact-secret", "\nsecret\n"):
                self.assertNotIn(secret, output)
            self.assertIn("[REDACTED]", output)

    def test_full_trace_streams_events_separates_logs_and_attributes_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repo, _ = self.workspace(root)
            secret = "fake-secret-123"
            (root / "lumen" / ".env.local").write_text(f"CURSOR_API_KEY={secret}\n", encoding="utf-8")
            script = """import json,pathlib,sys,time
repo=pathlib.Path(sys.argv[1].splitlines()[0])
def emit(x): print(json.dumps(x), flush=True)
emit({'type':'system','subtype':'init','session_id':'s-1','model':'fake'})
emit({'type':'assistant','message':{'content':[{'type':'text','text':'starting fake-secret-123'}]}})
emit({'type':'tool_call','subtype':'started','tool_call_id':'t-1','tool_call':{'writeToolCall':{'args':{'path':str(repo/'README.md')}}}})
time.sleep(.01); (repo/'README.md').write_text('after\\n')
emit({'type':'tool_call','subtype':'completed','tool_call_id':'t-1','tool_call':{'writeToolCall':{'result':{'success':{}}}}})
print('not-json', flush=True)
print('warning fake-secret-123', file=sys.stderr, flush=True)
print('-----BEGIN PRIVATE KEY-----\\nprivate-body\\n-----END PRIVATE KEY-----', file=sys.stderr, flush=True)
emit({'type':'result','request_id':'r-1','duration_ms':12,'duration_api_ms':8,'result':'done fake-secret-123'})
"""
            old_stdin = sys.stdin
            try:
                sys.stdin = type("Input", (), {"read": lambda _self: str(repo) + "\npassword=" + secret})()
                code = run_agent(self.args(root, [sys.executable, "-c", script]))
            finally:
                sys.stdin = old_stdin
            self.assertEqual(0, code)
            invocation = root / "lumen" / "results" / "agent-traces" / "20260719-120000" / "agents" / "implementation-001"
            self.assertTrue((invocation / "prompt.md").is_file())
            self.assertTrue((invocation / "context-manifest.json").is_file())
            self.assertNotIn(secret, "".join(path.read_text(encoding="utf-8") for path in invocation.iterdir() if path.is_file()))
            self.assertIn("warning", (invocation / "stderr.log").read_text(encoding="utf-8"))
            self.assertNotIn("warning", (invocation / "stdout.log").read_text(encoding="utf-8"))
            self.assertNotIn("private-body", (invocation / "stderr.log").read_text(encoding="utf-8"))
            events = (invocation / "events.ndjson").read_text(encoding="utf-8")
            self.assertIn("agent.tool.completed", events)
            self.assertIn("trace.parse.warning", events)
            result = json.loads((invocation / "result.json").read_text(encoding="utf-8"))
            self.assertEqual(1, result["tool_calls"])
            self.assertEqual("Write", result["tool_summary"][0]["name"])
            self.assertGreaterEqual(result["tool_summary"][0]["longest_duration_ms"], 1)
            self.assertEqual(1, result["files_changed"])
            self.assertEqual("partial", result["trace_completeness"])
            delivery = json.loads((root / "lumen" / "results" / "delivery-result.json").read_text(encoding="utf-8"))
            self.assertEqual("20260719-120000", delivery["agent_trace"]["trace_id"])

    def test_metadata_omits_prompt_and_log_bodies_and_failure_keeps_trace(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.workspace(root, "metadata")
            old_stdin = sys.stdin
            try:
                sys.stdin = type("Input", (), {"read": lambda _self: "secret prompt"})()
                code = run_agent(self.args(root, [sys.executable, "-c", "import sys; print('body'); print('error',file=sys.stderr); sys.exit(7)"]))
            finally:
                sys.stdin = old_stdin
            invocation = root / "lumen" / "results" / "agent-traces" / "20260719-120000" / "agents" / "implementation-001"
            self.assertEqual(7, code)
            self.assertFalse((invocation / "prompt.md").exists())
            self.assertEqual("", (invocation / "stdout.log").read_text(encoding="utf-8"))
            self.assertEqual("", (invocation / "stderr.log").read_text(encoding="utf-8"))
            self.assertEqual("failed", json.loads((invocation / "result.json").read_text())["status"])

    def test_remediation_ids_and_retention(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            trace_root = root / "lumen" / "results" / "agent-traces"
            old = trace_root / "old"; active = trace_root / "active"
            old.mkdir(parents=True); active.mkdir()
            stale = time.time() - 20 * 86400
            os.utime(old, (stale, stale)); os.utime(active, (stale, stale))
            cleanup_retention(root, "active", 14)
            self.assertFalse(old.exists())
            self.assertTrue(active.exists())

    def test_timeout_and_multiple_remediation_attempts_keep_separate_partial_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.workspace(root, "metadata")
            old_stdin = sys.stdin
            try:
                for attempt in (1, 2):
                    sys.stdin = type("Input", (), {"read": lambda _self: "remediate"})()
                    code = run_agent(self.args(root, [sys.executable, "-c", "print('ok')"], "remediation", attempt))
                    self.assertEqual(0, code)
                timeout_args = self.args(root, [sys.executable, "-c", "import time; time.sleep(2)"], "implementation", 1)
                timeout_args.timeout = 1
                sys.stdin = type("Input", (), {"read": lambda _self: "timeout"})()
                self.assertEqual(124, run_agent(timeout_args))
            finally:
                sys.stdin = old_stdin
            agents = root / "lumen" / "results" / "agent-traces" / "20260719-120000" / "agents"
            self.assertTrue((agents / "remediation-001" / "result.json").is_file())
            self.assertTrue((agents / "remediation-002" / "result.json").is_file())
            self.assertEqual("timed_out", json.loads((agents / "implementation-001" / "result.json").read_text())["status"])

    def test_idle_timeout_stops_a_silent_agent_before_total_timeout(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.workspace(root, "metadata")
            args = self.args(root, [sys.executable, "-c", "import time; print('working', flush=True); time.sleep(3)"])
            args.timeout, args.idle_timeout = 5, 1
            old_stdin = sys.stdin
            try:
                sys.stdin = type("Input", (), {"read": lambda _self: "idle"})()
                self.assertEqual(124, run_agent(args))
            finally:
                sys.stdin = old_stdin
            result = json.loads((root / "lumen" / "results" / "agent-traces" / "20260719-120000" / "agents" / "implementation-001" / "result.json").read_text())
            self.assertEqual("idle_timed_out", result["status"])

    def test_dashboard_caps_large_evidence_and_settings_preserve_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "lumen"
            invocation = workspace / "results" / "agent-traces" / "run-1" / "agents" / "implementation-001"
            invocation.mkdir(parents=True)
            write_json(invocation.parent.parent / "trace.json", {"trace_id": "run-1", "capture_mode": "full", "invocations": [{"invocation_id": "implementation-001"}]})
            for name in ("request.json", "result.json", "context-manifest.json", "changed-files.json"):
                write_json(invocation / name, {})
            (invocation / "events.ndjson").write_text('{"event_id":"one","type":"agent.process.started"}\n', encoding="utf-8")
            (invocation / "stdout.log").write_text("x" * 100_000, encoding="utf-8")
            payload = delivery_trace_payload(workspace, "run-1")
            self.assertTrue(payload["invocations"][0]["truncated"]["stdout"])
            self.assertEqual(65536, len(payload["invocations"][0]["stdout"]))
            write_json(workspace / "config" / "delivery.json", {"preserved": True})
            saved = DashboardServer.update_observability(None, workspace, {"capture_mode": "full", "retention_days": 21})
            self.assertEqual("full", saved["capture_mode"])
            self.assertTrue(json.loads((workspace / "config" / "delivery.json").read_text())["preserved"])

    def test_dashboard_activity_read_model_keeps_request_result_and_role(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            database_root = Path(temp)
            previous_agents_home = os.environ.get("LUMEN_AGENTS_HOME")
            os.environ["LUMEN_AGENTS_HOME"] = str(database_root)
            try:
                connection = connect_global(database_root / "agents.sqlite3")
                connection.execute(
                    """
                    INSERT INTO conversation_trace(
                        trace_id, message_id, project_slug, state, started_at, latency_ms
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    ("tr_test_activity", "msg-1", "mbpass", "completed", "2026-01-01T00:00:00Z", 1200),
                )
                connection.execute(
                    """
                    INSERT INTO conversation_event(trace_id, event, payload_json, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    ("tr_test_activity", "conversation.request", json.dumps({"agent_id": "mark", "role": "delivery", "workflow": "auto_delivery", "text": "Please check this Story."}), "2026-01-01T00:00:00Z"),
                )
                connection.execute(
                    """
                    INSERT INTO conversation_event(trace_id, event, payload_json, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    ("tr_test_activity", "conversation.completed", json.dumps({"agent_id": "mark", "role": "delivery", "workflow": "auto_delivery", "status": "completed", "action": "delivery.status", "text": "The Story is ready."}), "2026-01-01T00:00:01Z"),
                )
                connection.commit()
                connection.close()
                payload = agent_activity_payload("mbpass")
                self.assertTrue(payload["available"])
                item = payload["items"][0]
                self.assertEqual("mark", item["agent_id"])
                self.assertEqual("auto_delivery", item["workflow"])
                self.assertEqual("Please check this Story.", item["request_text"])
                self.assertEqual("The Story is ready.", item["response_text"])
            finally:
                if previous_agents_home is None:
                    os.environ.pop("LUMEN_AGENTS_HOME", None)
                else:
                    os.environ["LUMEN_AGENTS_HOME"] = previous_agents_home

    def test_archive_copies_trace_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            trace = root / "lumen" / "results" / "agent-traces" / "run-1"
            trace.mkdir(parents=True)
            write_json(trace / "trace.json", {"trace_id": "run-1"})
            result = root / "lumen" / "results" / "delivery-result.json"
            write_json(result, {"run_id": "run-1", "delivery_status": "failed", "agent_trace": {"path": "results/agent-traces/run-1"}})
            subprocess.run([sys.executable, str(SCRIPTS / "archive_delivery_run.py"), "--workspace-root", str(root), "--result", str(result)], check=True, capture_output=True, text=True)
            self.assertTrue((root / "lumen" / "history" / "delivery" / "run-1" / "agent-trace" / "trace.json").is_file())

    def test_archive_ignores_missing_or_unsafe_trace_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lumen = root / "lumen"
            trace_root = lumen / "results" / "agent-traces"
            trace_root.mkdir(parents=True)
            result = lumen / "results" / "delivery-result.json"
            write_json(result, {"run_id": "run-unsafe", "delivery_status": "failed", "agent_trace": {}})
            subprocess.run(
                [sys.executable, str(SCRIPTS / "archive_delivery_run.py"), "--workspace-root", str(root), "--result", str(result)],
                check=True,
                capture_output=True,
                text=True,
            )
            archive = lumen / "history" / "delivery" / "run-unsafe"
            self.assertTrue((archive.with_suffix(".json")).is_file())
            self.assertFalse((archive / "agent-trace").exists())

            write_json(trace_root / "trace.json", {"trace_id": "root"})
            write_json(result, {"run_id": "run-root", "delivery_status": "failed", "agent_trace": {"path": "results/agent-traces"}})
            subprocess.run(
                [sys.executable, str(SCRIPTS / "archive_delivery_run.py"), "--workspace-root", str(root), "--result", str(result)],
                check=True,
                capture_output=True,
                text=True,
            )
            root_archive = lumen / "history" / "delivery" / "run-root"
            self.assertTrue((root_archive.with_suffix(".json")).is_file())
            self.assertFalse((root_archive / "agent-trace").exists())

    def test_committed_agent_change_is_still_attributed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repo, _ = self.workspace(root, "metadata")
            script = """import pathlib,subprocess,sys
repo=pathlib.Path(sys.argv[1]); (repo/'README.md').write_text('committed by agent\\n')
subprocess.run(['git','-C',str(repo),'add','README.md'],check=True)
subprocess.run(['git','-C',str(repo),'commit','-qm','agent change'],check=True)
"""
            old_stdin = sys.stdin
            try:
                sys.stdin = type("Input", (), {"read": lambda _self: str(repo)})()
                self.assertEqual(0, run_agent(self.args(root, [sys.executable, "-c", script, str(repo)])))
            finally:
                sys.stdin = old_stdin
            changed = json.loads((root / "lumen" / "results" / "agent-traces" / "20260719-120000" / "agents" / "implementation-001" / "changed-files.json").read_text())
            self.assertEqual(["README.md"], [item["path"] for item in changed["files"]])


if __name__ == "__main__":
    unittest.main()
