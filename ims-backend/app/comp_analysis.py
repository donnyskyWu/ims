"""竞品分析 COMP — 竞品作品/账号（S-IMS-CO-01/02 P0）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.account import load_scope_ip_groups, scope_ip_groups
from app.api import current_user, db_session, fail
from app.corp import check_enum, ops_db, page_args, paged, tenant_of
from app.int_analysis import (
    ACCOUNT_SEGMENTS,
    SEGMENTS,
    classify,
    classify_account,
    fans_threshold_configured,
    fans_thresholds,
    work_threshold_configured,
    work_thresholds,
)
from app.models import User
from app.ops_models import ExternalAccount, ExternalWork

router = APIRouter(prefix="/comp-analysis", tags=["comp-analysis"])


def work_vo(row: ExternalWork, *, segment: str, hit_play: float, low_completion: float) -> dict:
    is_hit, is_low = classify(row, hit_play, low_completion)
    return {
        "id": str(row.id),
        "title": row.title,
        "accountName": row.account_name,
        "platformType": row.platform_type,
        "publishTime": row.publish_time,
        "playCount": row.play_count,
        "likeCount": row.like_count,
        "isHit": is_hit,
        "isLowScore": is_low,
        "segment": segment,
    }


@router.get("/work/page")
def work_page(
    request: Request,
    pageNo: int = 1,
    pageSize: int = 10,
    segment: str = "",
    platformType: str = "",
    ipGroupId: int | None = None,
    industry: str = "",
    contentType: str = "",
    startDate: str = "",
    endDate: str = "",
    accountIdentifier: str = "",
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    seg = (segment or "").strip().upper()
    if seg not in SEGMENTS:
        return fail(1001, "segment 必填且为 ALL/HIT/LOW_SCORE")

    if err := check_enum(db, "dict_platform_type", platformType or None, False):
        return err
    if err := check_enum(db, "dict_content_type", contentType or None, False):
        return err

    tenant_id = tenant_of(actor)
    if seg == "LOW_SCORE" and not work_threshold_configured(ops, tenant_id):
        return fail(1251, "作品阈值未配置")

    load_scope_ip_groups(db, request, actor)
    scoped_groups = scope_ip_groups(request)

    stmt = select(ExternalWork).where(
        ExternalWork.deleted == 0,
        ExternalWork.tenant_id == tenant_id,
    )
    if platformType:
        stmt = stmt.where(ExternalWork.platform_type == platformType)
    if ipGroupId:
        stmt = stmt.where(ExternalWork.ip_group_id == ipGroupId)
    if contentType:
        stmt = stmt.where(ExternalWork.content_type == contentType)
    if industry.strip():
        stmt = stmt.where(ExternalWork.industry == industry.strip())
    if startDate:
        stmt = stmt.where(ExternalWork.publish_time >= startDate[:10])
    if endDate:
        stmt = stmt.where(ExternalWork.publish_time <= endDate[:10] + " 23:59:59")
    if accountIdentifier.strip():
        ident = accountIdentifier.strip()
        stmt = stmt.where(
            (ExternalWork.account_identifier.contains(ident)) | (ExternalWork.account_name.contains(ident))
        )
    if scoped_groups is not None:
        stmt = stmt.where(ExternalWork.ip_group_id.in_(scoped_groups))

    rows = list(ops.scalars(stmt.order_by(ExternalWork.publish_time.desc())).all())
    filtered: list[dict] = []
    for row in rows:
        hit_play, low_completion, _ = work_thresholds(ops, tenant_id, row.platform_type or "")
        is_hit, is_low = classify(row, hit_play, low_completion)
        if seg == "HIT" and not is_hit:
            continue
        if seg == "LOW_SCORE" and not is_low:
            continue
        filtered.append(work_vo(row, segment=seg, hit_play=hit_play, low_completion=low_completion))

    page_no, size = page_args(pageNo, pageSize)
    start = (page_no - 1) * size
    page_rows = filtered[start : start + size]
    return paged(page_rows, len(filtered), page_no, size)


def account_vo(row: ExternalAccount, *, segment: str, high_fans: float, low_fans: float) -> dict:
    is_high, is_low = classify_account(row, high_fans, low_fans)
    return {
        "id": str(row.id),
        "accountName": row.account_name,
        "platformType": row.platform_type,
        "followerCount": row.follower_count,
        "workCount": row.work_count,
        "lastSyncedAt": row.last_synced_at,
        "isHighFans": is_high,
        "isLowFans": is_low,
        "segment": segment,
    }


@router.get("/account/page")
def account_page(
    request: Request,
    pageNo: int = 1,
    pageSize: int = 10,
    segment: str = "",
    platformType: str = "",
    ipGroupId: int | None = None,
    industry: str = "",
    startDate: str = "",
    endDate: str = "",
    accountName: str = "",
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    seg = (segment or "").strip().upper()
    if seg not in ACCOUNT_SEGMENTS:
        return fail(1001, "segment 必填且为 ALL/HIGH_FANS/LOW_FANS")

    if err := check_enum(db, "dict_platform_type", platformType or None, False):
        return err

    tenant_id = tenant_of(actor)
    if seg == "LOW_FANS" and not fans_threshold_configured(ops, tenant_id):
        return fail(1251, "粉丝阈值未配置")

    load_scope_ip_groups(db, request, actor)
    scoped_groups = scope_ip_groups(request)

    stmt = select(ExternalAccount).where(
        ExternalAccount.deleted == 0,
        ExternalAccount.tenant_id == tenant_id,
    )
    if platformType:
        stmt = stmt.where(ExternalAccount.platform_type == platformType)
    if ipGroupId:
        stmt = stmt.where(ExternalAccount.ip_group_id == ipGroupId)
    if industry.strip():
        stmt = stmt.where(ExternalAccount.industry == industry.strip())
    if startDate:
        stmt = stmt.where(ExternalAccount.last_synced_at >= startDate[:10])
    if endDate:
        stmt = stmt.where(ExternalAccount.last_synced_at <= endDate[:10] + " 23:59:59")
    if accountName.strip():
        stmt = stmt.where(ExternalAccount.account_name.contains(accountName.strip()))
    if scoped_groups is not None:
        stmt = stmt.where(ExternalAccount.ip_group_id.in_(scoped_groups))

    rows = list(ops.scalars(stmt.order_by(ExternalAccount.follower_count.desc())).all())
    filtered: list[dict] = []
    for row in rows:
        high_fans, low_fans, _ = fans_thresholds(ops, tenant_id, row.platform_type or "")
        is_high, is_low = classify_account(row, high_fans, low_fans)
        if seg == "HIGH_FANS" and not is_high:
            continue
        if seg == "LOW_FANS" and not is_low:
            continue
        filtered.append(account_vo(row, segment=seg, high_fans=high_fans, low_fans=low_fans))

    page_no, size = page_args(pageNo, pageSize)
    start = (page_no - 1) * size
    page_rows = filtered[start : start + size]
    return paged(page_rows, len(filtered), page_no, size)
