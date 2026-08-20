from __future__ import annotations

import logging
import json
from pathlib import Path
from typing import Any

from agents.security.actions import ActionRequest
from agents.security.errors import CapabilityDenied, ResourceDenied
from feishu.messenger import FeishuMessenger, extract_message_id, should_reply_in_thread


_LOG = logging.getLogger("lumen.security.feishu")
_MAX_PROGRESS_CHARS = 4_000
_MAX_FILE_BYTES = 20 * 1024 * 1024


def _workspace_root(request: ActionRequest) -> Path:
    raw = str((request.arguments or {}).get("_workspace_path") or "").strip()
    if not raw:
        raise ResourceDenied("Host workspace context is required")
    root = Path(raw).expanduser()
    if not root.is_absolute():
        raise ResourceDenied("Host workspace context must be an absolute path")
    try:
        resolved = root.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ResourceDenied("Host workspace is unavailable") from exc
    if not resolved.is_dir():
        raise ResourceDenied("Host workspace is not a directory")
    return resolved


def _source_message_id(request: ActionRequest) -> str:
    message_id = str(request.source_message_id or "").strip()
    if not message_id:
        raise ResourceDenied("Current source message is unavailable")
    return message_id


def _reply_in_thread(request: ActionRequest) -> bool:
    return should_reply_in_thread(
        {
            "thread_id": request.thread_id,
            "chat_type": str((request.arguments or {}).get("chat_type") or ""),
        }
    )


def _conversation_meta(request: ActionRequest) -> dict[str, Any]:
    args = request.arguments or {}
    return {
        "message_id": request.source_message_id,
        "chat_id": request.chat_id,
        "thread_id": request.thread_id,
        "root_id": str(args.get("_root_id") or request.source_message_id or "").strip(),
        "chat_type": str(args.get("chat_type") or "").strip(),
        "user_id": request.actor_user_id,
        "_origin_user_id": str(args.get("_origin_user_id") or request.actor_user_id or "").strip(),
        "_source_agent": str(args.get("_source_agent") or "").strip().lower(),
        "_relay_id": str(args.get("_relay_id") or "").strip(),
        "_relay_hop": str(args.get("_relay_hop") or "").strip(),
        "_relay_visited": str(args.get("_relay_visited") or "").strip(),
        "_project_slug": request.project_slug,
        "_thread_native_handoff": str(args.get("_thread_native_handoff") or "").strip(),
    }


def _workspace_common(root: Path) -> dict[str, Any]:
    path = root / "config" / "common.json"
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, TypeError, ValueError):
        return {}


def _optional_workspace_common(request: ActionRequest) -> dict[str, Any]:
    raw = str((request.arguments or {}).get("_workspace_path") or "").strip()
    if not raw:
        return {}
    root = Path(raw).expanduser()
    return _workspace_common(root) if root.is_dir() else {}


def _reply_agent_text_or_markdown(
    messenger: FeishuMessenger,
    message_id: str,
    text: str,
    *,
    reply_in_thread: bool,
    conversation_meta: dict[str, Any],
    conversation_common: dict[str, Any],
) -> dict[str, Any] | None:
    method = getattr(messenger, "reply_agent_text", None)
    if callable(method):
        return method(
            message_id,
            text,
            reply_in_thread=reply_in_thread,
            conversation_meta=conversation_meta,
            conversation_common=conversation_common,
        )
    # Compatibility for narrow test doubles and older integrations.  The
    # real FeishuMessenger always takes the transcript-aware path above.
    return messenger.reply_markdown(message_id, text, reply_in_thread=reply_in_thread)


def _as_bool(value: Any, *, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().casefold()
        if normalized in {"1", "true", "yes", "y", "on"}:
            return True
        if normalized in {"0", "false", "no", "n", "off"}:
            return False
    return default


def _secret_filename(name: str) -> bool:
    value = str(name or "").strip().casefold()
    return (
        value == ".env"
        or value.startswith(".env.")
        or value.endswith((".pem", ".key", ".p12", ".pfx"))
        or value in {"id_rsa", "id_ed25519", "authorized_keys"}
    )


def _resolve_upload_file(request: ActionRequest) -> tuple[Path, Path]:
    root = _workspace_root(request)
    args = dict(request.arguments or {})
    resource = dict(request.resource or {})
    raw = str(args.get("path") or resource.get("path") or "").strip()
    if not raw:
        raise ResourceDenied("path is required")

    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        candidate = root / candidate
    if candidate.is_symlink():
        raise ResourceDenied("symlink uploads are not allowed")
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, RuntimeError, ValueError) as exc:
        raise ResourceDenied("file must be inside the current workspace") from exc
    if not resolved.is_file():
        raise ResourceDenied("path must point to a regular file")
    if _secret_filename(resolved.name):
        raise ResourceDenied("secret-like files cannot be uploaded")
    try:
        size = resolved.stat().st_size
    except OSError as exc:
        raise ResourceDenied("file metadata is unavailable") from exc
    if size > _MAX_FILE_BYTES:
        raise ResourceDenied(f"file exceeds the {_MAX_FILE_BYTES // (1024 * 1024)} MB upload limit")
    return root, resolved


