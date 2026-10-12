"""证件到期扫描、换证与催办。同级别不重复推送，升级才再推。"""
from __future__ import annotations

from sqlalchemy import select

from app.core.clock import format_datetime, now_naive, today
from app.core.errors import BizError
from app.core.pagination import Page, page_result
from app.db.repository import assert_dict_values
from app.db.session import get_session
from app.domains.cert.model import CertExpireTask
from app.domains.cert.support import (
    holder,
    ident_of,
    load_cert,
    masked_no,
    remain,
    scope_realname_ids,
    status_label,
    task_label,
    warn_label,
    warn_level_for,
)
from app.domains.master.model import Cert
from app.domains.resource.common import one, text_of, user_ids_with_perm, user_map

_KEYS = {"YELLOW": "notify.cert.yellow", "RED": "notify.cert.red", "LOCKED": "notify.cert.locked"}


def is_locked(realname_id: int) -> bool:
    """供开播登记调用：实名人存在未删除的已过期证件即为锁定。"""
    row = get_session().scalar(select(Cert.id).where(Cert.realname_id == int(realname_id), Cert.status == "EXPIRED"))
    return row is not None


def _task_of(ident: int) -> CertExpireTask:
    row = get_session().get(CertExpireTask, int(ident))
    if row is None or row.deleted:
        raise BizError(1039)
    return row


def _append(task: CertExpireTask, title: str, detail: str) -> None:
    trace = list(task.trace or [])
    trace.append({"time": format_datetime(now_naive()), "title": title, "detail": detail})
    task.trace = trace


def _targets(cert: Cert) -> tuple[list[int], str]:
    person = holder(cert.realname_id)
    admins = user_ids_with_perm("ims:cert:expire:renew")
    holder_id = int(person["holderUserId"]) if person.get("holderUserId") else 0
    ids = []
    if holder_id:
        ids.append(holder_id)
    for item in admins:
        if item not in ids:
            ids.append(item)
    if holder_id:
        note = "已通知：本人、行政" if admins else "已通知：本人"
        hint = ""
    else:
        note = "已通知：行政"
        hint = "持有人未关联员工，仅通知行政"
    return ids, hint or note


def ensure_task(cert: Cert, level: str, *, notify: bool) -> CertExpireTask:
    session = get_session()
    task = session.scalar(select(CertExpireTask).where(CertExpireTask.cert_id == cert.id, CertExpireTask.status != "RENEW_RESOLVED"))
    previous = task.level if task is not None else ""
    if task is None:
        task = CertExpireTask(cert_id=cert.id, level=level, status="WARNING", notified_user_ids=[], remind_count=0, trace=[])
        session.add(task)
        session.flush()
    upgraded = previous != level
    if level == "LOCKED":
        cert.status = "EXPIRED"
        task.status = "EXPIRED_LOCKED"
    elif level in {"YELLOW", "RED"} and cert.status != "EXPIRED":
        cert.status = "EXPIRING"
        if task.status != "EXPIRED_LOCKED":
            task.status = "WARNING"
    task.level = level
    assert_dict_values(cert)
    assert_dict_values(task)
    if notify and (upgraded or not task.last_notified_at):
        ids, note = _targets(cert)
        from app.domains.cert.notify import deep_link, deliver

        sent = deliver(ids, _KEYS[level], "cert_expire", f"cert:{cert.id}:{level}", deep_link(cert.id), {"SITE", "DINGTALK"})
        task.notified_user_ids = sent
        task.last_notified_at = now_naive()
        _append(task, warn_label(level), note)
    session.flush()
    return task


def scan() -> dict:
    session = get_session()
    rows = list(session.scalars(select(Cert).where(Cert.status.in_(("EFFECTIVE", "EXPIRING", "EXPIRED")))))
    created = 0
    notified = 0
    for row in rows:
        level = warn_level_for(row.expire_date)
        if level is None:
            continue
        before = session.scalar(select(CertExpireTask.id).where(CertExpireTask.cert_id == row.id))
        task = ensure_task(row, level, notify=True)
        if before is None:
            created += 1
        if task.last_notified_at and task.last_notified_at.date() == today() and task.level == level:
            notified += 1
    return {"scanned": len(rows), "created": created, "notified": notified}


def _names(ids: list | None) -> str:
    clean = [int(item) for item in (ids or []) if item]
    users = user_map(clean)
    labels = []
    for item in clean:
        user = users.get(item)
        labels.append(user.nickname if user is not None and user.nickname else str(item))
    return "、".join(labels)


