from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Optional

from feishu.bitable import FeishuBitable
from feishu.config import load_agents_config
from feishu.sheets import FeishuSheets, column_letter, parse_spreadsheet_token
from skills.test_case.config import (
    PK03_SHEET_HEADER_COLUMNS,
    REQUIRED_FIELDS,
    load_test_case_config,
    normalize_test_case_language,
)
from skills.test_case.dedupe import partition_new_cases
from skills.test_case.designer import TestCaseDesignUnavailable, design_test_cases
from skills.test_case.jira_read import read_jira_issue
from skills.test_case.localization import (
    localize_test_case_type,
    localize_verify_status,
    localize_verify_status_options,
)
from skills.test_case.models import format_ac_refs
from skills.test_case.validator import TestCaseDesignQualityError, validate_test_cases
from skills.test_case.workspace_context import enrich_story_from_workspace, load_workspace_context

PK03_PATH_OPTIONS = ("Happy", "Alternative", "Sad", "Sad(Edge)")
PK03_PATH_COLORS = ("#bacefd", "#fed4a4", "#b1e8fc", "#7edafb")

DesignRunner = Callable[[str], str]


def _workspace_ai_config(
    workspace: Path | None,
    config: Optional[dict[str, Any]],
) -> dict[str, Any]:
    """Use the workspace-wide AI provider for every test-case design call."""
    data = load_agents_config() if config is None else dict(config) if isinstance(config, dict) else {}
    if workspace is None:
        return data
    root = Path(workspace).expanduser()
    for common_path in (root / "config" / "common.json", root / "lumon" / "config" / "common.json"):
        try:
            common = json.loads(common_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        execution = common.get("execution") if isinstance(common, dict) else None
        if isinstance(execution, dict) and (execution.get("provider") or execution.get("model")):
            data["execution"] = dict(execution)
            break
    return data


def story_sheet_name(story_key: str, story_title: str) -> str:
    key = str(story_key or "").strip() or "Story"
    title = str(story_title or "").strip() or key
    name = f"{key} · {title}".strip()
    return name[:100]


def _ensure_table(client: FeishuBitable, app_token: str, table_name: str) -> str:
    tables = client.list_tables(app_token)
    for table in tables:
        if str(table.get("name") or "").strip() == table_name:
            return str(table.get("table_id") or table.get("id") or "").strip()
    created = client.create_table(app_token, table_name)
    table_id = str(created.get("table_id") or created.get("id") or "").strip()
    if not table_id:
        raise RuntimeError("failed to create Test Cases table")
    return table_id


def _verify_status_property(language: str) -> dict[str, Any]:
    return {
        "options": [
            {"name": option, "color": index}
            for index, option in enumerate(localize_verify_status_options(language))
        ]
    }


def _ensure_fields(client: FeishuBitable, app_token: str, table_id: str, language: str = "zh-Hant") -> None:
    fields = client.list_fields(app_token, table_id)
    existing = {
        str(field.get("field_name") or field.get("name") or "").strip(): field
        for field in fields
        if isinstance(field, dict)
    }
    for name, field_type in REQUIRED_FIELDS:
        field = existing.get(name)
        property = _verify_status_property(language) if name == "Verify Status" else None
        if field is not None:
            field_id = str(field.get("field_id") or field.get("id") or "").strip()
            if name == "Verify Status" and int(field.get("type") or 0) != field_type and field_id:
                client.update_field(
                    app_token,
                    table_id,
                    field_id,
                    name=name,
                    field_type=field_type,
                    property=property,
                )
            continue
        client.create_field(app_token, table_id, name=name, field_type=field_type, property=property)


def _ensure_story_view(client: FeishuBitable, app_token: str, table_id: str, *, story_key: str, story_title: str) -> tuple[str, str]:
    view_name = f"{story_key} · {(story_title or story_key)[:80]}".strip()

    def _find() -> tuple[str, str]:
        for view in client.list_views(app_token, table_id):
            name = str(view.get("view_name") or view.get("name") or "").strip()
            if name == view_name:
                return view_name, str(view.get("view_id") or view.get("id") or "").strip()
        return view_name, ""

    found_name, found_id = _find()
    if found_id:
        return found_name, found_id
    try:
        created = client.create_view(app_token, table_id, name=view_name)
        view_id = str(created.get("view_id") or created.get("id") or "").strip()
        if view_id:
            return view_name, view_id
    except Exception:
        pass
    return _find()


def build_sheet_url(
    *,
    app_token: str = "",
    table_id: str = "",
    view_id: str = "",
    host: str = "inspiregroup.feishu.cn",
    destination: str = "bitable",
    spreadsheet_token: str = "",
    sheet_id: str = "",
) -> str:
    host_name = str(host or "inspiregroup.feishu.cn").strip() or "inspiregroup.feishu.cn"
    if str(destination or "").strip().lower() == "sheet":
        token = parse_spreadsheet_token(spreadsheet_token or app_token)
        if not token:
            return ""
        url = f"https://{host_name}/sheets/{token}"
        sid = str(sheet_id or "").strip()
        return f"{url}?sheet={sid}" if sid else url
    token = str(app_token or "").strip()
    table = str(table_id or "").strip()
    if not token or not table:
        return ""
    base = f"https://{host_name}/base/{token}"
    query = [f"table={table}"]
    view = str(view_id or "").strip()
    if view:
        query.append(f"view={view}")
    return f"{base}?{'&'.join(query)}"


def format_sheet_link(sheet_url: str, label: str = "Open Test Cases sheet") -> str:
    url = str(sheet_url or "").strip()
    if not url:
        return ""
    text = (label or "Open Test Cases sheet").replace("'", "").strip() or "Open Test Cases sheet"
    return f"<link icon='sheet-bitable_outlined' url='{url}'>{text}</link>\n{url}"


def _existing_titles_for_story(records: list[dict[str, Any]], story_key: str) -> set[str]:
    titles: set[str] = set()
    key = story_key.upper()
    for record in records:
        fields = record.get("fields") if isinstance(record.get("fields"), dict) else {}
        story = str(fields.get("Story Key") or "").strip().upper()
        if story and story != key:
            continue
        title = str(fields.get("Title") or "").strip()
        if title:
            titles.add(title)
    return titles


def _last_nonempty_row(rows: list[list[Any]]) -> int:
    last = 0
    for index, row in enumerate(rows, start=1):
        if any(str(cell or "").strip() for cell in row):
            last = index
    return last


def _pk03_existing_titles(rows: list[list[Any]]) -> set[str]:
    if not rows:
        return set()
    header = [str(cell or "").strip() for cell in rows[0]]
    try:
        title_index = header.index("Test Summary")
    except ValueError:
        return set()
    titles: set[str] = set()
    for row in rows[1:]:
        if title_index < len(row):
            title = str(row[title_index] or "").strip()
            if title:
                titles.add(title)
    return titles


def _pk03_next_case_number(rows: list[list[Any]]) -> int:
    if not rows:
        return 1
    header = [str(cell or "").strip() for cell in rows[0]]
    try:
        id_index = header.index("用例 ID")
    except ValueError:
        return 1
    highest = 0
    for row in rows[1:]:
        if id_index >= len(row):
            continue
        value = str(row[id_index] or "").strip()
        if value.upper().startswith("TC-"):
            try:
                highest = max(highest, int(value[3:]))
            except ValueError:
                continue
    return highest + 1


def _pk03_case_row(
    case: Any,
    *,
    story_key: str,
    story_title: str,
    language: str,
    case_number: int,
    jira_base_url: str,
) -> list[str]:
    case.ensure_meta()
    card_url = f"{str(jira_base_url or 'https://inspire.atlassian.net').rstrip('/')}/browse/{story_key}"
    card_title = story_sheet_name(story_key, story_title)
    type_label = localize_test_case_type(case.case_type, language)
    return [
        card_url,
        card_title,
        format_ac_refs(case.ac_refs),
        f"TC-{case_number:03d}",
        "",
        str(case.title or ""),
        str(case.preconditions or ""),
        "",
        str(case.steps or ""),
        str(case.expected_result or ""),
        "",
        localize_verify_status("pending", language),
        "",
        f"Type: {type_label}",
        "",
    ]


def _write_cases_to_sheet(
    *,
    client: FeishuSheets,
    cfg: dict[str, Any],
    story_key: str,
    story_title: str,
    generated: list[Any],
    language: str,
    generated_by: str,
) -> dict[str, Any]:
    spreadsheet_token = str(cfg.get("spreadsheet_token") or "").strip()
    tab_name = story_sheet_name(story_key, story_title)
    template_sheet_id = str(cfg.get("sheet_template_id") or "").strip()
    if not template_sheet_id:
        raise RuntimeError("PK03 sheet template is not configured (sheet_template_id is missing)")
    sheets = client.list_sheets(spreadsheet_token)
    sheet = next(
        (
            item
            for item in sheets
            if str(item.get("title") or item.get("name") or "").strip() == tab_name
        ),
        None,
    )
    created_sheet = sheet is None
    if sheet is None:
        sheet = client.copy_sheet(
            spreadsheet_token,
            source_sheet_id=template_sheet_id,
            title=tab_name,
        )
    sheet_id = str(sheet.get("sheetId") or sheet.get("sheet_id") or "").strip()
    if not sheet_id:
        refreshed = client.list_sheets(spreadsheet_token)
        sheet = next(
            (
                item
                for item in refreshed
                if str(item.get("title") or item.get("name") or "").strip() == tab_name
            ),
            None,
        )
        sheet_id = str((sheet or {}).get("sheetId") or (sheet or {}).get("sheet_id") or "").strip()
    if not sheet_id:
        raise RuntimeError(f"Feishu sheet id missing for {tab_name!r}")
    headers = list(PK03_SHEET_HEADER_COLUMNS)
    end_col = column_letter(len(headers) - 1)
    grid_rows = client.get_sheet_row_count(spreadsheet_token, sheet_id=sheet_id)
    if grid_rows < 2:
        raise RuntimeError(f"Feishu Sheet grid is too small: {grid_rows} rows")
    rows = client.get_values(spreadsheet_token, f"{sheet_id}!A1:{end_col}{grid_rows}")
    if created_sheet:
        client.clear_values(
            spreadsheet_token,
            sheet_id=sheet_id,
            range_a1=f"A1:{end_col}{grid_rows}",
        )
        rows = [headers]
    else:
        actual_header = [str(cell or "").strip() for cell in (rows[0] if rows else [])]
        if actual_header and actual_header != headers:
            raise RuntimeError(
                f"Sheet {tab_name!r} does not use the PK03 header; refusing to mix layouts"
            )
        if not actual_header:
            client.set_values(
                spreadsheet_token,
                sheet_id=sheet_id,
                range_a1=f"A1:{end_col}1",
                values=[headers],
            )
            rows = [headers]
    existing = _pk03_existing_titles(rows)
    created, skipped = partition_new_cases(generated, existing)
    next_case_number = _pk03_next_case_number(rows)
    values = []
    for offset, case in enumerate(created):
        case.generated_by = generated_by
        values.append(
            _pk03_case_row(
                case,
                story_key=story_key,
                story_title=story_title,
                language=language,
                case_number=next_case_number + offset,
                jira_base_url=str(cfg.get("jira_base_url") or "https://inspire.atlassian.net"),
            )
        )
    if created_sheet:
        client.set_values(
            spreadsheet_token,
            sheet_id=sheet_id,
            range_a1=f"A1:{end_col}{1 + len(values)}",
            values=[headers, *values],
        )
    elif values:
        start_row = _last_nonempty_row(rows) + 1
        client.set_values(
            spreadsheet_token,
            sheet_id=sheet_id,
            range_a1=f"A{start_row}:{end_col}{start_row + len(values) - 1}",
            values=values,
        )
    body_end_row = max(
        2,
        _last_nonempty_row([headers, *values])
        if created_sheet
        else _last_nonempty_row(rows) + len(values),
    )
    validation_range = f"E2:E{body_end_row}"
    try:
        client.set_dropdown(
            spreadsheet_token,
            sheet_id=sheet_id,
            range_a1=validation_range,
            options=list(PK03_PATH_OPTIONS),
            colors=list(PK03_PATH_COLORS),
        )
    except Exception as exc:
        raise RuntimeError(f"Feishu Sheet dropdown setup failed: {exc}") from exc
    try:
        client.verify_sheet_format(
            spreadsheet_token,
            sheet_id=sheet_id,
            freeze_rows=1,
            validation_range=validation_range,
            validation_options=list(PK03_PATH_OPTIONS),
        )
    except Exception as exc:
        raise RuntimeError(f"Feishu Sheet read-back verification failed: {exc}") from exc
    sheet_url = build_sheet_url(
        destination="sheet",
        spreadsheet_token=spreadsheet_token,
        sheet_id=sheet_id,
        host=str(cfg.get("feishu_base_host") or "inspiregroup.feishu.cn"),
    )
    return {
        "created_cases": created,
        "skipped_cases": skipped,
        "view_name": tab_name,
        "table_id": sheet_id,
        "view_id": "",
        "sheet_url": sheet_url,
    }


def _count_types(cases: list[Any], language: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for case in cases:
        key = str(getattr(case, "case_type", "") or "").strip().lower()
        if not key:
            continue
        try:
            label = localize_test_case_type(key, language)
        except Exception:
            label = key
        counts[label] = counts.get(label, 0) + 1
    return counts


def format_summary(result: dict[str, Any], language: str = "") -> str:
    language = normalize_test_case_language(language or str(result.get("response_language") or "en"))
    counts = result.get("test_case_counts") if isinstance(result.get("test_case_counts"), dict) else {}
    sheet_url = str(result.get("sheet_url") or "").strip()
    view_name = str(result.get("view_name") or "").strip()
    issue_key = str(result.get("issue_key") or "").strip()
    story_title = " ".join(str(result.get("story_title") or "").split())
    issue_label = " — ".join(item for item in (issue_key, story_title) if item)
    labels = {
        "zh-Hant": {"added": "新增", "existing": "已存在", "sheet": "飛書測試用例表：", "warnings": "警告"},
        "zh-Hans": {"added": "新增", "existing": "已存在", "sheet": "飞书测试用例表：", "warnings": "警告"},
        "en": {"added": "Added", "existing": "Existing", "sheet": "Feishu Test Cases sheet:", "warnings": "Warnings"},
    }[language]
    if language == "en":
        headline = f"Generated {result.get('generated', 0)} test cases for {issue_label}."
    elif language == "zh-Hans":
        headline = f"已为 {issue_label} 生成 {result.get('generated', 0)} 个测试用例。"
    else:
        headline = f"已為 {issue_label} 生成 {result.get('generated', 0)} 個測試用例。"
    lines = [headline, ""]
    for label, count in counts.items():
        lines.append(f"- {label}: {count}")
    lines.extend(
        [
            f"- {labels['added']}: {result.get('created', 0)}",
            f"- {labels['existing']}: {result.get('skipped_existing', 0)}",
            "",
            labels["sheet"],
        ]
    )
    link = format_sheet_link(sheet_url, view_name or "Open Test Cases sheet")
    if link:
        lines.append(link)
    elif view_name:
        lines.append(view_name)
    warnings = result.get("warnings") if isinstance(result.get("warnings"), list) else []
    if warnings:
        lines.extend(["", f"{labels['warnings']}:"] + [f"- {w}" for w in warnings[:8]])
    return "\n".join(lines).strip()


def _design_and_validate(
    *,
    story,
    workspace_ctx: dict[str, Any],
    language: str,
    workspace: Path | None,
    agents_config: dict[str, Any] | None,
    designer_runner: DesignRunner | None,
):
    last_error: Exception | None = None
    for _attempt in range(2):
        try:
            drafts = design_test_cases(
                story,
                workspace_context=workspace_ctx,
                language=language,
                workspace=workspace,
                runner=designer_runner,
                agents_config=agents_config,
            )
            return validate_test_cases(drafts, story=story, language=language)
        except TestCaseDesignUnavailable:
            raise
        except TestCaseDesignQualityError as exc:
            last_error = exc
            continue
        except Exception as exc:
            last_error = TestCaseDesignQualityError(str(exc)[:500])
            continue
    assert last_error is not None
    raise last_error


def generate_test_cases_for_issue(
    *,
    project: str,
    issue_key: str,
    workspace: Path | None = None,
    requested_by: str = "",
    generated_by: str = "mark",
    response_language: str = "",
    source_message_id: str = "",
    trace_id: str = "",
    config: Optional[dict[str, Any]] = None,
    client: FeishuBitable | None = None,
    sheets_client: FeishuSheets | None = None,
    story_reader=None,
    designer_runner: DesignRunner | None = None,
) -> dict[str, Any]:
    config = _workspace_ai_config(workspace, config)
    cfg = load_test_case_config(project, config=config)
    generated_by = str(generated_by or "mark").strip() or "mark"
    destination = str(cfg.get("destination") or "bitable")
    language = str(cfg.get("language") or "zh-Hant")
    response_language = normalize_test_case_language(response_language or language)
    app_token = cfg.get("base_app_token") or ""
    spreadsheet_token = cfg.get("spreadsheet_token") or ""
    if destination == "sheet" and not spreadsheet_token:
        return {
            "status": "failed",
            "code": "TEST_CASE_CONFIG_MISSING",
            "message": f"No Feishu Spreadsheet token configured for project {project}",
            "trace_id": trace_id,
        }
    if destination != "sheet" and not app_token:
        return {
            "status": "failed",
            "code": "TEST_CASE_CONFIG_MISSING",
            "message": f"No Feishu Bitable app token configured for project {project}",
            "trace_id": trace_id,
        }
    reader = story_reader or read_jira_issue
    try:
        story = reader(issue_key)
    except Exception as exc:
        from skills.test_case.workspace_context import load_workspace_story

        local = load_workspace_story(workspace=workspace, issue_key=issue_key)
        if local is None:
            return {
                "status": "failed",
                "code": "JIRA_READ_FAILED",
                "message": str(exc)[:500],
                "trace_id": trace_id,
            }
        story = local
        story.warnings = list(story.warnings or []) + [f"jira unavailable; used workspace story ({str(exc)[:160]})"]
    if str(story.type or "").lower() not in {"story", "bug", ""}:
        return {
            "status": "failed",
            "code": "UNSUPPORTED_ISSUE_TYPE",
            "message": f"Only Story/Bug supported in M1.0, got {story.type}",
            "trace_id": trace_id,
        }
    story = enrich_story_from_workspace(story, workspace=workspace)
    if not story.summary and not story.acceptance_criteria:
        return {
            "status": "failed",
            "code": "STORY_CONTEXT_EMPTY",
            "message": f"No usable story title/AC from Jira or workspace for {issue_key}",
            "trace_id": trace_id,
        }
    workspace_ctx = load_workspace_context(workspace=workspace, issue_key=story.key)
    try:
        generated = _design_and_validate(
            story=story,
            workspace_ctx=workspace_ctx,
            language=language,
            workspace=workspace,
            agents_config=config if isinstance(config, dict) else None,
            designer_runner=designer_runner,
        )
    except TestCaseDesignUnavailable as exc:
        return {
            "status": "failed",
            "code": "TEST_CASE_DESIGN_UNAVAILABLE",
            "message": str(exc)[:500],
            "trace_id": trace_id,
        }
    except TestCaseDesignQualityError as exc:
        return {
            "status": "failed",
            "code": "TEST_CASE_DESIGN_QUALITY_FAILED",
            "message": str(exc)[:500],
            "trace_id": trace_id,
        }
    try:
        if destination == "sheet":
            sheets = sheets_client or FeishuSheets(agent_id=generated_by)
            written = _write_cases_to_sheet(
                client=sheets,
                cfg=cfg,
                story_key=story.key,
                story_title=story.summary,
                generated=generated,
                language=language,
                generated_by=generated_by,
            )
            created_cases = written["created_cases"]
            skipped_cases = written["skipped_cases"]
            view_name = written["view_name"]
            table_id = written["table_id"]
            view_id = written["view_id"]
            sheet_url = written["sheet_url"]
        else:
            bitable = client or FeishuBitable(agent_id=generated_by)
            table_id = _ensure_table(bitable, app_token, cfg["table_name"])
            _ensure_fields(bitable, app_token, table_id, language)
            records = bitable.list_records(app_token, table_id)
            existing = _existing_titles_for_story(records, story.key)
            created_cases, skipped_cases = partition_new_cases(generated, existing)
            for case in created_cases:
                case.generated_by = generated_by
                bitable.create_record(app_token, table_id, case.to_fields(language))
            view_name, view_id = _ensure_story_view(
                bitable,
                app_token,
                table_id,
                story_key=story.key,
                story_title=story.summary,
            )
            sheet_url = build_sheet_url(
                app_token=app_token,
                table_id=table_id,
                view_id=view_id,
                host=str(cfg.get("feishu_base_host") or "inspiregroup.feishu.cn"),
            )
    except Exception as exc:
        message = str(exc)
        if "99991663" in message or "99991672" in message or "permission" in message.lower():
            code = "FEISHU_TABLE_PERMISSION_DENIED"
        elif destination == "sheet":
            code = "FEISHU_SHEETS_FAILED"
        else:
            code = "FEISHU_BITABLE_FAILED"
        return {
            "status": "failed",
            "code": code,
            "message": message[:500],
            "trace_id": trace_id,
        }
    counts = _count_types(generated, response_language)
    result = {
        "status": "completed",
        "issue_key": story.key,
        "story_title": story.summary,
        "generated": len(generated),
        "created": len(created_cases),
        "skipped_existing": len(skipped_cases),
        "obsolete_marked": 0,
        "view_name": view_name,
        "table_id": table_id,
        "view_id": view_id,
        "sheet_url": sheet_url,
        "destination": destination,
        "response_language": response_language,
        "test_case_counts": counts,
        "warnings": list(story.warnings),
        "requested_by": requested_by,
        "source_message_id": source_message_id,
        "trace_id": trace_id,
        "summary": "",
    }
    result["summary"] = format_summary(result, response_language)
    return result
