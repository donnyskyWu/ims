"""竞品分析 COMP — 竞品作品/账号（S-IMS-CO-01/02 P0）。"""

from __future__ import annotations

import csv
import io
import os

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy import func, select
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

WORK_CONTENT_TYPES = frozenset({"ARTICLE", "SHORT_VIDEO", "VIDEO", "LIVE_CLIP"})
CONTENT_LABELS = {
    "ARTICLE": "图文",
    "SHORT_VIDEO": "短视频",
    "VIDEO": "视频",
    "LIVE_CLIP": "直播切片",
}


def ensure_comp_monitor_stub(ops: Session, tenant_id: int) -> None:
    """开发 / E2E 库没有外部作品时补少量竞品，测试库保持为空以免干扰断言。"""
    if os.environ.get("IMS_DB") == "ims_test":
        return
    work_count = ops.scalar(
        select(func.count())
        .select_from(ExternalWork)
        .where(ExternalWork.deleted == 0, ExternalWork.tenant_id == tenant_id)
    )
    account_count = ops.scalar(
        select(func.count())
        .select_from(ExternalAccount)
        .where(ExternalAccount.deleted == 0, ExternalAccount.tenant_id == tenant_id)
    )
    if not account_count:
        for ident, name, platform, fans in (
            ("stub-dy", "悦跑圈", "DOUYIN", 860_000),
            ("stub-wx", "Keep 公众号", "WECHAT_OFFICIAL", 120_000),
            ("stub-ch", "咕咚视频号", "WECHAT_CHANNELS", 1_320_000),
        ):
            ops.add(
                ExternalAccount(
                    account_identifier=ident,
                    account_name=name,
                    platform_type=platform,
                    ip_theme="跑步健身",
                    industry="体育",
                    follower_count=fans,
                    work_count=1,
                    last_synced_at="2026-10-08 10:00:00",
                    tenant_id=tenant_id,
                )
            )
    if not work_count:
        for work_id, title, ident, name, platform, content_type, plays, likes, completion in (
            ("stub-w1", "晨跑挑战", "stub-dy", "悦跑圈", "DOUYIN", "SHORT_VIDEO", 2_400_000, 90_000, 46.0),
            ("stub-w2", "装备测评", "stub-wx", "Keep 公众号", "WECHAT_OFFICIAL", "ARTICLE", 180_000, 4_200, 12.0),
            ("stub-w3", "跟练回放", "stub-ch", "咕咚视频号", "WECHAT_CHANNELS", "VIDEO", 860_000, 12_000, 31.0),
        ):
            ops.add(
                ExternalWork(
                    platform_work_id=work_id,
                    title=title,
                    account_identifier=ident,
                    account_name=name,
                    platform_type=platform,
                    content_type=content_type,
                    ip_theme="跑步健身",
                    industry="体育",
                    play_count=plays,
                    like_count=likes,
                    completion_rate=completion,
                    publish_time="2026-10-08 09:00:00",
                    tenant_id=tenant_id,
                )
            )
    if not work_count or not account_count:
        ops.flush()


def work_vo(row: ExternalWork, *, segment: str, hit_play: float, low_completion: float) -> dict:
    is_hit, is_low = classify(row, hit_play, low_completion)
    plays = int(row.play_count or 0)
    return {
        "id": str(row.id),
        "title": row.title,
        "accountName": row.account_name,
        "accountIdentifier": row.account_identifier,
        "platformType": row.platform_type,
        "contentType": row.content_type or "",
        "contentTypeLabel": CONTENT_LABELS.get(row.content_type or "", row.content_type or "—"),
        "publishTime": row.publish_time,
        "playCount": plays,
        "likeCount": int(row.like_count or 0),
        "shareCount": 0,
        "completionRate": row.completion_rate,
        "hitIndex": round(plays / hit_play * 100, 1) if hit_play else 0,
        "isHit": is_hit,
        "isLowScore": is_low,
        "segment": segment,
    }


