"""BI0 自定义查询 · S-IMS-B0-01/02。只读消费 COLLECT 元数据，禁止页内元数据 CRUD。"""

from __future__ import annotations

import json
import os
import re
import time
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.audit import publish_notify
from app.bi_drill import router as bi_drill_router
from app.core import utcnow
from app.corp import count_of, ops_db, page_args, paged, tenant_of, visible
from app.models import BiCustomQuery, MetadataEntity, MetadataField, User

router = APIRouter(prefix="/bi/query", tags=["bi-query"])
# 静态下钻路径必须先于 /{query_id}，否则 dimension-tree / export 会被当成查询 id。
router.include_router(bi_drill_router)

_IDENT = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_MAX_LIMIT = 100000


def limit_ok(limit: int) -> bool:
    return 1 <= limit <= _MAX_LIMIT


def bi_query_timeout_ms() -> int:
    raw = os.environ.get("IMS_BI_QUERY_TIMEOUT_MS", "8000")
    try:
        return max(0, int(raw))
    except ValueError:
        return 8000


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
    limit: int = 1000
    aggFunc: str = ""
    aggField: str = ""
    groupBy: list[str] = Field(default_factory=list)
    joinTable: str = ""


class QueryPreviewBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    entityCode: str
    config: QueryConfigBody


# 只允许同库、已登记的等值关联。键为 (主表, 关联表) → (主表列, 关联表列)。
_JOIN_EDGES: dict[tuple[str, str], tuple[str, str]] = {
    ("oa_internal_content", "oa_ip_group"): ("ip_group_id", "id"),
    ("oa_ip_group", "oa_internal_content"): ("id", "ip_group_id"),
    ("oa_platform_account", "oa_ip_group"): ("ip_group_id", "id"),
    ("oa_ip_group", "oa_platform_account"): ("id", "ip_group_id"),
    ("oa_platform_account", "oa_realname"): ("realname_id", "id"),
    ("oa_realname", "oa_platform_account"): ("id", "realname_id"),
}

_AGG = frozenset({"", "DETAIL", "SUM", "COUNT"})

# 自定义查询目录。不写入 PLATFORM_ACCOUNT，避免和「元数据维护」新建实体用例抢编码。
_QUERY_CATALOG: list[dict[str, Any]] = [
    {
        "entity_code": "IP_GROUP",
        "entity_name": "IP组",
        "table_name": "oa_ip_group",
        "fields": [
            ("group_name", "group_name", "组名称", "STRING", "EQ"),
            ("level", "level", "级别", "STRING", "EQ"),
            ("status", "status", "状态", "STRING", "EQ"),
        ],
    },
    {
        "entity_code": "CONTENT_METRIC",
        "entity_name": "内容指标",
        "table_name": "oa_internal_content",
        "fields": [
            ("title", "title", "标题", "STRING", "LIKE"),
            ("play_count", "play_count", "播放量", "NUMBER", "EQ"),
            ("ip_group_id", "ip_group_id", "IP组", "NUMBER", "EQ"),
            ("publish_time", "publish_time", "发布时间", "STRING", "RANGE"),
        ],
    },
    {
        "entity_code": "LIVE_SESSION",
        "entity_name": "直播场次",
        "table_name": "ims_live_session",
        "fields": [
            ("session_code", "session_code", "场次编号", "STRING", "EQ"),
            ("topic", "topic", "主题", "STRING", "LIKE"),
            ("platform", "platform", "平台", "STRING", "EQ"),
            ("account_no", "account_no", "账号", "STRING", "EQ"),
        ],
    },
    {
        "entity_code": "REALNAME",
        "entity_name": "实名",
        "table_name": "oa_realname",
        "fields": [
            ("real_name", "real_name", "姓名", "STRING", "EQ"),
            ("status", "status", "状态", "STRING", "EQ"),
        ],
    },
]


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


class QueryRunBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    pageNo: int = 1
    pageSize: int = 20


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


