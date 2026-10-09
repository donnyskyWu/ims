"""组织事件：先验签再入队。Worker 才写 ims_sys_user，不写 Football。"""

import json
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Header, Query, Request
from pydantic import BaseModel
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.core import mask_mobile, utcnow
from app.dingtalk_client import pull_org_directory
from app.dingtalk_crypto import decrypt_encrypt, signature_ok
from app.models import (
    AssetLedger,
    CertArchive,
    OrgEvent,
    PositionRule,
    Role,
    RolePerm,
    Todo,
    User,
    UserDept,
    UserMapping,
    UserRole,
)

router = APIRouter()

EVENT_TYPES = ("hire", "transfer", "resign", "dept_change")
MAX_RETRY = 16
BACKOFF_SECONDS = (60, 300, 900, 3600)
DEAD_LETTER_ALERT = "ims.org.dead_letter"


class EventBody(BaseModel):
    encrypt: str


def iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.strftime("%Y-%m-%dT%H:%M:%S")


def clamp_page(page_no: int, page_size: int) -> tuple[int, int]:
    page_no = page_no if page_no > 0 else 1
    page_size = page_size if 0 < page_size <= 100 else 10
    return page_no, page_size


def backoff_seconds(retry_count: int) -> int:
    index = retry_count - 1
    if index < 0:
        return BACKOFF_SECONDS[0]
    if index >= len(BACKOFF_SECONDS):
        return BACKOFF_SECONDS[-1]
    return BACKOFF_SECONDS[index]


def read_payload(raw: str) -> dict:
    try:
        data = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    inner = data.get("payloadJson")
    if isinstance(inner, dict):
        merged = dict(inner)
        for key, value in data.items():
            if key != "payloadJson":
                merged.setdefault(key, value)
        return merged
    return data


def is_r1(db: Session, user: User) -> bool:
    role_ids = list(db.scalars(select(UserRole.role_id).where(UserRole.user_id == user.id)).all())
    if not role_ids:
        return False
    role = db.scalar(
        select(Role).where(
            Role.id.in_(role_ids),
            Role.role_key == "sys:admin",
            Role.deleted == 0,
            Role.status == "ENABLED",
        )
    )
    return role is not None


def enqueue(db: Session, plain: str) -> tuple[bool, str]:
    try:
        data = json.loads(plain)
    except json.JSONDecodeError:
        return False, "事件无法解析"
    if not isinstance(data, dict):
        return False, "事件无法解析"
    event_type = str(data.get("eventType") or "")
    event_id = str(data.get("dingtalkEventId") or "")
    if event_type not in EVENT_TYPES or not event_id:
        return False, "事件缺少类型或幂等键"
    key = f"{event_id}|{event_type}"
    existing = db.scalar(select(OrgEvent).where(OrgEvent.idempotency_key == key))
    if existing is not None:
        return True, ""
    merged = read_payload(plain)
    event = OrgEvent(
        dingtalk_event_id=event_id[:64],
        event_type=event_type,
        idempotency_key=key[:128],
        union_id=str(data.get("unionId") or "")[:64],
        user_id=int(data["userId"]) if str(data.get("userId") or "").isdigit() else None,
        before_dept=str(merged.get("beforeDept") or data.get("beforeDept") or "")[:128],
        after_dept=str(merged.get("afterDept") or data.get("afterDept") or "")[:128],
        payload_json=plain,
        sync_status="PENDING",
        retry_count=0,
        next_retry_at=None,
        dead_letter=0,
        tenant_id=0,
    )
    db.add(event)
    return True, ""


@router.post("/auth/org/event")
def org_event(
    body: EventBody,
    db: Session = Depends(db_session),
    timestamp: str = Header(default=""),
    nonce: str = Header(default=""),
    sign: str = Header(default=""),
):
    if not signature_ok(timestamp, nonce, body.encrypt, sign):
        return fail(1001, "签名无效")
    try:
        plain = decrypt_encrypt(body.encrypt)
    except Exception:
        return fail(1001, "事件无法解密")
    accepted, message = enqueue(db, plain)
    if not accepted:
        return fail(1001, message)
    return ok(None)


def latest_person_event(db: Session, user_id: int) -> OrgEvent | None:
    return db.scalar(
        select(OrgEvent)
        .where(OrgEvent.user_id == user_id, OrgEvent.event_type != "reconcile")
        .order_by(OrgEvent.id.desc())
    )


def dept_ids_of(payload: dict) -> list[int]:
    raw = payload.get("deptIds") or []
    if not isinstance(raw, list):
        return []
    ids: list[int] = []
    for item in raw:
        if str(item).isdigit():
            ids.append(int(item))
    return ids