def collect_works(
    request: Request,
    db: Session,
    ops: Session,
    actor: User,
    *,
    segment: str,
    platform_type: str,
    ip_group_id: int | None,
    industry: str,
    content_type: str,
    start_date: str,
    end_date: str,
    account_identifier: str,
) -> tuple[list[dict] | None, object | None]:
    seg = (segment or "").strip().upper()
    if seg not in SEGMENTS:
        return None, fail(1001, "segment 必填且为 ALL/HIT/LOW_SCORE")

    if err := check_enum(db, "dict_platform_type", platform_type or None, False):
        return None, err
    if content_type and content_type not in WORK_CONTENT_TYPES:
        return None, fail(1503, "字典枚举非法")

    tenant_id = tenant_of(actor)
    ensure_comp_monitor_stub(ops, tenant_id)
    if seg == "LOW_SCORE" and not work_threshold_configured(ops, tenant_id):
        return None, fail(1251, "作品阈值未配置")

    load_scope_ip_groups(db, request, actor)
    scoped_groups = scope_ip_groups(request)

    stmt = select(ExternalWork).where(
        ExternalWork.deleted == 0,
        ExternalWork.tenant_id == tenant_id,
    )
    if platform_type:
        stmt = stmt.where(ExternalWork.platform_type == platform_type)
    if ip_group_id:
        stmt = stmt.where(ExternalWork.ip_group_id == ip_group_id)
    if content_type:
        stmt = stmt.where(ExternalWork.content_type == content_type)
    if industry.strip():
        stmt = stmt.where(ExternalWork.industry == industry.strip())
    if start_date:
        stmt = stmt.where(ExternalWork.publish_time >= start_date[:10])
    if end_date:
        stmt = stmt.where(ExternalWork.publish_time <= end_date[:10] + " 23:59:59")
    if account_identifier.strip():
        ident = account_identifier.strip()
        stmt = stmt.where(
            (ExternalWork.account_identifier.contains(ident)) | (ExternalWork.account_name.contains(ident))
        )
    if scoped_groups is not None:
        stmt = stmt.where(ExternalWork.ip_group_id.in_(scoped_groups))

    rows = list(ops.scalars(stmt.order_by(ExternalWork.play_count.desc())).all())
    filtered: list[dict] = []
    for row in rows:
        hit_play, low_completion, _ = work_thresholds(ops, tenant_id, row.platform_type or "")
        is_hit, is_low = classify(row, hit_play, low_completion)
        if seg == "HIT" and not is_hit:
            continue
        if seg == "LOW_SCORE" and not is_low:
            continue
        filtered.append(work_vo(row, segment=seg, hit_play=hit_play, low_completion=low_completion))
    filtered.sort(key=lambda item: int(item["playCount"] or 0), reverse=True)
    for index, item in enumerate(filtered, start=1):
        item["rank"] = index
    return filtered, None


def work_summary(rows: list[dict]) -> dict:
    count = len(rows)
    likes = sum(int(item.get("likeCount") or 0) for item in rows)
    shares = sum(int(item.get("shareCount") or 0) for item in rows)
    return {
        "hitCount": sum(1 for item in rows if item.get("isHit")),
        "totalPlay": sum(int(item.get("playCount") or 0) for item in rows),
        "avgLike": round(likes / count) if count else 0,
        "avgShare": round(shares / count) if count else 0,
        "hitThresholdLabel": "播放量 ≥ 100w",
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
    filtered, err = collect_works(
        request,
        db,
        ops,
        actor,
        segment=segment,
        platform_type=platformType,
        ip_group_id=ipGroupId,
        industry=industry,
        content_type=contentType,
        start_date=startDate,
        end_date=endDate,
        account_identifier=accountIdentifier,
    )
    if err is not None or filtered is None:
        return err
    page_no, size = page_args(pageNo, pageSize)
    start = (page_no - 1) * size
    payload = paged(filtered[start : start + size], len(filtered), page_no, size)
    payload["data"]["summary"] = work_summary(filtered)
    return payload


def csv_response(filename: str, header: list[str], records: list[dict]) -> Response:
    limited = records[:5000]
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(header)
    for row in limited:
        writer.writerow([row.get(key, "") for key in header])
    payload = "\ufeff" + buf.getvalue()
    return Response(
        content=payload.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Export-Rows": str(len(limited)),
        },
    )


