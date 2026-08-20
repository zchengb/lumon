from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class AgentMention:
    agent_id: str
    display_name: str
    matched_text: str = ""
    start: int = 0
    end: int = 0


_AGENT_NAMES: dict[str, tuple[str, ...]] = {
    "milchick": ("milchick", "mr milchick"),
    "mark": ("mark", "mark s"),
    "dylan": ("dylan", "dylan g"),
    "irving": ("irving", "irving b"),
}
_DISPLAY_NAMES = {
    "milchick": "Milchick",
    "mark": "Mark",
    "dylan": "Dylan",
    "irving": "Irving",
}
_ALIASES: dict[str, str] = {}
for _agent_id, _names in _AGENT_NAMES.items():
    for _name in _names:
        _ALIASES[re.sub(r"[^a-z0-9]+", " ", _name.casefold()).strip()] = _agent_id

def _alias_pattern(name: str) -> str:
    if name == "mr milchick":
        return r"mr\.?\s+milchick"
    return re.escape(name).replace(r"\ ", r"\s+")


_NAME_PATTERN = "|".join(
    _alias_pattern(name) for name in sorted(_ALIASES, key=len, reverse=True)
)
_TEXT_MENTION_RE = re.compile(
    rf"(?<![A-Za-z0-9_@])@(?P<name>{_NAME_PATTERN})\.?(?=$|[^A-Za-z0-9_])",
    re.IGNORECASE,
)
_ANY_MENTION_RE = re.compile(r"(?<![A-Za-z0-9_@])@[A-Za-z][A-Za-z0-9_.-]*(?:\s+[A-Za-z][A-Za-z0-9_.-]*)?")
_URL_RE = re.compile(r"(?:https?://|mailto:)[^\s<>]+", re.IGNORECASE)
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def _normalise(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").casefold()).strip()


def _masked_ranges(text: str) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    in_fence = False
    offset = 0
    for line in str(text or "").splitlines(keepends=True):
        stripped = line.lstrip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            ranges.append((offset, offset + len(line)))
        elif in_fence or stripped.startswith(">"):
            ranges.append((offset, offset + len(line)))
        offset += len(line)
    for pattern in (_URL_RE, _EMAIL_RE):
        ranges.extend(match.span() for match in pattern.finditer(str(text or "")))
    # Inline code is intentionally masked without attempting Markdown parsing.
    for match in re.finditer(r"`[^`\n]*`", str(text or "")):
        ranges.append(match.span())
    return ranges


def _masked(span: tuple[int, int], ranges: Iterable[tuple[int, int]]) -> bool:
    return any(start < span[1] and span[0] < end for start, end in ranges)


def parse_agent_mentions(text: str) -> list[AgentMention]:
    raw = str(text or "")
    ranges = _masked_ranges(raw)
    found: list[AgentMention] = []
    for match in _TEXT_MENTION_RE.finditer(raw):
        if _masked(match.span(), ranges):
            continue
        agent_id = _ALIASES.get(_normalise(match.group("name")))
        if not agent_id:
            continue
        # Do not turn a normal person's full name into an Agent mention.  A
        # bare ``@Mark`` followed by an uppercase token is ambiguous, while
        # ``@Mark please`` and the known ``@Mark S.`` handle remain valid.
        normalised_name = _normalise(match.group("name"))
        if normalised_name in {"mark", "dylan", "irving", "milchick"}:
            suffix = raw[match.end() :]
            if re.match(r"\s+[A-Z][A-Za-z0-9]*(?:\.)?(?=$|\s|[^A-Za-z0-9_])", suffix):
                continue
        found.append(
            AgentMention(
                agent_id=agent_id,
                display_name=_DISPLAY_NAMES[agent_id],
                matched_text=match.group(0),
                start=match.start(),
                end=match.end(),
            )
        )
    return list(dict.fromkeys(found))


def has_any_agent_or_user_mention(text: str) -> bool:
    raw = str(text or "")
    ranges = _masked_ranges(raw)
    return any(not _masked(match.span(), ranges) for match in _ANY_MENTION_RE.finditer(raw))


def agent_ids_from_structured_mentions(mentions: object) -> list[str]:
    if not isinstance(mentions, list):
        return []
    found: list[str] = []
    for item in mentions:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or item.get("user_name") or "").strip()
        agent_id = _ALIASES.get(_normalise(name))
        if agent_id:
            found.append(agent_id)
    return list(dict.fromkeys(found))


def render_agent_mentions(
    text: str,
    target_agent_ids: Iterable[str] = (),
    *,
    identities: dict[str, str] | None = None,
) -> str:
    """Render a visible, provider-neutral handoff mention.

    Feishu can resolve an actual user mention when an open_id is known.  The
    plain ``@DisplayName`` fallback remains readable in every message type and
    is also what the exact parser uses for relay routing.
    """

    result = str(text or "").strip()
    identities = identities if isinstance(identities, dict) else {}
    present = {item.agent_id for item in parse_agent_mentions(result)}
    for agent_id in dict.fromkeys(str(item or "").strip().lower() for item in target_agent_ids):
        if not agent_id or agent_id in present:
            continue
        display = _DISPLAY_NAMES.get(agent_id, agent_id.title())
        result = f"{result}\n\n@{display}" if result else f"@{display}"
    return result


class AgentMentionRenderer:
    def render(self, text: str, target_agent_ids: Iterable[str] = (), *, identities: dict[str, str] | None = None) -> str:
        return render_agent_mentions(text, target_agent_ids, identities=identities)
