"""ASSET-003 登记关联校验：实名人 / 账号 / 场次是否存在、归属是否一致、状态是否允许。

VERIFY-R1：每周一（上海）全量，其余日期增量，同一天只跑一次。
VERIFY-R2：有异常的批次限期 3 个工作日，逾期把待办和站内信交给部门负责人。
"""

import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.asset_penetrate import ALLOWED_ACCOUNT_STATUS, ALLOWED_SESSION_STATUS
from app.core import utcnow
from app.corp import count_of, page_args, tenant_of
from app.models import (
    AssetBind,
    AssetHierarchy,
    AssetLedger,
    AssetVerifyBatch,
    AssetVerifyError,
    LiveSession,
    Role,
    Todo,
    User,
    UserDept,
    UserRole,
    WorkMessage,
)
from app.ops_db import ops_session
from app.ops_models import IpGroup, PlatformAccount, Realname

router = APIRouter()

VERIFY_TYPES = ("asset_account", "asset_person", "asset_session")
SCOPES = {"FULL", "INCREMENT"}
TASK_STATUS = {"PENDING_DISPATCH", "REPAIRING", "CLOSED"}
TRANSITIONS = {("PENDING_DISPATCH", "REPAIRING"), ("REPAIRING", "CLOSED")}


class VerifyRunBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    verifyTypes: list[str] = []
    scope: str = "FULL"


class VerifyTaskBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    taskStatus: str = ""
    ownerUserId: int | None = None
    remark: str = ""


def _clock(value) -> str:
    if value is None:
        return ""
    return value.strftime("%Y-%m-%d %H:%M:%S")


def _loads(text: str) -> list:
    try:
        data = json.loads(text or "[]")
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def _accounts(actor: User, ids: set[int]) -> dict[int, PlatformAccount]:
    if not ids:
        return {}
    ops = ops_session()
    try:
        rows = ops.scalars(
            select(PlatformAccount).where(PlatformAccount.deleted == 0, PlatformAccount.id.in_(ids))
        ).all()
        return {
            int(row.id): row
            for row in rows
            if (row.tenant_id or 0) == tenant_of(actor)
        }
    finally:
        ops.close()


def _persons(actor: User, ids: set[int]) -> dict[int, Realname]:
    if not ids:
        return {}
    ops = ops_session()
    try:
        rows = ops.scalars(select(Realname).where(Realname.deleted == 0, Realname.id.in_(ids))).all()
        return {int(row.id): row for row in rows if (row.tenant_id or 0) == tenant_of(actor)}
    finally:
        ops.close()


def shanghai_wall(value: datetime) -> datetime:
    """库存时间是去掉时区的 UTC。业务日按上海墙钟计算。"""
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value + timedelta(hours=8)


def schedule_date(value: datetime) -> str:
    return shanghai_wall(value).strftime("%Y-%m-%d")


def scheduled_scope(value: datetime) -> str:
    return "FULL" if shanghai_wall(value).weekday() == 0 else "INCREMENT"


def add_business_days(start: datetime, days: int) -> datetime:
    """从上海日期起跳过周六日，限期落在第 N 个工作日 23:59:59（再折回 UTC）。"""
    cursor = shanghai_wall(start).date()
    left = days
    while left > 0:
        cursor += timedelta(days=1)
        if cursor.weekday() < 5:
            left -= 1
    end_wall = datetime(cursor.year, cursor.month, cursor.day, 23, 59, 59)
    return end_wall - timedelta(hours=8)


def _assets(db: Session, actor: User, scope: str, now: datetime | None = None) -> list[AssetLedger]:
    clock = now or utcnow()
    stmt = select(AssetLedger).where(AssetLedger.deleted == 0, AssetLedger.tenant_id == tenant_of(actor))
    if scope == "INCREMENT":
        stmt = stmt.where(AssetLedger.updated_at >= clock - timedelta(days=1))
    return list(db.scalars(stmt.order_by(AssetLedger.id)).all())


