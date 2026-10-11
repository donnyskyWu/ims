"""采集成功后把桩结果投影到内部分析表。

任务页 simulate_run 与平台 Collector 落库都会调用这里，保证 oa_internal_account /
oa_internal_content 有数据。重复采集按账号标识和标题幂等更新。
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import utcnow
from app.crypto import encrypt_text
from app.ops_models import (
    CollectorAccountBind,
    Company,
    InternalAccount,
    InternalContent,
    IpGroup,
    PlatformAccount,
)

DEMO_PLATFORM_ID = "stub-dy-demo"
DEMO_ACCOUNT_NAME = "桩采集演示号"

# 与 BR-003 / BR-004 对齐的桩样例：爆款、低分、正常各一条。
STUB_WORKS = (
    ("hit", "桩采集·爆款样例", 1_284_000, 38.0, "2026-10-01 20:00:00"),
    ("low", "桩采集·低分样例", 62_000, 11.0, "2026-10-02 12:00:00"),
    ("ok", "桩采集·日常样例", 89_000, 26.0, "2026-10-03 09:00:00"),
)

_FOLLOWERS = {"DOUYIN": 12880, "KUAISHOU": 8600, "WECHAT_CHANNELS": 24600}


def completion_rate_for(video_id: str) -> float:
    """桩作品没有完播率时按 video_id 末位给出稳定值：奇数 <20%（低分），偶数正常。"""
    digits = [ch for ch in video_id if ch.isdigit()]
    tail = int(digits[-1]) if digits else 0
    return 12.0 if tail % 2 else 36.0


def _identifier(account: PlatformAccount) -> str:
    return (account.platform_account_id or account.account_no or str(account.id))[:128]


def upsert_internal_account(
    ops: Session,
    account: PlatformAccount,
    *,
    follower_count: int | None = None,
) -> InternalAccount:
    tenant_id = account.tenant_id or 0
    ident = _identifier(account)
    row = ops.scalar(
        select(InternalAccount).where(
            InternalAccount.deleted == 0,
            InternalAccount.tenant_id == tenant_id,
            InternalAccount.platform_type == account.platform_type,
            InternalAccount.account_identifier == ident,
        )
    )
    if row is None:
        row = InternalAccount(
            account_identifier=ident,
            platform_type=account.platform_type or "",
            tenant_id=tenant_id,
            deleted=0,
        )
        ops.add(row)
    row.account_name = (account.account_name or ident)[:128]
    row.ip_group_id = account.ip_group_id
    row.account_status = account.status or ""
    if follower_count is not None:
        row.follower_count = int(follower_count)
    elif not row.follower_count:
        row.follower_count = _FOLLOWERS.get(account.platform_type or "", 12880)
    row.last_synced_at = utcnow().strftime("%Y-%m-%d %H:%M:%S")
    row.updated_at = utcnow()
    ops.flush()
    return row


def upsert_internal_work(
    ops: Session,
    account: PlatformAccount,
    internal: InternalAccount,
    *,
    title: str,
    play_count: int,
    completion_rate: float,
    publish_time: str,
) -> None:
    tenant_id = account.tenant_id or 0
    title_text = (title or "未命名作品")[:255]
    published = (publish_time or "")[:32]
    row = ops.scalar(
        select(InternalContent).where(
            InternalContent.deleted == 0,
            InternalContent.tenant_id == tenant_id,
            InternalContent.account_id == internal.id,
            InternalContent.title == title_text,
            InternalContent.publish_time == published,
        )
    )
    if row is None:
        row = InternalContent(
            tenant_id=tenant_id,
            account_id=internal.id,
            title=title_text,
            publish_time=published,
            deleted=0,
        )
        ops.add(row)
    row.account_name = internal.account_name
    row.platform_type = account.platform_type or ""
    row.ip_group_id = account.ip_group_id
    row.play_count = int(play_count or 0)
    row.completion_rate = float(completion_rate or 0)
    row.content_type = "VIDEO"
    row.updated_at = utcnow()
    ops.flush()


def _refresh_content_count(ops: Session, internal: InternalAccount) -> None:
    total = ops.scalar(
        select(func.count()).select_from(InternalContent).where(
            InternalContent.deleted == 0,
            InternalContent.tenant_id == internal.tenant_id,
            InternalContent.account_id == internal.id,
        )
    )
    internal.content_count = int(total or 0)
    internal.updated_at = utcnow()


def persist_stub_catalog(ops: Session, account: PlatformAccount) -> InternalAccount:
    """任务页桩执行成功后写入爆款 / 低分 / 正常样例。"""
    internal = upsert_internal_account(
        ops,
        account,
        follower_count=_FOLLOWERS.get(account.platform_type or "", 12880),
    )
    for _key, title, play, completion, published in STUB_WORKS:
        upsert_internal_work(
            ops,
            account,
            internal,
            title=f"{title}",
            play_count=play,
            completion_rate=completion,
            publish_time=published,
        )
    _refresh_content_count(ops, internal)
    return internal


def persist_run_accounts(
    ops: Session,
    _task,
    type_results: list[dict],
    account_id: int | None,
) -> None:
    ids: list[int] = []
    if account_id:
        ids.append(int(account_id))
    for item in type_results or []:
        if item.get("status") != "SUCCESS":
            continue
        raw = item.get("accountId")
        if raw:
            ids.append(int(raw))
    seen: set[int] = set()
    for aid in ids:
        if aid in seen:
            continue
        seen.add(aid)
        account = ops.get(PlatformAccount, aid)
        if account is None or account.deleted:
            continue
        persist_stub_catalog(ops, account)


def mirror_collected_video(ops: Session, account: PlatformAccount, item: dict) -> None:
    """Collector 作品行同步到内部作品，完播率按 video_id 稳定生成。"""
    video_id = str(item.get("video_id") or item.get("videoId") or "").strip()
    if not video_id:
        return
    play = 0
    for name in ("play_count", "playCount", "read_count", "readCount"):
        if item.get(name) is not None:
            try:
                play = int(item[name])
            except (TypeError, ValueError):
                play = 0
            break
    title = str(item.get("title") or video_id)
    published = str(item.get("publish_time") or item.get("publishTime") or item.get("create_time") or "")
    internal = upsert_internal_account(ops, account)
    upsert_internal_work(
        ops,
        account,
        internal,
        title=title,
        play_count=play,
        completion_rate=completion_rate_for(video_id),
        publish_time=published,
    )
    _refresh_content_count(ops, internal)


def mirror_follower_count(ops: Session, account: PlatformAccount, follower_count: int) -> None:
    upsert_internal_account(ops, account, follower_count=follower_count)


def ensure_stub_analysis_demo() -> None:
    """空库补一条已绑定抖音账号和桩样例，让内部分析不是 0 条。已有作品则跳过。"""
    from app.ops_db import ops_session

    ops = ops_session()
    try:
        content_count = ops.scalar(
            select(func.count()).select_from(InternalContent).where(InternalContent.deleted == 0)
        )
        if content_count:
            return
        account = ops.scalar(
            select(PlatformAccount).where(
                PlatformAccount.deleted == 0,
                PlatformAccount.platform_account_id == DEMO_PLATFORM_ID,
            )
        )
        if account is None:
            company = Company(company_name="桩采集演示公司", status="ENABLED", tenant_id=0)
            group = IpGroup(group_name="桩采集演示组", status="ENABLED", tenant_id=0)
            ops.add_all([company, group])
            ops.flush()
            account = PlatformAccount(
                account_no="STUB-DY-DEMO",
                account_name=DEMO_ACCOUNT_NAME,
                platform_type="DOUYIN",
                platform_account_id=DEMO_PLATFORM_ID,
                ip_group_id=group.id,
                company_id=company.id,
                cookie_enc=encrypt_text("stub-cookie"),
                status="IN_USE",
                tenant_id=0,
            )
            ops.add(account)
            ops.flush()
            ops.add(
                CollectorAccountBind(
                    oa_account_id=account.id,
                    collector_account_id=f"acc_douyin_{DEMO_PLATFORM_ID}",
                    bind_status="BOUND",
                    conn_status="SUCCESS",
                    tenant_id=0,
                )
            )
        persist_stub_catalog(ops, account)
        ops.commit()
    except Exception:
        ops.rollback()
        raise
    finally:
        ops.close()
