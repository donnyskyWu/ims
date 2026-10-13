"""平台账号台账。"""
from __future__ import annotations

from sqlalchemy import or_, select

from app.core.errors import BizError
from app.core.pagination import page_result
from app.db.repository import Repository
from app.db.session import get_session
from app.domains.account.support import (
    ACCOUNT_STATUS,
    PLATFORM_LABEL,
    account_no_for,
    account_row,
    canon_platform,
    company_of,
    dept_name,
    limit,
    log_event,
    mask_amount,
    mismatch,
    money_text,
    names,
    owner_limit,
    page_slice,
    phone_of,
    realname_of,
    remember,
    replay,
    require_dict,
    require_platform,
    save,
    sim_of,
    text_of,
    token_of,
    user_brief,
    visible,
    when,
)
from app.domains.device.model import AssetBind, AssetLedger
from app.domains.master.model import Company, PlatformAccount
from app.domains.resource.company import wechat_official_used
from app.services.exchange import remember_export

_BIND = {"HOLD": "持有"}


def page(page_query, params: dict) -> dict:
    platform = require_platform(text_of(params, "platform"))
    rows = _filtered(platform, params)
    chunk, total = page_slice(rows, page_query)
    return page_result([_view(row) for row in chunk], total, page_query)


def detail(ident: int) -> dict:
    row = account_row(ident)
    visible(row)
    data = _view(row, detail=True)
    return data


def create(body: dict) -> dict:
    cached = replay(token_of(body))
    if cached:
        return cached
    platform = require_platform(text_of(body, "platform"))
    nickname = limit(text_of(body, "nickname"), "nickname", "昵称", 64, required=True)
    company = company_of(body.get("companyId"), required=True)
    person = realname_of(body.get("realnameId"), required=True)
    card = sim_of(body.get("simCardId"))
    phone = phone_of(body.get("phoneId"))
    if platform == "WECHAT_MP":
        used = wechat_official_used(company.id)
        total = int(company.wx_official_capacity or 0)
        if used >= total:
            raise BizError(1222, f"公众号容量不足（已用 {used} / 总量 {total}）", used=used, total=total)
    number = account_no_for(platform, text_of(body, "accountNo"))
    _unique(number, None)
    remark = limit(text_of(body, "remark"), "remark", "备注", 256)
    row = PlatformAccount(
        code=number,
        name=nickname,
        account_no=number,
        nickname=nickname,
        platform=platform,
        company_id=company.id,
        realname_id=person.id,
        sim_card_id=card.id if card else None,
        phone_id=phone.id if phone else None,
        ip_group_id=None,
        status="IN_POOL",
        collect_bind_status="UNBOUND",
        remark=remark,
        recharge_total_fen=0,
        owner_user_id=None,
    )
    _check_status(row.status)
    _check_collect(row.collect_bind_status)
    save(row)
    log_event(row.id, "REGISTER", "登记", nickname)
    payload = _view(row, detail=True)
    payload["warnings"] = mismatch(row)
    remember(token_of(body), payload)
    return payload


def update(ident: int, body: dict) -> dict:
    row = account_row(ident)
    visible(row)
    if row.status == "CANCELLED":
        raise BizError(1001, "状态已变化，请刷新")
    if "platform" in body and canon_platform(text_of(body, "platform")) not in {"", row.platform}:
        one_platform()
    if "accountNo" in body and text_of(body, "accountNo") not in {"", row.account_no or ""}:
        raise BizError(1001, data={"fieldErrors": [{"field": "accountNo", "message": "账号编号不可修改"}]})
    if "nickname" in body:
        row.nickname = limit(text_of(body, "nickname"), "nickname", "昵称", 64, required=True)
        row.name = row.nickname
    if "companyId" in body:
        row.company_id = company_of(body.get("companyId"), required=True).id
    if "realnameId" in body:
        row.realname_id = realname_of(body.get("realnameId"), required=True).id
    if "simCardId" in body:
        card = sim_of(body.get("simCardId"))
        row.sim_card_id = card.id if card else None
    if "phoneId" in body:
        phone = phone_of(body.get("phoneId"))
        row.phone_id = phone.id if phone else None
    if "remark" in body:
        row.remark = limit(text_of(body, "remark"), "remark", "备注", 256)
    save(row)
    payload = _view(row, detail=True)
    payload["warnings"] = mismatch(row)
    return payload