def dept_names_of(payload: dict, event: OrgEvent | None) -> list[str]:
    raw = payload.get("deptNames") or []
    if isinstance(raw, list) and raw:
        return [str(item) for item in raw if item]
    if event and event.after_dept:
        return [event.after_dept]
    return []


def replace_depts(db: Session, user_id: int, dept_ids: list[int]) -> None:
    db.execute(delete(UserDept).where(UserDept.user_id == user_id))
    for dept_id in dept_ids:
        db.add(UserDept(user_id=user_id, dept_id=dept_id, tenant_id=0))


def find_user(db: Session, ding_id: str, mobile: str, user_id: int | None) -> User | None:
    if ding_id:
        found = db.scalar(select(User).where(User.dingtalk_user_id == ding_id, User.deleted == 0))
        if found is not None:
            return found
    if user_id:
        found = db.get(User, user_id)
        if found is not None and not found.deleted:
            return found
    if mobile:
        return db.scalar(select(User).where(User.mobile == mobile, User.deleted == 0))
    return None


def payload_position(payload: dict) -> str:
    return str(payload.get("dingtalkPosition") or payload.get("position") or "").strip()[:64]


def stored_json(event: OrgEvent) -> dict:
    try:
        data = json.loads(event.payload_json or "{}")
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def enabled_position_rule(db: Session, position: str) -> PositionRule | None:
    if not position:
        return None
    return db.scalar(
        select(PositionRule).where(
            PositionRule.dingtalk_position == position,
            PositionRule.status == "ENABLED",
            PositionRule.deleted == 0,
        )
    )


def user_role_ids(db: Session, user_id: int) -> list[int]:
    return list(db.scalars(select(UserRole.role_id).where(UserRole.user_id == user_id)).all())


def role_names(db: Session, role_ids: list[int]) -> list[str]:
    if not role_ids:
        return []
    rows = db.scalars(select(Role).where(Role.id.in_(role_ids), Role.deleted == 0)).all()
    order = {row.id: row.role_name for row in rows}
    return [order[role_id] for role_id in role_ids if role_id in order]


def grant_roles(db: Session, user: User, role_ids: list[int]) -> list[str]:
    existing = set(user_role_ids(db, user.id))
    added: list[str] = []
    for raw in role_ids:
        role_id = int(raw)
        if role_id in existing:
            continue
        role = db.get(Role, role_id)
        if role is None or role.deleted or role.status != "ENABLED":
            continue
        db.add(UserRole(user_id=user.id, role_id=role.id, tenant_id=0))
        existing.add(role.id)
        added.append(role.role_name)
    return added


def previous_applied_position(db: Session, user_id: int) -> str:
    rows = db.scalars(
        select(OrgEvent)
        .where(
            OrgEvent.user_id == user_id,
            OrgEvent.sync_status == "SUCCESS",
            OrgEvent.event_type.in_(("hire", "transfer", "dept_change")),
        )
        .order_by(OrgEvent.id.desc())
    ).all()
    for event in rows:
        stored = stored_json(event)
        applied = str(stored.get("appliedPosition") or "").strip()
        if applied:
            return applied[:64]
        position = payload_position(read_payload(event.payload_json))
        if position:
            return position
    return ""


def previous_dept_names(db: Session, user_id: int) -> list[str]:
    rows = db.scalars(
        select(OrgEvent)
        .where(OrgEvent.user_id == user_id, OrgEvent.sync_status == "SUCCESS")
        .order_by(OrgEvent.id.desc())
    ).all()
    for event in rows:
        names = dept_names_of(read_payload(event.payload_json), event)
        if names:
            return names
    return []


def write_event_result(event: OrgEvent, position: str, diff: dict | None, dept_names: list[str]) -> None:
    stored = stored_json(event)
    if position:
        stored["appliedPosition"] = position
    if dept_names and not dept_names_of(read_payload(event.payload_json), event):
        stored["deptNames"] = dept_names
    if diff is not None:
        stored["permissionDiff"] = diff
    event.payload_json = json.dumps(stored, ensure_ascii=False)


def ensure_return_todo(db: Session, user: User) -> None:
    existing = db.scalar(
        select(Todo).where(
            Todo.ref_type == "org_resign",
            Todo.ref_id == user.id,
            Todo.status == "PENDING",
        )
    )
    if existing is not None:
        return
    admin = db.scalar(select(User).where(User.username == "admin", User.deleted == 0))
    db.add(
        Todo(
            assignee_user_id=admin.id if admin is not None else user.id,
            task_type="return",
            ref_type="org_resign",
            ref_id=user.id,
            title=f"离职待归还：{user.nickname or user.username}",
            content="账号、资产待归还，证件待回收",
            status="PENDING",
            deadline=datetime(2000, 1, 1),
            tenant_id=0,
        )
    )


