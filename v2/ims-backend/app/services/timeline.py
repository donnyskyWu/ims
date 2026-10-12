"""通用时间线。查询按事件时间倒序。"""
from __future__ import annotations

from sqlalchemy import select

from app.db.session import get_session
from app.domains.system.model import Timeline


def query_timeline(biz_type: str, biz_id: int) -> list[dict]:
    rows = list(
        get_session().scalars(
            select(Timeline)
            .where(Timeline.biz_type == biz_type, Timeline.biz_id == int(biz_id))
            .order_by(Timeline.event_time.desc(), Timeline.id.desc())
        )
    )
    return [
        {
            "id": row.id,
            "bizType": row.biz_type,
            "bizId": row.biz_id,
            "eventType": row.event_type,
            "title": row.title,
            "eventTime": row.event_time,
            "operatorId": row.operator_id,
        }
        for row in rows
    ]