def _view(task: CertExpireTask) -> dict:
    cert = load_cert(task.cert_id)
    person = holder(cert.realname_id)
    _, note = _targets(cert)
    notified = _names(task.notified_user_ids)
    data = {
        "id": task.id,
        "certId": cert.id,
        "holderName": person["holderName"],
        "external": person["external"],
        "certType": cert.cert_type or "",
        "certNoMasked": masked_no(cert),
        "expireDate": cert.expire_date.isoformat() if cert.expire_date else "",
        "level": task.level,
        "levelLabel": warn_label(task.level),
        "status": task.status,
        "statusLabel": task_label(task.status),
        "certStatus": cert.status,
        "certStatusLabel": status_label(cert.status),
        "notifyText": f"已通知：{notified}" if notified else note,
        "notifyHint": "持有人未关联员工，仅通知行政" if person["external"] else "",
        "remindCount": task.remind_count,
        "trace": task.trace or [],
        "realnameId": cert.realname_id,
    }
    data.update(remain(cert.expire_date))
    return data


def _visible_cert_ids() -> list[int] | None:
    allowed = scope_realname_ids()
    if allowed is None:
        return None
    if allowed == [-1]:
        return [-1]
    rows = get_session().scalars(select(Cert.id).where(Cert.realname_id.in_(allowed)))
    found = [int(item) for item in rows]
    return found or [-1]


def page(page_query: Page, params: dict) -> dict:
    where = []
    visible = _visible_cert_ids()
    if visible is not None:
        where.append(CertExpireTask.cert_id.in_(visible))
    if text_of(params, "level"):
        where.append(CertExpireTask.level == text_of(params, "level"))
    if text_of(params, "status"):
        where.append(CertExpireTask.status == text_of(params, "status"))
    if text_of(params, "realnameId"):
        cert_ids = [int(item) for item in get_session().scalars(select(Cert.id).where(Cert.realname_id == ident_of(params.get("realnameId"))))]
        where.append(CertExpireTask.cert_id.in_(cert_ids or [-1]))
    from app.db.repository import Repository

    rows, total = Repository(CertExpireTask).page(page_query, *where, order=[CertExpireTask.update_time.desc(), CertExpireTask.id.desc()])
    return page_result([_view(row) for row in rows], total, page_query)


def stats() -> dict:
    visible = _visible_cert_ids()
    session = get_session()
    stmt = select(CertExpireTask)
    if visible is not None:
        stmt = stmt.where(CertExpireTask.cert_id.in_(visible))
    rows = list(session.scalars(stmt))
    month = today().strftime("%Y-%m")
    renewed = 0
    for row in rows:
        if row.status == "RENEW_RESOLVED" and row.update_time and row.update_time.strftime("%Y-%m") == month:
            renewed += 1
    return {
        "yellow": sum(1 for row in rows if row.level == "YELLOW" and row.status == "WARNING"),
        "red": sum(1 for row in rows if row.level == "RED" and row.status == "WARNING"),
        "locked": sum(1 for row in rows if row.status == "EXPIRED_LOCKED" or row.level == "LOCKED"),
        "renewedMonth": renewed,
    }


def renew(ident: int, body: dict) -> dict:
    task = _task_of(ident)
    if not body.get("newCertId"):
        one("newCertId", "请先上传新证")
    new_cert = load_cert(ident_of(body.get("newCertId")))
    old = load_cert(task.cert_id)
    if new_cert.renew_of_cert_id and int(new_cert.renew_of_cert_id) != int(old.id):
        one("newCertId", "新证未关联当前旧证")
    if new_cert.realname_id != old.realname_id or new_cert.cert_type != old.cert_type:
        one("newCertId", "换证须沿用原持有人与证件类型")
    if not new_cert.renew_of_cert_id:
        new_cert.renew_of_cert_id = old.id
        get_session().flush()
    _append(task, "换证登记", "新证需审核生效后旧证自动归档")
    get_session().flush()
    data = _view(task)
    data["hint"] = "新证需审核生效后旧证自动归档"
    data["newCertId"] = new_cert.id
    return data


def remind(ident: int, body: dict) -> dict:
    task = _task_of(ident)
    channel = text_of(body, "channel") or "BOTH"
    if channel not in {"SITE", "DINGTALK", "BOTH"}:
        one("channel", "请选择通知渠道")
    channels = {"SITE", "DINGTALK"} if channel == "BOTH" else {channel}
    cert = load_cert(task.cert_id)
    ids, note = _targets(cert)
    from app.domains.cert.notify import deep_link, deliver

    deliver(ids, "notify.cert.remind", "cert_remind", f"cert-remind:{task.id}:{int(task.remind_count or 0) + 1}", deep_link(cert.id), channels)
    task.remind_count = int(task.remind_count or 0) + 1
    task.last_notified_at = now_naive()
    _append(task, "人工催办", note)
    get_session().flush()
    data = _view(task)
    data["hint"] = note if "仅通知行政" in note else ""
    return data


def manual_scan() -> dict:
    try:
        return scan()
    except BizError:
        raise
    except Exception as exc:
        raise BizError(5006, "扫描任务调度失败，请稍后重试") from exc
