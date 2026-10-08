"""DC-001 账号穿透查询（W9-3 只读首片 · 聚合层 mock）。"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, ok
from app.corp import page_args, tenant_of
from app.models import LiveSession, User

router = APIRouter(prefix="/dc/trace", tags=["dc-trace"])

BJ = timezone(timedelta(hours=8))
ENTRY_TYPES = frozenset({"PERSON", "ACCOUNT", "ASSET", "SESSION", "RESPONSIBLE", "IP_GROUP"})


class TraceQueryBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    entryType: str
    entryId: str
    mode: str = "GRAPH"
    pageNo: int = 1
    pageSize: int = 10
    dateRange: list[str] | None = None


def data_as_of() -> str:
    return datetime.now(BJ).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def session_rows(db: Session, tenant_id: int, limit: int = 20) -> list[LiveSession]:
    return list(
        db.scalars(
            select(LiveSession)
            .where(LiveSession.deleted == 0, LiveSession.tenant_id == tenant_id)
            .order_by(LiveSession.id.desc())
            .limit(limit)
        ).all()
    )


def build_graph_from_sessions(sessions: list[LiveSession]) -> dict:
    nodes: list[dict] = []
    edges: list[dict] = []
    seen: set[str] = set()

    def add_node(node_type: str, node_id: str, label: str, **extra) -> str:
        key = f"{node_type}:{node_id}"
        if key not in seen:
            seen.add(key)
            nodes.append({"nodeType": node_type, "nodeId": node_id, "nodeLabel": label, **extra})
        return node_id

    for row in sessions:
        person_id = add_node("PERSON", str(row.realname_person_id or 0), row.realname_name or "实名人")
        account_id = add_node(
            "ACCOUNT",
            str(row.account_id or 0),
            row.account_no or f"账号#{row.account_id}",
            platform=row.platform or None,
        )
        session_id = add_node("SESSION", row.session_code, row.topic or row.session_code, platform=row.platform)
        edges.append({"fromNodeId": person_id, "toNodeId": account_id})
        edges.append({"fromNodeId": account_id, "toNodeId": session_id})
    return {"nodes": nodes, "edges": edges}


def detail_from_sessions(sessions: list[LiveSession], page_no: int, size: int) -> tuple[list[dict], int]:
    total = len(sessions)
    chunk = sessions[(page_no - 1) * size : page_no * size]
    rows = []
    for row in chunk:
        rows.append(
            {
                "sessionCode": row.session_code,
                "sessionTitle": row.topic or row.session_code,
                "platform": row.platform,
                "realnamePersonId": int(row.realname_person_id or 0),
                "realnameName": row.realname_name or "",
                "accountId": int(row.account_id or 0),
                "accountNo": row.account_no or "",
                "assetIds": [],
                "gmv": None,
                "netProfit": None,
                "statPeriod": (row.plan_start_time or "")[:7],
            }
        )
    return rows, total


@router.get("/entry")
def trace_entry(
    keyword: str = "",
    entryType: str = "ACCOUNT",
    limit: int = 20,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    if entryType not in ENTRY_TYPES:
        entryType = "ACCOUNT"
    kw = keyword.strip()
    lim = min(max(limit, 1), 50)
    items: list[dict] = []
    if entryType == "ACCOUNT":
        stmt = select(LiveSession).where(LiveSession.deleted == 0, LiveSession.tenant_id == tenant_id)
        if kw:
            stmt = stmt.where(
                or_(LiveSession.account_no.contains(kw), LiveSession.session_code.contains(kw))
            )
        for row in db.scalars(stmt.order_by(LiveSession.id.desc()).limit(lim)).all():
            if not row.account_id:
                continue
            items.append(
                {
                    "entryType": "ACCOUNT",
                    "entryId": str(row.account_id),
                    "entryLabel": row.account_no or f"账号#{row.account_id}",
                    "platform": row.platform,
                    "hint": f"最近场次 {row.session_code}",
                }
            )
    elif entryType == "SESSION":
        stmt = select(LiveSession).where(LiveSession.deleted == 0, LiveSession.tenant_id == tenant_id)
        if kw:
            stmt = stmt.where(
                or_(LiveSession.session_code.contains(kw), LiveSession.topic.contains(kw))
            )
        for row in db.scalars(stmt.order_by(LiveSession.id.desc()).limit(lim)).all():
            items.append(
                {
                    "entryType": "SESSION",
                    "entryId": row.session_code,
                    "entryLabel": row.topic or row.session_code,
                    "platform": row.platform,
                    "hint": row.account_no or "",
                }
            )
    else:
        for row in session_rows(db, tenant_id, lim):
            if entryType == "PERSON" and row.realname_person_id:
                items.append(
                    {
                        "entryType": "PERSON",
                        "entryId": str(row.realname_person_id),
                        "entryLabel": row.realname_name or f"实名人#{row.realname_person_id}",
                        "hint": row.account_no or "",
                    }
                )
    dedup: dict[str, dict] = {}
    for item in items:
        dedup[f"{item['entryType']}:{item['entryId']}"] = item
    return ok(list(dedup.values())[:lim])


@router.post("/query")
def trace_query(
    body: TraceQueryBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    if body.entryType not in ENTRY_TYPES:
        return ok({"queryCostMs": 0, "dataAsOf": data_as_of(), "nodes": [], "edges": []})
    started = time.perf_counter()
    stmt = select(LiveSession).where(LiveSession.deleted == 0, LiveSession.tenant_id == tenant_id)
    entry_id = body.entryId.strip()
    if body.entryType == "ACCOUNT":
        stmt = stmt.where(LiveSession.account_id == int(entry_id or 0))
    elif body.entryType == "SESSION":
        stmt = stmt.where(LiveSession.session_code == entry_id)
    elif body.entryType == "PERSON":
        stmt = stmt.where(LiveSession.realname_person_id == int(entry_id or 0))
    elif body.entryType == "RESPONSIBLE":
        stmt = stmt.where(LiveSession.responsible_user_id == int(entry_id or 0))
    sessions = list(db.scalars(stmt.order_by(LiveSession.id.desc()).limit(50)).all())
    if not sessions:
        sessions = session_rows(db, tenant_id, 5)
    graph = build_graph_from_sessions(sessions)
    page_no, size = page_args(body.pageNo, body.pageSize)
    detail_list = None
    if body.mode == "DETAIL":
        rows, total = detail_from_sessions(sessions, page_no, size)
        detail_list = {"list": rows, "total": total, "pageNo": page_no, "pageSize": size}
    elapsed = round((time.perf_counter() - started) * 1000, 1)
    payload = {
        "queryCostMs": elapsed,
        "dataAsOf": data_as_of(),
        **graph,
    }
    if detail_list is not None:
        payload["detailList"] = detail_list
    return ok(payload)
