"""反向穿透。按账号、按场次的入口本批不开放，接口先交付。"""
from __future__ import annotations

from sqlalchemy import or_, select

from app.core.errors import BizError
from app.core.serialize import parse_api_id
from app.db.session import get_session
from app.domains.device.model import AssetBind, AssetEvent, AssetLedger, AssetVerifyBatch, AssetVerifyTask
from app.domains.device.support import ASSET_STATUS, ASSET_TYPE, deny_asset, masked_money, restricted_owner
from app.domains.master.model import LiveSession, Phone, PlatformAccount, Realname, SimCard
from app.domains.resource.common import text_of
from app.domains.system.model import User
from app.services.exchange import remember_export


def by_person(user_id: int, params: dict) -> dict:
    realname_raw = text_of(params, "realnameId")
    if int(user_id or 0) == 0 and realname_raw:
        return _by_realname(int(parse_api_id(realname_raw)), params)
    owner = restricted_owner()
    if owner is not None and int(user_id) != owner:
        deny_asset()
    user = get_session().get(User, int(user_id))
    if user is None or int(user.deleted or 0) != 0:
        raise BizError(1500, "关联的用户不存在")
    include = str(params.get("includeHistory", "true")).lower() not in {"0", "false", "no"}
    rows = _person_assets(int(user_id), include)
    return _pack("person", user, rows, params)


def _by_realname(ident: int, params: dict) -> dict:
    person = get_session().get(Realname, ident)
    if person is None or int(person.deleted or 0) != 0:
        raise BizError(1500, "关联的实名人不存在")
    session = get_session()
    assets = list(session.scalars(select(AssetLedger).where(AssetLedger.realname_id == ident)))
    phones = list(
        session.scalars(
            select(Phone)
            .join(SimCard, SimCard.phone_id == Phone.id)
            .where(SimCard.realname_id == ident, SimCard.deleted == 0)
        )
    )
    items = [_asset_hit(row, "实名人关联") for row in assets]
    for phone in phones:
        items.append(
            {
                "kind": "phone",
                "assetId": phone.id,
                "assetCode": phone.device_no or "",
                "assetName": phone.model or "",
                "assetTypeLabel": "手机设备",
                "bindType": "绑定手机卡",
                "status": phone.status,
                "statusLabel": phone.status,
                "bindTime": "",
                "consistency": "未校验",
                "frozen": False,
                "context": "经手机卡关联",
            }
        )
    summary = _summary(items)
    return {"dimension": "realname", "title": person.name, "banner": "", "summary": summary, "list": items}


def _person_assets(user_id: int, include: bool) -> list[AssetLedger]:
    session = get_session()
    current = list(session.scalars(select(AssetLedger).where(AssetLedger.owner_user_id == user_id)))
    if not include:
        return current
    event_ids = list(
        session.scalars(
            select(AssetEvent.asset_id).where(or_(AssetEvent.to_owner_id == user_id, AssetEvent.from_owner_id == user_id), AssetEvent.event_type.in_(("CHECKOUT", "TRANSFER")))
        )
    )
    if not event_ids:
        return current
    extra = list(session.scalars(select(AssetLedger).where(AssetLedger.id.in_(set(event_ids)))))
    merged = {row.id: row for row in current}
    for row in extra:
        merged[row.id] = row
    return list(merged.values())


def _pack(dimension: str, user: User, rows: list[AssetLedger], params: dict) -> dict:
    items = [_asset_hit(row, "持有") for row in rows]
    frozen_rows = user.status == "RESIGNED" and any(row.status == "IN_USE" for row in rows)
    if frozen_rows:
        for item, row in zip(items, rows):
            if row.status == "IN_USE":
                item["frozen"] = True
    summary = _summary(items)
    banner = "该人员离职归还未闭环，资产展示冻结态" if frozen_rows else ""
    return {"dimension": dimension, "title": user.nickname or user.username, "userStatus": user.status, "banner": banner, "summary": summary, "list": items}


