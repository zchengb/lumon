from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Optional

from agents.security.actions import MUTATION_ACTIONS
from agents.security.policy import load_access_config
from feishu.config import load_agents_config

POLICY_VERSION = "m0.4.0"

TrustZone = Literal["PRIVATE", "RESTRICTED", "SHARED", "DENY"]
HostReadMode = Literal["deny", "selected", "system_only"]

DEFAULT_EXPOSURE = {
    "dylan": "owner_private",
    "mark": "restricted_team",
    "milchick": "admin_private",
    "irving": "restricted_team",
}

DEFAULT_HOST_CAPS = {
    "dylan": frozenset({"host.disk.summary", "host.runtime.summary"}),
    "mark": frozenset(),
    "milchick": frozenset({"lumen.system.health", "lumen.agent.status", "lumen.runner.status", "host.runtime.summary"}),
    "irving": frozenset(),
}


@dataclass(frozen=True)
class AgentAccessPolicy:
    agent_id: str
    exposure_mode: str
    allowed_user_ids: frozenset[str]
    allowed_chat_ids: frozenset[str]
    dm_only: bool
    host_read_mode: str
    host_read_capabilities: frozenset[str]
    mutation_allowed_user_ids: frozenset[str]
    owners: frozenset[str]
    admins: frozenset[str]
    default_policy: str
    source: str = "agent"


@dataclass(frozen=True)
class InteractionContext:
    agent_id: str
    user_id: str
    chat_id: str
    chat_type: str
    thread_id: str
    message_id: str
    is_dm: bool
    trust_zone: str = ""
    is_owner: bool = False
    is_admin: bool = False


@dataclass(frozen=True)
class AccessDecision:
    allowed: bool
    reason_code: str
    trust_zone: str | None
    host_read_allowed: bool
    mutation_allowed: bool
    effective_capabilities: frozenset[str]
    exposure_mode: str = ""
    policy_version: str = POLICY_VERSION
    context: InteractionContext | None = None
    policy: AgentAccessPolicy | None = None


def _as_set(values: Any) -> frozenset[str]:
    if not isinstance(values, (list, tuple, set, frozenset)):
        return frozenset()
    return frozenset(str(x).strip() for x in values if str(x).strip())


def _expand_user_ids(store: Any, values: frozenset[str]) -> frozenset[str]:
    if store is None or not values:
        return values
    try:
        return frozenset(store.expand_feishu_open_ids(sorted(values)))
    except Exception:
        return values


def _user_in(store: Any, user_id: str, allowed: frozenset[str]) -> bool:
    user = str(user_id or "").strip()
    if not user:
        return False
    if user in allowed:
        return True
    expanded_allowed = _expand_user_ids(store, allowed)
    if user in expanded_allowed:
        return True
    expanded_user = _expand_user_ids(store, frozenset({user}))
    return bool(expanded_user & (allowed | expanded_allowed))


def is_dm_chat(chat_type: str, *, thread_id: str = "", chat_id: str = "") -> bool:
    kind = str(chat_type or "").strip().lower()
    if kind in {"p2p", "private", "dm"}:
        return True
    return not kind and not str(chat_id or "").strip()


def interaction_context_from_meta(
    *,
    agent_id: str,
    meta: dict[str, str],
    policy: AgentAccessPolicy,
    store: Any = None,
) -> InteractionContext:
    user_id = str(meta.get("user_id") or "").strip()
    chat_type = str(meta.get("chat_type") or "").strip()
    chat_id = str(meta.get("chat_id") or "").strip()
    owners = _expand_user_ids(store, policy.owners)
    admins = _expand_user_ids(store, policy.admins)
    allowed = _expand_user_ids(store, policy.allowed_user_ids)
    return InteractionContext(
        agent_id=str(agent_id or "").strip().lower(),
        user_id=user_id,
        chat_id=chat_id,
        chat_type=chat_type,
        thread_id=str(meta.get("thread_id") or "").strip(),
        message_id=str(meta.get("message_id") or "").strip(),
        is_dm=is_dm_chat(chat_type, chat_id=chat_id),
        is_owner=_user_in(store, user_id, owners)
        or (
            _user_in(store, user_id, allowed)
            and policy.exposure_mode == "owner_private"
        ),
        is_admin=_user_in(store, user_id, admins),
    )

