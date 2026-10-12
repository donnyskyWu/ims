"""字段级变更历史。"""
from __future__ import annotations

from app.core.context import get_ctx
from app.core.serialize import ser_money
from app.db.session import get_session


def _show(column, value):
    kind = (column.info or {}).get("sensitive") if column is not None else None
    if kind == "mobile" and value:
        text = str(value)
        return text[:3] + "****" + text[-4:] if len(text) >= 7 else "****"
    if kind == "id_card" and value:
        text = str(value)
        return text[:3] + "*" * max(0, len(text) - 7) + text[-4:]
    if kind == "cost":
        return "***"
    if value is None:
        return None
    if hasattr(value, "quantize"):
        return ser_money(value)
    return str(value)


def write_change(biz_type: str, biz_id: int, field: str, label: str, before, after, reason: str, column=None):
    from app.domains.system.model import ChangeLog

    ctx = get_ctx()
    row = ChangeLog(
        biz_type=biz_type,
        biz_id=biz_id,
        field=field,
        field_label=label or field,
        before_value=_show(column, before),
        after_value=_show(column, after),
        reason=reason,
        operator_id=ctx.user_id if ctx else 0,
    )
    get_session().add(row)


def diff_and_log(obj, before: dict, reason: str = "USER_EDIT"):
    if not getattr(obj.__class__, "__track_changes__", False):
        return
    for column in obj.__table__.columns:
        name = column.name
        if name in {"updater", "update_time", "creator", "create_time", "deleted", "tenant_id"}:
            continue
        old = before.get(name)
        new = getattr(obj, name)
        if old != new:
            labels = getattr(obj.__class__, "__field_labels__", {})
            write_change(obj.__tablename__, obj.id, name, labels.get(name, name), old, new, reason, column)
