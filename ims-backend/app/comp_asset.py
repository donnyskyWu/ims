"""竞品库 COMP-003 · V3 资产库（与 M7 comp-analysis 监测分离）。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.core import SessionLocal, utcnow
from app.corp import check_enum, ops_db, page_args, paged, tenant_of
from app.models import CompAsset, CompAssetSeq, User
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


def _used_seq(db: Session, tenant_id: int, prefix: str) -> int:
    numbers = {
        no
        for no in db.scalars(
            select(CompAsset.asset_no).where(
                CompAsset.tenant_id == tenant_id,
                CompAsset.asset_no.like(f"{prefix}%"),
            )
        ).all()
        if no
    }
    for obj in list(db.new) + list(db.dirty):
        if isinstance(obj, CompAsset) and int(obj.tenant_id or 0) == int(tenant_id) and obj.asset_no:
            numbers.add(obj.asset_no)
    best = 0
    for no in numbers:
        if not str(no).startswith(prefix):
            continue
        tail = str(no)[len(prefix) :]
        if tail.isdigit():
            best = max(best, int(tail))
    return best


def _ensure_seq_row(tenant_id: int, day: str) -> None:
    """用短事务建序号行。并发插入冲突或死锁时重试，不碰调用方事务。"""
    from sqlalchemy.exc import OperationalError

    for _ in range(5):
        db = SessionLocal()
        try:
            found = db.scalar(
                select(CompAssetSeq.id).where(
                    CompAssetSeq.tenant_id == tenant_id,
                    CompAssetSeq.biz_date == day,
                )
            )
            if found is not None:
                return
            db.add(CompAssetSeq(biz_date=day, tenant_id=tenant_id, seq_val=0))
            db.commit()
            return
        except IntegrityError:
            db.rollback()
        except OperationalError as exc:
            db.rollback()
            if "1213" not in str(exc):
                raise
        finally:
            db.close()


def _lock_day_seq(db: Session, tenant_id: int, day: str) -> CompAssetSeq:
    stmt = (
        select(CompAssetSeq)
        .where(CompAssetSeq.tenant_id == tenant_id, CompAssetSeq.biz_date == day)
        .with_for_update()
    )
    _ensure_seq_row(tenant_id, day)
    row = db.scalar(stmt)
    if row is None:
        _ensure_seq_row(tenant_id, day)
        row = db.scalar(stmt)
    if row is None:
        raise RuntimeError("竞品单号序号行不存在")
    return row


def next_asset_no(db: Session, tenant_id: int) -> str:
    """锁当日序号行后取下一个空号。已有单号（含软删）只参与占号，不会被改写。"""
    day = datetime.now(BJ).strftime("%Y%m%d")
    prefix = f"CP{day}"
    row = _lock_day_seq(db, tenant_id, day)
    floor = _used_seq(db, tenant_id, prefix)
    if int(row.seq_val or 0) < floor:
        row.seq_val = floor
    row.seq_val = int(row.seq_val or 0) + 1
    db.flush()
    return f"{prefix}{int(row.seq_val):03d}"


def assign_and_flush(db: Session, row: CompAsset) -> str:
    """写入新档案。单号唯一冲突时重新取号，名称冲突原样抛出。"""
    last: Exception | None = None
    for _ in range(5):
        if row in db:
            db.expunge(row)
        row.asset_no = next_asset_no(db, int(row.tenant_id or 0))
        try:
            with db.begin_nested():
                db.add(row)
            return row.asset_no
        except IntegrityError as exc:
            last = exc
            message = str(getattr(exc, "orig", exc))
            if "uk_comp_asset_no" not in message:
                raise
    if last is not None:
        raise last
    raise RuntimeError("竞品单号分配失败")


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


AUDIT_LABELS = {
    "APPROVED": "已入库",
    "STORED": "已入库",
    "TRACKING": "已入库",
    "PENDING": "待初审",
    "SUBMITTED": "待初审",
    "REJECTED": "已退回",
    "PAUSED": "暂停",
    "ARCHIVED": "归档",
}


def asset_vo(asset: CompAsset, metrics: dict) -> dict:
    initial = (asset.comp_name_std or "?")[:1]
    info = dict(asset.base_info or {})
    status = asset.status or "APPROVED"
    stored = status in {"APPROVED", "STORED", "TRACKING"}
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
        "status": status,
        "auditStatus": "STORED" if stored else status,
        "auditStatusLabel": AUDIT_LABELS.get(status, status),
        "monitorSubscribed": bool(info.get("monitorSubscribed", stored)),
        "homepageUrl": info.get("homepageUrl") or "",
        "cardKind": "asset",
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
        assign_and_flush(
            db,
            CompAsset(
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
            ),
        )


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
    assign_and_flush(db, row)
    return ok(asset_vo(row, enrich_metrics(ops, tenant_id, row)))


COMPARE_KEYS = (
    ("sales", "销售"),
    ("gmv", "GMV"),
    ("priceBand", "价格带"),
    ("contentStrategy", "内容策略"),
    ("adStrategy", "投放策略"),
    ("followerCount", "粉丝数"),
    ("works30d", "近30天作品"),
    ("engagementRate", "互动率"),
)


def _load_asset(db: Session, tenant_id: int, asset_no: str) -> CompAsset | None:
    return db.scalar(
        select(CompAsset).where(
            CompAsset.deleted == 0,
            CompAsset.tenant_id == tenant_id,
            CompAsset.asset_no == asset_no,
        )
    )


def top_works(ops: Session, tenant_id: int, account_identifier: str) -> list[dict]:
    if not account_identifier:
        return []
    rows = ops.scalars(
        select(ExternalWork)
        .where(
            ExternalWork.deleted == 0,
            ExternalWork.tenant_id == tenant_id,
            ExternalWork.account_identifier == account_identifier,
        )
        .order_by(ExternalWork.play_count.desc())
        .limit(3)
    ).all()
    return [
        {
            "title": row.title,
            "platformType": row.platform_type,
            "playCount": row.play_count,
            "likeCount": row.like_count,
        }
        for row in rows
    ]


def interaction_trend(rate: float) -> list[dict]:
    """没有日快照时给出 7 日示意，避免抽屉空白。"""
    today = datetime.now(BJ).date()
    base = float(rate or 0)
    return [
        {"date": (today - timedelta(days=6 - index)).isoformat(), "value": round(base, 1)}
        for index in range(7)
    ]


def asset_detail(ops: Session, tenant_id: int, asset: CompAsset) -> dict:
    metrics = enrich_metrics(ops, tenant_id, asset)
    vo = asset_vo(asset, metrics)
    info = dict(asset.base_info or {})
    works = int(metrics["works30d"] or 0)
    vo.update(
        {
            "versionTimeline": list(info.get("versionTimeline") or []),
            "aliasList": list(info.get("aliasList") or []),
            "conclusion": info.get("conclusion") or "",
            "dataSource": info.get("dataSource") or "",
            "dimensionData": dict(info.get("dimensionData") or {}),
            "updateFrequency": round(works / 30, 2),
            "trendNote": "示意（暂无日快照）",
            "interactionTrend": interaction_trend(float(metrics["engagementRate"] or 0)),
            "topWorks": top_works(ops, tenant_id, asset.comp_account_id),
            "monitorEffectiveDate": info.get("monitorEffectiveDate") or "",
        }
    )
    return vo


@router.get("/compare")
def compare_assets(
    assetNos: str = "",
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    numbers = [item.strip() for item in (assetNos or "").split(",") if item.strip()]
    if not numbers or len(numbers) > 5:
        return fail(1001, "请选择 1 到 5 个已入库竞品")
    assets: list[tuple[CompAsset, dict]] = []
    for number in numbers:
        row = _load_asset(db, tenant_id, number)
        if row is None:
            return fail(1504, f"竞品档案不存在：{number}")
        if row.status not in {"APPROVED", "STORED", "TRACKING"}:
            return fail(1001, "未入库的竞品不能加入对比")
        assets.append((row, asset_detail(ops, tenant_id, row)))
    matrix = []
    for key, _label in COMPARE_KEYS:
        values = []
        for _row, detail in assets:
            if key in {"followerCount", "works30d", "engagementRate"}:
                values.append(detail.get(key))
            else:
                values.append((detail.get("dimensionData") or {}).get(key))
        matrix.append({"dimensionKey": key, "values": values})
    return ok(
        {
            "assetNos": numbers,
            "dimensionMatrix": matrix,
            "conclusions": [
                {
                    "assetNo": detail["assetNo"],
                    "compNameStd": detail["compName"],
                    "conclusion": detail.get("conclusion") or "",
                }
                for _row, detail in assets
            ],
            "generatedAt": datetime.now(BJ).strftime("%Y-%m-%d %H:%M"),
        }
    )


@router.get("/{asset_no}")
def get_asset(
    asset_no: str,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    row = _load_asset(db, tenant_of(actor), asset_no)
    if row is None:
        return fail(1504, "竞品档案不存在")
    return ok(asset_detail(ops, tenant_of(actor), row))
