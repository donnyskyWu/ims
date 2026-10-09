"""选题立项与排期甘特（CONTENT-002）。

TOP-R1：立项必须同时给出计划发布日与启用中的 SOP，否则 1052。
TOP-R3：排期甘特按计划发布日排布；同账号同日超量只提示，不阻断。
立项通过后创建内容项目并允许出任务；落选与待评审不可出任务。
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.content import iso, next_seq, tenant
from app.corp import page_args, paged
from app.models import ContentProject, ContentPublish, ContentSop, ContentTopic, ContentTopicSeq, User

router = APIRouter(prefix="/content", tags=["content-topic"])

SOURCE_TYPES = {"HOTSPOT", "TALENT", "BRAND", "ORIGINAL"}
TOPIC_STATUSES = {"PENDING_REVIEW", "APPROVED_PROJECT", "REJECTED", "CANCELLED"}


class TopicCreateBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    title: str
    description: str
    sourceType: str
    planPublishDate: str | None = None
    sopId: int | None = None


class TopicReviewBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    action: str
    planPublishDate: str | None = None
    sopId: int | None = None
    reviewOpinion: str | None = None


def valid_date(value: str) -> bool:
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return False
    return True


def load_topic(db: Session, topic_id: int, actor: User) -> ContentTopic | None:
    row = db.get(ContentTopic, topic_id)
    if row is None or row.deleted or (row.tenant_id or 0) != tenant(actor):
        return None
    return row


def enabled_sop(db: Session, sop_id: int, actor: User) -> ContentSop | None:
    sop = db.get(ContentSop, sop_id)
    if sop is None or sop.deleted or (sop.tenant_id or 0) != tenant(actor):
        return None
    if sop.status != "ENABLED":
        return None
    return sop


def topic_vo(row: ContentTopic, submitter: User | None, sop: ContentSop | None) -> dict:
    return {
        "id": row.id,
        "topicNo": row.topic_no,
        "title": row.title,
        "description": row.description or "",
        "sourceType": row.source_type,
        "submitterUserId": row.submitter_user_id,
        "submitterName": (submitter.nickname or submitter.username) if submitter else "",
        "planPublishDate": row.plan_publish_date or "",
        "topicStatus": row.topic_status,
        "sopId": row.sop_id,
        "sopName": sop.sop_name if sop else "",
        "reviewOpinion": row.review_opinion or "",
        "contentProjectId": row.content_project_id,
        "canCreateTask": row.topic_status == "APPROVED_PROJECT",
        "createdAt": iso(row.created_at),
    }


def hydrate(db: Session, rows: list[ContentTopic]) -> list[dict]:
    if not rows:
        return []
    user_ids = {row.submitter_user_id for row in rows}
    sop_ids = {row.sop_id for row in rows if row.sop_id}
    users = {
        user.id: user
        for user in db.scalars(select(User).where(User.id.in_(user_ids))).all()
    }
    sops = {
        sop.id: sop
        for sop in db.scalars(select(ContentSop).where(ContentSop.id.in_(sop_ids))).all()
    } if sop_ids else {}
    return [topic_vo(row, users.get(row.submitter_user_id), sops.get(row.sop_id) if row.sop_id else None) for row in rows]


@router.post("/topic")
def topic_create(body: TopicCreateBody, db: Session = Depends(db_session), actor: User = Depends(current_user)):
    title = (body.title or "").strip()
    description = (body.description or "").strip()
    source = (body.sourceType or "").strip()
    if not title or len(title) > 256 or not description or len(description) > 2000 or source not in SOURCE_TYPES:
        return fail(1500, "参数校验失败")
    plan_date = (body.planPublishDate or "").strip()
    if plan_date and not valid_date(plan_date):
        return fail(1500, "参数校验失败")
    sop_id = body.sopId or None
    if sop_id is not None and enabled_sop(db, sop_id, actor) is None:
        return fail(1051, "SOP 不存在或未启用")
    tid = tenant(actor)
    row = ContentTopic(
        topic_no=next_seq(db, ContentTopicSeq, tid, "TP"),
        title=title,
        description=description,
        source_type=source,
        submitter_user_id=actor.id,
        plan_publish_date=plan_date,
        topic_status="PENDING_REVIEW",
        sop_id=sop_id,
        creator=actor.id,
        tenant_id=tid,
    )
    db.add(row)
    db.flush()
    submitter = db.get(User, actor.id)
    sop = db.get(ContentSop, sop_id) if sop_id else None
    return ok(topic_vo(row, submitter, sop))


@router.get("/topic/list")
def topic_list(
    pageNo: int = 1,
    pageSize: int = 20,
    topicStatus: str | None = None,
    sourceType: str | None = None,
    submitterUserId: int | None = None,
    keyword: str | None = None,
    topicNo: str | None = None,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    page_no, size = page_args(pageNo, pageSize)
    status = (topicStatus or "").strip()
    source = (sourceType or "").strip()
    if status and status not in TOPIC_STATUSES:
        return fail(1500, "参数校验失败")
    if source and source not in SOURCE_TYPES:
        return fail(1500, "参数校验失败")
    stmt = select(ContentTopic).where(ContentTopic.deleted == 0, ContentTopic.tenant_id == tenant(actor))
    if status:
        stmt = stmt.where(ContentTopic.topic_status == status)
    if source:
        stmt = stmt.where(ContentTopic.source_type == source)
    if submitterUserId:
        stmt = stmt.where(ContentTopic.submitter_user_id == submitterUserId)
    if keyword and keyword.strip():
        stmt = stmt.where(ContentTopic.title.contains(keyword.strip()))
    if topicNo and topicNo.strip():
        stmt = stmt.where(ContentTopic.topic_no == topicNo.strip())
    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = db.scalars(stmt.order_by(ContentTopic.id.desc()).offset((page_no - 1) * size).limit(size)).all()
    return paged(hydrate(db, list(rows)), total, page_no, size)


def day_text(value: str) -> str | None:
    text = (value or "").strip()
    if len(text) >= 10:
        text = text[:10]
    if not valid_date(text):
        return None
    return text


def publish_accounts(db: Session, actor: User, project_ids: set[int]) -> dict[int, set[int]]:
    if not project_ids:
        return {}
    rows = db.scalars(
        select(ContentPublish).where(
            ContentPublish.deleted == 0,
            ContentPublish.tenant_id == tenant(actor),
            ContentPublish.content_project_id.in_(project_ids),
        )
    ).all()
    grouped: dict[int, set[int]] = {}
    for row in rows:
        grouped.setdefault(row.content_project_id, set()).add(row.account_id)
    return grouped


@router.get("/topic/gantt")
def topic_gantt(
    timeRange: list[str] = Query(default=[]),
    accountId: int | None = None,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    """排期甘特（CONTENT-002 · TOP-R3）。同账号同日多于 1 条时 conflictHint，不阻断。"""
    if len(timeRange) < 2:
        return fail(1500, "参数校验失败")
    start = day_text(timeRange[0])
    end = day_text(timeRange[1])
    if start is None or end is None or start > end:
        return fail(1500, "参数校验失败")
    rows = db.scalars(
        select(ContentTopic)
        .where(
            ContentTopic.deleted == 0,
            ContentTopic.tenant_id == tenant(actor),
            ContentTopic.plan_publish_date >= start,
            ContentTopic.plan_publish_date <= end,
            ContentTopic.plan_publish_date != "",
        )
        .order_by(ContentTopic.plan_publish_date.asc(), ContentTopic.id.asc())
    ).all()
    hydrated = hydrate(db, list(rows))
    project_ids = {row.content_project_id for row in rows if row.content_project_id}
    accounts_by_project = publish_accounts(db, actor, project_ids)
    packed: list[tuple[dict, set[int]]] = []
    counter: Counter[tuple[int, str]] = Counter()
    for row, vo in zip(rows, hydrated, strict=True):
        accounts = accounts_by_project.get(row.content_project_id, set()) if row.content_project_id else set()
        packed.append((vo, accounts))
        for account in accounts:
            counter[(account, vo["planPublishDate"])] += 1
    items = []
    for vo, accounts in packed:
        if accountId is not None and accountId not in accounts:
            continue
        keys = [accountId] if accountId is not None else sorted(accounts)
        overflow = any(counter[(account, vo["planPublishDate"])] > 1 for account in keys)
        sop_name = vo["sopName"] or None
        items.append(
            {
                "topicNo": vo["topicNo"],
                "title": vo["title"],
                "planPublishDate": vo["planPublishDate"],
                "topicStatus": vo["topicStatus"],
                "sopName": sop_name,
                "conflictHint": "同账号同日超量" if overflow else None,
            }
        )
    return ok({"items": items})


@router.put("/topic/{topic_id}/review")
def topic_review(
    topic_id: int,
    body: TopicReviewBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    row = load_topic(db, topic_id, actor)
    if row is None or row.topic_status != "PENDING_REVIEW":
        return fail(1504, "选题不可评审")
    action = (body.action or "").strip()
    if action == "REJECT":
        opinion = (body.reviewOpinion or "").strip()
        if not opinion or len(opinion) > 512:
            return fail(1500, "参数校验失败")
        row.topic_status = "REJECTED"
        row.review_opinion = opinion
        return ok(None)
    if action != "APPROVE_PROJECT":
        return fail(1500, "参数校验失败")
    plan_date = (body.planPublishDate or "").strip()
    sop_id = body.sopId or None
    if not plan_date or sop_id is None:
        return fail(1052, "选题立项缺少 SOP 或计划发布日")
    if not valid_date(plan_date):
        return fail(1500, "参数校验失败")
    opinion = (body.reviewOpinion or "").strip()
    if len(opinion) > 512:
        return fail(1500, "参数校验失败")
    sop = enabled_sop(db, sop_id, actor)
    if sop is None:
        return fail(1051, "SOP 不存在或未启用")
    project = ContentProject(
        title=row.title[:256],
        body=row.description or "",
        content_status="DRAFT",
        submitter_user_id=row.submitter_user_id,
        creator=actor.id,
        tenant_id=tenant(actor),
    )
    db.add(project)
    db.flush()
    row.topic_status = "APPROVED_PROJECT"
    row.plan_publish_date = plan_date
    row.sop_id = sop.id
    row.review_opinion = opinion
    row.content_project_id = project.id
    return ok(None)
