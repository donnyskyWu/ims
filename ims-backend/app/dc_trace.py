"""DC-001 穿透查询（#52 账号 · #53 场次下钻 · #88 六入口 · #91 聚合与性能）。"""

from __future__ import annotations

import math
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
from app.live import get_session, role_tags
from app.models import DcTraceLog, FinCost, FinProfit, LiveReport, LiveSession, User, UserDept
from app.ops_db import ops_session
from app.ops_models import IpGroup, Phone, PlatformAccount

router = APIRouter(prefix="/dc/trace", tags=["dc-trace"])

BJ = timezone(timedelta(hours=8))
ENTRY_TYPES = frozenset({"PERSON", "ACCOUNT", "ASSET", "SESSION", "RESPONSIBLE", "IP_GROUP"})
AGGREGATE_BY = frozenset({"PERSON", "ACCOUNT", "TEAM", "IP_GROUP"})
ENTRY_NAMES = {
    "PERSON": "实名人",
    "ACCOUNT": "账号",
    "ASSET": "资产",
    "SESSION": "场次",
    "RESPONSIBLE": "责任人",
    "IP_GROUP": "IP组",
}
WIDE_RANGE_DAYS = 92
TIMEOUT_MS = 3000
TARGET_P95_MS = 3000
PRESSURE_SAMPLE = 10
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


def build_graph_from_sessions(
    sessions: list[LiveSession],
    labels: dict[int, str] | None = None,
    reports: dict[str, LiveReport] | None = None,
    costs: dict[str, FinCost] | None = None,
    profits: dict[str, FinProfit] | None = None,
    *,
    masked: bool = False,
) -> dict:
    nodes: list[dict] = []
    edges: list[dict] = []
    seen: set[str] = set()
    seen_edges: set[tuple[str, str]] = set()
    asset_labels = labels or {}
    report_map = reports or {}
    cost_map = costs or {}
    profit_map = profits or {}

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
        report = report_map.get(row.session_code)
        cost = cost_map.get(row.session_code)
        profit = profit_map.get(row.session_code)
        gmv = money(report.gmv) if report is not None else None
        total_cost = None if masked or cost is None else money(cost.total_cost)
        net = None if masked or profit is None else money(profit.net_profit)
        session_id = add_node("SESSION", row.session_code, row.topic or row.session_code, platform=row.platform)
        cost_id = add_node(
            "COST",
            f"cost:{row.session_code}",
            "成本",
            metrics={"sessionCount": 1, "totalCost": total_cost},
        )
        profit_id = add_node(
            "PROFIT",
            f"profit:{row.session_code}",
            "利润",
            metrics={"sessionCount": 1, "gmv": gmv, "netProfit": net},
        )
        add_edge(person_id, account_id)
        add_edge(account_id, session_id)
        add_edge(session_id, cost_id)
        add_edge(cost_id, profit_id)
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


def safe_asset_labels(asset_ids: set[int]) -> dict[int, str]:
    """Ops 手机台账不可用时仍给出资产桩标签，穿透查询不因外部库中断。"""
    try:
        return asset_label_map(asset_ids)
    except Exception:
        return {asset_id: f"资产#{asset_id}" for asset_id in asset_ids}


def safe_account_groups(tenant_id: int, account_ids: set[int]) -> dict[int, tuple[int, str]]:
    """Ops IP 组不可用时按未关联处理，前端展示空态。"""
    try:
        return account_group_map(tenant_id, account_ids)
    except Exception:
        return {}


