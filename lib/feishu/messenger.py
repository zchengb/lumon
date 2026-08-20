from __future__ import annotations

import json
import logging
import mimetypes
import os
import re
import threading
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from urllib.parse import quote, urlencode
from typing import Any, Callable, Optional

from agents.registry import APP_ID_ENV
from agents.runtime.final_response import sanitize_feishu_answer
from feishu.pdf_renderer import is_plan_document, plan_pdf_filename, render_markdown_pdf, split_plan_response

APP_SECRET_ENV = {
    "dylan": "FEISHU_DYLAN_APP_SECRET",
    "irving": "FEISHU_IRVING_APP_SECRET",
    "mark": "FEISHU_MARK_APP_SECRET",
    "milchick": "FEISHU_MILCHICK_APP_SECRET",
}

TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
REPLY_URL = "https://open.feishu.cn/open-apis/im/v1/messages/{message_id}/reply"
CREATE_URL = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"
UPLOAD_FILE_URL = "https://open.feishu.cn/open-apis/im/v1/files"
UPDATE_URL = "https://open.feishu.cn/open-apis/im/v1/messages/{message_id}"
MESSAGE_RESOURCE_URL = "https://open.feishu.cn/open-apis/im/v1/messages/{message_id}/resources/{file_key}"
REACTION_URL = "https://open.feishu.cn/open-apis/im/v1/messages/{message_id}/reactions"
REACTION_DELETE_URL = "https://open.feishu.cn/open-apis/im/v1/messages/{message_id}/reactions/{reaction_id}"

_LOG = logging.getLogger("lumen.feishu.channel")
_TRANSIENT_MARKERS = (
    "Can't assign requested address",
    "Network is unreachable",
    "nodename nor servname",
    "timed out",
    "Temporary failure",
    "Connection reset",
    "Broken pipe",
)

_MARKDOWN_CARD_LIMIT = 12000
_MARKDOWN_FENCE_OPEN = re.compile(r"(?m)^[ \t]*```(?:markdown|md)[ \t]*$")
_MARKDOWN_FENCE_CLOSE = re.compile(r"(?m)^[ \t]*```[ \t]*$")
# Provider-neutral citation plus backward-compatible provider-prefixed forms:
# :file-citation, :codex-file-citation, :cursor-file-citation,
# :opencode-file-citation, and future <provider>-file-citation markers.
_FILE_CITATION = re.compile(
    r":(?:(?P<provider>[a-z0-9]+(?:[-_][a-z0-9]+)*)[-_])?file-citation"
    r"\{(?P<body>[^{}]*)\}",
    re.IGNORECASE,
)
_FILE_CITATION_PATH = re.compile(r"\bpath\s*=\s*(?P<quote>[\"'])(?P<path>.*?)(?P=quote)", re.IGNORECASE)
_PDF_REQUEST = re.compile(r"(?i)(?:\bpdf\b|pdf\s*(?:file|document)|pdf(?:檔|档|文件|文檔))")
_PDF_NEGATION = re.compile(
    r"(?i)(?:不(?:要|需|需要)|无需|不用|no|without|don't|do not)\s*"
    r"(?:输出|輸出|生成|提供|export|generate|send)?\s*(?:the\s*)?pdf"
)
_TABLE_SEPARATOR = re.compile(r"^:?-{3,}:?$")
_METADATA_FIELD = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*):\s*(.*?)\s*$")


def is_pdf_output_request(text: str) -> bool:
    """Return whether the user explicitly asks for a PDF artifact."""
    raw = str(text or "").strip()
    return bool(_PDF_REQUEST.search(raw)) and not bool(_PDF_NEGATION.search(raw))


def _output_pdf_path(raw_path: str) -> Path | None:
    candidate = Path(str(raw_path or "").strip()).expanduser()
    if not candidate.is_absolute() or candidate.suffix.casefold() != ".pdf":
        return None
    try:
        resolved = candidate.resolve(strict=True)
    except OSError:
        return None
    parts = [part.casefold() for part in resolved.parts]
    if not any(parts[index : index + 2] == ["output", "pdf"] for index in range(max(0, len(parts) - 1))):
        return None
    return resolved if resolved.is_file() else None


