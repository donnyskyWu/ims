from __future__ import annotations

import json
import re
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.account import COLLECT_PLATFORMS
from app.api import current_user, db_session, fail, ok
from app.core import IMS_DB, utcnow
from app.corp import check_enum, count_of, ops_db, page_args, paged, tenant_of, visible
from app.models import DictData, MetadataEntity, MetadataField, User
from app.ops_models import CollectConfig, CollectKeyword, PlatformAccount, ThresholdConfig

router = APIRouter()

_IDENT = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


class ExternalAccountBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    configName: str
    platformType: str
    accountIdentifier: str
    collectEnabled: bool = True
    status: str = "ENABLED"


class ExternalKeywordBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    platformType: str
    keyword: str
    matchType: str = "CONTAINS"
    collectEnabled: bool | None = None
    status: str = "ENABLED"


class ThresholdBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    thresholdCategory: str
    platformType: str = ""
    status: str = "ENABLED"
    metricName: str | None = None
    thresholdType: str | None = None
    compareOperator: str | None = None
    thresholdValue: str | None = None
    notifyMethods: str | None = None
    lowFans: int | None = None
    highFans: int | None = None
    dailyLow: int | None = None
    dailyHigh: int | None = None
    contentType: str | None = None
    hotValue: str | None = None
    lowValue: str | None = None
    judgeMode: str | None = None
    overrideAccountId: int | None = None
    overrideValue: str | None = None


class MetadataCreateBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    entityCode: str
    entityName: str
    tableName: str
    status: str = "ENABLED"


class MetadataUpdateBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    entityName: str | None = None
    status: str | None = None


class MetadataFieldItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    fieldCode: str
    columnName: str
    displayName: str = ""
    dataType: str = "STRING"
    queryConditionType: str = "EQ"
    dictType: str = ""
    sortOrder: int = 0


class MetadataFieldsBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    fields: list[MetadataFieldItem] = Field(default_factory=list)


class ImportAccountRow(BaseModel):
    configName: str
    platformType: str
    accountIdentifier: str
    status: str = "ENABLED"


class ImportAccountBody(BaseModel):
    rows: list[ImportAccountRow] = Field(default_factory=list)


def parse_collect_enabled(raw: str) -> int | None:
    """列表筛选：空表示不限；1/0 对应是否采集。未知值不当作筛选。"""
    text = (raw or "").strip().lower()
    if text in {"1", "true", "yes"}:
        return 1
    if text in {"0", "false", "no"}:
        return 0
    return None


def external_account_vo(row: CollectConfig) -> dict:
    return {
        "id": str(row.id),
        "configName": row.config_name,
        "platformType": row.platform_type,
        "accountIdentifier": row.account_identifier,
        "collectEnabled": bool(row.collect_enabled),
        "status": row.status,
        "updatedAt": row.updated_at.strftime("%Y-%m-%d %H:%M:%S") if row.updated_at else "",
    }


def keyword_collect_flag(enabled: bool | None, *, default: bool = True) -> int:
    if enabled is None:
        return 1 if default else 0
    return 1 if enabled else 0


def keyword_taken(
    ops: Session,
    tenant_id: int,
    platform_type: str,
    keyword: str,
    exclude_id: int | None = None,
) -> bool:
    stmt = select(CollectKeyword).where(
        CollectKeyword.deleted == 0,
        CollectKeyword.tenant_id == tenant_id,
        CollectKeyword.platform_type == platform_type,
        CollectKeyword.keyword == keyword,
    )
    if exclude_id is not None:
        stmt = stmt.where(CollectKeyword.id != exclude_id)
    return ops.scalar(stmt) is not None


def keyword_vo(row: CollectKeyword) -> dict:
    return {
        "id": str(row.id),
        "platformType": row.platform_type,
        "keyword": row.keyword,
        "matchType": row.match_type,
        "collectEnabled": bool(row.collect_enabled),
        "status": row.status,
        "updatedAt": row.updated_at.strftime("%Y-%m-%d %H:%M:%S") if row.updated_at else "",
    }