def load_agent_access_policy(agent_id: str, config: Optional[dict[str, Any]] = None) -> AgentAccessPolicy:
    data = config if isinstance(config, dict) else load_agents_config()
    access = data.get("access") if isinstance(data.get("access"), dict) else {}
    legacy = load_access_config(data)
    owners = _as_set(access.get("owners") or access.get("admin_user_ids") or legacy.get("admin_user_ids"))
    admins = _as_set(access.get("admins") or access.get("admin_user_ids") or legacy.get("admin_user_ids"))
    global_chats = _as_set(access.get("allowed_chat_ids") or legacy.get("allowed_chat_ids"))
    default_policy = str(access.get("default_policy") or "legacy_allow").strip().lower() or "legacy_allow"
    agent = str(agent_id or "").strip().lower()
    agents = access.get("agents") if isinstance(access.get("agents"), dict) else {}
    raw = agents.get(agent) if isinstance(agents.get(agent), dict) else None

    if raw is None and default_policy == "legacy_allow":
        exposure = DEFAULT_EXPOSURE.get(agent, "restricted_team")
        dm_only = exposure in {"owner_private", "admin_private"}
        return AgentAccessPolicy(
            agent_id=agent,
            exposure_mode=exposure,
            allowed_user_ids=_as_set(legacy.get("allowed_user_ids")) | owners | admins,
            allowed_chat_ids=global_chats,
            dm_only=dm_only,
            host_read_mode="selected" if exposure == "owner_private" else ("system_only" if exposure == "admin_private" else "deny"),
            host_read_capabilities=DEFAULT_HOST_CAPS.get(agent, frozenset()),
            mutation_allowed_user_ids=_as_set(legacy.get("mutation_allowed_user_ids")) | admins,
            owners=owners,
            admins=admins,
            default_policy=default_policy,
            source="legacy",
        )

    global_users = _as_set(legacy.get("allowed_user_ids"))
    global_mutators = _as_set(legacy.get("mutation_allowed_user_ids"))

    if raw is None:
        # Dashboard stores the private-user and group ACLs as a global policy
        # until an agent-specific override is needed.  Do not discard that
        # authorization merely because `access.agents.<agent>` is absent:
        # otherwise every DM hits AGENT_ACCESS_UNCONFIGURED even when the
        # user was explicitly allowed in Dashboard.
        has_global_acl = bool(global_users or global_chats)
        return AgentAccessPolicy(
            agent_id=agent,
            exposure_mode=DEFAULT_EXPOSURE.get(agent, "restricted_team"),
            allowed_user_ids=global_users,
            allowed_chat_ids=global_chats,
            dm_only=True,
            host_read_mode="deny",
            host_read_capabilities=frozenset(),
            mutation_allowed_user_ids=global_mutators,
            owners=owners,
            admins=admins,
            default_policy=default_policy,
            source="global" if has_global_acl else "missing",
        )

    exposure = str(raw.get("exposure_mode") or DEFAULT_EXPOSURE.get(agent, "restricted_team")).strip()
    host_mode = str(raw.get("host_read") or raw.get("host_read_mode") or "deny").strip() or "deny"
    caps = _as_set(raw.get("host_read_capabilities"))
    if not caps:
        caps = DEFAULT_HOST_CAPS.get(agent, frozenset()) if host_mode in {"selected", "system_only"} else frozenset()
    return AgentAccessPolicy(
        agent_id=agent,
        exposure_mode=exposure,
        allowed_user_ids=_as_set(raw.get("allowed_user_ids")) | global_users,
        allowed_chat_ids=_as_set(raw.get("allowed_chat_ids")) | global_chats,
        dm_only=bool(raw.get("dm_only", exposure in {"owner_private", "admin_private"})),
        host_read_mode=host_mode,
        host_read_capabilities=caps,
        mutation_allowed_user_ids=_as_set(raw.get("mutation_allowed_user_ids")) | global_mutators,
        owners=owners,
        admins=admins,
        default_policy=default_policy,
        source="agent",
    )


