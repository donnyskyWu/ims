"""账号时间线。事件只追加，导出交接凭证为 PDF。"""
from __future__ import annotations

from sqlalchemy import select

from app.core.pagination import page_result
from app.db.session import get_session
from app.domains.account.support import account_row, page_slice, text_of, visible, when
from app.domains.system.model import Timeline
from app.services.exchange import remember_binary

_TYPES = {
    "REGISTER": "登记",
    "APPLY": "领用",
    "TRANSFER": "流转",
    "RETURN": "归还",
    "RECHARGE": "充值",
    "FREEZE": "冻结",
    "UNFREEZE": "解冻",
    "CANCEL": "注销",
    "COLLECT": "采集",
}


def by_account(ident: int) -> dict:
    account = account_row(ident)
    visible(account)
    rows = _rows(account.id)
    return {"accountId": account.id, "accountNo": account.account_no or "", "list": [_view(row) for row in rows]}


def export_pdf(ident: int) -> dict:
    data = by_account(ident)
    lines = [f"{item['eventType']} {item['title']} {item['eventTime']}" for item in data["list"]]
    filename = f"account-{data['accountNo'] or ident}.pdf"
    result = remember_binary(filename, _pdf(lines or ["ACCOUNT"]), "application/pdf", "account_timeline")
    result["filename"] = filename
    result["contentType"] = "application/pdf"
    return result


def events(page_query, params: dict) -> dict:
    stmt = select(Timeline).where(Timeline.biz_type == "ACCOUNT").order_by(Timeline.event_time.desc(), Timeline.id.desc())
    event_type = text_of(params, "eventType")
    if event_type:
        stmt = stmt.where(Timeline.event_type == event_type)
    account_id = text_of(params, "accountId")
    if account_id:
        from app.core.serialize import parse_api_id

        account = account_row(int(parse_api_id(account_id)))
        visible(account)
        stmt = stmt.where(Timeline.biz_id == account.id)
    rows = list(get_session().scalars(stmt))
    keyword = text_of(params, "keyword")
    if keyword:
        rows = [row for row in rows if keyword in (row.title or "") or keyword in (row.event_type or "")]
    chunk, total = page_slice(rows, page_query)
    return page_result([_view(row) for row in chunk], total, page_query)


def _rows(account_id: int) -> list[Timeline]:
    return list(
        get_session().scalars(
            select(Timeline).where(Timeline.biz_type == "ACCOUNT", Timeline.biz_id == int(account_id)).order_by(Timeline.event_time.desc(), Timeline.id.desc())
        )
    )


def _view(row: Timeline) -> dict:
    detail = row.detail if isinstance(row.detail, dict) else {}
    return {
        "id": row.id,
        "accountId": row.biz_id,
        "eventType": row.event_type,
        "eventLabel": _TYPES.get(row.event_type, row.event_type),
        "title": row.title,
        "detail": detail.get("text") or "",
        "ref": detail.get("ref") or "",
        "eventTime": when(row.event_time),
        "operatorId": row.operator_id,
    }


def _pdf(lines: list[str]) -> bytes:
    text = " | ".join(item.encode("ascii", "replace").decode("ascii") for item in lines)[:800]
    text = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = f"BT /F1 11 Tf 48 740 Td ({text}) Tj ET".encode("ascii")
    objects = [
        b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n",
        b"2 0 obj<< /Type /Pages /Count 1 /Kids [3 0 R] >>endobj\n",
        b"3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources<< /Font<< /F1 5 0 R >> >> >>endobj\n",
        b"4 0 obj<< /Length " + str(len(stream)).encode("ascii") + b" >>stream\n" + stream + b"\nendstream\nendobj\n",
        b"5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n",
    ]
    body = b"%PDF-1.4\n" + b"".join(objects)
    return body + b"trailer<< /Root 1 0 R >>\n%%EOF\n"