def apply_position_grant(db: Session, user: User, event: OrgEvent, position: str, before_position: str) -> dict:
    retained = role_names(db, user_role_ids(db, user.id))
    added: list[str] = []
    if event.event_type == "hire" and position:
        rule = enabled_position_rule(db, position)
        if rule is not None:
            added = grant_roles(db, user, [int(item) for item in (rule.grant_role_ids or [])])
            if added:
                rule.applied_user_count = int(rule.applied_user_count or 0) + 1
        summary = "入职按岗位供给角色" if added else "入职未匹配启用供给规则"
        retained_for_diff: list[str] = []
    elif event.event_type == "transfer" and position and position != before_position:
        rule = enabled_position_rule(db, position)
        if rule is not None:
            added = grant_roles(db, user, [int(item) for item in (rule.grant_role_ids or [])])
            if added:
                rule.applied_user_count = int(rule.applied_user_count or 0) + 1
        summary = "调岗后追加新岗位角色，24 小时内保留原角色" if added else "调岗部门已变更，角色无增减"
        retained_for_diff = retained
    elif event.event_type == "transfer":
        summary = "调岗部门已变更，角色无增减"
        retained_for_diff = retained
    else:
        summary = "部门变更，角色无增减"
        retained_for_diff = retained
    return {
        "beforePosition": before_position,
        "afterPosition": position or before_position,
        "beforeDept": event.before_dept,
        "afterDept": event.after_dept,
        "retainedRoleNames": retained_for_diff,
        "addedRoleNames": added,
        "removedRoleNames": [],
        "summary": summary,
    }


def create_user(db: Session, ding_id: str, union_id: str, mobile: str, nickname: str) -> User:
    stem = f"dt_{ding_id or union_id or mobile}"[:50]
    username = stem
    seq = 1
    while db.scalar(select(User).where(User.username == username)):
        seq += 1
        username = f"{stem}_{seq}"[:64]
    user = User(
        username=username,
        nickname=(nickname or username)[:64],
        mobile=mobile[:20],
        password_hash=secrets.token_hex(16),
        status="ENABLED",
        dingtalk_user_id=ding_id[:64],
        tenant_id=0,
    )
    db.add(user)
    db.flush()
    return user


def upsert_mapping(
    db: Session,
    user: User,
    ding_id: str,
    union_id: str,
    dept_ids: list[int],
    now: datetime,
    buffer_until: datetime | None,
    keep_previous: bool,
) -> UserMapping:
    mapping = db.scalar(
        select(UserMapping).where(
            UserMapping.tenant_id == 0,
            UserMapping.dingtalk_user_id == ding_id,
            UserMapping.deleted == 0,
        )
    )
    if mapping is None:
        mapping = UserMapping(
            user_id=user.id,
            dingtalk_user_id=ding_id,
            union_id=union_id[:64],
            dept_ids=dept_ids,
            prev_dept_ids=[],
            sync_status="SUCCESS",
            last_sync_time=now,
            buffer_until=buffer_until,
            tenant_id=0,
        )
        db.add(mapping)
    else:
        if keep_previous:
            mapping.prev_dept_ids = list(mapping.dept_ids or [])
        mapping.user_id = user.id
        mapping.union_id = union_id[:64] or mapping.union_id
        mapping.dept_ids = dept_ids
        mapping.sync_status = "SUCCESS"
        mapping.last_sync_time = now
        mapping.buffer_until = buffer_until
    db.flush()
    return mapping


