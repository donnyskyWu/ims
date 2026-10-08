"""DC-001 穿透查询（#52 账号入口 · #53 场次下钻与明细导出）。"""

from __future__ import annotations

import secrets
import time
import zipfile
from datetime import datetime, timedelta, timezone
from io import BytesIO

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.core import mask_name
from app.corp import page_args, tenant_of, user_names
from app.dc_profit_trace import cost_detail_rows, parse_asset_ids
from app.fin import approved_report, load_fin_cost, load_profit, money, net_profit_rate, operating_profit
from app.live import get_session
from app.models import LiveSession, User

router = APIRouter(prefix="/dc/trace", tags=["dc-trace"])

BJ = timezone(timedelta(hours=8))
ENTRY_TYPES = frozenset({"PERSON", "ACCOUNT", "ASSET", "SESSION", "RESPONSIBLE", "IP_GROUP"})
WIDE_RANGE_DAYS = 92
TIMEOUT_MS = 3000
TIMEOUT_MSG = "穿透查询超时降级，请缩小日期范围"
EXPORT_TTL_SEC = 300

# token -> (expires_at, body, media_type, filename, user_id)
_EXPORTS: dict[str, tuple[float, bytes, str, str, int]] = {}


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


def as_int(value: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def range_too_wide(date_range: list[str] | None) -> bool:
    if not date_range or len(date_range) < 2:
        return False
    try:
        start = datetime.strptime((date_range[0] or "")[:10], "%Y-%m-%d")
        end = datetime.strptime((date_range[1] or "")[:10], "%Y-%m-%d")
    except ValueError:
        return False
    return (end - start).days > WIDE_RANGE_DAYS


def filter_by_date(sessions: list[LiveSession], date_range: list[str] | None) -> list[LiveSession]:
    if not date_range or len(date_range) < 2:
        return sessions
    start = (date_range[0] or "")[:10]
    end = (date_range[1] or "")[:10]
    if not start or not end:
        return sessions
    kept: list[LiveSession] = []
    for row in sessions:
        anchor = (row.actual_start or row.plan_start_time or "")[:10]
        if not anchor or start <= anchor <= end:
            kept.append(row)
    return kept


def session_rows(db: Session, tenant_id: int, limit: int = 20) -> list[LiveSession]:
    return list(
        db.scalars(
            select(LiveSession)
            .where(LiveSession.deleted == 0, LiveSession.tenant_id == tenant_id)
            .order_by(LiveSession.id.desc())
            .limit(limit)
        ).all()
    )


def load_entry_sessions(db: Session, tenant_id: int, entry_type: str, entry_id: str) -> list[LiveSession]:
    stmt = select(LiveSession).where(LiveSession.deleted == 0, LiveSession.tenant_id == tenant_id)
    entry_id = (entry_id or "").strip()
    if entry_type == "ACCOUNT":
        stmt = stmt.where(LiveSession.account_id == as_int(entry_id))
    elif entry_type == "SESSION":
        stmt = stmt.where(LiveSession.session_code == entry_id)
    elif entry_type == "PERSON":
        stmt = stmt.where(LiveSession.realname_person_id == as_int(entry_id))
    elif entry_type == "RESPONSIBLE":
        stmt = stmt.where(LiveSession.responsible_user_id == as_int(entry_id))
    return list(db.scalars(stmt.order_by(LiveSession.id.desc()).limit(50)).all())


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
                "assetIds": parse_asset_ids(row.device_asset_ids or "[]"),
                "gmv": None,
                "netProfit": None,
                "statPeriod": (row.plan_start_time or "")[:7],
            }
        )
    return rows, total


