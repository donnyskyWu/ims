"""竞品分析提交与两级审核（COMP-001 / COMP-002）。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.comp_asset import asset_vo, assign_and_flush, enrich_metrics
from app.core import utcnow
from app.corp import check_enum, ops_db, page_args, paged, tenant_of
from app.models import CompAnalysis, CompAsset, Role, Todo, User, UserRole, WorkMessage
from app.ops_models import ExternalAccount
from app.scope import enabled_roles

router = APIRouter(prefix="/comp", tags=["comp-submit"])

BJ = timezone(timedelta(hours=8))
MONTH_RE_LEN = 7
DIMENSION_KEYS = ("sales", "gmv", "priceBand", "contentStrategy", "adStrategy")
PASS = "STORED"
BACK = "REJECTED"


class SubmitBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    periodMonth: str = ""
    compName: str = ""
    platform: str = ""
    homepageUrl: str = ""
    compAccountId: str = ""
    dataSource: str = ""
    dimensionData: dict = Field(default_factory=dict)
    conclusion: str = ""
    attachments: list = Field(default_factory=list)


class AuditBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    auditLevel: str
    conclusion: str
    rejectReason: str = ""
    rejectReasonTags: list[str] = Field(default_factory=list)


def fmt_bj(value: datetime | None) -> str:
    if value is None:
        return ""
    return (value + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M")


def match_key(name: str) -> str:
    return "".join((name or "").split()).casefold()


def display_name(name: str) -> str:
    return " ".join((name or "").split())


def period_ok(value: str) -> bool:
    text = (value or "").strip()
    if len(text) != MONTH_RE_LEN or text[4] != "-":
        return False
    year, month = text.split("-", 1)
    return year.isdigit() and month.isdigit() and 1 <= int(month) <= 12


def on_time(period_month: str, submitted: datetime) -> bool:
    """每月 25 日 22:00 截止，3 日内补交仍算按期。"""
    try:
        year, month = (int(part) for part in period_month.split("-", 1))
    except ValueError:
        return True
    local = submitted + timedelta(hours=8)
    deadline = datetime(year, month, 25, 22, 0) + timedelta(days=3)
    return local <= deadline


def role_tags_of(role: Role) -> set[str]:
    tags: set[str] = set()
    key = (role.role_key or "").strip().lower()
    position = (role.dingtalk_position or "").strip().upper()
    name = role.role_name or ""
    if key in {"sys:admin", "r1"} or key.endswith(":r1") or key.endswith("-r1"):
        tags.add("R1")
    for code in ("R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8", "R9", "R10"):
        low = code.lower()
        if key == low or key.endswith(":" + low) or key.endswith("-" + low) or position == code:
            tags.add(code)
    if "系统管理员" in name:
        tags.add("R1")
    if "运营总监" in name:
        tags.add("R4")
    if "审核" in name:
        tags.add("R8")
    if "短视频" in name:
        tags.add("R6")
    if "直播运营" in name and "总监" not in name:
        tags.add("R5")
    return tags


def actor_tags(db: Session, user: User) -> set[str]:
    tags: set[str] = set()
    if (user.username or "") == "admin":
        tags.add("R1")
    for role in enabled_roles(db, user):
        tags |= role_tags_of(role)
    return tags


def actor_caps(db: Session, user: User) -> dict:
    tags = actor_tags(db, user)
    return {
        "userId": user.id,
        "userName": user.nickname or user.username,
        "roles": sorted(tags),
        "canSubmit": bool(tags & {"R1", "R4", "R5", "R6"}),
        "canFirstAudit": "R8" in tags,
        "canFinalAudit": "R4" in tags,
    }


def status_view(row: CompAnalysis) -> tuple[str, str]:
    if row.submit_status == "REJECTED":
        return "REJECTED", "已退回"
    if row.submit_status == "STORED":
        return "STORED", "已入库"
    if row.submit_status == "DRAFT":
        return "DRAFT", "草稿"
    if (row.audit_stage or "FIRST") == "FINAL":
        return "PENDING_FINAL", "待终审"
    return "PENDING_FIRST", "待初审"


def next_analysis_no(db: Session, tenant_id: int) -> str:
    day = datetime.now(BJ).strftime("%Y%m%d")
    prefix = f"CA{day}"
    count = db.scalar(
        select(func.count())
        .select_from(CompAnalysis)
        .where(
            CompAnalysis.deleted == 0,
            CompAnalysis.tenant_id == tenant_id,
            CompAnalysis.analysis_no.like(f"{prefix}%"),
        )
    )
    return f"{prefix}{int(count or 0) + 1:03d}"


def analysis_vo(db: Session, row: CompAnalysis) -> dict:
    code, label = status_view(row)
    submitter = db.get(User, row.submitter_user_id)
    name = ""
    if submitter is not None:
        name = submitter.nickname or submitter.username
    return {
        "id": str(row.id),
        "analysisNo": row.analysis_no,
        "submitterUserId": row.submitter_user_id,
        "submitterName": name,
        "periodMonth": row.period_month,
        "compName": row.comp_name,
        "compNameStd": row.comp_name_std,
        "platform": row.platform,
        "homepageUrl": row.homepage_url,
        "compAccountId": row.comp_account_id,
        "dataSource": row.data_source,
        "dimensionData": row.dimension_data or {},
        "conclusion": row.conclusion,
        "attachments": row.attachments or [],
        "submitStatus": row.submit_status,
        "auditStage": row.audit_stage,
        "auditStatus": code,
        "auditStatusLabel": label,
        "rejectReason": row.reject_reason or "",
        "assetNo": row.asset_no or "",
        "isOnTime": bool(row.is_on_time),
        "submittedAt": fmt_bj(row.submitted_at),
        "createdAt": fmt_bj(row.created_at),
        "auditRounds": list(row.audit_rounds or []),
        "cardKind": "analysis",
    }


def users_with_tag(db: Session, tenant_id: int, code: str) -> list[User]:
    roles = list(
        db.scalars(
            select(Role).where(
                Role.deleted == 0,
                Role.status == "ENABLED",
                Role.tenant_id.in_((0, tenant_id)),
            )
        ).all()
    )
    role_ids = [role.id for role in roles if code in role_tags_of(role)]
    if not role_ids:
        return []
    user_ids = list(db.scalars(select(UserRole.user_id).where(UserRole.role_id.in_(role_ids))).all())
    if not user_ids:
        return []
    return list(
        db.scalars(
            select(User).where(User.id.in_(user_ids), User.deleted == 0, User.tenant_id == tenant_id)
        ).all()
    )


def close_open_todos(db: Session, analysis_id: int) -> None:
    rows = db.scalars(
        select(Todo).where(
            Todo.ref_type == "comp_analysis",
            Todo.ref_id == analysis_id,
            Todo.status == "PENDING",
        )
    ).all()
    for todo in rows:
        todo.status = "DONE"


def open_todo(db: Session, *, user_id: int, analysis: CompAnalysis, title: str, content: str, tenant_id: int) -> None:
    db.add(
        Todo(
            assignee_user_id=user_id,
            task_type="COMP_AUDIT",
            ref_type="comp_analysis",
            ref_id=analysis.id,
            title=title[:128],
            content=content[:512],
            status="PENDING",
            deadline=utcnow() + timedelta(hours=48),
            tenant_id=tenant_id,
        )
    )


def notify_user(db: Session, *, user_id: int, title: str, content: str, analysis_id: int, tenant_id: int) -> None:
    db.add(
        WorkMessage(
            user_id=user_id,
            title=title[:128],
            content=content[:512],
            channel="IN_APP",
            read_flag=0,
            source_module="COMP",
            ref_type="comp_analysis",
            ref_id=analysis_id,
            tenant_id=tenant_id,
        )
    )


def find_duplicate(db: Session, tenant_id: int, user_id: int, period: str, key: str, skip_id: int = 0) -> CompAnalysis | None:
    rows = db.scalars(
        select(CompAnalysis).where(
            CompAnalysis.deleted == 0,
            CompAnalysis.tenant_id == tenant_id,
            CompAnalysis.submitter_user_id == user_id,
            CompAnalysis.period_month == period,
            CompAnalysis.submit_status.in_(("SUBMITTED", "STORED", "DRAFT")),
        )
    ).all()
    for row in rows:
        if skip_id and row.id == skip_id:
            continue
        if match_key(row.comp_name_std or row.comp_name) == key:
            return row
    return None


def asset_by_key(db: Session, tenant_id: int, key: str, account_id: str) -> tuple[CompAsset | None, str]:
    rows = db.scalars(
        select(CompAsset).where(CompAsset.deleted == 0, CompAsset.tenant_id == tenant_id)
    ).all()
    account = (account_id or "").strip()
    for row in rows:
        info = dict(row.base_info or {})
        aliases = [str(item) for item in (info.get("aliasList") or [])]
        if account and (row.comp_account_id or "") == account:
            return row, "ACCOUNT_ID"
        if match_key(row.comp_name_std) == key:
            return row, "NAME_STD"
        if any(match_key(alias) == key for alias in aliases):
            return row, "ALIAS"
    return None, "NONE"


def merge_preview(db: Session, tenant_id: int, comp_name: str, account_id: str) -> dict:
    key = match_key(comp_name)
    asset, matched_by = asset_by_key(db, tenant_id, key, account_id)
    if asset is None:
        return {
            "matched": False,
            "matchedBy": "NONE",
            "similarity": 0,
        }
    return {
        "matched": True,
        "assetNo": asset.asset_no,
        "compNameStd": asset.comp_name_std,
        "latestVersion": asset.latest_version,
        "matchedBy": matched_by,
        "similarity": 100 if matched_by != "NONE" else 0,
    }


def dimension_filled(data: dict) -> bool:
    for key in DIMENSION_KEYS:
        value = data.get(key)
        if value is not None and str(value).strip():
            return True
    return False


ESSENTIALS_MSG = "来源、维度字段、结论均须明确"


def essentials_block(source: str, dimension: dict, conclusion: str):
    """提交时三要素不齐。来源单独缺失仍返回 1171，文案不含内部编号。"""
    if not (source or "").strip():
        return fail(1171, "数据来源必填（仅可采集公开数据）")
    if not dimension_filled(dimension or {}) or not (conclusion or "").strip():
        return fail(1174, ESSENTIALS_MSG)
    return None


def subscribe_monitor(ops: Session, tenant_id: int, asset: CompAsset, homepage: str) -> None:
    info = dict(asset.base_info or {})
    tomorrow = (datetime.now(BJ) + timedelta(days=1)).strftime("%Y-%m-%d")
    info["monitorSubscribed"] = True
    info["monitorEffectiveDate"] = tomorrow
    if homepage:
        info["homepageUrl"] = homepage
    asset.base_info = info
    ident = (asset.comp_account_id or f"ca-{asset.asset_no}")[:128]
    if not ident:
        return
    exists = ops.scalar(
        select(ExternalAccount.id).where(
            ExternalAccount.deleted == 0,
            ExternalAccount.tenant_id == tenant_id,
            ExternalAccount.platform_type == asset.platform,
            ExternalAccount.account_identifier == ident,
        )
    )
    if exists:
        return
    ops.add(
        ExternalAccount(
            account_identifier=ident,
            account_name=asset.comp_name_std[:128],
            platform_type=asset.platform,
            follower_count=int(info.get("followerCount") or 0),
            work_count=int(info.get("works30d") or 0),
            last_synced_at="",
            tenant_id=tenant_id,
        )
    )


def store_asset(
    db: Session,
    ops: Session,
    tenant_id: int,
    actor_id: int,
    row: CompAnalysis,
) -> CompAsset:
    key = match_key(row.comp_name)
    asset, _matched = asset_by_key(db, tenant_id, key, row.comp_account_id)
    version_entry = {
        "version": 1,
        "sourceAnalysisNo": row.analysis_no,
        "dimensionData": row.dimension_data or {},
        "conclusion": row.conclusion,
        "archivedAt": fmt_bj(utcnow()),
        "isValid": True,
    }
    if asset is None:
        asset = CompAsset(
            comp_name_std=row.comp_name,
            comp_account_id=(row.comp_account_id or "").strip(),
            platform=row.platform,
            base_info={
                "followerCount": 0,
                "works30d": 0,
                "engagementRate": 0,
                "featuredWorksIncluded": False,
                "homepageUrl": row.homepage_url,
                "dataSource": row.data_source,
                "dimensionData": row.dimension_data or {},
                "conclusion": row.conclusion,
                "versionTimeline": [version_entry],
                "aliasList": [],
            },
            latest_version=1,
            reference_count=0,
            status="TRACKING",
            created_by=actor_id,
            tenant_id=tenant_id,
        )
        assign_and_flush(db, asset)
    else:
        info = dict(asset.base_info or {})
        timeline = list(info.get("versionTimeline") or [])
        version_entry["version"] = int(asset.latest_version or 1) + 1
        timeline.append(version_entry)
        info["versionTimeline"] = timeline
        info["dimensionData"] = row.dimension_data or {}
        info["conclusion"] = row.conclusion
        info["dataSource"] = row.data_source
        if row.homepage_url:
            info["homepageUrl"] = row.homepage_url
        if row.comp_account_id and not asset.comp_account_id:
            asset.comp_account_id = row.comp_account_id
        asset.base_info = info
        asset.latest_version = version_entry["version"]
        asset.status = "TRACKING"
        asset.updated_at = utcnow()
    subscribe_monitor(ops, tenant_id, asset, row.homepage_url)
    return asset


def append_round(row: CompAnalysis, item: dict) -> None:
    rounds = list(row.audit_rounds or [])
    rounds.append(item)
    row.audit_rounds = rounds


def visible_stmt(db: Session, actor: User):
    tenant_id = tenant_of(actor)
    stmt = select(CompAnalysis).where(CompAnalysis.deleted == 0, CompAnalysis.tenant_id == tenant_id)
    tags = actor_tags(db, actor)
    if tags & {"R1", "R4", "R8", "R9", "R2", "R3"}:
        return stmt
    return stmt.where(CompAnalysis.submitter_user_id == actor.id)


@router.post("/analysis")
def submit_analysis(
    body: SubmitBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    caps = actor_caps(db, actor)
    if not caps["canSubmit"]:
        return fail(1008, "当前角色不能提交竞品分析")
    name = display_name(body.compName)
    if not name:
        return fail(1001, "必填项，请填写")
    if not period_ok(body.periodMonth):
        return fail(1001, "分析周期必填")
    if err := check_enum(db, "dict_platform_type", body.platform, True):
        return err
    source = (body.dataSource or "").strip()
    conclusion = (body.conclusion or "").strip()
    if blocked := essentials_block(source, dict(body.dimensionData or {}), conclusion):
        return blocked
    period = body.periodMonth.strip()
    dup = find_duplicate(db, tenant_id, actor.id, period, match_key(name))
    if dup is not None:
        return fail(1172, f"本月已提交过该竞品（{dup.analysis_no}）", {"analysisNo": dup.analysis_no})
    now = utcnow()
    row = CompAnalysis(
        analysis_no=next_analysis_no(db, tenant_id),
        submitter_user_id=actor.id,
        period_month=period,
        comp_name=name,
        comp_name_std=name,
        platform=body.platform.strip(),
        homepage_url=(body.homepageUrl or "").strip(),
        comp_account_id=(body.compAccountId or "").strip(),
        data_source=source,
        dimension_data=dict(body.dimensionData or {}),
        conclusion=conclusion,
        attachments=list(body.attachments or []),
        submit_status="SUBMITTED",
        audit_stage="FIRST",
        is_on_time=1 if on_time(period, now) else 0,
        audit_rounds=[],
        submitted_at=now,
        created_by=actor.id,
        tenant_id=tenant_id,
    )
    db.add(row)
    db.flush()
    for reviewer in users_with_tag(db, tenant_id, "R8"):
        if reviewer.id == actor.id:
            continue
        open_todo(
            db,
            user_id=reviewer.id,
            analysis=row,
            title=f"竞品初审 · {name}",
            content=f"{row.analysis_no} 待初审",
            tenant_id=tenant_id,
        )
    payload = analysis_vo(db, row)
    payload["mergePreview"] = merge_preview(db, tenant_id, name, row.comp_account_id)
    return ok(payload)


@router.get("/analysis/list")
def analysis_list(
    pageNo: int = 1,
    pageSize: int = 20,
    periodMonth: str = "",
    submitStatus: str = "",
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    stmt = visible_stmt(db, actor)
    if periodMonth.strip():
        stmt = stmt.where(CompAnalysis.period_month == periodMonth.strip())
    if submitStatus.strip():
        stmt = stmt.where(CompAnalysis.submit_status == submitStatus.strip())
    page_no, size = page_args(pageNo, pageSize)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(stmt.order_by(CompAnalysis.id.desc()).offset((page_no - 1) * size).limit(size)).all()
    payload = paged([analysis_vo(db, row) for row in rows], int(total or 0), page_no, size)
    payload["data"]["actor"] = actor_caps(db, actor)
    return payload


@router.get("/analysis/pending")
def analysis_pending(db: Session = Depends(db_session), actor: User = Depends(current_user)):
    period = datetime.now(BJ).strftime("%Y-%m")
    submitted = db.scalar(
        select(func.count())
        .select_from(CompAnalysis)
        .where(
            CompAnalysis.deleted == 0,
            CompAnalysis.tenant_id == tenant_of(actor),
            CompAnalysis.submitter_user_id == actor.id,
            CompAnalysis.period_month == period,
            CompAnalysis.submit_status.in_(("SUBMITTED", "STORED")),
        )
    )
    due = datetime.now(BJ).replace(day=25, hour=22, minute=0, second=0, microsecond=0)
    return ok(
        [
            {
                "periodMonth": period,
                "dueTime": due.strftime("%Y-%m-%d %H:%M"),
                "shouldCount": 1,
                "submittedCount": int(submitted or 0),
                "isNearDeadline": datetime.now(BJ) >= due - timedelta(days=3),
            }
        ]
    )


@router.get("/analysis/submit-rate")
def submit_rate(periodMonth: str = "", db: Session = Depends(db_session), actor: User = Depends(current_user)):
    tags = actor_tags(db, actor)
    if not (tags & {"R1", "R4", "R9"}):
        return fail(1008, "无提交率查看权限")
    return ok({"totalSubmitRate": 0, "byPerson": [], "target": 0.95, "periodMonth": periodMonth})


@router.get("/analysis/{analysis_no}")
def analysis_detail(analysis_no: str, db: Session = Depends(db_session), actor: User = Depends(current_user)):
    row = db.scalar(visible_stmt(db, actor).where(CompAnalysis.analysis_no == analysis_no))
    if row is None:
        return fail(1504, "资源不可用")
    payload = analysis_vo(db, row)
    payload["actor"] = actor_caps(db, actor)
    payload["mergePreview"] = merge_preview(db, tenant_of(actor), row.comp_name, row.comp_account_id)
    return ok(payload)


@router.put("/analysis/{analysis_no}")
def resubmit_analysis(
    analysis_no: str,
    body: SubmitBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    row = db.scalar(
        select(CompAnalysis).where(
            CompAnalysis.deleted == 0,
            CompAnalysis.tenant_id == tenant_id,
            CompAnalysis.analysis_no == analysis_no,
        )
    )
    if row is None:
        return fail(1504, "资源不可用")
    if row.submitter_user_id != actor.id:
        return fail(1008, "仅提交人可重新提交")
    if row.submit_status not in {"DRAFT", "REJECTED"}:
        return fail(1001, "仅草稿或已退回状态可修改")
    name = display_name(body.compName or row.comp_name)
    if not name:
        return fail(1001, "必填项，请填写")
    period = (body.periodMonth or row.period_month).strip()
    if not period_ok(period):
        return fail(1001, "分析周期必填")
    platform = (body.platform or row.platform).strip()
    if err := check_enum(db, "dict_platform_type", platform, True):
        return err
    source = (body.dataSource if body.dataSource is not None else row.data_source).strip()
    conclusion = (body.conclusion or row.conclusion).strip()
    dimension = dict(body.dimensionData) if body.dimensionData else dict(row.dimension_data or {})
    if blocked := essentials_block(source, dimension, conclusion):
        return blocked
    dup = find_duplicate(db, tenant_id, actor.id, period, match_key(name), skip_id=row.id)
    if dup is not None:
        return fail(1172, f"本月已提交过该竞品（{dup.analysis_no}）", {"analysisNo": dup.analysis_no})
    now = utcnow()
    row.comp_name = name
    row.comp_name_std = name
    row.period_month = period
    row.platform = platform
    row.homepage_url = (body.homepageUrl or row.homepage_url or "").strip()
    row.comp_account_id = (body.compAccountId if body.compAccountId is not None else row.comp_account_id).strip()
    row.data_source = source
    if body.dimensionData:
        row.dimension_data = dict(body.dimensionData)
    row.conclusion = conclusion
    row.submit_status = "SUBMITTED"
    row.audit_stage = "FIRST"
    row.submitted_at = now
    row.is_on_time = 1 if on_time(period, now) else 0
    row.updated_at = now
    append_round(
        row,
        {
            "round": len(list(row.audit_rounds or [])) + 1,
            "auditLevel": "RESUBMIT",
            "conclusion": "RESUBMITTED",
            "rejectReason": "",
            "rejectReasonTags": [],
            "auditorUserId": actor.id,
            "auditorName": actor.nickname or actor.username,
            "auditedAt": fmt_bj(now),
        },
    )
    row.reject_reason = ""
    close_open_todos(db, row.id)
    for reviewer in users_with_tag(db, tenant_id, "R8"):
        if reviewer.id == actor.id:
            continue
        open_todo(
            db,
            user_id=reviewer.id,
            analysis=row,
            title=f"竞品初审 · {name}",
            content=f"{row.analysis_no} 重新提交，待初审",
            tenant_id=tenant_id,
        )
    return ok(analysis_vo(db, row))


@router.get("/audit/queue")
def audit_queue(
    pageNo: int = 1,
    pageSize: int = 20,
    auditLevel: str = "FIRST",
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    level = (auditLevel or "FIRST").strip().upper()
    caps = actor_caps(db, actor)
    if level == "FIRST" and not caps["canFirstAudit"]:
        return fail(1176, "越级审核：初审队列仅内容审核员")
    if level == "FINAL" and not caps["canFinalAudit"]:
        return fail(1176, "越级审核：终审队列仅运营总监")
    if level not in {"FIRST", "FINAL"}:
        return fail(1001, "auditLevel 须为 FIRST 或 FINAL")
    stmt = select(CompAnalysis).where(
        CompAnalysis.deleted == 0,
        CompAnalysis.tenant_id == tenant_of(actor),
        CompAnalysis.submit_status == "SUBMITTED",
        CompAnalysis.audit_stage == level,
    )
    page_no, size = page_args(pageNo, pageSize)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(stmt.order_by(CompAnalysis.submitted_at.asc()).offset((page_no - 1) * size).limit(size)).all()
    items = []
    now = utcnow()
    for row in rows:
        item = analysis_vo(db, row)
        started = row.submitted_at or row.created_at or now
        waiting = max(int((now - started).total_seconds() // 3600), 0)
        item["waitingHours"] = waiting
        item["isTimeoutSla"] = level == "FIRST" and waiting > 48
        items.append(item)
    payload = paged(items, int(total or 0), page_no, size)
    payload["data"]["actor"] = caps
    return payload


@router.get("/audit/records")
def audit_records(
    pageNo: int = 1,
    pageSize: int = 20,
    analysisNo: str = "",
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    stmt = visible_stmt(db, actor)
    if analysisNo.strip():
        stmt = stmt.where(CompAnalysis.analysis_no == analysisNo.strip())
    rows = db.scalars(stmt.order_by(CompAnalysis.id.desc())).all()
    flat: list[dict] = []
    for row in rows:
        for item in list(row.audit_rounds or []):
            flat.append(
                {
                    "analysisNo": row.analysis_no,
                    "auditRound": item.get("round"),
                    "auditLevel": item.get("auditLevel"),
                    "conclusion": item.get("conclusion"),
                    "rejectReason": item.get("rejectReason") or "",
                    "auditorUserId": item.get("auditorUserId"),
                    "auditorName": item.get("auditorName") or "",
                    "auditedAt": item.get("auditedAt") or "",
                }
            )
    page_no, size = page_args(pageNo, pageSize)
    start = (page_no - 1) * size
    return paged(flat[start : start + size], len(flat), page_no, size)


@router.get("/audit/merge-preview")
def audit_merge_preview(
    compName: str = "",
    compAccountId: str = "",
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    if not display_name(compName) and not (compAccountId or "").strip():
        return fail(1001, "请填写竞品名称")
    return ok(merge_preview(db, tenant_of(actor), compName, compAccountId))


@router.put("/audit/{analysis_no}")
def audit_analysis(
    analysis_no: str,
    body: AuditBody,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    row = db.scalar(
        select(CompAnalysis).where(
            CompAnalysis.deleted == 0,
            CompAnalysis.tenant_id == tenant_id,
            CompAnalysis.analysis_no == analysis_no,
        )
    )
    if row is None:
        return fail(1504, "资源不可用")
    if row.submit_status != "SUBMITTED":
        return fail(1001, "当前状态不可审核")
    level = (body.auditLevel or "").strip().upper()
    conclusion = (body.conclusion or "").strip().upper()
    if level not in {"FIRST", "FINAL"} or conclusion not in {PASS, BACK}:
        return fail(1001, "审核参数不合法")
    caps = actor_caps(db, actor)
    if level == "FIRST" and not caps["canFirstAudit"]:
        return fail(1176, "越级审核：初审仅内容审核员")
    if level == "FINAL" and not caps["canFinalAudit"]:
        return fail(1176, "越级审核：终审仅运营总监")
    if level == "FINAL" and row.audit_stage != "FINAL":
        return fail(1176, "越级审核：初审未通过不可进终审")
    if level == "FIRST" and row.audit_stage != "FIRST":
        return fail(1176, "越级审核：该单已不在初审")
    if actor.id == row.submitter_user_id:
        return fail(1057, "1057 审核回避：不能审核自己提交的竞品")
    reason = (body.rejectReason or "").strip()
    if conclusion == BACK and not reason:
        return fail(1173, "1173 退回必须填写原因")
    if conclusion == PASS:
        if not (row.data_source or "").strip() or not (row.conclusion or "").strip() or not dimension_filled(row.dimension_data or {}):
            return fail(1174, "1174 三要素不齐：来源、维度字段、结论均须明确")
    if conclusion == BACK and int(row.reject_rounds or 0) >= 3:
        return fail(1175, "1175 该单已 3 轮退回，升级运营总监裁决")

    now = utcnow()
    round_no = len(list(row.audit_rounds or [])) + 1
    append_round(
        row,
        {
            "round": round_no,
            "auditLevel": level,
            "conclusion": conclusion,
            "rejectReason": reason if conclusion == BACK else "",
            "rejectReasonTags": list(body.rejectReasonTags or []),
            "auditorUserId": actor.id,
            "auditorName": actor.nickname or actor.username,
            "auditedAt": fmt_bj(now),
        },
    )
    close_open_todos(db, row.id)
    merge_info = None
    if conclusion == BACK:
        row.submit_status = "REJECTED"
        row.reject_reason = reason
        row.reject_rounds = int(row.reject_rounds or 0) + 1
        next_action = "BACK_TO_SUBMITTER"
        notify_user(
            db,
            user_id=row.submitter_user_id,
            title=f"竞品已退回 · {row.comp_name}",
            content=f"{row.analysis_no} 已退回，请补充后重新提交。原因：{reason}",
            analysis_id=row.id,
            tenant_id=tenant_id,
        )
        new_status = "REJECTED"
    elif level == "FIRST":
        row.submit_status = "SUBMITTED"
        row.audit_stage = "FINAL"
        row.reject_reason = ""
        next_action = "TO_FINAL"
        new_status = "SUBMITTED"
        for reviewer in users_with_tag(db, tenant_id, "R4"):
            if reviewer.id == row.submitter_user_id:
                continue
            open_todo(
                db,
                user_id=reviewer.id,
                analysis=row,
                title=f"竞品终审 · {row.comp_name}",
                content=f"{row.analysis_no} 待终审",
                tenant_id=tenant_id,
            )
    else:
        asset = store_asset(db, ops, tenant_id, actor.id, row)
        row.submit_status = "STORED"
        row.audit_stage = "DONE"
        row.asset_no = asset.asset_no
        row.reject_reason = ""
        next_action = "MERGE_STORED"
        new_status = "STORED"
        merge_info = {
            "assetNo": asset.asset_no,
            "compNameStd": asset.comp_name_std,
            "newVersion": asset.latest_version,
            "monitorSubscribed": True,
        }
        notify_user(
            db,
            user_id=row.submitter_user_id,
            title=f"竞品已入库 · {row.comp_name}",
            content=f"{row.analysis_no} 已归并入库 {asset.asset_no}，已订阅监控（次日生效）",
            analysis_id=row.id,
            tenant_id=tenant_id,
        )
    row.updated_at = now
    result = {
        "analysisNo": row.analysis_no,
        "newStatus": new_status,
        "auditStatusLabel": status_view(row)[1],
        "nextAction": next_action,
        "auditRounds": list(row.audit_rounds or []),
    }
    if merge_info:
        result["mergeInfo"] = merge_info
    return ok(result)