def attach_drill_fields(
    rows: list[dict],
    sessions: list[LiveSession],
    *,
    reports: dict[str, LiveReport],
    profits: dict[str, FinProfit],
    names: dict[int, str],
    groups: dict[int, tuple[int, str]],
    labels: dict[int, str],
    masked: bool,
) -> None:
    """在既有明细行上补资产 / 责任人 / IP 组，供再次 POST /dc/trace/query，不新增接口。"""
    by_code = {row.session_code: row for row in sessions}
    for item in rows:
        session = by_code.get(item["sessionCode"])
        if session is None:
            continue
        report = reports.get(session.session_code)
        profit = profits.get(session.session_code)
        item["gmv"] = money(report.gmv) if report is not None else None
        item["netProfit"] = None if masked or profit is None else money(profit.net_profit)
        user_id = int(session.responsible_user_id or 0)
        item["responsibleUserId"] = user_id
        item["responsibleUserName"] = names.get(user_id, "") if user_id else ""
        group_id, group_name = groups.get(int(session.account_id or 0), (0, ""))
        if not group_id:
            group_id, group_name = 0, ""
        item["ipGroupId"] = int(group_id)
        item["ipGroupName"] = group_name
        asset_ids = [int(asset_id) for asset_id in (item.get("assetIds") or [])]
        item["assetLabels"] = [labels.get(asset_id, f"资产#{asset_id}") for asset_id in asset_ids]


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
    asset_ids = parse_asset_ids(session.device_asset_ids or "[]")
    asset_labels = safe_asset_labels(set(asset_ids))
    group_id, group_name = safe_account_groups(tenant_id, {int(session.account_id or 0)}).get(
        int(session.account_id or 0),
        (0, ""),
    )
    ip_group_id = int(group_id or 0)
    ip_group_name = group_name if ip_group_id else ""
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
        "assetIds": asset_ids,
        "assetLabels": [asset_labels.get(asset_id, f"资产#{asset_id}") for asset_id in asset_ids],
        "ipGroupId": ip_group_id,
        "ipGroupName": ip_group_name,
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


def amounts_masked(db: Session, actor: User, request: Request) -> bool:
    """R7（本人）与 R9 的成本/利润金额返回 null。R1–R4 保留金额。"""
    tags = role_tags(db, actor)
    if tags & {"r1", "r2", "r3", "r4", "sys:admin"}:
        return False
    if "r9" in tags:
        return True
    scope = getattr(request.state, "scope", None)
    return scope is not None and getattr(scope, "kind", "") == "SELF"


def can_view_perf(db: Session, actor: User) -> bool:
    tags = role_tags(db, actor)
    return bool(tags & {"r1", "r9", "sys:admin"})


def parse_range_param(raw: str | None) -> tuple[list[str] | None, str | None]:
    text = (raw or "").strip()
    if not text:
        return None, None
    parts = [part.strip()[:10] for part in text.split(",") if part.strip()]
    if len(parts) != 2 or parts[0] > parts[1]:
        return None, "dateRange 须为开始日,结束日"
    try:
        datetime.strptime(parts[0], "%Y-%m-%d")
        datetime.strptime(parts[1], "%Y-%m-%d")
    except ValueError:
        return None, "dateRange 须为开始日,结束日"
    return parts, None


def finance_index(
    db: Session, tenant_id: int, codes: list[str]
) -> tuple[dict[str, LiveReport], dict[str, FinCost], dict[str, FinProfit]]:
    unique = [code for code in dict.fromkeys(codes) if code]
    if not unique:
        return {}, {}, {}
    reports = {
        row.session_code: row
        for row in db.scalars(
            select(LiveReport).where(
                LiveReport.deleted == 0,
                LiveReport.tenant_id == tenant_id,
                LiveReport.entry_status == "CONFIRMED",
                LiveReport.session_code.in_(unique),
            )
        ).all()
    }
    costs = {
        row.session_code: row
        for row in db.scalars(
            select(FinCost).where(
                FinCost.deleted == 0,
                FinCost.tenant_id == tenant_id,
                FinCost.session_code.in_(unique),
            )
        ).all()
    }
    profits = {
        row.session_code: row
        for row in db.scalars(
            select(FinProfit).where(
                FinProfit.deleted == 0,
                FinProfit.tenant_id == tenant_id,
                FinProfit.session_code.in_(unique),
            )
        ).all()
    }
    return reports, costs, profits


def add_amount(current: float | None, value: float | None) -> float | None:
    if value is None:
        return current
    if current is None:
        return money(value)
    return money(current + value)


def account_group_map(tenant_id: int, account_ids: set[int]) -> dict[int, tuple[int, str]]:
    ids = [item for item in account_ids if item]
    if not ids:
        return {}
    ops = ops_session()
    try:
        accounts = list(
            ops.scalars(
                select(PlatformAccount).where(
                    PlatformAccount.deleted == 0,
                    PlatformAccount.tenant_id == tenant_id,
                    PlatformAccount.id.in_(ids),
                )
            ).all()
        )
        group_ids = {account.ip_group_id for account in accounts if account.ip_group_id}
        groups = {}
        if group_ids:
            groups = {
                row.id: row
                for row in ops.scalars(select(IpGroup).where(IpGroup.id.in_(group_ids), IpGroup.deleted == 0)).all()
            }
    finally:
        ops.close()
    mapped: dict[int, tuple[int, str]] = {}
    for account in accounts:
        group = groups.get(account.ip_group_id or 0)
        if group is None:
            mapped[account.id] = (0, "未归属IP组")
        else:
            mapped[account.id] = (int(group.id), group.group_name or f"IP组#{group.id}")
    return mapped


