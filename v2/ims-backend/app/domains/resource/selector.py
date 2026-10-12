"""公司、实名人、手机卡选择器。只返回启用数据；按编号回显可带已停用标记。"""
from __future__ import annotations

from sqlalchemy import select

from app.core.errors import BizError
from app.core.pagination import Page, page_result
from app.core.serialize import parse_api_id
from app.db.session import get_session
from app.domains.master.model import Company, Realname, SimCard
from app.domains.resource.common import mask_keep, text_of
from app.domains.resource.realname import cert_expired

_HINT = "选择器暂无可选数据"


def _ids(params: dict) -> list[int]:
    raw = text_of(params, "ids")
    if not raw:
        return []
    found = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        found.append(int(parse_api_id(item)))
    return found


def companies(page: Page, params: dict) -> dict:
    session = get_session()
    wanted = _ids(params)
    keyword = text_of(params, "keyword")
    if wanted:
        rows = list(session.scalars(select(Company).where(Company.id.in_(wanted))))
        data = [_company(row) for row in rows]
        return page_result(data, len(data), page)
    enabled = list(session.scalars(select(Company).where(Company.status == "ENABLED").order_by(Company.id.desc())))
    if keyword:
        enabled = [row for row in enabled if keyword in (row.name or "") or keyword in (row.company_no or "")]
    if not enabled and not keyword:
        raise BizError(1221)
    start = (page.page_no - 1) * page.page_size
    chunk = enabled[start : start + page.page_size]
    return page_result([_company(row) for row in chunk], len(enabled), page)


def _company(row: Company) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "companyNo": row.company_no or row.code or "",
        "status": row.status,
        "disabled": row.status != "ENABLED",
    }


def persons(page: Page, params: dict) -> dict:
    session = get_session()
    wanted = _ids(params)
    keyword = text_of(params, "keyword")
    if wanted:
        rows = list(session.scalars(select(Realname).where(Realname.id.in_(wanted))))
        return page_result([_person(row) for row in rows], len(rows), page)
    enabled = list(session.scalars(select(Realname).where(Realname.status == "ENABLED").order_by(Realname.id.desc())))
    if keyword:
        enabled = [row for row in enabled if keyword in (row.name or "")]
    if not enabled and not keyword:
        raise BizError(1221)
    start = (page.page_no - 1) * page.page_size
    chunk = enabled[start : start + page.page_size]
    return page_result([_person(row) for row in chunk], len(enabled), page)


def _person(row: Realname) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "idNoMasked": mask_keep(row.id_no_enc),
        "certExpired": cert_expired(row.id) if row.status == "ENABLED" else False,
        "status": row.status,
        "disabled": row.status != "ENABLED",
    }


def sim_cards(page: Page, params: dict) -> dict:
    session = get_session()
    wanted = _ids(params)
    keyword = text_of(params, "keyword")
    if wanted:
        rows = list(session.scalars(select(SimCard).where(SimCard.id.in_(wanted))))
        return page_result([_sim(row) for row in rows], len(rows), page)
    enabled = list(session.scalars(select(SimCard).where(SimCard.status == "ENABLED").order_by(SimCard.id.desc())))
    if keyword:
        enabled = [row for row in enabled if (row.phone_number_enc or "").endswith(keyword)]
    if str(params.get("unboundOnly", "")).lower() in {"1", "true", "yes"}:
        enabled = [row for row in enabled if not row.phone_id]
    if not enabled and not keyword:
        raise BizError(1221)
    start = (page.page_no - 1) * page.page_size
    chunk = enabled[start : start + page.page_size]
    return page_result([_sim(row) for row in chunk], len(enabled), page)


def _sim(row: SimCard) -> dict:
    person = get_session().get(Realname, row.realname_id) if row.realname_id else None
    return {
        "id": row.id,
        "phoneMasked": mask_keep(row.phone_number_enc),
        "operator": row.operator or "",
        "realnameName": person.name if person is not None else "",
        "status": row.status,
        "disabled": row.status != "ENABLED",
    }