def _is_generated_pdf(root: Path, path: Path) -> bool:
    output_dir = root / "output" / "pdf"
    try:
        return (
            output_dir.is_dir()
            and path.parent == output_dir.resolve(strict=True)
            and path.suffix.casefold() == ".pdf"
        )
    except (OSError, RuntimeError):
        return False


def _cleanup_generated_file(path: Path) -> bool:
    try:
        path.unlink()
        return True
    except OSError as exc:
        _LOG.warning("Feishu action cleanup failed path=%s err=%s", path, exc)
        return False


def _relative_path(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return path.name


def _send_progress(request: ActionRequest) -> dict[str, Any]:
    args = dict(request.arguments or {})
    message = str(args.get("message") or "").strip()
    if not message:
        raise ResourceDenied("message is required")
    if len(message) > _MAX_PROGRESS_CHARS:
        raise ResourceDenied(f"progress message exceeds {_MAX_PROGRESS_CHARS} characters")
    phase = str(args.get("phase") or "").strip()
    if len(phase) > 120:
        raise ResourceDenied("phase exceeds 120 characters")
    body = f"**{phase}**\n\n{message}" if phase else message
    messenger = FeishuMessenger(request.agent_id)
    response = _reply_agent_text_or_markdown(
        messenger,
        _source_message_id(request),
        body,
        reply_in_thread=_reply_in_thread(request),
        conversation_meta=_conversation_meta(request),
        conversation_common=_optional_workspace_common(request),
    )
    message_id = extract_message_id(response)
    if not message_id:
        raise RuntimeError("Feishu progress reply did not return a message ID")
    return {
        "kind": "progress",
        "status": "sent",
        "phase": phase,
        "message_id": message_id,
    }


def _send_file(request: ActionRequest) -> dict[str, Any]:
    root, path = _resolve_upload_file(request)
    args = dict(request.arguments or {})
    caption = str(args.get("caption") or "").strip()
    if len(caption) > _MAX_PROGRESS_CHARS:
        raise ResourceDenied(f"caption exceeds {_MAX_PROGRESS_CHARS} characters")

    generated_pdf = _is_generated_pdf(root, path)
    cleanup_requested = _as_bool(args.get("cleanup"), default=generated_pdf)
    if cleanup_requested and not generated_pdf:
        raise ResourceDenied("cleanup is only allowed for generated files under output/pdf")

    messenger = FeishuMessenger(request.agent_id)
    message_id = _source_message_id(request)
    reply_in_thread = _reply_in_thread(request)
    file_key = ""
    caption_message_id = ""
    file_message_id = ""
    cleaned_up = False
    try:
        file_key = messenger.upload_file(path)
        if caption:
            caption_response = _reply_agent_text_or_markdown(
                messenger,
                message_id,
                caption,
                reply_in_thread=reply_in_thread,
                conversation_meta=_conversation_meta(request),
                conversation_common=_workspace_common(root),
            )
            caption_message_id = extract_message_id(caption_response)
        file_response = messenger.reply_file(
            message_id,
            file_key,
            reply_in_thread=reply_in_thread,
        )
        file_message_id = extract_message_id(file_response)
        if not file_message_id:
            raise RuntimeError("Feishu file reply did not return a message ID")
        try:
            from agents.conversation.relay import ConversationRelay

            relay = ConversationRelay()
            try:
                relay.publish(
                    source_agent_id=request.agent_id,
                    source_message_id=file_message_id,
                    text="",
                    meta=_conversation_meta(request),
                    common=_workspace_common(root),
                    attachment_refs=(f"file:{path.name}",),
                )
            finally:
                relay.close()
        except Exception as exc:
            _LOG.warning("Feishu file transcript publication failed message_id=%s err=%s", file_message_id, exc)
    finally:
        if cleanup_requested:
            cleaned_up = _cleanup_generated_file(path)

    return {
        "kind": "file",
        "status": "sent",
        "file_key": file_key,
        "message_id": file_message_id,
        "caption_message_id": caption_message_id,
        "path": _relative_path(root, path),
        "cleaned_up": cleaned_up,
    }


def execute_feishu_action(request: ActionRequest) -> dict[str, Any]:
    if request.action == "feishu.send_progress":
        return _send_progress(request)
    if request.action == "feishu.send_file":
        return _send_file(request)
    raise CapabilityDenied(f"unsupported Feishu action: {request.action}")
