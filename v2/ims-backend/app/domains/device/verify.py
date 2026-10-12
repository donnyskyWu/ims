"""资产关联校验。本批只跑资产与责任人、实名人。"""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func, select

from app.core.clock import now_naive, today
from app.core.errors import BizError
from app.core.pagination import Page, page_result
from app.db.repository import assert_dict_values, validate_refs_on_write
from app.db.session import get_session
from app.domains.device.ledger import load
from app.domains.device.model import AssetLedger, AssetVerifyBatch, AssetVerifyTask
from app.domains.device.support import (
    TASK_STATUS,
    VERIFY_TYPE,
    add_workdays,
    has_perm,
    limit,
    notify_both,
    one,
    parse_day,
    remember,
    replay,
    require_active_user,
    stamp_no,
    token_of,
    user_brief,
    viewer_id,
)
from app.domains.master.model import Realname
from app.domains.resource.common import text_of

_ANOMALY = {
    "OWNER_EMPTY": "责任人为空",
    "OWNER_RESIGNED": "责任人已离职",
    "REALNAME_EMPTY": "未关联实名人",
    "REALNAME_DISABLED": "实名人已停用",
}
_LOCK = "ims:asset:verify:manual"


def run(body: dict, trigger: str = "MANUAL") -> dict:
    types = _types(body)
    scope = (text_of(body, "scope") or "FULL").upper()
    if scope not in {"FULL", "INCREMENT"}:
        one("scope", "请选择全量或增量")
    cached = replay(token_of(body)) if trigger == "MANUAL" else None
    if cached:
        return cached
    if trigger == "MANUAL":
        _lock()
    try:
        payload = _execute(types, scope, trigger)
    finally:
        if trigger == "MANUAL":
            _unlock()
    if trigger == "MANUAL":
        remember(token_of(body), payload)
    return payload


def run_full() -> dict:
    return _execute(["asset_person"], "FULL", "SCHEDULE")


def run_increment() -> dict:
    return _execute(["asset_person"], "INCREMENT", "SCHEDULE")


def _types(body: dict) -> list[str]:
    raw = body.get("verifyTypes")
    if raw in (None, ""):
        raw = body.get("types") or ["asset_person"]
    if isinstance(raw, str):
        raw = [item.strip() for item in raw.split(",") if item.strip()]
    types = [str(item) for item in raw]
    if not types:
        one("verifyType", "请选择校验类型")
    blocked = [item for item in types if item != "asset_person"]
    if blocked:
        raise BizError(1001, "账号 / 场次模块上线后可用", data={"fieldErrors": [{"field": "verifyType", "message": "账号 / 场次模块上线后可用"}]})
    return types


def _lock() -> None:
    from app.core.redis_client import get_redis

    if not get_redis().set(_LOCK, "1", nx=True, ex=120):
        raise BizError(5006, "调度繁忙，请稍后重试")


def _unlock() -> None:
    from app.core.redis_client import get_redis

    get_redis().delete(_LOCK)


def _execute(types: list[str], scope: str, trigger: str) -> dict:
    session = get_session()
    batch = AssetVerifyBatch(
        batch_no=stamp_no("VB"),
        verify_type=types[0],
        scope=scope,
        trigger_type="SCHEDULE" if trigger == "SCHEDULE" else "MANUAL",
        status="RUNNING",
    )
    session.add(batch)
    session.flush()
    assert_dict_values(batch)
    rows = _targets(scope)
    batch.total_count = len(rows)
    found_assets: set[int] = set()
    created = 0
    index = 0
    for row in rows:
        for code, fields in _anomalies(row):
            found_assets.add(int(row.id))
            if _open_task(row.id, code) is not None:
                continue
            index += 1
            task = AssetVerifyTask(
                task_no=f"{stamp_no('VT')}{index:03d}",
                batch_no=batch.batch_no,
                batch_id=batch.id,
                asset_id=row.id,
                ref_type=code,
                inconsistent_fields=fields,
                task_status="PENDING_DISPATCH",
            )
            validate_refs_on_write(task)
            assert_dict_values(task)
            session.add(task)
            created += 1
    batch.error_count = len(found_assets)
    batch.status = "DONE"
    session.flush()
    return {
        "batchNo": batch.batch_no,
        "totalCount": batch.total_count,
        "errorCount": batch.error_count,
        "createdCount": created,
        "message": f"校验完成，共发现 {batch.error_count} 处异常",
    }


