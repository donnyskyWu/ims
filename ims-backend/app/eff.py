"""EFF-001 人员归属 · EFF-002 覆盖率（W9-5 首片）。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.core import utcnow
from app.corp import page_args, paged, tenant_of, user_names
from app.models import ContentProject, EffRelation, LiveReport, LiveSession, User

router = APIRouter(prefix="/eff", tags=["eff"])

BJ = timezone(timedelta(hours=8))


class RelationBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    userId: int
    relationType: str = "PRIMARY"
    targetType: str = "IP_GROUP"
    targetId: int = 0
    targetName: str = ""
    shareRatio: float = Field(default=100.0, ge=0, le=100)
    effectiveFrom: str = ""


def iso(dt: datetime | None) -> str:
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=BJ)
    return dt.astimezone(BJ).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def relation_vo(row: EffRelation, names: dict[int, str]) -> dict:
    return {
        "id": row.id,
        "userId": row.user_id,
        "userName": names.get(row.user_id, ""),
        "relationType": row.relation_type,
        "targetType": row.target_type,
        "targetId": row.target_id,
        "targetName": row.target_name,
        "shareRatio": float(row.share_ratio or 0),
        "effectiveFrom": row.effective_from,
        "effectiveTo": row.effective_to or None,
        "status": row.status,
        "changedByName": names.get(row.changed_by, ""),
        "changedAt": iso(row.updated_at),
    }


def active_primary(db: Session, tenant_id: int, user_id: int) -> EffRelation | None:
    return db.scalar(
        select(EffRelation).where(
            EffRelation.deleted == 0,
            EffRelation.tenant_id == tenant_id,
            EffRelation.user_id == user_id,
            EffRelation.relation_type == "PRIMARY",
            EffRelation.status == "ACTIVE",
        )
    )


def part_time_sum(db: Session, tenant_id: int, user_id: int) -> float:
    rows = db.scalars(
        select(EffRelation).where(
            EffRelation.deleted == 0,
            EffRelation.tenant_id == tenant_id,
            EffRelation.user_id == user_id,
            EffRelation.relation_type == "PART_TIME",
            EffRelation.status == "ACTIVE",
        )
    ).all()
    return sum(float(r.share_ratio or 0) for r in rows)


@router.get("/relation/list")
def relation_list(
    userId: int | None = None,
    relationType: str | None = None,
    status: str | None = None,
    pageNo: int = 1,
    pageSize: int = 10,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    q = select(EffRelation).where(EffRelation.deleted == 0, EffRelation.tenant_id == tenant_id)
    if userId is not None:
        q = q.where(EffRelation.user_id == userId)
    if relationType:
        q = q.where(EffRelation.relation_type == relationType.strip().upper())
    if status:
        q = q.where(EffRelation.status == status.strip().upper())
    page_no, size = page_args(pageNo, pageSize)
    stmt = q.order_by(EffRelation.id.desc())
    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = list(db.scalars(stmt.offset((page_no - 1) * size).limit(size)).all())
    user_ids = {r.user_id for r in rows} | {r.changed_by for r in rows}
    names = user_names(db, list(user_ids))
    return paged([relation_vo(r, names) for r in rows], total, page_no, size)


@router.post("/relation")
def relation_create(body: RelationBody, db: Session = Depends(db_session), actor: User = Depends(current_user)):
    tenant_id = tenant_of(actor)
    rtype = body.relationType.strip().upper()
    if rtype not in {"PRIMARY", "PART_TIME"}:
        return fail(1001, "归属类型无效")
    if rtype == "PRIMARY":
        if body.shareRatio != 100:
            return fail(1001, "主归属分摊比例必须为 100%")
        if active_primary(db, tenant_id, body.userId) is not None:
            return fail(1198, "在职人员已存在主归属")
    else:
        total = part_time_sum(db, tenant_id, body.userId) + body.shareRatio
        if total > 100:
            return fail(1199, "兼职分摊比例合计超过 100%")
    now = utcnow()
    eff_from = body.effectiveFrom.strip() or datetime.now(BJ).strftime("%Y-%m-%d")
    row = EffRelation(
        user_id=body.userId,
        relation_type=rtype,
        target_type=body.targetType.strip().upper() or "IP_GROUP",
        target_id=body.targetId,
        target_name=body.targetName.strip() or f"目标#{body.targetId}",
        share_ratio=body.shareRatio,
        effective_from=eff_from,
        status="ACTIVE",
        changed_by=actor.id,
        tenant_id=tenant_id,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()
    names = user_names(db, [row.user_id, row.changed_by])
    return ok(relation_vo(row, names))


@router.get("/relation/coverage")
def relation_coverage(db: Session = Depends(db_session), actor: User = Depends(current_user)):
    tenant_id = tenant_of(actor)
    enabled_users = int(
        db.scalar(
            select(func.count()).select_from(User).where(User.deleted == 0, User.status == "ENABLED", User.tenant_id == tenant_id)
        )
        or 0
    )
    covered = int(
        db.scalar(
            select(func.count(func.distinct(EffRelation.user_id))).where(
                EffRelation.deleted == 0,
                EffRelation.tenant_id == tenant_id,
                EffRelation.relation_type == "PRIMARY",
                EffRelation.status == "ACTIVE",
            )
        )
        or 0
    )
    rate = round(covered * 100.0 / enabled_users, 2) if enabled_users else 0.0
    return ok(
        {
            "enabledUserCount": enabled_users,
            "coveredUserCount": covered,
            "coverageRate": rate,
            "canPublish": rate >= 100.0 and enabled_users > 0,
        }
    )


@router.get("/inventory/snapshot")
def inventory_snapshot(db: Session = Depends(db_session), actor: User = Depends(current_user)):
    tenant_id = tenant_of(actor)
    enabled_users = int(
        db.scalar(
            select(func.count()).select_from(User).where(User.deleted == 0, User.status == "ENABLED", User.tenant_id == tenant_id)
        )
        or 0
    )
    covered = int(
        db.scalar(
            select(func.count(func.distinct(EffRelation.user_id))).where(
                EffRelation.deleted == 0,
                EffRelation.tenant_id == tenant_id,
                EffRelation.relation_type == "PRIMARY",
                EffRelation.status == "ACTIVE",
            )
        )
        or 0
    )
    rate = round(covered * 100.0 / enabled_users, 2) if enabled_users else 0.0
    period = datetime.now(BJ).strftime("%Y-%m")
    return ok(
        {
            "period": period,
            "enabledUserCount": enabled_users,
            "coveredUserCount": covered,
            "coverageRate": rate,
            "canPublish": rate >= 100.0 and enabled_users > 0,
            "status": "PUBLISHED" if rate >= 100 and enabled_users else "DRAFT",
            "note": "只读快照 · 发布裁决下一迭代",
        }
    )


def current_period() -> str:
    return datetime.now(BJ).strftime("%Y-%m")


def stamp_period(value: str | datetime | None) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=BJ)
        return value.astimezone(BJ).strftime("%Y-%m")
    text = str(value).strip()
    return text[:7] if len(text) >= 7 else ""


def capita(total: float, heads: int, has_source: bool) -> float | None:
    """无覆盖人数或台账没有记录时返回空，避免把占位数字当成人均。"""
    if heads <= 0 or not has_source:
        return None
    return round(total / heads, 2)


def dept_label(db: Session, user_id: int, tenant_id: int) -> str:
    from app.api import user_dept_snapshot

    _ids, names = user_dept_snapshot(db, user_id, tenant_id)
    return names[0] if names else ""


def month_activity(db: Session, tenant_id: int, period: str) -> tuple[dict[int, tuple[float, int]], dict[int, int]]:
    """当月直播 GMV/场次（责任人）与内容作品数（提交人）。没有记录的人不出现在字典里。"""
    sessions = db.scalars(
        select(LiveSession).where(LiveSession.deleted == 0, LiveSession.tenant_id == tenant_id)
    ).all()
    month_sessions = [row for row in sessions if stamp_period(row.plan_start_time or row.created_at) == period]
    codes = [row.session_code for row in month_sessions if row.session_code]
    reports = (
        db.scalars(select(LiveReport).where(LiveReport.deleted == 0, LiveReport.session_code.in_(codes))).all()
        if codes
        else []
    )
    gmv_by_code = {row.session_code: float(row.gmv or 0) for row in reports}
    live: dict[int, tuple[float, int]] = {}
    for row in month_sessions:
        uid = int(row.responsible_user_id or 0)
        if uid <= 0:
            continue
        gmv, count = live.get(uid, (0.0, 0))
        live[uid] = (gmv + gmv_by_code.get(row.session_code, 0.0), count + 1)
    projects = db.scalars(
        select(ContentProject).where(ContentProject.deleted == 0, ContentProject.tenant_id == tenant_id)
    ).all()
    works: dict[int, int] = {}
    for row in projects:
        if stamp_period(row.created_at) != period:
            continue
        uid = int(row.submitter_user_id or 0)
        if uid <= 0:
            continue
        works[uid] = works.get(uid, 0) + 1
    return live, works


def person_rows(
    db: Session,
    tenant_id: int,
    period: str,
    keyword: str = "",
    dept: str = "",
    share_status: str = "",
) -> tuple[list[dict], list[str]]:
    rows = db.scalars(
        select(EffRelation).where(
            EffRelation.deleted == 0,
            EffRelation.tenant_id == tenant_id,
            EffRelation.status == "ACTIVE",
        )
    ).all()
    by_user: dict[int, list[EffRelation]] = {}
    for row in rows:
        by_user.setdefault(int(row.user_id), []).append(row)
    names = user_names(db, list(by_user))
    live, works = month_activity(db, tenant_id, period)
    people: list[dict] = []
    depts: set[str] = set()
    needle = keyword.strip()
    want = share_status.strip().upper()
    for uid, rels in by_user.items():
        primary = next((item for item in rels if item.relation_type == "PRIMARY"), None)
        parts = [item for item in rels if item.relation_type == "PART_TIME"]
        part_sum = round(sum(float(item.share_ratio or 0) for item in parts), 2)
        # 分摊合计沿用已落地口径：只计兼职，不含主归属。是否改计主归属等产品裁定。
        over = part_sum > 100
        name = names.get(uid, "") or str(uid)
        department = dept_label(db, uid, tenant_id)
        if department:
            depts.add(department)
        if needle and needle not in name:
            continue
        if dept and department != dept:
            continue
        if want == "OVER" and not over:
            continue
        if want == "NORMAL" and over:
            continue
        has_live = uid in live
        gmv, sessions = live.get(uid, (0.0, 0))
        people.append(
            {
                "userId": uid,
                "userName": name,
                "deptName": department,
                "primaryName": primary.target_name if primary else "",
                "partTimeNames": [item.target_name for item in parts if item.target_name],
                "primaryShare": float(primary.share_ratio) if primary else None,
                "partTimeSum": part_sum,
                "shareTotal": part_sum,
                "score": None,
                "comment": "",
                "overShare": over,
                "attributedGmv": round(gmv, 2) if has_live else None,
                "sessionCount": sessions if has_live else None,
                "workCount": works[uid] if uid in works else None,
            }
        )
    people.sort(key=lambda item: (item["deptName"], item["userName"], item["userId"]))
    return people, sorted(depts)


@router.get("/metrics/board")
def metrics_board(
    keyword: str = "",
    dept: str = "",
    shareStatus: str = "",
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    period = current_period()
    active_count = int(
        db.scalar(
            select(func.count())
            .select_from(EffRelation)
            .where(EffRelation.deleted == 0, EffRelation.tenant_id == tenant_id, EffRelation.status == "ACTIVE")
        )
        or 0
    )
    over_ratio_users = 0
    user_ids = db.scalars(
        select(EffRelation.user_id)
        .where(EffRelation.deleted == 0, EffRelation.tenant_id == tenant_id, EffRelation.status == "ACTIVE")
        .distinct()
    ).all()
    for uid in user_ids:
        # BR-213 / EFF-R1：主归属固定 100% 全额，不计入「分摊>100%」。只统计兼职合计超过 100% 的人。
        if part_time_sum(db, tenant_id, uid) > 100:
            over_ratio_users += 1
    covered = db.scalars(
        select(EffRelation.user_id)
        .where(
            EffRelation.deleted == 0,
            EffRelation.tenant_id == tenant_id,
            EffRelation.relation_type == "PRIMARY",
            EffRelation.status == "ACTIVE",
        )
        .distinct()
    ).all()
    covered_ids = {int(uid) for uid in covered}
    live, works = month_activity(db, tenant_id, period)
    gmv_total = sum(live[uid][0] for uid in covered_ids if uid in live)
    session_total = sum(live[uid][1] for uid in covered_ids if uid in live)
    work_total = sum(works[uid] for uid in covered_ids if uid in works)
    has_live = any(uid in live for uid in covered_ids)
    has_works = any(uid in works for uid in covered_ids)
    heads = len(covered_ids)
    people, depts = person_rows(db, tenant_id, period, keyword, dept, shareStatus)
    chart_bucket: dict[str, float] = {}
    chart_seen = False
    for person in people:
        if person["attributedGmv"] is None:
            continue
        chart_seen = True
        label = person["primaryName"] or person["deptName"] or "未归属"
        chart_bucket[label] = chart_bucket.get(label, 0.0) + float(person["attributedGmv"])
    chart = [
        {"label": label, "gmv": round(value, 2)}
        for label, value in sorted(chart_bucket.items(), key=lambda item: (-item[1], item[0]))
    ]
    return ok(
        {
            "periodMonth": period,
            "avgGmvPerCap": capita(gmv_total, heads, has_live),
            "avgSessionsPerMonth": capita(float(session_total), heads, has_live),
            "avgWorksPerMonth": capita(float(work_total), heads, has_works),
            "capacityUtilization": None,
            "activeRelationCount": active_count,
            "overShareUserCount": over_ratio_users,
            "people": people,
            "depts": depts,
            "chart": chart if chart_seen else [],
        }
    )
