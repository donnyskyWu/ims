"""证件档案：上传、审核、列表、详情与数字化率。"""
from __future__ import annotations

from sqlalchemy import func, select

from app.core.clock import format_datetime, now_naive
from app.core.context import get_ctx
from app.core.errors import BizError
from app.core.pagination import Page, page_result
from app.db.repository import Repository, assert_dict_values, validate_refs_on_write
from app.db.session import get_session
from app.domains.cert.model import CertExpireTask, CertViewLog
from app.domains.cert.support import (
    LONG_TERM,
    holder,
    ident_of,
    load_cert,
    masked_no,
    parse_day,
    remain,
    scope_realname_ids,
    status_label,
    view_level,
)
from app.domains.master.model import Cert, Realname
from app.domains.resource.common import (
    digest,
    limit,
    next_no,
    normalize_id,
    one,
    remember,
    replay,
    text_of,
    token_of,
    valid_id_card,
    valid_passport,
)
from app.services.exchange import remember_export

_TYPE_LABEL = {
    "ID_CARD": "身份证",
    "PASSPORT": "护照",
    "HK_MACAU_TW": "港澳台通行证",
    "ANCHOR_QUAL": "主播资质证",
    "HEALTH": "健康证",
    "OTHER": "其他",
}


def _check_no(cert_type: str, number: str) -> str:
    number = normalize_id(number)
    if not number:
        one("certNoPlain", "请填写证件号")
    if cert_type == "ID_CARD" and not valid_id_card(number):
        one("certNoPlain", "身份证号格式不正确")
    elif cert_type == "PASSPORT" and not valid_passport(number):
        one("certNoPlain", "护照号须为 5 到 17 位字母或数字")
    elif len(number) > 32:
        one("certNoPlain", "证件号不能超过 32 字")
    return number


def _person(ident: int) -> Realname:
    row = Repository(Realname).get(ident)
    if row.status != "ENABLED":
        raise BizError(1501, "关联的实名人已停用，不可选择")
    return row


def _active_same(realname_id: int, cert_type: str, except_id: int | None = None) -> Cert | None:
    stmt = select(Cert).where(Cert.realname_id == realname_id, Cert.cert_type == cert_type, Cert.status.in_(("EFFECTIVE", "EXPIRING")))
    found = get_session().scalar(stmt)
    if found is not None and found.id != except_id:
        return found
    return None


def _view(row: Cert, *, detail: bool = False) -> dict:
    person = holder(row.realname_id)
    name = person["holderName"]
    if person.get("deptName"):
        name = f"{name}（{person['deptName']}）"
    data = {
        "id": row.id,
        "certNo": row.cert_no or row.code or "",
        "realnameId": row.realname_id,
        "holderName": name,
        "holderUserId": person.get("holderUserId"),
        "external": person.get("external"),
        "certType": row.cert_type or "",
        "certTypeLabel": _TYPE_LABEL.get(row.cert_type or "", row.cert_type or ""),
        "certNoMasked": masked_no(row),
        "issueDate": row.issue_date.isoformat() if row.issue_date else "",
        "expireDate": row.expire_date.isoformat() if row.expire_date else "",
        "longTerm": bool(row.expire_date == LONG_TERM),
        "fileKey": row.file_key or "",
        "version": row.version,
        "status": row.status,
        "statusLabel": status_label(row.status),
        "renewOfCertId": row.renew_of_cert_id,
        "uploadedBy": row.uploaded_by,
        "reviewedBy": row.reviewed_by,
        "reviewedAt": format_datetime(row.reviewed_at),
        "rejectReason": row.reject_reason or "",
        "ocrStatus": row.ocr_status or "",
        "viewLevel": view_level(row),
        "createTime": format_datetime(row.create_time),
        "updateTime": format_datetime(row.update_time),
    }
    data.update(remain(row.expire_date))
    if detail:
        data["versions"] = _versions(row)
        data["tasks"] = _tasks(row.id)
        data["recentViews"] = _recent_views(row.id) if _can_log() else []
    return data


def _can_log() -> bool:
    from app.domains.resource.common import has_perm

    return has_perm("ims:cert:security:log")


def _versions(row: Cert) -> list[dict]:
    rows = list(
        get_session().scalars(
            select(Cert).where(Cert.realname_id == row.realname_id, Cert.cert_type == row.cert_type).order_by(Cert.id.asc()).execution_options(include_deleted=True)
        )
    )
    return [{"id": item.id, "certNo": item.cert_no or "", "status": item.status, "version": item.version, "deleted": bool(item.deleted)} for item in rows]


