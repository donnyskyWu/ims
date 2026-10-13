"""办公 / 直播设备台账、采购导入与导出。"""
from __future__ import annotations

import csv
import io

from sqlalchemy import or_, select

from app.core.clock import format_datetime, today
from app.core.errors import BizError
from app.core.pagination import Page, page_result
from app.core.serialize import parse_api_id
from app.db.repository import Repository, assert_dict_values, validate_refs_on_write
from app.db.session import get_session
from app.domains.device.model import AssetBind, AssetEvent, AssetLedger, AssetPurchaseBatch
from app.domains.device.support import (
    ASSET_STATUS,
    ASSET_TYPE,
    amount_fen,
    asset_code,
    deny_asset,
    fen_to_yuan,
    limit,
    masked_money,
    not_future,
    one,
    parse_day,
    remember,
    replay,
    require_active_user,
    require_realname,
    restricted_owner,
    site_message,
    stamp_no,
    token_of,
    user_brief,
    viewer_id,
)
from app.domains.file.model import StoredFile
from app.domains.master.model import PlatformAccount, Realname
from app.domains.resource.common import text_of
from app.domains.system.model import User
from app.services.exchange import remember_export

_OFFICE = ("OFFICE",)
_LIVE = ("LIVE", "SHOOT")
_EDIT_FIELDS = ("assetName", "spec", "purchaseDate", "purchaseAmount", "realnameId", "photoFileKeys", "remark")


def _missing(exc: BizError):
    if exc.code == 1504:
        raise BizError(1011, "资产不存在") from exc
    raise exc


def load(ident: int, *, check_owner: bool = True) -> AssetLedger:
    try:
        row = Repository(AssetLedger).get(int(ident))
    except BizError as exc:
        _missing(exc)
    if check_owner:
        owner = restricted_owner()
        if owner is not None and int(row.owner_user_id or 0) != owner:
            deny_asset()
    return row


def _scope_clause(scope: str):
    if scope == "live":
        return AssetLedger.asset_type.in_(_LIVE)
    return AssetLedger.asset_type.in_(_OFFICE)


def _photos(raw) -> list[str]:
    if raw in (None, ""):
        return []
    if isinstance(raw, str):
        values = [item.strip() for item in raw.split(",") if item.strip()]
    elif isinstance(raw, list):
        values = [str(item).strip() for item in raw if str(item).strip()]
    else:
        one("photoFileKeys", "照片格式不正确")
        return []
    if len(values) > 5:
        one("photoFileKeys", "照片最多 5 张")
    session = get_session()
    for key in values:
        stored = session.scalar(select(StoredFile).where(StoredFile.file_key == key))
        if stored is None or stored.scene != "ASSET":
            raise BizError(5005, "文件保存失败，请稍后重试")
    return values


def _realname_name(ident: int | None) -> str:
    if not ident:
        return ""
    row = get_session().get(Realname, int(ident))
    return row.name if row is not None else ""


def _accounts(asset_id: int) -> list[dict]:
    session = get_session()
    binds = list(
        session.scalars(select(AssetBind).where(AssetBind.asset_id == int(asset_id), AssetBind.bind_status == "ACTIVE", AssetBind.account_id.is_not(None)))
    )
    found = []
    for bind in binds:
        account = session.get(PlatformAccount, bind.account_id)
        if account is None or int(account.deleted or 0) != 0:
            continue
        found.append(
            {
                "id": account.id,
                "accountNo": account.account_no or account.code or "",
                "nickname": account.nickname or account.name,
                "platform": account.platform or "",
                "status": account.status,
            }
        )
    return found


def needs_link(row: AssetLedger) -> bool:
    if row.status == "SCRAPPED":
        return False
    if not row.owner_user_id or not row.realname_id:
        return True
    return False


