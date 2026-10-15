from __future__ import annotations

import csv
import io
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
from app.models import MetadataEntity, MetadataField, User
from app.crypto import decrypt_text, encrypt_text
from app.ops_models import (
    CollectConfig,
    CollectCredential,
    CollectHttpSource,
    CollectKeyword,
    PlatformAccount,
    ThresholdConfig,
)

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
    ruleName: str | None = None


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
    csvText: str = ""


class BatchDeleteBody(BaseModel):
    ids: list[int] = Field(default_factory=list)


class CredentialBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    platformType: str
    profile: str = "default"
    displayName: str
    secret: str = ""
    expireAt: str = ""
    status: str = "ENABLED"


class HttpSourceBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    sourceName: str
    baseUrl: str
    status: str = "ENABLED"
    remark: str = ""


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
        "ruleName",
    ):
        val = getattr(body, key, None)
        if val is not None:
            data[key] = val
    return data


def threshold_vo(row: ThresholdConfig) -> dict:
    try:
        payload = json.loads(row.payload_json or "{}")
    except json.JSONDecodeError:
        payload = {}
    base = {
        "id": str(row.id),
        "thresholdCategory": row.threshold_category,
        "platformType": row.platform_type,
        "status": row.status,
    }
    base.update(payload)
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


def external_identifier_taken(
    ops: Session,
    tenant_id: int,
    platform_type: str,
    account_identifier: str,
    exclude_id: int | None = None,
) -> bool:
    stmt = select(CollectConfig).where(
        CollectConfig.deleted == 0,
        CollectConfig.tenant_id == tenant_id,
        CollectConfig.scope == "EXTERNAL",
        CollectConfig.platform_type == platform_type,
        CollectConfig.account_identifier == account_identifier,
    )
    if exclude_id is not None:
        stmt = stmt.where(CollectConfig.id != exclude_id)
    return ops.scalar(stmt) is not None


def parse_nonneg_number(raw: object) -> tuple[float | None, str | None]:
    if raw is None or str(raw).strip() == "":
        return None, "必填项缺失"
    text = str(raw).strip().replace(",", "")
    if text.lower().endswith("w"):
        try:
            value = float(text[:-1]) * 10_000
        except ValueError:
            return None, "阈值须为数字（1001）"
    else:
        try:
            value = float(text)
        except ValueError:
            return None, "阈值须为数字（1001）"
    if value < 0:
        return None, "阈值不能为负数（1001）"
    return value, None


def validate_threshold(body: ThresholdBody) -> dict | None:
    if body.thresholdCategory == "ALERT":
        if not (body.metricName or body.ruleName or "").strip():
            return fail(1001, "必填项缺失")
        _value, err = parse_nonneg_number(body.thresholdValue)
        if err:
            return fail(1001, err)
    elif body.thresholdCategory == "FANS":
        if body.lowFans is None or body.highFans is None:
            return fail(1001, "必填项缺失")
        if body.lowFans < 0 or body.highFans < 0:
            return fail(1001, "阈值不能为负数（1001）")
    elif body.thresholdCategory == "WORK":
        for raw in (body.hotValue, body.lowValue):
            _value, err = parse_nonneg_number(raw)
            if err:
                return fail(1001, err)
    elif body.thresholdCategory == "OVERRIDE":
        if not body.overrideAccountId:
            return fail(1001, "必填项缺失")
        _value, err = parse_nonneg_number(body.overrideValue)
        if err:
            return fail(1001, err)
    return None


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
    if external_identifier_taken(ops, tenant_of(actor), body.platformType, body.accountIdentifier.strip()):
        return fail(1001, "同平台账号标识已存在")
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
    if external_identifier_taken(
        ops, tenant_of(actor), body.platformType, body.accountIdentifier.strip(), exclude_id=row.id
    ):
        return fail(1001, "同平台账号标识已存在")
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


