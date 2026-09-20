"""Pure Feishu card rendering for the Auto Delivery lifecycle."""

from __future__ import annotations

from collections.abc import Mapping

from lumon.delivery.model import DeliveryEvent, DeliveryRun, DeliveryState

_EVENT_TITLES: Mapping[DeliveryEvent, str] = {
    DeliveryEvent.STARTED: "Lumon · Delivery Started",
    DeliveryEvent.DEV_DONE: "Lumon · Delivery Completed",
    DeliveryEvent.FAILED: "Lumon · Delivery Needs Attention",
    DeliveryEvent.BLOCKED: "Lumon · Delivery Blocked",
}

_EVENT_TEMPLATES: Mapping[DeliveryEvent, str] = {
    DeliveryEvent.STARTED: "blue",
    DeliveryEvent.DEV_DONE: "green",
    DeliveryEvent.FAILED: "red",
    DeliveryEvent.BLOCKED: "orange",
}


def build_delivery_card(event: DeliveryEvent | str, run: DeliveryRun) -> dict[str, object]:
    """Build a Feishu Interactive Card 2.0 payload without side effects."""

    event = DeliveryEvent(event)
    subtitle = " · ".join(part for part in (run.story_key.strip(), run.story_title.strip()) if part)
    elements = [{"tag": "markdown", "content": _overview(run)}, {"tag": "hr"}]
    elements.append({"tag": "markdown", "content": _event_detail(event, run)})
    if run.pull_request_url:
        elements.extend(
            [
                {"tag": "hr"},
                {
                    "tag": "markdown",
                    "content": f"**Pull request**\n{run.pull_request_url}",
                },
            ]
        )

    card: dict[str, object] = {
        "msg_type": "interactive",
        "card": {
            "schema": "2.0",
            "header": {
                "title": {"tag": "plain_text", "content": _EVENT_TITLES[event]},
                "subtitle": {"tag": "plain_text", "content": subtitle or "Delivery"},
                "template": _EVENT_TEMPLATES[event],
            },
            "body": {"elements": elements},
        },
    }
    if run.jira_url:
        card_payload = card["card"]
        assert isinstance(card_payload, dict)
        card_payload["card_link"] = {"url": run.jira_url}
    return card


def _overview(run: DeliveryRun) -> str:
    lines = [
        f"**Status:**  {_status_label(run.state)}",
        f"**Phase:**  `{run.phase}`",
    ]
    if run.repository:
        lines.append(f"**Repository:**  `{run.repository}`")
    if run.branch:
        lines.append(f"**Branch:**  `{run.branch}`")
    if run.duration_seconds is not None:
        lines.append(f"**Duration:**  {_format_duration(run.duration_seconds)}")
    if run.verification_summary:
        lines.append(f"**Verification:**  {run.verification_summary}")
    return "\n".join(lines)


def _event_detail(event: DeliveryEvent, run: DeliveryRun) -> str:
    if event is DeliveryEvent.STARTED:
        return (
            "**What happens next**\n"
            "Lumon has claimed the Story and is preparing the environment, "
            "worktree, and verification."
        )
    if event is DeliveryEvent.DEV_DONE:
        published = "Changes were published successfully."
        if run.pull_request_url:
            published = "Changes were verified and a pull request was created."
        return f"**Result**\n{published}"
    if event is DeliveryEvent.BLOCKED:
        return (
            f"**Blocked at phase**  `{run.phase}`\n"
            "**Reason**  "
            f"{run.reason or 'Additional context is required before Lumon can continue.'}"
        )
    return (
        f"**Action required**\nLumon stopped during `{run.phase}`.\n\n"
        f"**Reason**  {run.reason or 'An unexpected delivery error occurred.'}"
    )


def _status_label(state: DeliveryState) -> str:
    return state.value.replace("_", " ").title()


def _format_duration(seconds: int) -> str:
    minutes, remaining = divmod(seconds, 60)
    if minutes:
        return f"{minutes}m {remaining:02d}s"
    return f"{remaining}s"
