"""竞品库 COMP-003 · V3 资产库（与 M7 comp-analysis 监测分离）。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.core import utcnow
from app.corp import check_enum, ops_db, page_args, paged, tenant_of
from app.models import CompAsset, User
from app.ops_models import ExternalAccount, ExternalWork

router = APIRouter(prefix="/comp/asset", tags=["comp-asset"])

BJ = timezone(timedelta(hours=8))
ASSET_STATUSES = frozenset({"APPROVED", "PENDING", "ARCHIVED"})


class AssetBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    compName: str
    platform: str
    compAccountId: str = ""
    followerCount: int = Field(ge=0, default=0)
    works30d: int = Field(ge=0, default=0)
    engagementRate: float = Field(ge=0, default=0.0)


def next_asset_no(db: Session, tenant_id: int) -> str:
    day = datetime.now(BJ).strftime("%Y%m%d")
    prefix = f"CP{day}"
    count = db.scalar(
        select(func.count())
        .select_from(CompAsset)
        .where(
            CompAsset.deleted == 0,
            CompAsset.tenant_id == tenant_id,
            CompAsset.asset_no.like(f"{prefix}%"),
        )
    )
    seq = int(count or 0) + 1
    return f"{prefix}{seq:03d}"


def normalize_name(name: str) -> str:
    return " ".join(name.strip().split())


def works_30d(ops: Session, tenant_id: int, account_identifier: str) -> int:
    if not account_identifier:
        return 0
    cutoff = (datetime.now(BJ) - timedelta(days=30)).strftime("%Y-%m-%d")
    return int(
        ops.scalar(
            select(func.count())
            .select_from(ExternalWork)
            .where(
                ExternalWork.deleted == 0,
                ExternalWork.tenant_id == tenant_id,
                ExternalWork.account_identifier == account_identifier,
                ExternalWork.publish_time >= cutoff,
            )
        )
        or 0
    )


def engagement_rate(ops: Session, tenant_id: int, account_identifier: str) -> float:
    if not account_identifier:
        return 0.0
    row = ops.execute(
        select(
            func.coalesce(func.sum(ExternalWork.like_count), 0),
            func.coalesce(func.sum(ExternalWork.play_count), 0),
        ).where(
            ExternalWork.deleted == 0,
            ExternalWork.tenant_id == tenant_id,
            ExternalWork.account_identifier == account_identifier,
        )
    ).one()
    likes, plays = int(row[0] or 0), int(row[1] or 0)
    if plays <= 0:
        return 0.0
    return round(min(likes / plays * 100, 99.9), 1)


def enrich_metrics(ops: Session, tenant_id: int, asset: CompAsset) -> dict:
    info = dict(asset.base_info or {})
    follower = int(info.get("followerCount") or 0)
    works = int(info.get("works30d") or 0)
    rate = float(info.get("engagementRate") or 0.0)
    featured = bool(info.get("featuredWorksIncluded", True))

    if asset.comp_account_id:
        acc = ops.scalar(
            select(ExternalAccount).where(
                ExternalAccount.deleted == 0,
                ExternalAccount.tenant_id == tenant_id,
                ExternalAccount.account_identifier == asset.comp_account_id,
            )
        )
        if acc is not None:
            follower = int(acc.follower_count or 0)
            works = works_30d(ops, tenant_id, asset.comp_account_id)
            rate = engagement_rate(ops, tenant_id, asset.comp_account_id)
            featured = works > 0 or int(acc.work_count or 0) > 0

    return {
        "followerCount": follower,
        "works30d": works,
        "engagementRate": rate,
        "featuredWorksIncluded": featured,
    }


def asset_vo(asset: CompAsset, metrics: dict) -> dict:
    initial = (asset.comp_name_std or "?")[:1]
    return {
        "id": str(asset.id),
        "assetNo": asset.asset_no,
        "compName": asset.comp_name_std,
        "platform": asset.platform,
        "compAccountId": asset.comp_account_id,
        "avatarInitial": initial,
        "followerCount": metrics["followerCount"],
        "works30d": metrics["works30d"],
        "engagementRate": metrics["engagementRate"],
        "featuredWorksIncluded": metrics["featuredWorksIncluded"],
        "latestVersion": asset.latest_version,
        "referenceCount": asset.reference_count,
        "status": asset.status,
    }


def ensure_seed_assets(db: Session, tenant_id: int, actor_id: int) -> None:
    count = db.scalar(
        select(func.count())
        .select_from(CompAsset)
        .where(CompAsset.deleted == 0, CompAsset.tenant_id == tenant_id)
    )
    if count:
        return
    seeds = [
        ("Keep 官方", "DOUYIN", "", 4_860_000, 62, 4.8),
        ("刘畊宏", "DOUYIN", "", 61_230_000, 28, 6.2),
        ("咕咚运动", "WECHAT_CHANNELS", "", 1_320_000, 45, 3.1),
        ("悦跑圈", "XIAOHONGSHU", "", 860_000, 55, 5.4),
    ]
    for name, platform, acc_id, fans, works, rate in seeds:
        db.add(
            CompAsset(
                asset_no=next_asset_no(db, tenant_id),
                comp_name_std=name,
                comp_account_id=acc_id,
                platform=platform,
                base_info={
                    "followerCount": fans,
                    "works30d": works,
                    "engagementRate": rate,
                    "featuredWorksIncluded": True,
                },
                latest_version=1,
                reference_count=0,
                status="APPROVED",
                created_by=actor_id,
                tenant_id=tenant_id,
            )
        )
    db.flush()


@router.get("/list")
def asset_list(
    pageNo: int = 1,
    pageSize: int = 20,
    compName: str = "",
    platform: str = "",
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    if err := check_enum(db, "dict_platform_type", platform or None, False):
        return err
    ensure_seed_assets(db, tenant_id, actor.id)

    stmt = select(CompAsset).where(CompAsset.deleted == 0, CompAsset.tenant_id == tenant_id)
    if compName.strip():
        stmt = stmt.where(CompAsset.comp_name_std.like(f"%{compName.strip()}%"))
    if platform.strip():
        stmt = stmt.where(CompAsset.platform == platform.strip())

    page_no, size = page_args(pageNo, pageSize)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(
        stmt.order_by(CompAsset.id.desc()).offset((page_no - 1) * size).limit(size)
    ).all()
    items = [asset_vo(row, enrich_metrics(ops, tenant_id, row)) for row in rows]
    return paged(items, int(total or 0), page_no, size)


@router.post("/")
def create_asset(
    body: AssetBody,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    name = normalize_name(body.compName)
    if not name:
        return fail(1001, "竞品名称必填")
    if err := check_enum(db, "dict_platform_type", body.platform, True):
        return err
    exists = db.scalar(
        select(CompAsset.id).where(
            CompAsset.deleted == 0,
            CompAsset.tenant_id == tenant_id,
            CompAsset.comp_name_std == name,
        )
    )
    if exists:
        return fail(1203, "竞品名称已存在")
    row = CompAsset(
        asset_no=next_asset_no(db, tenant_id),
        comp_name_std=name,
        comp_account_id=(body.compAccountId or "").strip(),
        platform=body.platform.strip(),
        base_info={
            "followerCount": body.followerCount,
            "works30d": body.works30d,
            "engagementRate": body.engagementRate,
            "featuredWorksIncluded": body.works30d > 0,
        },
        latest_version=1,
        reference_count=0,
        status="APPROVED",
        created_by=actor.id,
        tenant_id=tenant_id,
    )
    db.add(row)
    db.flush()
    return ok(asset_vo(row, enrich_metrics(ops, tenant_id, row)))
