"""钉钉组织增量事件与全量对账。"""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.clock import now_naive, parse_input_datetime
from app.core.crypto import encrypt, hmac_hash
from app.core.errors import BizError
from app.core.events import events
from app.core.fault import faults
from app.db.changes import write_change
from app.db.session import get_session, session_scope
from app.domains.auth.model import OrgSyncBatch, OrgSyncDiff, OrgSyncEvent, UserMapping
from app.domains.system.model import Dept, DictData, User, UserDept
from app.domains.system.service import _rewrite_paths
from app.domains.todo.model import Todo, TodoAssignee
from app.integrations.dingtalk.client import list_directory
from app.services.position import apply_position_change
from app.services.sessions import revoke_user

_META_KEYS = {"eventId", "eventType", "eventTime", "payload"}
_RETRY_MINUTES = (1, 5, 15, 60)
_OPEN_STATUSES = {"PENDING"}


def process_event(body: dict) -> dict:
    session = get_session()
    event_id = str((body or {}).get("eventId") or "").strip()
    if not event_id:
        raise BizError(1001, data={"fieldErrors": [{"field": "eventId", "message": "事件编号不能为空"}]})
    row = session.scalar(select(OrgSyncEvent).where(OrgSyncEvent.event_id == event_id))
    if row is None:
        row = _insert_event(body)
        session.flush()
        return _execute(row)
    if row.status in _OPEN_STATUSES:
        incoming = _business_payload(body)
        if incoming:
            row.payload = incoming
        if body.get("eventType"):
            row.event_type = str(body["eventType"])
        if body.get("eventTime"):
            row.event_time = parse_input_datetime(str(body["eventTime"]))
        return _execute(row)
    return {"duplicated": True}


def drive_retries() -> list[dict]:
    session = get_session()
    current = now_naive()
    rows = list(
        session.scalars(
            select(OrgSyncEvent).where(
                OrgSyncEvent.status == "RETRYING",
                OrgSyncEvent.next_retry_at.is_not(None),
                OrgSyncEvent.next_retry_at <= current,
            )
        )
    )
    return [_execute(row) for row in rows]


def replay(event_id: str) -> dict:
    session = get_session()
    row = session.scalar(select(OrgSyncEvent).where(OrgSyncEvent.event_id == event_id))
    if row is None:
        raise BizError(1504)
    row.status = "PENDING"
    row.retry_count = 0
    row.next_retry_at = None
    row.last_error = None
    session.flush()
    return _execute(row)


def reconcile() -> dict:
    session = get_session()
    running = session.scalar(select(OrgSyncBatch).where(OrgSyncBatch.status == "RUNNING"))
    if running is not None:
        raise BizError(1001, "同步正在进行中")
    try:
        directory = list_directory()
    except BizError as exc:
        _persist_failed_batch(exc.code)
        raise
    batch = OrgSyncBatch(
        started_at=now_naive(),
        status="RUNNING",
        same_name_notes=[],
        dept_created=0,
        dept_updated=0,
        dept_disabled=0,
        user_created=0,
        user_updated=0,
        user_resigned=0,
        unassigned_count=0,
        fail_count=0,
    )
    session.add(batch)
    session.flush()
    remote_depts = list(directory.get("departments") or [])
    remote_users = list(directory.get("users") or [])
    seen_depts = _sync_remote_depts(batch, remote_depts)
    _disable_missing_depts(batch, seen_depts)
    seen_users = _sync_remote_users(batch, remote_users)
    _resign_missing_users(batch, seen_users)
    batch.status = "SUCCESS"
    batch.finished_at = now_naive()
    session.flush()
    return _batch_view(batch)


def latest_batch() -> dict | None:
    row = get_session().scalar(select(OrgSyncBatch).order_by(OrgSyncBatch.id.desc()))
    if row is None:
        return None
    return _batch_view(row)