@router.get("/work/export")
def work_export(
    request: Request,
    segment: str = "ALL",
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
    filtered, err = collect_works(
        request,
        db,
        ops,
        actor,
        segment=segment,
        platform_type=platformType,
        ip_group_id=ipGroupId,
        industry=industry,
        content_type=contentType,
        start_date=startDate,
        end_date=endDate,
        account_identifier=accountIdentifier,
    )
    if err is not None or filtered is None:
        return err
    return csv_response(
        "comp_works.csv",
        ["rank", "title", "contentType", "platformType", "playCount", "likeCount", "hitIndex"],
        filtered,
    )


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


def collect_accounts(
    request: Request,
    db: Session,
    ops: Session,
    actor: User,
    *,
    segment: str,
    platform_type: str,
    ip_group_id: int | None,
    industry: str,
    start_date: str,
    end_date: str,
    account_name: str,
) -> tuple[list[dict] | None, object | None]:
    seg = (segment or "").strip().upper()
    if seg not in ACCOUNT_SEGMENTS:
        return None, fail(1001, "segment 必填且为 ALL/HIGH_FANS/LOW_FANS")

    if err := check_enum(db, "dict_platform_type", platform_type or None, False):
        return None, err

    tenant_id = tenant_of(actor)
    ensure_comp_monitor_stub(ops, tenant_id)
    if seg == "LOW_FANS" and not fans_threshold_configured(ops, tenant_id):
        return None, fail(1251, "粉丝阈值未配置")

    load_scope_ip_groups(db, request, actor)
    scoped_groups = scope_ip_groups(request)

    stmt = select(ExternalAccount).where(
        ExternalAccount.deleted == 0,
        ExternalAccount.tenant_id == tenant_id,
    )
    if platform_type:
        stmt = stmt.where(ExternalAccount.platform_type == platform_type)
    if ip_group_id:
        stmt = stmt.where(ExternalAccount.ip_group_id == ip_group_id)
    if industry.strip():
        stmt = stmt.where(ExternalAccount.industry == industry.strip())
    if start_date:
        stmt = stmt.where(ExternalAccount.last_synced_at >= start_date[:10])
    if end_date:
        stmt = stmt.where(ExternalAccount.last_synced_at <= end_date[:10] + " 23:59:59")
    if account_name.strip():
        stmt = stmt.where(ExternalAccount.account_name.contains(account_name.strip()))
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
    return filtered, None


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
    filtered, err = collect_accounts(
        request,
        db,
        ops,
        actor,
        segment=segment,
        platform_type=platformType,
        ip_group_id=ipGroupId,
        industry=industry,
        start_date=startDate,
        end_date=endDate,
        account_name=accountName,
    )
    if err is not None or filtered is None:
        return err
    page_no, size = page_args(pageNo, pageSize)
    start = (page_no - 1) * size
    return paged(filtered[start : start + size], len(filtered), page_no, size)


@router.get("/account/export")
def account_export(
    request: Request,
    segment: str = "ALL",
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
    filtered, err = collect_accounts(
        request,
        db,
        ops,
        actor,
        segment=segment,
        platform_type=platformType,
        ip_group_id=ipGroupId,
        industry=industry,
        start_date=startDate,
        end_date=endDate,
        account_name=accountName,
    )
    if err is not None or filtered is None:
        return err
    return csv_response(
        "comp_accounts.csv",
        ["accountName", "platformType", "followerCount", "workCount", "lastSyncedAt"],
        filtered,
    )
