"""培训 TRAIN-001 岗位资料库 · TRAIN-002 学习任务（W7-6~8）。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.core import utcnow
from app.corp import page_args, paged, tenant_of, user_names
from app.models import TrainMaterial, TrainMaterialCate, TrainTask, TrainTaskRecord, User

router = APIRouter(prefix="/train", tags=["train"])

BJ = timezone(timedelta(hours=8))
MATERIAL_TYPES = frozenset({"DOC", "VIDEO", "LINK"})
MATERIAL_STATUSES = frozenset({"DRAFT", "PUBLISHED", "OFFLINE"})
ASSIGN_SCOPES = frozenset({"BY_USER", "BY_POSITION"})
CONFIRM_TYPES = frozenset({"DURATION", "QUIZ"})
TASK_STATUSES = frozenset({"IN_PROGRESS", "FINISHED"})


class MaterialBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    title: str
    cateId: int
    materialType: str = "DOC"
    fileKey: str = ""
    linkUrl: str = ""
    positionCodes: list[str] = Field(default_factory=list)
    publish: bool = False


def iso(dt: datetime | None) -> str:
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=BJ)
    return dt.astimezone(BJ).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def ensure_default_cates(db: Session, tenant_id: int) -> None:
    count = db.scalar(
        select(func.count())
        .select_from(TrainMaterialCate)
        .where(TrainMaterialCate.deleted == 0, TrainMaterialCate.tenant_id == tenant_id)
    )
    if count:
        return
    seeds = [
        ("R6", "内容运营", ["SOP与规范", "案例库"]),
        ("R5", "直播运营", ["开播手册", "复盘模板"]),
        ("R2", "行政管理", ["制度汇编", "流程指引"]),
    ]
    order = 0
    for pos, pos_name, children in seeds:
        order += 1
        parent = TrainMaterialCate(
            cate_name=pos_name,
            parent_id=None,
            position_code=pos,
            sort_order=order,
            tenant_id=tenant_id,
        )
        db.add(parent)
        db.flush()
        for idx, child_name in enumerate(children, start=1):
            db.add(
                TrainMaterialCate(
                    cate_name=child_name,
                    parent_id=parent.id,
                    position_code=pos,
                    sort_order=idx,
                    tenant_id=tenant_id,
                )
            )
    db.flush()


def cate_material_count(db: Session, cate_id: int, tenant_id: int) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(TrainMaterial)
            .where(
                TrainMaterial.deleted == 0,
                TrainMaterial.tenant_id == tenant_id,
                TrainMaterial.cate_id == cate_id,
                TrainMaterial.status == "PUBLISHED",
            )
        )
        or 0
    )


def cate_tree_vo(db: Session, tenant_id: int) -> list[dict]:
    rows = list(
        db.scalars(
            select(TrainMaterialCate)
            .where(TrainMaterialCate.deleted == 0, TrainMaterialCate.tenant_id == tenant_id)
            .order_by(TrainMaterialCate.sort_order.asc(), TrainMaterialCate.id.asc())
        ).all()
    )
    by_parent: dict[int | None, list[TrainMaterialCate]] = {}
    for row in rows:
        by_parent.setdefault(row.parent_id, []).append(row)

    def build(node: TrainMaterialCate) -> dict:
        children = [build(item) for item in by_parent.get(node.id, [])]
        published = cate_material_count(db, node.id, tenant_id)
        for child in children:
            published += child.get("_published", 0)
        item = {
            "id": node.id,
            "cateName": node.cate_name,
            "parentId": node.parent_id,
            "positionCode": node.position_code or None,
            "materialCount": published if node.parent_id else published,
            "children": children,
        }
        item["_published"] = published
        return item

    roots = [build(item) for item in by_parent.get(None, [])]
    for root in roots:
        root.pop("_published", None)
        for child in root.get("children", []):
            child.pop("_published", None)
    return roots


def next_material_no(db: Session, tenant_id: int) -> str:
    day = datetime.now(BJ).strftime("%Y%m%d")
    prefix = f"MT{day}"
    count = db.scalar(
        select(func.count())
        .select_from(TrainMaterial)
        .where(
            TrainMaterial.deleted == 0,
            TrainMaterial.tenant_id == tenant_id,
            TrainMaterial.material_no.like(f"{prefix}%"),
        )
    )
    seq = int(count or 0) + 1
    return f"{prefix}{seq:03d}"


def material_vo(db: Session, row: TrainMaterial) -> dict:
    names = user_names(db, {row.uploader_user_id})
    codes = row.position_codes if isinstance(row.position_codes, list) else []
    return {
        "id": row.id,
        "materialNo": row.material_no,
        "title": row.title,
        "cateId": row.cate_id,
        "materialType": row.material_type,
        "fileKey": row.file_key,
        "linkUrl": row.link_url,
        "positionCodes": codes,
        "version": row.version,
        "status": row.status,
        "uploaderUserId": row.uploader_user_id,
        "uploaderName": names.get(row.uploader_user_id, ""),
        "updatedAt": iso(row.updated_at),
    }


@router.get("/material/cates")
def material_cates(
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    ensure_default_cates(db, tenant_id)
    return ok(cate_tree_vo(db, tenant_id))


@router.post("/material")
def create_material(
    body: MaterialBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    if not body.title.strip():
        return fail(1001, "title 必填")
    if body.materialType not in MATERIAL_TYPES:
        return fail(1001, "materialType 无效")
    tenant_id = tenant_of(actor)
    cate = db.get(TrainMaterialCate, body.cateId)
    if cate is None or cate.deleted or cate.tenant_id != tenant_id:
        return fail(1101, "分类不存在")
    if body.materialType == "LINK":
        if not body.linkUrl.strip():
            return fail(1001, "linkUrl 必填")
    elif not body.fileKey.strip():
        return fail(1001, "fileKey 必填")
    row = TrainMaterial(
        material_no=next_material_no(db, tenant_id),
        title=body.title.strip(),
        cate_id=body.cateId,
        material_type=body.materialType,
        file_key=body.fileKey.strip(),
        link_url=body.linkUrl.strip(),
        position_codes=body.positionCodes or ([cate.position_code] if cate.position_code else []),
        status="PUBLISHED" if body.publish else "DRAFT",
        uploader_user_id=actor.id,
        tenant_id=tenant_id,
    )
    db.add(row)
    db.flush()
    return ok(material_vo(db, row))


@router.get("/material/list")
def material_list(
    cateId: int | None = None,
    title: str | None = None,
    materialType: str | None = None,
    status: str | None = None,
    positionCode: str | None = None,
    pageNo: int = 1,
    pageSize: int = 10,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    page_no, size = page_args(pageNo, pageSize)
    stmt = select(TrainMaterial).where(
        TrainMaterial.deleted == 0,
        TrainMaterial.tenant_id == tenant_id,
    )
    if cateId:
        stmt = stmt.where(TrainMaterial.cate_id == cateId)
    if title:
        stmt = stmt.where(TrainMaterial.title.contains(title.strip()))
    if materialType:
        stmt = stmt.where(TrainMaterial.material_type == materialType)
    if status:
        if status not in MATERIAL_STATUSES:
            return fail(1001, "status 无效")
        stmt = stmt.where(TrainMaterial.status == status)
    if positionCode:
        code = positionCode.strip()
        stmt = stmt.where(func.json_contains(TrainMaterial.position_codes, f'"{code}"'))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = list(
        db.scalars(
            stmt.order_by(TrainMaterial.id.desc())
            .offset((page_no - 1) * size)
            .limit(size)
        ).all()
    )
    return paged([material_vo(db, row) for row in rows], total, page_no, size)


@router.delete("/material/{material_id}")
def offline_material(
    material_id: int,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    row = db.get(TrainMaterial, material_id)
    if row is None or row.deleted or row.tenant_id != tenant_id:
        return fail(1500, "资料不存在")
    row.status = "OFFLINE"
    row.updated_at = utcnow()
    db.flush()
    return ok(None)


class QuizItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    question: str
    options: list[str] = Field(default_factory=list)
    answerIndex: int = 0


class TaskBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    taskName: str
    materialIds: list[int] = Field(default_factory=list)
    assignScope: str = "BY_USER"
    assignTargetUserIds: list[int] | None = None
    assignTargetPositionCodes: list[str] | None = None
    deadline: str
    confirmType: str = "DURATION"
    quiz: list[QuizItem] | None = None
    passScore: int | None = None


def next_task_no(db: Session, tenant_id: int) -> str:
    day = datetime.now(BJ).strftime("%Y%m%d")
    prefix = f"TT{day}"
    count = db.scalar(
        select(func.count())
        .select_from(TrainTask)
        .where(
            TrainTask.deleted == 0,
            TrainTask.tenant_id == tenant_id,
            TrainTask.task_no.like(f"{prefix}%"),
        )
    )
    seq = int(count or 0) + 1
    return f"{prefix}{seq:03d}"


def parse_deadline(raw: str) -> datetime | None:
    text = raw.strip()
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
    return dt


def resolve_task_status(task: TrainTask) -> str:
    if task.status == "FINISHED":
        return "FINISHED"
    if task.deadline and utcnow() >= task.deadline.replace(tzinfo=None):
        return "FINISHED"
    return "IN_PROGRESS"


def finish_rate(db: Session, task_id: int, assigned: int) -> float:
    if assigned <= 0:
        return 0.0
    done = int(
        db.scalar(
            select(func.count())
            .select_from(TrainTaskRecord)
            .where(
                TrainTaskRecord.deleted == 0,
                TrainTaskRecord.task_id == task_id,
                TrainTaskRecord.confirm_status == 1,
            )
        )
        or 0
    )
    return round(done * 100.0 / assigned, 2)


def task_vo(db: Session, row: TrainTask) -> dict:
    material_ids = row.material_ids if isinstance(row.material_ids, list) else []
    return {
        "id": row.id,
        "taskNo": row.task_no,
        "taskName": row.task_name,
        "materialIds": material_ids,
        "assignScope": row.assign_scope,
        "assignedCount": row.assigned_count,
        "deadline": iso(row.deadline),
        "confirmType": row.confirm_type,
        "status": resolve_task_status(row),
        "createdAt": iso(row.created_at),
    }


def expand_assignees(db: Session, tenant_id: int, body: TaskBody) -> list[int] | dict:
    if body.assignScope not in ASSIGN_SCOPES:
        return fail(1001, "assignScope 无效")
    if body.assignScope == "BY_USER":
        ids = [uid for uid in (body.assignTargetUserIds or []) if uid]
        if not ids:
            return fail(1001, "assignTargetUserIds 必填")
        return ids
    codes = [c.strip() for c in (body.assignTargetPositionCodes or []) if c and c.strip()]
    if not codes:
        return fail(1001, "assignTargetPositionCodes 必填")
    users = list(
        db.scalars(
            select(User.id).where(
                User.deleted == 0,
                User.tenant_id == tenant_id,
                User.status == "ENABLED",
            )
        ).all()
    )
    if not users:
        return fail(1001, "岗位下无可用用户")
    return users


def validate_materials(db: Session, tenant_id: int, material_ids: list[int]) -> dict | None:
    if not material_ids:
        return fail(1001, "materialIds 必填")
    for mid in material_ids:
        mat = db.get(TrainMaterial, mid)
        if mat is None or mat.deleted or mat.tenant_id != tenant_id:
            return fail(1101, "资料不存在或未发布")
        if mat.status != "PUBLISHED":
            return fail(1101, "资料不存在或未发布")
    return None


@router.post("/task")
def create_task(
    body: TaskBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    if not body.taskName.strip():
        return fail(1001, "taskName 必填")
    if body.confirmType not in CONFIRM_TYPES:
        return fail(1001, "confirmType 无效")
    deadline = parse_deadline(body.deadline)
    if deadline is None:
        return fail(1001, "deadline 无效")
    if deadline.astimezone(timezone.utc) <= utcnow().astimezone(timezone.utc):
        return fail(1102, "截止时间早于当前时间")
    tenant_id = tenant_of(actor)
    err = validate_materials(db, tenant_id, body.materialIds)
    if err:
        return err
    if body.confirmType == "QUIZ":
        if not body.quiz:
            return fail(1001, "quiz 必填")
        if body.passScore is None:
            return fail(1001, "passScore 必填")
    assignees = expand_assignees(db, tenant_id, body)
    if isinstance(assignees, dict):
        return assignees
    unique_users = sorted(set(assignees))
    row = TrainTask(
        task_no=next_task_no(db, tenant_id),
        task_name=body.taskName.strip(),
        material_ids=body.materialIds,
        assign_scope=body.assignScope,
        assign_targets=unique_users if body.assignScope == "BY_USER" else body.assignTargetPositionCodes or [],
        deadline=deadline.replace(tzinfo=None),
        confirm_type=body.confirmType,
        quiz=[item.model_dump() for item in (body.quiz or [])],
        pass_score=body.passScore or 0,
        assigned_count=len(unique_users),
        status="IN_PROGRESS",
        creator_user_id=actor.id,
        tenant_id=tenant_id,
    )
    db.add(row)
    db.flush()
    for uid in unique_users:
        db.add(
            TrainTaskRecord(
                task_id=row.id,
                user_id=uid,
                tenant_id=tenant_id,
            )
        )
    db.flush()
    return ok(task_vo(db, row))


@router.get("/stat/summary")
def stat_summary(
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    rows = list(
        db.scalars(
            select(TrainTask).where(TrainTask.deleted == 0, TrainTask.tenant_id == tenant_id)
        ).all()
    )
    in_progress = 0
    rates: list[float] = []
    for row in rows:
        st = resolve_task_status(row)
        if st == "IN_PROGRESS":
            in_progress += 1
        rates.append(finish_rate(db, row.id, row.assigned_count))
    avg = round(sum(rates) / len(rates), 2) if rates else 0.0
    return ok(
        {
            "taskCount": len(rows),
            "inProgress": in_progress,
            "avgFinishRate": avg,
        }
    )


@router.get("/task/list")
def task_list(
    taskName: str | None = None,
    status: str | None = None,
    confirmType: str | None = None,
    pageNo: int = 1,
    pageSize: int = 10,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    page_no, size = page_args(pageNo, pageSize)
    stmt = select(TrainTask).where(TrainTask.deleted == 0, TrainTask.tenant_id == tenant_id)
    if taskName:
        stmt = stmt.where(TrainTask.task_name.contains(taskName.strip()))
    if confirmType:
        if confirmType not in CONFIRM_TYPES:
            return fail(1001, "confirmType 无效")
        stmt = stmt.where(TrainTask.confirm_type == confirmType)
    if status:
        if status not in TASK_STATUSES:
            return fail(1001, "status 无效")
        now = utcnow()
        if status == "FINISHED":
            stmt = stmt.where(
                (TrainTask.status == "FINISHED") | (TrainTask.deadline <= now)
            )
        else:
            stmt = stmt.where(
                TrainTask.status == "IN_PROGRESS",
                (TrainTask.deadline.is_(None)) | (TrainTask.deadline > now),
            )
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = list(
        db.scalars(
            stmt.order_by(TrainTask.id.desc()).offset((page_no - 1) * size).limit(size)
        ).all()
    )
    items = []
    for row in rows:
        vo = task_vo(db, row)
        vo["finishRate"] = finish_rate(db, row.id, row.assigned_count)
        vo["materialCount"] = len(vo["materialIds"])
        items.append(vo)
    return paged(items, total, page_no, size)