def _view(row: AssetLedger, *, detail: bool = False) -> dict:
    owner = user_brief(row.owner_user_id)
    data = {
        "id": row.id,
        "assetCode": row.asset_code,
        "assetName": row.asset_name,
        "assetType": row.asset_type,
        "assetTypeLabel": ASSET_TYPE.get(row.asset_type, row.asset_type),
        "spec": row.spec or "",
        "status": row.status,
        "statusLabel": ASSET_STATUS.get(row.status, row.status),
        "ownerUserId": row.owner_user_id,
        "ownerName": owner["name"],
        "ownerResigned": owner["resigned"],
        "realnameId": row.realname_id,
        "realnameName": _realname_name(row.realname_id),
        "accountCount": len(_accounts(row.id)),
        "purchaseDate": row.purchase_date.isoformat() if row.purchase_date else "",
        "purchaseAmount": masked_money(row.purchase_amount),
        "needLink": needs_link(row),
        "version": int(row.version or 1),
        "remark": row.remark or "",
        "purchaseBatchNo": row.purchase_batch_no or "",
        "createTime": format_datetime(row.create_time),
    }
    if detail:
        data["photoFileKeys"] = list(row.photo_file_keys or [])
        accounts = _accounts(row.id)
        data["accounts"] = accounts
        data["accountEmpty"] = "" if accounts else "暂无绑定账号"
        data["holders"] = holders(row.id)
        data["timeline"] = timeline(row.id)
    return data


def _apply_filters(params: dict, scope: str):
    where = [_scope_clause(scope)]
    owner = restricted_owner()
    if owner is not None:
        where.append(AssetLedger.owner_user_id == owner)
    code = text_of(params, "assetCode")
    if code:
        where.append(AssetLedger.asset_code.contains(code))
    name = text_of(params, "assetName")
    if name:
        where.append(AssetLedger.asset_name.contains(name))
    asset_type = text_of(params, "assetType")
    if asset_type:
        if scope == "office" and asset_type != "OFFICE":
            where.append(AssetLedger.id == -1)
        elif scope == "live" and asset_type not in _LIVE:
            where.append(AssetLedger.id == -1)
        else:
            where.append(AssetLedger.asset_type == asset_type)
    if params.get("ownerUserId"):
        where.append(AssetLedger.owner_user_id == parse_api_id(params.get("ownerUserId")))
    status = text_of(params, "status")
    if status:
        where.append(AssetLedger.status == status)
    start = text_of(params, "purchaseDateStart") or text_of(params, "startDate")
    end = text_of(params, "purchaseDateEnd") or text_of(params, "endDate")
    if start:
        where.append(AssetLedger.purchase_date >= date_of(start))
    if end:
        where.append(AssetLedger.purchase_date <= date_of(end))
    return where


def date_of(value: str):
    from datetime import date

    return date.fromisoformat(value[:10])


def page(page_query: Page, params: dict, scope: str) -> dict:
    order = [AssetLedger.create_time.desc(), AssetLedger.id.desc()]
    sort = text_of(params, "sortField")
    direction = text_of(params, "sortOrder")
    column = {"purchaseDate": AssetLedger.purchase_date, "accountCount": AssetLedger.id}.get(sort)
    if column is not None and sort != "accountCount":
        order = [column.asc() if direction == "asc" else column.desc(), AssetLedger.id.desc()]
    rows, total = Repository(AssetLedger).page(page_query, *_apply_filters(params, scope), order=order)
    data = [_view(row) for row in rows]
    if sort == "accountCount":
        data.sort(key=lambda item: int(item["accountCount"]), reverse=direction != "asc")
    return page_result(data, total, page_query)


def detail(ident: int) -> dict:
    return _view(load(ident), detail=True)


