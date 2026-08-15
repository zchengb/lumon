from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Any


_PLAN_MARKER = re.compile(r"(?:technical[- ]plan|story[- ]plan)(?:\.md)?", re.IGNORECASE)
_TICKET = re.compile(r"\b[A-Z][A-Z0-9]+-\d+\b")
_FENCE = re.compile(r"^\s*```(?:[A-Za-z0-9_+-]+)?\s*$")
_TABLE_SEPARATOR = re.compile(r"^:?-{3,}:?$")
_METADATA_FIELD = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*):\s*(.*?)\s*$")


def is_plan_document(text: str) -> bool:
    raw = str(text or "").strip()
    return bool(
        len(raw) >= 600
        and _PLAN_MARKER.search(raw)
        and ("---" in raw or re.search(r"(?m)^#{1,6}\s+", raw))
    )


def plan_pdf_filename(text: str) -> str:
    raw = str(text or "")
    ticket = (_TICKET.search(raw) or ["LUMON"])[0]
    kind = "technical-plan" if "technical" in raw.lower() else "story-plan"
    return f"{ticket}-{kind}.pdf"


def _strip_outer_fence(text: str) -> str:
    raw = str(text or "").strip()
    opening = re.search(r"(?m)^[ \t]*```(?:markdown|md)[ \t]*$", raw)
    if opening is None:
        return raw
    closings = list(re.finditer(r"(?m)^[ \t]*```[ \t]*$", raw[opening.end() :]))
    if not closings:
        return raw
    closing = closings[-1]
    closing_start = opening.end() + closing.start()
    closing_end = opening.end() + closing.end()
    return "\n\n".join(
        part
        for part in (
            raw[: opening.start()].strip(),
            raw[opening.end() : closing_start].strip(),
            raw[closing_end:].strip(),
        )
        if part
    ).strip()


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
    return text or "-"


def _font_path(candidates: list[str]) -> str:
    for candidate in candidates:
        path = Path(candidate).expanduser()
        if path.is_file():
            return str(path)
    return ""


def _register_font(pdfmetrics: Any, ttfont: Any, name: str, candidates: list[str], fallback: str = "Helvetica") -> str:
    path = _font_path(candidates)
    if not path:
        return fallback
    try:
        pdfmetrics.registerFont(ttfont(name, path))
        return name
    except Exception:
        try:
            pdfmetrics.registerFont(ttfont(name, path, subfontIndex=0))
            return name
        except Exception:
            return fallback


def _register_fonts(pdfmetrics: Any, ttfont: Any) -> dict[str, str]:
    bundled = "/Users/xiaobin.zheng/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/libreoffice-headless/libreoffice/LibreOfficeDev.app/Contents/Resources/fonts/truetype"
    body = _register_font(
        pdfmetrics,
        ttfont,
        "LumonSans",
        [
            "~/Library/Fonts/MiSans-Regular.ttf",
            "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
            "/System/Library/Fonts/Hiragino Sans GB.ttc",
            f"{bundled}/NotoSans-Regular.ttf",
        ],
    )
    bold = _register_font(
        pdfmetrics,
        ttfont,
        "LumonSansBold",
        [
            "~/Library/Fonts/MiSans-Semibold.ttf",
            "~/Library/Fonts/MiSans-Bold.ttf",
            "/System/Library/Fonts/STHeiti Medium.ttc",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            f"{bundled}/NotoSans-Bold.ttf",
        ],
        fallback=body,
    )
    mono = _register_font(
        pdfmetrics,
        ttfont,
        "LumonMono",
        [
            # MiSans keeps CJK characters readable in Mermaid and code blocks.
            # Menlo remains a fallback for installations without the local font.
            "~/Library/Fonts/MiSans-Regular.ttf",
            "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
            "/System/Library/Fonts/Menlo.ttc",
            "/System/Library/Fonts/Monaco.ttf",
            f"{bundled}/DejaVuSansMono.ttf",
        ],
        fallback="Courier",
    )
    return {"body": body, "bold": bold, "mono": mono}


