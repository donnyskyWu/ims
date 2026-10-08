"""内部分析 INT — 内部作品（S-IMS-IN-01 P0）。"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.account import load_scope_ip_groups, scope_ip_groups
from app.api import current_user, db_session, fail, ok
from app.corp import check_enum, ops_db, page_args, paged, tenant_of
from app.models import User
from app.ops_models import InternalAccount, InternalContent, IpGroup, ThresholdConfig

router = APIRouter(prefix="/int-analysis", tags=["int-analysis"])

SEGMENTS = frozenset({"ALL", "HIT", "LOW_SCORE"})
ACCOUNT_SEGMENTS = frozenset({"ALL", "HIGH_FANS", "LOW_FANS"})
DEFAULT_HIT_PLAY = 1_000_000
DEFAULT_LOW_COMPLETION = 20.0
DEFAULT_HIGH_FANS = 100_000
DEFAULT_LOW_FANS = 1_000


def parse_threshold_value(raw: object, default: float) -> float:
    if raw is None or raw == "":
        return default
    text = str(raw).strip().lower().replace(",", "")
    if text.endswith("w"):
        try:
            return float(text[:-1]) * 10_000
        except ValueError:
            return default
    try:
        return float(text)
    except ValueError:
        return default


def work_threshold_configured(ops: Session, tenant_id: int) -> bool:
    found = ops.scalar(
        select(ThresholdConfig.id).where(
            ThresholdConfig.deleted == 0,
            ThresholdConfig.tenant_id == tenant_id,
            ThresholdConfig.threshold_category == "WORK",
            ThresholdConfig.status == "ENABLED",
        )
    )
    return found is not None


def work_thresholds(
    ops: Session, tenant_id: int, platform_type: str
) -> tuple[float, float, bool]:
    rows = list(
        ops.scalars(
            select(ThresholdConfig).where(
                ThresholdConfig.deleted == 0,
                ThresholdConfig.tenant_id == tenant_id,
                ThresholdConfig.threshold_category == "WORK",
                ThresholdConfig.status == "ENABLED",
            )
        ).all()
    )
    if not rows:
        return DEFAULT_HIT_PLAY, DEFAULT_LOW_COMPLETION, False

    def pick(platform: str) -> ThresholdConfig:
        if platform:
            matched = [row for row in rows if (row.platform_type or "") == platform]
            if matched:
                return matched[0]
        global_rows = [row for row in rows if not (row.platform_type or "")]
        return global_rows[0] if global_rows else rows[0]

    payload = json.loads(pick(platform_type).payload_json or "{}")
    hot = parse_threshold_value(payload.get("hotValue"), DEFAULT_HIT_PLAY)
    low = parse_threshold_value(payload.get("lowValue"), DEFAULT_LOW_COMPLETION)
    return hot, low, True


def classify(row: InternalContent, hit_play: float, low_completion: float) -> tuple[bool, bool]:
    is_hit = (row.play_count or 0) >= hit_play
    is_low = (row.completion_rate or 0.0) < low_completion
    return is_hit, is_low


def fans_threshold_configured(ops: Session, tenant_id: int) -> bool:
    found = ops.scalar(
        select(ThresholdConfig.id).where(
            ThresholdConfig.deleted == 0,
            ThresholdConfig.tenant_id == tenant_id,
            ThresholdConfig.threshold_category == "FANS",
            ThresholdConfig.status == "ENABLED",
        )
    )
    return found is not None


def fans_thresholds(ops: Session, tenant_id: int, platform_type: str) -> tuple[float, float, bool]:
    rows = list(
        ops.scalars(
            select(ThresholdConfig).where(
                ThresholdConfig.deleted == 0,
                ThresholdConfig.tenant_id == tenant_id,
                ThresholdConfig.threshold_category == "FANS",
                ThresholdConfig.status == "ENABLED",
            )
        ).all()
    )
    if not rows:
        return DEFAULT_HIGH_FANS, DEFAULT_LOW_FANS, False

    def pick(platform: str) -> ThresholdConfig:
        if platform:
            matched = [row for row in rows if (row.platform_type or "") == platform]
            if matched:
                return matched[0]
        global_rows = [row for row in rows if not (row.platform_type or "")]
        return global_rows[0] if global_rows else rows[0]

    payload = json.loads(pick(platform_type).payload_json or "{}")
    high = parse_threshold_value(payload.get("highFans"), DEFAULT_HIGH_FANS)
    low = parse_threshold_value(payload.get("lowFans"), DEFAULT_LOW_FANS)
    return high, low, True


def classify_account(row: object, high_fans: float, low_fans: float) -> tuple[bool, bool]:
    followers = getattr(row, "follower_count", 0) or 0
    is_high = followers >= high_fans
    is_low = followers < low_fans
    return is_high, is_low


def work_vo(row: InternalContent, *, segment: str, hit_play: float, low_completion: float) -> dict:
    is_hit, is_low = classify(row, hit_play, low_completion)
    return {
        "id": str(row.id),
        "title": row.title,
        "accountName": row.account_name,
        "platformType": row.platform_type,
        "publishTime": row.publish_time,
        "readCount": row.play_count,
        "playCount": row.play_count,
        "completionRate": row.completion_rate,
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
    contentType: str = "",
    startDate: str = "",
    endDate: str = "",
    keyword: str = "",
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

    stmt = select(InternalContent).where(
        InternalContent.deleted == 0,
        InternalContent.tenant_id == tenant_id,
    )
    if platformType:
        stmt = stmt.where(InternalContent.platform_type == platformType)
    if ipGroupId:
        stmt = stmt.where(InternalContent.ip_group_id == ipGroupId)
    if contentType:
        stmt = stmt.where(InternalContent.content_type == contentType)
    if startDate:
        stmt = stmt.where(InternalContent.publish_time >= startDate[:10])
    if endDate:
        stmt = stmt.where(InternalContent.publish_time <= endDate[:10] + " 23:59:59")
    if keyword.strip():
        stmt = stmt.where(InternalContent.title.contains(keyword.strip()))
    if scoped_groups is not None:
        stmt = stmt.where(InternalContent.ip_group_id.in_(scoped_groups))

    rows = list(ops.scalars(stmt.order_by(InternalContent.publish_time.desc())).all())
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


def account_vo(
    row: InternalAccount,
    *,
    segment: str,
    high_fans: float,
    low_fans: float,
    ip_group_name: str = "",
) -> dict:
    is_high, is_low = classify_account(row, high_fans, low_fans)
    return {
        "id": str(row.id),
        "accountName": row.account_name,
        "platformType": row.platform_type,
        "ipGroupName": ip_group_name,
        "followerCount": row.follower_count,
        "contentCount": row.content_count,
        "lastSyncedAt": row.last_synced_at,
        "tagHighFans": is_high,
        "tagLowFans": is_low,
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
    platform: str = "",
    ipGroupId: int | None = None,
    keyword: str = "",
    accountStatus: str = "",
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    seg = (segment or "").strip().upper()
    if seg not in ACCOUNT_SEGMENTS:
        return fail(1001, "segment 必填且为 ALL/HIGH_FANS/LOW_FANS")

    plat = (platformType or platform or "").strip()
    if err := check_enum(db, "dict_platform_type", plat or None, False):
        return err
    if err := check_enum(db, "dict_account_status", accountStatus or None, False):
        return err

    tenant_id = tenant_of(actor)
    if seg == "LOW_FANS" and not fans_threshold_configured(ops, tenant_id):
        return fail(1251, "粉丝阈值未配置")

    load_scope_ip_groups(db, request, actor)
    scoped_groups = scope_ip_groups(request)

    stmt = select(InternalAccount).where(
        InternalAccount.deleted == 0,
        InternalAccount.tenant_id == tenant_id,
    )
    if plat:
        stmt = stmt.where(InternalAccount.platform_type == plat)
    if ipGroupId:
        stmt = stmt.where(InternalAccount.ip_group_id == ipGroupId)
    if accountStatus.strip():
        stmt = stmt.where(InternalAccount.account_status == accountStatus.strip())
    if keyword.strip():
        kw = keyword.strip()
        stmt = stmt.where(
            (InternalAccount.account_name.contains(kw)) | (InternalAccount.account_identifier.contains(kw))
        )
    if scoped_groups is not None:
        stmt = stmt.where(InternalAccount.ip_group_id.in_(scoped_groups))

    rows = list(ops.scalars(stmt.order_by(InternalAccount.follower_count.desc())).all())
    group_names: dict[int, str] = {}
    group_ids = {row.ip_group_id for row in rows if row.ip_group_id}
    if group_ids:
        for g in ops.scalars(select(IpGroup).where(IpGroup.id.in_(group_ids), IpGroup.deleted == 0)).all():
            group_names[g.id] = g.group_name

    filtered: list[dict] = []
    for row in rows:
        high_fans, low_fans, _ = fans_thresholds(ops, tenant_id, row.platform_type or "")
        is_high, is_low = classify_account(row, high_fans, low_fans)
        if seg == "HIGH_FANS" and not is_high:
            continue
        if seg == "LOW_FANS" and not is_low:
            continue
        ip_name = group_names.get(row.ip_group_id or 0, "")
        filtered.append(
            account_vo(row, segment=seg, high_fans=high_fans, low_fans=low_fans, ip_group_name=ip_name)
        )

    page_no, size = page_args(pageNo, pageSize)
    start = (page_no - 1) * size
    page_rows = filtered[start : start + size]
    return paged(page_rows, len(filtered), page_no, size)
