from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal


LoopName = Literal["business", "technical", ""]
LoopDecision = Literal["none", "direct", "confirm", "continue", "decline"]


@dataclass(frozen=True)
class LoopIntent:
    loop: LoopName
    decision: LoopDecision
    confidence: float
    reason: str = ""
    source: str = "rule"

    @property
    def should_route_in_group(self) -> bool:
        return self.decision in {"direct", "confirm"} and bool(self.loop)


_INFO_RE = re.compile(
    r"(?:what\s+is|what's|explain|difference|why|how\s+does|区别|差异|是什么|为什么|怎么理解|如何理解)"
    r"[\s\S]{0,48}(?:business\s+loop|technical\s+loop|story\s*plan|technical\s*plan|需求流程|技术流程|需求卡)",
    re.IGNORECASE,
)

_BUSINESS_DIRECT_RE = re.compile(
    r"(?:business\s+loop|需求卡?|业务需求|产品需求|user\s+story|requirement|story)"
    r"[\s\S]{0,42}(?:创建|新建|建立|开启|启动|整理|转换|转成|变成|提炼|记录|拆成|create|draft|capture|turn|convert|make|open|start|begin)"
    r"|(?:创建|新建|建立|开启|启动|整理成|转换成|转成|变成|提炼成|记录为|拆成)"
    r"[\s\S]{0,42}(?:需求卡?|业务需求|产品需求|user\s+story|requirement|story)"
    r"|(?:create|draft|capture|turn|convert|make|open|start|begin)"
    r"[\s\S]{0,42}(?:a\s+)?(?:requirement|user\s+story|story)"
    r"|(?:need|want|please|let's)[\s\S]{0,42}(?:a\s+)?(?:new\s+)?(?:requirement|user\s+story|story)",
    re.IGNORECASE,
)

_TECHNICAL_DIRECT_RE = re.compile(
    r"(?:technical\s+loop|technical\s+plan|technical\s+design|implementation\s+plan|technical\s+solution|技术方案|技术计划|技术设计|实现方案|架构方案)"
    r"[\s\S]{0,42}(?:创建|新建|建立|开启|启动|整理|转换|转成|变成|制定|生成|设计|create|draft|turn|convert|make|open|start|begin|design|plan)"
    r"|(?:创建|新建|建立|开启|启动|整理成|转换成|转成|变成|制定|生成|设计)"
    r"[\s\S]{0,42}(?:技术方案|技术计划|技术设计|实现方案|架构方案|technical\s+plan|technical\s+design|implementation\s+plan|technical\s+solution)"
    r"|(?:create|draft|turn|convert|make|open|start|begin|design|plan|need|want|please|let's)"
    r"[\s\S]{0,42}(?:a\s+)?(?:technical\s+plan|technical\s+design|implementation\s+plan|technical\s+solution|architecture)",
    re.IGNORECASE,
)

# A request that names both artifacts is a staged workflow, not an implicit
# Technical Loop entry.  Keep this signal narrower than a bare ``story`` or
# ``technical-plan.md`` reference so evidence/status messages do not get
# mistaken for a new planning request.
_STORY_PLAN_SIGNAL_RE = re.compile(
    r"(?:\bstory[\s_-]*plan\b|\buser[\s_-]*story\b|\bbusiness[\s_-]*(?:requirement|loop)\b|"
    r"需求(?:方案|计划|卡)?|业务需求|故事(?:方案|计划))",
    re.IGNORECASE,
)
_TECHNICAL_PLAN_SIGNAL_RE = re.compile(
    r"(?:\btechnical[\s_-]*(?:plan|design|solution)\b|\bimplementation[\s_-]*plan\b|"
    r"技术(?:方案|计划|设计)|实现方案|架构方案)",
    re.IGNORECASE,
)

_BUSINESS_CONFIRM_RE = re.compile(
    r"(?:需求卡?|业务需求|产品需求|user\s+story|requirement|story)"
    r"[\s\S]{0,32}(?:整理|梳理|明确|讨论|看一下|想法|idea)"
    r"|(?:整理|梳理|明确|定义|拆解)[\s\S]{0,32}(?:需求|想法|这件事|这个)",
    re.IGNORECASE,
)

_TECHNICAL_CONFIRM_RE = re.compile(
    r"(?:technical|技术|方案|设计|架构|实现)[\s\S]{0,32}(?:整理|梳理|讨论|看一下|怎么做|如何实现|想法|idea)"
    r"|(?:整理|梳理|讨论|看看|想想)[\s\S]{0,32}(?:技术方案|技术设计|实现方案|架构)",
    re.IGNORECASE,
)

_CONFIRM_RE = re.compile(
    r"^(?:1|yes|y|ok|okay|sure|go\s+ahead|please\s+do|confirm|start|begin|open|开始|启动|确认|是的?|好(?:的)?|对|可以|行|继续|没问题|那就开始|那开始)[。.!！、，,\s]*$",
    re.IGNORECASE,
)
_DECLINE_RE = re.compile(
    r"^(?:2|no|n|not\s+now|cancel|stop|不要|不用|先不|暂时不用|取消|否|不是|不启动|先这样)[。.!！、，,\s]*$",
    re.IGNORECASE,
)


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip())


def _pending_loop(pending: dict[str, Any] | None) -> str:
    if not isinstance(pending, dict) or str(pending.get("mode") or "").strip().lower() != "loop_confirmation":
        return ""
    loop = str(pending.get("loop") or "").strip().lower()
    return loop if loop in {"business", "technical"} else ""


