"""抽样迁移。保留源主键，未知部门进待处理，创建人是数据迁移账号。"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import inspect, select, text

from app.core.context import system_context, use_context
from app.db.session import session_scope
from app.domains.system.model import Dept, MigrationPending, User
from tools.migrate.maps import map_tenant

MIGRATION_USER_ID = 8
DEPT_TABLES = ("system_dept", "sys_dept", "depts", "dept")
USER_TABLES = ("system_users", "system_user", "sys_user", "users", "user")


def _ctx(tenant_id: int):
    ctx = system_context(int(tenant_id))
    ctx.user_id = MIGRATION_USER_ID
    ctx.username = "data-migration"
    ctx.nickname = "数据迁移"
    return ctx


def _pick(row: dict, *names, default=None):
    for name in names:
        if name in row and row[name] is not None:
            return row[name]
    return default


def _as_dt(value):
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value
    if isinstance(value, str) and value.strip():
        return datetime.fromisoformat(value.strip().replace(" ", "T"))
    return None


def _jsonable(row: dict) -> dict:
    out = {}
    for key, value in row.items():
        if isinstance(value, datetime):
            out[key] = value.isoformat(sep=" ")
        elif isinstance(value, bytes):
            out[key] = value.hex()
        elif isinstance(value, Decimal):
            out[key] = str(value)
        else:
            out[key] = value
    return out


def _deleted(value) -> bool:
    if value in (None, 0, "0", False, b"\x00"):
        return False
    if isinstance(value, (bytes, bytearray)) and bytes(value) in (b"\x00", b""):
        return False
    return True


def _user_status(value) -> str:
    text_value = str(value if value is not None else "").strip().upper()
    if text_value in {"1", "FROZEN"}:
        return "FROZEN"
    if text_value in {"2", "RESIGNED"}:
        return "RESIGNED"
    return "ACTIVE"


def _rows(engine, table: str) -> list[dict]:
    with engine.connect() as conn:
        result = conn.execute(text(f"SELECT * FROM `{table}`"))
        return [dict(row) for row in result.mappings()]


def _first_table(names: set[str], candidates: tuple[str, ...]) -> str | None:
    for name in candidates:
        if name in names:
            return name
    return None


def _ensure_pending(session, system: str, object_type: str, source_id, reason: str, payload: dict) -> None:
    ident = str(source_id)
    found = session.scalar(
        select(MigrationPending.id).where(
            MigrationPending.source_system == system,
            MigrationPending.object_type == object_type,
            MigrationPending.source_id == ident,
        )
    )
    if found is not None:
        return
    session.add(
        MigrationPending(
            source_system=system,
            object_type=object_type,
            source_id=ident,
            reason=reason[:255],
            payload=_jsonable(payload),
            creator=MIGRATION_USER_ID,
            updater=MIGRATION_USER_ID,
            tenant_id=1,
        )
    )
    session.flush()


def _upsert_dept(session, row: dict, tenant_id: int) -> None:
    ident = int(row["id"])
    existing = session.scalar(select(Dept).where(Dept.id == ident).execution_options(skip_tenant=True, include_deleted=True))
    if existing is not None:
        return
    parent = int(_pick(row, "parent_id", "parent", default=0) or 0)
    name = str(_pick(row, "name", "dept_name", default="") or "")[:50] or f"部门{ident}"
    created = _as_dt(_pick(row, "create_time"))
    session.add(
        Dept(
            id=ident,
            parent_id=parent,
            path=f"/{parent}/{ident}/" if parent else f"/{ident}/",
            name=name,
            sort=int(_pick(row, "sort", default=0) or 0),
            status="ENABLED",
            source="LOCAL",
            tenant_id=tenant_id,
            creator=MIGRATION_USER_ID,
            updater=MIGRATION_USER_ID,
            create_time=created,
        )
    )
    session.flush()


def _upsert_user(session, row: dict, tenant_id: int, dept_id: int | None) -> None:
    ident = int(row["id"])
    existing = session.scalar(select(User).where(User.id == ident).execution_options(skip_tenant=True, include_deleted=True))
    if existing is not None:
        return
    username = str(_pick(row, "username", "user_name", "account", default="") or "")[:30] or f"u{ident}"
    nickname = str(_pick(row, "nickname", "nick_name", "name", default="") or username)[:50]
    created = _as_dt(_pick(row, "create_time"))
    session.add(
        User(
            id=ident,
            username=username,
            nickname=nickname,
            status=_user_status(_pick(row, "status")),
            main_dept_id=dept_id,
            source="MIGRATION",
            tenant_id=tenant_id,
            creator=MIGRATION_USER_ID,
            updater=MIGRATION_USER_ID,
            create_time=created,
        )
    )
    session.flush()


def _bump(session, table: str) -> None:
    max_id = session.execute(text(f"SELECT COALESCE(MAX(id), 0) FROM `{table}`")).scalar()
    nxt = int(max_id or 0) + 1
    session.execute(text(f"ALTER TABLE `{table}` AUTO_INCREMENT = {nxt}"))


def migrate_sample(source_engine, system: str) -> dict:
    name = str(system or "").strip().lower()
    tables = set(inspect(source_engine).get_table_names())
    read_depts = name in {"opsbiz", "legacy_ims"}
    dept_table = _first_table(tables, DEPT_TABLES) if read_depts else None
    user_table = _first_table(tables, USER_TABLES)
    dept_rows = _rows(source_engine, dept_table) if dept_table else []
    user_rows = _rows(source_engine, user_table) if user_table else []
    stats = {"depts": 0, "users": 0, "pending": 0, "skipped": 0}
    imported_depts: set[int] = set()
    with session_scope(commit=True) as session:
        with use_context(_ctx(1)):
            for row in dept_rows:
                if _deleted(_pick(row, "deleted", default=0)):
                    stats["skipped"] += 1
                    continue
                decision, tenant_id = map_tenant(name, _pick(row, "tenant_id"))
                if decision == "skip":
                    stats["skipped"] += 1
                    continue
                if decision != "ok":
                    _ensure_pending(session, name, "dept", row.get("id"), "租户未映射", row)
                    stats["pending"] += 1
                    continue
                _upsert_dept(session, row, int(tenant_id))
                imported_depts.add(int(row["id"]))
                stats["depts"] += 1
            for row in user_rows:
                if _deleted(_pick(row, "deleted", default=0)):
                    stats["skipped"] += 1
                    continue
                decision, tenant_id = map_tenant(name, _pick(row, "tenant_id"))
                if decision == "skip":
                    stats["skipped"] += 1
                    continue
                if decision != "ok":
                    _ensure_pending(session, name, "user", row.get("id"), "租户未映射", row)
                    stats["pending"] += 1
                    continue
                dept_id = _pick(row, "dept_id", "main_dept_id", "department_id")
                if dept_id not in (None, "", 0, "0"):
                    dept_id = int(dept_id)
                    known = dept_id in imported_depts or session.get(Dept, dept_id) is not None
                    if not known:
                        _ensure_pending(session, name, "user", row.get("id"), f"未知部门 {dept_id}", row)
                        stats["pending"] += 1
                        continue
                else:
                    dept_id = None
                taken = session.scalar(
                    select(User.id).where(User.username == str(_pick(row, "username", "user_name", "account", default="") or f"u{row.get('id')}"))
                )
                if taken is not None and int(taken) != int(row["id"]):
                    _ensure_pending(session, name, "user", row.get("id"), "用户名已存在", row)
                    stats["pending"] += 1
                    continue
                _upsert_user(session, row, int(tenant_id), dept_id)
                stats["users"] += 1
            session.flush()
            _bump(session, "ims_sys_user")
            _bump(session, "ims_sys_dept")
    return stats