def cleanup_generated_plan_pdfs(workspace: str | Path) -> list[Path]:
    """Remove ephemeral plan PDFs from a workspace's dedicated output folder.

    Agent-created PDFs are transfer artifacts, not workspace documents.  Keep
    the cleanup deliberately narrow: only regular ``*.pdf`` files directly
    under ``<workspace>/output/pdf`` are eligible, and symlinks are ignored.
    """

    root = Path(str(workspace or "")).expanduser()
    if not root.is_absolute():
        return []
    try:
        root = root.resolve(strict=True)
    except OSError:
        return []
    if not root.is_dir():
        return []

    output_dir = root / "output" / "pdf"
    try:
        resolved_output_dir = output_dir.resolve(strict=False)
        resolved_output_dir.relative_to(root)
    except OSError:
        return []
    except ValueError:
        # Do not follow a workspace/output/pdf symlink outside the workspace.
        return []
    if not resolved_output_dir.is_dir():
        return []

    removed: list[Path] = []
    for candidate in resolved_output_dir.iterdir():
        if candidate.is_symlink() or not candidate.is_file() or candidate.suffix.casefold() != ".pdf":
            continue
        try:
            candidate.unlink()
            removed.append(candidate)
        except OSError as exc:
            _LOG.warning("plan PDF cleanup failed path=%s err=%s", candidate, exc)
    return removed


def _delete_generated_pdf(path: Path) -> None:
    """Delete one cited PDF after the host has attempted to transfer it."""

    candidate = Path(path)
    if (
        candidate.suffix.casefold() != ".pdf"
        or candidate.parent.name.casefold() != "pdf"
        or candidate.parent.parent.name.casefold() != "output"
    ):
        return
    try:
        if candidate.is_file():
            candidate.unlink()
    except OSError as exc:
        _LOG.warning("cited PDF cleanup failed path=%s err=%s", candidate, exc)


def extract_pdf_file_citation(text: str) -> Path | None:
    """Resolve a generated PDF citation without allowing arbitrary host files."""
    for match in _FILE_CITATION.finditer(str(text or "")):
        path_match = _FILE_CITATION_PATH.search(match.group("body") or "")
        if path_match is None:
            continue
        path = _output_pdf_path(path_match.group("path"))
        if path is not None:
            return path
    return None


def has_pdf_file_citation(text: str) -> bool:
    return extract_pdf_file_citation(text) is not None


def _strip_file_citations(text: str) -> str:
    cleaned = _FILE_CITATION.sub("", str(text or ""))
    cleaned = re.sub(r"(?im)^\s*(?:PDF|file|attachment|附件)\s*:\s*$", "", cleaned)
    return re.sub(r"\n{3,}", "\n\n", cleaned).strip()


def _table_cells(line: str) -> list[str]:
    stripped = str(line or "").strip()
    if "|" not in stripped:
        return []
    inner = stripped[1:-1] if stripped.startswith("|") and stripped.endswith("|") else stripped
    return [cell.replace(r"\|", "|").strip() for cell in re.split(r"(?<!\\)\|", inner)]


def _is_table_separator(line: str) -> bool:
    cells = _table_cells(line)
    return len(cells) >= 2 and all(_TABLE_SEPARATOR.fullmatch(cell.replace(" ", "")) for cell in cells)


def _metadata_label(key: str) -> str:
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", str(key or "").replace("_", " ").replace("-", " "))
    return spaced.strip().title()


def _metadata_value(value: str) -> str:
    text = str(value or "").strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {'"', "'"}:
        text = text[1:-1].strip()
    return f"`{text}`" if text else "—"


def _normalize_metadata_blocks(text: str) -> str:
    """Turn YAML-like front matter into a compact card-friendly metadata section."""
    lines = str(text or "").splitlines()
    output: list[str] = []
    in_code = False
    index = 0
    while index < len(lines):
        line = lines[index]
        if not in_code and line.strip() == "---":
            fields: list[tuple[str, str]] = []
            cursor = index + 1
            while cursor < len(lines):
                if lines[cursor].strip() == "---":
                    break
                match = _METADATA_FIELD.match(lines[cursor].strip())
                if match is None:
                    fields = []
                    break
                fields.append((match.group(1), match.group(2)))
                cursor += 1
            if fields and cursor < len(lines) and lines[cursor].strip() == "---":
                if output and output[-1].strip():
                    output.append("")
                output.append("### Document metadata")
                output.extend(f"- **{_metadata_label(key)}:** {_metadata_value(value)}" for key, value in fields)
                output.append("")
                index = cursor + 1
                continue
        output.append(line)
        if line.strip().startswith("```"):
            in_code = not in_code
        index += 1
    return "\n".join(output).strip()