def threshold_payload(body: ThresholdBody) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for key in (
        "metricName",
        "thresholdType",
        "compareOperator",
        "thresholdValue",
        "notifyMethods",
        "lowFans",
        "highFans",
        "dailyLow",
        "dailyHigh",
        "contentType",
        "hotValue",
        "lowValue",
        "judgeMode",
        "overrideAccountId",
        "overrideValue",
    ):
        val = getattr(body, key, None)
        if val is not None:
            data[key] = val
    return data


METRIC_LABELS = {
    "play_count": "播放量",
    "like_count": "点赞量",
    "comment_count": "评论数",
    "share_count": "分享量",
    "follower_count": "粉丝数",
    "completion_rate": "完播率",
    "collect_fail_rate": "采集失败率",
    "engagement_rate": "互动率",
}
OPERATOR_LABELS = {
    "GT": ">",
    "GTE": "≥",
    "GE": "≥",
    "LT": "<",
    "LTE": "≤",
    "LE": "≤",
    "EQ": "=",
    "NEQ": "≠",
}
STATUS_FALLBACK = {"ENABLED": "启用", "DISABLED": "停用", "RUNNING": "运行中"}
_OP_PREFIXES = ("GTE", "LTE", "NEQ", "GT", "LT", "EQ", "GE", "LE")


def collect_status_labels(db: Session) -> dict[str, str]:
    """采集状态中文名。优先 dict_collect_status，缺字典时用内置对照。"""
    labels = dict(STATUS_FALLBACK)
    rows = db.scalars(
        select(DictData).where(
            DictData.dict_type == "dict_collect_status",
            DictData.deleted == 0,
            DictData.status == "ENABLED",
        )
    ).all()
    for row in rows:
        if row.dict_label:
            labels[row.dict_value] = row.dict_label
    return labels


def alert_summary(metric: object, operator: object, value: object) -> str:
    """预警阈值摘要。指标、比较符映射为中文和符号，例如 播放量 > 100。"""
    metric_code = str(metric or "").strip()
    op = str(operator or "").strip().upper()
    raw = "" if value is None else str(value).strip()
    if not op and raw:
        upper = raw.upper()
        for word in _OP_PREFIXES:
            if upper == word or upper.startswith(word + " "):
                op = word
                raw = raw[len(word) :].strip()
                break
    metric_label = METRIC_LABELS.get(metric_code, metric_code)
    op_label = OPERATOR_LABELS.get(op, op)
    return " ".join(part for part in (metric_label, op_label, raw) if part)


def threshold_vo(row: ThresholdConfig, status_labels: dict[str, str] | None = None) -> dict:
    try:
        payload = json.loads(row.payload_json or "{}")
    except json.JSONDecodeError:
        payload = {}
    labels = status_labels or STATUS_FALLBACK
    base = {
        "id": str(row.id),
        "thresholdCategory": row.threshold_category,
        "platformType": row.platform_type,
        "status": row.status,
        "statusLabel": labels.get(row.status) or row.status,
    }
    base.update(payload)
    if row.threshold_category == "ALERT":
        base["summary"] = alert_summary(
            payload.get("metricName"),
            payload.get("compareOperator"),
            payload.get("thresholdValue"),
        )
    return base


def metadata_entity_vo(row: MetadataEntity, field_count: int = 0) -> dict:
    return {
        "id": str(row.id),
        "entityCode": row.entity_code,
        "entityName": row.entity_name,
        "tableName": row.table_name,
        "status": row.status,
        "fieldCount": field_count,
    }


def metadata_field_vo(row: MetadataField) -> dict:
    return {
        "id": str(row.id),
        "fieldCode": row.field_code,
        "columnName": row.column_name,
        "displayName": row.display_name,
        "dataType": row.data_type,
        "queryConditionType": row.query_condition_type,
        "dictType": row.dict_type,
        "sortOrder": row.sort_order,
    }


