"""GET /air/mcp/audit-log。数据源 ims_mcp_log，不读外部模型。"""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.core import utcnow
from app.corp import page_args, paged, tenant_of, user_names
from app.models import AirApiKey, AirMcpLog, User, UserDept, UserMapping

router = APIRouter(prefix="/air/mcp", tags=["air-mcp-log"])
usage_router = APIRouter(prefix="/air/usage", tags=["air-usage"])

RETAIN_DAYS = 180
USAGE_TOOLS = ("skills.list", "skills.get", "experts.list", "experts.assemble")


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


def parse_usage_range(date_range: str | None, today: datetime) -> tuple[datetime, datetime] | object:
    """近 7 天，或调用方给出的闭区间。超 180 天、早于保留窗都拒绝。"""
    end_day = today.date()
    start_day = end_day - timedelta(days=6)
    text = (date_range or "").strip()
    if text:
        parts = [item.strip() for item in text.split(",") if item.strip()]
        if len(parts) != 2:
            return fail(1001, "dateRange 须为开始日,结束日")
        start = parse_day(parts[0])
        end = parse_day(parts[1])
        if start is None or end is None or end.date() < start.date():
            return fail(1001, "dateRange 日期无效")
        start_day = start.date()
        end_day = end.date()
    if (end_day - start_day).days + 1 > RETAIN_DAYS:
        return fail(1001, "统计区间不能超过 180 天")
    earliest = today.date() - timedelta(days=RETAIN_DAYS - 1)
    if start_day < earliest:
        return fail(1001, "审计日志仅保留 180 天，更早记录已清理")
    return (
        datetime(start_day.year, start_day.month, start_day.day),
        datetime(end_day.year, end_day.month, end_day.day) + timedelta(days=1),
    )


def dept_labels(db: Session, user_ids: list[int], tenant_id: int) -> dict[int, str]:
    labels: dict[int, str] = {}
    if not user_ids:
        return labels
    rows = db.execute(
        select(UserDept.user_id, UserDept.dept_id).where(
            UserDept.user_id.in_(user_ids),
            UserDept.tenant_id == tenant_id,
        )
    ).all()
    for user_id, dept_id in rows:
        labels.setdefault(int(user_id), f"部门#{int(dept_id)}")
    missing = [item for item in user_ids if item not in labels]
    if not missing:
        return labels
    mappings = db.scalars(
        select(UserMapping).where(
            UserMapping.user_id.in_(missing),
            UserMapping.deleted == 0,
            UserMapping.tenant_id == tenant_id,
        )
    ).all()
    for mapping in mappings:
        if mapping.user_id in labels:
            continue
        for item in mapping.dept_ids or []:
            if str(item).isdigit() and int(item) > 0:
                labels[int(mapping.user_id)] = f"部门#{int(item)}"
                break
    return labels


def usage_rows(db: Session, tenant_id: int, start: datetime, end: datetime) -> list[AirMcpLog]:
    return list(
        db.scalars(
            select(AirMcpLog).where(
                AirMcpLog.deleted == 0,
                AirMcpLog.tenant_id == tenant_id,
                AirMcpLog.created_at >= start,
                AirMcpLog.created_at < end,
            )
        ).all()
    )


def stat_by_day(rows: list[AirMcpLog], start: datetime, end: datetime) -> list[dict]:
    buckets: dict[str, dict] = {}
    cursor = start
    while cursor < end:
        key = cursor.strftime("%Y-%m-%d")
        buckets[key] = {"statDate": key, "callCnt": 0, "tokenCnt": 0}
        cursor += timedelta(days=1)
    for row in rows:
        if row.created_at is None:
            continue
        key = row.created_at.strftime("%Y-%m-%d")
        bucket = buckets.get(key)
        if bucket is None:
            continue
        bucket["callCnt"] += 1
        bucket["tokenCnt"] += int(row.token_cnt or 0)
    return list(buckets.values())


def stat_by_person(db: Session, rows: list[AirMcpLog], tenant_id: int) -> list[dict]:
    buckets: dict[int, dict] = {}
    for row in rows:
        user_id = int(row.user_id or 0)
        bucket = buckets.get(user_id)
        if bucket is None:
            bucket = {"userId": user_id, "callCnt": 0, "tokenCnt": 0}
            buckets[user_id] = bucket
        bucket["callCnt"] += 1
        bucket["tokenCnt"] += int(row.token_cnt or 0)
    names = user_names(db, set(buckets))
    labels = dept_labels(db, list(buckets), tenant_id)
    items = []
    for user_id, bucket in buckets.items():
        items.append(
            {
                "userId": user_id,
                "userName": names.get(user_id, ""),
                "deptName": labels.get(user_id, "未分配"),
                "callCnt": bucket["callCnt"],
                "tokenCnt": bucket["tokenCnt"],
            }
        )
    items.sort(key=lambda item: (-item["callCnt"], item["userId"]))
    return items


def stat_by_tool(rows: list[AirMcpLog]) -> list[dict]:
    buckets = {
        tool: {"tool": tool, "callCnt": 0, "failCnt": 0, "costSum": 0}
        for tool in USAGE_TOOLS
    }
    for row in rows:
        bucket = buckets.get(row.tool or "")
        if bucket is None:
            continue
        bucket["callCnt"] += 1
        if (row.result_code or "") != "0":
            bucket["failCnt"] += 1
        bucket["costSum"] += int(row.cost_ms or 0)
    items = []
    for tool in USAGE_TOOLS:
        bucket = buckets[tool]
        count = bucket["callCnt"]
        avg = int(round(bucket["costSum"] / count)) if count else 0
        items.append(
            {
                "tool": tool,
                "callCnt": count,
                "failCnt": bucket["failCnt"],
                "avgCostMs": avg,
            }
        )
    return items


@usage_router.get("/stat")
def usage_stat(
    by: str | None = None,
    dateRange: str | None = None,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    """GET /air/usage/stat。近 7 日用量从 ims_mcp_log 本地汇总，不读外部模型。"""
    kind = (by or "DAY").strip().upper()
    if kind not in {"DAY", "PERSON", "TOOL"}:
        return fail(1001, "by 仅支持 DAY、PERSON 或 TOOL")
    window = parse_usage_range(dateRange, utcnow())
    if not isinstance(window, tuple):
        return window
    start, end = window
    tenant_id = tenant_of(actor)
    rows = usage_rows(db, tenant_id, start, end)
    if kind == "PERSON":
        return ok(stat_by_person(db, rows, tenant_id))
    if kind == "TOOL":
        return ok(stat_by_tool(rows))
    return ok(stat_by_day(rows, start, end))