def apply_event(db: Session, event: OrgEvent, now: datetime) -> None:
    payload = read_payload(event.payload_json)
    ding_id = str(payload.get("dingtalkUserId") or "")
    mobile = str(payload.get("mobile") or "")
    nickname = str(payload.get("nickname") or "")
    union_id = str(payload.get("unionId") or event.union_id or "")
    raw_user_id = payload.get("userId")
    user_id = int(raw_user_id) if str(raw_user_id or "").isdigit() else event.user_id
    dept_ids = dept_ids_of(payload)
    user = find_user(db, ding_id, mobile, user_id)
    if event.event_type == "resign":
        if user is None:
            raise ValueError("未找到本地用户")
        user.status = "FROZEN"
    elif event.event_type in ("hire", "transfer", "dept_change"):
        if user is None:
            if not ding_id and not mobile:
                raise ValueError("缺少人员标识")
            user = create_user(db, ding_id, union_id, mobile, nickname)
        else:
            if nickname:
                user.nickname = nickname[:64]
            if mobile:
                user.mobile = mobile[:20]
            if ding_id:
                user.dingtalk_user_id = ding_id[:64]
            if event.event_type == "hire":
                user.status = "ENABLED"
        if not user.dingtalk_user_id:
            raise ValueError("缺少钉钉用户标识")
    else:
        raise ValueError("未知事件类型")
    buffer_until = now + timedelta(hours=24) if event.event_type == "transfer" else None
    upsert_mapping(
        db,
        user,
        user.dingtalk_user_id,
        union_id,
        dept_ids or list(
            db.scalars(select(UserDept.dept_id).where(UserDept.user_id == user.id)).all()
        ),
        now,
        buffer_until,
        keep_previous=event.event_type == "transfer",
    )
    if dept_ids:
        replace_depts(db, user.id, dept_ids)
    position = payload_position(payload)
    before_position = "" if event.event_type == "hire" else previous_applied_position(db, user.id)
    kept_dept_names = dept_names_of(payload, event) or previous_dept_names(db, user.id)
    diff = None
    if event.event_type == "resign":
        ensure_return_todo(db, user)
        try:
            from app.acct_return import ReturnReject, generate_return_order

            resign_day = str(payload.get("dingtalkResignDate") or payload.get("resignDate") or now.strftime("%Y-%m-%d"))
            generate_return_order(db, user, int(user.id), resign_day, manual=False)
        except ReturnReject:
            pass
        if not position:
            position = before_position
    else:
        diff = apply_position_grant(db, user, event, position, before_position)
        if not position:
            position = before_position
    event.user_id = user.id
    event.union_id = union_id[:64]
    write_event_result(event, position, diff, kept_dept_names)
    event.sync_status = "SUCCESS"
    event.synced_at = now
    event.dead_letter = 0
    event.next_retry_at = None
    event.last_error = ""
    event.updated_at = now


def fail_event(event: OrgEvent, now: datetime, message: str) -> None:
    event.retry_count += 1
    event.last_error = message[:500]
    event.updated_at = now
    event.sync_status = "FAILED_RETRY"
    if event.retry_count >= MAX_RETRY:
        event.dead_letter = 1
        event.next_retry_at = None
        event.alert_code = DEAD_LETTER_ALERT
        return
    event.dead_letter = 0
    base = now.replace(microsecond=0)
    event.next_retry_at = base + timedelta(seconds=backoff_seconds(event.retry_count))


def process_due(db: Session, now: datetime | None = None) -> int:
    moment = now or utcnow()
    rows = db.scalars(
        select(OrgEvent)
        .where(
            OrgEvent.dead_letter == 0,
            OrgEvent.sync_status.in_(("PENDING", "FAILED_RETRY")),
            or_(OrgEvent.next_retry_at.is_(None), OrgEvent.next_retry_at <= moment),
        )
        .order_by(OrgEvent.id)
    ).all()
    for event in rows:
        nested = db.begin_nested()
        try:
            apply_event(db, event, moment)
            nested.commit()
        except Exception as exc:
            nested.rollback()
            fail_event(event, moment, str(exc))
    return len(rows)


def user_sync_flags(db: Session, user_id: int, mapping: UserMapping) -> tuple[str, bool, bool]:
    event = latest_person_event(db, user_id)
    if mapping.sync_status == "SUCCESS":
        return "SUCCESS", False, False
    if event is not None and event.dead_letter:
        return "FAILED", False, True
    if event is not None and event.sync_status == "FAILED_RETRY":
        return "FAILED", True, False
    if mapping.sync_status == "PENDING":
        return "PENDING", False, False
    return "FAILED", False, False


def latest_permission_diff(db: Session, user_id: int) -> dict | None:
    rows = db.scalars(
        select(OrgEvent)
        .where(
            OrgEvent.user_id == user_id,
            OrgEvent.sync_status == "SUCCESS",
            OrgEvent.event_type.in_(("transfer", "dept_change", "hire")),
        )
        .order_by(OrgEvent.id.desc())
    ).all()
    for event in rows:
        diff = stored_json(event).get("permissionDiff")
        if isinstance(diff, dict):
            return diff
    return None