def _inline_markup(value: str, fonts: dict[str, str]) -> str:
    placeholders: dict[str, str] = {}

    def hold(markup: str) -> str:
        token = f"@@LUMON_MARKUP_{len(placeholders)}@@"
        placeholders[token] = markup
        return token

    raw = str(value or "")

    def link(match: re.Match[str]) -> str:
        label = html.escape(match.group(1), quote=False)
        url = html.escape(match.group(2), quote=True)
        return hold(f'<link href="{url}" color="#1769aa">{label}</link>')

    raw = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", link, raw)

    def code(match: re.Match[str]) -> str:
        return hold(
            f'<font name="{fonts["mono"]}" backColor="#eef2f7">'
            f"{html.escape(match.group(1), quote=False)}"
            "</font>"
        )

    raw = re.sub(r"`([^`]+)`", code, raw)
    escaped = html.escape(raw, quote=False)
    escaped = re.sub(r"\*\*([^*\n]+)\*\*", r"<b>\1</b>", escaped)
    escaped = re.sub(r"__([^_\n]+)__", r"<b>\1</b>", escaped)
    escaped = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<i>\1</i>", escaped)
    escaped = escaped.replace("  \n", "<br/>").replace("\n", "<br/>")
    for token, markup in placeholders.items():
        escaped = escaped.replace(token, markup)
    return escaped


def _title_from_markdown(text: str) -> str:
    for line in _strip_outer_fence(text).splitlines():
        match = re.match(r"^\s*#\s+(.+?)\s*$", line)
        if match:
            return re.sub(r"[`*_]", "", match.group(1)).strip()
    return "Lumon Engineering Plan"


def _metadata_flowable(fields: list[tuple[str, str]], styles: dict[str, Any], fonts: dict[str, str], width: float) -> list[Any]:
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors

    rows = [
        [
            Paragraph(f"<b>{html.escape(_metadata_label(key))}</b>", styles["metadata_label"]),
            Paragraph(_inline_markup(_metadata_value(value), fonts), styles["metadata_value"]),
        ]
        for key, value in fields
    ]
    table = Table(rows, colWidths=[width * 0.22, width * 0.78], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f5f7fa")),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#d7dee8")),
                ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#e2e8f0")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return [Paragraph("Document metadata", styles["metadata_heading"]), table, Spacer(1, 12)]


def _table_flowable(rows: list[list[str]], styles: dict[str, Any], fonts: dict[str, str], width: float) -> Any:
    from reportlab.platypus import Paragraph, Table, TableStyle
    from reportlab.lib import colors

    column_count = max(len(row) for row in rows)
    normalized = [row + [""] * (column_count - len(row)) for row in rows]
    data: list[list[Any]] = []
    for row_index, row in enumerate(normalized):
        cell_style = styles["table_header"] if row_index == 0 else styles["table_body"]
        data.append([Paragraph(_inline_markup(cell, fonts), cell_style) for cell in row])
    table = Table(data, colWidths=[width / column_count] * column_count, repeatRows=1, hAlign="LEFT")
    commands = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e79")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#dbe3ec")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]
    for row_index in range(1, len(normalized)):
        if row_index % 2 == 0:
            commands.append(("BACKGROUND", (0, row_index), (-1, row_index), colors.HexColor("#f8fafc")))
    table.setStyle(TableStyle(commands))
    return table


def _code_flowable(code: str, styles: dict[str, Any]) -> Any:
    from reportlab.platypus import Paragraph

    content = "<br/>".join(html.escape(line, quote=False) for line in str(code or "").splitlines()) or " "
    return Paragraph(content, styles["code"])