def session_detail(db: Session, tenant_id: int, session: LiveSession, *, masked: bool) -> dict:
    report = approved_report(db, session.session_code, tenant_id)
    cost = load_fin_cost(db, tenant_id, session.session_code)
    profit = load_profit(db, tenant_id, session.session_code)
    names = user_names(db, {session.responsible_user_id} if session.responsible_user_id else set())
    gross = money(profit.gross_profit) if profit is not None else None
    net = money(profit.net_profit) if profit is not None else None
    operating = operating_profit(gross or 0, cost) if profit is not None else None
    rate = None
    if profit is not None and net is not None:
        rate = net_profit_rate(float(profit.revenue or 0), float(profit.refund_amount or 0), net)
    if masked:
        gross = operating = net = rate = None
    realname = session.realname_name or ""
    if masked and realname:
        realname = mask_name(realname)
    persons: list[dict] = []
    if session.responsible_user_id:
        persons.append(
            {
                "userId": int(session.responsible_user_id),
                "userName": names.get(session.responsible_user_id, ""),
                "roleType": "RESPONSIBLE",
            }
        )
    if session.realname_person_id or realname:
        persons.append(
            {
                "userId": int(session.realname_person_id or 0),
                "userName": realname,
                "roleType": "REALNAME",
            }
        )
    gmv = money(report.gmv) if report is not None else 0.0
    refund = money(report.refund_amount) if report is not None else 0.0
    return {
        "sessionCode": session.session_code,
        "sessionTitle": session.topic or session.session_code,
        "platform": session.platform,
        "liveData": {
            "gmv": gmv,
            "refund": refund,
            "uv": int(report.viewer_count) if report is not None else None,
            "durationMinutes": int(report.duration_minutes) if report is not None else None,
        },
        "profit": {
            "grossProfit": gross,
            "operatingProfit": operating,
            "netProfit": net,
            "netProfitRate": rate,
            "calcVersion": int(profit.calc_version or 1) if profit is not None else 0,
        },
        "costDetail": cost_detail_rows(cost, masked=masked),
        "persons": persons,
        "account": {
            "accountId": int(session.account_id or 0),
            "accountNo": session.account_no or "",
            "nickname": session.account_no or "",
        },
        "assetIds": parse_asset_ids(session.device_asset_ids or "[]"),
        "dataAsOf": data_as_of(),
    }


def export_matrix(db: Session, tenant_id: int, sessions: list[LiveSession], elapsed: float) -> list[list[str]]:
    rows: list[list[str]] = [
        ["queryCostMs", str(elapsed)],
        ["sessionCode", "sessionTitle", "platform", "accountNo", "gmv", "netProfit"],
    ]
    for row in sessions:
        report = approved_report(db, row.session_code, tenant_id)
        profit = load_profit(db, tenant_id, row.session_code)
        rows.append(
            [
                row.session_code,
                row.topic or row.session_code,
                row.platform or "",
                row.account_no or "",
                "" if report is None else str(money(report.gmv)),
                "" if profit is None else str(money(profit.net_profit)),
            ]
        )
    return rows


def _xml_text(value: str) -> str:
    return (
        (value or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def build_xlsx(rows: list[list[str]]) -> bytes:
    sheet_rows: list[str] = []
    for r_idx, row in enumerate(rows, 1):
        cells: list[str] = []
        for c_idx, value in enumerate(row):
            col = chr(ord("A") + c_idx)
            cells.append(
                f'<c r="{col}{r_idx}" t="inlineStr"><is><t>{_xml_text(value)}</t></is></c>'
            )
        sheet_rows.append(f'<row r="{r_idx}">{"".join(cells)}</row>')
    sheet = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheetData>{''.join(sheet_rows)}</sheetData></worksheet>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        "</Types>"
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>'
        "</Relationships>"
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="trace" sheetId="1" r:id="rId1"/></sheets></workbook>'
    )
    workbook_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/>'
        "</Relationships>"
    )
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", rels)
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        archive.writestr("xl/worksheets/sheet1.xml", sheet)
    return buf.getvalue()


def build_pdf(lines: list[str]) -> bytes:
    commands = ["BT", "/F1 11 Tf", "40 780 Td"]
    for index, line in enumerate(lines):
        safe = "".join(ch if 32 <= ord(ch) < 127 else "?" for ch in line)
        safe = safe.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        if index:
            commands.append("0 -16 Td")
        commands.append(f"({safe}) Tj")
    commands.append("ET")
    stream = "\n".join(commands).encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Count 1 /Kids [3 0 R] >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            b"/Contents 5 0 R /Resources << /Font << /F1 4 0 R >> >> >>"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, obj in enumerate(objects, 1):
        offsets.append(len(out))
        out.extend(f"{number} 0 obj\n".encode("ascii"))
        out.extend(obj)
        out.extend(b"\nendobj\n")
    xref = len(out)
    out.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    out.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        out.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    out.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("ascii")
    )
    return bytes(out)


