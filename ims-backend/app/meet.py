"""会议日报 MEET-001~002 · MEET-004 会议纪要首片（W7-9）。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.core import utcnow
from app.corp import page_args, paged, tenant_of, user_names
from app.models import MeetDailyReport, MeetDailyReview, MeetMinutes, User
from app.scope import DataScope, dept_ids_of

router = APIRouter(prefix="/meet", tags=["meet"])

BJ = timezone(timedelta(hours=8))
DATE_RE = __import__("re").compile(r"^\d{4}-\d{2}-\d{2}$")


class DailyReviewBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    reviewLevel: int = Field(ge=1, le=2)
    action: str = "READ"
    comment: str = ""
    followUpItems: list[dict] | None = None


class DailySubmitBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    reportDate: str
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


def daily_vo(row: MeetDailyReport) -> dict:
    return {
        "id": row.id,
        "reportDate": row.report_date,
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
    if require_content:
        for field, label in (
            (body.contentDone, "今日完成"),
            (body.contentPlan, "明日计划"),
            (body.contentIssue, "问题与风险"),
        ):
            if not (field or "").strip():
                return f"{label} 必填"
    return None


def apply_body(row: MeetDailyReport, body: DailySubmitBody, *, allow_main: bool) -> None:
    if allow_main:
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
    return ok(
        {
            "sections": [
                {"key": "done", "label": "今日完成", "required": True},
                {"key": "plan", "label": "明日计划", "required": True},
                {"key": "issue", "label": "问题与风险", "required": True},
                *(
                    [{"key": "weekly", "label": "周小结", "required": True}]
                    if weekday == 4
                    else []
                ),
            ],
            "extraFields": [],
            "weekSummaryEnabled": weekday == 4,
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
    if body.action == "MARK_FOLLOW_UP" and not follow_items:
        return fail(1001, "标记跟进须填写 followUpItems")

    review = MeetDailyReview(
        report_id=report_id,
        reviewer_user_id=actor.id,
        reviewer_name=actor.nickname or actor.username,
        review_level=body.reviewLevel,
        action=body.action,
        comment=body.comment or "",
        follow_up_items=follow_items,
        reviewed_at=now,
        tenant_id=tenant_id,
        created_at=now,
        updated_at=now,
    )
    db.add(review)
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
    description: str = ""
    responsibleUserId: int = 0
    dueDate: str = ""


class MinutesCreateBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    meetingTitle: str
    meetingDate: str
    meetingRoom: str = ""
    durationMinutes: int = Field(default=60, ge=15, le=480)
    attendees: list[AttendeeItem] = Field(default_factory=list)
    summary: str = ""
    decisions: list[DecisionItem] | None = None
    actionItems: list[ActionItemIn] | None = None
    importFromAiMinutes: str | None = None


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


def normalize_action_items(db: Session, items: list[ActionItemIn] | None) -> list[dict]:
    if not items:
        return []
    ids = {int(it.responsibleUserId) for it in items if it.responsibleUserId}
    names = user_names(db, ids)
    out: list[dict] = []
    for idx, it in enumerate(items, start=1):
        uid = int(it.responsibleUserId or 0)
        out.append(
            {
                "itemId": idx,
                "description": it.description or "",
                "responsibleUserId": uid,
                "responsibleName": names.get(uid, ""),
                "dueDate": it.dueDate or "",
                "status": "OPEN",
            }
        )
    return out


def minutes_vo(row: MeetMinutes) -> dict:
    attendees = row.attendees or []
    return {
        "id": row.id,
        "minutesNo": row.minutes_no,
        "meetingTitle": row.meeting_title,
        "meetingDate": iso(row.meeting_date),
        "meetingRoom": row.meeting_room or None,
        "durationMinutes": row.duration_minutes,
        "organizerName": row.organizer_name or row.recorder_name,
        "attendeeCount": len(attendees),
        "attendees": attendees,
        "summary": row.summary or "",
        "decisions": row.decisions or [],
        "actionItems": row.action_items or [],
        "minutesStatus": row.minutes_status,
        "recorderUserId": row.recorder_user_id,
        "recorderName": row.recorder_name,
        "archivedAt": iso(row.archived_at),
        "createdAt": iso(row.created_at),
    }


def restrict_minutes(stmt, actor: User, scope: DataScope | None):
    stmt = stmt.where(MeetMinutes.deleted == 0, MeetMinutes.tenant_id == tenant_of(actor))
    if scope is None or scope.kind == "ALL":
        return stmt
    if scope.kind == "SELF":
        return stmt.where(MeetMinutes.recorder_user_id == actor.id)
    if scope.kind == "DEPT":
        if not scope.dept_ids:
            return stmt.where(MeetMinutes.id < 0)
        return stmt.where(MeetMinutes.dept_id.in_(scope.dept_ids))
    return stmt.where(MeetMinutes.id < 0)


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
    stmt = select(MeetMinutes)
    stmt = restrict_minutes(stmt, actor, request.state.scope)
    if meetingTitle:
        stmt = stmt.where(MeetMinutes.meeting_title.like(f"%{meetingTitle.strip()}%"))
    if minutesStatus:
        stmt = stmt.where(MeetMinutes.minutes_status == minutesStatus)
    if dateFrom:
        stmt = stmt.where(MeetMinutes.meeting_date >= parse_meeting_date(dateFrom[:10] + "T00:00:00+08:00"))
    if dateTo:
        stmt = stmt.where(MeetMinutes.meeting_date <= parse_meeting_date(dateTo[:10] + "T23:59:59+08:00"))
    page_no, size = page_args(pageNo, pageSize)
    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = list(
        db.scalars(
            stmt.order_by(MeetMinutes.meeting_date.desc(), MeetMinutes.id.desc())
            .offset((page_no - 1) * size)
            .limit(size)
        ).all()
    )
    return paged([minutes_vo(row) for row in rows], total, page_no, size)


@router.post("/minutes")
def minutes_create(
    body: MinutesCreateBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    title = (body.meetingTitle or "").strip()
    if not title:
        return fail(1001, "meetingTitle 必填")
    when = parse_meeting_date(body.meetingDate)
    if when is None:
        return fail(1001, "meetingDate 格式无效")
    tenant_id = tenant_of(actor)
    dept_id, _ = primary_dept(db, actor)
    now = utcnow()
    summary = (body.summary or "").strip()
    status = "MINUTES_RECORDED" if summary else "REGISTERED"
    attendees = [a.model_dump(exclude_none=True) for a in body.attendees]
    decisions = [{"description": d.description} for d in (body.decisions or []) if d.description]
    actions = normalize_action_items(db, body.actionItems)
    row = MeetMinutes(
        minutes_no=next_minutes_no(db, tenant_id),
        meeting_title=title,
        meeting_date=when,
        meeting_room=(body.meetingRoom or "").strip(),
        duration_minutes=body.durationMinutes,
        organizer_name=actor.nickname or actor.username,
        attendees=attendees,
        summary=summary,
        decisions=decisions,
        action_items=actions,
        minutes_status=status,
        recorder_user_id=actor.id,
        recorder_name=actor.nickname or actor.username,
        dept_id=dept_id,
        tenant_id=tenant_id,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
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
    stmt = select(MeetMinutes)
    stmt = restrict_minutes(stmt, actor, request.state.scope)
    if dateFrom:
        stmt = stmt.where(MeetMinutes.meeting_date >= parse_meeting_date(dateFrom[:10] + "T00:00:00+08:00"))
    if dateTo:
        stmt = stmt.where(MeetMinutes.meeting_date <= parse_meeting_date(dateTo[:10] + "T23:59:59+08:00"))
    rows = list(db.scalars(stmt).all())
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


@router.get("/minutes/{minutes_id}")
def minutes_detail(
    minutes_id: int,
    request: Request,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    stmt = restrict_minutes(select(MeetMinutes).where(MeetMinutes.id == minutes_id), actor, request.state.scope)
    row = db.scalar(stmt)
    if row is None:
        return fail(1004, "会议纪要不存在")
    return ok(minutes_vo(row))


@router.put("/minutes/{minutes_id}/archive")
def minutes_archive(
    minutes_id: int,
    request: Request,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    stmt = restrict_minutes(select(MeetMinutes).where(MeetMinutes.id == minutes_id), actor, request.state.scope)
    row = db.scalar(stmt)
    if row is None:
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