def cancel(ident: int, body: dict) -> dict:
    row = account_row(ident)
    visible(row)
    if row.status == "IN_USE":
        raise BizError(1001, "请先收回或办结归还")
    if row.status == "CANCELLED":
        raise BizError(1001, "状态已变化，请刷新")
    limit(text_of(body, "reason"), "reason", "注销原因", 256, required=True)
    _active_bind(row.id)
    row.status = "CANCELLED"
    _check_status(row.status)
    save(row)
    log_event(row.id, "CANCEL", "注销", text_of(body, "reason"))
    return _view(row, detail=True)


def remove(ident: int) -> dict:
    row = account_row(ident)
    visible(row)
    if row.status != "IN_POOL":
        raise BizError(1502, "该平台账号已被后续记录引用，不能删除")
    if _history(row.id) or _active_bind(row.id, strict=False):
        raise BizError(1502, "该平台账号已被领用、流转、充值或资产绑定引用，不能删除")
    Repository(PlatformAccount).soft_delete(row.id)
    return {}


def export(params: dict) -> dict:
    platform = require_platform(text_of(params, "platform"))
    rows = [_view(row) for row in _filtered(platform, params)]
    header = ["账号编号", "昵称", "平台", "公司", "实名人", "责任人", "状态", "采集绑定", "累计充值"]
    body = [
        [
            item["accountNo"],
            item["nickname"],
            item["platformLabel"],
            item["companyName"],
            item["realnameName"],
            item["ownerName"],
            item["statusLabel"],
            item["collectLabel"],
            "****" if mask_amount() else item["rechargeTotal"],
        ]
        for item in rows
    ]
    return remember_export(f"{PLATFORM_LABEL.get(platform, platform)}账号.xlsx", header, body, "account_platform")


def bind_assets(ident: int, body: dict) -> dict:
    row = account_row(ident)
    visible(row)
    if row.status == "CANCELLED":
        raise BizError(1001, "状态已变化，请刷新")
    raw = body.get("assetIds")
    if raw is None:
        raw = []
    if not isinstance(raw, list):
        from app.domains.account.support import one

        one("assetIds", "请选择资产")
    from app.core.serialize import parse_api_id

    wanted = []
    for item in raw:
        try:
            wanted.append(int(parse_api_id(item)))
        except BizError:
            from app.domains.account.support import one

            one("assetIds", "请选择资产")
    session = get_session()
    current = {
        int(bind.asset_id): bind
        for bind in session.scalars(select(AssetBind).where(AssetBind.account_id == row.id, AssetBind.bind_status == "ACTIVE"))
    }
    for asset_id in wanted:
        asset = session.get(AssetLedger, asset_id)
        if asset is None or int(asset.deleted or 0) != 0:
            raise BizError(1500, "关联的资产不存在")
        if asset.status == "SCRAPPED":
            raise BizError(1015, "当前状态不允许此操作")
        if asset_id in current:
            continue
        bind = AssetBind(asset_id=asset_id, account_id=row.id, bind_type="HOLD", bind_status="ACTIVE")
        save(bind)
    for asset_id, bind in current.items():
        if asset_id not in wanted:
            bind.bind_status = "RELEASED"
    session.flush()
    return {"assets": assets(ident)}


def assets(ident: int) -> list[dict]:
    row = account_row(ident)
    visible(row)
    session = get_session()
    binds = list(session.scalars(select(AssetBind).where(AssetBind.account_id == row.id).order_by(AssetBind.id.desc())))
    found = []
    for bind in binds:
        asset = session.get(AssetLedger, bind.asset_id)
        if asset is None or int(asset.deleted or 0) != 0:
            continue
        found.append(
            {
                "id": bind.id,
                "assetId": asset.id,
                "assetCode": asset.asset_code,
                "assetName": asset.asset_name,
                "bindType": bind.bind_type,
                "bindTypeLabel": _BIND.get(bind.bind_type, bind.bind_type),
                "bindStatus": bind.bind_status,
                "status": asset.status,
            }
        )
    return found


