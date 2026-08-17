from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Optional

from feishu.messenger import FeishuMessenger


_SHEET_URL_RE = re.compile(r"/sheets/([A-Za-z0-9_-]+)", re.IGNORECASE)


def parse_spreadsheet_token(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    match = _SHEET_URL_RE.search(raw)
    if match:
        return match.group(1)
    return raw.split("?", 1)[0].rstrip("/").split("/")[-1] if "/" in raw else raw


def column_letter(index: int) -> str:
    n = int(index) + 1
    letters = ""
    while n > 0:
        n, rem = divmod(n - 1, 26)
        letters = chr(65 + rem) + letters
    return letters or "A"


class FeishuSheets:
    def __init__(self, *, agent_id: str = "mark", messenger: FeishuMessenger | None = None) -> None:
        self.messenger = messenger or FeishuMessenger(agent_id)

    def _request(self, method: str, path: str, payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        token = self.messenger.tenant_token()
        url = f"https://open.feishu.cn/open-apis{path}"
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
            method=method.upper(),
        )
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                raw = response.read().decode("utf-8")
                body = json.loads(raw) if raw.strip() else {}
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Feishu Sheets HTTP {exc.code}: {detail}") from exc
        if int(body.get("code") or 0) != 0:
            raise RuntimeError(f"Feishu Sheets error: {body.get('msg') or body}")
        return body.get("data") if isinstance(body.get("data"), dict) else body

    def get_meta(self, spreadsheet_token: str) -> dict[str, Any]:
        token = parse_spreadsheet_token(spreadsheet_token)
        data = self._request("GET", f"/sheets/v2/spreadsheets/{token}/metainfo")
        return data if isinstance(data, dict) else {}

    def list_sheets(self, spreadsheet_token: str) -> list[dict[str, Any]]:
        meta = self.get_meta(spreadsheet_token)
        sheets = meta.get("sheets") if isinstance(meta.get("sheets"), list) else []
        return [s for s in sheets if isinstance(s, dict)]

    def resolve_sheet(self, spreadsheet_token: str, sheet_name: str = "Sheet1") -> dict[str, Any]:
        wanted = str(sheet_name or "Sheet1").strip() or "Sheet1"
        sheets = self.list_sheets(spreadsheet_token)
        for sheet in sheets:
            title = str(sheet.get("title") or sheet.get("name") or "").strip()
            if title == wanted:
                return sheet
        if sheets:
            return sheets[0]
        raise RuntimeError(f"No worksheet found in spreadsheet for tab {wanted!r}")

    def get_sheet_row_count(self, spreadsheet_token: str, *, sheet_id: str) -> int:
        sid = str(sheet_id or "").strip()
        if not sid:
            raise ValueError("sheet_id required")
        sheet = next(
            (
                item
                for item in self.list_sheets(spreadsheet_token)
                if str(item.get("sheetId") or item.get("sheet_id") or "").strip() == sid
            ),
            None,
        )
        if sheet is None:
            raise RuntimeError(f"Feishu Sheet metadata failed: worksheet {sid!r} not found")
        grid = sheet.get("gridProperties") if isinstance(sheet.get("gridProperties"), dict) else {}
        for source in (sheet, grid):
            for key in ("rowCount", "row_count"):
                try:
                    rows = int(source.get(key) or 0)
                except (TypeError, ValueError):
                    rows = 0
                if rows > 0:
                    return rows
        raise RuntimeError(f"Feishu Sheet metadata failed: row count missing for worksheet {sid!r}")

    def add_sheet(self, spreadsheet_token: str, title: str, *, index: int | None = None) -> dict[str, Any]:
        token = parse_spreadsheet_token(spreadsheet_token)
        props: dict[str, Any] = {"title": str(title or "Sheet").strip() or "Sheet"}
        if index is not None:
            props["index"] = int(index)
        data = self._request(
            "POST",
            f"/sheets/v2/spreadsheets/{token}/sheets_batch_update",
            {"requests": [{"addSheet": {"properties": props}}]},
        )
        replies = data.get("replies") if isinstance(data, dict) else []
        if isinstance(replies, list):
            for reply in replies:
                if not isinstance(reply, dict):
                    continue
                added = reply.get("addSheet") if isinstance(reply.get("addSheet"), dict) else {}
                properties = added.get("properties") if isinstance(added.get("properties"), dict) else added
                if isinstance(properties, dict) and (properties.get("sheetId") or properties.get("sheet_id")):
                    return properties
        return data if isinstance(data, dict) else {}

    def ensure_sheet(self, spreadsheet_token: str, sheet_name: str) -> dict[str, Any]:
        wanted = str(sheet_name or "").strip()
        if not wanted:
            raise ValueError("sheet_name required")
        for sheet in self.list_sheets(spreadsheet_token):
            title = str(sheet.get("title") or sheet.get("name") or "").strip()
            if title == wanted:
                return sheet
        created = self.add_sheet(spreadsheet_token, wanted)
        sheet_id = str(created.get("sheetId") or created.get("sheet_id") or "").strip()
        if sheet_id:
            return {"sheetId": sheet_id, "title": wanted, **created}
        for sheet in self.list_sheets(spreadsheet_token):
            title = str(sheet.get("title") or sheet.get("name") or "").strip()
            if title == wanted:
                return sheet
        raise RuntimeError(f"failed to create worksheet {wanted!r}")

    def delete_sheet(self, spreadsheet_token: str, sheet_id: str) -> dict[str, Any]:
        token = parse_spreadsheet_token(spreadsheet_token)
        sid = str(sheet_id or "").strip()
        if not sid:
            raise ValueError("sheet_id required")
        return self._request(
            "POST",
            f"/sheets/v2/spreadsheets/{token}/sheets_batch_update",
            {"requests": [{"deleteSheet": {"sheetId": sid}}]},
        )

    def set_dropdown(
        self,
        spreadsheet_token: str,
        *,
        sheet_id: str,
        range_a1: str,
        options: list[str],
        colors: list[str] | None = None,
    ) -> dict[str, Any]:
        token = parse_spreadsheet_token(spreadsheet_token)
        sid = str(sheet_id or "").strip()
        values = [str(item).strip() for item in options if str(item).strip()]
        if not sid or not values:
            return {}
        target = range_a1 if "!" in range_a1 else f"{sid}!{range_a1}"
        palette = list(colors) if colors else ["#34C759", "#FF3B30", "#8E8E93"]
        return self._request(
            "POST",
            f"/sheets/v2/spreadsheets/{token}/dataValidation",
            {
                "range": target,
                "dataValidationType": "list",
                "dataValidation": {
                    "conditionValues": values,
                    "options": {
                        "multipleValues": False,
                        "highlightValidData": True,
                        "colors": palette[: len(values)],
                    },
                },
            },
        )

    def get_dropdown(
        self,
        spreadsheet_token: str,
        *,
        sheet_id: str,
        range_a1: str,
    ) -> list[dict[str, Any]]:
        token = parse_spreadsheet_token(spreadsheet_token)
        sid = str(sheet_id or "").strip()
        if not sid or not range_a1:
            return []
        target = range_a1 if "!" in range_a1 else f"{sid}!{range_a1}"
        query = urllib.parse.urlencode({"dataValidationType": "list", "range": target})
        data = self._request(
            "GET",
            f"/sheets/v2/spreadsheets/{token}/dataValidation?{query}",
        )
        validations = data.get("dataValidations") if isinstance(data, dict) else []
        return [item for item in validations if isinstance(item, dict)]

    def set_range_style(
        self,
        spreadsheet_token: str,
        *,
        sheet_id: str,
        range_a1: str,
        bold: bool | None = None,
        v_align: int | None = None,
        back_color: str | None = None,
        fore_color: str | None = None,
        h_align: int | None = None,
        border_type: str | None = None,
        border_color: str | None = None,
        font_size: int | float | None = None,
    ) -> dict[str, Any]:
        token = parse_spreadsheet_token(spreadsheet_token)
        sid = str(sheet_id or "").strip()
        if not sid or not range_a1:
            return {}
        target = range_a1 if "!" in range_a1 else f"{sid}!{range_a1}"
        style: dict[str, Any] = {}
        font: dict[str, Any] = {}
        if bold is not None:
            font["bold"] = bool(bold)
        if font_size is not None:
            font["fontSize"] = font_size
        if font:
            style["font"] = font
        if v_align is not None:
            style["vAlign"] = int(v_align)
        if back_color:
            style["backColor"] = back_color
        if fore_color:
            style["foreColor"] = fore_color
        if h_align is not None:
            style["hAlign"] = int(h_align)
        if border_type:
            style["borderType"] = border_type
        if border_color:
            style["borderColor"] = border_color
        if not style:
            return {}
        return self._request(
            "PUT",
            f"/sheets/v2/spreadsheets/{token}/style",
            {"appendStyle": {"range": target, "style": style}},
        )

    def get_values(self, spreadsheet_token: str, range_a1: str) -> list[list[Any]]:
        token = parse_spreadsheet_token(spreadsheet_token)
        encoded = urllib.parse.quote(range_a1, safe="!:")
        data = self._request("GET", f"/sheets/v2/spreadsheets/{token}/values/{encoded}")
        value_range = data.get("valueRange") if isinstance(data, dict) else {}
        values = value_range.get("values") if isinstance(value_range, dict) else data.get("values")
        return values if isinstance(values, list) else []

    def append_values(
        self,
        spreadsheet_token: str,
        *,
        sheet_id: str,
        values: list[list[Any]],
        start_col: str = "A",
        end_col: str = "J",
    ) -> dict[str, Any]:
        token = parse_spreadsheet_token(spreadsheet_token)
        sid = str(sheet_id or "").strip()
        if not sid:
            raise ValueError("sheet_id required")
        if not values:
            return {}
        width = max(len(row) for row in values)
        end = end_col or column_letter(max(width - 1, 0))
        rows = max(len(values), 1)
        range_a1 = f"{sid}!{start_col}1:{end}{rows}"
        return self._request(
            "POST",
            f"/sheets/v2/spreadsheets/{token}/values_append?insertDataOption=INSERT_ROWS",
            {"valueRange": {"range": range_a1, "values": values}},
        )

    def format_sheet(
        self,
        spreadsheet_token: str,
        *,
        sheet_id: str,
        column_widths: list[tuple[int, int]] | None = None,
        freeze_rows: int = 1,
        bold_header: bool = False,
        header_end_col: str = "",
        body_row_height: int = 96,
        body_end_row: int | None = None,
    ) -> dict[str, Any]:
        token = parse_spreadsheet_token(spreadsheet_token)
        sid = str(sheet_id or "").strip()
        if not sid:
            return {}
        results: list[dict[str, Any]] = []
        for col_index, width in column_widths or []:
            results.append(
                self._request(
                    "PUT",
                    f"/sheets/v2/spreadsheets/{token}/dimension_range",
                    {
                        "dimension": {
                            "sheetId": sid,
                            "majorDimension": "COLUMNS",
                            # Feishu's dimension_range endpoint uses a
                            # 1-based column range and rejects startIndex=0.
                            "startIndex": int(col_index) + 1,
                            "endIndex": int(col_index) + 2,
                        },
                        "dimensionProperties": {"fixedSize": int(width)},
                    },
                )
            )
        if freeze_rows > 0:
            results.append(
                self._request(
                    "POST",
                    f"/sheets/v2/spreadsheets/{token}/sheets_batch_update",
                    {
                        "requests": [
                            {
                                "updateSheet": {
                                    "properties": {
                                        "sheetId": sid,
                                        "frozenRowCount": int(freeze_rows),
                                    }
                                }
                            }
                        ]
                    },
                )
            )
        body_end = int(body_end_row or 0)
        if body_row_height > 0 and body_end > int(freeze_rows):
            results.append(
                self._request(
                    "PUT",
                    f"/sheets/v2/spreadsheets/{token}/dimension_range",
                    {
                        "dimension": {
                            "sheetId": sid,
                            "majorDimension": "ROWS",
                            "startIndex": int(freeze_rows),
                            "endIndex": body_end,
                        },
                        "dimensionProperties": {"fixedSize": int(body_row_height)},
                    },
                )
            )
        if bold_header:
            end = str(header_end_col or "").strip() or "A"
            results.append(self.set_range_style(
                spreadsheet_token,
                sheet_id=sid,
                range_a1=f"A1:{end}1",
                bold=True,
                v_align=1,
                back_color="#E8F1FB",
                fore_color="#1F2937",
                border_type="FULL_BORDER",
                border_color="#B8C7D9",
                font_size=11,
            ))
            if body_end > int(freeze_rows):
                results.append(self.set_range_style(
                    spreadsheet_token,
                    sheet_id=sid,
                    range_a1=f"A2:{end}{body_end}",
                    v_align=0,
                    border_type="FULL_BORDER",
                    border_color="#E5E7EB",
                    font_size=10,
                ))
        return {"operations": len(results)}

    def verify_sheet_format(
        self,
        spreadsheet_token: str,
        *,
        sheet_id: str,
        freeze_rows: int = 0,
        validation_range: str = "",
        validation_options: list[str] | None = None,
    ) -> dict[str, Any]:
        sid = str(sheet_id or "").strip()
        if not sid:
            raise ValueError("sheet_id required")
        sheet = next(
            (
                item
                for item in self.list_sheets(spreadsheet_token)
                if str(item.get("sheetId") or item.get("sheet_id") or "").strip() == sid
            ),
            None,
        )
        if sheet is None:
            raise RuntimeError(f"Feishu Sheet read-back failed: worksheet {sid!r} not found")
        actual_freeze = int(sheet.get("frozenRowCount") or sheet.get("frozen_row_count") or 0)
        if actual_freeze != int(freeze_rows):
            raise RuntimeError(
                f"Feishu Sheet read-back mismatch: expected {freeze_rows} frozen rows, got {actual_freeze}"
            )
        validations: list[dict[str, Any]] = []
        expected = [str(item) for item in (validation_options or [])]
        if validation_range and expected:
            validations = self.get_dropdown(
                spreadsheet_token,
                sheet_id=sid,
                range_a1=validation_range,
            )
            found = False
            for validation in validations:
                values = validation.get("conditionValues")
                if not isinstance(values, list):
                    nested = validation.get("dataValidation")
                    values = nested.get("conditionValues") if isinstance(nested, dict) else []
                if [str(item) for item in values] == expected:
                    found = True
                    break
            if not found:
                raise RuntimeError(
                    f"Feishu Sheet read-back mismatch: dropdown options not found for {validation_range}"
                )
        return {"sheet": sheet, "data_validations": validations}