def _issue(asset: AssetLedger, fields: list[str], description: str) -> dict:
    return {
        "recordId": asset.id,
        "assetCode": asset.asset_code,
        "fields": fields,
        "description": description,
    }


def _person_issues(asset: AssetLedger, hier: AssetHierarchy | None, bind: AssetBind | None, persons: dict, users: dict) -> list[dict]:
    issues = []
    person_id = int(hier.realname_id or 0) if hier is not None else 0
    if not person_id:
        issues.append(_issue(asset, ["realnameId"], "未关联实名人"))
    else:
        person = persons.get(person_id)
        if person is None:
            issues.append(_issue(asset, ["realnameId"], "实名人不存在"))
        elif (person.status or "") != "ENABLED":
            issues.append(_issue(asset, ["realnameId"], "实名人已停用"))
    owner_id = int(asset.owner_user_id or 0)
    if owner_id:
        owner = users.get(owner_id)
        if owner is None:
            issues.append(_issue(asset, ["ownerUserId"], "使用人不存在"))
        elif owner.status != "ENABLED" or owner.deleted:
            issues.append(_issue(asset, ["ownerUserId"], "使用人已停用"))
    if bind is not None and person_id and int(bind.verified_person_id or 0) not in (0, person_id):
        issues.append(_issue(asset, ["verifiedPersonId"], "账号实名人与资产实名人不一致"))
    return issues


def _account_issues(asset: AssetLedger, bind: AssetBind | None, accounts: dict) -> list[dict]:
    if bind is None or not int(bind.account_id or 0):
        return [_issue(asset, ["accountNo"], "未关联账号")]
    account = accounts.get(int(bind.account_id))
    if account is None:
        return [_issue(asset, ["accountNo"], "账号不存在")]
    if (account.status or "") not in ALLOWED_ACCOUNT_STATUS:
        return [_issue(asset, ["accountNo"], "账号已停用")]
    return []


def _session_issues(asset: AssetLedger, bind: AssetBind | None, sessions: dict) -> list[dict]:
    if bind is None or not int(bind.session_id or 0):
        return []
    session = sessions.get(int(bind.session_id))
    if session is None:
        return [_issue(asset, ["sessionCode"], "场次不存在")]
    status = session.session_status or ""
    if status not in ALLOWED_SESSION_STATUS:
        text = "场次已取消" if status == "CANCELLED" else "场次状态不允许"
        return [_issue(asset, ["sessionCode"], text)]
    if int(session.account_id or 0) != int(bind.account_id or 0):
        return [_issue(asset, ["sessionCode"], "场次不属于该账号")]
    return []


def _scan(db: Session, actor: User, kind: str, assets: list[AssetLedger]) -> list[dict]:
    if not assets:
        return []
    ids = [row.id for row in assets]
    hier_rows = db.scalars(
        select(AssetHierarchy).where(
            AssetHierarchy.deleted == 0,
            AssetHierarchy.tenant_id == tenant_of(actor),
            AssetHierarchy.asset_id.in_(ids),
        )
    ).all()
    hierarchies = {int(row.asset_id): row for row in hier_rows}
    bind_rows = db.scalars(
        select(AssetBind).where(
            AssetBind.deleted == 0,
            AssetBind.tenant_id == tenant_of(actor),
            AssetBind.asset_id.in_(ids),
            AssetBind.bind_status == "ACTIVE",
        )
    ).all()
    binds = {int(row.asset_id): row for row in bind_rows}
    account_ids = {int(row.account_id) for row in binds.values() if row.account_id}
    person_ids = {int(row.realname_id) for row in hierarchies.values() if row.realname_id}
    person_ids.update(int(row.verified_person_id) for row in binds.values() if row.verified_person_id)
    session_ids = [int(row.session_id) for row in binds.values() if row.session_id]
    sessions = {}
    if session_ids and kind == "asset_session":
        found = db.scalars(
            select(LiveSession).where(
                LiveSession.deleted == 0,
                LiveSession.tenant_id == tenant_of(actor),
                LiveSession.id.in_(session_ids),
            )
        ).all()
        sessions = {int(row.id): row for row in found}
    accounts = _accounts(actor, account_ids) if kind == "asset_account" else {}
    persons = _persons(actor, person_ids) if kind == "asset_person" else {}
    users = {}
    if kind == "asset_person":
        owner_ids = {int(row.owner_user_id) for row in assets if row.owner_user_id}
        if owner_ids:
            found_users = db.scalars(select(User).where(User.id.in_(owner_ids))).all()
            users = {int(row.id): row for row in found_users if (row.tenant_id or 0) == tenant_of(actor)}
    issues = []
    for asset in assets:
        hier = hierarchies.get(asset.id)
        bind = binds.get(asset.id)
        if kind == "asset_person":
            issues.extend(_person_issues(asset, hier, bind, persons, users))
        elif kind == "asset_account":
            issues.extend(_account_issues(asset, bind, accounts))
        else:
            issues.extend(_session_issues(asset, bind, sessions))
    return issues


