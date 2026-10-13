"""采集凭证。本批 Collector 探活、导入和扫码走模拟适配。"""
from __future__ import annotations

import os

from sqlalchemy import select

from app.core.clock import now_naive
from app.db.session import get_session
from app.domains.account.model import CollectCredential
from app.domains.account.support import account_row, limit, log_event, save, text_of, visible
from app.domains.system.model import OperateLog

def credential_put(ident: int, body: dict) -> dict:
    row = account_row(ident)
    visible(row)
    found = _row(row.id)
    cookie = text_of(body, "cookie")
    token = text_of(body, "token")
    if cookie:
        found.cookie_enc = cookie
    if token:
        found.token_enc = token
    if "fieldMapping" in body:
        mapping = body.get("fieldMapping")
        if mapping is not None and not isinstance(mapping, dict):
            from app.domains.account.support import one

            one("fieldMapping", "字段映射须为 JSON 对象")
        found.field_mapping = mapping
    if row.platform == "KUAISHOU" and not found.field_mapping and body.get("fieldMapping") is None:
        found.field_mapping = found.field_mapping
    save(found)
    _audit(row.id, "更新采集凭证")
    return _view(row, found)


def credential_delete(ident: int) -> dict:
    row = account_row(ident)
    visible(row)
    found = _row(row.id)
    found.cookie_enc = None
    found.token_enc = None
    found.field_mapping = None
    found.collector_account_id = None
    found.last_probe_ok = None
    row.collect_bind_status = "UNBOUND"
    save(found)
    save(row)
    _audit(row.id, "清空采集凭证")
    return _view(row, found)


def probe(ident: int, body: dict) -> dict:
    return _simulate(ident, body, bind=False)


def import_collector(ident: int, body: dict) -> dict:
    return _simulate(ident, body, bind=True)


def qr_login(ident: int, body: dict) -> dict:
    row = account_row(ident)
    visible(row)
    found = _row(row.id)
    if not found.cookie_enc:
        found.cookie_enc = "simulated-session"
    return _simulate(ident, body, bind=True)


def _simulate(ident: int, body: dict, bind: bool) -> dict:
    row = account_row(ident)
    visible(row)
    found = _row(row.id)
    fail = text_of(body, "result") == "fail" or os.environ.get("IMS_COLLECT_RESULT") == "fail"
    if bind and not (found.cookie_enc or found.token_enc):
        fail = True
        message = "请先保存凭证"
    else:
        message = "连接失败" if fail else "连接成功"
    found.last_probe_at = now_naive()
    found.last_probe_ok = 0 if fail else 1
    found.probe_message = message
    if fail:
        row.collect_bind_status = "FAIL"
        found.collector_account_id = None
    else:
        row.collect_bind_status = "BOUND"
        found.collector_account_id = found.collector_account_id or f"SIM-{row.id}"
    save(found)
    save(row)
    if not fail and row.collect_bind_status == "BOUND":
        log_event(row.id, "COLLECT", "采集绑定", "模拟")
    payload = _view(row, found)
    payload["ok"] = not fail
    payload["message"] = message
    payload["simulated"] = True
    return payload


def _row(account_id: int) -> CollectCredential:
    found = get_session().scalar(select(CollectCredential).where(CollectCredential.account_id == int(account_id)))
    if found is None:
        found = CollectCredential(account_id=int(account_id))
        save(found)
    return found


def _view(account, found: CollectCredential) -> dict:
    return {
        "accountId": account.id,
        "collectBindStatus": account.collect_bind_status or "UNBOUND",
        "hasCredential": bool(found.cookie_enc or found.token_enc),
        "cookieMask": "******" if found.cookie_enc else "",
        "tokenMask": "******" if found.token_enc else "",
        "fieldMapping": found.field_mapping or None,
        "collectorAccountId": found.collector_account_id or "",
        "lastProbeAt": found.last_probe_at.isoformat(sep=" ") if found.last_probe_at else "",
        "lastProbeOk": bool(found.last_probe_ok) if found.last_probe_ok is not None else None,
        "message": found.probe_message or "",
        "hint": "凭证保存后须导入 Collector，否则任务报未绑定",
    }


def _audit(account_id: int, action: str) -> None:
    from app.core.context import get_ctx

    ctx = get_ctx()
    get_session().add(
        OperateLog(
            operator_id=ctx.user_id if ctx else None,
            operator_name=(ctx.nickname or ctx.username) if ctx else "",
            module="采集凭证",
            action=action,
            object_type="平台账号",
            object_id=str(account_id),
            success=1,
            path="",
            method="PUT",
            params_digest="{}",
            tenant_id=ctx.tenant_id if ctx else 1,
        )
    )
    get_session().flush()
