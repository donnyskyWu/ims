"""培训 TRAIN-001 岗位资料库 · TRAIN-002 学习任务（W7-6~8）。"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.core import utcnow
from app.corp import page_args, paged, tenant_of, user_names
from app.bi_br212 import primary_dept_id
from app.models import (
    TrainMaterial,
    TrainMaterialCate,
    TrainMaterialVersion,
    TrainStatDaily,
    TrainTask,
    TrainTaskRecord,
    User,
)

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


def material_versions(db: Session, material_id: int, tenant_id: int) -> list[dict]:
    rows = list(
        db.scalars(
            select(TrainMaterialVersion)
            .where(
                TrainMaterialVersion.tenant_id == tenant_id,
                TrainMaterialVersion.material_id == material_id,
            )
            .order_by(TrainMaterialVersion.version.desc())
        ).all()
    )
    names = user_names(db, {row.editor_user_id for row in rows})
    return [
        {
            "version": row.version,
            "title": row.title,
            "materialType": row.material_type,
            "fileKey": row.file_key or None,
            "linkUrl": row.link_url or None,
            "editorName": names.get(row.editor_user_id, ""),
            "updatedAt": iso(row.updated_at),
        }
        for row in rows
    ]


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
        "versions": material_versions(db, row.id, row.tenant_id),
        "status": row.status,
        "uploaderUserId": row.uploader_user_id,
        "uploaderName": names.get(row.uploader_user_id, ""),
        "updatedAt": iso(row.updated_at),
    }


def is_http_url(value: str) -> bool:
    text = value.strip()
    if not text or any(ch.isspace() for ch in text):
        return False
    lowered = text.lower()
    for prefix in ("https://", "http://"):
        if lowered.startswith(prefix) and len(text) > len(prefix):
            return True
    return False


def validate_material_body(db: Session, tenant_id: int, body: MaterialBody):
    if not body.title.strip():
        return fail(1001, "title 必填")
    if body.materialType not in MATERIAL_TYPES:
        return fail(1001, "materialType 无效")
    cate = db.get(TrainMaterialCate, body.cateId)
    if cate is None or cate.deleted or cate.tenant_id != tenant_id:
        return fail(1101, "分类不存在")
    if body.materialType == "LINK":
        if not body.linkUrl.strip():
            return fail(1001, "linkUrl 必填")
        if not is_http_url(body.linkUrl):
            return fail(1001, "linkUrl 须为 http(s) 地址")
    elif not body.fileKey.strip():
        return fail(1001, "fileKey 必填")
    return cate


def archive_material(db: Session, row: TrainMaterial) -> None:
    db.add(
        TrainMaterialVersion(
            material_id=row.id,
            version=int(row.version or 1),
            title=row.title,
            cate_id=row.cate_id,
            material_type=row.material_type,
            file_key=row.file_key,
            link_url=row.link_url,
            position_codes=row.position_codes if isinstance(row.position_codes, list) else [],
            status=row.status,
            editor_user_id=row.uploader_user_id,
            tenant_id=row.tenant_id,
            updated_at=row.updated_at or utcnow(),
        )
    )


def apply_material_fields(row: TrainMaterial, body: MaterialBody, cate: TrainMaterialCate, actor: User) -> None:
    codes = body.positionCodes or ([cate.position_code] if cate.position_code else [])
    row.title = body.title.strip()
    row.cate_id = body.cateId
    row.material_type = body.materialType
    row.file_key = body.fileKey.strip()
    row.link_url = body.linkUrl.strip()
    row.position_codes = codes
    if body.publish:
        row.status = "PUBLISHED"
    elif row.status != "OFFLINE":
        row.status = "DRAFT"
    row.uploader_user_id = actor.id
    row.updated_at = utcnow()


def week_window(week_start: str | None) -> tuple[datetime, datetime, str] | None:
    text = (week_start or "").strip()
    if text:
        try:
            day = datetime.strptime(text, "%Y-%m-%d").date()
        except ValueError:
            return None
    else:
        today = datetime.now(BJ).date()
        day = today - timedelta(days=today.weekday())
    start_bj = datetime(day.year, day.month, day.day, tzinfo=BJ)
    start_utc = start_bj.astimezone(timezone.utc).replace(tzinfo=None)
    return start_utc, start_utc + timedelta(days=7), day.isoformat()


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
    tenant_id = tenant_of(actor)
    cate = validate_material_body(db, tenant_id, body)
    if not isinstance(cate, TrainMaterialCate):
        return cate
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


@router.get("/material/weekly-update-metrics")
def weekly_update_metrics(
    weekStart: str | None = None,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    """BR-101 每周更新率。分母是已发布资料，分子是本周更新过的。"""
    window = week_window(weekStart)
    if window is None:
        return fail(1001, "weekStart 无效")
    start, end, label = window
    tenant_id = tenant_of(actor)
    rows = list(
        db.scalars(
            select(TrainMaterial).where(
                TrainMaterial.deleted == 0,
                TrainMaterial.tenant_id == tenant_id,
                TrainMaterial.status == "PUBLISHED",
            )
        ).all()
    )
    names = user_names(db, {row.uploader_user_id for row in rows})
    updated = 0
    unupdated: list[dict] = []
    for row in rows:
        touched = row.updated_at or row.created_at
        if touched is not None and start <= touched < end:
            updated += 1
            continue
        unupdated.append(
            {
                "materialNo": row.material_no,
                "title": row.title,
                "lastUpdatedAt": iso(touched),
                "ownerName": names.get(row.uploader_user_id, ""),
            }
        )
    unupdated.sort(key=lambda item: (item["lastUpdatedAt"], item["materialNo"]))
    should = len(rows)
    rate = 100.0 if should == 0 else round(updated * 100.0 / should, 2)
    return ok(
        {
            "weekStart": label,
            "shouldUpdateCount": should,
            "updatedCount": updated,
            "weeklyUpdateRate": rate,
            "unupdatedList": unupdated,
        }
    )


@router.put("/material/{material_id}")
def update_material(
    material_id: int,
    body: MaterialBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    """TRN-M-R2：当前行升版本，旧内容写入快照且不再改。"""
    tenant_id = tenant_of(actor)
    row = db.get(TrainMaterial, material_id)
    if row is None or row.deleted or row.tenant_id != tenant_id:
        return fail(1101, "资料不存在")
    cate = validate_material_body(db, tenant_id, body)
    if not isinstance(cate, TrainMaterialCate):
        return cate
    archive_material(db, row)
    row.version = int(row.version or 1) + 1
    apply_material_fields(row, body, cate, actor)
    db.flush()
    return ok(material_vo(db, row))


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


def parse_date_range(raw: str | None) -> tuple[datetime | None, datetime | None]:
    if not raw:
        return None, None
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    if len(parts) != 2:
        return None, None
    try:
        start = datetime.strptime(parts[0], "%Y-%m-%d")
        end = datetime.strptime(parts[1], "%Y-%m-%d")
    except ValueError:
        return None, None
    end = end.replace(hour=23, minute=59, second=59)
    return start, end


def rate_pct(finished: int, assigned: int) -> float:
    if assigned <= 0:
        return 0.0
    return round(finished * 100.0 / assigned, 2)


def parse_bounded_range(raw: str | None) -> tuple[datetime | None, datetime | None, str | None]:
    """逗号分隔的 yyyy-MM-dd。空值表示不限；起大于止或格式不对返回错误文案。"""
    if raw is None or not str(raw).strip():
        return None, None, None
    parts = [part.strip() for part in str(raw).split(",") if part.strip()]
    if len(parts) != 2:
        return None, None, "日期范围无效"
    try:
        start = datetime.strptime(parts[0], "%Y-%m-%d")
        end_day = datetime.strptime(parts[1], "%Y-%m-%d")
    except ValueError:
        return None, None, "日期范围无效"
    if start > end_day:
        return None, None, "日期范围起大于止"
    end = end_day.replace(hour=23, minute=59, second=59)
    return start, end, None


def as_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    return value


def dept_label(dept_id: int) -> str:
    return f"部门#{dept_id}" if dept_id else "未分配"


def dept_of(db: Session, cache: dict[int, int], user_id: int, tenant_id: int) -> int:
    if user_id not in cache:
        cache[user_id] = primary_dept_id(db, user_id, tenant_id)
    return cache[user_id]


def stat_pairs(
    db: Session,
    tenant_id: int,
    start: datetime | None,
    end: datetime | None,
    user_id: int | None,
) -> list[tuple[TrainTaskRecord, TrainTask]]:
    """与 finish-rate 相同的取数：任务创建时间落在范围内的指派记录。user_id 非空时只看本人。"""
    stmt = (
        select(TrainTaskRecord, TrainTask)
        .join(TrainTask, TrainTask.id == TrainTaskRecord.task_id)
        .where(
            TrainTaskRecord.deleted == 0,
            TrainTaskRecord.tenant_id == tenant_id,
            TrainTask.deleted == 0,
        )
    )
    if start and end:
        stmt = stmt.where(TrainTask.created_at >= start, TrainTask.created_at <= end)
    if user_id is not None:
        stmt = stmt.where(TrainTaskRecord.user_id == user_id)
    return list(db.execute(stmt).all())


def scoped_user_id(actor: User) -> int | None:
    return None if actor.username == "admin" else actor.id


def duration_minutes(study_seconds: int) -> int:
    return max(0, int(study_seconds or 0)) // 60


def aggregate_dept_daily(
    db: Session, tenant_id: int, pairs: list[tuple[TrainTaskRecord, TrainTask]]
) -> list[dict]:
    cache: dict[int, int] = {}
    buckets: dict[tuple[str, int], dict] = {}
    for record, task in pairs:
        created = task.created_at or utcnow()
        stat_date = created.date().isoformat()
        dept_id = dept_of(db, cache, record.user_id, tenant_id)
        bucket = buckets.setdefault(
            (stat_date, dept_id),
            {
                "statDate": stat_date,
                "deptId": dept_id,
                "deptName": dept_label(dept_id),
                "assignedCount": 0,
                "finishedCount": 0,
                "studySeconds": 0,
            },
        )
        bucket["assignedCount"] += 1
        if record.confirm_status == 1:
            bucket["finishedCount"] += 1
        bucket["studySeconds"] += int(record.study_seconds or 0)
    items: list[dict] = []
    for bucket in buckets.values():
        assigned = bucket["assignedCount"]
        seconds = bucket.pop("studySeconds")
        bucket["finishRate"] = rate_pct(bucket["finishedCount"], assigned)
        bucket["avgDurationMinutes"] = int(round(seconds / 60 / assigned)) if assigned else 0
        items.append(bucket)
    items.sort(key=lambda item: (item["statDate"], item["deptName"]), reverse=True)
    items.sort(key=lambda item: item["deptName"])
    items.sort(key=lambda item: item["statDate"], reverse=True)
    return items


def mark_low_finish_alerts(items: list[dict]) -> None:
    """连续两个自然周完成率都低于 85% 时打标。推送仍由 ALERT 执行，这里只展示。"""
    weeks: dict[int, dict[date, list[int]]] = {}
    for item in items:
        stat_day = datetime.strptime(item["statDate"], "%Y-%m-%d").date()
        week_start = stat_day - timedelta(days=stat_day.weekday())
        cell = weeks.setdefault(int(item["deptId"]), {}).setdefault(week_start, [0, 0])
        cell[0] += int(item["assignedCount"])
        cell[1] += int(item["finishedCount"])
    alert_depts: set[int] = set()
    for dept_id, by_week in weeks.items():
        ordered = sorted(by_week)
        for index in range(1, len(ordered)):
            previous, current = ordered[index - 1], ordered[index]
            if (current - previous).days != 7:
                continue
            prev_assigned, prev_finished = by_week[previous]
            cur_assigned, cur_finished = by_week[current]
            if prev_assigned <= 0 or cur_assigned <= 0:
                continue
            if prev_finished * 100 / prev_assigned < 85 and cur_finished * 100 / cur_assigned < 85:
                alert_depts.add(dept_id)
                break
    for item in items:
        item["alertPushed"] = int(item["deptId"]) in alert_depts


def persist_dept_daily(
    db: Session,
    tenant_id: int,
    start: datetime | None,
    end: datetime | None,
    items: list[dict],
) -> None:
    stmt = select(TrainStatDaily).where(TrainStatDaily.tenant_id == tenant_id)
    if start and end:
        stmt = stmt.where(
            TrainStatDaily.stat_date >= start.date(),
            TrainStatDaily.stat_date <= end.date(),
        )
    existing = list(db.scalars(stmt).all())
    by_key = {(as_date(row.stat_date), row.dept_id): row for row in existing}
    seen: set[tuple] = set()
    for item in items:
        stat_day = datetime.strptime(item["statDate"], "%Y-%m-%d").date()
        key = (stat_day, int(item["deptId"]))
        seen.add(key)
        row = by_key.get(key)
        if row is None:
            row = TrainStatDaily(stat_date=stat_day, dept_id=int(item["deptId"]), tenant_id=tenant_id)
            db.add(row)
        row.dept_name = item["deptName"]
        row.assigned_count = int(item["assignedCount"])
        row.finished_count = int(item["finishedCount"])
        row.finish_rate = float(item["finishRate"])
        row.avg_duration_minutes = int(item["avgDurationMinutes"])
        row.deleted = 0
        row.updated_at = utcnow()
    for key, row in by_key.items():
        if key not in seen:
            db.delete(row)
    db.flush()


def read_dept_daily(
    db: Session, tenant_id: int, start: datetime | None, end: datetime | None
) -> list[dict]:
    stmt = select(TrainStatDaily).where(
        TrainStatDaily.deleted == 0,
        TrainStatDaily.tenant_id == tenant_id,
    )
    if start and end:
        stmt = stmt.where(
            TrainStatDaily.stat_date >= start.date(),
            TrainStatDaily.stat_date <= end.date(),
        )
    rows = list(
        db.scalars(
            stmt.order_by(TrainStatDaily.stat_date.desc(), TrainStatDaily.dept_id.asc())
        ).all()
    )
    items = []
    for row in rows:
        stat_value = row.stat_date
        stat_text = stat_value.strftime("%Y-%m-%d") if hasattr(stat_value, "strftime") else str(stat_value)[:10]
        items.append(
            {
                "statDate": stat_text,
                "deptId": row.dept_id,
                "deptName": row.dept_name,
                "assignedCount": row.assigned_count,
                "finishedCount": row.finished_count,
                "finishRate": float(row.finish_rate or 0),
                "avgDurationMinutes": int(row.avg_duration_minutes or 0),
            }
        )
    return items


def aggregate_rank(
    db: Session,
    tenant_id: int,
    pairs: list[tuple[TrainTaskRecord, TrainTask]],
    dimension: str,
    top_n: int,
) -> list[dict]:
    cache: dict[int, int] = {}
    groups: dict[int, dict] = {}
    if dimension == "PERSON":
        names = user_names(db, {record.user_id for record, _ in pairs})
        for record, _task in pairs:
            bucket = groups.setdefault(
                record.user_id,
                {
                    "userId": record.user_id,
                    "userName": names.get(record.user_id, ""),
                    "assigned": 0,
                    "finished": 0,
                    "seconds": 0,
                },
            )
            bucket["assigned"] += 1
            if record.confirm_status == 1:
                bucket["finished"] += 1
            bucket["seconds"] += int(record.study_seconds or 0)
        items = [
            {
                "userId": bucket["userId"],
                "userName": bucket["userName"],
                "totalDurationMinutes": duration_minutes(bucket["seconds"]),
                "finishRate": rate_pct(bucket["finished"], bucket["assigned"]),
            }
            for bucket in groups.values()
        ]
        items.sort(key=lambda item: (-item["totalDurationMinutes"], -item["finishRate"], item["userName"]))
    else:
        for record, _task in pairs:
            dept_id = dept_of(db, cache, record.user_id, tenant_id)
            bucket = groups.setdefault(
                dept_id,
                {"deptName": dept_label(dept_id), "assigned": 0, "finished": 0, "seconds": 0},
            )
            bucket["assigned"] += 1
            if record.confirm_status == 1:
                bucket["finished"] += 1
            bucket["seconds"] += int(record.study_seconds or 0)
        items = [
            {
                "deptName": bucket["deptName"],
                "totalDurationMinutes": duration_minutes(bucket["seconds"]),
                "finishRate": rate_pct(bucket["finished"], bucket["assigned"]),
            }
            for bucket in groups.values()
        ]
        items.sort(key=lambda item: (-item["totalDurationMinutes"], -item["finishRate"], item["deptName"]))
    ranked = items[:top_n]
    for index, item in enumerate(ranked, start=1):
        item["rank"] = index
    return ranked


def aggregate_heat(
    db: Session,
    pairs: list[tuple[TrainTaskRecord, TrainTask]],
    top_n: int,
) -> list[dict]:
    stats: dict[int, dict] = {}
    for record, task in pairs:
        material_ids = task.material_ids if isinstance(task.material_ids, list) else []
        progress_map = material_progress_map(record)
        studied: set[int] = set()
        for raw_id in material_ids:
            try:
                material_id = int(raw_id)
            except (TypeError, ValueError):
                continue
            if progress_map.get(material_id, 0) > 0 or record.confirm_status == 1:
                studied.add(material_id)
        if not studied and record.progress > 0:
            for raw_id in material_ids:
                try:
                    studied.add(int(raw_id))
                except (TypeError, ValueError):
                    continue
        if not studied:
            continue
        for material_id in studied:
            bucket = stats.setdefault(material_id, {"count": 0, "seconds": 0})
            bucket["count"] += 1
            bucket["seconds"] += int(record.study_seconds or 0)
    if not stats:
        return []
    materials = list(
        db.scalars(select(TrainMaterial).where(TrainMaterial.id.in_(list(stats.keys())))).all()
    )
    by_id = {row.id: row for row in materials if not row.deleted}
    items = []
    for material_id, bucket in stats.items():
        material = by_id.get(material_id)
        if material is None:
            continue
        count = bucket["count"]
        items.append(
            {
                "materialId": material_id,
                "materialNo": material.material_no,
                "title": material.title,
                "materialType": material.material_type,
                "studyCount": count,
                "avgDurationMinutes": int(round((bucket["seconds"] / 60) / count)) if count else 0,
            }
        )
    items.sort(key=lambda item: (-item["studyCount"], -item["avgDurationMinutes"], item["materialNo"]))
    return items[:top_n]


def deadline_text(dt: datetime | None) -> str:
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=BJ)
    else:
        dt = dt.astimezone(BJ)
    return dt.strftime("%Y-%m-%d %H:%M")


def overdue_day_count(deadline: datetime, now: datetime) -> int:
    days = (now.date() - deadline.date()).days
    return days if days >= 1 else 1


def clamp_top_n(top_n: int | None):
    if top_n is None:
        return 10, None
    if top_n <= 0 or top_n > 50:
        return None, fail(1001, "topN 无效")
    return top_n, None


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


def public_quiz(raw) -> list[dict]:
    """学员可见题干与选项。正确答案只留在服务端。"""
    items = raw if isinstance(raw, list) else []
    out: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        out.append(
            {
                "question": item.get("question") or "",
                "options": list(item.get("options") or []),
            }
        )
    return out


def normalize_quiz(quiz: list[QuizItem] | None, pass_score: int | None):
    """手工组卷：每题 1 分，及格分是需要答对的题数。"""
    if not quiz:
        return fail(1001, "quiz 必填")
    if pass_score is None:
        return fail(1001, "passScore 必填")
    if pass_score < 1 or pass_score > len(quiz):
        return fail(1001, "及格分须在 1 到题目数之间")
    normalized: list[dict] = []
    for item in quiz:
        question = (item.question or "").strip()
        if not question or len(question) > 256:
            return fail(1001, "题目必填且不超过 256 字")
        options = [opt.strip() for opt in item.options]
        if len(options) < 2 or any(not opt for opt in options):
            return fail(1001, "每题选项至少 2 项")
        if len(set(options)) != len(options):
            return fail(1001, "选项不能重复")
        if item.answerIndex < 0 or item.answerIndex >= len(options):
            return fail(1001, "答案下标超出选项")
        normalized.append(
            {
                "question": question,
                "options": options,
                "answerIndex": int(item.answerIndex),
            }
        )
    return normalized, int(pass_score)


def parse_quiz_answers(quiz: list, answers: list) -> dict[int, int] | None:
    found: dict[int, int] = {}
    for raw in answers:
        if not isinstance(raw, dict) or "questionIndex" not in raw or "answerIndex" not in raw:
            return None
        try:
            found[int(raw["questionIndex"])] = int(raw["answerIndex"])
        except (TypeError, ValueError):
            return None
    for idx, item in enumerate(quiz):
        options = item.get("options") if isinstance(item, dict) else None
        option_count = len(options) if isinstance(options, list) else 0
        given = found.get(idx)
        if given is None or given < 0 or given >= option_count:
            return None
    return found


def score_quiz(quiz: list, chosen: dict[int, int]) -> int:
    score = 0
    for idx, item in enumerate(quiz):
        if not isinstance(item, dict):
            continue
        try:
            expected = int(item.get("answerIndex", -1))
        except (TypeError, ValueError):
            continue
        if chosen.get(idx) == expected:
            score += 1
    return score


def task_vo(db: Session, row: TrainTask) -> dict:
    material_ids = row.material_ids if isinstance(row.material_ids, list) else []
    targets = row.assign_targets if isinstance(row.assign_targets, list) else []
    user_ids = [int(item) for item in targets if isinstance(item, int) or str(item).isdigit()]
    quiz = public_quiz(row.quiz)
    return {
        "id": row.id,
        "taskNo": row.task_no,
        "taskName": row.task_name,
        "materialIds": material_ids,
        "assignScope": row.assign_scope,
        "assignTargetUserIds": user_ids if row.assign_scope == "BY_USER" else [],
        "assignedCount": row.assigned_count,
        "deadline": iso(row.deadline),
        "confirmType": row.confirm_type,
        "passScore": int(row.pass_score or 0),
        "questionCount": len(quiz),
        "quiz": quiz,
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
        parsed = normalize_quiz(body.quiz, body.passScore)
        if not isinstance(parsed, tuple):
            return parsed
        quiz_rows, pass_score = parsed
    else:
        quiz_rows, pass_score = [], 0
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
        quiz=quiz_rows,
        pass_score=pass_score,
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


@router.put("/task/{task_id}")
def update_task(
    task_id: int,
    body: TaskBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    """截止前编辑进行中任务。已有学习记录不删除、不改进度。"""
    tenant_id = tenant_of(actor)
    row = db.get(TrainTask, task_id)
    if row is None or row.deleted or row.tenant_id != tenant_id:
        return fail(1500, "任务不存在")
    if resolve_task_status(row) != "IN_PROGRESS":
        return fail(1102, "已过截止时间，不能编辑")
    if not body.taskName.strip():
        return fail(1001, "taskName 必填")
    if body.confirmType not in CONFIRM_TYPES:
        return fail(1001, "confirmType 无效")
    deadline = parse_deadline(body.deadline)
    if deadline is None:
        return fail(1001, "deadline 无效")
    if deadline.astimezone(timezone.utc) <= utcnow().astimezone(timezone.utc):
        return fail(1102, "截止时间早于当前时间")
    err = validate_materials(db, tenant_id, body.materialIds)
    if err:
        return err
    if body.confirmType == "QUIZ":
        parsed = normalize_quiz(body.quiz, body.passScore)
        if not isinstance(parsed, tuple):
            return parsed
        quiz_rows, pass_score = parsed
    else:
        quiz_rows, pass_score = [], 0
    assignees = expand_assignees(db, tenant_id, body)
    if not isinstance(assignees, list):
        return assignees
    unique_users = sorted(set(assignees))
    row.task_name = body.taskName.strip()
    row.material_ids = body.materialIds
    row.assign_scope = body.assignScope
    row.assign_targets = unique_users if body.assignScope == "BY_USER" else body.assignTargetPositionCodes or []
    row.deadline = deadline.replace(tzinfo=None)
    row.confirm_type = body.confirmType
    row.quiz = quiz_rows
    row.pass_score = pass_score
    row.updated_at = utcnow()
    existing = list(
        db.scalars(
            select(TrainTaskRecord).where(
                TrainTaskRecord.deleted == 0,
                TrainTaskRecord.tenant_id == tenant_id,
                TrainTaskRecord.task_id == row.id,
            )
        ).all()
    )
    have = {item.user_id for item in existing}
    for uid in unique_users:
        if uid in have:
            continue
        db.add(TrainTaskRecord(task_id=row.id, user_id=uid, tenant_id=tenant_id))
        have.add(uid)
    row.assigned_count = len(have)
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


@router.get("/stat/finish-rate")
def stat_finish_rate(
    dateRange: str | None = None,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    """TRAIN-003 · BR-102 完成率（分母含未确认指派记录）。"""
    tenant_id = tenant_of(actor)
    start, end = parse_date_range(dateRange)
    rows = stat_pairs(db, tenant_id, start, end, scoped_user_id(actor))

    total_assigned = len(rows)
    total_finished = sum(1 for rec, _ in rows if rec.confirm_status == 1)
    total_finish_rate = rate_pct(total_finished, total_assigned)

    by_task: dict[int, dict] = {}
    by_dept: dict[int, dict] = {}
    by_person: dict[int, dict] = {}
    user_ids = {rec.user_id for rec, _ in rows}
    names = user_names(db, user_ids)

    for record, task in rows:
        finished = record.confirm_status == 1
        tid = task.id
        if tid not in by_task:
            by_task[tid] = {
                "taskNo": task.task_no,
                "taskName": task.task_name,
                "assignedCount": 0,
                "finishedCount": 0,
            }
        by_task[tid]["assignedCount"] += 1
        if finished:
            by_task[tid]["finishedCount"] += 1

        dept_id = primary_dept_id(db, record.user_id, tenant_id)
        if dept_id not in by_dept:
            by_dept[dept_id] = {
                "deptId": dept_id,
                "deptName": dept_label(dept_id),
                "assignedCount": 0,
                "finishedCount": 0,
            }
        by_dept[dept_id]["assignedCount"] += 1
        if finished:
            by_dept[dept_id]["finishedCount"] += 1

        uid = record.user_id
        if uid not in by_person:
            dept_name = by_dept.get(dept_id, {}).get("deptName", "")
            by_person[uid] = {
                "userId": uid,
                "userName": names.get(uid, ""),
                "deptName": dept_name,
                "assignedCount": 0,
                "finishedCount": 0,
            }
        by_person[uid]["assignedCount"] += 1
        if finished:
            by_person[uid]["finishedCount"] += 1

    task_items = []
    for item in by_task.values():
        item["finishRate"] = rate_pct(item["finishedCount"], item["assignedCount"])
        task_items.append(item)
    task_items.sort(key=lambda x: (-x["finishRate"], x["taskNo"]))

    dept_items = []
    for item in by_dept.values():
        item["finishRate"] = rate_pct(item["finishedCount"], item["assignedCount"])
        dept_items.append(item)
    dept_items.sort(key=lambda x: (-x["finishRate"], x["deptName"]))

    person_items = []
    for item in by_person.values():
        item["finishRate"] = rate_pct(item["finishedCount"], item["assignedCount"])
        person_items.append(item)
    person_items.sort(key=lambda x: (-x["finishRate"], x["userName"]))

    return ok(
        {
            "totalFinishRate": total_finish_rate,
            "byTask": task_items,
            "byDept": dept_items,
            "byPerson": person_items,
        }
    )


@router.get("/stat/dept")
def stat_dept(
    statDateRange: str | None = None,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    """部门日汇总。先按全租户重写 ims_train_stat_daily，管理员读这张表。"""
    start, end, error = parse_bounded_range(statDateRange)
    if error:
        return fail(1001, error)
    tenant_id = tenant_of(actor)
    all_pairs = stat_pairs(db, tenant_id, start, end, None)
    tenant_items = aggregate_dept_daily(db, tenant_id, all_pairs)
    persist_dept_daily(db, tenant_id, start, end, tenant_items)
    if actor.username == "admin":
        items = read_dept_daily(db, tenant_id, start, end)
    else:
        items = aggregate_dept_daily(db, tenant_id, stat_pairs(db, tenant_id, start, end, actor.id))
    mark_low_finish_alerts(items)
    return ok(items)


@router.get("/stat/rank")
def stat_rank(
    dimension: str | None = None,
    dateRange: str | None = None,
    topN: int | None = None,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    if dimension not in {"DEPT", "PERSON"}:
        return fail(1001, "dimension 无效")
    top_n, top_error = clamp_top_n(topN)
    if top_error is not None:
        return top_error
    start, end, error = parse_bounded_range(dateRange)
    if error:
        return fail(1001, error)
    tenant_id = tenant_of(actor)
    pairs = stat_pairs(db, tenant_id, start, end, scoped_user_id(actor))
    return ok(aggregate_rank(db, tenant_id, pairs, dimension, top_n))


@router.get("/stat/material-heat")
def stat_material_heat(
    dateRange: str | None = None,
    topN: int | None = None,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    top_n, top_error = clamp_top_n(topN)
    if top_error is not None:
        return top_error
    start, end, error = parse_bounded_range(dateRange)
    if error:
        return fail(1001, error)
    tenant_id = tenant_of(actor)
    pairs = stat_pairs(db, tenant_id, start, end, scoped_user_id(actor))
    return ok(aggregate_heat(db, pairs, top_n))


@router.get("/stat/overdue")
def stat_overdue(
    taskId: int | None = None,
    deptId: int | None = None,
    pageNo: int = 1,
    pageSize: int = 10,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    """未确认且截止时间已过。分母口径与完成率一致，逾期记录仍留在完成率里。"""
    tenant_id = tenant_of(actor)
    page_no, size = page_args(pageNo, pageSize)
    now = utcnow()
    stmt = (
        select(TrainTaskRecord, TrainTask)
        .join(TrainTask, TrainTask.id == TrainTaskRecord.task_id)
        .where(
            TrainTaskRecord.deleted == 0,
            TrainTaskRecord.tenant_id == tenant_id,
            TrainTask.deleted == 0,
            TrainTaskRecord.confirm_status == 0,
            TrainTask.deadline.isnot(None),
            TrainTask.deadline < now,
        )
    )
    if taskId:
        stmt = stmt.where(TrainTaskRecord.task_id == taskId)
    if scoped_user_id(actor) is not None:
        stmt = stmt.where(TrainTaskRecord.user_id == actor.id)
    rows = list(db.execute(stmt).all())
    cache: dict[int, int] = {}
    names = user_names(db, {record.user_id for record, _ in rows})
    items = []
    for record, task in rows:
        dept_id = dept_of(db, cache, record.user_id, tenant_id)
        if deptId is not None and dept_id != deptId:
            continue
        deadline = task.deadline
        items.append(
            {
                "taskId": task.id,
                "taskNo": task.task_no,
                "taskName": task.task_name,
                "userId": record.user_id,
                "userName": names.get(record.user_id, ""),
                "deptName": dept_label(dept_id),
                "deadline": deadline_text(deadline),
                "overdueDays": overdue_day_count(deadline, now) if deadline else 1,
                "progress": int(record.progress or 0),
            }
        )
    items.sort(key=lambda item: (-item["overdueDays"], item["taskNo"], item["userId"]))
    total = len(items)
    start_at = (page_no - 1) * size
    return paged(items[start_at : start_at + size], total, page_no, size)


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


def record_for_user(
    db: Session, tenant_id: int, task_id: int, user_id: int
) -> TrainTaskRecord | None:
    return db.scalar(
        select(TrainTaskRecord).where(
            TrainTaskRecord.deleted == 0,
            TrainTaskRecord.tenant_id == tenant_id,
            TrainTaskRecord.task_id == task_id,
            TrainTaskRecord.user_id == user_id,
        )
    )


def confirm_status_label(status: int) -> str:
    return "CONFIRMED" if status == 1 else "NOT_CONFIRMED"


def material_progress_map(record: TrainTaskRecord) -> dict[int, int]:
    raw = record.material_progress if isinstance(record.material_progress, dict) else {}
    out: dict[int, int] = {}
    for key, val in raw.items():
        try:
            out[int(key)] = int(val)
        except (TypeError, ValueError):
            continue
    return out


def recompute_overall_progress(task: TrainTask, mat_prog: dict[int, int]) -> int:
    material_ids = task.material_ids if isinstance(task.material_ids, list) else []
    if not material_ids:
        return 0
    values = [min(100, max(0, mat_prog.get(int(mid), 0))) for mid in material_ids]
    return int(sum(values) / len(values))


def progress_vo(
    db: Session,
    task: TrainTask,
    record: TrainTaskRecord,
    material_id: int | None = None,
) -> dict:
    mat_prog = material_progress_map(record)
    mid = material_id or (
        int(task.material_ids[0]) if isinstance(task.material_ids, list) and task.material_ids else 0
    )
    finished = iso(record.finished_at) if record.finished_at else None
    return {
        "taskId": task.id,
        "userId": record.user_id,
        "materialId": mid,
        "progress": record.progress,
        "materialProgress": {str(k): v for k, v in mat_prog.items()},
        "confirmStatus": confirm_status_label(record.confirm_status),
        "confirmScore": record.confirm_score,
        "startedAt": iso(record.created_at),
        "finishedAt": finished,
    }


def confirm_payload(task: TrainTask, record: TrainTaskRecord) -> dict:
    passed = record.confirm_status == 1
    data = {
        "confirmStatus": confirm_status_label(record.confirm_status),
        "confirmScore": record.confirm_score,
        "isPassed": passed,
        "finishedAt": iso(record.finished_at) if record.finished_at else None,
    }
    if task.confirm_type == "QUIZ":
        data["passScore"] = int(task.pass_score or 0)
    return data


class ProgressBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    materialId: int
    watchedSeconds: int | None = None
    currentPage: int | None = None
    totalPages: int | None = None
    heartbeatAt: str


class ConfirmBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    answers: list[dict] | None = None


@router.put("/task/{task_id}/progress")
def report_progress(
    task_id: int,
    body: ProgressBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    task = db.get(TrainTask, task_id)
    if task is None or task.deleted or task.tenant_id != tenant_id:
        return fail(1500, "任务不存在")
    material_ids = task.material_ids if isinstance(task.material_ids, list) else []
    if body.materialId not in material_ids:
        return fail(1101, "资料不存在或未发布")
    record = record_for_user(db, tenant_id, task_id, actor.id)
    if record is None:
        return fail(1105, "非被指派人无权上报进度")
    if record.confirm_status == 1:
        return ok(progress_vo(db, task, record, body.materialId))

    pct = 0
    if body.totalPages and body.totalPages > 0 and body.currentPage is not None:
        pct = min(100, int(body.currentPage * 100 / body.totalPages))
    elif body.watchedSeconds is not None and body.watchedSeconds >= 60:
        pct = 100
    elif body.watchedSeconds is not None and body.watchedSeconds > 0:
        pct = min(99, body.watchedSeconds)

    mat_prog = material_progress_map(record)
    mat_prog[body.materialId] = max(mat_prog.get(body.materialId, 0), pct)
    record.material_progress = {str(k): v for k, v in mat_prog.items()}
    record.progress = recompute_overall_progress(task, mat_prog)
    if body.watchedSeconds is not None and body.watchedSeconds > 0:
        record.study_seconds = max(int(record.study_seconds or 0), int(body.watchedSeconds))
    record.updated_at = utcnow()
    db.flush()
    return ok(progress_vo(db, task, record, body.materialId))


@router.post("/task/{task_id}/confirm")
def confirm_task(
    task_id: int,
    body: ConfirmBody | None = None,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    task = db.get(TrainTask, task_id)
    if task is None or task.deleted or task.tenant_id != tenant_id:
        return fail(1500, "任务不存在")
    record = record_for_user(db, tenant_id, task_id, actor.id)
    if record is None:
        return fail(1105, "非被指派人无权上报进度")
    if record.confirm_status == 1:
        return ok(confirm_payload(task, record))

    if task.confirm_type == "DURATION":
        material_ids = task.material_ids if isinstance(task.material_ids, list) else []
        mat_prog = material_progress_map(record)
        if not all(mat_prog.get(int(mid), 0) >= 100 for mid in material_ids):
            return fail(1104, "学时未达标")
    elif task.confirm_type == "QUIZ":
        quiz = task.quiz if isinstance(task.quiz, list) else []
        if not quiz:
            return fail(1104, "问卷未配置")
        chosen = parse_quiz_answers(quiz, (body.answers if body else None) or [])
        if chosen is None:
            return fail(1001, "问卷未答完")
        score = score_quiz(quiz, chosen)
        pass_line = int(task.pass_score or len(quiz))
        now = utcnow()
        record.confirm_score = score
        record.updated_at = now
        if score < pass_line:
            db.flush()
            return ok(confirm_payload(task, record))
    else:
        return fail(1001, "confirmType 无效")

    now = utcnow()
    record.confirm_status = 1
    record.progress = 100
    record.finished_at = now
    record.updated_at = now
    db.flush()
    return ok(confirm_payload(task, record))


@router.get("/task/records")
def task_records(
    taskId: int | None = None,
    userId: int | None = None,
    deptId: int | None = None,
    confirmStatus: str | None = None,
    overdue: bool | None = None,
    pageNo: int = 1,
    pageSize: int = 10,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    page_no, size = page_args(pageNo, pageSize)
    stmt = (
        select(TrainTaskRecord, TrainTask)
        .join(TrainTask, TrainTask.id == TrainTaskRecord.task_id)
        .where(
            TrainTaskRecord.deleted == 0,
            TrainTaskRecord.tenant_id == tenant_id,
            TrainTask.deleted == 0,
        )
    )
    if taskId:
        stmt = stmt.where(TrainTaskRecord.task_id == taskId)
    if userId:
        stmt = stmt.where(TrainTaskRecord.user_id == userId)
    elif not taskId:
        stmt = stmt.where(TrainTaskRecord.user_id == actor.id)
    if confirmStatus:
        if confirmStatus not in {"NOT_CONFIRMED", "CONFIRMED"}:
            return fail(1001, "confirmStatus 无效")
        want = 1 if confirmStatus == "CONFIRMED" else 0
        stmt = stmt.where(TrainTaskRecord.confirm_status == want)
    if overdue:
        now = utcnow()
        stmt = stmt.where(
            TrainTaskRecord.confirm_status == 0,
            TrainTask.deadline.isnot(None),
            TrainTask.deadline < now,
        )
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = list(
        db.execute(
            stmt.order_by(TrainTaskRecord.id.desc())
            .offset((page_no - 1) * size)
            .limit(size)
        ).all()
    )
    names = user_names(db, {rec.user_id for rec, _ in rows})
    items = []
    now = utcnow()
    for record, task in rows:
        vo = progress_vo(db, task, record)
        vo["taskNo"] = task.task_no
        vo["taskName"] = task.task_name
        vo["userName"] = names.get(record.user_id, "")
        vo["deptName"] = ""
        deadline = task.deadline
        vo["isOverdue"] = bool(
            record.confirm_status == 0 and deadline and deadline < now.replace(tzinfo=None)
        )
        items.append(vo)
    return paged(items, total, page_no, size)
