from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from agents.conversation.config import DEFAULT_REPLY_LANGUAGE, normalize_reply_language


@dataclass
class ToolCall:
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass
class RouterResult:
    intent: str
    confidence: float
    source: str
    project_slug: Optional[str] = None
    finding_id: Optional[str] = None
    run_id: Optional[str] = None
    reference: Optional[dict[str, Any]] = None
    needs_clarification: bool = False
    clarification_question: Optional[str] = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentTask:
    task_id: str
    intent: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    project_slug: Optional[str] = None
    finding_id: Optional[str] = None
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentPlan:
    language: str
    confidence: float
    needs_clarification: bool = False
    clarification_question: Optional[str] = None
    tasks: list[AgentTask] = field(default_factory=list)
    source: str = "agent"


@dataclass
class ModelConfig:
    provider: str = "cursor"
    base_url: str = ""
    api_key_env: str = ""
    reasoning_effort: str = ""
    account_email: str = ""
    router_timeout_seconds: int = 8
    response_timeout_seconds: int = 25
    max_router_retries: int = 1
    max_response_retries: int = 1
    model_name: str = "cursor-grok-4.5-medium"
    planner_timeout_seconds: int = 45
    responder_timeout_seconds: int = 60
    required: bool = True


@dataclass
class TypingConfig:
    enabled: bool = True
    delay_ms: int = 350
    progress_after_ms: int = 5000
    long_wait_after_ms: int = 15000
    overall_timeout_ms: int = 45000
    max_updates: int = 4


@dataclass
class ReactionConfig:
    enabled: bool = True
    emoji_type: str = "Typing"
    add_immediately: bool = True
    remove_on_success: bool = True
    remove_on_failure: bool = True
    cleanup_after_seconds: int = 120


@dataclass
class AgentLoopConfig:
    max_iterations: int = 2
    max_tool_calls: int = 8
    max_total_tool_seconds: int = 20
    allow_multi_task: bool = True


@dataclass
class ObservabilityConfig:
    log_level: str = "INFO"
    jsonl_enabled: bool = True
    trace_enabled: bool = True
    store_model_io: bool = False
    model_io_retention_days: int = 3
    redact_secrets: bool = True