def ensure_query_catalog(ims: Session, tenant_id: int) -> None:
    """补齐自定义查询可读的已映射实体。已有字段不覆盖。"""
    for item in _QUERY_CATALOG:
        row = ims.scalar(
            select(MetadataEntity).where(
                MetadataEntity.tenant_id == tenant_id,
                MetadataEntity.entity_code == item["entity_code"],
                MetadataEntity.deleted == 0,
            )
        )
        if row is None:
            row = MetadataEntity(
                entity_code=item["entity_code"],
                entity_name=item["entity_name"],
                table_name=item["table_name"],
                status="ENABLED",
                tenant_id=tenant_id,
            )
            ims.add(row)
            ims.flush()
        elif not row.table_name:
            row.table_name = item["table_name"]
        existing = set(
            ims.scalars(
                select(MetadataField.field_code).where(
                    MetadataField.entity_id == row.id,
                    MetadataField.deleted == 0,
                )
            ).all()
        )
        for idx, (code, column, display, data_type, cond) in enumerate(item["fields"]):
            if code in existing:
                continue
            ims.add(
                MetadataField(
                    entity_id=row.id,
                    field_code=code,
                    column_name=column,
                    display_name=display,
                    data_type=data_type,
                    query_condition_type=cond,
                    sort_order=idx,
                    tenant_id=tenant_id,
                )
            )
    ims.flush()


def join_options_for(table_name: str, by_table: dict[str, MetadataEntity]) -> list[dict[str, str]]:
    options: list[dict[str, str]] = []
    for (left, right), _cols in _JOIN_EDGES.items():
        if left != table_name:
            continue
        if read_db_kind(left) != read_db_kind(right):
            continue
        other = by_table.get(right)
        options.append(
            {
                "table": right,
                "entityCode": other.entity_code if other else "",
                "label": other.entity_name if other else right,
            }
        )
    return options


def _lookup_field(code: str, fmap: dict[str, MetadataField], join_map: dict[str, MetadataField]) -> tuple[MetadataField | None, str]:
    if code in fmap:
        return fmap[code], "t" if join_map else ""
    if code in join_map:
        return join_map[code], "j"
    return None, ""


def _col_sql(mf: MetadataField, alias: str) -> str | None:
    col = mf.column_name
    if not _IDENT.match(col):
        return None
    if alias:
        return f"{alias}.`{col}`"
    return f"`{col}`"


def _parse_order(item: str) -> tuple[str, str]:
    raw = item.strip()
    if raw.startswith("-"):
        return raw[1:].strip(), "DESC"
    parts = raw.split()
    if len(parts) == 2 and parts[1].upper() in {"ASC", "DESC"}:
        return parts[0], parts[1].upper()
    return raw, "ASC"


def read_db_kind(table_name: str) -> str:
    """COLLECT P4m 映射 IMS 物理表；legacy oa_* 仍在 ops 库。"""
    name = table_name.strip()
    if name.startswith("oa_"):
        return "ops"
    return "ims"