def _session_totals(db: Session, actor: User, assets: list[AssetLedger]) -> int:
    if not assets:
        return 0
    rows = db.scalars(
        select(AssetBind.asset_id).where(
            AssetBind.deleted == 0,
            AssetBind.tenant_id == tenant_of(actor),
            AssetBind.bind_status == "ACTIVE",
            AssetBind.session_id > 0,
            AssetBind.asset_id.in_([item.id for item in assets]),
        )
    ).all()
    return len({int(item) for item in rows})


def _complete_rate(db: Session, actor: User, assets: list[AssetLedger]) -> float:
    if not assets:
        return 1.0
    ids = [row.id for row in assets]
    linked_person = set(
        db.scalars(
            select(AssetHierarchy.asset_id).where(
                AssetHierarchy.deleted == 0,
                AssetHierarchy.tenant_id == tenant_of(actor),
                AssetHierarchy.asset_id.in_(ids),
                AssetHierarchy.realname_id > 0,
            )
        ).all()
    )
    linked_account = set(
        db.scalars(
            select(AssetBind.asset_id).where(
                AssetBind.deleted == 0,
                AssetBind.tenant_id == tenant_of(actor),
                AssetBind.asset_id.in_(ids),
                AssetBind.bind_status == "ACTIVE",
                AssetBind.account_id > 0,
            )
        ).all()
    )
    complete = sum(1 for row in assets if row.id in linked_person and row.id in linked_account)
    return round(complete / len(assets), 4)


def _batch_vo(row: AssetVerifyBatch, names: dict[int, str]) -> dict:
    overdue = bool(
        row.task_status != "CLOSED"
        and row.deadline_at is not None
        and row.deadline_at < utcnow()
    )
    return {
        "id": row.id,
        "batchNo": row.batch_no,
        "runNo": row.run_no,
        "verifyType": row.verify_type,
        "scope": row.scope,
        "triggerMode": row.trigger_mode or "MANUAL",
        "scheduleDate": row.schedule_date or "",
        "totalCount": row.total_count,
        "errorCount": row.error_count,
        "errorDetailSummary": row.error_detail or "",
        "taskStatus": row.task_status,
        "ownerUserId": row.owner_user_id,
        "ownerName": names.get(row.owner_user_id or 0, "") if row.owner_user_id else "",
        "remark": row.remark or "",
        "deadlineAt": _clock(row.deadline_at),
        "overdue": overdue,
        "escalatedAt": _clock(row.escalated_at),
        "escalateUserId": row.escalate_user_id,
        "escalateUserName": names.get(row.escalate_user_id or 0, "") if row.escalate_user_id else "",
        "createdAt": _clock(row.created_at),
    }