def resolve_trust_zone(
    context: InteractionContext,
    policy: AgentAccessPolicy,
    *,
    store: Any = None,
) -> TrustZone:
    group_allowed = not context.is_dm and context.chat_id in policy.allowed_chat_ids
    if policy.dm_only and not context.is_dm and not group_allowed:
        return "DENY"
    user = context.user_id
    if not user:
        return "DENY"
    # A missing per-agent block may still use the Dashboard's explicit global
    # group or private-user ACL.  Owners/admins alone are not enough to turn a
    # completely unconfigured Agent on.
    if policy.source == "missing" and policy.default_policy != "legacy_allow":
        if not group_allowed and not policy.allowed_user_ids:
            return "DENY"
    allowed_users = policy.allowed_user_ids | policy.owners | policy.admins
    # A whitelisted group is the authorization boundary.  Every human in the
    # group may talk to the Agent; the private-user allowlist must not turn a
    # group permission into a second one-to-one approval step.
    if not group_allowed and allowed_users and not _user_in(store, user, allowed_users):
        return "DENY"
    if context.is_dm and not _user_in(store, user, allowed_users):
        # A configured ACL is authoritative: DMs must be explicitly allowed
        # one person at a time.  Keep the historical fallback only for an
        # untouched legacy installation so existing local runtimes continue
        # to work until the Dashboard saves the new deny-by-default policy.
        if (
            policy.source == "legacy"
            and policy.default_policy == "legacy_allow"
            and not policy.allowed_chat_ids
            and not allowed_users
        ):
            return "PRIVATE" if policy.exposure_mode in {"owner_private", "admin_private"} else "RESTRICTED"
        return "DENY"
    if not group_allowed and not context.is_dm and not allowed_users and policy.default_policy != "legacy_allow" and policy.source != "legacy":
        return "DENY"

    if context.is_dm and _user_in(store, user, policy.owners | policy.admins | policy.allowed_user_ids):
        if policy.exposure_mode in {"owner_private", "admin_private"} or _user_in(
            store, user, policy.owners | policy.admins
        ):
            return "PRIVATE"
        return "RESTRICTED"

    if policy.allowed_chat_ids:
        if context.chat_id in policy.allowed_chat_ids:
            if policy.exposure_mode == "restricted_team":
                return "RESTRICTED"
            if policy.dm_only and policy.exposure_mode in {"owner_private", "admin_private"}:
                return "RESTRICTED"
            return "SHARED"
        return "DENY"

    if context.is_dm:
        return "DENY"

    # Preserve the old open-group behavior only for truly untouched legacy
    # installations.  Once either private users or group chats are configured
    # in Dashboard, groups become an explicit allowlist as well.
    if policy.source == "legacy" and not policy.allowed_chat_ids and not allowed_users:
        return "RESTRICTED"
    return "DENY"

def _role_actions(agent_id: str) -> frozenset[str]:
    try:
        from agents.security.policy import agent_allowed_actions

        return agent_allowed_actions(agent_id)
    except Exception:
        return frozenset()


def _zone_capabilities(
    *,
    agent_id: str,
    zone: TrustZone,
    policy: AgentAccessPolicy,
    mutation_user: bool,
) -> frozenset[str]:
    role = set(_role_actions(agent_id))
    host_caps = set(policy.host_read_capabilities)
    # Host capabilities are an independent resource grant.  Do not let the
    # role action vocabulary (or a future role document) accidentally turn a
    # host adapter into a general-purpose machine inspection interface.
    role -= {action for action in role if action.startswith("host.") or action.startswith("lumen.")}
    if zone == "PRIVATE":
        allowed = set(role)
        if policy.host_read_mode in {"selected", "system_only"}:
            allowed |= host_caps
        if not mutation_user:
            allowed -= set(MUTATION_ACTIONS)
        return frozenset(allowed)
    if zone == "RESTRICTED":
        allowed = set(role) - host_caps
        if not mutation_user:
            allowed -= set(MUTATION_ACTIONS)
        return frozenset(allowed)
    if zone == "SHARED":
        allowed = set(role) - host_caps - set(MUTATION_ACTIONS)
        return frozenset(allowed)
    return frozenset()


