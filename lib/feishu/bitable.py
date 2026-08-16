from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Optional

from feishu.messenger import FeishuMessenger


class FeishuBitable:
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
            raise RuntimeError(f"Feishu Bitable HTTP {exc.code}: {detail}") from exc
        if int(body.get("code") or 0) != 0:
            raise RuntimeError(f"Feishu Bitable error: {body.get('msg') or body}")
        return body.get("data") if isinstance(body.get("data"), dict) else body

    def list_tables(self, app_token: str) -> list[dict[str, Any]]:
        data = self._request("GET", f"/bitable/v1/apps/{app_token}/tables")
        items = data.get("items") if isinstance(data, dict) else []
        return items if isinstance(items, list) else []

    def create_table(self, app_token: str, name: str) -> dict[str, Any]:
        data = self._request(
            "POST",
            f"/bitable/v1/apps/{app_token}/tables",
            {"table": {"name": name}},
        )
        table = data.get("table") if isinstance(data, dict) else None
        return table if isinstance(table, dict) else (data if isinstance(data, dict) else {})

    def list_fields(self, app_token: str, table_id: str) -> list[dict[str, Any]]:
        data = self._request("GET", f"/bitable/v1/apps/{app_token}/tables/{table_id}/fields")
        items = data.get("items") if isinstance(data, dict) else []
        return items if isinstance(items, list) else []

    def create_field(
        self,
        app_token: str,
        table_id: str,
        *,
        name: str,
        field_type: int = 1,
        property: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"field_name": name, "type": field_type}
        if property is not None:
            payload["property"] = property
        data = self._request(
            "POST",
            f"/bitable/v1/apps/{app_token}/tables/{table_id}/fields",
            payload,
        )
        field = data.get("field") if isinstance(data, dict) else None
        return field if isinstance(field, dict) else (data if isinstance(data, dict) else {})

    def update_field(
        self,
        app_token: str,
        table_id: str,
        field_id: str,
        *,
        name: str,
        field_type: int,
        property: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"field_name": name, "type": field_type}
        if property is not None:
            payload["property"] = property
        data = self._request(
            "PUT",
            f"/bitable/v1/apps/{app_token}/tables/{table_id}/fields/{field_id}",
            payload,
        )
        field = data.get("field") if isinstance(data, dict) else None
        return field if isinstance(field, dict) else (data if isinstance(data, dict) else {})

    def list_views(self, app_token: str, table_id: str) -> list[dict[str, Any]]:
        data = self._request("GET", f"/bitable/v1/apps/{app_token}/tables/{table_id}/views")
        items = data.get("items") if isinstance(data, dict) else []
        return items if isinstance(items, list) else []

    def create_view(self, app_token: str, table_id: str, *, name: str, view_type: str = "grid") -> dict[str, Any]:
        data = self._request(
            "POST",
            f"/bitable/v1/apps/{app_token}/tables/{table_id}/views",
            {"view_name": name, "view_type": view_type},
        )
        view = data.get("view") if isinstance(data, dict) else None
        return view if isinstance(view, dict) else (data if isinstance(data, dict) else {})

    def list_records(self, app_token: str, table_id: str, *, page_size: int = 100) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        page_token = ""
        while True:
            query = urllib.parse.urlencode(
                {
                    "page_size": str(page_size),
                    **({"page_token": page_token} if page_token else {}),
                }
            )
            data = self._request("GET", f"/bitable/v1/apps/{app_token}/tables/{table_id}/records?{query}")
            items = data.get("items") if isinstance(data, dict) else []
            if isinstance(items, list):
                records.extend(items)
            page_token = str(data.get("page_token") or "") if isinstance(data, dict) else ""
            if not page_token or not (isinstance(data, dict) and data.get("has_more")):
                break
        return records

    def create_record(self, app_token: str, table_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        data = self._request(
            "POST",
            f"/bitable/v1/apps/{app_token}/tables/{table_id}/records",
            {"fields": fields},
        )
        record = data.get("record") if isinstance(data, dict) else None
        return record if isinstance(record, dict) else (data if isinstance(data, dict) else {})

    def update_record(self, app_token: str, table_id: str, record_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        data = self._request(
            "PUT",
            f"/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}",
            {"fields": fields},
        )
        record = data.get("record") if isinstance(data, dict) else None
        return record if isinstance(record, dict) else (data if isinstance(data, dict) else {})