def matrix_lines(rows: list[list[str]]) -> list[str]:
    lines: list[str] = []
    for row in rows:
        lines.append(" | ".join(row))
    return lines


def purge_exports(now: float) -> None:
    dead = [key for key, item in _EXPORTS.items() if item[0] < now]
    for key in dead:
        _EXPORTS.pop(key, None)


def issue_export(actor_id: int, body: bytes, media: str, filename: str) -> dict:
    now = time.time()
    purge_exports(now)
    token = secrets.token_urlsafe(24)
    _EXPORTS[token] = (now + EXPORT_TTL_SEC, body, media, filename, actor_id)
    return {
        "downloadUrl": f"/admin-api/ims/dc/trace/export/file?token={token}",
        "expiresIn": EXPORT_TTL_SEC,
    }


def degraded_payload(elapsed: float) -> dict:
    return {
        "queryCostMs": elapsed,
        "dataAsOf": data_as_of(),
        "nodes": [],
        "edges": [],
    }


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
    started = time.perf_counter()
    if body.entryType not in ENTRY_TYPES:
        elapsed = round((time.perf_counter() - started) * 1000, 1)
        return ok({"queryCostMs": elapsed, "dataAsOf": data_as_of(), "nodes": [], "edges": []})
    if range_too_wide(body.dateRange):
        elapsed = round((time.perf_counter() - started) * 1000, 1)
        return fail(1181, TIMEOUT_MSG, degraded_payload(elapsed))
    sessions = filter_by_date(
        load_entry_sessions(db, tenant_id, body.entryType, body.entryId),
        body.dateRange,
    )
    graph = build_graph_from_sessions(sessions)
    page_no, size = page_args(body.pageNo, body.pageSize)
    detail_list = None
    if body.mode == "DETAIL":
        rows, total = detail_from_sessions(sessions, page_no, size)
        detail_list = {"list": rows, "total": total, "pageNo": page_no, "pageSize": size}
    elapsed = round((time.perf_counter() - started) * 1000, 1)
    if elapsed > TIMEOUT_MS:
        return fail(1181, TIMEOUT_MSG, degraded_payload(elapsed))
    payload = {
        "queryCostMs": elapsed,
        "dataAsOf": data_as_of(),
        **graph,
    }
    if detail_list is not None:
        payload["detailList"] = detail_list
    return ok(payload)


@router.get("/detail/{session_code}")
def trace_detail(
    session_code: str,
    request: Request,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    session = get_session(db, actor, getattr(request.state, "scope", None), session_code)
    if session is None:
        return fail(1504, "资源不可用")
    masked = request.state.scope is not None and request.state.scope.kind == "SELF"
    return ok(session_detail(db, tenant_of(actor), session, masked=masked))


@router.get("/export")
def trace_export(
    entryType: str,
    entryId: str,
    format: str = "XLSX",
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    if format not in {"XLSX", "PDF"}:
        return fail(1001, "format 仅支持 XLSX 或 PDF")
    if entryType not in ENTRY_TYPES:
        return fail(1001, "entryType 无效")
    started = time.perf_counter()
    sessions = load_entry_sessions(db, tenant_of(actor), entryType, entryId)
    elapsed = round((time.perf_counter() - started) * 1000, 1)
    matrix = export_matrix(db, tenant_of(actor), sessions, elapsed)
    if format == "PDF":
        body = build_pdf(matrix_lines(matrix))
        media = "application/pdf"
        filename = "dc_trace_report.pdf"
    else:
        body = build_xlsx(matrix)
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = "dc_trace_report.xlsx"
    return ok(issue_export(actor.id, body, media, filename))


@router.get("/export/file")
def trace_export_file(
    token: str,
    actor: User = Depends(current_user),
):
    now = time.time()
    purge_exports(now)
    item = _EXPORTS.get(token)
    if item is None or item[0] < now:
        return fail(1002, "下载链接已过期")
    if item[4] != actor.id:
        return fail(1008, "无数据权限")
    _expires, body, media, filename, _user_id = item
    return Response(
        content=body,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