def _names(db: Session, rows: list[AssetVerifyBatch]) -> dict[int, str]:
    ids = {row.owner_user_id for row in rows if row.owner_user_id}
    ids.update(row.escalate_user_id for row in rows if row.escalate_user_id)
    if not ids:
        return {}
    users = db.scalars(select(User).where(User.id.in_(ids))).all()
    return {int(user.id): user.nickname or user.username for user in users}


def execute_verify(
    db: Session,
    actor: User,
    kinds: list[str],
    scope: str,
    *,
    trigger_mode: str = "MANUAL",
    schedule_date_value: str = "",
    now: datetime | None = None,
    run_no: str | None = None,
) -> dict:
    clock = now or utcnow()
    assets = _assets(db, actor, scope, clock)
    complete = _complete_rate(db, actor, assets)
    stamped = clock
    run_no = run_no or ("AV" + stamped.strftime("%Y%m%d%H%M%S%f"))
    batches = []
    error_asset_ids: set[int] = set()
    pending_errors: list[tuple[AssetVerifyBatch, list[dict]]] = []
    session_totals = _session_totals(db, actor, assets)
    for kind in kinds:
        issues = _scan(db, actor, kind, assets)
        error_asset_ids.update(int(item["recordId"]) for item in issues)
        total = session_totals if kind == "asset_session" else len(assets)
        batch_no = run_no if len(kinds) == 1 else f"{run_no}:{kind}"
        summary = "；".join(f"{item['assetCode']} {item['description']}" for item in issues[:8])
        batch = AssetVerifyBatch(
            batch_no=batch_no,
            run_no=run_no,
            verify_type=kind,
            scope=scope,
            total_count=total,
            error_count=len(issues),
            complete_rate=complete,
            consistency_rate=1.0,
            error_detail=summary[:1000],
            task_status="PENDING_DISPATCH" if issues else "CLOSED",
            deadline_at=add_business_days(stamped, 3) if issues else None,
            trigger_mode=trigger_mode,
            schedule_date=schedule_date_value,
            deleted=0,
            tenant_id=tenant_of(actor),
            created_at=stamped,
        )
        db.add(batch)
        batches.append(batch)
        pending_errors.append((batch, issues))
    checked = len(assets)
    consistency = 1.0 if not checked else round(1 - (len(error_asset_ids) / checked), 4)
    for batch, _issues in pending_errors:
        batch.consistency_rate = consistency
    db.flush()
    for batch, issues in pending_errors:
        for item in issues:
            db.add(
                AssetVerifyError(
                    batch_id=batch.id,
                    batch_no=batch.batch_no,
                    run_no=run_no,
                    record_id=item["recordId"],
                    record_type=batch.verify_type,
                    asset_code=item["assetCode"],
                    inconsistent_fields=json.dumps(item["fields"], ensure_ascii=False),
                    description=item["description"],
                    deleted=0,
                    tenant_id=tenant_of(actor),
                    created_at=stamped,
                )
            )
    db.flush()
    names = _names(db, batches)
    return {
        "batchNo": run_no,
        "triggeredAt": _clock(stamped),
        "errorCount": len(error_asset_ids),
        "relationCompleteRate": complete,
        "consistencyRate": consistency,
        "batches": [_batch_vo(row, names) for row in batches],
    }


