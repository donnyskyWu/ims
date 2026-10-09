"""选题库（CONTENT-002）。

TOP-R1：立项必须同时给出计划发布日与启用中的 SOP，否则 1052。
TOP-R2：落选归档保留，评审动作 REVIVE 回到待评审（契约 2.2.4，无独立路径）。
待评审可编辑（契约 2.2.3）；已评审锁定。待评审可取消为 CANCELLED。
立项通过后创建内容项目并允许出任务；其余状态不可出任务。
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.content import iso, next_seq, tenant
from app.corp import page_args, paged
from app.models import ContentProject, ContentSop, ContentTopic, ContentTopicSeq, User

router = APIRouter(prefix="/content", tags=["content-topic"])

SOURCE_TYPES = {"HOTSPOT", "TALENT", "BRAND", "ORIGINAL"}
TOPIC_STATUSES = {"PENDING_REVIEW", "APPROVED_PROJECT", "REJECTED", "CANCELLED"}
REVIEW_ACTIONS = {"APPROVE_PROJECT", "REJECT", "REVIVE", "CANCEL"}
CONTENT_CHAIN = (
    ("DRAFT", "草稿"),
    ("IN_PROGRESS", "制作中"),
    ("PENDING_REVIEW", "待审核"),
    ("APPROVED", "已通过"),
    ("PUBLISHED", "已发布"),
    ("ARCHIVED", "已归档"),
)


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


def content_chain(status: str) -> list[dict]:
    known = {code for code, _label in CONTENT_CHAIN}
    steps = [{"status": code, "label": label, "current": code == status} for code, label in CONTENT_CHAIN]
    if status and status not in known:
        steps.append({"status": status, "label": status, "current": True})
    return steps


def topic_vo(
    row: ContentTopic,
    submitter: User | None,
    sop: ContentSop | None,
    project: ContentProject | None = None,
) -> dict:
    status = project.content_status if project else ""
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
        "contentProjectStatus": status,
        "contentStatusChain": content_chain(status) if project else [],
        "canCreateTask": row.topic_status == "APPROVED_PROJECT",
        "createdAt": iso(row.created_at),
    }


def hydrate(db: Session, rows: list[ContentTopic]) -> list[dict]:
    if not rows:
        return []
    user_ids = {row.submitter_user_id for row in rows}
    sop_ids = {row.sop_id for row in rows if row.sop_id}
    project_ids = {row.content_project_id for row in rows if row.content_project_id}
    users = {
        user.id: user
        for user in db.scalars(select(User).where(User.id.in_(user_ids))).all()
    }
    sops = {
        sop.id: sop
        for sop in db.scalars(select(ContentSop).where(ContentSop.id.in_(sop_ids))).all()
    } if sop_ids else {}
    projects = {
        project.id: project
        for project in db.scalars(select(ContentProject).where(ContentProject.id.in_(project_ids))).all()
    } if project_ids else {}
    return [
        topic_vo(
            row,
            users.get(row.submitter_user_id),
            sops.get(row.sop_id) if row.sop_id else None,
            projects.get(row.content_project_id) if row.content_project_id else None,
        )
        for row in rows
    ]


def topic_fields(body: TopicCreateBody, db: Session, actor: User):
    title = (body.title or "").strip()
    description = (body.description or "").strip()
    source = (body.sourceType or "").strip()
    if not title or len(title) > 256 or not description or len(description) > 2000 or source not in SOURCE_TYPES:
        return None, fail(1500, "参数校验失败")
    plan_date = (body.planPublishDate or "").strip()
    if plan_date and not valid_date(plan_date):
        return None, fail(1500, "参数校验失败")
    sop_id = body.sopId or None
    sop = None
    if sop_id is not None:
        sop = enabled_sop(db, sop_id, actor)
        if sop is None:
            return None, fail(1051, "SOP 不存在或未启用")
    return {
        "title": title,
        "description": description,
        "source": source,
        "plan_date": plan_date,
        "sop_id": sop_id,
        "sop": sop,
    }, None


@router.post("/topic")
def topic_create(body: TopicCreateBody, db: Session = Depends(db_session), actor: User = Depends(current_user)):
    fields, error = topic_fields(body, db, actor)
    if error is not None:
        return error
    tid = tenant(actor)
    row = ContentTopic(
        topic_no=next_seq(db, ContentTopicSeq, tid, "TP"),
        title=fields["title"],
        description=fields["description"],
        source_type=fields["source"],
        submitter_user_id=actor.id,
        plan_publish_date=fields["plan_date"],
        topic_status="PENDING_REVIEW",
        sop_id=fields["sop_id"],
        creator=actor.id,
        tenant_id=tid,
    )
    db.add(row)
    db.flush()
    submitter = db.get(User, actor.id)
    return ok(topic_vo(row, submitter, fields["sop"]))


@router.put("/topic/{topic_id}")
def topic_update(
    topic_id: int,
    body: TopicCreateBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    row = load_topic(db, topic_id, actor)
    if row is None or row.topic_status != "PENDING_REVIEW":
        return fail(1504, "选题不可编辑")
    fields, error = topic_fields(body, db, actor)
    if error is not None:
        return error
    row.title = fields["title"]
    row.description = fields["description"]
    row.source_type = fields["source"]
    row.plan_publish_date = fields["plan_date"]
    row.sop_id = fields["sop_id"]
    return ok(None)


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


@router.put("/topic/{topic_id}/review")
def topic_review(
    topic_id: int,
    body: TopicReviewBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    row = load_topic(db, topic_id, actor)
    if row is None:
        return fail(1504, "选题不可评审")
    action = (body.action or "").strip()
    if action not in REVIEW_ACTIONS:
        return fail(1500, "参数校验失败")
    if action == "REVIVE":
        if row.topic_status != "REJECTED":
            return fail(1504, "选题不可复活")
        row.topic_status = "PENDING_REVIEW"
        return ok(None)
    if action == "CANCEL":
        if row.topic_status != "PENDING_REVIEW":
            return fail(1504, "选题不可取消")
        opinion = (body.reviewOpinion or "").strip()
        if not opinion or len(opinion) > 512:
            return fail(1500, "参数校验失败")
        row.topic_status = "CANCELLED"
        row.review_opinion = opinion
        return ok(None)
    if row.topic_status != "PENDING_REVIEW":
        return fail(1504, "选题不可评审")
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
