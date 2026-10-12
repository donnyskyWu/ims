"""工作日历与应提交天数。考勤未启用时不扣请假。"""
from __future__ import annotations

import calendar
from datetime import date
from decimal import Decimal

from sqlalchemy import select

from app.core.config import get_settings
from app.core.errors import BizError
from app.db.session import get_session
from app.domains.system.model import LeaveRecord, SyncState, WorkCalendar


def _month_bounds(month: str) -> tuple[date, date]:
    year, mon = [int(part) for part in month.split("-")]
    last = calendar.monthrange(year, mon)[1]
    return date(year, mon, 1), date(year, mon, last)


def _is_weekday(day: date) -> bool:
    return day.weekday() < 5


def calendar_map(month: str) -> dict[str, str]:
    start, end = _month_bounds(month)
    rows = get_session().scalars(select(WorkCalendar).where(WorkCalendar.cal_date >= start.isoformat(), WorkCalendar.cal_date <= end.isoformat()))
    return {row.cal_date: row.day_type for row in rows}


def base_days(month: str) -> Decimal:
    start, end = _month_bounds(month)
    marked = calendar_map(month)
    total = Decimal("0")
    cursor = start
    while cursor <= end:
        kind = marked.get(cursor.isoformat())
        if kind == "HOLIDAY":
            pass
        elif kind == "WORKDAY_ADJUST" or _is_weekday(cursor):
            total += 1
        cursor = date.fromordinal(cursor.toordinal() + 1)
    return total


def is_workday(day: date, marked: dict[str, str] | None = None) -> bool:
    kind = (marked or {}).get(day.isoformat())
    if kind == "HOLIDAY":
        return False
    if kind == "WORKDAY_ADJUST":
        return True
    return _is_weekday(day)


def should_days(user_id: int, month: str) -> dict:
    base = base_days(month)
    settings = get_settings()
    enabled = str((settings.dingtalk_attendance or {}).get("enabled", False)).lower() in {"1", "true", "yes"}
    state = get_session().scalar(select(SyncState).where(SyncState.state_key == f"attendance:{month}"))
    if enabled and state is not None and state.state_value in {"FAILED", "同步失败"}:
        return {"shouldDays": base, "degraded": True}
    if not enabled:
        return {"shouldDays": base, "degraded": False}
    start, end = _month_bounds(month)
    marked = calendar_map(month)
    rows = list(
        get_session().scalars(
            select(LeaveRecord).where(
                LeaveRecord.user_id == user_id,
                LeaveRecord.leave_date >= start.isoformat(),
                LeaveRecord.leave_date <= end.isoformat(),
            )
        )
    )
    deducted = Decimal("0")
    for row in rows:
        day = date.fromisoformat(row.leave_date)
        if is_workday(day, marked):
            deducted += Decimal(row.portion)
    return {"shouldDays": base - deducted, "degraded": False}


def update_calendar(cal_date: str, day_type: str) -> dict:
    if day_type not in {"HOLIDAY", "WORKDAY_ADJUST"}:
        raise BizError(1001, data={"fieldErrors": [{"field": "dayType", "message": "日期类型不正确"}]})
    session = get_session()
    row = session.scalar(select(WorkCalendar).where(WorkCalendar.cal_date == cal_date))
    if row is None:
        row = WorkCalendar(cal_date=cal_date, day_type=day_type)
        session.add(row)
    else:
        row.day_type = day_type
    session.flush()
    return {"date": cal_date, "dayType": day_type}


def pull_leaves() -> dict:
    from app.integrations.dingtalk_attendance.client import list_leaves

    try:
        rows = list_leaves([], "", "")
    except BizError:
        _persist_state("同步失败")
        raise
    session = get_session()
    for item in rows:
        exists = session.scalar(
            select(LeaveRecord).where(
                LeaveRecord.user_id == int(item["userId"]),
                LeaveRecord.leave_date == item["leaveDate"],
                LeaveRecord.approval_no == item["approvalNo"],
            )
        )
        if exists is None:
            session.add(
                LeaveRecord(
                    user_id=int(item["userId"]),
                    leave_date=item["leaveDate"],
                    portion=item.get("portion") or 1,
                    approval_no=item["approvalNo"],
                )
            )
    _mark("OK")
    session.flush()
    return {"count": len(rows)}


def _mark(value: str) -> None:
    from app.core.clock import now_naive

    month = now_naive().strftime("%Y-%m")
    session = get_session()
    row = session.scalar(select(SyncState).where(SyncState.state_key == f"attendance:{month}"))
    if row is None:
        session.add(SyncState(state_key=f"attendance:{month}", state_value=value))
    else:
        row.state_value = value


def read_attendance_config() -> dict:
    """考勤配置读取。AppSecret 只回显掩码。"""
    settings = get_settings()
    block = settings.dingtalk_attendance or {}
    return {
        "appKey": block.get("app_key") or "",
        "appSecret": "******",
        "enabled": block.get("enabled", False),
        "groupName": "钉钉考勤",
    }


def read_dingtalk_app_config() -> dict:
    settings = get_settings()
    block = settings.dingtalk or {}
    return {"appKey": block.get("app_key") or "", "appSecret": "******", "groupName": "钉钉"}


def set_attendance_app_key(value: str) -> dict:
    """只改考勤 AppKey，不动 IMS 钉钉应用。"""
    settings = get_settings()
    settings.dingtalk_attendance["app_key"] = value
    _write_param("dingtalk_attendance.app_key", value)
    return {"attendanceAppKey": value, "dingtalkAppKey": (settings.dingtalk or {}).get("app_key")}


def set_dingtalk_app_key(value: str) -> dict:
    """只改 IMS 钉钉应用 AppKey，不动考勤。"""
    settings = get_settings()
    settings.dingtalk["app_key"] = value
    _write_param("dingtalk.app_key", value)
    return {"dingtalkAppKey": value, "attendanceAppKey": (settings.dingtalk_attendance or {}).get("app_key")}


def update_attendance_secret(raw: str) -> dict:
    """写入密钥，操作日志和适配器日志只保留掩码。"""
    import json

    from app.domains.system.model import OperateLog
    from app.domains.system.service import param_update
    from app.integrations.dingtalk_attendance.client import ADAPTER_LOGS

    settings = get_settings()
    settings.dingtalk_attendance["app_secret"] = raw
    param_update("dingtalk_attendance.app_secret", raw)
    digest = json.dumps({"appKey": settings.dingtalk_attendance.get("app_key") or "", "appSecret": "******"}, ensure_ascii=False)
    get_session().add(
        OperateLog(
            module="钉钉考勤",
            action="修改考勤密钥",
            method="PUT",
            path="/admin-api/ims/system/param/update",
            params_digest=digest,
            success=1,
        )
    )
    ADAPTER_LOGS.append({"action": "config", "appSecret": "******"})
    get_session().flush()
    return read_attendance_config()


def _write_param(key: str, value: str) -> None:
    from app.domains.system.service import param_update

    param_update(key, value)


def _persist_state(value: str) -> None:
    """失败标记单独提交，避免调用方回滚时把 FAILED 一起丢掉。"""
    from app.core.clock import now_naive
    from app.core.context import system_context, use_context
    from app.db.session import session_scope

    month = now_naive().strftime("%Y-%m")
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            row = session.scalar(select(SyncState).where(SyncState.state_key == f"attendance:{month}"))
            if row is None:
                session.add(SyncState(state_key=f"attendance:{month}", state_value=value))
            else:
                row.state_value = value