def _execute(row: OrgSyncEvent) -> dict:
    try:
        faults.raise_if("org.fail")
    except Exception as exc:
        _mark_retry(row, exc)
        return {"duplicated": False, "status": row.status, "retryCount": row.retry_count}
    _dispatch(row)
    if row.status != "EXPIRED":
        row.status = "SUCCESS"
    row.processed_at = now_naive()
    row.next_retry_at = None
    row.last_error = None
    _publish_delay(row)
    return {"duplicated": False, "status": row.status, "retryCount": row.retry_count}


def _mark_retry(row: OrgSyncEvent, exc: Exception) -> None:
    row.retry_count = int(row.retry_count or 0) + 1
    row.last_error = str(exc)[:255]
    row.processed_at = None
    if row.retry_count >= 5:
        row.status = "DEAD"
        row.next_retry_at = None
        return
    row.status = "RETRYING"
    row.next_retry_at = now_naive() + timedelta(minutes=_RETRY_MINUTES[row.retry_count - 1])


def _publish_delay(row: OrgSyncEvent) -> None:
    if row.processed_at is None or row.event_time is None:
        return
    if row.processed_at - row.event_time > timedelta(minutes=5):
        events.publish("org.delay", {"eventId": row.event_id})


def _insert_event(body: dict) -> OrgSyncEvent:
    event_time = None
    if body.get("eventTime"):
        event_time = parse_input_datetime(str(body["eventTime"]))
    row = OrgSyncEvent(
        event_id=str(body["eventId"]),
        event_type=str(body.get("eventType") or ""),
        event_time=event_time,
        payload=_business_payload(body),
        status="PENDING",
        retry_count=0,
    )
    get_session().add(row)
    return row


def _business_payload(body: dict) -> dict:
    if not isinstance(body, dict):
        return {}
    base = {key: value for key, value in body.items() if key not in _META_KEYS}
    extra = body.get("payload")
    if isinstance(extra, dict):
        base.update(extra)
    return base


def _fields(row: OrgSyncEvent) -> dict:
    raw = row.payload or {}
    if not isinstance(raw, dict):
        return {}
    if any(key in raw for key in _META_KEYS):
        return _business_payload(raw)
    return raw


def _dispatch(row: OrgSyncEvent) -> None:
    payload = _fields(row)
    kind = row.event_type or ""
    if kind.startswith("dept_"):
        _dept_event(row, payload)
        return
    if kind.startswith("user_"):
        _user_event(row, payload)


def _dept_event(row: OrgSyncEvent, payload: dict) -> None:
    ding_id = _first_int(payload, "dingtalkDeptId", "deptId")
    dept = _dept_by_ding(ding_id) if ding_id is not None else None
    if dept is not None and _is_stale(row.event_time, dept.last_sync_at):
        row.status = "EXPIRED"
        return
    if row.event_type == "dept_remove":
        if dept is not None and dept.source == "DINGTALK":
            _retire_ding_dept(dept, {dept.id})
            dept.last_sync_at = row.event_time or now_naive()
        return
    if row.event_type == "dept_add" and dept is not None:
        raise BizError(1001, data={"fieldErrors": [{"field": "dingtalkDeptId", "message": "钉钉部门编号已存在"}]})
    if row.event_type == "dept_add" and dept is None:
        parent = _parent_from_payload(payload)
        name = str(payload.get("name") or "")
        if ding_id is None or not name:
            raise BizError(1001, data={"fieldErrors": [{"field": "dingtalkDeptId", "message": "部门事件缺少钉钉部门"}]})
        dept = _insert_ding_dept(parent, ding_id, name, row.event_time or now_naive())
    elif dept is not None and dept.source == "DINGTALK":
        _override_name(dept, payload.get("name"))
        if "parentDingtalkDeptId" in payload or "parentId" in payload:
            _apply_parent(dept, _parent_from_payload(payload))
    if dept is not None and dept.source == "DINGTALK":
        dept.last_sync_at = row.event_time or now_naive()


