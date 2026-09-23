"""Legacy-compatible HTML and Chrome PDF reports for Auto Scan."""

# The report markup intentionally mirrors the legacy template line-for-line.
# ruff: noqa: E501

from __future__ import annotations

import html
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from lumon.scan.model import ScanRun

_SECRET_PATTERNS = (
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
    re.compile(r"https://open\.feishu\.cn/open-apis/bot/v2/hook/[A-Za-z0-9._-]+"),
    re.compile(r"(?i)(password\s*[=:]\s*)['\"][^'\"]{6,}['\"]"),
    re.compile(r"(?i)(token\s*[=:]\s*)['\"][^'\"]{8,}['\"]"),
    re.compile(r"(?i)(secret\s*[=:]\s*)['\"][^'\"]{8,}['\"]"),
    re.compile(
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
        re.S,
    ),
)


@dataclass(frozen=True, slots=True)
class ReportResult:
    """Generated report paths and a safe PDF error, if any."""

    html_path: str | None
    pdf_path: str | None
    error: str | None = None


def write_report(run: ScanRun, output_directory: Path) -> ReportResult:
    """Write the old report HTML and print it to PDF with a system browser."""

    if not run.findings:
        return ReportResult(None, None)
    output_directory.mkdir(parents=True, exist_ok=True)
    html_path = output_directory / "report.html"
    pdf_path = output_directory / "report.pdf"
    html_path.write_text(_render_html(run), encoding="utf-8")
    try:
        _convert_via_chrome(html_path, pdf_path)
    except (OSError, subprocess.SubprocessError, RuntimeError) as exc:
        return ReportResult("report.html", None, str(exc)[:500])
    if not pdf_path.is_file():
        return ReportResult(
            "report.html",
            None,
            "PDF file was not created by the browser exporter.",
        )
    return ReportResult("report.html", "report.pdf")