def build_preview_sql(
    table_name: str,
    fields: list[MetadataField],
    config: QueryConfigBody,
    tenant_id: int,
    join_fields: list[MetadataField] | None = None,
) -> tuple[str | None, dict | None, list[str] | None]:
    if not _IDENT.match(table_name):
        return None, fail(1001, "非法表名"), None
    fmap = field_map(fields)
    join_map = field_map(join_fields or [])
    join_table = (config.joinTable or "").strip()
    edge: tuple[str, str] | None = None
    if join_table:
        if not _IDENT.match(join_table):
            return None, fail(1001, "非法关联表"), None
        edge = _JOIN_EDGES.get((table_name, join_table))
        if edge is None:
            return None, fail(1001, "关联表不在允许范围"), None
        if read_db_kind(table_name) != read_db_kind(join_table):
            return None, fail(1001, "关联表与数据源不在同一库"), None
        if not join_map:
            return None, fail(1001, "关联表未映射"), None
    alias = "t" if edge else ""
    agg = (config.aggFunc or "").strip().upper()
    if agg not in _AGG:
        return None, fail(1001, "计算方式无效"), None
    select_codes = list(config.selectFields or [f.field_code for f in fields])
    if not select_codes and agg in ("", "DETAIL"):
        return None, fail(1001, "展示字段不能为空"), None
    out_aliases: list[str] = []
    col_sql: list[str] = []
    if agg in ("SUM", "COUNT"):
        if not config.aggField.strip():
            return None, fail(1001, "请选择计算字段"), None
        group_codes = list(config.groupBy or select_codes)
        for code in group_codes:
            mf, qual = _lookup_field(code, fmap, join_map if edge else {})
            if mf is None:
                return None, fail(1001, f"未知字段 {code}"), None
            expr = _col_sql(mf, qual or alias)
            if expr is None:
                return None, fail(1001, f"非法列名 {code}"), None
            col_sql.append(f"{expr} AS `{code}`")
            out_aliases.append(code)
        mf, qual = _lookup_field(config.aggField.strip(), fmap, join_map if edge else {})
        if mf is None:
            return None, fail(1001, f"未知计算字段 {config.aggField}"), None
        expr = _col_sql(mf, qual or alias)
        if expr is None:
            return None, fail(1001, "非法计算字段"), None
        agg_alias = config.aggField.strip() if agg == "SUM" else f"{config.aggField.strip()}_count"
        if agg_alias in out_aliases:
            agg_alias = "agg_value"
        fn = "SUM" if agg == "SUM" else "COUNT"
        col_sql.append(f"{fn}({expr}) AS `{agg_alias}`")
        out_aliases.append(agg_alias)
        group_exprs = col_sql[: len(group_codes)]
        group_sql = ", ".join(part.split(" AS ")[0] for part in group_exprs) if group_codes else ""
    else:
        group_sql = ""
        for code in select_codes:
            mf, qual = _lookup_field(code, fmap, join_map if edge else {})
            if mf is None:
                return None, fail(1001, f"未知字段 {code}"), None
            expr = _col_sql(mf, qual or alias)
            if expr is None:
                return None, fail(1001, f"非法列名 {code}"), None
            col_sql.append(f"{expr} AS `{code}`")
            out_aliases.append(code)
    if edge:
        left_col, right_col = edge
        if not _IDENT.match(left_col) or not _IDENT.match(right_col):
            return None, fail(1001, "非法关联列"), None
        sql = (
            f"SELECT {', '.join(col_sql)} FROM `{table_name}` t "
            f"LEFT JOIN `{join_table}` j ON t.`{left_col}` = j.`{right_col}` "
            f"AND j.deleted = 0 AND j.tenant_id = :tenant_id "
            f"WHERE t.deleted = 0"
        )
        qual_where = "t"
    else:
        sql = f"SELECT {', '.join(col_sql)} FROM `{table_name}` WHERE deleted = 0"
        qual_where = ""
    params: dict[str, Any] = {}
    cond_i = 0
    for cond in config.conditions:
        if not (cond.fieldCode or "").strip():
            continue
        mf, qual = _lookup_field(cond.fieldCode, fmap, join_map if edge else {})
        if mf is None:
            return None, fail(1001, f"未知条件字段 {cond.fieldCode}"), None
        expr = _col_sql(mf, qual or alias)
        if expr is None:
            return None, fail(1001, f"非法列名 {cond.fieldCode}"), None
        key = f"p{cond_i}"
        cond_i += 1
        op = (cond.operator or "EQ").upper()
        prefix = f" AND {expr}"
        if op == "LIKE":
            sql += f"{prefix} LIKE :{key}"
            params[key] = f"%{cond.value}%"
        elif op == "RANGE":
            parts = cond.value.split(",", 1)
            if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
                return None, fail(1001, "请同时填写开始和结束日期"), None
            lo, hi = parts[0].strip(), parts[1].strip()
            if _DATE.match(lo) and _DATE.match(hi) and lo > hi:
                return None, fail(1001, "开始日期不能晚于结束日期"), None
            sql += f"{prefix} BETWEEN :{key}_lo AND :{key}_hi"
            params[f"{key}_lo"] = lo
            params[f"{key}_hi"] = hi
        else:
            sql += f"{prefix} = :{key}"
            params[key] = cond.value
    tenant_expr = f"{qual_where}.tenant_id" if qual_where else "tenant_id"
    sql += f" AND {tenant_expr} = :tenant_id"
    params["tenant_id"] = tenant_id
    if agg in ("SUM", "COUNT") and group_sql:
        sql += f" GROUP BY {group_sql}"
    if config.orderBy:
        order_parts = []
        for item in config.orderBy:
            code, direction = _parse_order(item)
            if not code:
                continue
            mf, qual = _lookup_field(code, fmap, join_map if edge else {})
            if mf is None:
                return None, fail(1001, f"非法排序字段 {code}"), None
            expr = _col_sql(mf, qual or alias)
            if expr is None:
                return None, fail(1001, f"非法排序字段 {code}"), None
            order_parts.append(f"{expr} {direction}")
        if order_parts:
            sql += " ORDER BY " + ", ".join(order_parts)
    if not limit_ok(config.limit):
        return None, fail(1001, "行数上限须为 1~100000"), None
    sql += f" LIMIT {int(config.limit)}"
    return sql, params, out_aliases