def _user_event(row: OrgSyncEvent, payload: dict) -> None:
    ding_id = _user_ding_id(payload)
    if not ding_id:
        raise BizError(1001, data={"fieldErrors": [{"field": "dingtalkUserId", "message": "缺少钉钉用户"}]})
    mapping = _mapping(ding_id)
    stamp = mapping.last_sync_time if mapping is not None else None
    if _is_stale(row.event_time, stamp):
        row.status = "EXPIRED"
        return
    if row.event_type == "user_leave":
        _leave_user(mapping)
    elif mapping is None:
        _create_ding_user(ding_id, payload, row.event_id, batch_id=None, stamp=row.event_time)
    else:
        user = get_session().get(User, mapping.user_id)
        if user is not None:
            _update_ding_user(user, mapping, payload, row.event_id, batch_id=None, stamp=row.event_time)
    if row.status == "EXPIRED":
        return
    current = _mapping(ding_id)
    if current is None:
        return
    current.last_sync_time = row.event_time or now_naive()
    if row.event_type != "user_leave":
        current.sync_status = "SUCCESS"
    if "deptIds" in payload:
        current.dept_ids = _ding_id_list(payload.get("deptIds"))


def _sync_remote_depts(batch: OrgSyncBatch, remote_depts: list[dict]) -> set[int]:
    seen: set[int] = set()
    for item in _order_depts(remote_depts):
        ding_id = _first_int(item, "dingtalkDeptId", "deptId", "id")
        if ding_id is None:
            continue
        seen.add(ding_id)
        name = str(item.get("name") or "")
        parent = _parent_from_payload(item)
        existing = _dept_by_ding(ding_id)
        if existing is not None and existing.source != "DINGTALK":
            continue
        if existing is None:
            if not name:
                continue
            _note_same_name(batch, parent.id, name)
            _insert_ding_dept(parent, ding_id, name, now_naive())
            batch.dept_created = int(batch.dept_created or 0) + 1
            continue
        changed = False
        if name and existing.name != name:
            _override_name(existing, name)
            changed = True
        if _apply_parent(existing, parent):
            changed = True
        existing.last_sync_at = now_naive()
        if changed:
            batch.dept_updated = int(batch.dept_updated or 0) + 1
    return seen


def _disable_missing_depts(batch: OrgSyncBatch, seen: set[int]) -> None:
    rows = list(get_session().scalars(select(Dept).where(Dept.source == "DINGTALK")))
    missing = [row for row in rows if row.dingtalk_dept_id is not None and int(row.dingtalk_dept_id) not in seen]
    skip = {row.id for row in missing}
    for row in sorted(missing, key=lambda item: len(item.path or ""), reverse=True):
        moved = _retire_ding_dept(row, skip)
        batch.dept_disabled = int(batch.dept_disabled or 0) + 1
        batch.unassigned_count = int(batch.unassigned_count or 0) + moved


def _sync_remote_users(batch: OrgSyncBatch, remote_users: list[dict]) -> set[str]:
    seen: set[str] = set()
    for item in remote_users:
        ding_id = _user_ding_id(item)
        if not ding_id:
            continue
        seen.add(ding_id)
        mapping = _mapping(ding_id)
        event_id = f"reconcile-{batch.id}-{ding_id}"
        if mapping is None:
            _create_ding_user(ding_id, item, event_id, batch_id=batch.id, stamp=now_naive())
            batch.user_created = int(batch.user_created or 0) + 1
        else:
            user = get_session().get(User, mapping.user_id)
            if user is not None:
                _update_ding_user(user, mapping, item, event_id, batch_id=batch.id, stamp=now_naive())
                batch.user_updated = int(batch.user_updated or 0) + 1
        current = _mapping(ding_id)
        if current is not None:
            current.last_sync_time = now_naive()
            current.sync_status = "SUCCESS"
            if "deptIds" in item or "dept_ids" in item:
                current.dept_ids = _ding_id_list(item.get("deptIds", item.get("dept_ids")))
    return seen


def _resign_missing_users(batch: OrgSyncBatch, seen: set[str]) -> None:
    rows = list(get_session().scalars(select(UserMapping)))
    for mapping in rows:
        if mapping.dingtalk_user_id in seen:
            continue
        user = get_session().get(User, mapping.user_id)
        if user is None or user.status == "RESIGNED":
            continue
        _mark_resigned(user)
        mapping.sync_status = "RESIGNED"
        batch.user_resigned = int(batch.user_resigned or 0) + 1


