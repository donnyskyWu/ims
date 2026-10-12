"""通用仓储。默认过滤已删除，并套用租户与数据范围。"""
from __future__ import annotations

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError

from app.core.context import get_ctx
from app.core.errors import BizError
from app.core.pagination import Page
from app.db.changes import diff_and_log, write_change
from app.db.refs import REGISTRY, refs_to
from app.db.scope import EMPTY, scope_clause
from app.db.session import get_session
from app.core.enums import DISABLED_STATUSES
from app.core.fault import faults

TABLES: dict[str, type] = {}
LABELS: dict[str, str] = {}


def register_tables(models):
    for model in models:
        TABLES[model.__tablename__] = model
        LABELS[model.__tablename__] = getattr(model, "__entity_label__", model.__tablename__)


def _camel(name: str) -> str:
    parts = name.split("_")
    return parts[0] + "".join(part.capitalize() for part in parts[1:])


class Repository:
    def __init__(self, model):
        self.model = model

    def _query(self, include_deleted=False):
        stmt = select(self.model)
        if include_deleted:
            stmt = stmt.execution_options(include_deleted=True)
        clause = _safe_scope(self.model)
        if clause is EMPTY:
            stmt = stmt.where(self.model.id == -1)
        elif clause is not None:
            stmt = stmt.where(clause)
        return stmt

    def get(self, ident: int, include_deleted: bool = False):
        clause = _safe_scope(self.model)
        if clause is EMPTY and not include_deleted:
            raise BizError(1504)
        stmt = select(self.model).where(self.model.id == ident)
        if include_deleted:
            stmt = stmt.execution_options(include_deleted=True, skip_tenant=False)
        if clause is not None and clause is not EMPTY and not include_deleted:
            stmt = stmt.where(clause)
        row = get_session().scalar(stmt)
        if row is None:
            raise BizError(1504)
        return row

    def page(self, page: Page, *where, order=None):
        session = get_session()
        stmt = self._query()
        for item in where:
            stmt = stmt.where(item)
        total = session.scalar(select(func.count()).select_from(stmt.subquery()))
        if order is not None:
            stmt = stmt.order_by(*order)
        else:
            stmt = stmt.order_by(self.model.id.desc())
        stmt = stmt.offset((page.page_no - 1) * page.page_size).limit(page.page_size)
        rows = list(session.scalars(stmt))
        return rows, int(total or 0)

    def list(self, *where, include_deleted: bool = False):
        stmt = self._query(include_deleted)
        for item in where:
            stmt = stmt.where(item)
        return list(get_session().scalars(stmt))

    def create(self, obj):
        self._ensure_write_scope()
        self._ensure_platform_write()
        validate_refs_on_write(obj)
        assert_dict_values(obj)
        session = get_session()
        session.add(obj)
        self._flush_unique(obj)
        return obj

    def update(self, obj, before: dict | None = None):
        self._ensure_write_scope()
        self._ensure_platform_write()
        if getattr(self.model, "__versioned__", False):
            expected = before.get("version") if before else None
            if expected is not None and obj.version != expected:
                raise BizError(1001, "数据已被他人修改，请刷新后重试")
        validate_refs_on_write(obj)
        assert_dict_values(obj)
        if before:
            diff_and_log(obj, before)
        if getattr(self.model, "__versioned__", False) and before and "version" in before:
            obj.version = int(before["version"]) + 1
        self._flush_unique(obj)
        return obj

    def soft_delete(self, ident: int):
        obj = self.get(ident)
        session = get_session()
        session.scalar(select(self.model).where(self.model.id == obj.id).with_for_update())
        self.apply_delete_rules(obj)
        obj.deleted = obj.id
        session.flush()
        return obj

    def disable(self, ident: int):
        """停用主数据。被引用时与删除一样拒绝。"""
        obj = self.get(ident)
        refs = protect_counts(obj)
        if refs:
            raise BizError(1502, data={"refs": refs})
        if hasattr(obj, "status"):
            obj.status = "DISABLED"
        get_session().flush()
        return obj

    def apply_delete_rules(self, obj):
        faults.raise_if(f"delete:{obj.__tablename__}")
        refs = protect_counts(obj)
        if refs:
            raise BizError(1502, data={"refs": refs})
        cascade_soft(obj)
        set_null_refs(obj)

    def _ensure_write_scope(self):
        clause = _safe_scope(self.model, write=True)
        if clause is EMPTY:
            raise BizError(1008)

    def _ensure_platform_write(self):
        if getattr(self.model, "__platform__", False):
            ctx = get_ctx()
            if ctx is None or ctx.tenant_id != 1:
                raise BizError(1008, "暂无权限")

    def _flush_unique(self, obj):
        try:
            get_session().flush()
        except IntegrityError as exc:
            get_session().rollback()
            text = str(exc.orig) if getattr(exc, "orig", None) else str(exc)
            field = "code"
            for token in ("username", "code", "role_key", "position_code", "dict_value", "dingtalk"):
                if token in text:
                    field = _camel(token if token != "dingtalk" else "dingtalkDeptId")
                    break
            raise BizError(1001, data={"fieldErrors": [{"field": field, "message": "该值已存在"}]}) from exc


