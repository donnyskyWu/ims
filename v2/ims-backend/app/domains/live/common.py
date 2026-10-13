"""直播域共用：范围、金额、时间与时间线。"""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import or_, select

from app.core.clock import format_datetime, now_naive
from app.core.context import get_ctx
from app.core.errors import BizError
from app.db.repository import assert_dict_values, validate_refs_on_write
from app.db.session import get_session
from app.domains.master.model import IpMember, LiveSession
from app.domains.resource.common import has_perm, one, text_of
from app.domains.system.model import Timeline, User
from app.domains.todo.model import Todo

LIVE_PLATFORMS = ("DOUYIN", "KUAISHOU", "WECHAT_CHANNELS", "XIAOHONGSHU")
PLATFORM_LABEL = {"DOUYIN": "抖音", "KUAISHOU": "快手", "WECHAT_CHANNELS": "视频号", "XIAOHONGSHU": "小红书", "WECHAT_MP": "公众号"}
STATUS_LABEL = {
    "PENDING_RISK_CHECK": "待风控",
    "APPROVED": "已放行",
    "LIVE": "直播中",
    "ENDED": "已下播",
    "CANCELLED": "已取消",
}
ENTRY_LABEL = {"DRAFT": "草稿", "SUBMITTED": "已提交", "CONFIRMED": "已核准"}
SYNC_LABEL = {"UNLINKED": "未关联", "PENDING": "待拉取", "SYNCED": "已同步", "FAILED": "失败"}
OPEN_STATUS = ("PENDING_RISK_CHECK", "APPROVED", "LIVE")


def viewer_id() -> int:
    ctx = get_ctx()
    return int(ctx.user_id) if ctx and ctx.user_id else 0


def save(row) -> None:
    assert_dict_values(row)
    validate_refs_on_write(row)
    session = get_session()
    session.add(row)
    session.flush()


def parse_dt(value, field: str, label: str, required: bool = True) -> datetime | None:
    if value in (None, ""):
        if required:
            one(field, f"请填写{label}")
        return None
    if isinstance(value, datetime):
        return value.replace(microsecond=0)
    text = str(value).strip().replace("T", " ")
    if len(text) == 16:
        text = text + ":00"
    text = text[:19]
    try:
        return datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        one(field, f"{label}格式不正确")
    return None


def money_of(value, field: str, label: str, required: bool = True) -> Decimal | None:
    if value in (None, ""):
        if required:
            one(field, f"请填写{label}")
        return None
    try:
        number = Decimal(str(value))
    except Exception:
        one(field, f"{label}格式不正确")
        return None
    if number < 0:
        one(field, f"{label}不能为负数")
    quant = number.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if quant != number:
        one(field, f"{label}最多两位小数")
    return quant


def int_of(value, field: str, label: str, required: bool = True) -> int | None:
    if value in (None, ""):
        if required:
            one(field, f"请填写{label}")
        return None
    if isinstance(value, bool):
        one(field, f"{label}须为整数")
    text = str(value).strip()
    if "." in text or not text.lstrip("-").isdigit():
        one(field, f"{label}须为整数")
    number = int(text)
    if number < 0:
        one(field, f"{label}不能为负数")
    return number


def limit_text(value, field: str, label: str, max_len: int, required: bool = False) -> str:
    text = "" if value is None else str(value).strip()
    if required and not text:
        one(field, f"请填写{label}")
    if len(text) > max_len:
        one(field, f"{label}最多 {max_len} 字")
    return text


def trace(session_id: int, event: str, title: str, detail: str = "") -> None:
    get_session().add(
        Timeline(
            biz_type="LIVE",
            biz_id=int(session_id),
            event_type=event,
            title=title[:100],
            detail={"text": detail} if detail else {},
            operator_id=viewer_id() or None,
            event_time=now_naive(),
        )
    )
    get_session().flush()


def timeline_of(session_id: int) -> list[dict]:
    rows = list(
        get_session().scalars(
            select(Timeline)
            .where(Timeline.biz_type == "LIVE", Timeline.biz_id == int(session_id))
            .order_by(Timeline.event_time.asc(), Timeline.id.asc())
        )
    )
    names = _names([row.operator_id for row in rows])
    return [
        {
            "id": row.id,
            "eventType": row.event_type,
            "title": row.title,
            "detail": (row.detail or {}).get("text") if isinstance(row.detail, dict) else "",
            "eventTime": format_datetime(row.event_time),
            "operatorName": names.get(int(row.operator_id or 0), "系统"),
        }
        for row in rows
    ]