def holding_summary(db: Session, user: User | None) -> dict:
    empty = {"accountInUse": 0, "assetInUse": 0, "certActive": 0, "certRecycled": 0}
    if user is None:
        return empty
    try:
        from app.ops_db import ops_session
        from app.ops_models import PlatformAccount

        ops = ops_session()
        try:
            accounts = ops.scalar(
                select(func.count())
                .select_from(PlatformAccount)
                .where(
                    PlatformAccount.deleted == 0,
                    PlatformAccount.holder_user_id == user.id,
                    PlatformAccount.status == "IN_USE",
                )
            ) or 0
        finally:
            ops.close()
        assets = db.scalar(
            select(func.count())
            .select_from(AssetLedger)
            .where(
                AssetLedger.deleted == 0,
                AssetLedger.owner_user_id == user.id,
                AssetLedger.status == "IN_USE",
            )
        ) or 0
        nickname = (user.nickname or "").strip()
        cert_active = 0
        cert_recycled = 0
        if nickname:
            cert_active = db.scalar(
                select(func.count())
                .select_from(CertArchive)
                .where(
                    CertArchive.deleted == 0,
                    CertArchive.holder_name == nickname,
                    CertArchive.status != "RECYCLED",
                )
            ) or 0
            cert_recycled = db.scalar(
                select(func.count())
                .select_from(CertArchive)
                .where(
                    CertArchive.deleted == 0,
                    CertArchive.holder_name == nickname,
                    CertArchive.status == "RECYCLED",
                )
            ) or 0
        return {
            "accountInUse": int(accounts),
            "assetInUse": int(assets),
            "certActive": int(cert_active),
            "certRecycled": int(cert_recycled),
        }
    except Exception:
        return empty


def org_user_vo(db: Session, mapping: UserMapping) -> dict:
    user = db.get(User, mapping.user_id)
    payload = {}
    event = latest_person_event(db, mapping.user_id)
    if event is not None:
        payload = read_payload(event.payload_json)
    status, retry_flag, dead_letter = user_sync_flags(db, mapping.user_id, mapping)
    role_ids = list(db.scalars(select(UserRole.role_id).where(UserRole.user_id == mapping.user_id)).all())
    names: list[str] = []
    if role_ids:
        names = list(db.scalars(select(Role.role_name).where(Role.id.in_(role_ids), Role.deleted == 0)).all())
    from app.system_role import user_perm_codes

    perm_codes = user_perm_codes(db, mapping.user_id) if user is not None else []
    position = ""
    if event is not None:
        position = str(stored_json(event).get("appliedPosition") or "") or payload_position(payload)
    if not position and user is not None:
        position = previous_applied_position(db, user.id)
    return {
        "userId": mapping.user_id,
        "nickname": user.nickname if user else "",
        "mobileMasked": mask_mobile(user.mobile if user else ""),
        "deptIds": list(mapping.dept_ids or []),
        "deptNames": dept_names_of(payload, event),
        "dingtalkUserId": mapping.dingtalk_user_id,
        "syncStatus": status,
        "retryFlag": retry_flag,
        "deadLetter": dead_letter,
        "lastSyncTime": iso(mapping.last_sync_time),
        "status": user.status if user else "",
        "grantedRoleNames": names,
        "positionName": position,
        "grantedPermCodes": perm_codes,
        "bufferUntil": iso(mapping.buffer_until),
        "permissionDiff": latest_permission_diff(db, mapping.user_id),
        "holdings": holding_summary(db, user),
    }


def event_payload(event: OrgEvent) -> dict:
    return read_payload(event.payload_json or "{}")


def event_vo(event: OrgEvent) -> dict:
    status = "DEAD_LETTER" if event.dead_letter else event.sync_status
    return {
        "id": event.id,
        "eventType": event.event_type,
        "dingtalkEventId": event.dingtalk_event_id,
        "unionId": event.union_id,
        "userId": event.user_id,
        "beforeDept": event.before_dept,
        "afterDept": event.after_dept,
        "payloadJson": event_payload(event),
        "syncStatus": status,
        "syncedAt": iso(event.synced_at),
        "createdAt": iso(event.created_at),
        "retryCount": event.retry_count,
        "deadLetter": bool(event.dead_letter),
        "lastError": event.last_error or "",
    }


def user_matches_sync_status(item: dict, wanted: str) -> bool:
    """人员列表按四态筛选。失败重试和死信在行上归成 FAILED，另带 retryFlag / deadLetter。"""
    status = (wanted or "").strip()
    if not status:
        return True
    if status == "FAILED_RETRY":
        return bool(item.get("retryFlag"))
    if status == "DEAD_LETTER":
        return bool(item.get("deadLetter"))
    if status == "FAILED":
        return item.get("syncStatus") == "FAILED" and not item.get("retryFlag") and not item.get("deadLetter")
    return item.get("syncStatus") == status


def can_read_org(db: Session, user: User) -> bool:
    if is_r1(db, user):
        return True
    role_ids = list(db.scalars(select(UserRole.role_id).where(UserRole.user_id == user.id)).all())
    if not role_ids:
        return False
    found = db.scalar(
        select(RolePerm.id).where(RolePerm.role_id.in_(role_ids), RolePerm.perm_code == "auth:org:query")
    )
    return found is not None