def _flatten_markdown_tables(text: str) -> str:
    """Replace GFM tables with labeled bullets accepted by Feishu cards."""
    lines = str(text or "").splitlines()
    output: list[str] = []
    in_code = False
    index = 0
    while index < len(lines):
        line = lines[index]
        if not in_code and index + 1 < len(lines) and _table_cells(line) and _is_table_separator(lines[index + 1]):
            headers = _table_cells(line)
            cursor = index + 2
            rows: list[list[str]] = []
            while cursor < len(lines) and not in_code and _table_cells(lines[cursor]):
                cells = _table_cells(lines[cursor])
                if cells:
                    rows.append(cells)
                cursor += 1
            for row in rows:
                pairs = []
                for position, value in enumerate(row):
                    label = headers[position] if position < len(headers) else f"Column {position + 1}"
                    pairs.append(f"**{label}:** {value or '—'}")
                output.append("- " + " · ".join(pairs))
            if rows:
                output.append("")
                index = cursor
                continue
        output.append(line)
        if line.strip().startswith("```"):
            in_code = not in_code
        index += 1
    return "\n".join(output).strip()


def normalize_markdown_for_feishu(text: str) -> str:
    """Render a Markdown document using syntax supported by Feishu cards."""
    raw = str(text or "").strip()
    opening = _MARKDOWN_FENCE_OPEN.search(raw)
    if opening is not None:
        closings = list(_MARKDOWN_FENCE_CLOSE.finditer(raw, opening.end()))
        if closings:
            closing = closings[-1]
            parts = (
                raw[: opening.start()].strip(),
                raw[opening.end() : closing.start()].strip(),
                raw[closing.end() :].strip(),
            )
            raw = "\n\n".join(part for part in parts if part).strip()
    return _flatten_markdown_tables(_normalize_metadata_blocks(raw))


def split_markdown_for_feishu(text: str, *, limit: int = _MARKDOWN_CARD_LIMIT) -> list[str]:
    """Split long Markdown at line boundaries so every card remains renderable."""
    remaining = str(text or "").strip()
    if not remaining:
        return [""]
    parts: list[str] = []
    while len(remaining) > limit:
        cut = remaining.rfind("\n\n", 0, limit + 1)
        if cut < limit // 2:
            cut = remaining.rfind("\n", 0, limit + 1)
        if cut <= 0:
            cut = limit
        parts.append(remaining[:cut].rstrip())
        remaining = remaining[cut:].lstrip("\n")
    parts.append(remaining)
    return parts


def should_reply_in_thread(meta: dict[str, Any] | None = None) -> bool:
    data = meta if isinstance(meta, dict) else {}
    if str(data.get("thread_id") or "").strip():
        return True
    chat_type = str(data.get("chat_type") or "").strip().lower()
    return chat_type not in {"p2p", "private", "dm"}


def extract_message_id(response: dict[str, Any] | None) -> str:
    if not isinstance(response, dict):
        return ""
    data = response.get("data") if isinstance(response.get("data"), dict) else {}
    message = data.get("message") if isinstance(data.get("message"), dict) else {}
    return str(
        response.get("message_id")
        or data.get("message_id")
        or message.get("message_id")
        or ""
    ).strip()


def _is_transient(exc: BaseException) -> bool:
    text = str(exc)
    if any(marker in text for marker in _TRANSIENT_MARKERS):
        return True
    errno = getattr(exc, "errno", None)
    if errno in {8, 49, 51, 54, 60, 61}:
        return True
    cause = getattr(exc, "reason", None) or getattr(exc, "__cause__", None)
    if cause is not None and cause is not exc:
        return _is_transient(cause)
    return False