def _targets(scope: str) -> list[AssetLedger]:
    stmt = select(AssetLedger).where(AssetLedger.status != "SCRAPPED").order_by(AssetLedger.id.asc())
    if scope == "INCREMENT":
        since = now_naive() - timedelta(days=1)
        stmt = stmt.where(AssetLedger.update_time >= since)
    return list(get_session().scalars(stmt))


def _anomalies(row: AssetLedger) -> list[tuple[str, list[dict]]]:
    found = []
    owner = user_brief(row.owner_user_id) if row.owner_user_id else {"name": "", "resigned": False}
    if not row.owner_user_id:
        found.append(("OWNER_EMPTY", [_field("OWNER_EMPTY", "应有在职责任人", "空")]))
    elif owner["resigned"] and row.status == "IN_USE":
        found.append(("OWNER_RESIGNED", [_field("OWNER_RESIGNED", "在职责任人", f"{owner['name']}已离职")]))
    if not row.realname_id:
        found.append(("REALNAME_EMPTY", [_field("REALNAME_EMPTY", "已关联实名人", "未关联")]))
    else:
        person = get_session().get(Realname, row.realname_id)
        if person is not None and person.status != "ENABLED":
            found.append(("REALNAME_DISABLED", [_field("REALNAME_DISABLED", "启用的实名人", f"{person.name}已停用")]))
    return found


def _field(code: str, registered: str, actual: str) -> dict:
    return {"field": code, "label": _ANOMALY[code], "registered": registered, "actual": actual}


def _open_task(asset_id: int, code: str) -> AssetVerifyTask | None:
    return get_session().scalar(
        select(AssetVerifyTask).where(
            AssetVerifyTask.asset_id == int(asset_id),
            AssetVerifyTask.ref_type == code,
            AssetVerifyTask.task_status != "CLOSED",
        )
    )


def metrics() -> dict:
    session = get_session()
    rows = list(session.scalars(select(AssetLedger).where(AssetLedger.status != "SCRAPPED")))
    total = len(rows)
    complete = 0
    for row in rows:
        owner = user_brief(row.owner_user_id) if row.owner_user_id else None
        person = session.get(Realname, row.realname_id) if row.realname_id else None
        if owner and not owner["resigned"] and person is not None and person.status == "ENABLED":
            complete += 1
    completeness = None if total == 0 else round(complete / total, 4)
    batch = session.scalar(
        select(AssetVerifyBatch).where(AssetVerifyBatch.scope == "FULL", AssetVerifyBatch.status == "DONE").order_by(AssetVerifyBatch.id.desc())
    )
    consistency = None
    if batch is not None and int(batch.total_count or 0) > 0:
        consistency = round((int(batch.total_count) - int(batch.error_count or 0)) / int(batch.total_count), 4)
    open_count = int(session.scalar(select(func.count()).select_from(AssetVerifyTask).where(AssetVerifyTask.task_status != "CLOSED")) or 0)
    start = today() - timedelta(days=6)
    week = int(
        session.scalar(select(func.count()).select_from(AssetVerifyBatch).where(AssetVerifyBatch.create_time >= start.isoformat())) or 0
    )
    trend = []
    for offset in range(29, -1, -1):
        day = today() - timedelta(days=offset)
        day_batch = session.scalar(
            select(AssetVerifyBatch)
            .where(
                AssetVerifyBatch.scope == "FULL",
                AssetVerifyBatch.status == "DONE",
                func.date(AssetVerifyBatch.create_time) == day.isoformat(),
            )
            .order_by(AssetVerifyBatch.id.desc())
        )
        day_consistency = None
        if day_batch is not None and int(day_batch.total_count or 0) > 0:
            day_consistency = round((int(day_batch.total_count) - int(day_batch.error_count or 0)) / int(day_batch.total_count), 4)
        trend.append(
            {
                "date": day.isoformat(),
                "completeness": completeness if offset == 0 else None,
                "consistency": day_consistency,
            }
        )
    return {
        "completeness": _percent(completeness),
        "completenessRatio": completeness,
        "consistency": _percent(consistency),
        "consistencyRatio": consistency,
        "consistencyWarn": consistency is not None and consistency < 0.98,
        "openCount": open_count,
        "weekBatchCount": week,
        "trend": trend,
    }