def _fill(row: AssetLedger, body: dict, creating: bool, scope: str) -> None:
    if creating or "assetName" in body:
        row.asset_name = limit(text_of(body, "assetName"), "assetName", "资产名称", 64, required=True)
    if creating:
        if scope == "office":
            row.asset_type = "OFFICE"
        else:
            asset_type = text_of(body, "assetType")
            if not asset_type:
                one("assetType", "请选择资产类型")
            if asset_type not in _LIVE:
                raise BizError(1503, "字典值非法", data={"field": "assetType"})
            row.asset_type = asset_type
        number = text_of(body, "assetCode") or asset_code()
        number = limit(number, "assetCode", "资产编号", 32, required=True)
        taken = get_session().scalar(select(AssetLedger).where(AssetLedger.asset_code == number))
        if taken is not None:
            one("assetCode", "资产编号已存在")
        row.asset_code = number
    if creating or "spec" in body:
        row.spec = limit(text_of(body, "spec"), "spec", "规格", 128) or None
    if creating or "purchaseDate" in body:
        found = parse_day(body.get("purchaseDate"), "purchaseDate", required=creating, label="采购日期")
        not_future(found, "purchaseDate")
        row.purchase_date = found
    if creating or "purchaseAmount" in body:
        row.purchase_amount = amount_fen(body.get("purchaseAmount"), "purchaseAmount")
    if creating or "ownerUserId" in body:
        if creating:
            user = require_active_user(body.get("ownerUserId"), "ownerUserId", "责任人")
            row.owner_user_id = user.id
    if creating or "realnameId" in body:
        person = require_realname(body.get("realnameId"))
        row.realname_id = person.id if person is not None else None
    if creating or "photoFileKeys" in body:
        row.photo_file_keys = _photos(body.get("photoFileKeys"))
    if creating or "remark" in body:
        row.remark = limit(text_of(body, "remark"), "remark", "备注", 256) or None


def create(body: dict) -> dict:
    cached = replay(token_of(body))
    if cached:
        return cached
    scope = "live" if text_of(body, "scope") == "live" or text_of(body, "assetType") in _LIVE else "office"
    if text_of(body, "scope") == "office":
        scope = "office"
    row = AssetLedger(status="PENDING_REVIEW", purchase_amount=0, version=1)
    _fill(row, body, creating=True, scope=scope)
    Repository(AssetLedger).create(row)
    add_event(row, "REGISTER", "资产登记", detail="资产登记")
    get_session().flush()
    payload = _view(row)
    remember(token_of(body), payload)
    return payload


def update(ident: int, body: dict) -> dict:
    row = load(ident)
    if row.status == "SCRAPPED":
        raise BizError(1015, "当前状态不允许此操作")
    before = {
        "名称": row.asset_name,
        "规格": row.spec or "",
        "采购日期": row.purchase_date.isoformat() if row.purchase_date else "",
        "采购金额": fen_to_yuan(row.purchase_amount),
        "实名人": _realname_name(row.realname_id),
        "备注": row.remark or "",
    }
    scope = "live" if row.asset_type in _LIVE else "office"
    _fill(row, body, creating=False, scope=scope)
    validate_refs_on_write(row)
    assert_dict_values(row)
    after = {
        "名称": row.asset_name,
        "规格": row.spec or "",
        "采购日期": row.purchase_date.isoformat() if row.purchase_date else "",
        "采购金额": fen_to_yuan(row.purchase_amount),
        "实名人": _realname_name(row.realname_id),
        "备注": row.remark or "",
    }
    changes = [f"{key} 由{before[key] or '空'} 改为{after[key] or '空'}" for key in before if before[key] != after[key]]
    if changes:
        add_event(row, "EDIT", "编辑", detail="；".join(changes))
    get_session().flush()
    return _view(row, detail=True)


def remove(ident: int) -> dict:
    row = load(ident)
    if row.status != "PENDING_REVIEW":
        raise BizError(1015, "当前状态不允许此操作")
    session = get_session()
    used = session.scalar(select(AssetEvent).where(AssetEvent.asset_id == row.id, AssetEvent.event_type == "CHECKOUT"))
    if used is not None:
        raise BizError(1015, "当前状态不允许此操作")
    bound = session.scalar(select(AssetBind).where(AssetBind.asset_id == row.id))
    if bound is not None:
        raise BizError(1502, "该资产已被绑定引用，不能删除")
    Repository(AssetLedger).soft_delete(row.id)
    return {}