def rows_from_csv(text: str) -> list[ImportAccountRow]:
    reader = csv.DictReader(io.StringIO(text.strip()))
    parsed: list[ImportAccountRow] = []
    for item in reader:
        norm = {(key or "").strip().lower(): (value or "").strip() for key, value in item.items() if key}
        platform = norm.get("platform") or norm.get("platformtype") or ""
        nick = norm.get("nick") or norm.get("configname") or ""
        url = norm.get("url") or ""
        ident = norm.get("accountidentifier") or nick or url
        name = nick or ident
        if not platform or not name or not ident:
            continue
        parsed.append(
            ImportAccountRow(
                configName=name,
                platformType=platform,
                accountIdentifier=ident,
                status="DISABLED",
            )
        )
    return parsed


@router.post("/external/account/import")
def external_account_import(
    body: ImportAccountBody,
    ops: Session = Depends(ops_db),
    ims: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    candidate = bool(body.csvText.strip())
    items = rows_from_csv(body.csvText) if candidate else list(body.rows)
    created = 0
    skipped = 0
    for item in items:
        status = "DISABLED" if candidate else (item.status or "ENABLED")
        ext = ExternalAccountBody(
            configName=item.configName,
            platformType=item.platformType,
            accountIdentifier=item.accountIdentifier,
            status=status,
            collectEnabled=not candidate,
        )
        if validate_external_account(ext, ims):
            skipped += 1
            continue
        if external_identifier_taken(ops, tenant_id, item.platformType, item.accountIdentifier.strip()):
            skipped += 1
            continue
        ops.add(
            CollectConfig(
                config_name=item.configName.strip(),
                platform_type=item.platformType,
                account_identifier=item.accountIdentifier.strip(),
                collect_enabled=0 if candidate else 1,
                scope="EXTERNAL",
                status=status,
                tenant_id=tenant_id,
            )
        )
        created += 1
    ops.flush()
    return ok(
        {
            "imported": created,
            "skipped": skipped,
            "pool": "CANDIDATE" if candidate else "ACTIVE",
            "message": "已进入候选池，待启用" if candidate else "导入完成",
        }
    )


@router.post("/external/account/batch-delete")
def external_account_batch_delete(
    body: BatchDeleteBody,
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    deleted = 0
    for config_id in body.ids:
        row = load_external_config(ops, actor, config_id)
        if row is None:
            continue
        row.deleted = 1
        row.updated_at = utcnow()
        deleted += 1
    return ok({"deleted": deleted, "message": "历史采集数据保留，已停止更新"})


def mask_secret(enc: str) -> str:
    if not enc:
        return ""
    try:
        plain = decrypt_text(enc)
    except Exception:
        return "******"
    if not plain:
        return ""
    tail = plain[-2:] if len(plain) >= 2 else ""
    return f"******{tail}"


def credential_vo(row: CollectCredential) -> dict:
    return {
        "id": str(row.id),
        "platformType": row.platform_type,
        "profile": row.profile,
        "displayName": row.display_name,
        "secretMask": mask_secret(row.secret_enc),
        "connStatus": row.conn_status,
        "expireAt": row.expire_at,
        "status": row.status,
        "updatedAt": row.updated_at.strftime("%Y-%m-%d %H:%M:%S") if row.updated_at else "",
    }


@router.get("/external/credential/page")
def credential_page(
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    rows = ops.scalars(
        select(CollectCredential)
        .where(CollectCredential.deleted == 0, CollectCredential.tenant_id == tenant_id)
        .order_by(CollectCredential.id.desc())
    ).all()
    return ok({"list": [credential_vo(row) for row in rows]})


@router.post("/external/credential")
def credential_create(
    body: CredentialBody,
    ops: Session = Depends(ops_db),
    ims: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    if not body.displayName.strip() or not body.platformType.strip() or not body.profile.strip():
        return fail(1001, "必填项缺失")
    if err := check_enum(ims, "dict_collect_status", body.status, True):
        return err
    row = CollectCredential(
        platform_type=body.platformType,
        profile=body.profile.strip(),
        display_name=body.displayName.strip(),
        secret_enc=encrypt_text(body.secret) if body.secret else "",
        conn_status="UNKNOWN",
        expire_at=(body.expireAt or "")[:32],
        status=body.status,
        tenant_id=tenant_of(actor),
    )
    ops.add(row)
    ops.flush()
    return ok(credential_vo(row))


@router.put("/external/credential/{credential_id}")
def credential_update(
    credential_id: int,
    body: CredentialBody,
    ops: Session = Depends(ops_db),
    ims: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    row = ops.get(CollectCredential, credential_id)
    if not visible(row, actor):
        return fail(1504, "资源不可用")
    if not body.displayName.strip():
        return fail(1001, "必填项缺失")
    if err := check_enum(ims, "dict_collect_status", body.status, True):
        return err
    row.platform_type = body.platformType
    row.profile = body.profile.strip() or row.profile
    row.display_name = body.displayName.strip()
    if body.secret:
        row.secret_enc = encrypt_text(body.secret)
    row.expire_at = (body.expireAt or "")[:32]
    row.status = body.status
    row.updated_at = utcnow()
    return ok(credential_vo(row))


@router.post("/external/credential/{credential_id}/probe")
def credential_probe(
    credential_id: int,
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    row = ops.get(CollectCredential, credential_id)
    if not visible(row, actor):
        return fail(1504, "资源不可用")
    plain = ""
    if row.secret_enc:
        try:
            plain = decrypt_text(row.secret_enc)
        except Exception:
            plain = ""
    row.conn_status = "SUCCESS" if plain else "FAILED"
    row.updated_at = utcnow()
    data = credential_vo(row)
    data["message"] = "探活完成" if plain else "凭据为空，探活失败"
    return ok(data)


def source_vo(row: CollectHttpSource) -> dict:
    return {
        "id": str(row.id),
        "sourceName": row.source_name,
        "baseUrl": row.base_url,
        "status": row.status,
        "remark": row.remark,
    }


@router.get("/external/source/page")
def source_page(
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    rows = ops.scalars(
        select(CollectHttpSource)
        .where(CollectHttpSource.deleted == 0, CollectHttpSource.tenant_id == tenant_id)
        .order_by(CollectHttpSource.id.desc())
    ).all()
    return ok({"list": [source_vo(row) for row in rows]})


@router.post("/external/source")
def source_create(
    body: HttpSourceBody,
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    if not body.sourceName.strip() or not body.baseUrl.strip():
        return fail(1001, "必填项缺失")
    if body.baseUrl.strip().lower().startswith("jdbc:"):
        return fail(1243, "禁止 JDBC")
    row = CollectHttpSource(
        source_name=body.sourceName.strip(),
        base_url=body.baseUrl.strip(),
        status=body.status or "ENABLED",
        remark=body.remark or "",
        tenant_id=tenant_of(actor),
    )
    ops.add(row)
    ops.flush()
    return ok(source_vo(row))


@router.put("/external/source/{source_id}")
def source_update(
    source_id: int,
    body: HttpSourceBody,
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    row = ops.get(CollectHttpSource, source_id)
    if not visible(row, actor):
        return fail(1504, "资源不可用")
    if body.baseUrl.strip().lower().startswith("jdbc:"):
        return fail(1243, "禁止 JDBC")
    row.source_name = body.sourceName.strip() or row.source_name
    row.base_url = body.baseUrl.strip() or row.base_url
    row.status = body.status or row.status
    row.remark = body.remark
    row.updated_at = utcnow()
    return ok(source_vo(row))


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
    return ok({"list": [threshold_vo(row) for row in rows]})


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
    if err := validate_threshold(body):
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
    return ok(threshold_vo(row))


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
    if err := validate_threshold(body):
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
    return ok(threshold_vo(row))


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