class FeishuMessenger:
    def __init__(self, agent_id: str = "dylan") -> None:
        self.agent_id = str(agent_id or "dylan").strip().lower()
        self._token = ""
        self._token_expires_at = 0.0
        self._token_lock = threading.Lock()

    def credentials(self) -> tuple[str, str]:
        app_id = os.environ.get(APP_ID_ENV.get(self.agent_id, ""), "").strip()
        app_secret = os.environ.get(APP_SECRET_ENV.get(self.agent_id, ""), "").strip()
        return app_id, app_secret

    def tenant_token(self, *, force: bool = False) -> str:
        now = time.time()
        with self._token_lock:
            if not force and self._token and now < self._token_expires_at:
                return self._token
        app_id, app_secret = self.credentials()
        if not app_id or not app_secret:
            raise RuntimeError(f"Missing Feishu credentials for {self.agent_id}")
        payload = json.dumps({"app_id": app_id, "app_secret": app_secret}).encode("utf-8")
        request = urllib.request.Request(
            TOKEN_URL,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        body = self._urlopen_json(request, retries=4)
        token = str(body.get("tenant_access_token") or "").strip()
        if not token:
            raise RuntimeError(f"Feishu token error: {body.get('msg') or body}")
        # refresh 60s early; Feishu tokens are typically ~2h
        expire = int(body.get("expire") or 7200)
        with self._token_lock:
            self._token = token
            self._token_expires_at = time.time() + max(expire - 60, 60)
        return token

    def _urlopen_json(
        self,
        request: urllib.request.Request,
        *,
        retries: int = 3,
        timeout: float = 30,
    ) -> dict[str, Any]:
        last_exc: BaseException | None = None
        for attempt in range(max(retries, 1)):
            try:
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    raw = response.read().decode("utf-8")
                    return json.loads(raw) if raw.strip() else {}
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")
                raise RuntimeError(f"Feishu API HTTP {exc.code}: {detail}") from exc
            except Exception as exc:
                last_exc = exc
                if attempt + 1 >= retries or not _is_transient(exc):
                    raise
                time.sleep(min(2 ** attempt, 8) + 0.25 * attempt)
        assert last_exc is not None
        raise last_exc

    def _urlopen_bytes(
        self,
        request: urllib.request.Request,
        *,
        retries: int = 3,
        timeout: float = 30,
        max_bytes: int = 20 * 1024 * 1024,
    ) -> tuple[bytes, str]:
        last_exc: BaseException | None = None
        for attempt in range(max(retries, 1)):
            try:
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    body = response.read(max_bytes + 1)
                    if len(body) > max_bytes:
                        raise RuntimeError(f"Feishu resource exceeds {max_bytes} bytes")
                    content_type = str(response.headers.get("Content-Type") or "application/octet-stream")
                    return body, content_type.split(";", 1)[0].strip().lower()
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")
                raise RuntimeError(f"Feishu API HTTP {exc.code}: {detail}") from exc
            except Exception as exc:
                last_exc = exc
                if attempt + 1 >= retries or not _is_transient(exc):
                    raise
                time.sleep(min(2 ** attempt, 8) + 0.25 * attempt)
        assert last_exc is not None
        raise last_exc

    def _request(
        self,
        method: str,
        url: str,
        token: str,
        payload: Optional[dict[str, Any]] = None,
        *,
        retries: int = 4,
        timeout: float = 30,
    ) -> dict[str, Any]:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
            method=method.upper(),
        )
        return self._urlopen_json(request, retries=retries, timeout=timeout)

    def _post(self, url: str, token: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", url, token, payload)

    def upload_file(self, file_path: str | Path) -> str:
        path = Path(file_path).expanduser()
        if not path.is_file():
            raise FileNotFoundError(path)
        token = self.tenant_token()
        boundary = f"----Lumon{uuid.uuid4().hex}"
        body = bytearray()

        def field(name: str, value: str) -> None:
            body.extend(f"--{boundary}\r\n".encode())
            body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
            body.extend(str(value).encode("utf-8"))
            body.extend(b"\r\n")

        field("file_type", "stream")
        field("file_name", path.name)
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'.encode())
        mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        body.extend(f"Content-Type: {mime_type}\r\n\r\n".encode("ascii"))
        body.extend(path.read_bytes())
        body.extend(b"\r\n")
        body.extend(f"--{boundary}--\r\n".encode())
        request = urllib.request.Request(
            UPLOAD_FILE_URL,
            data=bytes(body),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            },
            method="POST",
        )
        response = self._urlopen_json(request, retries=4)
        data = response.get("data") if isinstance(response.get("data"), dict) else {}
        file_key = str(data.get("file_key") or response.get("file_key") or "").strip()
        if not file_key:
            raise RuntimeError(f"Feishu file upload error: {response.get('msg') or response}")
        return file_key

    def add_reaction(self, message_id: str, emoji_type: str) -> dict[str, Any]:
        token = self.tenant_token()
        return self._post(
            REACTION_URL.format(message_id=message_id),
            token,
            {"reaction_type": {"emoji_type": str(emoji_type or "Typing")}},
        )

    def delete_reaction(self, message_id: str, reaction_id: str) -> dict[str, Any]:
        token = self.tenant_token()
        return self._request(
            "DELETE",
            REACTION_DELETE_URL.format(message_id=message_id, reaction_id=reaction_id),
            token,
            None,
        )

    def safe_add_reaction(self, message_id: str, emoji_type: str) -> Optional[dict[str, Any]]:
        try:
            return self.add_reaction(message_id, emoji_type)
        except Exception as exc:
            _LOG.warning("add_reaction failed message_id=%s err=%s", message_id, exc)
            return None

    def safe_delete_reaction(self, message_id: str, reaction_id: str) -> Optional[dict[str, Any]]:
        try:
            return self.delete_reaction(message_id, reaction_id)
        except Exception as exc:
            _LOG.warning("delete_reaction failed message_id=%s reaction_id=%s err=%s", message_id, reaction_id, exc)
            return None

    def reply_text(self, message_id: str, text: str, *, reply_in_thread: bool = False) -> dict[str, Any]:
        token = self.tenant_token()
        payload: dict[str, Any] = {
            "content": json.dumps({"text": text}, ensure_ascii=False),
            "msg_type": "text",
        }
        if reply_in_thread:
            payload["reply_in_thread"] = True
        return self._post(REPLY_URL.format(message_id=message_id), token, payload)

    def reply_markdown(self, message_id: str, text: str, *, reply_in_thread: bool = False) -> dict[str, Any]:
        token = self.tenant_token()
        card = {
            "schema": "2.0",
            "config": {"wide_screen_mode": True},
            "body": {
                "elements": [{"tag": "markdown", "content": str(text or "")[:12000]}],
            },
        }
        payload: dict[str, Any] = {
            "content": json.dumps(card, ensure_ascii=False),
            "msg_type": "interactive",
        }
        if reply_in_thread:
            payload["reply_in_thread"] = True
        return self._post(REPLY_URL.format(message_id=message_id), token, payload)

    def reply_card(self, message_id: str, card_envelope: dict[str, Any], *, reply_in_thread: bool = False) -> dict[str, Any]:
        token = self.tenant_token()
        card = card_envelope.get("card", card_envelope)
        payload: dict[str, Any] = {
            "content": json.dumps(card, ensure_ascii=False),
            "msg_type": "interactive",
        }
        if reply_in_thread:
            payload["reply_in_thread"] = True
        return self._post(REPLY_URL.format(message_id=message_id), token, payload)

    def reply_file(self, message_id: str, file_key: str, *, reply_in_thread: bool = False) -> dict[str, Any]:
        token = self.tenant_token()
        payload: dict[str, Any] = {
            "content": json.dumps({"file_key": str(file_key or "").strip()}, ensure_ascii=False),
            "msg_type": "file",
        }
        if reply_in_thread:
            payload["reply_in_thread"] = True
        return self._post(REPLY_URL.format(message_id=message_id), token, payload)

    def get_message(self, message_id: str) -> dict[str, Any]:
        token = self.tenant_token()
        return self._request(
            "GET",
            UPDATE_URL.format(message_id=message_id),
            token,
            None,
        )

    def get_message_resource(
        self,
        message_id: str,
        file_key: str,
        *,
        resource_type: str = "image",
    ) -> tuple[bytes, str]:
        mid = str(message_id or "").strip()
        key = str(file_key or "").strip()
        kind = str(resource_type or "image").strip().lower() or "image"
        if not mid or not key:
            raise ValueError("message_id and file_key are required")
        if kind not in {"image", "file"}:
            raise ValueError("resource_type must be image or file")
        token = self.tenant_token()
        url = (
            MESSAGE_RESOURCE_URL.format(message_id=quote(mid, safe=""), file_key=quote(key, safe=""))
            + f"?type={quote(kind, safe='')}"
        )
        request = urllib.request.Request(
            url,
            headers={"Authorization": f"Bearer {token}"},
            method="GET",
        )
        return self._urlopen_bytes(request)

    def safe_get_message_resource(
        self,
        message_id: str,
        file_key: str,
        *,
        resource_type: str = "image",
    ) -> Optional[tuple[bytes, str]]:
        try:
            return self.get_message_resource(message_id, file_key, resource_type=resource_type)
        except Exception as exc:
            _LOG.warning(
                "get_message_resource failed message_id=%s file_key=%s err=%s",
                message_id,
                file_key,
                exc,
            )
            return None

    def get_user_profile(self, open_id: str) -> dict[str, str]:
        user_id = str(open_id or "").strip()
        if not user_id:
            return {"open_id": "", "name": "", "union_id": ""}
        token = self.tenant_token()
        url = f"https://open.feishu.cn/open-apis/contact/v3/users/{user_id}?user_id_type=open_id"
        body = self._request("GET", url, token, None, retries=2, timeout=8)
        if int(body.get("code") or 0) != 0:
            return {"open_id": user_id, "name": "", "union_id": ""}
        data = body.get("data") if isinstance(body.get("data"), dict) else {}
        user = data.get("user") if isinstance(data.get("user"), dict) else {}
        return {
            "open_id": str(user.get("open_id") or user_id).strip(),
            "name": str(user.get("name") or user.get("en_name") or user.get("nickname") or "").strip(),
            "union_id": str(user.get("union_id") or "").strip(),
        }

    def get_user_name(self, open_id: str) -> str:
        return self.get_user_profile(open_id).get("name") or ""

    def safe_get_user_profile(self, open_id: str) -> dict[str, str]:
        try:
            return self.get_user_profile(open_id)
        except Exception as exc:
            _LOG.warning("get_user_profile failed open_id=%s err=%s", open_id, exc)
            return {"open_id": str(open_id or "").strip(), "name": "", "union_id": ""}

    def safe_get_user_name(self, open_id: str) -> str:
        return self.safe_get_user_profile(open_id).get("name") or ""

    def get_chat_name(self, chat_id: str) -> str:
        cid = str(chat_id or "").strip()
        if not cid:
            return ""
        token = self.tenant_token()
        url = f"https://open.feishu.cn/open-apis/im/v1/chats/{cid}"
        body = self._request("GET", url, token, None, retries=2, timeout=8)
        if int(body.get("code") or 0) != 0:
            return ""
        data = body.get("data") if isinstance(body.get("data"), dict) else {}
        name = str(data.get("name") or data.get("chat_name") or "").strip()
        if name:
            return name
        mode = str(data.get("chat_mode") or "").strip().lower()
        if mode in {"p2p", "private", "dm"}:
            return "Direct message"
        return ""

    def safe_get_chat_name(self, chat_id: str) -> str:
        try:
            return self.get_chat_name(chat_id)
        except Exception as exc:
            _LOG.warning("get_chat_name failed chat_id=%s err=%s", chat_id, exc)
            return ""

    def list_group_chats(self, *, page_size: int = 100, max_pages: int = 20) -> list[dict[str, Any]]:
        """List group chats that this Feishu app is currently a member of."""
        token = self.tenant_token()
        size = max(1, min(int(page_size or 100), 100))
        pages = max(1, min(int(max_pages or 20), 50))
        page_token = ""
        chats: list[dict[str, Any]] = []
        for _ in range(pages):
            params = {"page_size": str(size)}
            if page_token:
                params["page_token"] = page_token
            url = "https://open.feishu.cn/open-apis/im/v1/chats?" + urlencode(params)
            body = self._request("GET", url, token, None, retries=2, timeout=10)
            if int(body.get("code") or 0) != 0:
                raise RuntimeError(f"Feishu chat list error: {body.get('msg') or body}")
            data = body.get("data") if isinstance(body.get("data"), dict) else {}
            items = data.get("items") if isinstance(data.get("items"), list) else []
            for item in items:
                if not isinstance(item, dict):
                    continue
                chat_id = str(item.get("chat_id") or item.get("id") or "").strip()
                if not chat_id:
                    continue
                mode = str(item.get("chat_mode") or item.get("chat_type") or "group").strip().lower()
                if mode in {"p2p", "private", "dm"}:
                    continue
                chats.append(
                    {
                        "id": chat_id,
                        "name": str(item.get("name") or item.get("chat_name") or "").strip(),
                        "kind": "chat",
                        "chat_mode": mode,
                    }
                )
            has_more = bool(data.get("has_more"))
            next_token = str(data.get("page_token") or "").strip()
            if not has_more or not next_token or next_token == page_token:
                break
            page_token = next_token
        return chats

    def safe_list_group_chats(self, *, page_size: int = 100, max_pages: int = 20) -> list[dict[str, Any]]:
        try:
            return self.list_group_chats(page_size=page_size, max_pages=max_pages)
        except Exception as exc:
            _LOG.warning("list_group_chats failed agent=%s err=%s", self.agent_id, exc)
            return []

    def safe_get_message(self, message_id: str) -> Optional[dict[str, Any]]:
        try:
            return self.get_message(message_id)
        except Exception as exc:
            _LOG.warning("get_message failed message_id=%s err=%s", message_id, exc)
            return None

    def update_text(self, message_id: str, text: str) -> dict[str, Any]:
        token = self.tenant_token()
        return self._request(
            "PUT",
            UPDATE_URL.format(message_id=message_id),
            token,
            {"msg_type": "text", "content": json.dumps({"text": text}, ensure_ascii=False)},
        )

    def safe_update_text(self, message_id: str, text: str) -> Optional[dict[str, Any]]:
        try:
            return self.update_text(message_id, text)
        except Exception as exc:
            _LOG.warning("update_text failed message_id=%s err=%s", message_id, exc)
            return None

    def send_text(self, chat_id: str, text: str) -> dict[str, Any]:
        token = self.tenant_token()
        return self._post(
            CREATE_URL,
            token,
            {
                "receive_id": chat_id,
                "msg_type": "text",
                "content": json.dumps({"text": text}, ensure_ascii=False),
            },
        )

    def send_card(self, chat_id: str, card: dict[str, Any]) -> dict[str, Any]:
        token = self.tenant_token()
        return self._post(
            CREATE_URL,
            token,
            {
                "receive_id": chat_id,
                "msg_type": "interactive",
                "content": json.dumps(card, ensure_ascii=False),
            },
        )

    def safe_reply_text(
        self,
        message_id: str,
        text: str,
        *,
        reply_in_thread: bool = False,
        allow_pdf: bool = False,
        suppress_pdf_artifact: bool = False,
        _on_sent: Callable[[dict[str, Any], str, tuple[str, ...]], None] | None = None,
    ) -> Optional[dict[str, Any]]:
        """Send a conversational answer as text unless PDF output is explicit.

        Plan-shaped content is still valid conversation: it may be a draft,
        a clarification, or a progress update.  Converting it to an
        attachment based only on length and headings can hide the actual
        answer and make an unfinished Technical Plan look final.  Callers
        that explicitly need a document attachment can opt in with
        ``allow_pdf=True`` or use :meth:`safe_reply_pdf` directly.

        ``suppress_pdf_artifact=True`` is used when an Agent already sent the
        requested file through the Host Feishu action.  It keeps the final
        conversational text while preventing a second upload from legacy
        citation or plan-shape detection.
        """

        def notify(response: object, visible_text: str = "", attachment_refs: tuple[str, ...] = ()) -> None:
            if _on_sent is None or not isinstance(response, dict):
                return
            try:
                _on_sent(response, visible_text, attachment_refs)
            except Exception as exc:
                # A transcript/relay observer must never change Feishu
                # delivery success into a reply failure.
                _LOG.warning("agent reply observer failed message_id=%s err=%s", message_id, exc)

        text = sanitize_feishu_answer(text)
        cited_pdf = None if suppress_pdf_artifact else extract_pdf_file_citation(text)
        if cited_pdf is not None:
            try:
                file_key = self.upload_file(cited_pdf)
                clean_text = _strip_file_citations(text)
                sent: Optional[dict[str, Any]] = None
                if clean_text:
                    sent = self.reply_markdown(
                        message_id,
                        normalize_markdown_for_feishu(clean_text),
                        reply_in_thread=reply_in_thread,
                    )
                    notify(sent, clean_text)
                sent = self.reply_file(message_id, file_key, reply_in_thread=reply_in_thread)
                notify(sent, "", (f"file:{Path(cited_pdf).name}",))
                return sent
            except Exception as exc:
                _LOG.warning("cited PDF reply failed message_id=%s path=%s err=%s", message_id, cited_pdf, exc)
            finally:
                _delete_generated_pdf(cited_pdf)
        text = _strip_file_citations(text)
        if allow_pdf and not suppress_pdf_artifact:
            prefix, document, suffix = split_plan_response(text)
            if is_plan_document(document):
                try:
                    file_key = self._upload_plan_pdf(document)
                    sent: Optional[dict[str, Any]] = None
                    if prefix:
                        sent = self.reply_markdown(
                            message_id,
                            normalize_markdown_for_feishu(prefix),
                            reply_in_thread=reply_in_thread,
                        )
                        notify(sent, prefix)
                    sent = self.reply_file(message_id, file_key, reply_in_thread=reply_in_thread)
                    notify(sent, "", (f"file:{plan_pdf_filename(document)}",))
                    if suffix:
                        sent = self.reply_markdown(
                            message_id,
                            normalize_markdown_for_feishu(suffix),
                            reply_in_thread=reply_in_thread,
                        )
                        notify(sent, suffix)
                    return sent
                except Exception as exc:
                    _LOG.warning("PDF plan reply failed message_id=%s err=%s; falling back to card", message_id, exc)
        rendered = normalize_markdown_for_feishu(text)
        parts = split_markdown_for_feishu(rendered)
        sent: Optional[dict[str, Any]] = None
        try:
            for part in parts:
                sent = self.reply_markdown(message_id, part, reply_in_thread=reply_in_thread)
                notify(sent, part)
            return sent
        except Exception as exc:
            _LOG.warning("reply_markdown failed message_id=%s err=%s; falling back to text", message_id, exc)
            if sent is not None:
                return sent
            try:
                sent = self.reply_text(message_id, rendered, reply_in_thread=reply_in_thread)
                notify(sent, rendered)
                return sent
            except Exception as exc2:
                _LOG.warning("reply_text failed message_id=%s err=%s", message_id, exc2)
                return None

    def reply_agent_text(
        self,
        message_id: str,
        text: str,
        *,
        reply_in_thread: bool = False,
        allow_pdf: bool = False,
        suppress_pdf_artifact: bool = False,
        conversation_meta: dict[str, Any] | None = None,
        conversation_common: dict[str, Any] | None = None,
        attachment_refs: list[str] | None = None,
    ) -> Optional[dict[str, Any]]:
        """Send and publish one visible Agent reply to the shared transcript.

        The normal Feishu send path remains the source of truth for delivery.
        Transcript recording and Agent relay happen only after that send
        succeeds, so an unsent model response can never wake a coworker.
        """

        conversation = dict(conversation_meta or {})
        published_ids: set[str] = set()

        def publish_sent(
            response: dict[str, Any],
            visible_text: str,
            sent_attachment_refs: tuple[str, ...],
        ) -> None:
            outbound_id = extract_message_id(response)
            if not outbound_id or outbound_id in published_ids:
                return
            published_ids.add(outbound_id)
            try:
                from agents.runtime.reply_anchor import remember_outbound

                remember_outbound(
                    message_id=outbound_id,
                    text=str(visible_text or ""),
                    chat_id=str(conversation.get("chat_id") or ""),
                    agent_id=self.agent_id,
                    reply_to=str(conversation.get("message_id") or message_id or ""),
                    thread_id=str(conversation.get("thread_id") or ""),
                )
                from agents.conversation.relay import ConversationRelay

                relay = ConversationRelay()
                try:
                    relay.publish(
                        source_agent_id=self.agent_id,
                        source_message_id=outbound_id,
                        text=str(visible_text or ""),
                        meta=dict(conversation, message_id=str(message_id or "")),
                        common=conversation_common,
                        attachment_refs=[*(attachment_refs or []), *sent_attachment_refs],
                    )
                finally:
                    relay.close()
            except Exception as exc:
                # Collaboration is additive.  A transcript/relay persistence
                # issue must not turn an already delivered Feishu reply into
                # a failed Agent turn.
                _LOG.warning("agent reply publication failed message_id=%s err=%s", message_id, exc)

        sent = self.safe_reply_text(
            message_id,
            text,
            reply_in_thread=reply_in_thread,
            allow_pdf=allow_pdf,
            suppress_pdf_artifact=suppress_pdf_artifact,
            _on_sent=publish_sent,
        )
        if sent is None:
            return None
        # Keep compatibility with tests/adapters that replace safe_reply_text
        # and do not invoke the private observer callback.
        if not published_ids:
            visible_text = _strip_file_citations(sanitize_feishu_answer(text))
            publish_sent(sent, visible_text, tuple(attachment_refs or ()))
        return sent

    def safe_reply_pdf(
        self,
        message_id: str,
        markdown: str,
        *,
        reply_in_thread: bool = False,
    ) -> dict[str, Any]:
        file_key = self._upload_plan_pdf(markdown)
        return self.reply_file(message_id, file_key, reply_in_thread=reply_in_thread)

    def _upload_plan_pdf(self, markdown: str) -> str:
        from tempfile import TemporaryDirectory

        filename = plan_pdf_filename(markdown)
        with TemporaryDirectory(prefix="lumon-pdf-") as temporary_dir:
            pdf_path = Path(temporary_dir) / filename
            render_markdown_pdf(markdown, pdf_path)
            return self.upload_file(pdf_path)