def team_of_users(db: Session, tenant_id: int, user_ids: set[int]) -> dict[int, tuple[str, str]]:
    ids = [item for item in user_ids if item]
    found: dict[int, tuple[str, str]] = {}
    if ids:
        rows = db.execute(
            select(UserDept.user_id, UserDept.dept_id).where(
                UserDept.user_id.in_(ids),
                UserDept.tenant_id == tenant_id,
            )
        ).all()
        by_user: dict[int, list[int]] = {}
        for user_id, dept_id in rows:
            by_user.setdefault(int(user_id), []).append(int(dept_id))
        for user_id, dept_ids in by_user.items():
            dept_id = sorted(dept_ids)[0]
            found[user_id] = (str(dept_id), f"团队#{dept_id}")
    for user_id in ids:
        found.setdefault(int(user_id), ("0", "未归属团队"))
    return found


def ip_group_label(tenant_id: int, group_id: int) -> str:
    if not group_id:
        return ""
    ops = ops_session()
    try:
        group = ops.get(IpGroup, group_id)
    finally:
        ops.close()
    if group is None or group.deleted or (group.tenant_id or 0) != tenant_id:
        return ""
    return (group.group_name or "").strip() or f"IP组#{group_id}"


def describe_entry(
    db: Session,
    tenant_id: int,
    entry_type: str,
    entry_id: str,
    sessions: list[LiveSession],
    labels: dict[int, str] | None = None,
) -> str:
    entry_id = (entry_id or "").strip()
    if sessions:
        row = sessions[0]
        if entry_type == "PERSON" and (row.realname_name or "").strip():
            return row.realname_name.strip()
        if entry_type == "ACCOUNT" and (row.account_no or "").strip():
            return row.account_no.strip()
        if entry_type == "SESSION":
            return (row.topic or row.session_code or entry_id).strip()
        if entry_type == "RESPONSIBLE" and row.responsible_user_id:
            names = user_names(db, {int(row.responsible_user_id)})
            named = names.get(int(row.responsible_user_id))
            if named:
                return named
        if entry_type == "ASSET":
            named = (labels or {}).get(as_int(entry_id))
            if named:
                return named
        if entry_type == "IP_GROUP":
            named = ip_group_label(tenant_id, as_int(entry_id))
            if named:
                return named
    fallback = ENTRY_NAMES.get(entry_type, entry_type or "入口")
    return f"{fallback} {entry_id}".strip()


def record_trace(
    db: Session,
    actor: User,
    entry_type: str,
    entry_id: str,
    entry_label: str,
    result_rows: int,
    cost_ms: float,
) -> None:
    db.add(
        DcTraceLog(
            entry_type=(entry_type or "")[:32],
            entry_id=(entry_id or "")[:64],
            entry_label=(entry_label or "")[:128],
            query_user_id=actor.id,
            result_rows=int(result_rows or 0),
            cost_ms=float(cost_ms or 0),
            tenant_id=tenant_of(actor),
        )
    )