def authorize_agent_interaction(
    *,
    agent_id: str,
    meta: dict[str, str],
    config: Optional[dict[str, Any]] = None,
    store: Any = None,
) -> AccessDecision:
    from agents.security.audit import emit_security_event

    data = config if isinstance(config, dict) else load_agents_config()
    policy = load_agent_access_policy(agent_id, data)
    own_store = False
    identity_store = store
    if identity_store is None:
        try:
            from feishu.identity import link_access_identities, remember_user_identity
            from risk.store import GlobalAgentStore

            identity_store = GlobalAgentStore()
            own_store = True
            remember_user_identity(
                store=identity_store,
                open_id=str(meta.get("user_id") or "").strip(),
                display_name=str(meta.get("user_name") or "").strip(),
                union_id=str(meta.get("union_id") or "").strip(),
                agent_id=agent_id,
            )
            link_access_identities(
                store=identity_store,
                identity_ids=sorted(
                    policy.allowed_user_ids | policy.owners | policy.admins | policy.mutation_allowed_user_ids
                ),
            )
        except Exception:
            identity_store = None
            own_store = False
    try:
        context = interaction_context_from_meta(
            agent_id=agent_id, meta=meta, policy=policy, store=identity_store
        )
        zone = resolve_trust_zone(context, policy, store=identity_store)
        context = InteractionContext(
            agent_id=context.agent_id,
            user_id=context.user_id,
            chat_id=context.chat_id,
            chat_type=context.chat_type,
            thread_id=context.thread_id,
            message_id=context.message_id,
            is_dm=context.is_dm,
            trust_zone=zone,
            is_owner=_user_in(identity_store, context.user_id, policy.owners),
            is_admin=_user_in(identity_store, context.user_id, policy.admins),
        )
        if zone == "DENY":
            reason = "DM_ONLY" if policy.dm_only and not context.is_dm else "ACCESS_DENIED"
            if policy.source == "missing":
                reason = "AGENT_ACCESS_UNCONFIGURED"
            decision = AccessDecision(
                allowed=False,
                reason_code=reason,
                trust_zone=None,
                host_read_allowed=False,
                mutation_allowed=False,
                effective_capabilities=frozenset(),
                exposure_mode=policy.exposure_mode,
                context=context,
                policy=policy,
            )
            emit_security_event(
                "agent.access.denied",
                agent_id=context.agent_id,
                user_id=context.user_id,
                chat_id=context.chat_id,
                chat_type=context.chat_type,
                exposure_mode=policy.exposure_mode,
                reason_code=reason,
                policy_version=POLICY_VERSION,
            )
            return decision

        mutation_users = policy.mutation_allowed_user_ids | policy.admins | (
            policy.owners if policy.exposure_mode in {"owner_private", "admin_private"} else frozenset()
        )
        mutation_user = _user_in(identity_store, context.user_id, mutation_users)
        mutation_allowed = mutation_user and zone in {"PRIVATE", "RESTRICTED"}
        host_read_allowed = (
            zone == "PRIVATE"
            and policy.host_read_mode in {"selected", "system_only"}
            and bool(policy.host_read_capabilities)
            and (
                context.is_owner
                or context.is_admin
                or _user_in(identity_store, context.user_id, policy.allowed_user_ids)
            )
        )
        caps = _zone_capabilities(
            agent_id=context.agent_id,
            zone=zone,
            policy=policy,
            mutation_user=mutation_allowed,
        )
        if not host_read_allowed:
            caps = frozenset(c for c in caps if not c.startswith("host.") and not c.startswith("lumen."))
            if zone == "PRIVATE" and policy.exposure_mode == "admin_private":
                caps = frozenset(set(caps) | {c for c in policy.host_read_capabilities if c.startswith("lumen.")})
                host_read_allowed = bool(policy.host_read_capabilities)

        decision = AccessDecision(
            allowed=True,
            reason_code="ALLOWED",
            trust_zone=zone,
            host_read_allowed=host_read_allowed,
            mutation_allowed=mutation_allowed,
            effective_capabilities=caps,
            exposure_mode=policy.exposure_mode,
            context=context,
            policy=policy,
        )
        emit_security_event(
            "agent.access.allowed",
            agent_id=context.agent_id,
            user_id=context.user_id,
            chat_id=context.chat_id,
            chat_type=context.chat_type,
            trust_zone=zone,
            exposure_mode=policy.exposure_mode,
            host_read_allowed=host_read_allowed,
            mutation_allowed=mutation_allowed,
            policy_version=POLICY_VERSION,
        )
        emit_security_event(
            "agent.access.zone_resolved",
            agent_id=context.agent_id,
            user_id=context.user_id,
            chat_id=context.chat_id,
            trust_zone=zone,
            exposure_mode=policy.exposure_mode,
            policy_version=POLICY_VERSION,
        )
        return decision
    finally:
        if own_store and identity_store is not None:
            try:
                identity_store.close()
            except Exception:
                pass


def security_context_prompt(decision: AccessDecision) -> str:
    zone = decision.trust_zone or "DENY"
    host_caps = sorted(c for c in decision.effective_capabilities if c.startswith("host.") or c.startswith("lumen."))
    lines = [
        "# Security Context",
        "",
        f"Exposure mode: {decision.exposure_mode or '-'}",
        f"Trust zone: {zone}",
        "",
    ]
    if decision.host_read_allowed and host_caps:
        lines.append("Machine read capabilities:")
        lines.extend(f"- {cap}" for cap in host_caps)
    else:
        lines.append("Machine read: DENIED")
    lines.extend(
        [
            "",
            "Unavailable:",
            "- credentials",
            "- private keys",
            "- arbitrary host file inspection",
            "- raw ~/.ssh / Keychain / .env secrets",
        ]
    )
    if zone == "SHARED":
        lines.extend(["", "Shared chat: mutations denied; private owner machine data never sent."])
    return "\n".join(lines)


def mutation_allowed_for_decision(decision: AccessDecision, *, action: str) -> bool:
    if action not in MUTATION_ACTIONS:
        return True
    if not decision.allowed or not decision.mutation_allowed:
        return False
    if decision.trust_zone == "SHARED":
        return False
    return action in decision.effective_capabilities