def load_external_config(ops: Session, actor: User, config_id: int) -> CollectConfig | None:
    row = ops.get(CollectConfig, config_id)
    if not visible(row, actor) or row.scope != "EXTERNAL":
        return None
    return row


def validate_external_account(body: ExternalAccountBody, ims: Session) -> dict | None:
    if not body.configName.strip() or not body.accountIdentifier.strip():
        return fail(1001, "必填项缺失")
    if body.platformType not in COLLECT_PLATFORMS:
        if err := check_enum(ims, "dict_third_platform", body.platformType, True):
            return err
    if err := check_enum(ims, "dict_collect_status", body.status, True):
        return err
    return None


@router.get("/external/account/page")
def external_account_page(
    pageNo: int = 1,
    pageSize: int = 10,
    configName: str = "",
    platformType: str = "",
    status: str = "",
    collectEnabled: str = "",
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    page_no, size = page_args(pageNo, pageSize)
    tenant_id = tenant_of(actor)
    stmt = select(CollectConfig).where(
        CollectConfig.deleted == 0,
        CollectConfig.tenant_id == tenant_id,
        CollectConfig.scope == "EXTERNAL",
    )
    if configName.strip():
        stmt = stmt.where(CollectConfig.config_name.contains(configName.strip()))
    if platformType:
        stmt = stmt.where(CollectConfig.platform_type == platformType)
    if status:
        stmt = stmt.where(CollectConfig.status == status)
    flag = parse_collect_enabled(collectEnabled)
    if flag is not None:
        stmt = stmt.where(CollectConfig.collect_enabled == flag)
    total = count_of(ops, stmt)
    rows = ops.scalars(stmt.order_by(CollectConfig.id.desc()).offset((page_no - 1) * size).limit(size)).all()
    return paged([external_account_vo(row) for row in rows], total, page_no, size)


@router.post("/external/account")
def external_account_create(
    body: ExternalAccountBody,
    ops: Session = Depends(ops_db),
    ims: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    if err := validate_external_account(body, ims):
        return err
    row = CollectConfig(
        config_name=body.configName.strip(),
        platform_type=body.platformType,
        account_identifier=body.accountIdentifier.strip(),
        collect_enabled=1 if body.collectEnabled else 0,
        status=body.status,
        scope="EXTERNAL",
        tenant_id=tenant_of(actor),
    )
    ops.add(row)
    ops.flush()
    return ok(external_account_vo(row))


@router.put("/external/account/{config_id}")
def external_account_update(
    config_id: int,
    body: ExternalAccountBody,
    ops: Session = Depends(ops_db),
    ims: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    row = load_external_config(ops, actor, config_id)
    if row is None:
        return fail(1504, "资源不可用")
    if err := validate_external_account(body, ims):
        return err
    row.config_name = body.configName.strip()
    row.platform_type = body.platformType
    row.account_identifier = body.accountIdentifier.strip()
    row.collect_enabled = 1 if body.collectEnabled else 0
    row.status = body.status
    row.updated_at = utcnow()
    return ok(external_account_vo(row))


@router.delete("/external/account/{config_id}")
def external_account_delete(
    config_id: int,
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    row = load_external_config(ops, actor, config_id)
    if row is None:
        return fail(1504, "资源不可用")
    row.deleted = 1
    row.updated_at = utcnow()
    return ok(None)


@router.post("/external/account/import")
def external_account_import(
    body: ImportAccountBody,
    ops: Session = Depends(ops_db),
    ims: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    created = 0
    for item in body.rows:
        ext = ExternalAccountBody(
            configName=item.configName,
            platformType=item.platformType,
            accountIdentifier=item.accountIdentifier,
            status=item.status,
        )
        if validate_external_account(ext, ims):
            continue
        ops.add(
            CollectConfig(
                config_name=item.configName.strip(),
                platform_type=item.platformType,
                account_identifier=item.accountIdentifier.strip(),
                scope="EXTERNAL",
                status=item.status,
                tenant_id=tenant_id,
            )
        )
        created += 1
    ops.flush()
    return ok({"imported": created})


@router.get("/external/keyword/page")
def external_keyword_page(
    pageNo: int = 1,
    pageSize: int = 10,
    keyword: str = "",
    platformType: str = "",
    status: str = "",
    collectEnabled: str = "",
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    page_no, size = page_args(pageNo, pageSize)
    tenant_id = tenant_of(actor)
    stmt = select(CollectKeyword).where(CollectKeyword.deleted == 0, CollectKeyword.tenant_id == tenant_id)
    if keyword.strip():
        stmt = stmt.where(CollectKeyword.keyword.contains(keyword.strip()))
    if platformType:
        stmt = stmt.where(CollectKeyword.platform_type == platformType)
    if status:
        stmt = stmt.where(CollectKeyword.status == status)
    flag = parse_collect_enabled(collectEnabled)
    if flag is not None:
        stmt = stmt.where(CollectKeyword.collect_enabled == flag)
    total = count_of(ops, stmt)
    rows = ops.scalars(stmt.order_by(CollectKeyword.id.desc()).offset((page_no - 1) * size).limit(size)).all()
    return paged([keyword_vo(row) for row in rows], total, page_no, size)


@router.post("/external/keyword")
def external_keyword_create(
    body: ExternalKeywordBody,
    ops: Session = Depends(ops_db),
    ims: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    if not body.keyword.strip():
        return fail(1001, "必填项缺失")
    if err := check_enum(ims, "dict_match_type", body.matchType, True):
        return err
    if err := check_enum(ims, "dict_collect_status", body.status, True):
        return err
    if keyword_taken(ops, tenant_of(actor), body.platformType, body.keyword.strip()):
        return fail(1001, "同平台关键词已存在")
    row = CollectKeyword(
        platform_type=body.platformType,
        keyword=body.keyword.strip(),
        match_type=body.matchType,
        collect_enabled=keyword_collect_flag(body.collectEnabled),
        status=body.status,
        tenant_id=tenant_of(actor),
    )
    ops.add(row)
    ops.flush()
    return ok(keyword_vo(row))


@router.put("/external/keyword/{keyword_id}")
def external_keyword_update(
    keyword_id: int,
    body: ExternalKeywordBody,
    ops: Session = Depends(ops_db),
    ims: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    row = ops.get(CollectKeyword, keyword_id)
    if not visible(row, actor):
        return fail(1504, "资源不可用")
    if not body.keyword.strip():
        return fail(1001, "必填项缺失")
    if err := check_enum(ims, "dict_match_type", body.matchType, True):
        return err
    if err := check_enum(ims, "dict_collect_status", body.status, True):
        return err
    if keyword_taken(ops, tenant_of(actor), body.platformType, body.keyword.strip(), exclude_id=row.id):
        return fail(1001, "同平台关键词已存在")
    row.platform_type = body.platformType
    row.keyword = body.keyword.strip()
    row.match_type = body.matchType
    row.status = body.status
    if body.collectEnabled is not None:
        row.collect_enabled = keyword_collect_flag(body.collectEnabled)
    row.updated_at = utcnow()
    return ok(keyword_vo(row))


@router.delete("/external/keyword/{keyword_id}")
def external_keyword_delete(
    keyword_id: int,
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    row = ops.get(CollectKeyword, keyword_id)
    if not visible(row, actor):
        return fail(1504, "资源不可用")
    row.deleted = 1
    row.updated_at = utcnow()
    return ok(None)


@router.get("/threshold/list")
def threshold_list(
    thresholdCategory: str = "",
    platformType: str = "",
    ops: Session = Depends(ops_db),
    ims: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    if not thresholdCategory.strip():
        return fail(1001, "thresholdCategory 必填")
    tenant_id = tenant_of(actor)
    stmt = select(ThresholdConfig).where(
        ThresholdConfig.deleted == 0,
        ThresholdConfig.tenant_id == tenant_id,
        ThresholdConfig.threshold_category == thresholdCategory.strip(),
    )
    if platformType:
        stmt = stmt.where(ThresholdConfig.platform_type == platformType)
    rows = ops.scalars(stmt.order_by(ThresholdConfig.id.desc())).all()
    labels = collect_status_labels(ims)
    return ok({"list": [threshold_vo(row, labels) for row in rows]})


@router.post("/threshold")
def threshold_create(
    body: ThresholdBody,
    ops: Session = Depends(ops_db),
    ims: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    if err := check_enum(ims, "dict_threshold_category", body.thresholdCategory, True):
        return err
    if err := check_enum(ims, "dict_collect_status", body.status, True):
        return err
    if body.thresholdCategory == "OVERRIDE" and body.overrideAccountId:
        acct = ops.get(PlatformAccount, body.overrideAccountId)
        if not visible(acct, actor):
            return fail(1501, "账号不可用")
    row = ThresholdConfig(
        threshold_category=body.thresholdCategory,
        platform_type=body.platformType,
        payload_json=json.dumps(threshold_payload(body), ensure_ascii=False),
        status=body.status,
        tenant_id=tenant_of(actor),
    )
    ops.add(row)
    ops.flush()
    return ok(threshold_vo(row, collect_status_labels(ims)))


@router.put("/threshold/{threshold_id}")
def threshold_update(
    threshold_id: int,
    body: ThresholdBody,
    ops: Session = Depends(ops_db),
    ims: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    row = ops.get(ThresholdConfig, threshold_id)
    if not visible(row, actor):
        return fail(1504, "资源不可用")
    if err := check_enum(ims, "dict_threshold_category", body.thresholdCategory, True):
        return err
    if body.thresholdCategory == "OVERRIDE" and body.overrideAccountId:
        acct = ops.get(PlatformAccount, body.overrideAccountId)
        if not visible(acct, actor):
            return fail(1501, "账号不可用")
    row.threshold_category = body.thresholdCategory
    row.platform_type = body.platformType
    row.payload_json = json.dumps(threshold_payload(body), ensure_ascii=False)
    row.status = body.status
    row.updated_at = utcnow()
    return ok(threshold_vo(row, collect_status_labels(ims)))


@router.delete("/threshold/{threshold_id}")
def threshold_delete(
    threshold_id: int,
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    row = ops.get(ThresholdConfig, threshold_id)
    if not visible(row, actor):
        return fail(1504, "资源不可用")
    row.deleted = 1
    row.updated_at = utcnow()
    return ok(None)


def load_metadata_entity(ims: Session, actor: User, entity_id: int) -> MetadataEntity | None:
    row = ims.get(MetadataEntity, entity_id)
    if not visible(row, actor):
        return None
    return row


def valid_sql_identifier(name: str) -> bool:
    return bool(_IDENT.match(name))


def suggest_entity_code(table_name: str) -> str:
    stem = table_name
    for prefix in ("ims_", "oa_"):
        if stem.startswith(prefix):
            stem = stem[len(prefix) :]
            break
    return stem.upper() if stem else table_name.upper()


def suggest_entity_name(table_name: str, table_comment: str) -> str:
    comment = (table_comment or "").strip()
    if comment:
        return comment
    stem = table_name
    for prefix in ("ims_", "oa_"):
        if stem.startswith(prefix):
            stem = stem[len(prefix) :]
            break
    return stem or table_name


def ims_catalog_schema() -> str:
    """Physical metadata always reads IMS catalog (not ops / not connection default)."""
    name = (IMS_DB or "ims").strip()
    if not valid_sql_identifier(name):
        return "ims"
    return name


def list_ims_physical_tables(ims: Session) -> list[tuple[str, str]]:
    schema = ims_catalog_schema()
    rows = ims.execute(
        text(
            """
            SELECT TABLE_NAME, COALESCE(TABLE_COMMENT, '')
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = :schema
              AND TABLE_TYPE = 'BASE TABLE'
            ORDER BY TABLE_NAME
            """
        ),
        {"schema": schema},
    ).all()
    out: list[tuple[str, str]] = []
    for table_name, comment in rows:
        name = str(table_name)
        if valid_sql_identifier(name):
            out.append((name, str(comment or "")))
    return out


def ims_table_exists(ims: Session, table_name: str) -> bool:
    if not valid_sql_identifier(table_name):
        return False
    count = ims.scalar(
        text(
            """
            SELECT COUNT(*)
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = :schema
              AND TABLE_TYPE = 'BASE TABLE'
              AND TABLE_NAME = :table_name
            """
        ),
        {"schema": ims_catalog_schema(), "table_name": table_name},
    )
    return int(count or 0) > 0


def list_ims_table_columns(ims: Session, table_name: str) -> list[dict[str, Any]]:
    rows = ims.execute(
        text(
            """
            SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, ORDINAL_POSITION
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = :schema
              AND TABLE_NAME = :table_name
            ORDER BY ORDINAL_POSITION
            """
        ),
        {"schema": ims_catalog_schema(), "table_name": table_name},
    ).all()
    cols: list[dict[str, Any]] = []
    for column_name, data_type, nullable, ordinal in rows:
        cols.append(
            {
                "columnName": str(column_name),
                "dataType": str(data_type),
                "nullable": str(nullable) == "YES",
                "sortOrder": int(ordinal) - 1,
            }
        )
    return cols


@router.get("/metadata/list")
def metadata_list(
    pageNo: int = 1,
    pageSize: int = 10,
    entityCode: str = "",
    ims: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    page_no, size = page_args(pageNo, pageSize)
    tenant_id = tenant_of(actor)
    stmt = select(MetadataEntity).where(MetadataEntity.deleted == 0, MetadataEntity.tenant_id == tenant_id)
    if entityCode.strip():
        stmt = stmt.where(MetadataEntity.entity_code.contains(entityCode.strip()))
    total = count_of(ims, stmt)
    rows = ims.scalars(stmt.order_by(MetadataEntity.id.desc()).offset((page_no - 1) * size).limit(size)).all()
    out = []
    for row in rows:
        fc = int(
            ims.scalar(
                select(func.count(MetadataField.id)).where(
                    MetadataField.entity_id == row.id,
                    MetadataField.deleted == 0,
                )
            )
            or 0
        )
        out.append(metadata_entity_vo(row, fc))
    return paged(out, total, page_no, size)


@router.get("/metadata/unmapped-tables")
def metadata_unmapped(
    ims: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    mapped = set(
        ims.scalars(
            select(MetadataEntity.table_name).where(
                MetadataEntity.deleted == 0,
                MetadataEntity.tenant_id == tenant_id,
            )
        ).all()
    )
    tables = []
    for table_name, comment in list_ims_physical_tables(ims):
        if table_name in mapped:
            continue
        tables.append(
            {
                "tableName": table_name,
                "tableComment": comment,
                "suggestedEntityCode": suggest_entity_code(table_name),
                "suggestedEntityName": suggest_entity_name(table_name, comment),
            }
        )
    return ok({"list": tables})


@router.get("/metadata/table-columns")
def metadata_table_columns(
    tableName: str = "",
    ims: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    del actor
    if not tableName.strip():
        return fail(1001, "tableName 必填")
    name = tableName.strip()
    if not valid_sql_identifier(name):
        return fail(1001, "非法表名")
    if not ims_table_exists(ims, name):
        return ok({"list": []})
    return ok({"list": list_ims_table_columns(ims, name)})


@router.post("/metadata/create")
def metadata_create(
    body: MetadataCreateBody,
    ims: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    if not body.entityCode.strip() or not body.tableName.strip():
        return fail(1001, "必填项缺失")
    table_name = body.tableName.strip()
    if not valid_sql_identifier(table_name):
        return fail(1001, "非法表名")
    if not ims_table_exists(ims, table_name):
        return fail(1001, "物理表不存在")
    tenant_id = tenant_of(actor)
    dup = ims.scalar(
        select(MetadataEntity.id).where(
            MetadataEntity.tenant_id == tenant_id,
            MetadataEntity.entity_code == body.entityCode.strip(),
            MetadataEntity.deleted == 0,
        )
    )
    if dup:
        return fail(1001, "实体编码已存在")
    row = MetadataEntity(
        entity_code=body.entityCode.strip(),
        entity_name=body.entityName.strip() or body.entityCode.strip(),
        table_name=table_name,
        status=body.status,
        tenant_id=tenant_id,
    )
    ims.add(row)
    ims.flush()
    return ok(metadata_entity_vo(row, 0))


@router.get("/metadata/{entity_id}")
def metadata_get(
    entity_id: int,
    ims: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    row = load_metadata_entity(ims, actor, entity_id)
    if row is None:
        return fail(1504, "资源不可用")
    fields = ims.scalars(
        select(MetadataField)
        .where(MetadataField.entity_id == row.id, MetadataField.deleted == 0)
        .order_by(MetadataField.sort_order, MetadataField.id)
    ).all()
    data = metadata_entity_vo(row, len(fields))
    data["fields"] = [metadata_field_vo(f) for f in fields]
    return ok(data)


@router.put("/metadata/{entity_id}")
def metadata_update(
    entity_id: int,
    body: MetadataUpdateBody,
    ims: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    row = load_metadata_entity(ims, actor, entity_id)
    if row is None:
        return fail(1504, "资源不可用")
    if body.entityName is not None:
        row.entity_name = body.entityName.strip()
    if body.status is not None:
        row.status = body.status
    row.updated_at = utcnow()
    return ok(metadata_entity_vo(row))


@router.put("/metadata/{entity_id}/fields")
def metadata_save_fields(
    entity_id: int,
    body: MetadataFieldsBody,
    ims: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    row = load_metadata_entity(ims, actor, entity_id)
    if row is None:
        return fail(1504, "资源不可用")
    existing = ims.scalars(select(MetadataField).where(MetadataField.entity_id == row.id)).all()
    for old in existing:
        ims.delete(old)
    ims.flush()
    tenant_id = tenant_of(actor)
    for item in body.fields:
        ims.add(
            MetadataField(
                entity_id=row.id,
                field_code=item.fieldCode.strip(),
                column_name=item.columnName.strip(),
                display_name=item.displayName.strip() or item.fieldCode.strip(),
                data_type=item.dataType,
                query_condition_type=item.queryConditionType,
                dict_type=item.dictType or "",
                sort_order=item.sortOrder,
                tenant_id=tenant_id,
            )
        )
    row.updated_at = utcnow()
    ims.flush()
    fields = ims.scalars(
        select(MetadataField).where(MetadataField.entity_id == row.id, MetadataField.deleted == 0)
    ).all()
    return ok({"fields": [metadata_field_vo(f) for f in fields]})


@router.get("/metadata/entity/{code}/fields")
def metadata_entity_fields_by_code(
    code: str,
    ims: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    row = ims.scalar(
        select(MetadataEntity).where(
            MetadataEntity.entity_code == code,
            MetadataEntity.tenant_id == tenant_id,
            MetadataEntity.deleted == 0,
            MetadataEntity.status == "ENABLED",
        )
    )
    if row is None:
        return fail(1261, "自定义查询实体未映射")
    fields = ims.scalars(
        select(MetadataField)
        .where(MetadataField.entity_id == row.id, MetadataField.deleted == 0)
        .order_by(MetadataField.sort_order, MetadataField.id)
    ).all()
    return ok(
        {
            "entityCode": row.entity_code,
            "entityName": row.entity_name,
            "tableName": row.table_name,
            "fields": [metadata_field_vo(f) for f in fields],
        }
    )
