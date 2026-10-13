"""公司主数据。"""
from __future__ import annotations

from sqlalchemy import select

from app.core.clock import format_datetime
from app.core.context import get_ctx
from app.core.errors import BizError
from app.core.pagination import Page, page_result
from app.db.repository import Repository, assert_dict_values
from app.db.session import get_session
from app.domains.master.model import Company
from app.domains.resource.common import fail, limit, next_no, normalize_credit, one, parse_int, ref_blocked, remember, replay, text_of, valid_credit
from app.domains.resource.model import CompanyCapacityLog
from app.services.exchange import remember_export

_STATUS = {"ENABLED": "启用", "DISABLED": "停用"}


def wechat_official_used(company_id: int) -> int:
    """公众号已用数。只计未注销的 WECHAT_MP。"""
    from app.domains.master.model import PlatformAccount

    if not hasattr(PlatformAccount, "company_id"):
        return 0
    session = get_session()
    stmt = select(PlatformAccount).where(
        PlatformAccount.company_id == int(company_id),
        PlatformAccount.platform == "WECHAT_MP",
        PlatformAccount.status != "CANCELLED",
    )
    return len(list(session.scalars(stmt)))


def _row(ident: int) -> Company:
    return Repository(Company).get(int(ident))


def _view(row: Company, *, detail: bool = False) -> dict:
    used = wechat_official_used(row.id)
    total = int(row.wx_official_capacity or 0)
    data = {
        "id": row.id,
        "companyNo": row.company_no or row.code or "",
        "name": row.name,
        "creditCode": row.credit_code or "",
        "legalPerson": row.legal_person or "",
        "address": row.address or "",
        "wxOfficialCapacity": total,
        "usedCapacity": used,
        "capacityText": f"{used} / {total}",
        "capacityTight": used >= total and total >= 0,
        "status": row.status,
        "statusLabel": _STATUS.get(row.status, row.status),
        "remark": row.remark or "",
        "updateTime": format_datetime(row.update_time),
    }
    if detail:
        data["capacityLogs"] = _logs(row.id)
        from app.domains.account.platform import summary_by_company

        data["accountSummary"] = summary_by_company(row.id)
    return data


def _logs(company_id: int) -> list[dict]:
    rows = list(
        get_session().scalars(
            select(CompanyCapacityLog).where(CompanyCapacityLog.company_id == company_id).order_by(CompanyCapacityLog.id.desc()).limit(10)
        )
    )
    return [
        {
            "id": item.id,
            "time": format_datetime(item.create_time),
            "title": f"{item.before_value} → {item.after_value}",
            "operator": item.operator_name or "",
            "detail": item.reason or "",
        }
        for item in rows
    ]


def _payload(body: dict, *, creating: bool, current: Company | None = None) -> dict:
    name = limit(text_of(body, "name"), "name", "公司名称", 64, required=creating or "name" in body)
    credit = text_of(body, "creditCode")
    if creating or "creditCode" in body:
        if not credit:
            one("creditCode", "请填写统一社会信用代码")
        credit = normalize_credit(credit)
        if not valid_credit(credit):
            one("creditCode", "统一社会信用代码须为 18 位且校验位正确")
    legal = limit(text_of(body, "legalPerson"), "legalPerson", "法人", 32) if "legalPerson" in body or creating else None
    address = limit(text_of(body, "address"), "address", "地址", 128) if "address" in body or creating else None
    remark = limit(text_of(body, "remark"), "remark", "备注", 255) if "remark" in body or creating else None
    status = text_of(body, "status") or ("ENABLED" if creating else "")
    if status and status not in _STATUS:
        fail([{"field": "status", "message": "状态不正确"}])
    capacity = None
    if creating:
        raw = body.get("wxOfficialCapacity", 0)
        if raw in ("", None):
            raw = 0
        capacity = parse_int(raw, "wxOfficialCapacity", "公众号总容量", 0, 999)
    return {
        "name": name,
        "credit": credit,
        "legal": legal,
        "address": address,
        "remark": remark,
        "status": status,
        "capacity": capacity,
    }


def _ensure_unique(name: str, credit: str, except_id: int | None) -> None:
    session = get_session()
    if name:
        found = session.scalar(select(Company).where(Company.name == name))
        if found is not None and found.id != except_id:
            one("name", "公司名称已存在")
    if credit:
        found = session.scalar(select(Company).where(Company.credit_code == credit))
        if found is not None and found.id != except_id:
            one("creditCode", "统一社会信用代码已存在")