def load_join_fields(
    ims: Session, actor: User, base_table: str, join_table: str
) -> tuple[list[MetadataField], dict | None]:
    if not join_table.strip():
        return [], None
    if (base_table, join_table) not in _JOIN_EDGES:
        return [], fail(1001, "关联表不在允许范围")
    if read_db_kind(base_table) != read_db_kind(join_table):
        return [], fail(1001, "关联表与数据源不在同一库")
    tenant_id = tenant_of(actor)
    row = ims.scalar(
        select(MetadataEntity).where(
            MetadataEntity.table_name == join_table,
            MetadataEntity.tenant_id == tenant_id,
            MetadataEntity.deleted == 0,
            MetadataEntity.status == "ENABLED",
        )
    )
    if row is None:
        return [], fail(1001, "关联表未映射")
    fields = list(
        ims.scalars(
            select(MetadataField)
            .where(MetadataField.entity_id == row.id, MetadataField.deleted == 0)
            .order_by(MetadataField.sort_order, MetadataField.id)
        ).all()
    )
    return fields, None


def execute_query(
    ims: Session,
    ops: Session,
    entity: MetadataEntity,
    fields: list[MetadataField],
    config: QueryConfigBody,
    tenant_id: int,
    page_no: int = 1,
    page_size: int = 20,
    actor: User | None = None,
) -> tuple[dict | None, dict | None]:
    join_fields: list[MetadataField] = []
    if config.joinTable.strip():
        if actor is None:
            return None, fail(1001, "关联表未映射")
        join_fields, join_err = load_join_fields(ims, actor, entity.table_name, config.joinTable.strip())
        if join_err:
            return None, join_err
    sql, params, columns = build_preview_sql(entity.table_name, fields, config, tenant_id, join_fields)
    if sql is None:
        return None, params
    assert columns is not None
    db = ops if read_db_kind(entity.table_name) == "ops" else ims
    t0 = time.perf_counter()
    rows = db.execute(text(sql), params).mappings().all()
    data_rows = [{c: row.get(c) for c in columns} for row in rows]
    total = len(data_rows)
    empty = total == 0
    pg_no, pg_size = page_args(page_no, page_size)
    start = (pg_no - 1) * pg_size
    page_rows = data_rows[start : start + pg_size]
    cost_ms = int((time.perf_counter() - t0) * 1000)
    if cost_ms >= bi_query_timeout_ms():
        task_id = uuid.uuid4().hex
        folder = Path(os.environ.get("IMS_BI_EXPORT_DIR", "/tmp/ims-bi-exports"))
        folder.mkdir(parents=True, exist_ok=True)
        artifact = {
            "exportTaskId": task_id,
            "entityCode": entity.entity_code,
            "sql": sql,
            "status": "SUBMITTED",
            "message": "导出任务已提交",
        }
        (folder / f"{task_id}.json").write_text(json.dumps(artifact, ensure_ascii=False), encoding="utf-8")
        publish_notify(
            ims,
            event_type="BI_QUERY_EXPORT",
            biz_key=task_id,
            receiver=(actor.username if actor is not None else "system"),
            receiver_user_id=actor.id if actor is not None else 0,
            tenant_id=tenant_id,
            creator=actor.id if actor is not None else 0,
        )
        return None, fail(1262, "导出任务已提交", {"message": "导出任务已提交", "exportTaskId": task_id})
    return {
        "sql": sql,
        "columns": columns,
        "rows": page_rows,
        "total": total,
        "pageNo": pg_no,
        "pageSize": pg_size,
        "queryCostMs": cost_ms,
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


@router.get("/sources")
def query_sources(ims: Session = Depends(db_session), actor: User = Depends(current_user)):
    tenant_id = tenant_of(actor)
    ensure_query_catalog(ims, tenant_id)
    rows = list(
        ims.scalars(
            select(MetadataEntity)
            .where(
                MetadataEntity.deleted == 0,
                MetadataEntity.tenant_id == tenant_id,
                MetadataEntity.status == "ENABLED",
            )
            .order_by(MetadataEntity.id)
        ).all()
    )
    by_table = {r.table_name: r for r in rows if r.table_name}
    data = []
    for row in rows:
        data.append(
            {
                "entityCode": row.entity_code,
                "entityName": row.entity_name,
                "tableName": row.table_name,
                "joins": join_options_for(row.table_name, by_table),
            }
        )
    return ok({"list": data})


class QueryAdhocBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    entityCode: str
    config: QueryConfigBody
    pageNo: int = 1
    pageSize: int = 20


@router.post("/run")
def query_run_adhoc(
    body: QueryAdhocBody,
    ims: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    if not body.entityCode.strip():
        return fail(1001, "请选择数据源")
    if not limit_ok(body.config.limit):
        return fail(1001, "行数上限须为 1~100000")
    entity, fields, err = load_entity_bundle(ims, actor, body.entityCode)
    if err:
        return err
    assert entity is not None
    result, run_err = execute_query(
        ims,
        ops,
        entity,
        fields,
        body.config,
        tenant_of(actor),
        page_no=body.pageNo,
        page_size=body.pageSize,
        actor=actor,
    )
    if run_err:
        return run_err
    return ok(result)


@router.post("/preview")
def query_preview(
    body: QueryPreviewBody,
    ims: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    if not body.entityCode.strip():
        return fail(1001, "请选择数据源")
    if not limit_ok(body.config.limit):
        return fail(1001, "行数上限须为 1~100000")
    entity, fields, err = load_entity_bundle(ims, actor, body.entityCode)
    if err:
        return err
    assert entity is not None
    join_fields: list[MetadataField] = []
    if body.config.joinTable.strip():
        join_fields, join_err = load_join_fields(ims, actor, entity.table_name, body.config.joinTable.strip())
        if join_err:
            return join_err
    sql, params, _columns = build_preview_sql(entity.table_name, fields, body.config, tenant_of(actor), join_fields)
    if sql is None:
        return params
    return ok({"sql": sql, "paramNames": list(params.keys()) if isinstance(params, dict) else []})


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
        return fail(1001, "行数上限须为 1~100000")
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
    body: QueryRunBody | None = None,
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
    run_body = body or QueryRunBody()
    result, run_err = execute_query(
        ims,
        ops,
        entity,
        fields,
        config,
        tenant_of(actor),
        page_no=run_body.pageNo,
        page_size=run_body.pageSize,
        actor=actor,
    )
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