def _percent(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value * 100:.1f}%"


def batches(page_query: Page, params: dict) -> dict:
    stmt = select(AssetVerifyBatch).order_by(AssetVerifyBatch.id.desc())
    batch_no = text_of(params, "batchNo")
    if batch_no:
        stmt = stmt.where(AssetVerifyBatch.batch_no.contains(batch_no))
    verify_type = text_of(params, "verifyType")
    if verify_type:
        stmt = stmt.where(AssetVerifyBatch.verify_type == verify_type)
    status = text_of(params, "status")
    if status:
        stmt = stmt.where(AssetVerifyBatch.status == status)
    start = text_of(params, "startDate") or (today() - timedelta(days=30)).isoformat()
    end = text_of(params, "endDate")
    if start:
        stmt = stmt.where(AssetVerifyBatch.create_time >= start)
    if end:
        stmt = stmt.where(AssetVerifyBatch.create_time <= end + " 23:59:59")
    rows = list(get_session().scalars(stmt))
    start_at = (page_query.page_no - 1) * page_query.page_size
    chunk = rows[start_at : start_at + page_query.page_size]
    return page_result([_batch(row) for row in chunk], len(rows), page_query)


def _batch(row: AssetVerifyBatch) -> dict:
    pending = int(
        get_session().scalar(
            select(func.count()).select_from(AssetVerifyTask).where(AssetVerifyTask.batch_no == row.batch_no, AssetVerifyTask.task_status != "CLOSED")
        )
        or 0
    )
    return {
        "id": row.id,
        "batchNo": row.batch_no,
        "verifyType": row.verify_type,
        "verifyTypeLabel": VERIFY_TYPE.get(row.verify_type, row.verify_type),
        "scope": row.scope,
        "triggerType": row.trigger_type,
        "triggerLabel": "定时" if row.trigger_type == "SCHEDULE" else "手动",
        "totalCount": row.total_count,
        "errorCount": row.error_count,
        "pendingCount": pending,
        "status": row.status,
        "statusLabel": {"RUNNING": "运行中", "DONE": "完成", "FAILED": "失败"}.get(row.status, row.status),
        "createTime": row.create_time.isoformat(sep=" ") if row.create_time else "",
    }


def errors(page_query: Page, params: dict) -> dict:
    see_all = has_perm("ims:asset:verify:query")
    stmt = select(AssetVerifyTask).order_by(AssetVerifyTask.id.desc())
    batch_no = text_of(params, "batchNo")
    if batch_no:
        stmt = stmt.where(AssetVerifyTask.batch_no == batch_no)
    status = text_of(params, "taskStatus") or text_of(params, "status")
    if status:
        stmt = stmt.where(AssetVerifyTask.task_status == status)
    task_raw = text_of(params, "taskId")
    if task_raw:
        from app.core.serialize import parse_api_id

        stmt = stmt.where(AssetVerifyTask.id == int(parse_api_id(task_raw)))
    if not see_all:
        stmt = stmt.where(AssetVerifyTask.owner_user_id == viewer_id())
    rows = list(get_session().scalars(stmt))
    if task_raw and not rows and not see_all:
        raise BizError(1008, "您无权处理该工单")
    start_at = (page_query.page_no - 1) * page_query.page_size
    chunk = rows[start_at : start_at + page_query.page_size]
    return page_result([_task(row) for row in chunk], len(rows), page_query)