def _names(ids) -> dict[int, str]:
    wanted = [int(item) for item in ids if item]
    if not wanted:
        return {}
    rows = list(get_session().scalars(select(User).where(User.id.in_(wanted))))
    return {int(row.id): row.nickname or row.username for row in rows}


def user_name(user_id: int | None) -> str:
    if not user_id:
        return ""
    return _names([user_id]).get(int(user_id), "")


def close_todos(source_type: str, source_id: int) -> None:
    rows = list(
        get_session().scalars(
            select(Todo).where(Todo.source_type == source_type, Todo.source_id == int(source_id), Todo.status == "PENDING")
        )
    )
    for row in rows:
        row.status = "CANCELLED"
    get_session().flush()


def scope_mode() -> tuple[str, int, list[int]]:
    ctx = get_ctx()
    if ctx is None or ctx.system or ctx.skip_scope:
        return "all", 0, []
    scopes = {item for item in (ctx.data_scopes or set()) if item}
    if not scopes or "ALL" in scopes:
        return "all", 0, []
    user_id = int(ctx.user_id or 0)
    if scopes == {"SELF"} or ("SELF" in scopes and "DEPT" not in scopes and "IP_GROUP" not in scopes):
        return "self", user_id, []
    groups = [int(item) for item in get_session().scalars(select(IpMember.group_id).where(IpMember.user_id == user_id))]
    return "group", user_id, groups


def apply_scope(stmt):
    kind, user_id, groups = scope_mode()
    if kind == "all":
        return stmt
    if kind == "self":
        return stmt.where(LiveSession.responsible_user_id == user_id)
    if not groups:
        return stmt.where(LiveSession.responsible_user_id == user_id)
    return stmt.where(or_(LiveSession.responsible_user_id == user_id, LiveSession.ip_group_id.in_(groups)))


def in_scope(row: LiveSession) -> bool:
    kind, user_id, groups = scope_mode()
    if kind == "all":
        return True
    if int(row.responsible_user_id or 0) == user_id:
        return True
    return kind == "group" and int(row.ip_group_id or 0) in groups


def require_scope(row: LiveSession) -> None:
    if not in_scope(row):
        raise BizError(1008, "您无权查看该场次")


def broad_editor() -> bool:
    return has_perm("ims:live:session:approve") or has_perm("ims:live:report:correct")


def owns(row: LiveSession) -> bool:
    return int(row.responsible_user_id or 0) == viewer_id()


def show_money(row: LiveSession) -> bool:
    """财务字段：全量范围可见；本人 / IP 组范围只看自己负责的场次。"""
    if not has_perm("ims:live:report:finance"):
        return False
    kind, _, _ = scope_mode()
    if kind == "all":
        return True
    return owns(row)


def view_mode() -> str:
    """finance：只回财务列；hide：去掉金额；full：全字段。"""
    finance = has_perm("ims:live:report:finance")
    broad = any(
        has_perm(code)
        for code in (
            "ims:live:session:register",
            "ims:live:session:approve",
            "ims:live:alarm:query",
            "ims:live:report:correct",
            "ims:live:report:entry",
        )
    )
    if finance and not broad:
        return "finance"
    if not finance:
        return "hide"
    return "full"


def money_text(value) -> str | None:
    if value is None:
        return None
    return f"{Decimal(value).quantize(Decimal('0.01')):.2f}"


def duration_text(minutes) -> str:
    if minutes in (None, ""):
        return "—"
    total = int(minutes)
    hours, mins = divmod(total, 60)
    if hours and mins:
        return f"{hours} 小时 {mins} 分"
    if hours:
        return f"{hours} 小时"
    return f"{mins} 分"


def divide(left, right) -> str | None:
    if right in (None, 0, Decimal("0")):
        return None
    if left is None:
        return None
    return f"{(Decimal(left) / Decimal(right)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):.2f}"


def when_text(value) -> str:
    return format_datetime(value) if value else ""


def hours_between(start: datetime, end: datetime) -> float:
    return (end - start).total_seconds() / 3600


def plus_hours(value: datetime, hours: int) -> datetime:
    return value + timedelta(hours=hours)


def body_text(body: dict, key: str) -> str:
    return text_of(body, key)