def _create_ding_user(ding_id: str, payload: dict, event_id: str, batch_id: int | None, stamp) -> User:
    session = get_session()
    nickname = str(payload.get("nickname") or payload.get("name") or ding_id)[:50]
    user = User(
        username=_unique_username(ding_id),
        nickname=nickname,
        password_hash=None,
        status="ACTIVE",
        source="DINGTALK",
    )
    mobile = payload.get("mobile")
    if mobile:
        user.mobile_enc = encrypt(str(mobile))
        user.mobile_hash = hmac_hash(str(mobile))
    session.add(user)
    session.flush()
    _apply_emp(user, payload, batch_id=batch_id, ding_user_id=ding_id, on_create=True)
    _replace_ding_memberships(user, _ding_id_list(payload.get("deptIds")))
    _apply_position(user, payload, event_id)
    session.add(
        UserMapping(
            user_id=user.id,
            dingtalk_user_id=ding_id,
            dept_ids=_ding_id_list(payload.get("deptIds")),
            sync_status="SUCCESS",
            last_sync_time=stamp or now_naive(),
        )
    )
    session.flush()
    return user


def _update_ding_user(user: User, mapping: UserMapping, payload: dict, event_id: str, batch_id: int | None, stamp) -> None:
    if payload.get("nickname") or payload.get("name"):
        user.nickname = str(payload.get("nickname") or payload.get("name"))[:50]
    mobile = payload.get("mobile")
    if mobile:
        user.mobile_enc = encrypt(str(mobile))
        user.mobile_hash = hmac_hash(str(mobile))
    _apply_emp(user, payload, batch_id=batch_id, ding_user_id=mapping.dingtalk_user_id, on_create=False)
    if "deptIds" in payload or "dept_ids" in payload:
        _replace_ding_memberships(user, _ding_id_list(payload.get("deptIds", payload.get("dept_ids"))))
    _apply_position(user, payload, event_id)
    mapping.last_sync_time = stamp or now_naive()
    if "deptIds" in payload or "dept_ids" in payload:
        mapping.dept_ids = _ding_id_list(payload.get("deptIds", payload.get("dept_ids")))


def _leave_user(mapping: UserMapping | None) -> None:
    if mapping is None:
        return
    user = get_session().get(User, mapping.user_id)
    if user is None:
        return
    _mark_resigned(user)
    mapping.sync_status = "RESIGNED"


def _mark_resigned(user: User) -> None:
    if user.status == "RESIGNED":
        return
    user.status = "RESIGNED"
    revoke_user(user.id)
    events.publish("user.resigned", {"userId": user.id})


def _apply_emp(user: User, payload: dict, *, batch_id: int | None, ding_user_id: str, on_create: bool) -> None:
    present = on_create or "empNo" in payload or "emp_no" in payload
    if not present:
        return
    if "empNo" in payload:
        remote = payload.get("empNo")
    elif "emp_no" in payload:
        remote = payload.get("emp_no")
    else:
        remote = None
    remote_text = "" if remote is None else str(remote).strip()
    ims_text = "" if user.emp_no is None else str(user.emp_no).strip()
    if remote_text == "":
        _add_diff(batch_id, "EMP_NO_MISSING", "工号缺失", user.id, ding_user_id, ims_text, "")
        return
    if ims_text == "":
        user.emp_no = remote_text
        return
    if ims_text != remote_text:
        _add_diff(batch_id, "EMP_NO_MISMATCH", "工号不一致", user.id, ding_user_id, ims_text, remote_text)


def _add_diff(batch_id, diff_type: str, label: str, user_id: int, ding_user_id: str, ims_value: str, remote_value: str) -> None:
    get_session().add(
        OrgSyncDiff(
            batch_id=batch_id,
            diff_type=diff_type,
            diff_label=label,
            user_id=user_id,
            dingtalk_user_id=ding_user_id,
            ims_value=ims_value or None,
            remote_value=remote_value or None,
        )
    )