def page(page_query: Page, params: dict) -> dict:
    where = []
    name = text_of(params, "name")
    if name:
        where.append(Company.name.contains(name))
    credit = text_of(params, "creditCode")
    if credit:
        where.append(Company.credit_code == normalize_credit(credit))
    status = text_of(params, "status")
    if status:
        where.append(Company.status == status)
    rows, total = Repository(Company).page(page_query, *where, order=[Company.update_time.desc(), Company.id.desc()])
    return page_result([_view(row) for row in rows], total, page_query)


def detail(ident: int) -> dict:
    return _view(_row(ident), detail=True)


def create(body: dict) -> dict:
    cached = replay(text_of(body, "clientToken") or _header_token())
    if cached:
        return cached
    data = _payload(body, creating=True)
    _ensure_unique(data["name"], data["credit"], None)
    number = next_no("CO", "COMPANY")
    row = Company(
        code=number,
        company_no=number,
        name=data["name"],
        credit_code=data["credit"],
        legal_person=data["legal"] or "",
        address=data["address"] or "",
        wx_official_capacity=data["capacity"] or 0,
        status=data["status"] or "ENABLED",
        remark=data["remark"] or "",
    )
    Repository(Company).create(row)
    payload = _view(row)
    remember(text_of(body, "clientToken") or _header_token(), payload)
    return payload


def update(ident: int, body: dict) -> dict:
    row = _row(ident)
    data = _payload(body, creating=False, current=row)
    name = data["name"] or row.name
    credit = data["credit"] or row.credit_code or ""
    _ensure_unique(name, credit, row.id)
    if data["name"]:
        row.name = data["name"]
    if data["credit"]:
        row.credit_code = data["credit"]
    if data["legal"] is not None:
        row.legal_person = data["legal"]
    if data["address"] is not None:
        row.address = data["address"]
    if data["remark"] is not None:
        row.remark = data["remark"]
    if data["status"]:
        row.status = data["status"]
    assert_dict_values(row)
    get_session().flush()
    return _view(row)


def set_status(ident: int, body: dict) -> dict:
    row = _row(ident)
    status = text_of(body, "status")
    if status not in _STATUS:
        one("status", "状态不正确")
    row.status = status
    assert_dict_values(row)
    get_session().flush()
    return _view(row)


def remove(ident: int) -> dict:
    try:
        Repository(Company).soft_delete(int(ident))
    except BizError as exc:
        if exc.code == 1502:
            ref_blocked("公司", exc)
        raise
    return {}


def adjust_capacity(ident: int, body: dict) -> dict:
    row = _row(ident)
    new_value = parse_int(body.get("capacity"), "capacity", "新容量", 0, 999)
    reason = limit(text_of(body, "reason"), "reason", "原因", 128, required=True)
    used = wechat_official_used(row.id)
    if new_value < used:
        raise BizError(1222, used=used, total=int(row.wx_official_capacity or 0))
    ctx = get_ctx()
    before = int(row.wx_official_capacity or 0)
    row.wx_official_capacity = new_value
    get_session().add(
        CompanyCapacityLog(
            company_id=row.id,
            before_value=before,
            after_value=new_value,
            reason=reason,
            operator_id=ctx.user_id if ctx else None,
            operator_name=(ctx.nickname or ctx.username) if ctx else "",
        )
    )
    get_session().flush()
    return _view(row, detail=True)


def export(params: dict) -> dict:
    data = page(Page(1, 100), params)
    rows = []
    page_no = 1
    while True:
        chunk = page(Page(page_no, 100), params)
        rows.extend(chunk["list"])
        if len(rows) >= chunk["total"]:
            break
        page_no += 1
    header = ["公司编号", "名称", "统一社会信用代码", "法人", "公众号容量", "状态", "更新时间"]
    body = [
        [item["companyNo"], item["name"], item["creditCode"], item["legalPerson"], item["capacityText"], item["statusLabel"], item["updateTime"]]
        for item in rows
    ]
    if not body and data["total"] == 0:
        body = []
    return remember_export("公司.xlsx", header, body, "company")


def _header_token() -> str:
    from app.domains.resource.common import token_of

    return token_of({})