def dept_limit(request: Request) -> list[int] | None:
    """None = 全量。列表 = 查看者自己的部门号，精确匹配，不含下级。"""
    scope = getattr(request.state, "scope", None)
    if scope is None or getattr(scope, "kind", "ALL") == "ALL":
        return None
    return [int(item) for item in (getattr(scope, "dept_ids", None) or [])]


def empty_org_page(page_no: int, size: int):
    return ok({"list": [], "total": 0, "pageNo": page_no, "pageSize": size, "deptMatch": "EXACT"})


def users_in_depts(dept_ids: list[int]):
    return select(UserDept.user_id).where(UserDept.dept_id.in_(dept_ids))


@router.get("/auth/org/users")
def org_users(
    request: Request,
    pageNo: int = 1,
    pageSize: int = 10,
    keyword: str = "",
    deptId: int | None = None,
    syncStatus: str = "",
    db: Session = Depends(db_session),
    user: User = Depends(current_user),
):
    if not can_read_org(db, user):
        return fail(403, "无操作权限")
    page_no, size = clamp_page(pageNo, pageSize)
    allowed = dept_limit(request)
    if allowed is not None and deptId and int(deptId) not in allowed:
        return empty_org_page(page_no, size)
    if allowed is not None and not allowed:
        return empty_org_page(page_no, size)
    stmt = select(UserMapping).where(UserMapping.deleted == 0, UserMapping.tenant_id == 0)
    if keyword:
        stmt = stmt.join(User, User.id == UserMapping.user_id).where(
            or_(User.nickname.like(f"%{keyword}%"), UserMapping.dingtalk_user_id.like(f"%{keyword}%"))
        )
    if deptId:
        stmt = stmt.where(UserMapping.user_id.in_(users_in_depts([int(deptId)])))
    elif allowed is not None:
        stmt = stmt.where(UserMapping.user_id.in_(users_in_depts(allowed)))
    rows = db.scalars(stmt.order_by(UserMapping.id.desc())).all()
    items = []
    for mapping in rows:
        item = org_user_vo(db, mapping)
        if not user_matches_sync_status(item, syncStatus):
            continue
        items.append(item)
    total = len(items)
    start = (page_no - 1) * size
    return ok(
        {
            "list": items[start : start + size],
            "total": total,
            "pageNo": page_no,
            "pageSize": size,
            "deptMatch": "EXACT",
        }
    )


@router.get("/auth/org/events")
def org_events(
    request: Request,
    pageNo: int = 1,
    pageSize: int = 10,
    eventType: str = "",
    syncStatus: str = "",
    timeRange: list[str] = Query(default=[]),
    db: Session = Depends(db_session),
    user: User = Depends(current_user),
):
    if not can_read_org(db, user):
        return fail(403, "无操作权限")
    page_no, size = clamp_page(pageNo, pageSize)
    allowed = dept_limit(request)
    if allowed is not None and not allowed:
        return empty_org_page(page_no, size)
    stmt = select(OrgEvent)
    if allowed is not None:
        stmt = stmt.where(OrgEvent.user_id.in_(users_in_depts(allowed)))
    if eventType:
        stmt = stmt.where(OrgEvent.event_type == eventType)
    if syncStatus == "DEAD_LETTER":
        stmt = stmt.where(OrgEvent.dead_letter == 1)
    elif syncStatus == "FAILED_RETRY":
        stmt = stmt.where(OrgEvent.sync_status == "FAILED_RETRY", OrgEvent.dead_letter == 0)
    elif syncStatus:
        stmt = stmt.where(OrgEvent.sync_status == syncStatus, OrgEvent.dead_letter == 0)
    if len(timeRange) >= 2 and timeRange[0] and timeRange[1]:
        stmt = stmt.where(OrgEvent.created_at >= timeRange[0][:19], OrgEvent.created_at <= timeRange[1][:19])
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(OrgEvent.id.desc()).offset((page_no - 1) * size).limit(size)).all()
    return ok({"list": [event_vo(row) for row in rows], "total": total, "pageNo": page_no, "pageSize": size})


def delay_minutes(event: OrgEvent) -> float | None:
    if event.synced_at is None or event.created_at is None:
        return None
    return max((event.synced_at - event.created_at).total_seconds(), 0) / 60


