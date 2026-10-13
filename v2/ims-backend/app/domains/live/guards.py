"""给 B6 / B7 的只增查询。"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select

from app.db.session import get_session
from app.domains.device.model import AssetBind
from app.domains.live.model import LiveCost, LiveReport
from app.domains.master.model import LiveSession


def open_hint(account_id: int) -> str:
    from app.domains.live.service import open_session_codes

    codes = [item for item in open_session_codes(int(account_id)) if item]
    if not codes:
        return ""
    return f"该账号有未结束场次 {codes[0]}"


def on_account_status(account_id: int, status: str) -> None:
    from app.domains.live.alarm import on_account

    on_account(int(account_id), status)


def recent_sessions(asset_id: int) -> list[dict]:
    binds = list(
        get_session().scalars(select(AssetBind).where(AssetBind.asset_id == int(asset_id), AssetBind.session_id.is_not(None)))
    )
    seen = []
    for bind in binds:
        row = get_session().get(LiveSession, bind.session_id)
        if row is None or row.deleted or not row.session_code:
            continue
        if row.session_code in {item["sessionCode"] for item in seen}:
            continue
        seen.append(
            {
                "sessionCode": row.session_code,
                "topic": row.topic or "",
                "status": row.session_status,
                "start": (row.actual_start_time or row.plan_start_time).isoformat(sep=" ") if (row.actual_start_time or row.plan_start_time) else "",
            }
        )
    seen.sort(key=lambda item: item["start"], reverse=True)
    return seen[:10]


def confirmed_cost(asset_id: int) -> dict:
    binds = list(
        get_session().scalars(select(AssetBind).where(AssetBind.asset_id == int(asset_id), AssetBind.session_id.is_not(None)))
    )
    ad = Decimal("0")
    total = Decimal("0")
    for bind in binds:
        report = get_session().scalar(select(LiveReport).where(LiveReport.session_id == int(bind.session_id), LiveReport.entry_status == "CONFIRMED"))
        if report is None:
            continue
        ad += Decimal(report.ad_cost or 0)
        costs = list(get_session().scalars(select(LiveCost).where(LiveCost.session_id == int(bind.session_id))))
        total += sum((Decimal(item.amount or 0) for item in costs), Decimal("0"))
    return {"adCost": f"{ad:.2f}", "costTotal": f"{total:.2f}"}


def held_by_ended(asset_id: int) -> bool:
    binds = list(
        get_session().scalars(
            select(AssetBind).where(AssetBind.asset_id == int(asset_id), AssetBind.bind_status == "ACTIVE", AssetBind.session_id.is_not(None))
        )
    )
    for bind in binds:
        row = get_session().get(LiveSession, bind.session_id)
        if row is not None and row.session_status == "ENDED":
            return True
    return False