@router.post("/asset/verify/run")
def verify_run(
    body: VerifyRunBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    kinds = []
    for item in body.verifyTypes or []:
        kind = (item or "").strip()
        if kind and kind not in kinds:
            kinds.append(kind)
    if not kinds:
        return fail(1001, "校验类型必填")
    if any(kind not in VERIFY_TYPES for kind in kinds):
        return fail(1001, "校验类型不正确")
    scope = (body.scope or "FULL").strip().upper()
    if scope not in SCOPES:
        return fail(1001, "校验范围不正确")
    return ok(execute_verify(db, actor, kinds, scope, trigger_mode="MANUAL"))


def _schedule_actor(db: Session, tenant_id: int) -> User | None:
    admin = db.scalar(
        select(User).where(
            User.username == "admin",
            User.deleted == 0,
            User.status == "ENABLED",
            User.tenant_id == tenant_id,
        )
    )
    if admin is not None:
        return admin
    return db.scalars(
        select(User)
        .where(User.deleted == 0, User.status == "ENABLED", User.tenant_id == tenant_id)
        .order_by(User.id)
        .limit(1)
    ).first()


def run_scheduled_verify(db: Session, now: datetime | None = None) -> list[str]:
    """VERIFY-R1。周一上海全量，其余日期只扫近 24 小时有变更的台账。同一天不重复。"""
    clock = now or utcnow()
    day = schedule_date(clock)
    scope = scheduled_scope(clock)
    tenant_ids = {
        int(item or 0)
        for item in db.scalars(select(AssetLedger.tenant_id).where(AssetLedger.deleted == 0).distinct()).all()
    }
    created: list[str] = []
    for tenant_id in sorted(tenant_ids):
        existing = db.scalar(
            select(AssetVerifyBatch.run_no).where(
                AssetVerifyBatch.deleted == 0,
                AssetVerifyBatch.tenant_id == tenant_id,
                AssetVerifyBatch.trigger_mode == "SCHEDULE",
                AssetVerifyBatch.schedule_date == day,
            )
        )
        if existing:
            created.append(str(existing))
            continue
        actor = _schedule_actor(db, tenant_id)
        if actor is None:
            continue
        prefix = "F" if scope == "FULL" else "I"
        run_no = f"AVS{day.replace('-', '')}{prefix}{tenant_id}"
        try:
            with db.begin_nested():
                payload = execute_verify(
                    db,
                    actor,
                    list(VERIFY_TYPES),
                    scope,
                    trigger_mode="SCHEDULE",
                    schedule_date_value=day,
                    now=clock,
                    run_no=run_no,
                )
            created.append(str(payload["batchNo"]))
        except IntegrityError:
            created.append(run_no)
    return created


def _enabled_user(db: Session, user_id: int, tenant_id: int) -> User | None:
    user = db.get(User, user_id)
    if user is None or user.deleted or user.status != "ENABLED":
        return None
    if (user.tenant_id or 0) != tenant_id:
        return None
    return user


def _dept_leader(db: Session, batch: AssetVerifyBatch) -> User | None:
    tenant_id = int(batch.tenant_id or 0)
    asset_ids = list(
        db.scalars(
            select(AssetVerifyError.record_id).where(
                AssetVerifyError.deleted == 0,
                AssetVerifyError.batch_id == batch.id,
            )
        ).all()
    )
    owner_ids = []
    if asset_ids:
        owner_ids = [
            int(item)
            for item in db.scalars(
                select(AssetLedger.owner_user_id).where(
                    AssetLedger.id.in_(asset_ids),
                    AssetLedger.owner_user_id.is_not(None),
                )
            ).all()
            if item
        ]
    dept_ids = []
    if owner_ids:
        dept_ids = [
            int(item)
            for item in db.scalars(select(UserDept.dept_id).where(UserDept.user_id.in_(owner_ids))).all()
        ]
    if dept_ids:
        ops = ops_session()
        try:
            groups = ops.scalars(
                select(IpGroup).where(
                    IpGroup.deleted == 0,
                    IpGroup.status == "ENABLED",
                    IpGroup.ding_dept_id.in_(dept_ids),
                    IpGroup.leader_user_id.is_not(None),
                    IpGroup.tenant_id == tenant_id,
                )
            ).all()
        finally:
            ops.close()
        for group in groups:
            leader = _enabled_user(db, int(group.leader_user_id or 0), tenant_id)
            if leader is not None:
                return leader
    roles = db.scalars(select(Role).where(Role.deleted == 0, Role.status == "ENABLED", Role.tenant_id == tenant_id)).all()
    role_ids = [int(role.id) for role in roles if "行政" in (role.role_name or "") or role.role_key == "R2"]
    if role_ids:
        link = db.scalar(select(UserRole).where(UserRole.role_id.in_(role_ids), UserRole.tenant_id == tenant_id))
        if link is not None:
            affairs = _enabled_user(db, int(link.user_id), tenant_id)
            if affairs is not None:
                return affairs
    return _schedule_actor(db, tenant_id)


def escalate_overdue(db: Session, now: datetime | None = None) -> int:
    """VERIFY-R2。未闭环且已过 3 个工作日限期的批次，待办和站内信交给部门负责人。

    同时记一条钉钉通道消息作为本地桩，不调用钉钉开放平台。不重复升级。
    """
    clock = now or utcnow()
    rows = list(
        db.scalars(
            select(AssetVerifyBatch).where(
                AssetVerifyBatch.deleted == 0,
                AssetVerifyBatch.task_status != "CLOSED",
                AssetVerifyBatch.escalated_at.is_(None),
                AssetVerifyBatch.deadline_at.is_not(None),
                AssetVerifyBatch.deadline_at < clock,
            )
        ).all()
    )
    sent = 0
    for row in rows:
        leader = _dept_leader(db, row)
        if leader is None:
            continue
        title = f"资产校验逾期：{row.batch_no}"[:128]
        content = f"关联校验超过 3 个工作日未闭环，已升级部门负责人。批次 {row.batch_no}"[:512]
        stub = f"{content} 钉钉未外发。"[:512]
        db.add(
            Todo(
                assignee_user_id=leader.id,
                task_type="asset_verify_overdue",
                ref_type="asset_verify",
                ref_id=row.id,
                title=title,
                content=content,
                status="PENDING",
                deadline=row.deadline_at,
                tenant_id=row.tenant_id or 0,
            )
        )
        db.add(
            WorkMessage(
                user_id=leader.id,
                title=title,
                content=content,
                channel="IN_APP",
                read_flag=0,
                source_module="ASSET",
                ref_type="asset_verify",
                ref_id=row.id,
                tenant_id=row.tenant_id or 0,
            )
        )
        db.add(
            WorkMessage(
                user_id=leader.id,
                title=title,
                content=stub,
                channel="DINGTALK",
                read_flag=0,
                source_module="ASSET",
                ref_type="asset_verify",
                ref_id=row.id,
                tenant_id=row.tenant_id or 0,
            )
        )
        row.escalated_at = clock
        row.escalate_user_id = leader.id
        sent += 1
    if sent:
        db.flush()
    return sent


def _batch_stmt(db: Session, actor: User):
    return select(AssetVerifyBatch).where(
        AssetVerifyBatch.deleted == 0,
        AssetVerifyBatch.tenant_id == tenant_of(actor),
    )


@router.get("/asset/verify/batches")
def verify_batches(
    pageNo: int = 1,
    pageSize: int = 10,
    batchNo: str = "",
    verifyType: str = "",
    taskStatus: str = "",
    timeFrom: str = "",
    timeTo: str = "",
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    run_scheduled_verify(db)
    escalate_overdue(db)
    number, size = page_args(pageNo, pageSize)
    stmt = _batch_stmt(db, actor)
    text = (batchNo or "").strip()
    if text:
        stmt = stmt.where((AssetVerifyBatch.batch_no == text) | (AssetVerifyBatch.run_no == text))
    if verifyType:
        stmt = stmt.where(AssetVerifyBatch.verify_type == verifyType.strip())
    if taskStatus:
        stmt = stmt.where(AssetVerifyBatch.task_status == taskStatus.strip())
    if timeFrom:
        stmt = stmt.where(AssetVerifyBatch.created_at >= timeFrom.strip())
    if timeTo:
        stmt = stmt.where(AssetVerifyBatch.created_at <= timeTo.strip() + " 23:59:59")
    total = count_of(db, stmt)
    rows = list(db.scalars(stmt.order_by(AssetVerifyBatch.id.desc()).offset((number - 1) * size).limit(size)).all())
    return ok({"list": [_batch_vo(row, _names(db, rows)) for row in rows], "total": total, "pageNo": number, "pageSize": size})


@router.get("/asset/verify/errors")
def verify_errors(
    batchNo: str = "",
    assetCode: str = "",
    pageNo: int = 1,
    pageSize: int = 20,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    text = (batchNo or "").strip()
    if not text:
        return fail(1001, "批次号必填")
    number, size = page_args(pageNo, pageSize)
    stmt = select(AssetVerifyError).where(
        AssetVerifyError.deleted == 0,
        AssetVerifyError.tenant_id == tenant_of(actor),
        (AssetVerifyError.batch_no == text) | (AssetVerifyError.run_no == text),
    )
    code = (assetCode or "").strip()
    if code:
        stmt = stmt.where(AssetVerifyError.asset_code == code)
    total = count_of(db, stmt)
    rows = list(db.scalars(stmt.order_by(AssetVerifyError.id).offset((number - 1) * size).limit(size)).all())
    return ok(
        {
            "list": [
                {
                    "id": row.id,
                    "batchNo": row.batch_no,
                    "recordId": row.record_id,
                    "recordType": row.record_type,
                    "assetCode": row.asset_code,
                    "inconsistentFields": _loads(row.inconsistent_fields),
                    "description": row.description,
                }
                for row in rows
            ],
            "total": total,
            "pageNo": number,
            "pageSize": size,
        }
    )


@router.put("/asset/verify/task/{task_id}")
def verify_task(
    task_id: int,
    body: VerifyTaskBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    row = db.get(AssetVerifyBatch, task_id)
    if row is None or row.deleted or (row.tenant_id or 0) != tenant_of(actor):
        return fail(1014, "校验批次不存在")
    target = (body.taskStatus or "").strip()
    if target not in TASK_STATUS or (row.task_status, target) not in TRANSITIONS:
        return fail(1014, "工单状态非法")
    if target == "REPAIRING":
        owner_id = int(body.ownerUserId or 0)
        if not owner_id:
            return fail(1001, "修复责任人必填")
        owner = db.get(User, owner_id)
        if owner is None or owner.deleted or (owner.tenant_id or 0) != tenant_of(actor):
            return fail(1500, "修复责任人不存在")
        if owner.status != "ENABLED":
            return fail(1501, "修复责任人已停用")
        row.owner_user_id = owner_id
    remark = (body.remark or "").strip()
    if remark:
        row.remark = remark[:256]
    row.task_status = target
    db.flush()
    return ok(_batch_vo(row, _names(db, [row])))


@router.get("/asset/verify/metrics")
def verify_metrics(
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    assets = _assets(db, actor, "FULL")
    complete = _complete_rate(db, actor, assets)
    batches = list(
        db.scalars(
            _batch_stmt(db, actor).order_by(AssetVerifyBatch.id.desc()).limit(200)
        ).all()
    )
    latest = batches[0].consistency_rate if batches else complete
    by_day: dict[str, AssetVerifyBatch] = {}
    for row in reversed(batches):
        if row.created_at is None:
            continue
        by_day[row.created_at.strftime("%Y-%m-%d")] = row
    trend = [
        {
            "date": day,
            "completeRate": row.complete_rate,
            "consistencyRate": row.consistency_rate,
        }
        for day, row in sorted(by_day.items())[-30:]
    ]
    pending = sum(1 for row in batches if row.task_status == "PENDING_DISPATCH")
    return ok(
        {
            "relationCompleteRate": complete,
            "consistencyRate": latest,
            "pendingTaskCount": pending,
            "trend": trend,
        }
    )