def _safe_scope(model, write: bool = False):
    import logging

    try:
        faults.raise_if("scope.calc")
        return scope_clause(model, write=write)
    except BizError:
        raise
    except Exception:
        logging.getLogger("ims.scope").exception("数据范围计算失败")
        raise BizError(1008)


def assert_dict_values(obj):
    from app.domains.system.model import DictData

    session = get_session()
    for column in obj.__table__.columns:
        dict_type = (column.info or {}).get("dict")
        if not dict_type:
            continue
        value = getattr(obj, column.name)
        if value in (None, ""):
            continue
        row = session.scalar(
            select(DictData)
            .where(DictData.dict_type == dict_type, DictData.dict_value.collate("utf8mb4_bin") == str(value))
            .execution_options(skip_tenant=True)
        )
        if row is None or row.status != "ENABLED" or int(row.deleted or 0) != 0:
            raise BizError(1503, data={"field": _camel(column.name)})


def validate_refs_on_write(obj):
    ctx = get_ctx()
    for column in obj.__table__.columns:
        spec = (column.info or {}).get("ref")
        if spec is None or spec.external:
            continue
        value = getattr(obj, column.name)
        if value in (None, 0, ""):
            continue
        _check_one_ref(column.name, spec, value, ctx.tenant_id if ctx else None)


def _check_one_ref(field: str, spec, value, tenant_id: int | None):
    model = TABLES.get(spec.target)
    if model is None:
        return
    session = get_session()
    stmt = (
        select(model)
        .where(model.id == value)
        .execution_options(skip_tenant=True, include_deleted=True, populate_existing=True)
        .with_for_update(read=True)
    )
    row = session.scalar(stmt)
    camel = _camel(field)
    if row is None or getattr(row, "deleted", 0) not in (0, None):
        raise BizError(1500, data={"field": camel})
    row_tenant = getattr(row, "tenant_id", tenant_id)
    if tenant_id is not None and row_tenant != tenant_id and not getattr(model, "__platform__", False):
        raise BizError(1504, data={"field": camel})
    status = getattr(row, "status", None)
    if status in DISABLED_STATUSES and not spec.allow_disabled:
        raise BizError(1501, data={"field": camel})


