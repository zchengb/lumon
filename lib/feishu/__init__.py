__all__ = [
    "FeishuChannel",
    "MessageDeduper",
    "agents_enabled",
    "agents_home",
    "configured_agents",
    "load_agents_config",
    "load_client_config",
]


def __getattr__(name: str):
    """Load Feishu integrations lazily to keep lightweight submodules acyclic."""

    if name == "FeishuChannel":
        from feishu.channel import FeishuChannel

        return FeishuChannel
    if name == "MessageDeduper":
        from feishu.dedup import MessageDeduper

        return MessageDeduper
    if name in {"agents_enabled", "agents_home", "load_agents_config"}:
        from feishu.config import agents_enabled, agents_home, load_agents_config

        return {
            "agents_enabled": agents_enabled,
            "agents_home": agents_home,
            "load_agents_config": load_agents_config,
        }[name]
    if name in {"configured_agents", "load_client_config"}:
        from feishu.client_registry import configured_agents, load_client_config

        return {"configured_agents": configured_agents, "load_client_config": load_client_config}[name]
    raise AttributeError(name)
