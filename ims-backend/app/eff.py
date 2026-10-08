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
from app.models import EffRelation, User

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


@router.get("/metrics/board")
def metrics_board(db: Session = Depends(db_session), actor: User = Depends(current_user)):
    tenant_id = tenant_of(actor)
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
        total = part_time_sum(db, tenant_id, uid)
        primary = active_primary(db, tenant_id, uid)
        if primary:
            total += float(primary.share_ratio or 0)
        if total > 100:
            over_ratio_users += 1
    return ok(
        {
            "avgGmvPerCap": 286000,
            "avgSessionsPerMonth": 4.8,
            "avgWorksPerMonth": 9.6,
            "capacityUtilization": 87,
            "activeRelationCount": active_count,
            "overShareUserCount": over_ratio_users,
        }
    )