@dataclass
class ConversationFlags:
    enabled: bool = False
    llm_router_enabled: bool = False
    llm_response_enabled: bool = False
    grounding_guard_enabled: bool = True
    model: ModelConfig = field(default_factory=ModelConfig)
    typing: TypingConfig = field(default_factory=TypingConfig)
    # v3
    v3_enabled: bool = False
    routing_mode: str = "legacy"
    reaction: ReactionConfig = field(default_factory=ReactionConfig)
    agent_loop: AgentLoopConfig = field(default_factory=AgentLoopConfig)
    observability: ObservabilityConfig = field(default_factory=ObservabilityConfig)
    v4_enabled: bool = False
    autonomous_mode: str = ""
    session_scope: str = "thread_shared"
    harness_mode: str = "unshackled"
    soft_timeout_seconds: int = 90
    hard_timeout_seconds: int = 3600
    default_language: str = DEFAULT_REPLY_LANGUAGE

    @classmethod
    def from_common(
        cls,
        common: dict[str, Any] | None,
        agents_config: dict[str, Any] | None = None,
        agent_id: str = "dylan",
    ) -> "ConversationFlags":
        data = common if isinstance(common, dict) else {}
        common_conversation = data.get("conversation") if isinstance(data.get("conversation"), dict) else {}
        configured_conversation = (
            agents_config.get("conversation")
            if isinstance(agents_config, dict) and isinstance(agents_config.get("conversation"), dict)
            else {}
        )
        agents = data.get("agents") if isinstance(data.get("agents"), dict) else {}
        key = str(agent_id or "dylan").strip().lower() or "dylan"
        dylan = agents.get(key) if isinstance(agents.get(key), dict) else {}
        if not dylan and isinstance(agents_config, dict):
            dylan = agents_config.get(key) if isinstance(agents_config.get(key), dict) else {}
        risk = dylan.get("risk_analyst") if isinstance(dylan.get("risk_analyst"), dict) else {}
        conv = risk.get("conversation_v2") if isinstance(risk.get("conversation_v2"), dict) else {}
        v3 = dylan.get("conversation_v3") if isinstance(dylan.get("conversation_v3"), dict) else {}
        v4 = dylan.get("conversation_v4") if isinstance(dylan.get("conversation_v4"), dict) else {}
        if isinstance(agents_config, dict):
            cfg_dylan = agents_config.get(key) if isinstance(agents_config.get(key), dict) else {}
            if not v3:
                v3 = cfg_dylan.get("conversation_v3") if isinstance(cfg_dylan.get("conversation_v3"), dict) else {}
            if not v4:
                v4 = cfg_dylan.get("conversation_v4") if isinstance(cfg_dylan.get("conversation_v4"), dict) else {}
            if not conv:
                cfg_risk = cfg_dylan.get("risk_analyst") if isinstance(cfg_dylan.get("risk_analyst"), dict) else {}
                conv = cfg_risk.get("conversation_v2") if isinstance(cfg_risk.get("conversation_v2"), dict) else {}
        execution = data.get("execution") if isinstance(data.get("execution"), dict) else {}
        global_model_src = {
            key: execution.get(key)
            for key in ("provider", "model", "base_url", "api_key_env", "reasoning_effort", "account_email")
            if execution.get(key)
        }
        provider_src = global_model_src or (v4.get("provider") if isinstance(v4.get("provider"), dict) else {})
        model_src = (
            provider_src
            if provider_src
            else (v3.get("model") if isinstance(v3.get("model"), dict) else (conv.get("model") if isinstance(conv.get("model"), dict) else {}))
        )
        typing_raw = conv.get("typing") if isinstance(conv.get("typing"), dict) else {}
        reaction_raw = (
            v4.get("reaction")
            if isinstance(v4.get("reaction"), dict)
            else (v3.get("reaction") if isinstance(v3.get("reaction"), dict) else {})
        )
        loop_raw = v3.get("agent_loop") if isinstance(v3.get("agent_loop"), dict) else {}
        obs_raw = (
            v4.get("observability")
            if isinstance(v4.get("observability"), dict)
            else (v3.get("observability") if isinstance(v3.get("observability"), dict) else {})
        )
        session_raw = v4.get("session") if isinstance(v4.get("session"), dict) else {}
        runtime_raw = v4.get("runtime") if isinstance(v4.get("runtime"), dict) else {}
        harness_raw = {}
        if isinstance(agents_config, dict):
            configured_harness = agents_config.get("harness")
            if isinstance(configured_harness, dict):
                harness_raw = dict(configured_harness)
            security_raw = agents_config.get("agent_security")
            if isinstance(security_raw, dict):
                # The execution world is the provider-facing mode.  Keep
                # harness capability switches, but let an explicit trusted
                # or isolated security mode win over the older generic
                # ``harness.mode`` value.
                if not harness_raw:
                    harness_raw = dict(security_raw)
                elif security_raw.get("mode"):
                    harness_raw["mode"] = security_raw["mode"]
        v4_enabled = bool(v4.get("enabled", False))
        provider_name = str(model_src.get("type") or model_src.get("provider") or "cursor").strip().casefold()
        codex_provider = provider_name in {"codex", "codex_cli", "codex-cli"}
        opencode_provider = provider_name in {"opencode", "opencode_deepseek", "deepseek", "deepseek_api"}
        api_provider = provider_name in {"openai", "openai_compatible", "openai-compatible"}
        default_model = (
            "gpt-5.6-luna"
            if codex_provider
            else "deepseek-v4-flash"
            if opencode_provider
            else "gpt-4o-mini"
            if api_provider
            else "cursor-grok-4.5-medium"
        )
        model = ModelConfig(
            provider=str(model_src.get("type") or model_src.get("provider") or "cursor"),
            base_url=str(model_src.get("base_url") or ""),
            api_key_env=str(model_src.get("api_key_env") or ""),
            reasoning_effort=str(model_src.get("reasoning_effort") or ("xhigh" if codex_provider else "")),
            account_email=str(model_src.get("account_email") or ("kuoyio0820@gmail.com" if codex_provider else "")),
            router_timeout_seconds=int(model_src.get("router_timeout_seconds") or model_src.get("planner_timeout_seconds") or 45),
            response_timeout_seconds=int(model_src.get("response_timeout_seconds") or model_src.get("responder_timeout_seconds") or 60),
            max_router_retries=int(model_src.get("max_router_retries") or model_src.get("max_planner_retries") or 1),
            max_response_retries=int(model_src.get("max_response_retries") or model_src.get("max_responder_retries") or 1),
            model_name=str(model_src.get("model") or model_src.get("name") or default_model),
            planner_timeout_seconds=int(model_src.get("planner_timeout_seconds") or 45),
            responder_timeout_seconds=int(model_src.get("responder_timeout_seconds") or 60),
            required=bool(model_src.get("required", True if (v4_enabled or v3.get("enabled")) else False)),
        )
        typing = TypingConfig(
            enabled=bool(typing_raw.get("enabled", True)),
            delay_ms=int(typing_raw.get("delay_ms") or 350),
            progress_after_ms=int(typing_raw.get("progress_after_ms") or 5000),
            long_wait_after_ms=int(typing_raw.get("long_wait_after_ms") or 15000),
            overall_timeout_ms=int(typing_raw.get("overall_timeout_ms") or 45000),
            max_updates=int(typing_raw.get("max_updates") or 4),
        )
        reaction = ReactionConfig(
            enabled=bool(reaction_raw.get("enabled", True)),
            emoji_type=str(reaction_raw.get("emoji_type") or "Typing"),
            add_immediately=bool(reaction_raw.get("add_immediately", True)),
            remove_on_success=bool(reaction_raw.get("remove_on_success", True)),
            remove_on_failure=bool(reaction_raw.get("remove_on_failure", True)),
            cleanup_after_seconds=int(reaction_raw.get("cleanup_after_seconds") or 120),
        )
        agent_loop = AgentLoopConfig(
            max_iterations=int(loop_raw.get("max_iterations") or 2),
            max_tool_calls=int(loop_raw.get("max_tool_calls") or 8),
            max_total_tool_seconds=int(loop_raw.get("max_total_tool_seconds") or 20),
            allow_multi_task=bool(loop_raw.get("allow_multi_task", True)),
        )
        observability = ObservabilityConfig(
            log_level=str(obs_raw.get("log_level") or "INFO"),
            jsonl_enabled=bool(obs_raw.get("jsonl_enabled", True)),
            trace_enabled=bool(obs_raw.get("trace_enabled", True)),
            store_model_io=bool(obs_raw.get("store_model_io", False)),
            model_io_retention_days=int(obs_raw.get("model_io_retention_days") or 3),
            redact_secrets=bool(obs_raw.get("redact_secrets", True)),
        )
        v3_enabled = bool(v3.get("enabled", False))
        flags = cls(
            enabled=bool(conv.get("enabled", False)) or v3_enabled or v4_enabled,
            llm_router_enabled=bool(conv.get("llm_router_enabled", False)),
            llm_response_enabled=bool(conv.get("llm_response_enabled", False)),
            grounding_guard_enabled=bool(conv.get("grounding_guard_enabled", True)),
            model=model,
            typing=typing,
            v3_enabled=v3_enabled,
            routing_mode=str(v3.get("routing_mode") or ("agent_only" if v3_enabled else "legacy")),
            reaction=reaction,
            agent_loop=agent_loop,
            observability=observability,
            v4_enabled=v4_enabled,
            autonomous_mode=str(v4.get("mode") or ("autonomous_workspace" if v4_enabled else "")),
            session_scope=str(session_raw.get("scope") or "thread_shared"),
            harness_mode=str(harness_raw.get("mode") or "unshackled").strip().casefold(),
            soft_timeout_seconds=int(runtime_raw.get("soft_timeout_seconds") or 90),
            hard_timeout_seconds=int(runtime_raw.get("hard_timeout_seconds") or 3600),
            default_language=normalize_reply_language(
                configured_conversation.get(
                    "default_language",
                    common_conversation.get("default_language", DEFAULT_REPLY_LANGUAGE),
                )
            ),
        )
        flags._max_concurrent_jobs = int(dylan.get("max_concurrent_jobs") or runtime_raw.get("max_concurrent_sessions") or 3)  # type: ignore[attr-defined]
        return flags

    @property
    def max_concurrent_jobs(self) -> int:
        return int(getattr(self, "_max_concurrent_jobs", 3) or 3)

    @property
    def autonomous(self) -> bool:
        return self.v4_enabled and self.autonomous_mode == "autonomous_workspace"

    @property
    def agent_only(self) -> bool:
        return self.v3_enabled and self.routing_mode == "agent_only" and not self.autonomous


