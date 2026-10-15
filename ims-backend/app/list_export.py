"""按当前筛选导出 CSV。下载路径挂在各资源自己的前缀下，沿用既有数据范围。"""

from __future__ import annotations

import csv
import secrets
import time
from io import StringIO

from fastapi.responses import Response

from app.api import fail
from app.models import User

EXPORT_TTL_SEC = 300
_FILES: dict[str, tuple[float, bytes, str, int]] = {}


def csv_bytes(rows: list[list[str]]) -> bytes:
    buf = StringIO()
    csv.writer(buf).writerows(rows)
    return buf.getvalue().encode("utf-8-sig")


def issue_list_csv(actor_id: int, filename: str, rows: list[list[str]], download_path: str) -> dict:
    now = time.time()
    dead = [key for key, item in _FILES.items() if item[0] < now]
    for key in dead:
        _FILES.pop(key, None)
    token = secrets.token_urlsafe(18)
    _FILES[token] = (now + EXPORT_TTL_SEC, csv_bytes(rows), filename, actor_id)
    return {
        "message": "导出已生成",
        "fileName": filename,
        "downloadUrl": f"{download_path}?token={token}",
    }


def take_csv(token: str, actor: User):
    now = time.time()
    item = _FILES.get(token)
    if item is None or item[0] < now:
        return fail(1002, "下载链接已过期")
    if item[3] != actor.id:
        return fail(1008, "无数据权限")
    _expires, body, filename, _user_id = item
    return Response(
        content=body,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