def _tasks(cert_id: int) -> list[dict]:
    rows = list(get_session().scalars(select(CertExpireTask).where(CertExpireTask.cert_id == cert_id).order_by(CertExpireTask.id.desc())))
    return [{"id": item.id, "level": item.level, "status": item.status, "trace": item.trace or []} for item in rows]


def _recent_views(cert_id: int) -> list[dict]:
    rows = list(
        get_session().scalars(select(CertViewLog).where(CertViewLog.cert_id == cert_id).order_by(CertViewLog.id.desc()).limit(5))
    )
    return [
        {
            "id": item.id,
            "viewerName": item.viewer_name or "",
            "viewLevel": item.view_level,
            "durationSec": item.duration_sec,
            "time": format_datetime(item.create_time),
        }
        for item in rows
    ]


def _filtered(params: dict):
    where = []
    allowed = scope_realname_ids()
    if allowed is not None:
        where.append(Cert.realname_id.in_(allowed))
    if text_of(params, "realnameId"):
        where.append(Cert.realname_id == ident_of(params.get("realnameId")))
    if text_of(params, "certType"):
        where.append(Cert.cert_type == text_of(params, "certType"))
    if text_of(params, "status"):
        where.append(Cert.status == text_of(params, "status"))
    if text_of(params, "certNo"):
        where.append(Cert.cert_no_hash == digest(normalize_id(text_of(params, "certNo"))))
    start = text_of(params, "expireFrom")
    end = text_of(params, "expireTo")
    if start:
        where.append(Cert.expire_date >= parse_day(start, "expireFrom", "有效期起"))
    if end:
        where.append(Cert.expire_date <= parse_day(end, "expireTo", "有效期止"))
    return where


def page(page_query: Page, params: dict) -> dict:
    rows, total = Repository(Cert).page(page_query, *_filtered(params), order=[Cert.update_time.desc(), Cert.id.desc()])
    return page_result([_view(row) for row in rows], total, page_query)


def detail(ident: int) -> dict:
    return _view(load_cert(ident), detail=True)


def upload(body: dict) -> dict:
    cached = replay(token_of(body))
    if cached:
        return cached
    realname_id = ident_of(body.get("realnameId")) if body.get("realnameId") not in (None, "") else 0
    if not realname_id:
        one("realnameId", "请选择持有人")
    person = _person(realname_id)
    cert_type = text_of(body, "certType")
    if not cert_type:
        one("certType", "请选择证件类型")
    number = _check_no(cert_type, text_of(body, "certNoPlain"))
    issue = parse_day(body.get("issueDate"), "issueDate", "签发日期")
    long_term = bool(body.get("longTerm"))
    expire = LONG_TERM if long_term else parse_day(body.get("expireDate"), "expireDate", "有效期至")
    if expire <= issue:
        one("expireDate", "有效期至须晚于签发日期")
    file_key = text_of(body, "fileKey")
    if not file_key:
        one("fileKey", "请上传扫描件")
    renew_of = body.get("renewOfCertId")
    renew_id = ident_of(renew_of) if renew_of not in (None, "", 0, "0") else None
    if renew_id:
        old = load_cert(renew_id)
        if old.realname_id != person.id or old.cert_type != cert_type:
            one("renewOfCertId", "换证须沿用原持有人与证件类型")
    elif _active_same(person.id, cert_type):
        raise BizError(1032)
    hashed = digest(number)
    number_no = next_no("CERT", "CERT")
    ctx = get_ctx()
    row = Cert(
        code=number_no,
        cert_no=number_no,
        name=person.name,
        cert_type=cert_type,
        cert_no_enc=number,
        cert_no_hash=hashed,
        issue_date=issue,
        expire_date=expire,
        file_key=file_key,
        version=1,
        status="PENDING_REVIEW",
        realname_id=person.id,
        renew_of_cert_id=renew_id,
        uploaded_by=ctx.user_id if ctx else None,
        ocr_status=text_of(body, "ocrStatus") or "",
    )
    Repository(Cert).create(row)
    from app.domains.file.service import bind

    bind(file_key, "ims_master_cert", row.id)
    payload = _view(row)
    remember(token_of(body), payload)
    return payload


