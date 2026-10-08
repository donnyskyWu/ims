"""DC-001 穿透查询（#52 账号 · #53 场次下钻 · #88 实名人/责任人/资产/IP 组）。"""

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
from app.ops_db import ops_session
from app.ops_models import IpGroup, Phone, PlatformAccount

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


def base_sessions(tenant_id: int):
    return select(LiveSession).where(LiveSession.deleted == 0, LiveSession.tenant_id == tenant_id)


def asset_label(phone: Phone | None, asset_id: int) -> str:
    if phone is None:
        return f"资产#{asset_id}"
    label = (phone.phone_code or phone.device_number or phone.phone_model or "").strip()
    return label or f"资产#{asset_id}"


def asset_label_map(asset_ids: set[int]) -> dict[int, str]:
    if not asset_ids:
        return {}
    ops = ops_session()
    try:
        rows = ops.scalars(select(Phone).where(Phone.id.in_(asset_ids), Phone.deleted == 0)).all()
    finally:
        ops.close()
    found = {row.id: row for row in rows}
    return {asset_id: asset_label(found.get(asset_id), asset_id) for asset_id in asset_ids}


def sessions_containing_asset(db: Session, tenant_id: int, asset_id: int, limit: int = 50) -> list[LiveSession]:
    if not asset_id:
        return []
    rows = db.scalars(
        base_sessions(tenant_id)
        .where(LiveSession.device_asset_ids.contains(str(asset_id)))
        .order_by(LiveSession.id.desc())
        .limit(200)
    ).all()
    matched = [row for row in rows if asset_id in parse_asset_ids(row.device_asset_ids or "[]")]
    return matched[:limit]


def account_ids_in_group(tenant_id: int, group_id: int) -> list[int]:
    if not group_id:
        return []
    ops = ops_session()
    try:
        return list(
            ops.scalars(
                select(PlatformAccount.id).where(
                    PlatformAccount.deleted == 0,
                    PlatformAccount.tenant_id == tenant_id,
                    PlatformAccount.ip_group_id == group_id,
                )
            ).all()
        )
    finally:
        ops.close()


def load_entry_sessions(db: Session, tenant_id: int, entry_type: str, entry_id: str) -> list[LiveSession]:
    stmt = base_sessions(tenant_id)
    entry_id = (entry_id or "").strip()
    if entry_type == "ACCOUNT":
        stmt = stmt.where(LiveSession.account_id == as_int(entry_id))
    elif entry_type == "SESSION":
        stmt = stmt.where(LiveSession.session_code == entry_id)
    elif entry_type == "PERSON":
        stmt = stmt.where(LiveSession.realname_person_id == as_int(entry_id))
    elif entry_type == "RESPONSIBLE":
        stmt = stmt.where(LiveSession.responsible_user_id == as_int(entry_id))
    elif entry_type == "ASSET":
        return sessions_containing_asset(db, tenant_id, as_int(entry_id))
    elif entry_type == "IP_GROUP":
        account_ids = account_ids_in_group(tenant_id, as_int(entry_id))
        if not account_ids:
            return []
        stmt = stmt.where(LiveSession.account_id.in_(account_ids))
    else:
        return []
    return list(db.scalars(stmt.order_by(LiveSession.id.desc()).limit(50)).all())


def build_graph_from_sessions(sessions: list[LiveSession], labels: dict[int, str] | None = None) -> dict:
    nodes: list[dict] = []
    edges: list[dict] = []
    seen: set[str] = set()
    seen_edges: set[tuple[str, str]] = set()
    asset_labels = labels or {}

    def add_node(node_type: str, node_id: str, label: str, **extra) -> str:
        key = f"{node_type}:{node_id}"
        if key not in seen:
            seen.add(key)
            nodes.append({"nodeType": node_type, "nodeId": node_id, "nodeLabel": label, **extra})
        return node_id

    def add_edge(from_id: str, to_id: str) -> None:
        key = (from_id, to_id)
        if key in seen_edges or from_id == to_id:
            return
        seen_edges.add(key)
        edges.append({"fromNodeId": from_id, "toNodeId": to_id})

    for row in sessions:
        person_id = add_node("PERSON", str(row.realname_person_id or 0), row.realname_name or "实名人")
        account_id = add_node(
            "ACCOUNT",
            str(row.account_id or 0),
            row.account_no or f"账号#{row.account_id}",
            platform=row.platform or None,
        )
        session_id = add_node("SESSION", row.session_code, row.topic or row.session_code, platform=row.platform)
        add_edge(person_id, account_id)
        add_edge(account_id, session_id)
        for asset_id in parse_asset_ids(row.device_asset_ids or "[]"):
            asset_node = add_node("ASSET", str(asset_id), asset_labels.get(asset_id, f"资产#{asset_id}"))
            add_edge(asset_node, session_id)
    return {"nodes": nodes, "edges": edges}


