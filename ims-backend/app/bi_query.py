"""BI0 自定义查询 · S-IMS-B0-01/02。只读消费 COLLECT 元数据，禁止页内元数据 CRUD。"""

from __future__ import annotations

import json
import re
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.bi_drill import router as bi_drill_router
from app.core import utcnow
from app.corp import count_of, ops_db, page_args, paged, tenant_of, visible
from app.models import BiCustomQuery, MetadataEntity, MetadataField, User

router = APIRouter(prefix="/bi/query", tags=["bi-query"])
# 静态下钻路径必须先于 /{query_id}，否则 dimension-tree / export 会被当成查询 id。
router.include_router(bi_drill_router)

_IDENT = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_MAX_LIMIT = 1000


def limit_ok(limit: int) -> bool:
    return 1 <= limit <= _MAX_LIMIT


class QueryCondition(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    fieldCode: str
    operator: str = "EQ"
    value: str = ""


class QueryConfigBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    selectFields: list[str] = Field(default_factory=list)
    conditions: list[QueryCondition] = Field(default_factory=list)
    orderBy: list[str] = Field(default_factory=list)
    limit: int = 100


class QuerySaveBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    queryName: str
    entityCode: str
    status: str = "DRAFT"
    config: QueryConfigBody


class QueryUpdateBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    queryName: str | None = None
    entityCode: str | None = None
    status: str | None = None
    config: QueryConfigBody | None = None


def query_vo(row: BiCustomQuery, creator_name: str = "") -> dict:
    try:
        config = json.loads(row.config_json or "{}")
    except json.JSONDecodeError:
        config = {}
    return {
        "id": str(row.id),
        "queryName": row.query_name,
        "entityCode": row.entity_code,
        "status": row.status,
        "config": config,
        "creatorName": creator_name,
        "updatedAt": row.updated_at.strftime("%Y-%m-%dT%H:%M:%S+08:00") if row.updated_at else "",
    }


def load_entity_bundle(
    ims: Session, actor: User, entity_code: str
) -> tuple[MetadataEntity | None, list[MetadataField], dict | None]:
    tenant_id = tenant_of(actor)
    row = ims.scalar(
        select(MetadataEntity).where(
            MetadataEntity.entity_code == entity_code.strip(),
            MetadataEntity.tenant_id == tenant_id,
            MetadataEntity.deleted == 0,
            MetadataEntity.status == "ENABLED",
        )
    )
    if row is None:
        return None, [], fail(1261, "自定义查询实体未映射")
    fields = list(
        ims.scalars(
            select(MetadataField)
            .where(MetadataField.entity_id == row.id, MetadataField.deleted == 0)
            .order_by(MetadataField.sort_order, MetadataField.id)
        ).all()
    )
    return row, fields, None


def field_map(fields: list[MetadataField]) -> dict[str, MetadataField]:
    return {f.field_code: f for f in fields}


def build_preview_sql(
    table_name: str,
    fields: list[MetadataField],
    config: QueryConfigBody,
    tenant_id: int,
) -> tuple[str | None, dict | None]:
    if not _IDENT.match(table_name):
        return None, fail(1001, "非法表名")
    fmap = field_map(fields)
    select_codes = config.selectFields or [f.field_code for f in fields]
    if not select_codes:
        return None, fail(1001, "展示字段不能为空")
    cols: list[str] = []
    for code in select_codes:
        mf = fmap.get(code)
        if mf is None:
            return None, fail(1001, f"未知字段 {code}")
        col = mf.column_name
        if not _IDENT.match(col):
            return None, fail(1001, f"非法列名 {col}")
        cols.append(f"`{col}` AS `{code}`")
    sql = f"SELECT {', '.join(cols)} FROM `{table_name}` WHERE deleted = 0"
    params: dict[str, Any] = {}
    for idx, cond in enumerate(config.conditions):
        mf = fmap.get(cond.fieldCode)
        if mf is None:
            return None, fail(1001, f"未知条件字段 {cond.fieldCode}")
        col = mf.column_name
        if not _IDENT.match(col):
            return None, fail(1001, f"非法列名 {col}")
        key = f"p{idx}"
        op = (cond.operator or "EQ").upper()
        if op == "LIKE":
            sql += f" AND `{col}` LIKE :{key}"
            params[key] = f"%{cond.value}%"
        elif op == "RANGE":
            parts = cond.value.split(",", 1)
            if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
                return None, fail(1001, "请同时填写开始和结束日期")
            lo, hi = parts[0].strip(), parts[1].strip()
            if _DATE.match(lo) and _DATE.match(hi) and lo > hi:
                return None, fail(1001, "开始日期不能晚于结束日期")
            sql += f" AND `{col}` BETWEEN :{key}_lo AND :{key}_hi"
            params[f"{key}_lo"] = lo
            params[f"{key}_hi"] = hi
        else:
            sql += f" AND `{col}` = :{key}"
            params[key] = cond.value
    sql += " AND tenant_id = :tenant_id"
    params["tenant_id"] = tenant_id
    if config.orderBy:
        order_parts = []
        for item in config.orderBy:
            code = item.lstrip("-").strip()
            mf = fmap.get(code)
            if mf is None or not _IDENT.match(mf.column_name):
                return None, fail(1001, f"非法排序字段 {code}")
            direction = "DESC" if item.startswith("-") else "ASC"
            order_parts.append(f"`{mf.column_name}` {direction}")
        sql += " ORDER BY " + ", ".join(order_parts)
    if not limit_ok(config.limit):
        return None, fail(1001, "行数上限须为 1~1000")
    sql += f" LIMIT {config.limit}"
    return sql, params


def execute_query(
    ops: Session,
    entity: MetadataEntity,
    fields: list[MetadataField],
    config: QueryConfigBody,
    tenant_id: int,
) -> tuple[dict | None, dict | None]:
    sql, params = build_preview_sql(entity.table_name, fields, config, tenant_id)
    if sql is None:
        return None, params
    rows = ops.execute(text(sql), params).mappings().all()
    columns = config.selectFields or [f.field_code for f in fields]
    data_rows = [{c: row.get(c) for c in columns} for row in rows]
    empty = len(data_rows) == 0
    return {
        "sql": sql,
        "columns": columns,
        "rows": data_rows,
        "total": len(data_rows),
        "empty": empty,
        "emptyReason": "当前条件下暂无数据" if empty else "",
    }, None


@router.get("/page")
def query_page(
    pageNo: int = 1,
    pageSize: int = 10,
    queryName: str = "",
    status: str = "",
    ims: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    page_no, size = page_args(pageNo, pageSize)
    tenant_id = tenant_of(actor)
    stmt = select(BiCustomQuery).where(BiCustomQuery.deleted == 0, BiCustomQuery.tenant_id == tenant_id)
    if queryName.strip():
        stmt = stmt.where(BiCustomQuery.query_name.contains(queryName.strip()))
    if status.strip():
        stmt = stmt.where(BiCustomQuery.status == status.strip())
    total = count_of(ims, stmt)
    rows = ims.scalars(stmt.order_by(BiCustomQuery.updated_at.desc()).offset((page_no - 1) * size).limit(size)).all()
    user_ids = {r.creator_id for r in rows}
    names: dict[int, str] = {}
    if user_ids:
        for u in ims.scalars(select(User).where(User.id.in_(user_ids))).all():
            names[u.id] = u.nickname or u.username
    return paged([query_vo(r, names.get(r.creator_id, "")) for r in rows], total, page_no, size)


@router.get("/{query_id}")
def query_get(
    query_id: int,
    ims: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    row = ims.get(BiCustomQuery, query_id)
    if not visible(row, actor):
        return fail(1504, "资源不可用")
    creator = ims.get(User, row.creator_id)
    name = (creator.nickname or creator.username) if creator else ""
    return ok(query_vo(row, name))


@router.post("")
def query_create(
    body: QuerySaveBody,
    ims: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    if not body.queryName.strip() or not body.entityCode.strip():
        return fail(1001, "必填项缺失")
    if not limit_ok(body.config.limit):
        return fail(1001, "行数上限须为 1~1000")
    entity, fields, err = load_entity_bundle(ims, actor, body.entityCode)
    if err:
        return err
    assert entity is not None
    row = BiCustomQuery(
        query_name=body.queryName.strip(),
        entity_code=body.entityCode.strip(),
        config_json=json.dumps(body.config.model_dump(), ensure_ascii=False),
        status=body.status if body.status in ("DRAFT", "PUBLISHED") else "DRAFT",
        creator_id=actor.id,
        tenant_id=tenant_of(actor),
    )
    ims.add(row)
    ims.flush()
    return ok(query_vo(row, actor.nickname or actor.username))


@router.put("/{query_id}")
def query_update(
    query_id: int,
    body: QueryUpdateBody,
    ims: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    row = ims.get(BiCustomQuery, query_id)
    if not visible(row, actor):
        return fail(1504, "资源不可用")
    if body.entityCode is not None:
        _, _, err = load_entity_bundle(ims, actor, body.entityCode)
        if err:
            return err
        row.entity_code = body.entityCode.strip()
    if body.queryName is not None:
        row.query_name = body.queryName.strip()
    if body.status is not None and body.status in ("DRAFT", "PUBLISHED"):
        row.status = body.status
    if body.config is not None:
        entity, fields, err = load_entity_bundle(ims, actor, row.entity_code)
        if err:
            return err
        assert entity is not None
        row.config_json = json.dumps(body.config.model_dump(), ensure_ascii=False)
    row.updated_at = utcnow()
    creator = ims.get(User, row.creator_id)
    name = (creator.nickname or creator.username) if creator else ""
    return ok(query_vo(row, name))


@router.post("/{query_id}/run")
def query_run(
    query_id: int,
    ims: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    row = ims.get(BiCustomQuery, query_id)
    if not visible(row, actor):
        return fail(1504, "资源不可用")
    entity, fields, err = load_entity_bundle(ims, actor, row.entity_code)
    if err:
        return err
    assert entity is not None
    try:
        config = QueryConfigBody.model_validate(json.loads(row.config_json or "{}"))
    except Exception:
        return fail(1001, "查询配置无效")
    result, run_err = execute_query(ops, entity, fields, config, tenant_of(actor))
    if run_err:
        return run_err
    return ok(result)


@router.put("/{query_id}/publish")
def query_publish(
    query_id: int,
    ims: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    row = ims.get(BiCustomQuery, query_id)
    if not visible(row, actor):
        return fail(1504, "资源不可用")
    entity, _, err = load_entity_bundle(ims, actor, row.entity_code)
    if err:
        return err
    row.status = "PUBLISHED"
    row.updated_at = utcnow()
    creator = ims.get(User, row.creator_id)
    name = (creator.nickname or creator.username) if creator else ""
    return ok(query_vo(row, name))