def _task(row: AssetVerifyTask) -> dict:
    asset = get_session().get(AssetLedger, row.asset_id)
    fields = row.inconsistent_fields or []
    labels = [str(item.get("label") or "") for item in fields if isinstance(item, dict)]
    overdue = 0
    if row.task_status == "REPAIRING" and row.deadline and row.deadline < today():
        overdue = (today() - row.deadline).days
    owner = user_brief(row.owner_user_id)
    return {
        "id": row.id,
        "taskNo": row.task_no,
        "batchNo": row.batch_no,
        "assetId": row.asset_id,
        "assetCode": asset.asset_code if asset is not None else "",
        "assetName": asset.asset_name if asset is not None else "",
        "assetType": asset.asset_type if asset is not None else "",
        "fields": fields,
        "fieldText": "，".join(item for item in labels if item),
        "taskStatus": row.task_status,
        "statusLabel": TASK_STATUS.get(row.task_status, row.task_status),
        "ownerUserId": row.owner_user_id,
        "ownerName": owner["name"],
        "deadline": row.deadline.isoformat() if row.deadline else "",
        "overdueDays": overdue,
        "fixRemark": row.fix_remark or "",
        "recheckRemark": row.recheck_remark or "",
        "escalated": row.escalated_at is not None,
        "route": _route(asset, row.id) if asset is not None else "",
    }


def act(ident: int, body: dict) -> dict:
    row = get_session().get(AssetVerifyTask, int(ident))
    if row is None or int(row.deleted or 0) != 0:
        raise BizError(1014, "校验批次不存在或工单状态不允许此操作")
    action = text_of(body, "action")
    if action == "DISPATCH":
        _dispatch(row, body)
    elif action == "SUBMIT_FIX":
        _submit(row, body)
    elif action == "RECHECK_PASS":
        _recheck(row, body, passed=True)
    elif action == "RECHECK_REJECT":
        _recheck(row, body, passed=False)
    else:
        raise BizError(1014, "校验批次不存在或工单状态不允许此操作")
    assert_dict_values(row)
    get_session().flush()
    return _task(row)


def _dispatch(row: AssetVerifyTask, body: dict) -> None:
    if not has_perm("ims:asset:verify:dispatch"):
        raise BizError(1008, "您无权处理该工单")
    if row.task_status != "PENDING_DISPATCH":
        raise BizError(1014, "校验批次不存在或工单状态不允许此操作")
    user = require_active_user(body.get("ownerUserId") or body.get("userId"), "ownerUserId", "修复责任人")
    deadline = parse_day(body.get("deadline"), "deadline") if body.get("deadline") else add_workdays(today(), 3)
    if deadline is None:
        one("deadline", "请填写限期")
    row.owner_user_id = user.id
    row.deadline = deadline
    row.task_status = "REPAIRING"
    asset = load(row.asset_id, check_owner=False)
    route = _route(asset, row.id)
    notify_both(user.id, "校验工单待处理", f"请处理资产 {asset.asset_code} 的关联异常", route, "ASSET_VERIFY_DISPATCH", f"verify:{row.id}")
    from app.domains.todo.service import todo_create

    todo_create(
        "ASSET_VERIFY",
        int(row.id),
        "REVIEW",
        f"校验工单 {row.task_no}",
        user_ids=[user.id],
        summary=_task(row)["fieldText"],
        route=route,
        source_module="asset",
    )


def _submit(row: AssetVerifyTask, body: dict) -> None:
    if int(row.owner_user_id or 0) != viewer_id():
        raise BizError(1008, "您无权处理该工单")
    if row.task_status != "REPAIRING":
        raise BizError(1014, "校验批次不存在或工单状态不允许此操作")
    remark = limit(text_of(body, "remark") or text_of(body, "fixRemark"), "remark", "修复说明", 512, required=True)
    row.fix_remark = remark
    row.task_status = "PENDING_RECHECK"