def percentile(values: list[float], ratio: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * ratio
    low = int(rank)
    high = min(low + 1, len(ordered) - 1)
    weight = rank - low
    return ordered[low] * (1 - weight) + ordered[high] * weight


@router.get("/auth/org/sync-metrics")
def sync_metrics(db: Session = Depends(db_session), _: User = Depends(current_user)):
    events = db.scalars(select(OrgEvent)).all()
    delays = [item for item in (delay_minutes(row) for row in events) if item is not None]
    avg = sum(delays) / len(delays) if delays else 0.0
    success = sum(1 for row in events if row.sync_status == "SUCCESS")
    rate = (success / len(events)) if events else 1.0
    delay_ms = int(round(avg * 60000))
    by_day: dict[str, list[float]] = {}
    for row in events:
        minutes = delay_minutes(row)
        if minutes is None:
            continue
        day = row.created_at.strftime("%Y-%m-%d")
        by_day.setdefault(day, []).append(minutes)
    trend = [
        {"date": day, "delayMinutes": round(sum(vals) / len(vals), 2)}
        for day, vals in sorted(by_day.items())[-30:]
    ]
    pending = sum(1 for row in events if row.sync_status == "PENDING")
    users = db.scalar(select(func.count()).select_from(UserMapping).where(UserMapping.deleted == 0)) or 0
    return ok(
        {
            "avgSyncDelayMinutes": round(avg, 2),
            "p95SyncDelayMinutes": round(percentile(delays, 0.95), 2),
            "successRate": round(rate, 4),
            "trend": trend,
            "delayMillis": delay_ms,
            "level": "red" if delay_ms >= 300000 else "green",
            "totalUsers": users,
            "pendingEvents": pending,
        }
    )


def apply_pull_user(db: Session, row: dict, now: datetime) -> str:
    """写入/更新本地用户与映射。返回 created|updated。"""
    ding_id = str(row.get("userid") or "").strip()
    if not ding_id:
        raise ValueError("缺少钉钉 userid")
    mobile = str(row.get("mobile") or "").strip()
    nickname = str(row.get("name") or "").strip()
    union_id = str(row.get("unionid") or "").strip()
    dept_ids = [int(x) for x in (row.get("deptIds") or []) if str(x).isdigit()]
    user = find_user(db, ding_id, mobile, None)
    created = user is None
    if user is None:
        if not mobile:
            mobile = f"ding_{ding_id[-8:]}"
        user = create_user(db, ding_id, union_id, mobile, nickname)
    else:
        if nickname:
            user.nickname = nickname[:64]
        if mobile:
            user.mobile = mobile[:20]
        user.dingtalk_user_id = ding_id[:64]
        if user.status == "FROZEN":
            user.status = "ENABLED"
    upsert_mapping(
        db,
        user,
        ding_id,
        union_id,
        dept_ids,
        now,
        buffer_until=None,
        keep_previous=False,
    )
    if dept_ids:
        replace_depts(db, user.id, dept_ids)
    return "created" if created else "updated"


@router.post("/auth/org/sync-from-dingtalk")
def sync_from_dingtalk(db: Session = Depends(db_session), user: User = Depends(current_user)):
    """R1：从钉钉拉取部门+人员并 upsert 本地映射（一次性全量同步）。"""
    if not is_r1(db, user):
        return fail(403, "仅 R1 可执行钉钉全量同步")
    snapshot, err = pull_org_directory()
    if err or snapshot is None:
        meta = (snapshot or {}).get("meta") or {}
        hint = meta.get("authScopeHint")
        msg = f"钉钉通讯录拉取失败: {err or 'unknown'}"
        if hint:
            msg = f"{msg}。{hint}"
        return fail(
            1001,
            msg,
            data={
                "authScopeHint": hint,
                "authorizedRootDeptIds": meta.get("authorizedRootDeptIds"),
                "authedDeptIds": meta.get("authedDeptIds"),
                "firstApiError": meta.get("firstApiError"),
                "departmentsFetched": meta.get("departmentsFetched", 0),
                "usersFetched": meta.get("usersFetched", 0),
            },
        )
    now = utcnow()
    created = 0
    updated = 0
    failures: list[dict] = []
    for row in snapshot.get("users") or []:
        nested = db.begin_nested()
        try:
            outcome = apply_pull_user(db, row, now)
            nested.commit()
            if outcome == "created":
                created += 1
            else:
                updated += 1
        except Exception as exc:  # noqa: BLE001
            nested.rollback()
            failures.append({"userid": row.get("userid"), "error": str(exc)[:200]})
    meta = snapshot.get("meta") or {}
    dept_count = len(snapshot.get("departments") or [])
    payload: dict = {
        "departmentsFetched": dept_count,
        "usersCreated": created,
        "usersUpdated": updated,
        "usersFailed": len(failures),
        "failures": failures[:20],
        "syncedAt": iso(now),
        "authorizedRootDeptIds": meta.get("authorizedRootDeptIds"),
        "firstApiError": meta.get("firstApiError"),
        "listsubCalls": meta.get("listsubCalls"),
        "subDepartmentIdsDiscovered": meta.get("subDepartmentIdsDiscovered"),
        "rootSubDeptIdCount": meta.get("rootSubDeptIdCount"),
    }
    if meta.get("partialScope"):
        payload["partialScope"] = True
        payload["authScopeHint"] = meta.get("authScopeHint")
    return ok(payload)


@router.post("/auth/org/reconcile")
def reconcile(db: Session = Depends(db_session), user: User = Depends(current_user)):
    if not is_r1(db, user):
        return fail(403, "仅 R1 可对账")
    now = utcnow()
    task_id = "rc-" + secrets.token_hex(8)
    local_users = db.scalar(select(func.count()).select_from(UserMapping).where(UserMapping.deleted == 0)) or 0
    db.add(
        OrgEvent(
            dingtalk_event_id=task_id,
            event_type="reconcile",
            idempotency_key=f"{task_id}|reconcile",
            payload_json=json.dumps(
                {"kind": "reconcile", "localUserCount": local_users, "source": "local"},
                ensure_ascii=False,
            ),
            sync_status="SUCCESS",
            retry_count=0,
            dead_letter=0,
            tenant_id=0,
            created_at=now,
            updated_at=now,
            synced_at=now,
        )
    )
    return ok({"reconcileTaskId": task_id, "triggeredAt": iso(now)})


class ReplayBody(BaseModel):
    startTime: str = ""
    endTime: str = ""


def parse_moment(value: str) -> datetime | None:
    text = (value or "").strip().replace("Z", "")
    if not text:
        return None
    if len(text) == 16:
        text = text + ":00"
    try:
        return datetime.fromisoformat(text[:19])
    except ValueError:
        return None


def report_body(event: OrgEvent | None) -> dict:
    if event is None:
        return {
            "found": False,
            "reconcileTaskId": "",
            "triggeredAt": None,
            "diffCount": 0,
            "fixedCount": 0,
            "localUserCount": 0,
            "failures": [],
            "source": "local",
        }
    payload = event_payload(event)
    failures = payload.get("failures") if isinstance(payload.get("failures"), list) else []
    return {
        "found": True,
        "reconcileTaskId": event.dingtalk_event_id,
        "triggeredAt": iso(event.synced_at or event.created_at),
        "diffCount": int(payload.get("diffCount") or 0),
        "fixedCount": int(payload.get("fixedCount") or 0),
        "localUserCount": int(payload.get("localUserCount") or 0),
        "failures": failures,
        "source": "local",
    }


@router.get("/callback/dingtalk/reconcile/report")
def reconcile_report(db: Session = Depends(db_session), user: User = Depends(current_user)):
    """最近一次本地对账。不拉取钉钉。"""
    if not is_r1(db, user):
        return fail(403, "仅 R1 可查看对账报告")
    event = db.scalar(
        select(OrgEvent).where(OrgEvent.event_type == "reconcile").order_by(OrgEvent.id.desc()).limit(1)
    )
    return ok(report_body(event))


@router.post("/callback/dingtalk/retry-queue/replay")
def replay_failed(body: ReplayBody, db: Session = Depends(db_session), user: User = Depends(current_user)):
    """按时间重放失败/死信。只走本地队列，不调用钉钉。"""
    if not is_r1(db, user):
        return fail(403, "仅 R1 可重放失败事件")
    start = parse_moment(body.startTime)
    end = parse_moment(body.endTime)
    if start is None or end is None:
        return fail(1001, "请填写开始和结束时间")
    if end < start:
        return fail(1001, "结束时间须晚于开始时间")
    if (end - start).total_seconds() > 7 * 24 * 3600:
        return fail(1001, "重放区间不能超过 7 天")
    rows = db.scalars(
        select(OrgEvent).where(
            OrgEvent.created_at >= start,
            OrgEvent.created_at <= end,
            or_(OrgEvent.dead_letter == 1, OrgEvent.sync_status == "FAILED_RETRY"),
        )
    ).all()
    if not rows:
        return ok({"replayed": 0, "stillFailed": 0, "source": "local"})
    for event in rows:
        event.sync_status = "PENDING"
        event.dead_letter = 0
        event.next_retry_at = None
        event.updated_at = utcnow()
    db.flush()
    process_due(db)
    still = 0
    for event in rows:
        db.refresh(event)
        if event.dead_letter or event.sync_status == "FAILED_RETRY":
            still += 1
    return ok({"replayed": len(rows), "stillFailed": still, "source": "local"})