def aggregate_rows(
    db: Session,
    tenant_id: int,
    sessions: list[LiveSession],
    aggregate_by: str,
    *,
    masked: bool,
) -> list[dict]:
    reports, costs, profits = finance_index(db, tenant_id, [row.session_code for row in sessions])
    groups = (
        account_group_map(tenant_id, {int(row.account_id or 0) for row in sessions})
        if aggregate_by == "IP_GROUP"
        else {}
    )
    teams = (
        team_of_users(db, tenant_id, {int(row.responsible_user_id or 0) for row in sessions})
        if aggregate_by == "TEAM"
        else {}
    )
    buckets: dict[str, dict] = {}
    for row in sessions:
        if aggregate_by == "PERSON":
            key = str(row.realname_person_id or 0)
            label = row.realname_name or (f"实名人#{key}" if key != "0" else "未归属实名人")
        elif aggregate_by == "ACCOUNT":
            key = str(row.account_id or 0)
            label = row.account_no or (f"账号#{key}" if key != "0" else "未归属账号")
        elif aggregate_by == "IP_GROUP":
            group_id, label = groups.get(int(row.account_id or 0), (0, "未归属IP组"))
            key = str(group_id)
        else:
            key, label = teams.get(int(row.responsible_user_id or 0), ("0", "未归属团队"))
        bucket = buckets.get(key)
        if bucket is None:
            bucket = {
                "dimensionValue": key,
                "dimensionLabel": label,
                "sessionCount": 0,
                "gmv": None,
                "totalCost": None,
                "netProfit": None,
                "_persons": set(),
            }
            buckets[key] = bucket
        report = reports.get(row.session_code)
        cost = costs.get(row.session_code)
        profit = profits.get(row.session_code)
        bucket["sessionCount"] += 1
        bucket["gmv"] = add_amount(bucket["gmv"], money(report.gmv) if report is not None else None)
        if not masked:
            bucket["totalCost"] = add_amount(
                bucket["totalCost"], money(cost.total_cost) if cost is not None else None
            )
            bucket["netProfit"] = add_amount(
                bucket["netProfit"], money(profit.net_profit) if profit is not None else None
            )
        person_key = str(row.realname_person_id or 0) if row.realname_person_id else (row.realname_name or "")
        if person_key:
            bucket["_persons"].add(person_key)
    rows_out: list[dict] = []
    for bucket in buckets.values():
        persons = bucket.pop("_persons")
        bucket["personCount"] = len(persons)
        rows_out.append(bucket)
    rows_out.sort(key=lambda item: (-item["sessionCount"], item["dimensionValue"]))
    return rows_out


def percentile_ms(values: list[float], percent: float) -> float:
    """最近秩：ceil(p% × n) 的那一条。无样本为 0。"""
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = math.ceil(percent / 100 * len(ordered))
    index = min(len(ordered), max(rank, 1)) - 1
    return round(float(ordered[index]), 1)