def selector(page_query, params: dict) -> dict:
    from app.core.serialize import parse_api_id

    session = get_session()
    raw_ids = text_of(params, "ids")
    if raw_ids:
        ids = []
        for item in raw_ids.split(","):
            if item.strip():
                ids.append(int(parse_api_id(item.strip())))
        rows = list(session.scalars(select(PlatformAccount).where(PlatformAccount.id.in_(ids)))) if ids else []
        return page_result([_option(row) for row in rows], len(rows), page_query)
    stmt = select(PlatformAccount).where(PlatformAccount.status != "CANCELLED").order_by(PlatformAccount.id.desc())
    platform = text_of(params, "platform")
    if platform:
        stmt = stmt.where(PlatformAccount.platform == require_platform(platform))
    status = text_of(params, "status")
    if status:
        _check_status(status)
        stmt = stmt.where(PlatformAccount.status == status)
    ip_group = text_of(params, "ipGroupId")
    if ip_group:
        stmt = stmt.where(PlatformAccount.ip_group_id == int(parse_api_id(ip_group)))
    rows = list(session.scalars(stmt))
    keyword = text_of(params, "keyword")
    if keyword:
        rows = [row for row in rows if keyword in (row.account_no or "") or keyword in (row.nickname or "") or keyword in (row.name or "")]
    if not rows and not keyword:
        raise BizError(1221, "选择器暂无可选数据")
    chunk, total = page_slice(rows, page_query)
    return page_result([_option(row) for row in chunk], total, page_query)


def summary_by_company(company_id: int) -> list[dict]:
    rows = list(get_session().scalars(select(PlatformAccount).where(PlatformAccount.company_id == int(company_id), PlatformAccount.status != "CANCELLED")))
    counts: dict[str, int] = {}
    for row in rows:
        key = row.platform or ""
        counts[key] = counts.get(key, 0) + 1
    return [{"platform": key, "platformLabel": PLATFORM_LABEL.get(key, key), "count": count} for key, count in counts.items()]


def summary_by_realname(realname_id: int) -> list[dict]:
    rows = list(
        get_session().scalars(select(PlatformAccount).where(PlatformAccount.realname_id == int(realname_id), PlatformAccount.status != "CANCELLED"))
    )
    return [_option(row) for row in rows]


def linked_by_sim(sim_id: int) -> list[dict]:
    rows = list(get_session().scalars(select(PlatformAccount).where(PlatformAccount.sim_card_id == int(sim_id), PlatformAccount.status != "CANCELLED")))
    return [_option(row) for row in rows]


def linked_by_phone(phone_id: int) -> list[dict]:
    rows = list(get_session().scalars(select(PlatformAccount).where(PlatformAccount.phone_id == int(phone_id), PlatformAccount.status != "CANCELLED")))
    return [_option(row) for row in rows]


def _filtered(platform: str, params: dict) -> list[PlatformAccount]:
    stmt = select(PlatformAccount).where(PlatformAccount.platform == platform).order_by(PlatformAccount.update_time.desc(), PlatformAccount.id.desc())
    owner = owner_limit()
    if owner is not None:
        stmt = stmt.where(PlatformAccount.owner_user_id == owner)
    status = text_of(params, "status")
    if status:
        _check_status(status)
        stmt = stmt.where(PlatformAccount.status == status)
    collect = text_of(params, "collectBindStatus") or text_of(params, "collectStatus")
    if collect:
        _check_collect(collect)
        stmt = stmt.where(PlatformAccount.collect_bind_status == collect)
    keyword = text_of(params, "keyword") or text_of(params, "accountNo")
    if keyword:
        stmt = stmt.where(or_(PlatformAccount.account_no.contains(keyword), PlatformAccount.nickname.contains(keyword), PlatformAccount.name.contains(keyword)))
    company = text_of(params, "companyId")
    if company:
        from app.core.serialize import parse_api_id

        stmt = stmt.where(PlatformAccount.company_id == int(parse_api_id(company)))
    person = text_of(params, "realnameId")
    if person:
        from app.core.serialize import parse_api_id

        stmt = stmt.where(PlatformAccount.realname_id == int(parse_api_id(person)))
    owner_id = text_of(params, "ownerUserId")
    if owner_id:
        from app.core.serialize import parse_api_id

        stmt = stmt.where(PlatformAccount.owner_user_id == int(parse_api_id(owner_id)))
    return list(get_session().scalars(stmt))


