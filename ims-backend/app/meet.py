"""会议日报 MEET-001~002 · MEET-004 会议纪要首片（W7-9）。"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from urllib import request as urlrequest

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.api import current_user, db_session, fail, ok
from app.core import utcnow
from app.corp import page_args, paged, tenant_of, user_names
from app.models import MeetDailyReport, MeetDailyReview, MeetMinutes, Todo, User
from app.scope import DataScope, dept_ids_of

router = APIRouter(prefix="/meet", tags=["meet"])


def ensure_meet_columns() -> None:
    """已有库补会议/日报列。create_all 不会给旧表加列。"""
    from sqlalchemy import inspect, text

    from app.core import engine

    insp = inspect(engine)
    tables = set(insp.get_table_names())
    alters: list[tuple[str, str, str]] = []
    if "ims_meet_daily_report" in tables:
        cols = {c["name"] for c in insp.get_columns("ims_meet_daily_report")}
        if "report_type" not in cols:
            alters.append(("ims_meet_daily_report", "report_type", "VARCHAR(32) NOT NULL DEFAULT ''"))
    if "ims_meet_minutes" in tables:
        cols = {c["name"] for c in insp.get_columns("ims_meet_minutes")}
        if "organizer_user_id" not in cols:
            alters.append(("ims_meet_minutes", "organizer_user_id", "BIGINT NOT NULL DEFAULT 0"))
        if "agenda" not in cols:
            alters.append(("ims_meet_minutes", "agenda", "TEXT NULL"))
        if "appendix" not in cols:
            alters.append(("ims_meet_minutes", "appendix", "TEXT NULL"))
    if not alters:
        return
    with engine.begin() as conn:
        for table, column, ddl in alters:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))

BJ = timezone(timedelta(hours=8))
DATE_RE = __import__("re").compile(r"^\d{4}-\d{2}-\d{2}$")


class DailyReviewBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    reviewLevel: int = Field(ge=1, le=2)
    action: str = "READ"
    comment: str = ""
    followUpItems: list[dict] | None = None


class ActionCloseBody(BaseModel):
    closeRemark: str = ""
    evidenceUrl: str = ""


REPORT_TYPES = {
    "LIVE": "直播",
    "SHORT_VIDEO": "短视频",
    "OPS": "运营",
    "ADMIN": "行政",
}
REPORT_TYPE_BY_LABEL = {label: key for key, label in REPORT_TYPES.items()}


class DailySubmitBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    reportDate: str
    reportType: str = ""
    contentDone: str = ""
    contentPlan: str = ""
    contentIssue: str = ""
    weekSummary: str = ""
    extraFields: dict[str, str] | None = None
    asDraft: bool = False
    supplement: str | None = None


def iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=BJ)
    return dt.astimezone(BJ).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def primary_dept(db: Session, user: User) -> tuple[int, str]:
    dept_ids = dept_ids_of(db, user)
    if not dept_ids:
        return 0, ""
    return dept_ids[0], f"部门#{dept_ids[0]}"


def calc_on_time(report_date: str, submitted_at: datetime) -> bool:
    try:
        day = datetime.strptime(report_date, "%Y-%m-%d").replace(tzinfo=BJ)
    except ValueError:
        return False
    deadline = day.replace(hour=22, minute=0, second=0, microsecond=0)
    at = submitted_at if submitted_at.tzinfo else submitted_at.replace(tzinfo=BJ)
    return at.astimezone(BJ) <= deadline


def normalize_report_type(raw: str) -> str:
    text = (raw or "").strip()
    if not text:
        return ""
    if text in REPORT_TYPES:
        return text
    return REPORT_TYPE_BY_LABEL.get(text, "")


def is_friday(report_date: str) -> bool:
    try:
        return datetime.strptime(report_date, "%Y-%m-%d").weekday() == 4
    except ValueError:
        return False


def daily_vo(row: MeetDailyReport) -> dict:
    report_type = row.report_type or ""
    return {
        "id": row.id,
        "reportDate": row.report_date,
        "reportType": report_type,
        "reportTypeLabel": REPORT_TYPES.get(report_type, report_type),
        "userId": row.user_id,
        "userName": row.user_name,
        "deptName": row.dept_name,
        "contentDone": row.content_done,
        "contentPlan": row.content_plan,
        "contentIssue": row.content_issue,
        "weekSummary": row.week_summary or None,
        "extraFields": row.extra_fields or {},
        "submitStatus": row.submit_status,
        "supplement": row.supplement or None,
        "submittedAt": iso(row.submitted_at),
        "isOnTime": bool(row.is_on_time),
        "createdAt": iso(row.created_at),
    }


def validate_submit_body(body: DailySubmitBody, *, require_content: bool) -> str | None:
    if not DATE_RE.match(body.reportDate or ""):
        return "reportDate 格式须为 yyyy-MM-dd"
    if (body.reportType or "").strip() and not normalize_report_type(body.reportType):
        return "日报类型无效"
    body.reportType = normalize_report_type(body.reportType)
    if require_content:
        if not (body.contentDone or "").strip():
            return "必填项，请填写"
        if is_friday(body.reportDate) and not (body.weekSummary or "").strip():
            return "必填项，请填写"
    return None


def apply_body(row: MeetDailyReport, body: DailySubmitBody, *, allow_main: bool) -> None:
    if allow_main:
        row.report_type = normalize_report_type(body.reportType)
        row.content_done = body.contentDone or ""
        row.content_plan = body.contentPlan or ""
        row.content_issue = body.contentIssue or ""
        row.week_summary = body.weekSummary or ""
        row.extra_fields = body.extraFields or {}
    if body.supplement is not None:
        row.supplement = body.supplement


def waiting_hours(submitted_at: datetime | None) -> float:
    if submitted_at is None:
        return 0.0
    now = datetime.now(BJ)
    at = submitted_at if submitted_at.tzinfo else submitted_at.replace(tzinfo=BJ)
    return max(0.0, (now - at.astimezone(BJ)).total_seconds() / 3600.0)


def review_vo(row: MeetDailyReview, report: MeetDailyReport | None = None) -> dict:
    items = row.follow_up_items or []
    return {
        "id": row.id,
        "reportId": row.report_id,
        "reportDate": report.report_date if report else "",
        "reviewerUserId": row.reviewer_user_id,
        "reviewerName": row.reviewer_name,
        "reviewLevel": row.review_level,
        "action": row.action,
        "comment": row.comment or None,
        "followUpItems": items,
        "reviewedAt": iso(row.reviewed_at),
    }


def queue_vo(row: MeetDailyReport, *, review_level: int) -> dict:
    hours = waiting_hours(row.submitted_at)
    data = daily_vo(row)
    data["reviewLevel"] = review_level
    data["waitingHours"] = round(hours, 1)
    data["isTimeout"] = review_level == 1 and hours > 24
    return data


def parse_follow_items(db: Session, raw_items: list) -> tuple[str | None, list[dict]]:
    if not raw_items:
        return "必填项，请填写", []
    ids = {
        int(item.get("responsibleUserId") or 0)
        for item in raw_items
        if isinstance(item, dict) and item.get("responsibleUserId")
    }
    names = user_names(db, ids)
    out: list[dict] = []
    for item in raw_items:
        if not isinstance(item, dict):
            return "必填项，请填写", []
        description = str(item.get("description") or "").strip()
        user_id = int(item.get("responsibleUserId") or 0)
        due = str(item.get("dueDate") or "").strip()[:10]
        if not description or not user_id or not DATE_RE.match(due):
            return "必填项，请填写", []
        out.append(
            {
                "description": description,
                "responsibleUserId": user_id,
                "responsibleName": names.get(user_id, ""),
                "dueDate": due,
                "status": "OPEN",
            }
        )
    return None, out


def sync_follow_todos(db: Session, review: MeetDailyReview, report: MeetDailyReport) -> None:
    now = utcnow()
    for item in review.follow_up_items or []:
        if not isinstance(item, dict):
            continue
        user_id = int(item.get("responsibleUserId") or 0)
        item_id = int(item.get("itemId") or 0)
        if not user_id or not item_id:
            continue
        found = db.scalar(
            select(Todo).where(
                Todo.ref_type == "meet_follow",
                Todo.ref_id == item_id,
                Todo.assignee_user_id == user_id,
            )
        )
        if found is not None:
            continue
        due = datetime.strptime(str(item["dueDate"])[:10], "%Y-%m-%d")
        db.add(
            Todo(
                assignee_user_id=user_id,
                task_type="MEET_FOLLOW",
                ref_type="meet_follow",
                ref_id=item_id,
                title=str(item.get("description") or "日报跟进")[:128],
                content=f"{report.report_date} {report.user_name}"[:512],
                status="PENDING",
                deadline=due,
                tenant_id=review.tenant_id,
                created_at=now,
            )
        )


def find_follow_item(db: Session, tenant_id: int, item_id: int) -> tuple[MeetDailyReview | None, dict | None]:
    rows = list(
        db.scalars(
            select(MeetDailyReview).where(
                MeetDailyReview.deleted == 0,
                MeetDailyReview.tenant_id == tenant_id,
            )
        ).all()
    )
    for review in rows:
        for item in review.follow_up_items or []:
            if isinstance(item, dict) and int(item.get("itemId") or 0) == item_id:
                return review, item
    return None, None


def has_review(db: Session, report_id: int, level: int, tenant_id: int) -> bool:
    found = db.scalar(
        select(MeetDailyReview.id).where(
            MeetDailyReview.deleted == 0,
            MeetDailyReview.tenant_id == tenant_id,
            MeetDailyReview.report_id == report_id,
            MeetDailyReview.review_level == level,
        )
    )
    return found is not None


def restrict_daily(stmt, actor: User, scope: DataScope | None, *, only_mine: bool):
    stmt = stmt.where(
        MeetDailyReport.deleted == 0,
        MeetDailyReport.tenant_id == tenant_of(actor),
    )
    if only_mine:
        return stmt.where(MeetDailyReport.user_id == actor.id)
    if scope is None or scope.kind == "ALL":
        return stmt
    if scope.kind == "SELF":
        return stmt.where(MeetDailyReport.user_id == actor.id)
    if scope.kind == "DEPT":
        if not scope.dept_ids:
            return stmt.where(MeetDailyReport.id < 0)
        return stmt.where(MeetDailyReport.dept_id.in_(scope.dept_ids))
    return stmt.where(MeetDailyReport.id < 0)


def upsert_daily(db: Session, actor: User, body: DailySubmitBody):
    err = validate_submit_body(body, require_content=not body.asDraft)
    if err:
        return fail(1001, err)

    tenant_id = tenant_of(actor)
    existing = db.scalar(
        select(MeetDailyReport).where(
            MeetDailyReport.deleted == 0,
            MeetDailyReport.tenant_id == tenant_id,
            MeetDailyReport.user_id == actor.id,
            MeetDailyReport.report_date == body.reportDate,
        )
    )
    dept_id, dept_name = primary_dept(db, actor)
    now = utcnow()

    if existing is None:
        row = MeetDailyReport(
            user_id=actor.id,
            dept_id=dept_id,
            user_name=actor.nickname or actor.username,
            dept_name=dept_name,
            report_date=body.reportDate,
            tenant_id=tenant_id,
            created_at=now,
            updated_at=now,
        )
        apply_body(row, body, allow_main=True)
        row.submit_status = "DRAFT"
        if not body.asDraft:
            row.submit_status = "SUBMITTED"
            row.submitted_at = now
            row.is_on_time = 1 if calc_on_time(body.reportDate, now) else 0
        db.add(row)
        db.flush()
        return ok(daily_vo(row))

    if existing.submit_status == "SUBMITTED" and not body.asDraft:
        if body.supplement is None and (
            body.contentDone != existing.content_done
            or body.contentPlan != existing.content_plan
            or body.contentIssue != existing.content_issue
        ):
            return fail(1112, "已提交不可再编辑正文，须走补充说明")
        if body.supplement is not None:
            existing.supplement = body.supplement
            existing.updated_at = now
            db.flush()
            return ok(daily_vo(existing))
        return fail(1111, "该日日报已提交")

    if existing.submit_status != "DRAFT":
        return fail(1112, "已提交不可再编辑正文，须走补充说明")

    apply_body(existing, body, allow_main=True)
    existing.updated_at = now
    if not body.asDraft:
        existing.submit_status = "SUBMITTED"
        existing.submitted_at = now
        existing.is_on_time = 1 if calc_on_time(body.reportDate, now) else 0
    db.flush()
    return ok(daily_vo(existing))


@router.get("/daily/template")
def daily_template(_: User = Depends(current_user)):
    weekday = datetime.now(BJ).weekday()
    friday = weekday == 4
    return ok(
        {
            "sections": [
                {"key": "done", "label": "今日完成", "required": True},
                {"key": "plan", "label": "明日计划", "required": False},
                {"key": "issue", "label": "问题与风险", "required": False},
                *(
                    [{"key": "weekly", "label": "周小结", "required": True}]
                    if friday
                    else []
                ),
            ],
            "reportTypes": [{"value": key, "label": label} for key, label in REPORT_TYPES.items()],
            "extraFields": [],
            "weekSummaryEnabled": friday,
            "deadlineTime": "22:00",
        }
    )


@router.post("/daily")
def daily_submit(body: DailySubmitBody, db: Session = Depends(db_session), actor: User = Depends(current_user)):
    return upsert_daily(db, actor, body)


@router.post("/daily/submit")
def daily_submit_alias(body: DailySubmitBody, db: Session = Depends(db_session), actor: User = Depends(current_user)):
    return upsert_daily(db, actor, body)


def _daily_list_query(
    request: Request,
    *,
    pageNo: int,
    pageSize: int,
    userId: int | None,
    deptId: int | None,
    submitStatus: str,
    dateFrom: str,
    dateTo: str,
    only_mine: bool,
    exclude_self: bool,
    db: Session,
    actor: User,
):
    stmt = select(MeetDailyReport)
    stmt = restrict_daily(stmt, actor, request.state.scope, only_mine=only_mine or userId == actor.id)
    if exclude_self:
        stmt = stmt.where(MeetDailyReport.user_id != actor.id)
    if userId and not only_mine:
        stmt = stmt.where(MeetDailyReport.user_id == userId)
    if deptId:
        stmt = stmt.where(MeetDailyReport.dept_id == deptId)
    if submitStatus:
        stmt = stmt.where(MeetDailyReport.submit_status == submitStatus)
    if dateFrom:
        stmt = stmt.where(MeetDailyReport.report_date >= dateFrom[:10])
    if dateTo:
        stmt = stmt.where(MeetDailyReport.report_date <= dateTo[:10])
    page_no, size = page_args(pageNo, pageSize)
    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = list(
        db.scalars(
            stmt.order_by(MeetDailyReport.report_date.desc(), MeetDailyReport.id.desc())
            .offset((page_no - 1) * size)
            .limit(size)
        ).all()
    )
    return page_no, size, total, rows


@router.get("/daily/team/list")
def daily_team_list(
    request: Request,
    pageNo: int = 1,
    pageSize: int = 10,
    userId: int | None = None,
    deptId: int | None = None,
    submitStatus: str = "",
    dateFrom: str = "",
    dateTo: str = "",
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    page_no, size, total, rows = _daily_list_query(
        request,
        pageNo=pageNo,
        pageSize=pageSize,
        userId=userId,
        deptId=deptId,
        submitStatus=submitStatus,
        dateFrom=dateFrom,
        dateTo=dateTo,
        only_mine=False,
        exclude_self=True,
        db=db,
        actor=actor,
    )
    return paged([daily_vo(row) for row in rows], total, page_no, size)


@router.get("/daily/list")
def daily_list(
    request: Request,
    pageNo: int = 1,
    pageSize: int = 10,
    userId: int | None = None,
    deptId: int | None = None,
    submitStatus: str = "",
    dateFrom: str = "",
    dateTo: str = "",
    onlyMine: bool = False,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    page_no, size, total, rows = _daily_list_query(
        request,
        pageNo=pageNo,
        pageSize=pageSize,
        userId=userId,
        deptId=deptId,
        submitStatus=submitStatus,
        dateFrom=dateFrom,
        dateTo=dateTo,
        only_mine=onlyMine,
        exclude_self=False,
        db=db,
        actor=actor,
    )
    return paged([daily_vo(row) for row in rows], total, page_no, size)


def rate_pct(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(100.0 * numerator / denominator, 1)


def parse_date_range(date_from: str, date_to: str) -> tuple[str, str]:
    today = datetime.now(BJ).date()
    end = (date_to or today.isoformat())[:10]
    start = (date_from or (today - timedelta(days=6)).isoformat())[:10]
    return start, end


@router.get("/stat/on-time-rate")
def stat_on_time_rate(
    request: Request,
    dateFrom: str = "",
    dateTo: str = "",
    deptId: int | None = None,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    """MEET-003 · BR-103 按时提交率（日口径，基于已落库日报聚合）。"""
    start, end = parse_date_range(dateFrom, dateTo)
    stmt = select(MeetDailyReport)
    stmt = restrict_daily(stmt, actor, request.state.scope, only_mine=False)
    stmt = stmt.where(
        MeetDailyReport.report_date >= start,
        MeetDailyReport.report_date <= end,
        MeetDailyReport.submit_status != "DRAFT",
    )
    if deptId:
        stmt = stmt.where(MeetDailyReport.dept_id == deptId)
    rows = list(db.scalars(stmt).all())

    on_time = sum(1 for r in rows if r.is_on_time and r.submit_status in ("SUBMITTED", "READ"))
    submitted = len(rows)
    total_on_time_rate = rate_pct(on_time, submitted)

    by_dept_map: dict[int, dict] = {}
    for row in rows:
        bucket = by_dept_map.setdefault(
            row.dept_id,
            {
                "deptId": row.dept_id,
                "deptName": row.dept_name or f"部门#{row.dept_id}",
                "onTime": 0,
                "submitted": 0,
            },
        )
        bucket["submitted"] += 1
        if row.is_on_time:
            bucket["onTime"] += 1
    by_dept = [
        {
            "deptId": item["deptId"],
            "deptName": item["deptName"],
            "onTimeRate": rate_pct(item["onTime"], item["submitted"]),
            "submitRate": rate_pct(item["submitted"], item["submitted"]),
        }
        for item in by_dept_map.values()
    ]
    by_dept.sort(key=lambda x: x["onTimeRate"], reverse=True)

    by_person_map: dict[int, dict] = {}
    for row in rows:
        bucket = by_person_map.setdefault(
            row.user_id,
            {
                "userId": row.user_id,
                "userName": row.user_name,
                "deptName": row.dept_name,
                "onTimeDays": 0,
                "submittedDays": 0,
                "shouldDays": 0,
            },
        )
        bucket["shouldDays"] += 1
        bucket["submittedDays"] += 1
        if row.is_on_time:
            bucket["onTimeDays"] += 1
    by_person = sorted(by_person_map.values(), key=lambda x: x["submittedDays"], reverse=True)

    trend_map: dict[str, dict] = {}
    for row in rows:
        bucket = trend_map.setdefault(row.report_date, {"date": row.report_date, "onTime": 0, "total": 0})
        bucket["total"] += 1
        if row.is_on_time:
            bucket["onTime"] += 1
    trend = [
        {"date": item["date"], "onTimeRate": rate_pct(item["onTime"], item["total"])}
        for item in sorted(trend_map.values(), key=lambda x: x["date"])
    ]

    return ok(
        {
            "totalOnTimeRate": total_on_time_rate,
            "totalSubmitRate": rate_pct(submitted, submitted) if submitted else 0.0,
            "byDept": by_dept,
            "byPerson": by_person,
            "trend": trend,
            "dateFrom": start,
            "dateTo": end,
        }
    )


@router.get("/daily/{date}")
def daily_by_date(date: str, db: Session = Depends(db_session), actor: User = Depends(current_user)):
    if not DATE_RE.match(date or ""):
        return fail(1001, "date 格式须为 yyyy-MM-dd")
    row = db.scalar(
        select(MeetDailyReport).where(
            MeetDailyReport.deleted == 0,
            MeetDailyReport.tenant_id == tenant_of(actor),
            MeetDailyReport.user_id == actor.id,
            MeetDailyReport.report_date == date,
        )
    )
    return ok(daily_vo(row) if row else None)


@router.put("/daily/{report_id}")
def daily_update(
    report_id: int,
    body: DailySubmitBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    row = db.get(MeetDailyReport, report_id)
    if row is None or row.deleted or row.tenant_id != tenant_of(actor) or row.user_id != actor.id:
        return fail(1004, "日报不存在")
    body.reportDate = row.report_date
    if row.submit_status == "DRAFT":
        return upsert_daily(db, actor, body)
    if body.supplement is None:
        return fail(1112, "已提交不可再编辑正文，须走补充说明")
    row.supplement = body.supplement
    row.updated_at = utcnow()
    db.flush()
    return ok(daily_vo(row))


@router.get("/review/queue")
def review_queue(
    request: Request,
    pageNo: int = 1,
    pageSize: int = 10,
    reviewLevel: int = 1,
    dateFrom: str = "",
    dateTo: str = "",
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    level = 1 if reviewLevel != 2 else 2
    tenant_id = tenant_of(actor)
    stmt = select(MeetDailyReport).where(
        MeetDailyReport.deleted == 0,
        MeetDailyReport.tenant_id == tenant_id,
        MeetDailyReport.submit_status == "SUBMITTED",
        MeetDailyReport.user_id != actor.id,
    )
    stmt = restrict_daily(stmt, actor, request.state.scope, only_mine=False)
    if dateFrom:
        stmt = stmt.where(MeetDailyReport.report_date >= dateFrom[:10])
    if dateTo:
        stmt = stmt.where(MeetDailyReport.report_date <= dateTo[:10])
    candidates = list(db.scalars(stmt.order_by(MeetDailyReport.submitted_at.asc())).all())
    pending: list[MeetDailyReport] = []
    for row in candidates:
        if level == 1:
            if not has_review(db, row.id, 1, tenant_id):
                pending.append(row)
        elif has_review(db, row.id, 1, tenant_id) and not has_review(db, row.id, 2, tenant_id):
            pending.append(row)
    page_no, size = page_args(pageNo, pageSize)
    total = len(pending)
    page_rows = pending[(page_no - 1) * size : page_no * size]
    return paged([queue_vo(row, review_level=level) for row in page_rows], total, page_no, size)


@router.put("/review/follow-up/{item_id}")
def review_follow_close(
    item_id: int,
    body: ActionCloseBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    review, item = find_follow_item(db, tenant_of(actor), item_id)
    if review is None or item is None:
        return fail(1004, "跟进项不存在")
    if int(item.get("responsibleUserId") or 0) != actor.id:
        return fail(1115, "非跟进项责任人，无权限回填")
    remark = (body.closeRemark or "").strip()
    if not remark:
        return fail(1001, "必填项，请填写")
    if item.get("status") != "CLOSED":
        item["status"] = "CLOSED"
        item["closeRemark"] = remark
        review.follow_up_items = list(review.follow_up_items or [])
        flag_modified(review, "follow_up_items")
        review.updated_at = utcnow()
        todo = db.scalar(
            select(Todo).where(
                Todo.ref_type == "meet_follow",
                Todo.ref_id == item_id,
                Todo.assignee_user_id == actor.id,
            )
        )
        if todo is not None and todo.status == "PENDING":
            todo.status = "DONE"
        db.flush()
    return ok(None)


@router.put("/review/{report_id}")
def review_action(
    report_id: int,
    body: DailyReviewBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    if body.action not in ("READ", "COMMENT", "MARK_FOLLOW_UP"):
        return fail(1001, "action 无效")
    if body.reviewLevel not in (1, 2):
        return fail(1001, "reviewLevel 须为 1 或 2")
    tenant_id = tenant_of(actor)
    row = db.get(MeetDailyReport, report_id)
    if row is None or row.deleted or row.tenant_id != tenant_id:
        return fail(1004, "日报不存在")
    if row.user_id == actor.id:
        return fail(1114, "非该日报的审阅人，无权限")
    if row.submit_status != "SUBMITTED":
        return fail(1001, "仅已提交日报可审阅")
    if body.reviewLevel == 2 and not has_review(db, report_id, 1, tenant_id):
        return fail(1113, "越级审阅：二级队列仅一级完成后进入")
    if has_review(db, report_id, body.reviewLevel, tenant_id):
        return fail(1001, "该层级已审阅")

    now = utcnow()
    follow_items = body.followUpItems or []
    parsed_follow: list[dict] = []
    if body.action == "MARK_FOLLOW_UP":
        err, parsed_follow = parse_follow_items(db, follow_items)
        if err:
            return fail(1001, err)

    review = MeetDailyReview(
        report_id=report_id,
        reviewer_user_id=actor.id,
        reviewer_name=actor.nickname or actor.username,
        review_level=body.reviewLevel,
        action=body.action,
        comment=body.comment or "",
        follow_up_items=[],
        reviewed_at=now,
        tenant_id=tenant_id,
        created_at=now,
        updated_at=now,
    )
    db.add(review)
    db.flush()
    if parsed_follow:
        for index, item in enumerate(parsed_follow, start=1):
            item["itemId"] = int(review.id) * 100 + index
        review.follow_up_items = parsed_follow
        flag_modified(review, "follow_up_items")
        sync_follow_todos(db, review, row)
    next_level: int | None = None
    if body.reviewLevel == 1 and body.action in ("READ", "COMMENT", "MARK_FOLLOW_UP"):
        next_level = 2
    if body.reviewLevel == 2 and body.action in ("READ", "COMMENT", "MARK_FOLLOW_UP"):
        row.submit_status = "READ"
        row.updated_at = now
        next_level = None
    db.flush()
    return ok(
        {
            "reviewId": review.id,
            "reportId": report_id,
            "reviewedAt": iso(now),
            "nextLevel": next_level,
        }
    )


@router.get("/review/records")
def review_records(
    pageNo: int = 1,
    pageSize: int = 10,
    reportId: int | None = None,
    reviewerUserId: int | None = None,
    reviewLevel: int | None = None,
    action: str = "",
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    stmt = select(MeetDailyReview).where(
        MeetDailyReview.deleted == 0,
        MeetDailyReview.tenant_id == tenant_id,
    )
    if reportId:
        stmt = stmt.where(MeetDailyReview.report_id == reportId)
    if reviewerUserId:
        stmt = stmt.where(MeetDailyReview.reviewer_user_id == reviewerUserId)
    if reviewLevel in (1, 2):
        stmt = stmt.where(MeetDailyReview.review_level == reviewLevel)
    if action:
        stmt = stmt.where(MeetDailyReview.action == action)
    page_no, size = page_args(pageNo, pageSize)
    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = list(
        db.scalars(
            stmt.order_by(MeetDailyReview.reviewed_at.desc(), MeetDailyReview.id.desc())
            .offset((page_no - 1) * size)
            .limit(size)
        ).all()
    )
    report_ids = {r.report_id for r in rows}
    reports = {}
    if report_ids:
        for rep in db.scalars(select(MeetDailyReport).where(MeetDailyReport.id.in_(report_ids))).all():
            reports[rep.id] = rep
    return paged([review_vo(r, reports.get(r.report_id)) for r in rows], total, page_no, size)


class AttendeeItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    userId: int | None = None
    userName: str = ""
    external: bool = False


class DecisionItem(BaseModel):
    description: str = ""


class ActionItemIn(BaseModel):
    itemId: int = 0
    description: str = ""
    responsibleUserId: int = 0
    dueDate: str = ""


class MinutesCreateBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    meetingTitle: str = ""
    meetingDate: str = ""
    meetingRoom: str = ""
    durationMinutes: int = Field(default=60, ge=15, le=480)
    attendees: list[AttendeeItem] = Field(default_factory=list)
    recorderUserId: int = 0
    agenda: str = ""
    summary: str = ""
    decisions: list[DecisionItem] | None = None
    actionItems: list[ActionItemIn] | None = None
    importFromAiMinutes: str | None = None
    appendix: str = ""


def parse_meeting_date(raw: str) -> datetime | None:
    text = (raw or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=BJ)
    return dt.astimezone(BJ)


def next_minutes_no(db: Session, tenant_id: int) -> str:
    day = datetime.now(BJ).strftime("%Y%m%d")
    prefix = f"MM{day}"
    count = db.scalar(
        select(func.count())
        .select_from(MeetMinutes)
        .where(
            MeetMinutes.deleted == 0,
            MeetMinutes.tenant_id == tenant_id,
            MeetMinutes.minutes_no.like(f"{prefix}%"),
        )
    )
    seq = int(count or 0) + 1
    return f"{prefix}{seq:03d}"


def build_action_items(
    db: Session,
    items: list[ActionItemIn] | None,
    *,
    minutes_id: int,
    existing: list | None = None,
) -> list[dict]:
    old = {
        int(it.get("itemId") or 0): it
        for it in (existing or [])
        if isinstance(it, dict) and int(it.get("itemId") or 0)
    }
    ids = {int(it.responsibleUserId) for it in (items or []) if it.responsibleUserId}
    names = user_names(db, ids)
    used = set(old)
    seq = 0
    out: list[dict] = []
    for it in items or []:
        desc = (it.description or "").strip()
        uid = int(it.responsibleUserId or 0)
        if not desc and not uid:
            continue
        iid = int(it.itemId or 0)
        prev = old.get(iid)
        if prev is None:
            seq += 1
            iid = minutes_id * 100 + seq
            while iid in used:
                seq += 1
                iid = minutes_id * 100 + seq
            used.add(iid)
            status = "OPEN"
            close_remark = ""
        else:
            status = "OPEN" if prev.get("status") == "OVERDUE" else (prev.get("status") or "OPEN")
            close_remark = prev.get("closeRemark") or ""
        out.append(
            {
                "itemId": iid,
                "description": desc,
                "responsibleUserId": uid,
                "responsibleName": names.get(uid) or (prev.get("responsibleName") if prev else "") or "",
                "dueDate": it.dueDate or "",
                "status": status,
                "closeRemark": close_remark,
            }
        )
    return out


def action_item_vo(item: dict) -> dict:
    status = item.get("status") or "OPEN"
    due = str(item.get("dueDate") or "")[:10]
    today = datetime.now(BJ).strftime("%Y-%m-%d")
    if status == "OPEN" and DATE_RE.match(due) and due < today:
        status = "OVERDUE"
    return {
        "itemId": item.get("itemId"),
        "description": item.get("description") or "",
        "responsibleUserId": item.get("responsibleUserId") or 0,
        "responsibleName": item.get("responsibleName") or "",
        "dueDate": item.get("dueDate") or "",
        "status": status,
        "closeRemark": item.get("closeRemark") or "",
    }


def sync_action_todos(db: Session, row: MeetMinutes) -> None:
    now = utcnow()
    for item in row.action_items or []:
        if not isinstance(item, dict):
            continue
        uid = int(item.get("responsibleUserId") or 0)
        item_id = int(item.get("itemId") or 0)
        if not uid or not item_id or (item.get("status") or "OPEN") != "OPEN":
            continue
        found = db.scalar(
            select(Todo).where(
                Todo.ref_type == "meet_action",
                Todo.ref_id == item_id,
                Todo.assignee_user_id == uid,
            )
        )
        if found is not None:
            continue
        due = None
        due_text = str(item.get("dueDate") or "")[:10]
        if DATE_RE.match(due_text):
            due = datetime.strptime(due_text, "%Y-%m-%d")
        db.add(
            Todo(
                assignee_user_id=uid,
                task_type="MEET_ACTION",
                ref_type="meet_action",
                ref_id=item_id,
                title=(item.get("description") or "会议行动项")[:128],
                content=f"{row.minutes_no} {row.meeting_title}"[:512],
                status="PENDING",
                deadline=due,
                tenant_id=row.tenant_id,
                created_at=now,
            )
        )


def find_action_item(db: Session, tenant_id: int, item_id: int) -> tuple[MeetMinutes | None, dict | None]:
    rows = list(
        db.scalars(
            select(MeetMinutes).where(MeetMinutes.deleted == 0, MeetMinutes.tenant_id == tenant_id)
        ).all()
    )
    for row in rows:
        for item in row.action_items or []:
            if isinstance(item, dict) and int(item.get("itemId") or 0) == item_id:
                return row, item
    return None, None


def meet_ai_draft(row: MeetMinutes) -> dict:
    """听记初稿。默认 stub；配置 MEET_AI_ENDPOINT 后走第三方 HTTP，不接本地模型。"""
    endpoint = os.environ.get("MEET_AI_ENDPOINT", "").strip()
    if endpoint:
        remote = _meet_ai_remote(endpoint, row)
        if remote is not None:
            remote["provider"] = "remote"
            remote["phase"] = "READY"
            return remote
    names = "、".join(
        str(item.get("userName") or "")
        for item in (row.attendees or [])
        if isinstance(item, dict) and item.get("userName")
    )
    return {
        "summary": (
            f"（AI 初稿·待校对）会议「{row.meeting_title}」。"
            f"议程：{row.agenda or '未提供'}。参会：{names or '未列'}。"
            "请记录人核对决议与行动项后保存。"
        ),
        "decisions": [{"description": "待记录人确认决议"}],
        "provider": "stub",
        "phase": "READY",
    }


def _meet_ai_remote(endpoint: str, row: MeetMinutes) -> dict | None:
    payload = {
        "meetingTitle": row.meeting_title,
        "agenda": row.agenda or "",
        "meetingDate": iso(row.meeting_date),
        "attendees": row.attendees or [],
    }
    req = urlrequest.Request(
        endpoint,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlrequest.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode() or "{}")
    except Exception:
        return None
    summary = str(data.get("summary") or "").strip()
    if not summary:
        return None
    decisions = data.get("decisions") if isinstance(data.get("decisions"), list) else []
    return {"summary": summary, "decisions": decisions}


def minutes_vo(row: MeetMinutes) -> dict:
    attendees = row.attendees or []
    return {
        "id": row.id,
        "minutesNo": row.minutes_no,
        "meetingTitle": row.meeting_title,
        "meetingDate": iso(row.meeting_date),
        "meetingRoom": row.meeting_room or None,
        "durationMinutes": row.duration_minutes,
        "agenda": row.agenda or "",
        "organizerUserId": row.organizer_user_id or row.recorder_user_id,
        "organizerName": row.organizer_name or row.recorder_name,
        "attendeeCount": len(attendees),
        "attendees": attendees,
        "summary": row.summary or "",
        "appendix": row.appendix or "",
        "decisions": row.decisions or [],
        "actionItems": [action_item_vo(item) for item in (row.action_items or []) if isinstance(item, dict)],
        "minutesStatus": row.minutes_status,
        "recorderUserId": row.recorder_user_id,
        "recorderName": row.recorder_name,
        "archivedAt": iso(row.archived_at),
        "createdAt": iso(row.created_at),
    }


def minutes_base(actor: User):
    return select(MeetMinutes).where(MeetMinutes.deleted == 0, MeetMinutes.tenant_id == tenant_of(actor))


def attendee_of(row: MeetMinutes, actor: User) -> bool:
    names = {(actor.nickname or "").strip(), (actor.username or "").strip()}
    names.discard("")
    for item in row.attendees or []:
        if not isinstance(item, dict):
            continue
        try:
            uid = int(item.get("userId") or 0)
        except (TypeError, ValueError):
            uid = 0
        if uid and uid == actor.id:
            return True
        user_name = str(item.get("userName") or "").strip()
        if user_name and user_name in names:
            return True
    return False


def minutes_visible(row: MeetMinutes, actor: User, scope: DataScope | None) -> bool:
    """发起人、记录人、参会人可见；部门数据范围另外可见本部门会议。"""
    if scope is None or scope.kind == "ALL":
        return True
    if row.recorder_user_id == actor.id or int(row.organizer_user_id or 0) == actor.id:
        return True
    if attendee_of(row, actor):
        return True
    if scope.kind == "DEPT" and scope.dept_ids and int(row.dept_id or 0) in set(scope.dept_ids):
        return True
    return False


def load_visible_minutes(db: Session, actor: User, scope: DataScope | None, stmt):
    rows = list(
        db.scalars(stmt.order_by(MeetMinutes.meeting_date.desc(), MeetMinutes.id.desc())).all()
    )
    return [row for row in rows if minutes_visible(row, actor, scope)]


@router.get("/minutes/list")
def minutes_list(
    request: Request,
    pageNo: int = 1,
    pageSize: int = 10,
    meetingTitle: str = "",
    minutesStatus: str = "",
    dateFrom: str = "",
    dateTo: str = "",
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    stmt = minutes_base(actor)
    if meetingTitle:
        stmt = stmt.where(MeetMinutes.meeting_title.like(f"%{meetingTitle.strip()}%"))
    if minutesStatus:
        stmt = stmt.where(MeetMinutes.minutes_status == minutesStatus)
    if dateFrom:
        stmt = stmt.where(MeetMinutes.meeting_date >= parse_meeting_date(dateFrom[:10] + "T00:00:00+08:00"))
    if dateTo:
        stmt = stmt.where(MeetMinutes.meeting_date <= parse_meeting_date(dateTo[:10] + "T23:59:59+08:00"))
    page_no, size = page_args(pageNo, pageSize)
    rows = load_visible_minutes(db, actor, request.state.scope, stmt)
    total = len(rows)
    page = rows[(page_no - 1) * size : page_no * size]
    return paged([minutes_vo(row) for row in page], total, page_no, size)


@router.post("/minutes")
def minutes_create(
    body: MinutesCreateBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    title = (body.meetingTitle or "").strip()
    when = parse_meeting_date(body.meetingDate)
    attendees = [a.model_dump(exclude_none=True) for a in body.attendees if (a.userName or "").strip() or a.userId]
    if not title or when is None or not attendees:
        return fail(1001, "必填项，请填写")
    tenant_id = tenant_of(actor)
    dept_id, _ = primary_dept(db, actor)
    now = utcnow()
    summary = (body.summary or "").strip()
    status = "MINUTES_RECORDED" if summary else "REGISTERED"
    recorder_id = int(body.recorderUserId or 0) or actor.id
    recorder = db.get(User, recorder_id) if recorder_id != actor.id else actor
    if recorder is None or recorder.deleted:
        recorder = actor
        recorder_id = actor.id
    decisions = [{"description": d.description} for d in (body.decisions or []) if d.description]
    row = MeetMinutes(
        minutes_no=next_minutes_no(db, tenant_id),
        meeting_title=title,
        meeting_date=when,
        meeting_room=(body.meetingRoom or "").strip(),
        duration_minutes=body.durationMinutes,
        agenda=(body.agenda or "").strip(),
        organizer_user_id=actor.id,
        organizer_name=actor.nickname or actor.username,
        attendees=attendees,
        summary=summary,
        decisions=decisions,
        action_items=[],
        minutes_status=status,
        recorder_user_id=recorder.id,
        recorder_name=recorder.nickname or recorder.username,
        dept_id=dept_id,
        tenant_id=tenant_id,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()
    if body.actionItems:
        row.action_items = build_action_items(db, body.actionItems, minutes_id=row.id)
        sync_action_todos(db, row)
        db.flush()
    return ok(minutes_vo(row))


@router.get("/minutes/archive-rate")
def minutes_archive_rate(
    request: Request,
    dateFrom: str = "",
    dateTo: str = "",
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    stmt = minutes_base(actor)
    if dateFrom:
        stmt = stmt.where(MeetMinutes.meeting_date >= parse_meeting_date(dateFrom[:10] + "T00:00:00+08:00"))
    if dateTo:
        stmt = stmt.where(MeetMinutes.meeting_date <= parse_meeting_date(dateTo[:10] + "T23:59:59+08:00"))
    rows = load_visible_minutes(db, actor, request.state.scope, stmt)
    total = len(rows)
    archived = sum(1 for r in rows if r.minutes_status == "ARCHIVED")
    recorded = sum(1 for r in rows if r.minutes_status in ("MINUTES_RECORDED", "ARCHIVED"))
    rate = round(archived * 100.0 / total, 2) if total else 0.0
    trace_rate = round(archived * 100.0 / recorded, 2) if recorded else 0.0
    return ok(
        {
            "totalMeetings": total,
            "archivedCount": archived,
            "recordedCount": recorded,
            "archiveRate": rate,
            "traceRate": trace_rate,
        }
    )


@router.get("/minutes/participants")
def minutes_participants(db: Session = Depends(db_session), actor: User = Depends(current_user)):
    rows = list(
        db.scalars(
            select(User)
            .where(User.deleted == 0, User.status == "ENABLED", User.tenant_id == tenant_of(actor))
            .order_by(User.id)
            .limit(300)
        ).all()
    )
    return ok(
        {
            "list": [
                {"userId": row.id, "userName": row.nickname or row.username, "username": row.username}
                for row in rows
            ]
        }
    )


@router.put("/minutes/action-item/{item_id}")
def minutes_action_close(
    item_id: int,
    body: ActionCloseBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    row, item = find_action_item(db, tenant_of(actor), item_id)
    if row is None or item is None:
        return fail(1004, "行动项不存在")
    owner = int(item.get("responsibleUserId") or 0)
    if owner != actor.id:
        return fail(1118, "非行动项责任人")
    remark = (body.closeRemark or "").strip()
    if not remark:
        return fail(1118, "请填写回填说明")
    if item.get("status") != "CLOSED":
        item["status"] = "CLOSED"
        item["closeRemark"] = remark
        if (body.evidenceUrl or "").strip():
            item["evidenceUrl"] = body.evidenceUrl.strip()
        row.action_items = list(row.action_items or [])
        flag_modified(row, "action_items")
        row.updated_at = utcnow()
        todo = db.scalar(
            select(Todo).where(
                Todo.ref_type == "meet_action",
                Todo.ref_id == item_id,
                Todo.assignee_user_id == actor.id,
            )
        )
        if todo is not None and todo.status == "PENDING":
            todo.status = "DONE"
        db.flush()
    return ok(minutes_vo(row))


@router.get("/minutes/{minutes_id}")
def minutes_detail(
    minutes_id: int,
    request: Request,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    row = db.scalar(minutes_base(actor).where(MeetMinutes.id == minutes_id))
    if row is None or not minutes_visible(row, actor, request.state.scope):
        return fail(1004, "会议纪要不存在")
    return ok(minutes_vo(row))


def _visible_minutes(db: Session, actor: User, scope: DataScope | None, minutes_id: int) -> MeetMinutes | None:
    row = db.scalar(minutes_base(actor).where(MeetMinutes.id == minutes_id))
    if row is None or not minutes_visible(row, actor, scope):
        return None
    return row


@router.put("/minutes/{minutes_id}")
def minutes_update(
    minutes_id: int,
    body: MinutesCreateBody,
    request: Request,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    row = _visible_minutes(db, actor, request.state.scope, minutes_id)
    if row is None:
        return fail(1004, "会议纪要不存在")
    now = utcnow()
    if row.minutes_status == "ARCHIVED":
        note = (body.appendix or "").strip()
        if not note:
            return fail(1117, "已归档纪要不可修改")
        row.appendix = f"{row.appendix}\n{note}".strip() if row.appendix else note
        row.updated_at = now
        db.flush()
        return ok(minutes_vo(row))
    summary = (body.summary or "").strip()
    if not summary:
        return fail(1001, "必填项，请填写")
    title = (body.meetingTitle or "").strip() or row.meeting_title
    when = parse_meeting_date(body.meetingDate) if (body.meetingDate or "").strip() else row.meeting_date
    attendees = [a.model_dump(exclude_none=True) for a in body.attendees if (a.userName or "").strip() or a.userId]
    row.meeting_title = title
    if when is not None:
        row.meeting_date = when
    if (body.meetingRoom or "").strip():
        row.meeting_room = body.meetingRoom.strip()
    if body.durationMinutes:
        row.duration_minutes = body.durationMinutes
    if (body.agenda or "").strip():
        row.agenda = body.agenda.strip()
    if attendees:
        row.attendees = attendees
    row.summary = summary
    row.decisions = [{"description": d.description} for d in (body.decisions or []) if (d.description or "").strip()]
    row.action_items = build_action_items(
        db, body.actionItems, minutes_id=row.id, existing=list(row.action_items or [])
    )
    row.minutes_status = "MINUTES_RECORDED"
    row.updated_at = now
    sync_action_todos(db, row)
    db.flush()
    return ok(minutes_vo(row))


@router.post("/minutes/{minutes_id}/ai-draft")
def minutes_ai_draft(
    minutes_id: int,
    request: Request,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    row = _visible_minutes(db, actor, request.state.scope, minutes_id)
    if row is None:
        return fail(1004, "会议纪要不存在")
    if row.minutes_status == "ARCHIVED":
        return fail(1117, "已归档纪要不可修改")
    return ok(meet_ai_draft(row))


@router.put("/minutes/{minutes_id}/archive")
def minutes_archive(
    minutes_id: int,
    request: Request,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    row = db.scalar(minutes_base(actor).where(MeetMinutes.id == minutes_id))
    if row is None or not minutes_visible(row, actor, request.state.scope):
        return fail(1004, "会议纪要不存在")
    if row.minutes_status == "REGISTERED":
        return fail(1001, "请先录入纪要再归档")
    if row.minutes_status == "ARCHIVED":
        return ok(minutes_vo(row))
    now = utcnow()
    row.minutes_status = "ARCHIVED"
    row.archived_at = now
    row.updated_at = now
    db.flush()
    return ok(minutes_vo(row))