def _render_html(run: ScanRun) -> str:
    counts = _severity_counts(run)
    findings_html = "\n".join(
        _render_finding(finding.as_payload(), index)
        for index, finding in enumerate(run.findings, start=1)
    )
    if not findings_html:
        findings_html = (
            '<p class="empty">No confirmed findings were detected in this scan window.</p>'
        )
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Code Quality & Security Review Report</title>
  <style>
    @page {{ size: A4; margin: 18mm; }}
    * {{ box-sizing: border-box; }}
    html, body {{ max-width: 100%; overflow-x: hidden; }}
    body {{
      font-family: Arial, Helvetica, sans-serif; color: #111; line-height: 1.42; font-size: 13px;
      overflow-wrap: break-word; word-wrap: break-word; word-break: break-word;
    }}
    h1 {{ font-size: 28px; margin: 0 0 8px; overflow-wrap: break-word; }}
    h2 {{ font-size: 18px; margin: 28px 0 10px; border-bottom: 1px solid #ccc; padding-bottom: 6px; }}
    h3 {{ font-size: 15px; margin: 0 0 4px; overflow-wrap: break-word; }}
    .meta, .muted {{ color: #666; overflow-wrap: break-word; }}
    .summary {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 18px 0; }}
    .metric {{ border: 1px solid #ddd; padding: 10px; background: #f7f7f7; overflow: hidden; }}
    .metric b {{ display: block; font-size: 20px; }}
    table {{ width: 100%; max-width: 100%; table-layout: fixed; border-collapse: collapse; margin: 10px 0; }}
    th, td {{
      border-bottom: 1px solid #ddd; padding: 7px; text-align: left; vertical-align: top;
      overflow-wrap: break-word; word-wrap: break-word; word-break: break-word;
    }}
    th {{ background: #f0f0f0; }}
    .finding {{ page-break-inside: avoid; border-top: 1px solid #ddd; padding-top: 14px; margin-top: 16px; overflow: hidden; }}
    dl {{ display: grid; grid-template-columns: 95px 1fr; gap: 6px 10px; max-width: 100%; }}
    dt {{ font-weight: bold; color: #333; overflow-wrap: break-word; }}
    dd {{ margin: 0; min-width: 0; overflow-wrap: break-word; word-wrap: break-word; word-break: break-word; }}
    pre {{
      white-space: pre-wrap; overflow-wrap: break-word; word-wrap: break-word; word-break: break-word;
      background: #f5f5f5; padding: 8px; border: 1px solid #ddd; max-width: 100%; overflow-x: hidden;
    }}
    code {{
      font-family: Menlo, Consolas, monospace; overflow-wrap: break-word; word-wrap: break-word;
      word-break: break-word; white-space: pre-wrap;
    }}
    .empty {{ color: #666; }}
  </style>
</head>
<body>
  <h1>Code Quality & Security Review Report</h1>
  <div class="meta">Generated: {_h(datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"))}</div>
  <div class="meta">Scan window: {_h(run.scan_window)} · Status: {_h(_status_label(run.state.value))}</div>

  <h2>1. Summary</h2>
  <div class="summary">
    <div class="metric"><span>High</span><b>{counts["High"]}</b></div>
    <div class="metric"><span>Medium</span><b>{counts["Medium"]}</b></div>
    <div class="metric"><span>Low</span><b>{counts["Low"]}</b></div>
    <div class="metric"><span>Repositories</span><b>{_h(run.repositories_scanned)}</b></div>
  </div>

  <h2>2. Findings</h2>
  {findings_html}

  <h2>3. PR Summary</h2>
  <p>0 PR(s) created in this run.</p>

  <h2>4. Decisions</h2>
  <p>Only confirmed High severity issues are eligible for automated fixes and PRs. Medium and Low issues remain report-only unless policy changes.</p>
</body>
</html>
"""


def _render_finding(finding: dict[str, str | None], index: int) -> str:
    pr = finding.get("pr_url")
    pr_html = f'<div><b>PR:</b> <a href="{_h(pr)}">{_h(pr)}</a></div>' if pr else ""
    optional = _field("Root cause", finding.get("root_cause")) + _field(
        "Validation", finding.get("validation")
    )
    return f"""
    <section class="finding">
      <div class="finding-head">
        <div>
          <h3>{index}. [{_h(finding.get("severity"))}] {_h(finding.get("title"))}</h3>
          <div class="muted">{_h(finding.get("repository"))} · {_h(finding.get("issue_id"))} · {_h(finding.get("issue_status"))}</div>
        </div>
      </div>
      <dl>
        <dt>Impact</dt><dd>{_h(finding.get("impact"))}</dd>
        <dt>Trigger</dt><dd>{_h(finding.get("trigger"))}</dd>
        <dt>File</dt><dd><code>{_h(finding.get("file"))}:{_h(finding.get("line_range"))}</code></dd>
        <dt>Code</dt><dd><pre>{_h(finding.get("code_snippet"))}</pre></dd>
        <dt>Suggestion</dt><dd>{_h(finding.get("suggestion"))}</dd>
        {optional}
      </dl>
      {pr_html}
    </section>
    """


def _field(label: str, value: str | None) -> str:
    return f"<dt>{_h(label)}</dt><dd>{_h(value)}</dd>" if value else ""


def _h(value: object) -> str:
    return html.escape(_redact(value), quote=True)


def _redact(value: object) -> str:
    text = "" if value is None else str(value)
    for pattern in _SECRET_PATTERNS:
        if pattern.pattern.startswith("(?i)("):
            text = pattern.sub(lambda match: f'{match.group(1)}"[REDACTED]"', text)
        else:
            text = pattern.sub("[REDACTED]", text)
    return text


def _severity_counts(run: ScanRun) -> dict[str, int]:
    counts = {"High": 0, "Medium": 0, "Low": 0}
    for finding in run.findings:
        counts[finding.severity] = counts.get(finding.severity, 0) + 1
    return counts


def _status_label(value: str) -> str:
    return {
        "completed": "Completed",
        "completed_with_findings": "Completed with findings",
        "completed_with_failures": "Completed with failures",
        "failed": "Failed",
    }.get(value, value)


def _convert_via_chrome(html_path: Path, pdf_path: Path) -> None:
    chrome = _find_chrome_binary()
    if not chrome:
        raise RuntimeError("Chrome/Chromium/Edge headless was not found")
    subprocess.run(
        [
            chrome,
            "--headless",
            "--disable-gpu",
            "--no-pdf-header-footer",
            f"--print-to-pdf={pdf_path}",
            html_path.resolve().as_uri(),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _find_chrome_binary() -> str | None:
    candidates = (
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        shutil.which("google-chrome"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
    )
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    return None
