"""GET /air/mcp/audit-log。数据源 ims_mcp_log，不读外部模型。"""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail
from app.corp import page_args, paged, tenant_of, user_names
from app.models import AirApiKey, AirMcpLog, User

router = APIRouter(prefix="/air/mcp", tags=["air-mcp-log"])


def iso(dt: datetime | None) -> str:
    if dt is None:
        return ""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def parse_day(value: str) -> datetime | None:
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d")
    except ValueError:
        return None


def auth_note(row: AirMcpLog) -> str:
    code = row.result_code or ""
    if code == "429":
        return "QPM 超限"
    if code == "403":
        return "未授权"
    if code == "401":
        return "认证失败"
    token = int(row.token_cnt or 0)
    hit = int(row.filter_hit or 0)
    if row.tool == "experts.assemble":
        return f"组装下发；Token {token}；过滤命中 {hit}（本期无检索，只计未发布技能）"
    return f"调用成功；Token {token}；过滤命中 {hit}"


@router.get("/audit-log")
def audit_log(
    keyword: str | None = None,
    tool: str | None = None,
    result: str | None = None,
    keyId: int | None = None,
    dateRange: str | None = None,
    pageNo: int = 1,
    pageSize: int = 20,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    start = end = None
    range_text = (dateRange or "").strip()
    if range_text:
        parts = [item.strip() for item in range_text.split(",") if item.strip()]
        if len(parts) != 2:
            return fail(1001, "dateRange 须为开始日,结束日")
        start = parse_day(parts[0])
        end = parse_day(parts[1])
        if start is None or end is None or end < start:
            return fail(1001, "dateRange 日期无效")
        end = end + timedelta(days=1)
    q = select(AirMcpLog).where(AirMcpLog.deleted == 0, AirMcpLog.tenant_id == tenant_id)
    if tool:
        q = q.where(AirMcpLog.tool == tool.strip())
    if keyId:
        q = q.where(AirMcpLog.key_id == keyId)
    wanted = (result or "").strip().upper()
    if wanted == "SUCCESS":
        q = q.where(AirMcpLog.result_code == "0")
    elif wanted == "FAIL":
        q = q.where(AirMcpLog.result_code != "0")
    elif wanted:
        return fail(1001, "result 仅支持 SUCCESS 或 FAIL")
    if start is not None and end is not None:
        q = q.where(AirMcpLog.created_at >= start, AirMcpLog.created_at < end)
    if (keyword or "").strip():
        kw = f"%{keyword.strip()}%"
        user_ids = select(User.id).where(
            User.deleted == 0,
            or_(User.username.like(kw), User.nickname.like(kw)),
        )
        q = q.where(or_(AirMcpLog.tool.like(kw), AirMcpLog.user_id.in_(user_ids)))
    page_no, size = page_args(pageNo, pageSize)
    stmt = q.order_by(AirMcpLog.created_at.desc(), AirMcpLog.id.desc())
    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = list(db.scalars(stmt.offset((page_no - 1) * size).limit(size)).all())
    names = user_names(db, [row.user_id for row in rows])
    key_ids = [row.key_id for row in rows if row.key_id]
    codes: dict[int, str] = {}
    if key_ids:
        for item in db.scalars(select(AirApiKey).where(AirApiKey.id.in_(key_ids))).all():
            codes[item.id] = item.key_code
    items = []
    for row in rows:
        code = row.result_code or ""
        items.append(
            {
                "id": row.id,
                "createdAt": iso(row.created_at),
                "tool": row.tool,
                "userId": row.user_id,
                "userName": names.get(row.user_id, ""),
                "keyId": row.key_id,
                "keyCode": codes.get(row.key_id, ""),
                "resultCode": "SUCCESS" if code == "0" else code,
                "costMs": int(row.cost_ms or 0),
                "tokenCnt": int(row.token_cnt or 0),
                "filterHit": int(row.filter_hit or 0),
                "authNote": auth_note(row),
                "paramDigest": row.param_digest,
            }
        )
    return paged(items, total, page_no, size)
