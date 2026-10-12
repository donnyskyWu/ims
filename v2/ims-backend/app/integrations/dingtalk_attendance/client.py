"""钉钉考勤适配器。与 IMS 钉钉应用配置隔离。日志不记录 AppSecret。"""
from __future__ import annotations

from app.core.config import get_settings
from app.integrations.runtime import ADAPTERS

client = ADAPTERS["dingtalk_attendance"]
ADAPTER_LOGS: list[dict] = []
SECRET_MASK = "******"


def _remember(action: str) -> None:
    settings = get_settings()
    block = settings.dingtalk_attendance or {}
    ADAPTER_LOGS.append(
        {
            "action": action,
            "appKey": block.get("app_key") or "",
            "appSecret": SECRET_MASK,
        }
    )


def list_leaves(user_ids, start_date, end_date):
    _remember("list_leaves")
    data = client.call("list_leaves", {"userIds": list(user_ids), "start": start_date, "end": end_date})
    if isinstance(data, list):
        return data
    return data.get("leaves") or []
