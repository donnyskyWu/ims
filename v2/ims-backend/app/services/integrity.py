"""引用完整性巡检。只写报告表和站内信，不改业务行。"""
from __future__ import annotations

from sqlalchemy import select

from app.core.clock import now_naive
from app.core.enums import DISABLED_STATUSES
from app.db.refs import REGISTRY
from app.db.repository import TABLES
from app.db.session import get_session, set_sql_log, SQL_LOG
from app.domains.system.model import IntegrityIssue, IntegrityScan


def run_scan(tenant_id: int | None = None, tables: list[str] | None = None) -> dict:
    session = get_session()
    started = now_naive()
    scan = IntegrityScan(started_at=started, tenant_filter=tenant_id, issue_count=0)
    session.add(scan)
    session.flush()
    found: list[dict] = []
    set_sql_log(True)
    try:
        for (table, column), spec in list(REGISTRY.items()):
            if spec.external:
                continue
            if tables and table not in tables:
                continue
            model = TABLES.get(table)
            target = TABLES.get(spec.target)
            if model is None or target is None or not hasattr(model, column):
                continue
            stmt = select(model).execution_options(include_deleted=True, skip_tenant=True)
            if tenant_id is not None and hasattr(model, "tenant_id"):
                stmt = stmt.where(model.tenant_id == int(tenant_id))
            SQL_LOG.append(str(stmt.compile(compile_kwargs={"literal_binds": True})))
            for row in session.scalars(stmt):
                value = getattr(row, column)
                if value in (None, 0, ""):
                    continue
                target_stmt = select(target).where(target.id == value).execution_options(include_deleted=True, skip_tenant=True)
                target_row = session.scalar(target_stmt)
                issue = _classify(spec, row, target_row, table, column, value)
                if issue:
                    found.append(issue)
    finally:
        set_sql_log(False)
    day = started.strftime("%Y-%m-%d")
    saved = 0
    for item in found:
        existing = session.scalar(
            select(IntegrityIssue).where(
                IntegrityIssue.issue_type == item["issue_type"],
                IntegrityIssue.table_name == item["table_name"],
                IntegrityIssue.record_id == item["record_id"],
                IntegrityIssue.field == item["field"],
                IntegrityIssue.seen_on == day,
            )
        )
        if existing is None:
            session.add(
                IntegrityIssue(
                    scan_id=scan.id,
                    seen_on=day,
                    last_seen_time=started,
                    status="OPEN",
                    tenant_id=item.get("tenant_id") or tenant_id or 1,
                    **{k: v for k, v in item.items() if k != "tenant_id"},
                )
            )
            saved += 1
        else:
            existing.last_seen_time = started
            existing.scan_id = scan.id
    scan.finished_at = now_naive()
    scan.issue_count = len(found)
    session.flush()
    if found:
        _notify(scan.id, len(found))
    return {"scanId": scan.id, "issueCount": len(found), "issues": found}


def _classify(spec, row, target_row, table, column, value) -> dict | None:
    base = {
        "table_name": table,
        "record_id": int(row.id),
        "field": column,
        "target_table": spec.target,
        "target_id": int(value),
        "tenant_id": getattr(row, "tenant_id", None),
    }
    if spec.on_delete == "CASCADE_SOFT" and getattr(row, "deleted", 0) in (0, None):
        parent = target_row
        if parent is not None and getattr(parent, "deleted", 0) not in (0, None):
            return {**base, "issue_type": "CASCADE_MISSED", "suggestion": "级联删除未完成"}
    if getattr(row, "deleted", 0) not in (0, None):
        return None
    if target_row is None or getattr(target_row, "deleted", 0) not in (0, None):
        return {**base, "issue_type": "ORPHAN", "suggestion": "引用目标不存在"}
    row_tenant = getattr(row, "tenant_id", None)
    target_tenant = getattr(target_row, "tenant_id", None)
    if row_tenant is not None and target_tenant is not None and row_tenant != target_tenant and not getattr(type(target_row), "__platform__", False):
        return {**base, "issue_type": "CROSS_TENANT", "suggestion": "引用跨租户"}
    status = getattr(target_row, "status", None)
    if status in DISABLED_STATUSES:
        return {**base, "issue_type": "DISABLED_REF", "suggestion": "引用已停用"}
    return None


def _notify(scan_id: int, count: int) -> None:
    from app.domains.message.service import send
    from app.domains.todo.service import users_with_perm

    holders = users_with_perm("ims:system:integrity:query")
    for user_id in holders:
        send(user_id, "引用巡检", f"本次巡检发现 {count} 条问题", "INTEGRITY", f"scan:{scan_id}")
