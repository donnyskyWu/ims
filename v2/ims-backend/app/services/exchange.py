"""示例域导入与异步导出。导出沿用列表的数据范围和脱敏。"""
from __future__ import annotations

import base64
from io import BytesIO

from openpyxl import Workbook
from sqlalchemy import select

from app.core.context import get_ctx
from app.core.error_codes import get_entry
from app.core.errors import BizError
from app.core.fault import faults
from app.core.pagination import Page
from app.db.repository import Repository
from app.db.session import get_session
from app.domains.demo.model import DemoOrder
from app.domains.demo.service import _mask_id, page_orders
from app.domains.master.model import Realname
from app.domains.system.model import ExportTask


def _import_error(excel_row: int, column: str, code: int) -> dict:
    entry = get_entry(code)
    return {"row": excel_row, "column": column, "message": entry.msg if entry else "导入失败", "code": code}


def import_orders(rows: list[dict], mode: str = "ALL_OR_NOTHING") -> dict:
    if len(rows) > 5000:
        raise BizError(1001, "超过 5000 行，请拆分后再导入")
    errors = []
    ready = []
    session = get_session()
    for index, row in enumerate(rows):
        excel_row = index + 2
        status = row.get("status") or "ACTIVE"
        if status not in {"ACTIVE", "CLOSED"}:
            errors.append(_import_error(excel_row, "status", 1503))
            continue
        realname_id = row.get("realnameId")
        if realname_id not in (None, ""):
            found = session.get(Realname, int(realname_id))
            if found is None or found.deleted:
                errors.append(_import_error(excel_row, "realnameId", 1500))
                continue
        ready.append((excel_row, row, status, realname_id))
    if mode != "PARTIAL" and errors:
        return {"successCount": 0, "errors": errors}
    created = 0
    for _excel_row, row, status, realname_id in ready:
        item = DemoOrder(
            name=row.get("name") or "",
            code=row.get("code"),
            status=status,
            dept_id=int(row["deptId"]) if row.get("deptId") else None,
            realname_id=int(realname_id) if realname_id not in (None, "") else None,
        )
        Repository(DemoOrder).create(item)
        created += 1
    return {"successCount": created, "errors": errors}


_EXPORT_BODIES: dict[int, str | dict] = {}


def start_export(query: dict | None = None) -> dict:
    ctx = get_ctx()
    task = ExportTask(status="PENDING", progress=0, biz_type="demo_order", query_json=query or {}, creator=ctx.user_id if ctx else 0)
    get_session().add(task)
    get_session().flush()
    return {"id": task.id, "status": task.status}


def run_export(task_id: int) -> dict:
    task = get_session().get(ExportTask, task_id)
    if task is None:
        raise BizError(1504)
    task.status = "RUNNING"
    try:
        faults.raise_if("export.fail")
        data = page_orders(Page(1, 100))
        lines = ["name,idCard,mobile"]
        for item in data["list"]:
            lines.append(f"{item.get('name')},{item.get('idCard') or ''},{item.get('mobile') or ''}")
        text_body = "\n".join(lines)
        task.file_key = f"EXPORT/demo/{task.id}.csv"
        task.status = "SUCCESS"
        task.progress = 100
        task.error = None
        _EXPORT_BODIES[int(task.id)] = text_body
        get_session().info[f"export:{task.id}"] = text_body
    except Exception as exc:
        task.status = "FAILED"
        task.error = "导出失败，请稍后重试" if not isinstance(exc, BizError) else exc.msg
        if not isinstance(exc, BizError):
            task.error = str(exc) if str(exc) else "导出失败，请稍后重试"
        get_session().flush()
        return {"id": task.id, "status": task.status, "error": task.error}
    get_session().flush()
    return {"id": task.id, "status": task.status, "fileKey": task.file_key}


def remember_export(filename: str, header: list, rows: list, biz_type: str) -> dict:
    """把表格记成已完成的导出任务。演示导出仍返回文本，本函数返回表格文件。"""
    ctx = get_ctx()
    book = Workbook()
    sheet = book.active
    sheet.append(header)
    for row in rows:
        sheet.append(["" if item is None else item for item in row])
    buffer = BytesIO()
    book.save(buffer)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    task = ExportTask(
        status="SUCCESS",
        progress=100,
        biz_type=biz_type,
        query_json={},
        creator=ctx.user_id if ctx else 0,
        file_key=f"EXPORT/{biz_type}/{filename}",
    )
    get_session().add(task)
    get_session().flush()
    payload = {
        "encoding": "base64",
        "filename": filename,
        "contentType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "content": encoded,
    }
    _EXPORT_BODIES[int(task.id)] = payload
    get_session().info[f"export:{task.id}"] = payload
    return {"id": task.id, "status": task.status, "fileKey": task.file_key}


def remember_binary(filename: str, content: bytes, content_type: str, biz_type: str, expires_seconds: int | None = None) -> dict:
    """把二进制文件记成导出任务。设置过期秒数后，过期下载返回 1001。"""
    from datetime import timedelta

    from app.core.clock import now_naive

    ctx = get_ctx()
    query = {}
    if expires_seconds:
        query["expiresAt"] = (now_naive() + timedelta(seconds=int(expires_seconds))).isoformat(sep=" ")
    task = ExportTask(
        status="SUCCESS",
        progress=100,
        biz_type=biz_type,
        query_json=query,
        creator=ctx.user_id if ctx else 0,
        file_key=f"EXPORT/{biz_type}/{filename}",
    )
    get_session().add(task)
    get_session().flush()
    payload = {
        "encoding": "base64",
        "filename": filename,
        "contentType": content_type,
        "content": base64.b64encode(content).decode("ascii"),
    }
    _EXPORT_BODIES[int(task.id)] = payload
    get_session().info[f"export:{task.id}"] = payload
    return {"id": task.id, "status": task.status, "fileKey": task.file_key}


def export_body(task_id: int):
    from app.core.clock import now_naive

    task = _own_task(task_id)
    expires = (task.query_json or {}).get("expiresAt")
    if expires and str(expires) < now_naive().isoformat(sep=" "):
        raise BizError(1001, "链接已过期，请重新导出")
    if task.status != "SUCCESS":
        raise BizError(1001, "导出尚未完成")
    cached = _EXPORT_BODIES.get(int(task.id))
    if cached is not None:
        return cached
    return get_session().info.get(f"export:{task.id}") or ""


def _own_task(task_id: int) -> ExportTask:
    ctx = get_ctx()
    task = get_session().get(ExportTask, task_id)
    if task is None or (ctx and task.creator not in (None, ctx.user_id)):
        raise BizError(1504)
    return task


def my_exports() -> dict:
    ctx = get_ctx()
    rows = list(get_session().scalars(select(ExportTask).where(ExportTask.creator == (ctx.user_id if ctx else -1))))
    return {
        "list": [{"id": row.id, "status": row.status, "error": row.error, "fileKey": row.file_key, "progress": row.progress} for row in rows],
        "total": len(rows),
    }


def masked_sample(value: str) -> str:
    return _mask_id(value) or ""
