"""作品监测 MON — IP 主题 / 行业聚合（S-IMS-MON P0）。"""

from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.account import load_scope_ip_groups, scope_ip_groups
from app.api import current_user, db_session
from app.corp import check_enum, ops_db, page_args, paged, tenant_of
from app.int_analysis import classify, work_thresholds
from app.models import User
from app.ops_models import ExternalAccount, ExternalWork

router = APIRouter(prefix="/monitor", tags=["monitor"])


def _filter_accounts(
    ops: Session,
    tenant_id: int,
    *,
    platform_type: str,
    ip_group_id: int | None,
    keyword: str,
    scoped_groups: list[int] | None,
) -> list[ExternalAccount]:
    stmt = select(ExternalAccount).where(
        ExternalAccount.deleted == 0,
        ExternalAccount.tenant_id == tenant_id,
    )
    if platform_type:
        stmt = stmt.where(ExternalAccount.platform_type == platform_type)
    if ip_group_id:
        stmt = stmt.where(ExternalAccount.ip_group_id == ip_group_id)
    if scoped_groups is not None:
        stmt = stmt.where(ExternalAccount.ip_group_id.in_(scoped_groups))
    rows = list(ops.scalars(stmt).all())
    if keyword.strip():
        key = keyword.strip()
        rows = [row for row in rows if key in (row.ip_theme or "") or key in (row.industry or "")]
    return rows


def _filter_works(
    ops: Session,
    tenant_id: int,
    *,
    platform_type: str,
    ip_group_id: int | None,
    start_date: str,
    end_date: str,
    scoped_groups: list[int] | None,
) -> list[ExternalWork]:
    stmt = select(ExternalWork).where(
        ExternalWork.deleted == 0,
        ExternalWork.tenant_id == tenant_id,
    )
    if platform_type:
        stmt = stmt.where(ExternalWork.platform_type == platform_type)
    if ip_group_id:
        stmt = stmt.where(ExternalWork.ip_group_id == ip_group_id)
    if start_date:
        stmt = stmt.where(ExternalWork.publish_time >= start_date[:10])
    if end_date:
        stmt = stmt.where(ExternalWork.publish_time <= end_date[:10] + " 23:59:59")
    if scoped_groups is not None:
        stmt = stmt.where(ExternalWork.ip_group_id.in_(scoped_groups))
    return list(ops.scalars(stmt).all())


def _aggregate_rows(
    ops: Session,
    tenant_id: int,
    accounts: list[ExternalAccount],
    works: list[ExternalWork],
    *,
    dimension: str,
) -> list[dict]:
    account_keys: dict[str, set[int]] = defaultdict(set)
    for row in accounts:
        key = (row.ip_theme if dimension == "IP_THEME" else row.industry) or "未分类"
        account_keys[key].add(row.id)

    work_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"workCount": 0, "hitCount": 0})
    for row in works:
        key = (row.ip_theme if dimension == "IP_THEME" else row.industry) or "未分类"
        work_stats[key]["workCount"] += 1
        hit_play, low_completion, _ = work_thresholds(ops, tenant_id, row.platform_type or "")
        is_hit, _ = classify(row, hit_play, low_completion)
        if is_hit:
            work_stats[key]["hitCount"] += 1

    keys = sorted(set(account_keys) | set(work_stats))
    rows: list[dict] = []
    for key in keys:
        rows.append(
            {
                "dimensionKey": key,
                "dimensionLabel": key,
                "externalAccountCount": len(account_keys.get(key, set())),
                "workCount": work_stats.get(key, {}).get("workCount", 0),
                "hitCount": work_stats.get(key, {}).get("hitCount", 0),
            }
        )
    rows.sort(key=lambda item: (-item["hitCount"], -item["workCount"], item["dimensionKey"]))
    return rows


def _page_aggregate(
    request: Request,
    db: Session,
    ops: Session,
    actor: User,
    *,
    dimension: str,
    page_no: int,
    page_size: int,
    platform_type: str,
    ip_group_id: int | None,
    keyword: str,
    start_date: str,
    end_date: str,
):
    if err := check_enum(db, "dict_platform_type", platform_type or None, False):
        return err

    tenant_id = tenant_of(actor)
    load_scope_ip_groups(db, request, actor)
    scoped_groups = scope_ip_groups(request)

    accounts = _filter_accounts(
        ops,
        tenant_id,
        platform_type=platform_type,
        ip_group_id=ip_group_id,
        keyword=keyword,
        scoped_groups=scoped_groups,
    )
    works = _filter_works(
        ops,
        tenant_id,
        platform_type=platform_type,
        ip_group_id=ip_group_id,
        start_date=start_date,
        end_date=end_date,
        scoped_groups=scoped_groups,
    )
    if keyword.strip():
        key = keyword.strip()
        works = [
            row
            for row in works
            if key in (row.ip_theme or "") or key in (row.industry or "") or key in (row.title or "")
        ]

    aggregated = _aggregate_rows(ops, tenant_id, accounts, works, dimension=dimension)
    page_no, size = page_args(page_no, page_size)
    start = (page_no - 1) * size
    page_rows = aggregated[start : start + size]
    return paged(page_rows, len(aggregated), page_no, size)


@router.get("/ip-theme/page")
def ip_theme_page(
    request: Request,
    pageNo: int = 1,
    pageSize: int = 10,
    platformType: str = "",
    ipGroupId: int | None = None,
    keyword: str = "",
    startDate: str = "",
    endDate: str = "",
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    return _page_aggregate(
        request,
        db,
        ops,
        actor,
        dimension="IP_THEME",
        page_no=pageNo,
        page_size=pageSize,
        platform_type=platformType,
        ip_group_id=ipGroupId,
        keyword=keyword,
        start_date=startDate,
        end_date=endDate,
    )


@router.get("/industry/page")
def industry_page(
    request: Request,
    pageNo: int = 1,
    pageSize: int = 10,
    platformType: str = "",
    ipGroupId: int | None = None,
    keyword: str = "",
    startDate: str = "",
    endDate: str = "",
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    return _page_aggregate(
        request,
        db,
        ops,
        actor,
        dimension="INDUSTRY",
        page_no=pageNo,
        page_size=pageSize,
        platform_type=platformType,
        ip_group_id=ipGroupId,
        keyword=keyword,
        start_date=startDate,
        end_date=endDate,
    )