def _asset_hit(row: AssetLedger, bind_type: str) -> dict:
    return {
        "kind": "asset",
        "assetId": row.id,
        "assetCode": row.asset_code,
        "assetName": row.asset_name,
        "assetType": row.asset_type,
        "assetTypeLabel": ASSET_TYPE.get(row.asset_type, row.asset_type),
        "bindType": bind_type,
        "status": row.status,
        "statusLabel": ASSET_STATUS.get(row.status, row.status),
        "bindTime": row.create_time.isoformat(sep=" ") if row.create_time else "",
        "consistency": _consistency(row.id),
        "frozen": False,
        "context": f"{row.asset_code} {ASSET_STATUS.get(row.status, row.status)}",
        "purchaseAmount": masked_money(row.purchase_amount),
    }


def _summary(items: list[dict]) -> dict:
    in_use = sum(1 for item in items if item.get("status") == "IN_USE")
    returned = sum(1 for item in items if item.get("status") == "RETURNED")
    scrapped = sum(1 for item in items if item.get("status") == "SCRAPPED")
    total = len(items)
    return {
        "total": total,
        "inUse": in_use,
        "returned": returned,
        "scrapped": scrapped,
        "text": f"命中 {total} 条（使用中 {in_use} / 已归还 {returned} / 已报废 {scrapped}）",
    }


def _consistency(asset_id: int) -> str:
    session = get_session()
    batch = session.scalar(select(AssetVerifyBatch).where(AssetVerifyBatch.scope == "FULL", AssetVerifyBatch.status == "DONE").order_by(AssetVerifyBatch.id.desc()))
    if batch is None:
        return "未校验"
    open_task = session.scalar(
        select(AssetVerifyTask).where(
            AssetVerifyTask.asset_id == asset_id,
            AssetVerifyTask.task_status != "CLOSED",
        )
    )
    if open_task is not None:
        return "不一致"
    return "一致"


def by_account(account_id: int) -> dict:
    account = get_session().get(PlatformAccount, int(account_id))
    if account is None or int(account.deleted or 0) != 0:
        raise BizError(1500, "关联的账号不存在")
    rows = list(get_session().scalars(select(AssetBind).where(AssetBind.account_id == int(account_id), AssetBind.bind_status == "ACTIVE")))
    assets = []
    for bind in rows:
        asset = get_session().get(AssetLedger, bind.asset_id)
        if asset is not None and int(asset.deleted or 0) == 0:
            assets.append(asset)
    items = [_asset_hit(row, "持有") for row in assets]
    return {"dimension": "account", "title": account.name, "banner": "", "summary": _summary(items), "list": items}


def by_session(session_id: int) -> dict:
    found = get_session().get(LiveSession, int(session_id))
    if found is None or int(found.deleted or 0) != 0:
        raise BizError(1500, "关联的场次不存在")
    rows = list(get_session().scalars(select(AssetBind).where(AssetBind.session_id == int(session_id), AssetBind.bind_status == "ACTIVE")))
    assets = []
    for bind in rows:
        asset = get_session().get(AssetLedger, bind.asset_id)
        if asset is not None and int(asset.deleted or 0) == 0:
            assets.append(asset)
    items = [_asset_hit(row, "持有") for row in assets]
    return {"dimension": "session", "title": found.session_code or found.name, "banner": "", "summary": _summary(items), "list": items}


def export(params: dict) -> dict:
    user_raw = text_of(params, "userId")
    realname_raw = text_of(params, "realnameId")
    if realname_raw:
        data = _by_realname(int(parse_api_id(realname_raw)), params)
    elif user_raw:
        data = by_person(int(parse_api_id(user_raw)), params)
    else:
        raise BizError(1001, data={"fieldErrors": [{"field": "userId", "message": "请选择人员"}]})
    header = ["资产编号", "名称", "类型", "绑定方式", "状态", "绑定时间", "一致性"]
    body = [[item["assetCode"], item["assetName"], item["assetTypeLabel"], item["bindType"], item["statusLabel"], item["bindTime"], item["consistency"]] for item in data["list"]]
    return remember_export("反查资产.xlsx", header, body, "asset_reverse")
