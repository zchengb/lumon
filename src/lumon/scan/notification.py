"""Render scan results using the legacy Feishu Card 2.0 layout."""

from lumon.scan.model import ScanRun, ScanState
from lumon.tools.safety import sanitize_output


def _text(text: str) -> str:
    clean = sanitize_output(text)
    for character in ("\\", "*", "_", "`", "[", "]"):
        clean = clean.replace(character, "\\" + character)
    return clean


def build_scan_card(run: ScanRun, model: str) -> dict[str, object]:
    """Build a message without reading configuration or contacting Feishu."""
    counts = {
        level: sum(f.severity == level for f in run.findings) for level in ("High", "Medium", "Low")
    }
    color = "green"
    if counts["Medium"] or run.failures:
        color = "orange"
    if counts["High"] or run.state == ScanState.FAILED:
        color = "red"
    status = run.state.value.replace("_", " ").capitalize()
    elements: list[dict[str, object]] = [
        {
            "tag": "markdown",
            "content": (
                f"**Scan Window:** {run.scan_window}\n"
                f"**Repositories Scanned:** {run.repositories_scanned}\n"
                f"**Model:** {_text(model)}\n**Status:** {status}"
            ),
        },
        {"tag": "hr"},
        {
            "tag": "markdown",
            "content": (
                f"**Overall Summary**\n🔴 High: **{counts['High']}**\n"
                f"🟡 Medium: **{counts['Medium']}**\n🟢 Low: **{counts['Low']}**"
            ),
        },
        {"tag": "hr"},
    ]
    for index, finding in enumerate(run.findings, 1):
        if index > 1:
            elements.append({"tag": "hr"})
        elements.append(
            {
                "tag": "markdown",
                "content": (
                    f"**Finding {index} — {_text(finding.title)}**\n"
                    f"**Severity:** {finding.severity}\n"
                    f"**Repository:** {_text(finding.repository)}\n"
                    f"**Impact:** {_text(finding.impact)}\n"
                    f"**Trigger:** {_text(finding.trigger)}"
                ),
            }
        )
        elements.append(
            {
                "tag": "collapsible_panel",
                "expanded": False,
                "header": {"title": {"tag": "plain_text", "content": "View detail"}},
                "elements": [
                    {
                        "tag": "markdown",
                        "content": (
                            f"**File:** {_text(finding.file)}:{_text(finding.line_range)}\n"
                            f"**Code Snippet:** {_text(finding.code_snippet)}\n"
                            f"**Suggestion:** {_text(finding.suggestion)}"
                        ),
                    }
                ],
            }
        )
    if not run.findings:
        empty_summary = "No confirmed findings were detected in this scan window."
        if run.state in {ScanState.FAILED, ScanState.COMPLETED_WITH_FAILURES}:
            empty_summary = "Review incomplete; no confirmed findings recorded. See failures."
        elements.append(
            {
                "tag": "markdown",
                "content": f"**Findings:** {empty_summary}",
            }
        )
    if run.failures:
        elements.extend(
            [
                {"tag": "hr"},
                {
                    "tag": "markdown",
                    "content": "**Failures:**\n" + "\n".join(_text(item) for item in run.failures),
                },
            ]
        )
    return {
        "msg_type": "interactive",
        "card": {
            "schema": "2.0",
            "config": {"wide_screen_mode": True},
            "header": {
                "template": color,
                "title": {
                    "tag": "plain_text",
                    "content": "🔎 Lumon — Code Quality & Security Scan Report",
                },
            },
            "body": {"elements": elements},
        },
    }