ALLOWED_INTENTS = {
    "scan.run",
    "scan.status",
    "scan.summary",
    "scan.cancel",
    "risk.top",
    "risk.unresolved",
    "risk.recent",
    "risk.trend",
    "risk.recurring",
    "risk.overdue",
    "risk.explain",
    "risk.why_severity",
    "risk.finding_status",
    "risk.finding_links",
    "risk.compare_period",
    "conversation.greeting",
    "conversation.agent_identity",
    "conversation.agent_relationship",
    "conversation.capabilities",
    "conversation.follow_up",
    "conversation.thanks",
    "conversation.small_talk",
    "clarification.project",
    "clarification.run",
    "clarification.finding",
    "clarification.reference",
    "unsupported",
}

INTENT_TOOLS = {
    "risk.top": {"query_top_risks"},
    "risk.unresolved": {"query_unresolved_findings"},
    "risk.recent": {"query_recent_findings", "query_unresolved_findings", "get_recent_scan_status"},
    "risk.trend": {"query_project_trend"},
    "risk.recurring": {"query_recurring_findings"},
    "risk.overdue": {"query_overdue_high"},
    "risk.explain": {"explain_finding", "get_finding_summary"},
    "risk.why_severity": {"explain_finding", "get_finding_summary"},
    "risk.finding_status": {"get_finding_status", "get_finding_summary"},
    "risk.finding_links": {"get_finding_links", "get_finding_status"},
    "risk.compare_period": {"compare_project_risk", "query_recent_findings"},
    "scan.status": {"get_recent_scan_status", "get_scan_summary", "get_scan_result"},
    "scan.summary": {"get_scan_summary", "get_scan_result", "query_recent_findings"},
    "conversation.greeting": {"get_agent_profile", "get_thread_context"},
    "conversation.agent_identity": {"get_agent_profile", "list_agent_capabilities"},
    "conversation.agent_relationship": {"get_agent_relationship"},
    "conversation.capabilities": {"list_agent_capabilities"},
    "conversation.follow_up": {"explain_finding", "get_finding_links", "get_finding_summary"},
}

READ_ONLY_TOOLS = set().union(*INTENT_TOOLS.values()) if INTENT_TOOLS else set()
READ_ONLY_TOOLS |= {
    "get_thread_context",
    "resolve_previous_result",
    "resolve_recent_run",
    "list_agent_capabilities",
    "get_agent_profile",
}