def _apply_position(user: User, payload: dict, event_id: str) -> None:
    code = payload.get("positionCode")
    if code in (None, ""):
        return
    text = str(code).strip()
    if not text:
        return
    _ensure_position(text)
    apply_position_change(user.id, text, event_id)


def _ensure_position(code: str) -> None:
    session = get_session()
    row = session.scalar(
        select(DictData)
        .where(DictData.dict_type == "dict_position", DictData.dict_value == code)
        .execution_options(skip_tenant=True)
    )
    if row is not None:
        return
    session.add(
        DictData(
            dict_type="dict_position",
            dict_value=code[:64],
            dict_label=code[:50],
            color_type="neutral",
            sort=0,
            status="ENABLED",
            is_builtin=0,
            source="DINGTALK",
            tenant_id=1,
        )
    )
    session.flush()


def _replace_ding_memberships(user: User, ding_ids: list[int]) -> None:
    session = get_session()
    current = list(session.scalars(select(UserDept).where(UserDept.user_id == user.id)))
    local_rows = [row for row in current if row.source != "DINGTALK"]
    for row in current:
        if row.source == "DINGTALK":
            session.delete(row)
    session.flush()
    local_ids = {row.dept_id for row in local_rows}
    resolved: list[Dept] = []
    for ding_id in ding_ids:
        dept = _dept_by_ding(ding_id)
        if dept is None or dept.status != "ENABLED":
            continue
        resolved.append(dept)
        if dept.id in local_ids:
            continue
        session.add(UserDept(user_id=user.id, dept_id=dept.id, is_main=0, source="DINGTALK"))
    session.flush()
    links = list(session.scalars(select(UserDept).where(UserDept.user_id == user.id)))
    if resolved:
        main_id = resolved[0].id
        for link in links:
            link.is_main = 1 if link.dept_id == main_id else 0
        user.main_dept_id = main_id
        return
    if local_rows:
        main = next((row for row in links if row.dept_id in local_ids and row.is_main), None)
        if main is None:
            main = next(row for row in links if row.dept_id in local_ids)
        for link in links:
            link.is_main = 1 if link.id == main.id else 0
        user.main_dept_id = main.dept_id
        return
    pending = _pending_dept()
    session.add(UserDept(user_id=user.id, dept_id=pending.id, is_main=1, source="LOCAL"))
    user.main_dept_id = pending.id


def _retire_ding_dept(dept: Dept, skip_ids: set[int]) -> int:
    if dept.source != "DINGTALK":
        return 0
    _reparent_local_children(dept, skip_ids)
    moved = _move_members(dept, skip_ids)
    dept.status = "DISABLED"
    dept.deleted = dept.id
    return moved


def _reparent_local_children(dept: Dept, skip_ids: set[int]) -> None:
    children = list(get_session().scalars(select(Dept).where(Dept.parent_id == dept.id, Dept.source == "LOCAL")))
    if not children:
        return
    ancestor = _alive_ancestor(int(dept.parent_id or 0), skip_ids | {dept.id})
    for child in children:
        child.parent_id = ancestor.id
        child.local_orphan = 1
        _rewrite_paths(child, ancestor.path)
        _add_todo(f"请确认本地部门{child.name}的归属", "DEPT_ORPHAN", child.id)


def _move_members(dept: Dept, skip_ids: set[int]) -> int:
    session = get_session()
    links = list(session.scalars(select(UserDept).where(UserDept.dept_id == dept.id)))
    pending = _pending_dept()
    moved = 0
    blocked = set(skip_ids) | {dept.id}
    for link in links:
        user = session.get(User, link.user_id)
        others = list(session.scalars(select(UserDept).where(UserDept.user_id == link.user_id, UserDept.id != link.id)))
        session.delete(link)
        session.flush()
        if user is None:
            continue
        dest = None
        for other in others:
            target = session.get(Dept, other.dept_id)
            if target is None or target.id in blocked:
                continue
            if target.source == "DINGTALK" and target.status == "ENABLED" and int(target.deleted or 0) == 0:
                dest = other
                break
        if dest is not None:
            for other in others:
                other.is_main = 1 if other.id == dest.id else 0
            user.main_dept_id = dest.dept_id
            continue
        moved += 1
        for other in others:
            other.is_main = 0
        existing = next((other for other in others if other.dept_id == pending.id), None)
        if existing is None:
            session.add(UserDept(user_id=user.id, dept_id=pending.id, is_main=1, source="LOCAL"))
        else:
            existing.is_main = 1
        user.main_dept_id = pending.id
    _add_todo(f"有{moved}人已转入待分配", "DEPT_UNASSIGNED", dept.id)
    return moved