def _recheck(row: AssetVerifyTask, body: dict, *, passed: bool) -> None:
    if not has_perm("ims:asset:verify:recheck"):
        raise BizError(1008, "您无权处理该工单")
    if row.task_status != "PENDING_RECHECK":
        raise BizError(1014, "校验批次不存在或工单状态不允许此操作")
    remark = limit(text_of(body, "remark") or text_of(body, "recheckRemark"), "remark", "复审意见", 512, required=not passed)
    row.recheck_remark = remark or row.recheck_remark
    if passed:
        row.task_status = "CLOSED"
        _close_todos(row.id)
        return
    row.task_status = "REPAIRING"
    asset = load(row.asset_id, check_owner=False)
    notify_both(
        int(row.owner_user_id or 0),
        "校验工单已退回",
        f"资产 {asset.asset_code} 复审未通过：{remark}",
        _route(asset, row.id),
        "ASSET_VERIFY_REJECT",
        f"verify-reject:{row.id}:{row.recheck_remark}",
    )


def _close_todos(task_id: int) -> None:
    from app.domains.todo.model import Todo

    rows = list(
        get_session().scalars(
            select(Todo).where(
                Todo.source_id == int(task_id),
                Todo.source_type.in_(("ASSET_VERIFY", "ASSET_VERIFY_ESCALATE")),
                Todo.status == "PENDING",
            )
        )
    )
    for item in rows:
        item.status = "DONE"
        item.done_by = viewer_id() or None


def _route(asset: AssetLedger, task_id: int) -> str:
    base = "/ims/corp/device/live" if asset.asset_type in {"LIVE", "SHOOT"} else "/ims/corp/device/office"
    return f"{base}?drawer=verify&taskId={task_id}"


def scan_overdue() -> dict:
    session = get_session()
    rows = list(
        session.scalars(
            select(AssetVerifyTask).where(
                AssetVerifyTask.task_status == "REPAIRING",
                AssetVerifyTask.deadline.is_not(None),
                AssetVerifyTask.deadline < today(),
                AssetVerifyTask.escalated_at.is_(None),
            )
        )
    )
    sent = 0
    for row in rows:
        row.escalated_at = now_naive()
        receivers = _leaders(row.owner_user_id)
        asset = session.get(AssetLedger, row.asset_id)
        route = _route(asset, row.id) if asset is not None else "/ims/corp/device/office"
        title = "校验工单已逾期"
        content = f"工单 {row.task_no} 已超过限期，请跟进"
        for user_id in receivers:
            notify_both(user_id, title, content, route, "ASSET_VERIFY_OVERDUE", f"verify-overdue:{row.id}")
        if receivers:
            from app.domains.todo.service import todo_create

            todo_create(
                "ASSET_VERIFY_ESCALATE",
                int(row.id),
                "REVIEW",
                f"逾期升级 {row.task_no}",
                user_ids=receivers,
                summary=content,
                route=route,
                source_module="asset",
            )
            sent += 1
    session.flush()
    return {"escalated": len(rows), "notified": sent}


def _leaders(owner_id: int | None) -> list[int]:
    from app.domains.system.model import Dept
    from app.domains.todo.service import users_with_perm

    owner = user_brief(owner_id)
    user = None
    if owner_id:
        from app.domains.device.support import user_of

        user = user_of(owner_id)
    if user is not None and user.main_dept_id:
        dept = get_session().get(Dept, user.main_dept_id)
        if dept is not None and dept.leader_user_id:
            leader = user_of(dept.leader_user_id)
            if leader is not None and leader.status == "ACTIVE" and int(leader.deleted or 0) == 0:
                return [int(leader.id)]
    _ = owner
    return users_with_perm("ims:asset:verify:dispatch")
