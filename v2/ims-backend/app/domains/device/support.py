"""设备域共用：校验、编号、范围、时间线与站内通知。"""
from __future__ import annotations

import json
from datetime import date, timedelta

from sqlalchemy import select

from app.core.clock import now_naive, today
from app.core.context import get_ctx
from app.core.errors import BizError
from app.db.session import get_session
from app.domains.resource.common import fen_to_yuan, has_perm, mask_keep, money_to_fen

ASSET_STATUS = {
    "PENDING_REVIEW": "待审核",
    "IN_USE": "使用中",
    "RETURNED": "已归还",
    "IDLE": "闲置",
    "REPAIRING": "维修中",
    "SCRAPPED": "已报废",
}
ASSET_TYPE = {"OFFICE": "办公设备", "LIVE": "直播设备", "SHOOT": "拍摄设备"}
PHONE_STATUS = {"IDLE": "闲置", "IN_USE": "使用中", "REPAIRING": "维修中", "SCRAPPED": "已报废"}
PHONE_OS = {"ANDROID": "Android", "IOS": "iPhone"}
TRANSFER_REASON = {"WORK_CHANGE": "工作调整", "RESIGN": "人员离职", "ALLOCATE": "设备调配", "OTHER": "其他"}
VERIFY_TYPE = {"asset_person": "资产↔实名人/责任人", "asset_account": "资产↔账号", "asset_session": "资产↔场次"}
TASK_STATUS = {"PENDING_DISPATCH": "待派发", "REPAIRING": "修复中", "PENDING_RECHECK": "待复审", "CLOSED": "已闭环"}
CONDITION = {"GOOD": "完好", "DAMAGED": "有损坏"}
OPEN_TASK = {"PENDING_DISPATCH", "REPAIRING", "PENDING_RECHECK"}


def fail(errors: list[dict]) -> None:
    raise BizError(1001, data={"fieldErrors": errors})


def one(field: str, message: str) -> None:
    fail([{"field": field, "message": message}])


def limit(value: str, field: str, label: str, max_len: int, required: bool = False) -> str:
    if required and not value:
        one(field, f"请填写{label}")
    if len(value) > max_len:
        one(field, f"{label}不能超过 {max_len} 字")
    return value


def amount_fen(value, field: str, required: bool = False) -> int:
    if value in (None, ""):
        if required:
            one(field, "请填写金额")
        return 0
    return money_to_fen(value, field)


def parse_day(value, field: str, required: bool = False, label: str = "日期") -> date | None:
    if value in (None, ""):
        if required:
            one(field, f"请填写{label}")
        return None
    text = str(value).strip()
    try:
        found = date.fromisoformat(text[:10])
    except ValueError:
        one(field, f"{label}格式错误")
        return None
    return found


def not_future(value: date | None, field: str) -> None:
    if value is not None and value > today():
        one(field, "日期不能晚于今天")


def viewer_id() -> int:
    ctx = get_ctx()
    return int(ctx.user_id) if ctx and ctx.user_id else 0


def restricted_owner() -> int | None:
    """非全部数据范围时，只看本人负责的资产。"""
    ctx = get_ctx()
    if ctx is None or ctx.system or ctx.skip_scope:
        return None
    scopes = {item for item in (ctx.data_scopes or set()) if item}
    if not scopes or "ALL" in scopes:
        return None
    return int(ctx.user_id or 0)


def deny_asset() -> None:
    raise BizError(1008, "您无权查看该资产")


def user_of(ident: int | None):
    if not ident:
        return None
    from app.domains.system.model import User

    return get_session().get(User, int(ident))


def user_brief(ident: int | None) -> dict:
    user = user_of(ident)
    if user is None:
        return {"userId": ident, "name": "", "resigned": False}
    return {"userId": user.id, "name": user.nickname or user.username, "resigned": user.status == "RESIGNED"}


def require_active_user(ident, field: str, label: str = "用户"):
    raw = ident
    if raw in (None, "", 0, "0"):
        one(field, f"请选择{label}")
    from app.core.serialize import parse_api_id

    try:
        number = int(parse_api_id(raw))
    except BizError:
        one(field, f"请选择{label}")
        return None
    user = user_of(number)
    if user is None or int(user.deleted or 0) != 0:
        raise BizError(1500, f"关联的{label}不存在", data={"field": field})
    if user.status != "ACTIVE":
        raise BizError(1501, f"关联的{label}已停用，不可选择", data={"field": field})
    return user


def require_realname(ident, required: bool = False):
    if ident in (None, "", 0, "0"):
        if required:
            one("realnameId", "请选择实名人")
        return None
    from app.core.serialize import parse_api_id
    from app.domains.master.model import Realname

    try:
        number = int(parse_api_id(ident))
    except BizError:
        one("realnameId", "请选择实名人")
        return None
    row = get_session().get(Realname, number)
    if row is None or int(row.deleted or 0) != 0:
        raise BizError(1500, "关联的实名人不存在", data={"field": "realnameId"})
    if row.status != "ENABLED":
        raise BizError(1501, "关联的实名人已停用，不可选择", data={"field": "realnameId"})
    return row