def _intent(loop: LoopName, decision: LoopDecision, confidence: float, reason: str) -> LoopIntent:
    return LoopIntent(loop=loop, decision=decision, confidence=confidence, reason=reason)


def is_combined_plan_request(text: str) -> bool:
    """Return whether a message explicitly asks for both planning stages.

    Story planning owns the business-ready prerequisite for technical
    planning.  This helper is intentionally shared by the group front door
    and the autonomous prompt builder so the routing rule is not duplicated.
    """

    raw = _clean(text)
    return bool(_STORY_PLAN_SIGNAL_RE.search(raw) and _TECHNICAL_PLAN_SIGNAL_RE.search(raw))


def classify_loop_intent(
    text: str,
    *,
    active_loop: str = "",
    pending: dict[str, Any] | None = None,
) -> LoopIntent:
    """Classify only Loop entry language; ordinary conversation remains untouched."""

    raw = _clean(text)
    if not raw or _INFO_RE.search(raw):
        return _intent("", "none", 0.0, "informational or empty message")

    pending_loop = _pending_loop(pending)
    if pending_loop:
        if _DECLINE_RE.fullmatch(raw):
            return _intent("", "decline", 1.0, "user declined the proposed Loop")
        if _CONFIRM_RE.fullmatch(raw):
            return _intent(pending_loop, "direct", 1.0, "user confirmed the proposed Loop")

    business = bool(_BUSINESS_DIRECT_RE.search(raw))
    technical = bool(_TECHNICAL_DIRECT_RE.search(raw))
    if is_combined_plan_request(raw):
        return _intent(
            "business",
            "direct",
            0.99,
            "combined Story and Technical Plan request must start with Story Plan",
        )
    if technical and not business:
        return _intent("technical", "direct", 0.96, "clear request for a technical plan or design")
    if business and not technical:
        return _intent("business", "direct", 0.96, "clear request to create or shape a requirement")
    if technical and business:
        return _intent("technical", "direct", 0.98, "request explicitly connects a requirement to technical design")

    current = str(active_loop or "").strip().lower()
    if _TECHNICAL_CONFIRM_RE.search(raw):
        if current == "technical":
            return _intent("technical", "continue", 0.72, "continue the active Technical Loop")
        return _intent("technical", "confirm", 0.72, "message may be asking to enter technical planning")
    if _BUSINESS_CONFIRM_RE.search(raw):
        if current == "business":
            return _intent("business", "continue", 0.72, "continue the active Business Loop")
        return _intent("business", "confirm", 0.72, "message may be asking to shape a new requirement")

    if current in {"business", "technical"}:
        return _intent(current, "continue", 0.55, "continue the active Loop in this conversation")
    return _intent("", "none", 0.0, "no Loop entry signal")


def loop_display_name(loop: str) -> str:
    return "Business Loop" if str(loop or "").strip().lower() == "business" else "Technical Loop"


def loop_confirmation_text(intent: LoopIntent, *, chinese: bool = False) -> str:
    name = loop_display_name(intent.loop)
    if chinese:
        target = "需求" if intent.loop == "business" else "技术方案"
        return (
            f"这句话看起来可能是在把当前内容整理成一个新的 {name}（{target}）。\n"
            f"要我现在开始推进吗？\n\n"
            f"1. 开始 {name}\n"
            "2. 先不启动，只继续普通对话\n\n"
            "如果你的意思不同，直接告诉我就好。"
        )
    return (
        f"This sounds like you may want to start a new {name}.\n"
        "Should I start it now?\n\n"
        f"1. Start {name}\n"
        "2. Keep this as a normal conversation\n\n"
        "If I read that wrong, just tell me what you meant."
    )


def loop_gateway_prompt(intent: LoopIntent, *, active_loop: str = "") -> str:
    if intent.decision == "none":
        return ""
    name = loop_display_name(intent.loop or active_loop)
    if intent.decision == "direct":
        if intent.loop == "business" and "combined" in intent.reason.lower():
            return (
                "[LUMEN LOOP GATEWAY]\n"
                "The user requested both a Story Plan and a Technical Plan. This is a staged workflow: "
                "start the Story/Business Loop first, finish the business-ready Story, and only then enter the Technical Loop.\n"
                "Keep the user-facing plan and progress as Feishu text. Do not create, present, or attach a technical plan "
                "until the Story artifact exists and metadata businessStatus is ready.\n"
                "Starting the Business Loop is not authorization to start Development/Delivery or to emit delivery.start.\n"
            )
        return (
            "[LUMEN LOOP GATEWAY]\n"
            f"The user has clearly entered {name} through natural language ({intent.reason}).\n"
            f"Start {name} now; do not ask whether to start it. Read the matching Lumen skill and follow its workflow.\n"
            "Starting a Business or Technical Loop is not authorization to start Development/Delivery or to emit delivery.start.\n"
            "Ask only the Loop's own highest-impact question, record confirmed decisions in its artifacts, and keep the user in this Feishu thread.\n"
        )
    if intent.decision == "confirm":
        return (
            "[LUMEN LOOP GATEWAY]\n"
            f"The message may be an attempt to enter {name}, but the intent is not clear enough to start it ({intent.reason}).\n"
            f"Ask one concise confirmation: whether the user wants to start {name}. Do not inspect or modify Loop artifacts until they confirm.\n"
        )
    if intent.decision == "continue":
        return (
            "[LUMEN LOOP GATEWAY]\n"
            f"This conversation is already inside {name}. Treat the user's message as a continuation unless they explicitly switch or stop.\n"
        )
    return ""
