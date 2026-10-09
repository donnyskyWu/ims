"""账号池尾巴：池状态、已归还回收回池、交接凭证导出。

不经过离职归还单（/account/return/generate、1024）。
回收只处理 RETURNED → IN_POOL。冻结账号仍走解冻。
"""

from __future__ import annotations

import os
import secrets
import time
from datetime import datetime
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.account import check_platform, router as account_router
from app.acct_flow import _append_timeline, _is_admin, _load_account, router as flow_router
from app.api import current_user, db_session, fail, ok
from app.core import utcnow
from app.corp import count_of, page_args, paged, tenant_of
from app.models import AccountTimelineEvent, User
from app.ops_db import ops_session
from app.ops_models import PlatformAccount

router = APIRouter()

POOL_STATUSES = ("IN_POOL", "IN_USE", "FROZEN", "RETURNED", "CANCELLED")
STATUS_LABEL = {
    "IN_POOL": "池可领用",
    "IN_USE": "在用",
    "FROZEN": "冻结",
    "RETURNED": "已归还",
    "CANCELLED": "已注销",
}
EVENT_LABEL = {
    "REGISTER": "登记",
    "APPLY": "领用",
    "TRANSFER": "流转",
    "RETURN": "归还",
    "RECHARGE": "冲话费",
    "FREEZE": "冻结",
    "UNFREEZE": "解冻",
    "CANCEL": "注销",
    "RECYCLE": "回收回池",
}
EXPORT_TTL_SEC = 600
PDF_MEDIA = "application/pdf"
FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
)
# token -> (expires_at, body, filename, user_id)
_EXPORTS: dict[str, tuple[float, bytes, str, int]] = {}


class RecycleBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    remark: str


def file_root() -> Path:
    configured = (os.environ.get("IMS_FILE_ROOT") or "").strip()
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[1] / "data" / "ims-files"