def _alive_ancestor(start_parent_id: int, skip_ids: set[int]) -> Dept:
    session = get_session()
    parent_id = start_parent_id
    seen: set[int] = set()
    while parent_id and parent_id not in seen:
        seen.add(parent_id)
        if parent_id not in skip_ids:
            parent = session.get(Dept, parent_id)
            if parent is not None and int(parent.deleted or 0) == 0 and parent.status == "ENABLED":
                return parent
        raw = session.scalar(select(Dept).where(Dept.id == parent_id).execution_options(include_deleted=True, skip_tenant=True))
        if raw is None:
            break
        parent_id = int(raw.parent_id or 0)
    return _root_dept()


def _apply_parent(dept: Dept, parent: Dept) -> bool:
    if parent.id == dept.parent_id:
        return False
    previous = get_session().get(Dept, int(dept.parent_id or 0))
    before = previous.name if previous is not None else str(dept.parent_id)
    write_change("ims_sys_dept", dept.id, "parent_id", "上级部门", before, parent.name, "DINGTALK_OVERRIDE")
    dept.parent_id = parent.id
    _rewrite_paths(dept, parent.path)
    return True


def _persist_failed_batch(code: int) -> None:
    """钉钉不可用时单独提交失败批次。请求事务回滚后组织数据仍与对账前一致。"""
    with session_scope(commit=True) as extra:
        extra.add(
            OrgSyncBatch(
                started_at=now_naive(),
                finished_at=now_naive(),
                status="FAILED",
                error_code=int(code),
                fail_count=1,
                same_name_notes=[],
                dept_created=0,
                dept_updated=0,
                dept_disabled=0,
                user_created=0,
                user_updated=0,
                user_resigned=0,
                unassigned_count=0,
            )
        )


def _override_name(dept: Dept, name) -> None:
    if not name or str(name) == dept.name:
        return
    new_name = str(name)
    write_change("ims_sys_dept", dept.id, "name", "部门名称", dept.name, new_name, "DINGTALK_OVERRIDE")
    dept.name = new_name


def _note_same_name(batch: OrgSyncBatch, parent_id: int, name: str) -> None:
    sibling = get_session().scalar(
        select(Dept).where(Dept.parent_id == parent_id, Dept.name == name, Dept.source == "LOCAL")
    )
    if sibling is None:
        return
    notes = list(batch.same_name_notes or [])
    notes.append("存在同名本地部门")
    batch.same_name_notes = notes


def _insert_ding_dept(parent: Dept, ding_id: int, name: str, stamp) -> Dept:
    session = get_session()
    row = Dept(
        parent_id=parent.id,
        name=str(name)[:50],
        source="DINGTALK",
        status="ENABLED",
        path="/",
        dingtalk_dept_id=int(ding_id),
        last_sync_at=stamp,
        local_orphan=0,
        sort=0,
    )
    session.add(row)
    try:
        session.flush()
    except IntegrityError as exc:
        raise BizError(1001, data={"fieldErrors": [{"field": "dingtalkDeptId", "message": "钉钉部门编号已存在"}]}) from exc
    row.path = f"{parent.path}{row.id}/"
    return row