def add_event(row: AssetLedger, event_type: str, title: str, *, reason: str = "", detail: str = "", from_owner=None, to_owner=None, from_status: str | None = None, to_status: str | None = None, event_time=None) -> None:
    from app.core.clock import now_naive

    get_session().add(
        AssetEvent(
            asset_id=row.id,
            event_type=event_type,
            title=title[:128],
            from_owner_id=from_owner,
            to_owner_id=to_owner,
            from_status=from_status,
            to_status=to_status if to_status is not None else row.status,
            reason=reason or None,
            detail=detail or None,
            operator_id=viewer_id() or None,
            event_time=event_time or now_naive(),
        )
    )


def timeline(ident: int) -> list[dict]:
    rows = list(
        get_session().scalars(select(AssetEvent).where(AssetEvent.asset_id == int(ident)).order_by(AssetEvent.event_time.desc(), AssetEvent.id.desc()))
    )
    items = []
    for row in rows:
        operator = user_brief(row.operator_id)["name"]
        previous = user_brief(row.from_owner_id)["name"]
        current = user_brief(row.to_owner_id)["name"]
        items.append(
            {
                "id": row.id,
                "time": row.event_time.isoformat(sep=" ") if row.event_time else "",
                "title": row.title,
                "eventType": row.event_type,
                "operator": operator,
                "fromOwner": previous,
                "toOwner": current,
                "reason": row.reason or "",
                "detail": row.detail or "",
            }
        )
    return items


def holders(ident: int) -> list[dict]:
    rows = list(get_session().scalars(select(AssetEvent).where(AssetEvent.asset_id == int(ident)).order_by(AssetEvent.id.asc())))
    found: list[dict] = []
    for row in rows:
        if row.event_type == "CHECKOUT" and row.to_owner_id:
            if found and found[-1]["state"] == "IN_USE":
                found[-1]["state"] = "RETURNED"
                found[-1]["stateLabel"] = "已归还"
            person = user_brief(row.to_owner_id)
            found.append(
                {
                    "userId": row.to_owner_id,
                    "userName": person["name"],
                    "state": "IN_USE",
                    "stateLabel": "领用中",
                    "time": row.event_time.isoformat(sep=" ") if row.event_time else "",
                }
            )
        elif row.event_type in {"RETURN", "TRANSFER"} and found and found[-1]["state"] == "IN_USE":
            found[-1]["state"] = "RETURNED"
            found[-1]["stateLabel"] = "已归还"
        elif row.event_type == "SCRAP" and found and found[-1]["state"] == "IN_USE":
            found[-1]["state"] = "SCRAPPED"
            found[-1]["stateLabel"] = "已报废时持有"
    return found


def export(params: dict) -> dict:
    scope = "live" if text_of(params, "scope") == "live" else "office"
    rows = []
    page_no = 1
    total = 1
    while len(rows) < total:
        chunk = page(Page(page_no, 100), params, scope)
        total = chunk["total"]
        rows.extend(chunk["list"])
        if not chunk["list"]:
            break
        page_no += 1
    header = ["资产编号", "名称", "类型", "规格", "状态", "责任人", "实名人", "绑定账号数", "采购日期", "采购金额"]
    body = [
        [
            item["assetCode"],
            item["assetName"],
            item["assetTypeLabel"],
            item["spec"],
            item["statusLabel"],
            item["ownerName"],
            item["realnameName"],
            item["accountCount"],
            item["purchaseDate"],
            item["purchaseAmount"],
        ]
        for item in rows
    ]
    payload = remember_export("设备台账.xlsx", header, body, "asset_ledger")
    site_message(viewer_id(), "台账导出完成", "设备台账已生成，请到消息中心领取", "/ims/workbench/messages", "ASSET_EXPORT", f"asset-export:{payload['id']}")
    return payload