def protect_counts(obj) -> list[dict]:
    session = get_session()
    grouped: dict[str, int] = {}
    tenant_id = getattr(obj, "tenant_id", None)
    for table, column, spec in refs_to(obj.__tablename__):
        if spec.on_delete != "RESTRICT" or not spec.enforce_delete or spec.external:
            continue
        model = TABLES.get(table)
        if model is None:
            continue
        stmt = select(func.count()).select_from(model).where(getattr(model, column) == obj.id)
        if hasattr(model, "deleted"):
            stmt = stmt.where(model.deleted == 0)
        if hasattr(model, "tenant_id") and tenant_id is not None:
            stmt = stmt.where(model.tenant_id == tenant_id)
        # 锁定引用行，避免与并发插入互相看不见（REPEATABLE READ 快照）。
        stmt = stmt.execution_options(skip_tenant=True).with_for_update()
        count = int(session.scalar(stmt) or 0)
        if count:
            label = LABELS.get(table, spec.entity_label or table)
            grouped[label] = grouped.get(label, 0) + count
    return [{"entity": name, "count": count} for name, count in grouped.items()]


def cascade_soft(obj):
    session = get_session()
    for table, column, spec in refs_to(obj.__tablename__, "CASCADE_SOFT"):
        model = TABLES.get(table)
        if model is None:
            continue
        stmt = select(model).where(getattr(model, column) == obj.id).execution_options(skip_tenant=True)
        if hasattr(model, "deleted"):
            stmt = stmt.where(model.deleted == 0)
        rows = list(session.scalars(stmt))
        for index, row in enumerate(rows):
            faults.raise_if(f"cascade:{table}:{index}")
            if hasattr(row, "deleted"):
                row.deleted = row.id
            else:
                session.delete(row)


def set_null_refs(obj):
    session = get_session()
    for table, column, spec in refs_to(obj.__tablename__, "SET_NULL"):
        model = TABLES.get(table)
        if model is None:
            continue
        stmt = select(model).where(getattr(model, column) == obj.id).execution_options(skip_tenant=True)
        if hasattr(model, "deleted"):
            stmt = stmt.where(model.deleted == 0)
        for row in session.scalars(stmt):
            before = getattr(row, column)
            setattr(row, column, None)
            write_change(table, row.id, column, column, before, None, "SET_NULL_CASCADE")


def bulk_check(rows: list[dict], model) -> list[dict]:
    """批量引用校验，返回错误列表。规则与单行一致。"""
    errors = []
    ctx = get_ctx()
    tenant_id = ctx.tenant_id if ctx else None
    needed: dict[str, set] = {}
    specs = []
    for column in model.__table__.columns:
        spec = (column.info or {}).get("ref")
        if spec is None or spec.external:
            continue
        specs.append((column.name, spec))
        needed.setdefault(spec.target, set())
    for row in rows:
        for name, spec in specs:
            value = row.get(name)
            if value not in (None, 0, ""):
                needed[spec.target].add(value)
    found = {}
    session = get_session()
    for target, ids in needed.items():
        target_model = TABLES.get(target)
        if not target_model or not ids:
            found[target] = {}
            continue
        stmt = (
            select(target_model)
            .where(target_model.id.in_(ids))
            .execution_options(skip_tenant=True, include_deleted=True)
        )
        found[target] = {item.id: item for item in session.scalars(stmt)}
    for index, row in enumerate(rows, start=1):
        for name, spec in specs:
            value = row.get(name)
            if value in (None, 0, ""):
                continue
            item = found.get(spec.target, {}).get(value)
            camel = _camel(name)
            line = row.get("_excel_row", index)
            if item is None or getattr(item, "deleted", 0) not in (0, None):
                errors.append({"row": line, "field": camel, "code": 1500, "message": "关联的数据不存在"})
                continue
            if tenant_id is not None and getattr(item, "tenant_id", tenant_id) != tenant_id and not getattr(TABLES.get(spec.target), "__platform__", False):
                errors.append({"row": line, "field": camel, "code": 1504, "message": "资源不可用"})
                continue
            if getattr(item, "status", None) in DISABLED_STATUSES and not spec.allow_disabled:
                errors.append({"row": line, "field": camel, "code": 1501, "message": "关联的数据已停用"})
    return errors