def dedup_entries(items: list[dict], limit: int) -> list[dict]:
    dedup: dict[str, dict] = {}
    for item in items:
        dedup[f"{item['entryType']}:{item['entryId']}"] = item
    return list(dedup.values())[:limit]


def entry_item(entry_type: str, entry_id: str, label: str, hint: str, platform: str | None = None) -> dict:
    item = {
        "entryType": entry_type,
        "entryId": entry_id,
        "entryLabel": label,
        "hint": hint,
    }
    if platform:
        item["platform"] = platform
    return item


def search_person_entries(db: Session, tenant_id: int, keyword: str, limit: int) -> list[dict]:
    stmt = base_sessions(tenant_id).where(LiveSession.realname_person_id != 0)
    if keyword:
        conds = [LiveSession.realname_name.contains(keyword)]
        if keyword.isdigit():
            conds.append(LiveSession.realname_person_id == int(keyword))
        stmt = stmt.where(or_(*conds))
    items: list[dict] = []
    for row in db.scalars(stmt.order_by(LiveSession.id.desc()).limit(200)).all():
        items.append(
            entry_item(
                "PERSON",
                str(row.realname_person_id),
                row.realname_name or f"实名人#{row.realname_person_id}",
                row.account_no or "",
                row.platform,
            )
        )
    return dedup_entries(items, limit)


def search_responsible_entries(db: Session, tenant_id: int, keyword: str, limit: int) -> list[dict]:
    user_stmt = select(User).where(User.deleted == 0, User.tenant_id == tenant_id)
    if keyword:
        conds = [User.nickname.contains(keyword), User.username.contains(keyword)]
        if keyword.isdigit():
            conds.append(User.id == int(keyword))
        user_stmt = user_stmt.where(or_(*conds))
    users = list(db.scalars(user_stmt.order_by(User.id.asc()).limit(80)).all())
    items: list[dict] = []
    for user in users:
        row = db.scalar(
            base_sessions(tenant_id)
            .where(LiveSession.responsible_user_id == user.id)
            .order_by(LiveSession.id.desc())
            .limit(1)
        )
        if row is None:
            continue
        items.append(
            entry_item(
                "RESPONSIBLE",
                str(user.id),
                user.nickname or user.username or f"责任人#{user.id}",
                row.session_code,
            )
        )
        if len(items) >= limit:
            break
    return items


def search_asset_entries(db: Session, tenant_id: int, keyword: str, limit: int) -> list[dict]:
    ops = ops_session()
    try:
        phone_stmt = select(Phone).where(Phone.deleted == 0, Phone.tenant_id == tenant_id)
        exact_phone: Phone | None = None
        if keyword and keyword.isdigit():
            candidate = ops.get(Phone, int(keyword))
            if candidate is not None and not candidate.deleted and (candidate.tenant_id or 0) == tenant_id:
                exact_phone = candidate
        if keyword:
            conds = [
                Phone.phone_code.contains(keyword),
                Phone.device_number.contains(keyword),
                Phone.phone_model.contains(keyword),
            ]
            if keyword.isdigit():
                conds.append(Phone.id == int(keyword))
            phone_stmt = phone_stmt.where(or_(*conds))
        else:
            recent_ids: list[int] = []
            for row in session_rows(db, tenant_id, 80):
                for asset_id in parse_asset_ids(row.device_asset_ids or "[]"):
                    if asset_id not in recent_ids:
                        recent_ids.append(asset_id)
            if not recent_ids:
                return []
            phone_stmt = phone_stmt.where(Phone.id.in_(recent_ids[:80]))
        phones = list(ops.scalars(phone_stmt.order_by(Phone.id.asc()).limit(80)).all())
        if exact_phone is not None:
            phones = [exact_phone] + [phone for phone in phones if phone.id != exact_phone.id]
    finally:
        ops.close()
    items: list[dict] = []
    for phone in phones:
        row = None
        matched = sessions_containing_asset(db, tenant_id, phone.id, limit=1)
        if matched:
            row = matched[0]
        if row is None:
            continue
        items.append(
            entry_item(
                "ASSET",
                str(phone.id),
                asset_label(phone, phone.id),
                row.session_code,
                row.platform,
            )
        )
        if len(items) >= limit:
            break
    return items


