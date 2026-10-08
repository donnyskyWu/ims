"""运营看板 HOME-001。已登录即可；聚合 IMS 内 KPI/待办，不请求 OPS/Football。"""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.core import utcnow
from app.corp import ops_db, page_args, paged, tenant_of, visible
from app.models import ContentReview, Todo, User
from app.ops_models import CollectLog, IpGroup, PlatformAccount
from app.scope import resolve

router = APIRouter(prefix="/home", tags=["home"])

SHORTCUT_CATALOG = [
    ("contentWork", "登记工作任务", "/ims/content/work-task"),
    ("ipg", "IP 组", "/ims/ip-group"),
    ("caDouyin", "账号领用", "/ims/corp/account/douyin"),
    ("collectTask", "采集任务", "/ims/collect/task"),
    ("cost", "账号 ROI", "/ims/cost"),
    ("contentReview", "内容审核", "/ims/content/review"),
]


def parse_date(value: str) -> datetime | None:
    value = (value or "").strip()
    if len(value) < 10:
        return None
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d")
    except ValueError:
        return None


def date_span_ok(date_from: str, date_to: str) -> bool:
    start = parse_date(date_from)
    end = parse_date(date_to)
    if start is None or end is None:
        return True
    return (end - start).days <= 90


def ip_group_allowed(db: Session, actor: User, ip_group_id: int | None) -> tuple[bool, list[int] | None]:
    if ip_group_id is None:
        return True, None
    scope = resolve(db, actor)
    if scope.kind == "ALL":
        return True, None
    if scope.kind == "IP_GROUP":
        allowed = scope.ip_group_ids or []
        if ip_group_id not in allowed:
            return False, allowed
        return True, allowed
    return False, []


def account_count(ops: Session, tenant_id: int, ip_group_id: int | None) -> int:
    stmt = select(func.count()).select_from(PlatformAccount).where(
        PlatformAccount.deleted == 0,
        PlatformAccount.tenant_id == tenant_id,
    )
    if ip_group_id:
        stmt = stmt.where(PlatformAccount.ip_group_id == ip_group_id)
    return int(ops.scalar(stmt) or 0)


def collect_fail_count(ops: Session, tenant_id: int, since: str) -> int:
    return int(
        ops.scalar(
            select(func.count()).select_from(CollectLog).where(
                CollectLog.deleted == 0,
                CollectLog.tenant_id == tenant_id,
                CollectLog.status.in_(("FAILED", "PARTIAL")),
                CollectLog.started_at >= since,
            )
        )
        or 0
    )


def pending_todo_count(db: Session, user_id: int) -> int:
    return int(
        db.scalar(
            select(func.count()).select_from(Todo).where(
                Todo.assignee_user_id == user_id,
                Todo.status == "PENDING",
            )
        )
        or 0
    )


def aggregate_todos(db: Session, ops: Session, actor: User, limit: int = 10) -> list[dict]:
    items: list[dict] = []
    reviews = db.scalars(
        select(ContentReview)
        .where(ContentReview.deleted == 0, ContentReview.conclusion.is_(None))
        .order_by(ContentReview.id.desc())
        .limit(limit)
    ).all()
    for row in reviews:
        items.append(
            {
                "type": "CONTENT_REVIEW",
                "title": f"内容审核 {row.review_no}",
                "bizId": row.review_no,
                "url": "/ims/content/review",
            }
        )
    since = (utcnow() - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
    fails = ops.scalars(
        select(CollectLog)
        .where(
            CollectLog.deleted == 0,
            CollectLog.tenant_id == tenant_of(actor),
            CollectLog.status == "FAILED",
            CollectLog.started_at >= since,
        )
        .order_by(CollectLog.id.desc())
        .limit(max(0, limit - len(items)))
    ).all()
    for row in fails:
        items.append(
            {
                "type": "COLLECT_FAIL",
                "title": f"采集失败 #{row.id}",
                "bizId": str(row.id),
                "url": f"/ims/collect/log?logId={row.id}",
            }
        )
    todos = db.scalars(
        select(Todo)
        .where(Todo.assignee_user_id == actor.id, Todo.status == "PENDING")
        .order_by(Todo.id.desc())
        .limit(max(0, limit - len(items)))
    ).all()
    for row in todos:
        ttype = row.task_type or "WORK_TASK"
        items.append(
            {
                "type": ttype,
                "title": row.title,
                "bizId": str(row.ref_id or row.id),
                "url": "/ims/workbench",
            }
        )
    return items[:limit]


def trend_placeholder() -> list[dict]:
    return [{"label": f"D-{i}", "play": 40 + i * 5, "engage": 20 + i * 3} for i in range(6, -1, -1)]


@router.get("/dashboard")
def home_dashboard(
    ipGroupId: int | None = None,
    dateFrom: str = "",
    dateTo: str = "",
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    if not date_span_ok(dateFrom, dateTo):
        return fail(1202, "日期跨度超过 90 天")
    ok_ip, _ = ip_group_allowed(db, actor, ipGroupId)
    if not ok_ip:
        return fail(1201, "无 IP 组权限")
    tenant_id = tenant_of(actor)
    if ipGroupId:
        group = ops.get(IpGroup, ipGroupId)
        if not visible(group, actor):
            return fail(1201, "无 IP 组权限")
    since = (utcnow() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    kpis = [
        {"key": "accounts", "label": "账号数", "value": str(account_count(ops, tenant_id, ipGroupId))},
        {"key": "worksToday", "label": "今日作品", "value": "数据延迟", "wow": "采集 KPI 不直连 Football"},
        {"key": "pendingTodos", "label": "待办任务", "value": str(pending_todo_count(db, actor.id))},
        {
            "key": "collectAlert",
            "label": "采集异常",
            "value": str(collect_fail_count(ops, tenant_id, since)),
        },
    ]
    todos = aggregate_todos(db, ops, actor, 8)
    shortcuts = [{"code": c, "name": n, "route": r} for c, n, r in SHORTCUT_CATALOG]
    return ok(
        {
            "kpis": kpis,
            "todos": todos,
            "shortcuts": shortcuts,
            "trendPlayEngage": trend_placeholder(),
            "ipGroupFilter": str(ipGroupId) if ipGroupId else None,
            "dateFrom": dateFrom or None,
            "dateTo": dateTo or None,
        }
    )


@router.get("/todos")
def home_todos(
    pageNo: int = 1,
    pageSize: int = 10,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    page_no, size = page_args(pageNo, pageSize)
    items = aggregate_todos(db, ops, actor, limit=200)
    total = len(items)
    start = (page_no - 1) * size
    chunk = items[start : start + size]
    return paged(chunk, total, page_no, size)


@router.get("/shortcuts")
def home_shortcuts(actor: User = Depends(current_user)):
    _ = actor
    data = [{"code": c, "name": n, "route": r} for c, n, r in SHORTCUT_CATALOG]
    return ok(data)