def default_perf_parts() -> list[str]:
    today = datetime.now(BJ).date()
    start = today - timedelta(days=6)
    return [start.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")]


def utc_bounds(parts: list[str]) -> tuple[datetime, datetime]:
    start = datetime.strptime(parts[0], "%Y-%m-%d").replace(tzinfo=BJ)
    end = datetime.strptime(parts[1], "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=BJ)
    return (
        start.astimezone(timezone.utc).replace(tzinfo=None),
        end.astimezone(timezone.utc).replace(tzinfo=None),
    )


def bj_stamp(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(BJ)


def pressure_passed(rows: list[DcTraceLog], day: str) -> bool:
    sample = [row for row in rows if bj_stamp(row.created_at).strftime("%Y-%m-%d") == day]
    if len(sample) < PRESSURE_SAMPLE:
        return False
    return percentile_ms([float(row.cost_ms or 0) for row in sample], 95) <= TARGET_P95_MS


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
    request: Request,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    started = time.perf_counter()
    masked = amounts_masked(db, actor, request)
    if body.entryType not in ENTRY_TYPES:
        elapsed = round((time.perf_counter() - started) * 1000, 1)
        record_trace(db, actor, body.entryType, body.entryId, body.entryType or "入口", 0, elapsed)
        return ok({"queryCostMs": elapsed, "dataAsOf": data_as_of(), "nodes": [], "edges": []})
    if range_too_wide(body.dateRange):
        elapsed = round((time.perf_counter() - started) * 1000, 1)
        record_trace(
            db,
            actor,
            body.entryType,
            body.entryId,
            describe_entry(db, tenant_id, body.entryType, body.entryId, []),
            0,
            elapsed,
        )
        return fail(1181, TIMEOUT_MSG, degraded_payload(elapsed))
    sessions = filter_by_date(
        load_entry_sessions(db, tenant_id, body.entryType, body.entryId),
        body.dateRange,
    )
    asset_ids: set[int] = set()
    for row in sessions:
        asset_ids.update(parse_asset_ids(row.device_asset_ids or "[]"))
    labels = asset_label_map(asset_ids)
    reports, costs, profits = finance_index(db, tenant_id, [row.session_code for row in sessions])
    graph = build_graph_from_sessions(sessions, labels, reports, costs, profits, masked=masked)
    page_no, size = page_args(body.pageNo, body.pageSize)
    detail_list = None
    if body.mode == "DETAIL":
        rows, total = detail_from_sessions(sessions, page_no, size)
        attach_drill_fields(
            rows,
            sessions,
            reports=reports,
            profits=profits,
            names=user_names(db, {int(row.responsible_user_id or 0) for row in sessions}),
            groups=safe_account_groups(tenant_id, {int(row.account_id or 0) for row in sessions}),
            labels=labels,
            masked=masked,
        )
        detail_list = {"list": rows, "total": total, "pageNo": page_no, "pageSize": size}
    elapsed = round((time.perf_counter() - started) * 1000, 1)
    label = describe_entry(db, tenant_id, body.entryType, body.entryId, sessions, labels)
    if elapsed > TIMEOUT_MS:
        record_trace(db, actor, body.entryType, body.entryId, label, 0, elapsed)
        return fail(1181, TIMEOUT_MSG, degraded_payload(elapsed))
    record_trace(db, actor, body.entryType, body.entryId, label, len(sessions), elapsed)
    payload = {
        "queryCostMs": elapsed,
        "dataAsOf": data_as_of(),
        **graph,
    }
    if detail_list is not None:
        payload["detailList"] = detail_list
    return ok(payload)


@router.get("/aggregate")
def trace_aggregate(
    request: Request,
    entryType: str = "",
    entryId: str = "",
    aggregateBy: str = "PERSON",
    dateRange: str = "",
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    if entryType not in ENTRY_TYPES:
        return fail(1001, "entryType 无效")
    if aggregateBy not in AGGREGATE_BY:
        return fail(1001, "aggregateBy 仅支持 PERSON、ACCOUNT、TEAM、IP_GROUP")
    parts, error = parse_range_param(dateRange)
    if error:
        return fail(1001, error)
    tenant_id = tenant_of(actor)
    started = time.perf_counter()
    if range_too_wide(parts):
        elapsed = round((time.perf_counter() - started) * 1000, 1)
        record_trace(db, actor, entryType, entryId, describe_entry(db, tenant_id, entryType, entryId, []), 0, elapsed)
        return fail(1181, TIMEOUT_MSG, [])
    sessions = filter_by_date(load_entry_sessions(db, tenant_id, entryType, entryId), parts)
    rows = aggregate_rows(
        db,
        tenant_id,
        sessions,
        aggregateBy,
        masked=amounts_masked(db, actor, request),
    )
    elapsed = round((time.perf_counter() - started) * 1000, 1)
    label = describe_entry(db, tenant_id, entryType, entryId, sessions)
    record_trace(db, actor, entryType, entryId, label, len(rows), elapsed)
    if elapsed > TIMEOUT_MS:
        return fail(1181, TIMEOUT_MSG, [])
    return ok(rows)


@router.get("/perf-metrics")
def trace_perf_metrics(
    dateRange: str = "",
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    if not can_view_perf(db, actor):
        return fail(1008, "无数据权限")
    parts, error = parse_range_param(dateRange)
    if error:
        return fail(1001, error)
    if parts is None:
        parts = default_perf_parts()
    start, end = utc_bounds(parts)
    rows = list(
        db.scalars(
            select(DcTraceLog)
            .where(
                DcTraceLog.tenant_id == tenant_of(actor),
                DcTraceLog.created_at >= start,
                DcTraceLog.created_at <= end,
            )
            .order_by(DcTraceLog.id.asc())
        ).all()
    )
    costs = [float(row.cost_ms or 0) for row in rows]
    slow = [row for row in rows if float(row.cost_ms or 0) > TIMEOUT_MS]
    slow.sort(key=lambda row: (-float(row.cost_ms or 0), -row.id))
    return ok(
        {
            "p95Ms": percentile_ms(costs, 95),
            "p99Ms": percentile_ms(costs, 99),
            "targetP95Ms": TARGET_P95_MS,
            "queryCount": len(rows),
            "slowQueries": [
                {
                    "queryId": f"Q{row.id}",
                    "entryLabel": row.entry_label or "",
                    "costMs": round(float(row.cost_ms or 0), 1),
                    "occurredAt": bj_stamp(row.created_at).strftime("%Y-%m-%dT%H:%M:%S+08:00"),
                }
                for row in slow[:50]
            ],
            "dailyPressureTestPassed": pressure_passed(rows, parts[1]),
        }
    )


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