def search_ip_group_entries(db: Session, tenant_id: int, keyword: str, limit: int) -> list[dict]:
    ops = ops_session()
    try:
        group_stmt = select(IpGroup).where(IpGroup.deleted == 0, IpGroup.tenant_id == tenant_id)
        exact: list[IpGroup] = []
        if keyword:
            exact = list(
                ops.scalars(
                    group_stmt.where(IpGroup.group_name == keyword).order_by(IpGroup.id.desc())
                ).all()
            )
            group_stmt = group_stmt.where(IpGroup.group_name.contains(keyword))
        groups = list(ops.scalars(group_stmt.order_by(IpGroup.id.desc()).limit(80)).all())
        if exact:
            seen_ids = {group.id for group in exact}
            groups = exact + [group for group in groups if group.id not in seen_ids]
        if not groups:
            return []
        group_ids = [group.id for group in groups]
        accounts = list(
            ops.scalars(
                select(PlatformAccount).where(
                    PlatformAccount.deleted == 0,
                    PlatformAccount.tenant_id == tenant_id,
                    PlatformAccount.ip_group_id.in_(group_ids),
                )
            ).all()
        )
    finally:
        ops.close()
    accounts_by_group: dict[int, list[int]] = {}
    for account in accounts:
        if account.ip_group_id:
            accounts_by_group.setdefault(account.ip_group_id, []).append(account.id)
    items: list[dict] = []
    for group in groups:
        account_ids = accounts_by_group.get(group.id) or []
        if not account_ids:
            continue
        row = db.scalar(
            base_sessions(tenant_id)
            .where(LiveSession.account_id.in_(account_ids))
            .order_by(LiveSession.id.desc())
            .limit(1)
        )
        if row is None:
            continue
        items.append(
            entry_item(
                "IP_GROUP",
                str(group.id),
                group.group_name or f"IP组#{group.id}",
                row.account_no or "",
            )
        )
        if len(items) >= limit:
            break
    return items


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
        stmt = base_sessions(tenant_id)
        if kw:
            stmt = stmt.where(
                or_(LiveSession.account_no.contains(kw), LiveSession.session_code.contains(kw))
            )
        for row in db.scalars(stmt.order_by(LiveSession.id.desc()).limit(lim)).all():
            if not row.account_id:
                continue
            items.append(
                entry_item(
                    "ACCOUNT",
                    str(row.account_id),
                    row.account_no or f"账号#{row.account_id}",
                    f"最近场次 {row.session_code}",
                    row.platform,
                )
            )
        return ok(dedup_entries(items, lim))
    if entryType == "SESSION":
        stmt = base_sessions(tenant_id)
        if kw:
            stmt = stmt.where(
                or_(LiveSession.session_code.contains(kw), LiveSession.topic.contains(kw))
            )
        for row in db.scalars(stmt.order_by(LiveSession.id.desc()).limit(lim)).all():
            items.append(
                entry_item(
                    "SESSION",
                    row.session_code,
                    row.topic or row.session_code,
                    row.account_no or "",
                    row.platform,
                )
            )
        return ok(dedup_entries(items, lim))
    if entryType == "PERSON":
        return ok(search_person_entries(db, tenant_id, kw, lim))
    if entryType == "RESPONSIBLE":
        return ok(search_responsible_entries(db, tenant_id, kw, lim))
    if entryType == "ASSET":
        return ok(search_asset_entries(db, tenant_id, kw, lim))
    if entryType == "IP_GROUP":
        return ok(search_ip_group_entries(db, tenant_id, kw, lim))
    return ok([])


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
    asset_ids: set[int] = set()
    for row in sessions:
        asset_ids.update(parse_asset_ids(row.device_asset_ids or "[]"))
    graph = build_graph_from_sessions(sessions, asset_label_map(asset_ids))
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