def parse_dt(value: str) -> datetime | None:
    text = (value or "").strip().replace("T", " ")
    if not text:
        return None
    try:
        if len(text) <= 10:
            return datetime.strptime(text[:10], "%Y-%m-%d")
        return datetime.strptime(text[:19], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def iso(value: datetime | None) -> str:
    if value is None:
        return ""
    return value.strftime("%Y-%m-%dT%H:%M:%S")


def purge_exports(now: float) -> None:
    dead = [key for key, item in _EXPORTS.items() if item[0] < now]
    for key in dead:
        _EXPORTS.pop(key, None)


def register_cjk() -> str:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    if "IMS-CJK" in pdfmetrics.getRegisteredFontNames():
        return "IMS-CJK"
    for path in FONT_CANDIDATES:
        if not os.path.isfile(path):
            continue
        pdfmetrics.registerFont(TTFont("IMS-CJK", path, subfontIndex=0))
        return "IMS-CJK"
    raise FileNotFoundError("cjk font")


def build_pdf(lines: list[str]) -> bytes:
    from reportlab.pdfgen import canvas

    font = register_cjk()
    buf = BytesIO()
    pdf = canvas.Canvas(buf, pagesize=(595, 842))
    pdf.setTitle("账号交接凭证")
    y = 800
    pdf.setFont(font, 11)
    for line in lines:
        if y < 48:
            pdf.showPage()
            pdf.setFont(font, 11)
            y = 800
        pdf.drawString(40, y, line[:42])
        y -= 18
    pdf.save()
    return buf.getvalue()


def event_vo(row: AccountTimelineEvent, names: dict[int, str]) -> dict:
    return {
        "id": row.id,
        "accountId": row.account_id,
        "eventType": row.event_type,
        "eventLabel": EVENT_LABEL.get(row.event_type, row.event_type),
        "refNo": row.ref_no,
        "refId": row.ref_id,
        "operatorUserId": row.operator_user_id,
        "operatorName": names.get(row.operator_user_id, ""),
        "snapshotSummary": row.snapshot_summary,
        "remark": row.remark,
        "eventTime": iso(row.event_time),
    }


@account_router.get("/corp/account/status/summary")
def pool_status(
    platformType: str = "",
    actor: User = Depends(current_user),
):
    """当前平台账号池各状态数量。"""
    error = check_platform(platformType)
    if error:
        return error
    counts = {code: 0 for code in POOL_STATUSES}
    ops = ops_session()
    try:
        rows = ops.execute(
            select(PlatformAccount.status, func.count())
            .where(
                PlatformAccount.deleted == 0,
                PlatformAccount.tenant_id == tenant_of(actor),
                PlatformAccount.platform_type == platformType,
            )
            .group_by(PlatformAccount.status)
        ).all()
    finally:
        ops.close()
    for status, count in rows:
        if status in counts:
            counts[status] = int(count)
    return ok(
        {
            "platform": platformType,
            "counts": counts,
            "total": sum(counts.values()),
        }
    )


@flow_router.post("/account/{account_id}/recycle")
def recycle_account(
    account_id: int,
    body: RecycleBody,
    actor: User = Depends(current_user),
    db: Session = Depends(db_session),
):
    """已归还账号回收回可领用池。冻结账号不在这里处理。"""
    remark = (body.remark or "").strip()
    if not remark:
        return fail(1001, "回收说明必填")
    if len(remark) > 512:
        return fail(1001, "回收说明不超过 512 字")
    if not _is_admin(db, actor):
        return fail(1008, "仅管理员可回收回池")
    ops = ops_session()
    try:
        account = _load_account(ops, account_id)
        if account is None or (account.tenant_id or 0) != tenant_of(actor):
            return fail(1504, "资源不可用")
        if account.status == "FROZEN":
            return fail(1023, "冻结账号请走解冻，不能回收")
        if account.status != "RETURNED":
            return fail(1023, "仅已归还账号可回收回池")
        now = utcnow()
        account.status = "IN_POOL"
        account.holder_user_id = None
        account.updated_at = now
        ops.commit()
        _append_timeline(
            db,
            account_id=account.id,
            event_type="RECYCLE",
            ref_no=f"RY{account.id}",
            ref_id=account.id,
            operator=actor,
            summary=f"回收回池 · 状态 IN_POOL · {remark}",
            tenant_id=tenant_of(actor),
        )
        return ok(
            {
                "accountId": account.id,
                "accountNo": account.account_no,
                "status": "IN_POOL",
                "message": "已回收回池",
            }
        )
    finally:
        ops.close()


@flow_router.get("/account/timeline/events")
def timeline_events(
    pageNo: int = 1,
    pageSize: int = 10,
    accountId: int = 0,
    eventType: str = "",
    operatorUserId: int = 0,
    timeRange: list[str] = Query(default=[]),
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    """跨账号时间线。供账号页「最近池动态」。"""
    page_no, size = page_args(pageNo, pageSize)
    stmt = select(AccountTimelineEvent).where(AccountTimelineEvent.tenant_id == tenant_of(actor))
    if accountId:
        stmt = stmt.where(AccountTimelineEvent.account_id == accountId)
    event_type = (eventType or "").strip().upper()
    if event_type:
        if event_type not in EVENT_LABEL:
            return fail(1001, "事件类型不合法")
        stmt = stmt.where(AccountTimelineEvent.event_type == event_type)
    if operatorUserId:
        stmt = stmt.where(AccountTimelineEvent.operator_user_id == operatorUserId)
    if timeRange:
        if len(timeRange) < 2 or not timeRange[0] or not timeRange[1]:
            return fail(1001, "时间范围不合法")
        start = parse_dt(timeRange[0])
        end = parse_dt(timeRange[1])
        if start is None or end is None:
            return fail(1001, "时间范围不合法")
        stmt = stmt.where(AccountTimelineEvent.event_time >= start, AccountTimelineEvent.event_time <= end)
    total = count_of(db, stmt)
    rows = db.scalars(stmt.order_by(AccountTimelineEvent.id.desc()).offset((page_no - 1) * size).limit(size)).all()
    ids = {row.operator_user_id for row in rows if row.operator_user_id}
    names: dict[int, str] = {}
    if ids:
        for user in db.scalars(select(User).where(User.id.in_(ids))).all():
            names[user.id] = user.nickname or user.username
    return paged([event_vo(row, names) for row in rows], total, page_no, size)


def _prefer_static(target, path: str, method: str) -> None:
    """静态路径要排在 /timeline/{account_id} 前面，否则 events 会被当成账号 id 并 422。"""
    for index, route in enumerate(list(target.routes)):
        if getattr(route, "path", None) == path and method in (getattr(route, "methods", None) or set()):
            target.routes.insert(0, target.routes.pop(index))
            return


_prefer_static(flow_router, "/account/timeline/events", "GET")


def voucher_lines(account: PlatformAccount, events: list[AccountTimelineEvent]) -> list[str]:
    status = STATUS_LABEL.get(account.status, account.status)
    lines = [
        "账号交接凭证",
        f"账号 {account.account_no} · {account.account_name or ''} · {status}",
    ]
    if not events:
        lines.append("暂无领用事件")
        return lines
    for row in events:
        label = EVENT_LABEL.get(row.event_type, row.event_type)
        when = iso(row.event_time)
        lines.append(f"{when} {label} {row.snapshot_summary or ''}".strip())
    return lines


@flow_router.get("/account/timeline/{account_id}/export")
def export_timeline(
    account_id: int,
    actor: User = Depends(current_user),
    db: Session = Depends(db_session),
):
    """导出交接凭证 PDF。失败 5005。"""
    ops = ops_session()
    try:
        account = _load_account(ops, account_id)
        if account is None or (account.tenant_id or 0) != tenant_of(actor):
            return fail(1504, "资源不可用")
        events = db.scalars(
            select(AccountTimelineEvent)
            .where(
                AccountTimelineEvent.account_id == account.id,
                AccountTimelineEvent.tenant_id == tenant_of(actor),
            )
            .order_by(AccountTimelineEvent.id.desc())
        ).all()
        try:
            body = build_pdf(voucher_lines(account, list(events)))
            folder = file_root() / "account" / datetime.now().strftime("%Y%m")
            folder.mkdir(parents=True, exist_ok=True)
        except (OSError, FileNotFoundError):
            return fail(5005, "交接凭证生成失败，请稍后重试")
        now = time.time()
        purge_exports(now)
        token = secrets.token_urlsafe(24)
        filename = f"handover_{account.account_no or account.id}.pdf"
        path = folder / f"{token}.pdf"
        try:
            path.write_bytes(body)
        except OSError:
            return fail(5005, "交接凭证生成失败，请稍后重试")
        _EXPORTS[token] = (now + EXPORT_TTL_SEC, body, filename, actor.id)
        return ok(
            {
                "exportTaskId": token,
                "message": "交接凭证已生成",
                "downloadUrl": f"/admin-api/ims/account/timeline/{account.id}/export/file?token={token}",
                "fileName": filename,
                "expiresIn": EXPORT_TTL_SEC,
            }
        )
    finally:
        ops.close()


@flow_router.get("/account/timeline/{account_id}/export/file")
def export_timeline_file(
    account_id: int,
    token: str,
    actor: User = Depends(current_user),
):
    now = time.time()
    purge_exports(now)
    item = _EXPORTS.get((token or "").strip())
    if item is None or item[0] < now:
        return fail(1002, "下载链接已过期")
    if item[3] != actor.id:
        return fail(1008, "无数据权限")
    _expires, body, filename, _user_id = item
    del account_id
    return Response(
        content=body,
        media_type=PDF_MEDIA,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