def _styles(fonts: dict[str, str]) -> dict[str, Any]:
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle

    return {
        "body": ParagraphStyle(
            "LumonBody", fontName=fonts["body"], fontSize=9.6, leading=14.5, textColor=colors.HexColor("#273444"),
            spaceAfter=7, wordWrap="CJK",
        ),
        "title": ParagraphStyle(
            "LumonTitle", parent=None, fontName=fonts["bold"], fontSize=23, leading=29,
            textColor=colors.HexColor("#132238"), spaceBefore=3, spaceAfter=16, wordWrap="CJK",
        ),
        "h1": ParagraphStyle(
            "LumonH1", fontName=fonts["bold"], fontSize=17, leading=22, textColor=colors.HexColor("#173b63"),
            spaceBefore=16, spaceAfter=8, keepWithNext=True, wordWrap="CJK",
        ),
        "h2": ParagraphStyle(
            "LumonH2", fontName=fonts["bold"], fontSize=13, leading=18, textColor=colors.HexColor("#245b87"),
            spaceBefore=12, spaceAfter=5, keepWithNext=True, wordWrap="CJK",
        ),
        "h3": ParagraphStyle(
            "LumonH3", fontName=fonts["bold"], fontSize=10.5, leading=15, textColor=colors.HexColor("#334e68"),
            spaceBefore=9, spaceAfter=4, keepWithNext=True, wordWrap="CJK",
        ),
        "bullet": ParagraphStyle(
            "LumonBullet", parent=None, fontName=fonts["body"], fontSize=9.4, leading=14,
            leftIndent=15, firstLineIndent=0, bulletIndent=2, spaceAfter=4, wordWrap="CJK",
        ),
        "ordered": ParagraphStyle(
            "LumonOrdered", parent=None, fontName=fonts["body"], fontSize=9.4, leading=14,
            leftIndent=18, firstLineIndent=0, bulletIndent=1, spaceAfter=4, wordWrap="CJK",
        ),
        "quote": ParagraphStyle(
            "LumonQuote", parent=None, fontName=fonts["body"], fontSize=9.2, leading=13.5,
            leftIndent=16, rightIndent=8, borderColor=colors.HexColor("#9fb3c8"), borderWidth=2,
            borderPadding=7, textColor=colors.HexColor("#52606d"), spaceAfter=7, wordWrap="CJK",
        ),
        "code": ParagraphStyle(
            "LumonCode", fontName=fonts["mono"], fontSize=7.7, leading=10.2, textColor=colors.HexColor("#263238"),
            backColor=colors.HexColor("#f3f5f7"), borderColor=colors.HexColor("#d7dee8"), borderWidth=0.5,
            borderPadding=8, spaceBefore=4, spaceAfter=9, wordWrap="CJK",
        ),
        "metadata_heading": ParagraphStyle(
            "LumonMetadataHeading", fontName=fonts["bold"], fontSize=11.5, leading=15,
            textColor=colors.HexColor("#245b87"), spaceBefore=2, spaceAfter=6, keepWithNext=True,
        ),
        "metadata_label": ParagraphStyle(
            "LumonMetadataLabel", fontName=fonts["bold"], fontSize=8.7, leading=12, textColor=colors.HexColor("#52606d"),
        ),
        "metadata_value": ParagraphStyle(
            "LumonMetadataValue", fontName=fonts["body"], fontSize=8.7, leading=12, textColor=colors.HexColor("#273444"),
            wordWrap="CJK",
        ),
        "table_header": ParagraphStyle(
            "LumonTableHeader", fontName=fonts["bold"], fontSize=7.8, leading=10, textColor=colors.white, wordWrap="CJK",
        ),
        "table_body": ParagraphStyle(
            "LumonTableBody", fontName=fonts["body"], fontSize=7.8, leading=10.5, textColor=colors.HexColor("#273444"),
            wordWrap="CJK",
        ),
    }