def selector(page_query: Page, params: dict) -> dict:
    keyword = text_of(params, "keyword")
    ids = text_of(params, "ids")
    if ids:
        wanted = [int(parse_api_id(item)) for item in ids.split(",") if item.strip()]
        rows = list(get_session().scalars(select(AssetLedger).where(AssetLedger.id.in_(wanted)))) if wanted else []
        return page_result([_selector(row) for row in rows], len(rows), page_query)
    stmt = select(AssetLedger).order_by(AssetLedger.id.desc())
    types = text_of(params, "assetTypes")
    if types:
        stmt = stmt.where(AssetLedger.asset_type.in_([item.strip() for item in types.split(",") if item.strip()]))
    status = text_of(params, "status")
    if status:
        stmt = stmt.where(AssetLedger.status == status)
    if params.get("ownerUserId"):
        stmt = stmt.where(AssetLedger.owner_user_id == parse_api_id(params.get("ownerUserId")))
    rows = list(get_session().scalars(stmt))
    if keyword:
        rows = [row for row in rows if keyword in (row.asset_code or "") or keyword in (row.asset_name or "")]
    if not rows and not keyword:
        raise BizError(1221)
    start = (page_query.page_no - 1) * page_query.page_size
    return page_result([_selector(row) for row in rows[start : start + page_query.page_size]], len(rows), page_query)


def _selector(row: AssetLedger) -> dict:
    owner = user_brief(row.owner_user_id)
    return {
        "id": row.id,
        "assetCode": row.asset_code,
        "assetName": row.asset_name,
        "assetType": row.asset_type,
        "status": row.status,
        "statusLabel": ASSET_STATUS.get(row.status, row.status),
        "ownerName": owner["name"],
        "label": f"{row.asset_code} {row.asset_name}",
    }


_HEADERS = {
    "资产编号": "assetCode",
    "资产名称": "assetName",
    "资产类型": "assetType",
    "规格": "spec",
    "采购日期": "purchaseDate",
    "责任人工号": "empNo",
}
_REQUIRED_HEADERS = ("资产名称", "资产类型", "采购日期")
_TYPE_ALIAS = {"办公设备": "OFFICE", "直播设备": "LIVE", "拍摄设备": "SHOOT", "OFFICE": "OFFICE", "LIVE": "LIVE", "SHOOT": "SHOOT"}


def import_csv(content: bytes, filename: str, scope: str) -> dict:
    text = _decode(content)
    if not text.strip():
        raise BizError(1001, "文件没有内容", data={"fieldErrors": [{"field": "file", "message": "文件没有内容"}]})
    reader = csv.reader(io.StringIO(text))
    try:
        header = next(reader)
    except StopIteration:
        raise BizError(1001, "文件没有内容") from None
    names = [item.strip().lstrip("\ufeff") for item in header]
    missing = [item for item in _REQUIRED_HEADERS if item not in names]
    if missing:
        raise BizError(1001, "缺少必填列", data={"fieldErrors": [{"field": "file", "message": "缺少必填列：" + "、".join(missing)}]})
    data_rows = [row for row in reader if any(cell.strip() for cell in row)]
    if not data_rows:
        raise BizError(1001, "没有数据行", data={"fieldErrors": [{"field": "file", "message": "没有数据行"}]})
    if len(data_rows) > 200:
        raise BizError(1001, "单次最多导入 200 行", data={"fieldErrors": [{"field": "file", "message": "单次最多导入 200 行"}]})
    index = {name: pos for pos, name in enumerate(names)}
    errors = []
    success = 0
    batch_no = stamp_no("PB")
    session = get_session()
    for offset, cells in enumerate(data_rows, start=2):
        record = {key: _cell(cells, index, title) for title, key in _HEADERS.items()}
        try:
            with session.begin_nested():
                _import_row(record, scope, batch_no)
            success += 1
        except BizError as exc:
            message = exc.msg
            field = ""
            if exc.data and exc.data.get("fieldErrors"):
                message = exc.data["fieldErrors"][0]["message"]
                field = exc.data["fieldErrors"][0]["field"]
            elif exc.data and exc.data.get("field"):
                field = str(exc.data["field"])
            errors.append({"row": offset, "field": field, "message": message, "code": exc.code})
    batch = AssetPurchaseBatch(
        batch_no=batch_no,
        file_name=(filename or "")[:128],
        scope=scope,
        total_count=len(data_rows),
        success_count=success,
        fail_count=len(errors),
        error_detail=errors,
    )
    session.add(batch)
    session.flush()
    return {
        "batchNo": batch_no,
        "successCount": success,
        "failCount": len(errors),
        "message": f"成功 {success} 条，失败 {len(errors)} 条",
        "errors": errors,
    }