def _view(row: PlatformAccount, *, detail: bool = False) -> dict:
    label = names(row.company_id, row.realname_id, row.sim_card_id, row.phone_id)
    owner = user_brief(row.owner_user_id)
    data = {
        "id": row.id,
        "accountNo": row.account_no or row.code or "",
        "nickname": row.nickname or row.name,
        "platform": row.platform or "",
        "platformLabel": PLATFORM_LABEL.get(row.platform or "", row.platform or ""),
        "companyId": row.company_id,
        "companyName": label["companyName"],
        "realnameId": row.realname_id,
        "realnameName": label["realnameName"],
        "simCardId": row.sim_card_id,
        "simMasked": label["simMasked"],
        "phoneId": row.phone_id,
        "phoneNo": label["phoneNo"],
        "ownerUserId": row.owner_user_id,
        "ownerName": owner["name"] or "—",
        "ownerResigned": owner["resigned"],
        "ownerDept": dept_name(row.owner_user_id),
        "status": row.status,
        "statusLabel": ACCOUNT_STATUS.get(row.status, row.status),
        "frozen": row.status == "FROZEN",
        "collectBindStatus": row.collect_bind_status or "UNBOUND",
        "collectLabel": {"UNBOUND": "未绑定", "BOUND": "已绑定", "FAIL": "连接失败"}.get(row.collect_bind_status or "UNBOUND", "未绑定"),
        "rechargeTotal": money_text(row.recharge_total_fen),
        "rechargeTotalFen": 0 if mask_amount() else int(row.recharge_total_fen or 0),
        "remark": row.remark or "",
        "ipGroupText": "—，IP 组模块上线后可绑定",
        "updateTime": when(row.update_time),
        "idle": _idle(row),
    }
    if detail:
        data["warnings"] = mismatch(row)
        data["canApply"] = row.status == "IN_POOL"
        data["canTransfer"] = row.status == "IN_USE"
        data["canRecall"] = row.status == "IN_USE"
        data["canUnfreeze"] = row.status == "FROZEN"
        data["canCancel"] = row.status not in {"IN_USE", "CANCELLED"}
    return data


def _option(row: PlatformAccount) -> dict:
    owner = user_brief(row.owner_user_id)
    return {
        "id": row.id,
        "accountNo": row.account_no or row.code or "",
        "nickname": row.nickname or row.name,
        "platform": row.platform or "",
        "platformLabel": PLATFORM_LABEL.get(row.platform or "", ""),
        "status": row.status,
        "statusLabel": ACCOUNT_STATUS.get(row.status, row.status),
        "ownerName": owner["name"],
        "label": f"{row.account_no or row.code or ''} {row.nickname or row.name}",
    }


def _unique(number: str, current: int | None) -> None:
    found = get_session().scalar(select(PlatformAccount).where(PlatformAccount.account_no == number))
    if found is not None and found.id != current:
        from app.domains.account.support import one

        one("accountNo", "账号编号已存在")


def _check_status(value: str) -> None:
    require_dict("dict_account_status", value, "status", "状态")


def _check_collect(value: str) -> None:
    require_dict("dict_collect_bind_status", value, "collectBindStatus", "采集绑定")


def _active_bind(account_id: int, strict: bool = True) -> bool:
    row = get_session().scalar(select(AssetBind.id).where(AssetBind.account_id == int(account_id), AssetBind.bind_status == "ACTIVE"))
    if row and strict:
        raise BizError(1502, "该平台账号已被资产绑定引用，不能删除")
    return row is not None


def _history(account_id: int) -> bool:
    from app.domains.account.model import AccountApply, AccountTransfer, Recharge

    session = get_session()
    if session.scalar(select(AccountApply.id).where(AccountApply.account_id == account_id)):
        return True
    if session.scalar(select(AccountTransfer.id).where(AccountTransfer.account_id == account_id)):
        return True
    if session.scalar(select(Recharge.id).where(Recharge.account_id == account_id)):
        return True
    if session.scalar(select(AssetBind.id).where(AssetBind.account_id == account_id)):
        return True
    return False


def _idle(row: PlatformAccount) -> bool:
    if row.status != "IN_USE":
        return False
    from datetime import timedelta

    from app.core.clock import now_naive
    from app.domains.account.model import AccountApply, AccountTransfer, CollectCredential, Recharge

    session = get_session()
    apply = session.scalar(
        select(AccountApply).where(AccountApply.account_id == row.id, AccountApply.apply_status == "APPROVED").order_by(AccountApply.id.desc())
    )
    if apply is None or apply.update_time is None:
        return False
    if apply.update_time > now_naive() - timedelta(days=15):
        return False
    since = apply.update_time
    if session.scalar(select(AccountTransfer.id).where(AccountTransfer.account_id == row.id, AccountTransfer.create_time > since)):
        return False
    if session.scalar(select(Recharge.id).where(Recharge.account_id == row.id, Recharge.create_time > since)):
        return False
    cred = session.scalar(select(CollectCredential).where(CollectCredential.account_id == row.id, CollectCredential.last_probe_ok == 1))
    if cred is not None and cred.last_probe_at and cred.last_probe_at > since:
        return False
    return True


def one_platform() -> None:
    raise BizError(1001, data={"fieldErrors": [{"field": "platform", "message": "平台不可修改"}]})