def next_code(prefix: str, column, width: int = 3) -> str:
    rows = list(get_session().scalars(select(column).where(column.like(f"{prefix}%"))))
    highest = 0
    for item in rows:
        tail = str(item or "")[len(prefix) :]
        if tail.isdigit():
            highest = max(highest, int(tail))
    return f"{prefix}{highest + 1:0{width}d}"


def phone_no() -> str:
    from app.domains.master.model import Phone

    return next_code(f"PH-{today().year}-", Phone.device_no)


def asset_code() -> str:
    from app.domains.device.model import AssetLedger

    return next_code(f"AS{today().strftime('%Y%m%d')}", AssetLedger.asset_code)


def stamp_no(prefix: str) -> str:
    return prefix + now_naive().strftime("%Y%m%d%H%M%S%f")[:17]


def add_workdays(start: date, days: int) -> date:
    from app.domains.system.model import WorkCalendar
    from app.services.attendance import is_workday

    end = start + timedelta(days=40)
    rows = get_session().scalars(select(WorkCalendar).where(WorkCalendar.cal_date >= start.isoformat(), WorkCalendar.cal_date <= end.isoformat()))
    marked = {row.cal_date: row.day_type for row in rows}
    cursor = start
    left = days
    while left > 0:
        cursor = cursor + timedelta(days=1)
        if is_workday(cursor, marked):
            left -= 1
    return cursor


def phone_log(phone_id: int, event_type: str, title: str, detail: str = "") -> None:
    from app.domains.system.model import Timeline

    get_session().add(
        Timeline(
            biz_type="PHONE",
            biz_id=int(phone_id),
            event_type=event_type,
            title=title[:100],
            detail={"text": detail} if detail else None,
            operator_id=viewer_id() or None,
            event_time=now_naive(),
        )
    )


def phone_logs(phone_id: int) -> list[dict]:
    from app.domains.system.model import Timeline

    rows = list(
        get_session().scalars(
            select(Timeline).where(Timeline.biz_type == "PHONE", Timeline.biz_id == int(phone_id)).order_by(Timeline.event_time.desc(), Timeline.id.desc())
        )
    )
    names = {}
    items = []
    for row in rows:
        if row.operator_id and row.operator_id not in names:
            names[row.operator_id] = user_brief(row.operator_id)["name"]
        text = ""
        if isinstance(row.detail, dict):
            text = str(row.detail.get("text") or "")
        items.append(
            {
                "time": row.event_time.isoformat(sep=" ") if row.event_time else "",
                "title": row.title,
                "operator": names.get(row.operator_id or 0, ""),
                "detail": text,
                "eventType": row.event_type,
            }
        )
    return items


def site_message(receiver_id: int, title: str, content: str, route: str, event_type: str, biz_key: str) -> None:
    from app.domains.message.model import Message, NotifyRecord

    if not receiver_id:
        return
    session = get_session()
    session.add(
        Message(
            receiver_id=int(receiver_id),
            msg_type="SYSTEM",
            title=title,
            content=content,
            route=route or None,
            source_module="asset",
            read_status="UNREAD",
        )
    )
    session.add(
        NotifyRecord(
            event_type=event_type,
            biz_key=biz_key,
            receiver_id=int(receiver_id),
            channel="SITE",
            status="SENT",
            title=title,
            content=content,
        )
    )


def notify_both(receiver_id: int, title: str, content: str, route: str, event_type: str, biz_key: str) -> None:
    from app.domains.message.service import send_notify

    if not receiver_id:
        return
    send_notify(int(receiver_id), title, content, event_type, biz_key, route=route, source_module="asset")


def replay(token: str | None):
    text = (token or "").strip()
    if not text:
        return None
    from app.core.redis_client import get_redis

    cached = get_redis().get(f"ims:idem:b6:{viewer_id()}:{text}")
    if not cached:
        return None
    return json.loads(cached)


def remember(token: str | None, payload: dict) -> None:
    text = (token or "").strip()
    if not text:
        return
    from app.core.redis_client import get_redis

    get_redis().set(f"ims:idem:b6:{viewer_id()}:{text}", json.dumps(payload, ensure_ascii=False, default=str), ex=86400)


def token_of(body: dict) -> str:
    from app.domains.resource.common import token_of as shared

    return shared(body)


def masked_money(cents: int) -> str:
    if has_perm("ims:asset:cost:view"):
        return fen_to_yuan(cents)
    if has_perm("ims:asset:cost:masked"):
        return "¥****"
    return fen_to_yuan(cents)


def show_cost() -> str:
    if has_perm("ims:asset:cost:view"):
        return "plain"
    if has_perm("ims:asset:cost:masked"):
        return "masked"
    return "hidden"


def mask_imei(value: str | None) -> str:
    return mask_keep(value, 3, 2) if value else ""


def reason_label(value: str) -> str:
    text = (value or "").strip()
    if text in TRANSFER_REASON:
        return TRANSFER_REASON[text]
    if text in TRANSFER_REASON.values():
        return text
    return text


def reason_code(value: str) -> str:
    text = (value or "").strip()
    if text in TRANSFER_REASON:
        return text
    for code, label in TRANSFER_REASON.items():
        if text == label:
            return code
    return ""
