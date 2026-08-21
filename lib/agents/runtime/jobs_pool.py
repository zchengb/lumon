from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Optional

from agents.runtime.jobs import ConversationJobStore, ScopeLockManager
from feishu.config import load_agents_config
from risk.store import utc_now

_LOG = logging.getLogger("lumen.agent.runtime")
_EXECUTOR: Optional[ThreadPoolExecutor] = None
_SCOPE_LOCKS = ScopeLockManager()


def _max_workers() -> int:
    try:
        cfg = load_agents_config()
        dylan = cfg.get("dylan") if isinstance(cfg.get("dylan"), dict) else {}
        mark = cfg.get("mark") if isinstance(cfg.get("mark"), dict) else {}
        return max(int(dylan.get("max_concurrent_jobs") or mark.get("max_concurrent_jobs") or 3), 1)
    except Exception:
        return 3


def get_executor() -> ThreadPoolExecutor:
    global _EXECUTOR
    if _EXECUTOR is None:
        _EXECUTOR = ThreadPoolExecutor(max_workers=_max_workers(), thread_name_prefix="agent-conv")
    return _EXECUTOR


def _prepare_conversation_job(
    *,
    message_id: str,
    chat_id: str,
    thread_id: str,
    user_id: str,
    agent_id: str = "",
) -> dict[str, Any]:
    bootstrap = ConversationJobStore()
    try:
        # The same Feishu inbound message may intentionally wake several
        # Agents.  conversation_job predates Thread-native collaboration and
        # has a global UNIQUE(message_id), so scope its compatibility record
        # by Agent while preserving the old key for callers without one.
        base_message_id = message_id or f"local-{chat_id}-{thread_id}-{user_id}"
        normalized_agent = str(agent_id or "").strip().lower()
        job_message_id = (
            f"{base_message_id}::agent:{normalized_agent}" if normalized_agent else base_message_id
        )
        existing = bootstrap.get_by_message_id(job_message_id) if job_message_id else None
        if existing is not None:
            return {"status": "duplicate", "job": existing}
        job = bootstrap.create(
            {
                "message_id": job_message_id,
                "chat_id": chat_id,
                "thread_id": thread_id,
                "user_id": user_id,
                "state": "queued",
            }
        )
        return {"status": "queued", "job": job, "job_message_id": job_message_id}
    finally:
        bootstrap.close()


def _execute_conversation_job(
    *,
    job_message_id: str,
    chat_id: str,
    thread_id: str,
    agent_id: str,
    worker: Callable[[], Any],
) -> Any:
    jobs = ConversationJobStore()
    try:
        # A Thread is a shared blackboard, not a global single-writer lock.
        # Serialize only one inbound event per Agent session; peers in the
        # same Thread must be able to work concurrently.
        lock = _SCOPE_LOCKS.lock_for(chat_id, f"{thread_id}::{str(agent_id or '').strip().lower()}")
        with lock:
            jobs.update(job_message_id, state="routing")
            try:
                result = worker()
                jobs.update(
                    job_message_id,
                    state="completed",
                    intent=str((result or {}).get("action") or ""),
                    completed_at=utc_now(),
                )
                return result
            except Exception as exc:
                _LOG.exception("conversation job failed")
                jobs.update(
                    job_message_id,
                    state="failed",
                    error_code="worker_error",
                    error_detail=str(exc)[:300],
                )
                raise
    finally:
        jobs.close()


def run_conversation_job(
    *,
    message_id: str,
    chat_id: str,
    thread_id: str,
    user_id: str,
    agent_id: str = "",
    worker: Callable[[], Any],
) -> dict[str, Any]:
    """Run on the current thread. Prefer this from Feishu pool workers to avoid nested-pool deadlock."""
    prepared = _prepare_conversation_job(
        message_id=message_id,
        chat_id=chat_id,
        thread_id=thread_id,
        user_id=user_id,
        agent_id=agent_id,
    )
    if prepared.get("status") == "duplicate":
        return prepared
    result = _execute_conversation_job(
        job_message_id=str(prepared["job_message_id"]),
        chat_id=chat_id,
        thread_id=thread_id,
        agent_id=agent_id,
        worker=worker,
    )
    return {"status": "completed", "job": prepared.get("job"), "result": result}


def submit_conversation_job(
    *,
    message_id: str,
    chat_id: str,
    thread_id: str,
    user_id: str,
    agent_id: str = "",
    worker: Callable[[], Any],
) -> dict[str, Any]:
    prepared = _prepare_conversation_job(
        message_id=message_id,
        chat_id=chat_id,
        thread_id=thread_id,
        user_id=user_id,
        agent_id=agent_id,
    )
    if prepared.get("status") == "duplicate":
        return prepared
    job_message_id = str(prepared["job_message_id"])
    job = prepared.get("job")

    def _run() -> Any:
        return _execute_conversation_job(
            job_message_id=job_message_id,
            chat_id=chat_id,
            thread_id=thread_id,
            agent_id=agent_id,
            worker=worker,
        )

    future = get_executor().submit(_run)
    return {"status": "queued", "job": job, "future": future}