def _cell(cells: list[str], index: dict, title: str) -> str:
    pos = index.get(title)
    if pos is None or pos >= len(cells):
        return ""
    return cells[pos].strip()


def _decode(content: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise BizError(1001, "文件编码无法识别，请使用 UTF-8 或 GBK")


def _import_row(record: dict, scope: str, batch_no: str) -> None:
    name = record["assetName"]
    if not name:
        one("assetName", "资产名称为空")
    if len(name) > 64:
        one("assetName", "资产名称不能超过 64 字")
    raw_type = record["assetType"]
    if not raw_type:
        if scope == "live":
            raise BizError(1503, "资产类型必填", data={"field": "assetType"})
        asset_type = "OFFICE"
    else:
        asset_type = _TYPE_ALIAS.get(raw_type, "")
        if not asset_type:
            raise BizError(1503, "字典值非法", data={"field": "assetType"})
        if scope == "office" and asset_type != "OFFICE":
            raise BizError(1503, "办公页只能导入办公设备", data={"field": "assetType"})
        if scope == "live" and asset_type not in _LIVE:
            raise BizError(1503, "资产类型必填", data={"field": "assetType"})
    spec = record["spec"]
    if len(spec) > 128:
        one("spec", "规格不能超过 128 字")
    raw_date = record["purchaseDate"]
    if not raw_date:
        one("purchaseDate", "采购日期格式错误")
    found = parse_day(raw_date, "purchaseDate", required=True, label="采购日期")
    if found > today():
        one("purchaseDate", "采购日期不能晚于今天")
    number = record["assetCode"] or asset_code()
    if len(number) > 32:
        one("assetCode", "资产编号不能超过 32 字")
    taken = get_session().scalar(select(AssetLedger).where(AssetLedger.asset_code == number))
    if taken is not None:
        raise BizError(1012, "资产编号已存在", data={"field": "assetCode"})
    owner_id = None
    emp = record["empNo"]
    if emp:
        user = get_session().scalar(select(User).where(or_(User.emp_no == emp, User.username == emp)))
        if user is None or int(user.deleted or 0) != 0:
            raise BizError(1500, "关联的责任人不存在", data={"field": "empNo"})
        if user.status != "ACTIVE":
            raise BizError(1501, "关联的责任人已停用，不可选择", data={"field": "empNo"})
        owner_id = user.id
    row = AssetLedger(
        asset_code=number,
        asset_name=name,
        asset_type=asset_type,
        spec=spec or None,
        status="PENDING_REVIEW",
        owner_user_id=owner_id,
        purchase_date=found,
        purchase_amount=0,
        purchase_batch_no=batch_no,
        version=1,
    )
    Repository(AssetLedger).create(row)
    add_event(row, "IMPORT", "采购入台账", detail=batch_no)