def _add_todo(title: str, source_type: str, source_id: int) -> None:
    session = get_session()
    todo = Todo(
        type="CONFIRM",
        source_module="org",
        source_type=source_type,
        source_id=int(source_id),
        title=title[:200],
        status="PENDING",
        assignee_perm_code="ims:system:user:update",
    )
    session.add(todo)
    session.flush()
    for user_id in _holders("ims:system:user:update"):
        session.add(TodoAssignee(todo_id=todo.id, user_id=user_id))


def _holders(perm: str) -> list[int]:
    from app.domains.system.model import Menu, RoleMenu, UserRole

    session = get_session()
    menu_ids = [row.id for row in session.scalars(select(Menu).where(Menu.perm_code == perm))]
    if not menu_ids:
        return []
    role_ids = [row.role_id for row in session.scalars(select(RoleMenu).where(RoleMenu.menu_id.in_(menu_ids)))]
    if not role_ids:
        return []
    return list(
        {
            row.user_id
            for row in session.scalars(select(UserRole).where(UserRole.role_id.in_(role_ids), UserRole.manual_removed == 0))
        }
    )


def _dept_by_ding(ding_id: int | None) -> Dept | None:
    if ding_id is None:
        return None
    return get_session().scalar(select(Dept).where(Dept.dingtalk_dept_id == int(ding_id)))


def _mapping(ding_id: str) -> UserMapping | None:
    return get_session().scalar(select(UserMapping).where(UserMapping.dingtalk_user_id == ding_id))


def _root_dept() -> Dept:
    row = get_session().scalar(select(Dept).where(Dept.parent_id == 0))
    if row is None:
        raise BizError(1504)
    return row


def _pending_dept() -> Dept:
    row = get_session().scalar(select(Dept).where(Dept.source == "SYSTEM", Dept.name == "待分配"))
    if row is None:
        raise BizError(1001, "没有待分配部门")
    return row


def _parent_from_payload(payload: dict) -> Dept:
    parent_ding = _first_int(payload, "parentDingtalkDeptId", "parentId")
    if parent_ding in (None, 0):
        return _root_dept()
    parent = _dept_by_ding(parent_ding)
    if parent is None or parent.source != "DINGTALK":
        return _root_dept()
    return parent


def _unique_username(ding_id: str) -> str:
    raw = "".join(ch for ch in str(ding_id) if ch.isalnum() or ch in {"_", "-"})
    base = (raw or "ding")[:28]
    session = get_session()
    name = base
    index = 0
    while session.scalar(select(User).where(User.username == name).execution_options(skip_tenant=True)):
        index += 1
        name = f"{base[:22]}_{index}"
    return name[:30]


def _order_depts(items: list[dict]) -> list[dict]:
    keyed: dict[int, dict] = {}
    for item in items:
        ding_id = _first_int(item, "dingtalkDeptId", "deptId", "id")
        if ding_id is not None:
            keyed[ding_id] = item
    ordered: list[dict] = []
    seen: set[int] = set()

    def visit(item: dict) -> None:
        ding_id = _first_int(item, "dingtalkDeptId", "deptId", "id")
        if ding_id is None or ding_id in seen:
            return
        parent_id = _first_int(item, "parentDingtalkDeptId", "parentId")
        if parent_id and parent_id in keyed and parent_id not in seen:
            visit(keyed[parent_id])
        seen.add(ding_id)
        ordered.append(item)

    for item in items:
        visit(item)
    return ordered


def _user_ding_id(payload: dict) -> str:
    for key in ("dingtalkUserId", "userid", "userId"):
        value = payload.get(key)
        if value not in (None, ""):
            return str(value)
    return ""


def _ding_id_list(value) -> list[int]:
    if not value:
        return []
    result = []
    for item in value:
        if item in (None, ""):
            continue
        result.append(int(item))
    return result


def _first_int(payload: dict, *keys: str) -> int | None:
    for key in keys:
        if key not in payload:
            continue
        value = payload.get(key)
        if value in (None, ""):
            return None
        return int(value)
    return None


def _is_stale(event_time, last_sync) -> bool:
    if event_time is None or last_sync is None:
        return False
    return event_time < last_sync


def _batch_view(row: OrgSyncBatch) -> dict:
    from app.api.dump import dump_row

    return dump_row(row)