def _parse_markdown(
    text: str,
    styles: dict[str, Any],
    fonts: dict[str, str],
    width: float,
    document_title: str,
) -> list[Any]:
    from reportlab.lib import colors
    from reportlab.platypus import HRFlowable, Paragraph, Spacer

    lines = _strip_outer_fence(text).splitlines()
    story: list[Any] = []
    paragraph_lines: list[str] = []
    in_code = False
    code_lines: list[str] = []
    title_consumed = False

    def flush_paragraph() -> None:
        if paragraph_lines:
            story.append(Paragraph(_inline_markup(" ".join(line.strip() for line in paragraph_lines), fonts), styles["body"]))
            paragraph_lines.clear()

    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if in_code:
            if _FENCE.match(line):
                story.append(_code_flowable("\n".join(code_lines), styles))
                code_lines.clear()
                in_code = False
            else:
                code_lines.append(line.rstrip())
            index += 1
            continue
        if _FENCE.match(line):
            flush_paragraph()
            in_code = True
            index += 1
            continue
        if stripped == "---":
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
                flush_paragraph()
                story.extend(_metadata_flowable(fields, styles, fonts, width))
                index = cursor + 1
                continue
            flush_paragraph()
            story.append(HRFlowable(width="100%", thickness=0.7, color=colors.HexColor("#cbd5e1"), spaceBefore=5, spaceAfter=9))
            index += 1
            continue
        heading = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if heading:
            flush_paragraph()
            level = min(len(heading.group(1)), 3)
            heading_text = re.sub(r"[`*_]", "", heading.group(2)).strip()
            if not title_consumed and level == 1 and heading_text == document_title:
                title_consumed = True
                index += 1
                continue
            style = styles[f"h{level}"]
            story.append(Paragraph(_inline_markup(heading.group(2), fonts), style))
            index += 1
            continue
        if index + 1 < len(lines) and _table_cells(line) and _is_table_separator(lines[index + 1]):
            flush_paragraph()
            rows = [_table_cells(line)]
            cursor = index + 2
            while cursor < len(lines) and _table_cells(lines[cursor]):
                rows.append(_table_cells(lines[cursor]))
                cursor += 1
            story.append(_table_flowable(rows, styles, fonts, width))
            story.append(Spacer(1, 10))
            index = cursor
            continue
        bullet = re.match(r"^(\s*)[-*+]\s+(.*)$", line)
        if bullet:
            flush_paragraph()
            indent = min(len(bullet.group(1)) // 2, 4)
            style = styles["bullet"].clone(f"LumonBullet{indent}")
            style.leftIndent += indent * 12
            text_value = bullet.group(2).replace("[ ] ", "☐ ").replace("[x] ", "☑ ")
            story.append(Paragraph(_inline_markup(text_value, fonts), style, bulletText="•"))
            index += 1
            continue
        ordered = re.match(r"^\s*(\d+)[.)]\s+(.*)$", line)
        if ordered:
            flush_paragraph()
            story.append(Paragraph(_inline_markup(ordered.group(2), fonts), styles["ordered"], bulletText=f"{ordered.group(1)}."))
            index += 1
            continue
        quote = re.match(r"^\s*>\s?(.*)$", line)
        if quote:
            flush_paragraph()
            story.append(Paragraph(_inline_markup(quote.group(1), fonts), styles["quote"]))
            index += 1
            continue
        if not stripped:
            flush_paragraph()
            story.append(Spacer(1, 3))
            index += 1
            continue
        paragraph_lines.append(line)
        index += 1
    if in_code:
        story.append(_code_flowable("\n".join(code_lines), styles))
    flush_paragraph()
    return story


def render_markdown_pdf(markdown: str, output_path: str | Path, *, title: str = "") -> Path:
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_LEFT
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
    except ImportError as exc:
        raise RuntimeError("PDF export requires the reportlab package") from exc

    destination = Path(output_path).expanduser()
    destination.parent.mkdir(parents=True, exist_ok=True)
    fonts = _register_fonts(pdfmetrics, TTFont)
    document_title = title.strip() or _title_from_markdown(markdown)
    styles = _styles(fonts)
    styles["cover"] = ParagraphStyle(
        "LumonCover", parent=styles["body"], alignment=TA_LEFT, fontName=fonts["body"],
        fontSize=9, leading=13, textColor=colors.HexColor("#52606d"), spaceAfter=5,
    )
    width, _ = A4
    left = 48
    right = 48
    top = 58
    bottom = 45

    def draw_page(canvas: Any, doc: Any) -> None:
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#d7dee8"))
        canvas.setLineWidth(0.5)
        canvas.line(left, 34, width - right, 34)
        canvas.setFont(fonts["body"], 7.5)
        canvas.setFillColor(colors.HexColor("#7b8794"))
        canvas.drawString(left, 22, "LUMON · ENGINEERING DOCUMENT")
        canvas.drawRightString(width - right, 22, f"Page {doc.page}")
        canvas.restoreState()

    document = SimpleDocTemplate(
        str(destination), pagesize=A4, leftMargin=left, rightMargin=right, topMargin=top, bottomMargin=bottom,
        title=document_title, author="Lumon",
    )
    story = [Paragraph(html.escape(document_title), styles["title"]), Spacer(1, 2)]
    story.extend(_parse_markdown(markdown, styles, fonts, width - left - right, document_title))
    document.build(story, onFirstPage=draw_page, onLaterPages=draw_page)
    return destination