def review(ident: int, body: dict) -> dict:
    row = load_cert(ident)
    ctx = get_ctx()
    uid = int(ctx.user_id) if ctx and ctx.user_id else 0
    if row.uploaded_by and int(row.uploaded_by) == uid:
        raise BizError(1008, "不能审核自己提交的单据")
    if row.status != "PENDING_REVIEW":
        raise BizError(1001, "状态已变化，请刷新")
    action = text_of(body, "action")
    if action not in {"APPROVE", "REJECT"}:
        one("action", "请选择通过或驳回")
    now = now_naive()
    if action == "REJECT":
        reason = limit(text_of(body, "reason"), "reason", "驳回原因", 255, required=True)
        row.reject_reason = reason
        row.reviewed_by = uid or None
        row.reviewed_at = now
        row.deleted = row.id
        get_session().flush()
        _notify_reject(row)
        return {"id": row.id, "status": "DELETED", "rejectReason": reason}
    row.status = "EFFECTIVE"
    level = None
    from app.domains.cert.support import warn_level_for

    level = warn_level_for(row.expire_date)
    if level:
        row.status = "EXPIRING" if level != "LOCKED" else "EXPIRED"
    row.reviewed_by = uid or None
    row.reviewed_at = now
    assert_dict_values(row)
    get_session().flush()
    if row.renew_of_cert_id:
        _archive_old(int(row.renew_of_cert_id))
    if level:
        from app.domains.cert.expire import ensure_task

        ensure_task(row, level, notify=True)
    return _view(row)


def _archive_old(cert_id: int) -> None:
    old = load_cert(cert_id)
    old.status = "RECYCLED"
    assert_dict_values(old)
    task = get_session().scalar(select(CertExpireTask).where(CertExpireTask.cert_id == old.id, CertExpireTask.status != "RENEW_RESOLVED"))
    if task is not None:
        task.status = "RENEW_RESOLVED"
        trace = list(task.trace or [])
        trace.append({"time": format_datetime(now_naive()), "title": "已换证", "detail": "新证审核通过，旧证归档"})
        task.trace = trace
        assert_dict_values(task)
    get_session().flush()


def _notify_reject(row: Cert) -> None:
    if not row.uploaded_by:
        return
    from app.domains.cert.notify import deep_link, deliver

    deliver(
        [int(row.uploaded_by)],
        "notify.cert.reject",
        "cert_reject",
        f"cert-reject:{row.id}",
        deep_link(row.id, "archive"),
        {"SITE", "DINGTALK"},
        extra=f"原因：{row.reject_reason or ''}",
    )


def metrics() -> dict:
    session = get_session()
    people = list(session.scalars(select(Realname).where(Realname.status == "ENABLED")))
    total = len(people)
    covered_ids = set()
    groups: dict[str, int] = {}
    certs = list(session.scalars(select(Cert).where(Cert.status.in_(("EFFECTIVE", "EXPIRING")), Cert.file_key.is_not(None), Cert.file_key != "")))
    enabled = {int(item.id) for item in people}
    for item in certs:
        if item.realname_id and int(item.realname_id) in enabled:
            groups[item.cert_type or "OTHER"] = groups.get(item.cert_type or "OTHER", 0) + 1
            if item.cert_type == "ID_CARD":
                covered_ids.add(int(item.realname_id))
    numerator = len(covered_ids)
    rate = (numerator / total) if total else 0
    return {
        "denominator": total,
        "numerator": numerator,
        "rate": f"{rate:.4f}",
        "belowStandard": rate < 0.95,
        "groups": [{"certType": key, "certTypeLabel": _TYPE_LABEL.get(key, key), "count": value} for key, value in sorted(groups.items())],
    }


def export(params: dict) -> dict:
    rows = []
    page_no = 1
    total = 1
    while len(rows) < total:
        chunk = page(Page(page_no, 100), params)
        total = int(chunk["total"])
        rows.extend(chunk["list"])
        if not chunk["list"]:
            break
        page_no += 1
    header = ["档案编号", "持有人", "证件类型", "证件号", "签发日期", "有效期至", "剩余", "状态"]
    body = [
        [item["certNo"], item["holderName"], item["certTypeLabel"], item["certNoMasked"], item["issueDate"], item["expireDate"], item["remainText"], item["statusLabel"]]
        for item in rows
    ]
    return remember_export("证件档案.xlsx", header, body, "cert")


def count_enabled_id_cards() -> int:
    return int(get_session().scalar(select(func.count()).select_from(Cert).where(Cert.cert_type == "ID_CARD")) or 0)
