"""内部账号作品与粉丝日统计公共层。

快手与抖音共用：账号凭证掩码、Collector 绑定、IMS 定时器、幂等写入、采集记录和健康状态。
平台差异只放在 PlatformProfile（接口、表、source / dataType）。
同一条定时器先写 FOLLOWER_STATS（契约里有粉丝列表时再写列表），再写作品。
作品日快照已覆盖：不另调 video-stats / videos/stats，播放、点赞、评论、转发随作品列表写入当日快照。
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collector_client import MSG_COOKIE, MSG_ENGINE, CollectorCall, account_health, import_account
from app.core import utcnow
from app.crypto import decrypt_text, encrypt_text
from app.models import User
from app.ops_models import CollectLog, CollectTask, CollectorAccountBind, PlatformAccount

STATUS_LABEL = {
    "SUCCESS": "成功",
    "FAILED": "失败",
    "PARTIAL": "部分成功",
    "COOKIE_EXPIRED": "Cookie 已失效",
    "ENGINE_UNAVAILABLE": "浏览器引擎不可用",
}
_PROFILES: list[PlatformProfile] = []
_SCHEDULER_STARTED = False


@dataclass(frozen=True)
class PlatformProfile:
    key: str
    platform_type: str
    source: str
    data_type: str
    cred_prefix: str
    task_suffix: str
    missing_member_error: str
    video_model: type
    snapshot_model: type
    fetch_videos: Callable[..., CollectorCall]
    import_platform: str
    fetch_follower_stats: Callable[..., CollectorCall] | None = None
    fetch_followers: Callable[..., CollectorCall] | None = None
    follower_model: type | None = None
    follower_daily_model: type | None = None
    follower_list_data_type: str = ""


class AccountBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    accountName: str | None = None
    companyId: int | None = None
    ipGroupId: int | None = None
    platformAccountId: str | None = None
    cookie: str | None = None
    authToken: str | None = None
    frequency: str | None = None
    cron: str | None = None


def register(profile: PlatformProfile) -> None:
    if all(item.key != profile.key for item in _PROFILES):
        _PROFILES.append(profile)


def profiles() -> list[PlatformProfile]:
    return list(_PROFILES)


def profile_of(platform_type: str) -> PlatformProfile | None:
    for item in _PROFILES:
        if item.platform_type == platform_type:
            return item
    return None


def ops_db():
    """延迟导入，避免 collect → 平台模块 → corp → api → collect 环。"""
    from app.corp import ops_db as _ops_db

    yield from _ops_db()


def current_user(
    request: Request,
    authorization: str | None = Header(default=None),
):
    from app.api import current_user as _current_user
    from app.api import db_session

    gen = db_session()
    db = next(gen)
    try:
        user = _current_user(request, authorization, db)
        yield user
    except Exception as exc:
        gen.throw(exc)
    else:
        try:
            next(gen)
        except StopIteration:
            pass
    finally:
        gen.close()


def fail(code: int, msg: str, data=None):
    from app.api import fail as _fail

    return _fail(code, msg, data)


def ok(data=None):
    from app.api import ok as _ok

    return _ok(data)


def page_args(page_no: int, page_size: int):
    from app.corp import page_args as _page_args

    return _page_args(page_no, page_size)


def paged(rows: list, total: int, page_no: int, size: int):
    from app.corp import paged as _paged

    return _paged(rows, total, page_no, size)


def tenant_of(actor: User) -> int:
    from app.corp import tenant_of as _tenant_of

    return _tenant_of(actor)


def visible(row, actor: User) -> bool:
    from app.corp import visible as _visible

    return _visible(row, actor)


def bind_summary(row, bind):
    from app.account import bind_summary as _bind_summary

    return _bind_summary(row, bind)


def check_company(ops: Session, actor: User, company_id: int | None, required: bool):
    from app.account import check_company as _check_company

    return _check_company(ops, actor, company_id, required)


def check_ip_group(ops: Session, actor: User, group_id: int | None, required: bool):
    from app.account import check_ip_group as _check_ip_group

    return _check_ip_group(ops, actor, group_id, required)


def status_label(status: str) -> str:
    return STATUS_LABEL.get(status, status or "失败")


def credential_mask(enc: str) -> str:
    if not enc:
        return ""
    return "****" + hashlib.sha256(enc.encode()).hexdigest()[:4]


def health_label(bind: CollectorAccountBind | None) -> str:
    if bind is None or bind.deleted or bind.bind_status != "BOUND":
        return "未绑定"
    return {
        "SUCCESS": "连接正常",
        "CONNECTED": "连接正常",
        "COOKIE_EXPIRED": "Cookie 已失效",
        "ENGINE_UNAVAILABLE": "浏览器引擎不可用",
        "FAILED": "连接失败",
    }.get(bind.conn_status or "", "未探活")


def pack_credential(cookie: str, auth_token: str) -> str:
    payload = json.dumps({"cookie": cookie, "authToken": auth_token}, ensure_ascii=False)
    return encrypt_text(payload)


def unpack_credential(enc: str) -> tuple[str, str]:
    if not enc:
        return "", ""
    plain = decrypt_text(enc)
    if plain.startswith("{"):
        try:
            data = json.loads(plain)
        except json.JSONDecodeError:
            data = None
        if isinstance(data, dict) and "cookie" in data:
            return str(data.get("cookie") or ""), str(data.get("authToken") or "")
    return plain, ""


def initial_next_run(frequency: str, now=None) -> str:
    base = now or utcnow()
    if frequency == "HOURLY":
        nxt = base + timedelta(hours=1)
    elif frequency == "WEEKLY":
        nxt = base + timedelta(days=7)
    else:
        nxt = base + timedelta(days=1)
    return nxt.strftime("%Y-%m-%d %H:%M:%S")


def _bind_of(ops: Session, account_id: int) -> CollectorAccountBind | None:
    return ops.scalar(
        select(CollectorAccountBind).where(
            CollectorAccountBind.oa_account_id == account_id,
            CollectorAccountBind.deleted == 0,
        )
    )


def video_snapshot_public(ops: Session, account: PlatformAccount) -> dict:
    """最近作品日快照。指标来自作品列表，不是独立的 stats 拉取。"""
    profile = profile_of(account.platform_type)
    model = profile.snapshot_model if profile else None
    if model is None:
        return {"videoSnapshots": []}
    rows = ops.scalars(
        select(model)
        .where(
            model.tenant_id == (account.tenant_id or 0),
            model.account_id == account.id,
            model.deleted == 0,
        )
        .order_by(model.stat_date.desc(), model.id.desc())
        .limit(20)
    ).all()
    return {
        "videoSnapshots": [
            {
                "videoId": row.video_id,
                "statDate": row.stat_date or "",
                "playCount": int(row.play_count or 0),
                "likeCount": int(row.like_count or 0),
                "commentCount": int(row.comment_count or 0),
                "shareCount": int(row.share_count or 0),
            }
            for row in rows
        ]
    }


def follower_public(ops: Session, account: PlatformAccount) -> dict:
    empty = {"followerCount": None, "followerStatDate": "", "followerDaily": []}
    profile = profile_of(account.platform_type)
    model = profile.follower_daily_model if profile else None
    if model is None:
        return empty
    rows = ops.scalars(
        select(model)
        .where(
            model.tenant_id == (account.tenant_id or 0),
            model.account_id == account.id,
            model.deleted == 0,
        )
        .order_by(model.stat_date.desc(), model.id.desc())
        .limit(7)
    ).all()
    if not rows:
        return empty
    latest = rows[0]
    return {
        "followerCount": int(latest.follower_count or 0),
        "followerStatDate": latest.stat_date or "",
        "followerDaily": [
            {
                "statDate": row.stat_date,
                "followerCount": int(row.follower_count or 0),
                "newFollowerCount": int(row.new_follower_count or 0),
            }
            for row in rows
        ],
    }


def account_public(ops: Session, row: PlatformAccount) -> dict:
    bind = _bind_of(ops, row.id)
    data = {
        "id": row.id,
        "accountNo": row.account_no or str(row.id),
        "accountName": row.account_name,
        "platformType": row.platform_type,
        "platformAccountId": row.platform_account_id or "",
        "credentialRef": row.credential_ref or "",
        "credentialMask": credential_mask(row.cookie_enc),
        "hasCredential": bool(row.cookie_enc),
        "companyId": row.company_id,
        "ipGroupId": row.ip_group_id,
        "collectBindSummary": bind_summary(row, bind),
        "healthLabel": health_label(bind),
        "collectorAccountId": bind.collector_account_id if bind else "",
        "connStatus": bind.conn_status if bind else "",
        "bindStatus": bind.bind_status if bind else "UNBOUND",
    }
    data.update(follower_public(ops, row))
    data.update(video_snapshot_public(ops, row))
    return data


def task_public(row: CollectTask | None) -> dict | None:
    if row is None:
        return None
    return {
        "id": str(row.id),
        "taskName": row.task_name,
        "cron": row.cron,
        "frequency": row.frequency,
        "status": row.status,
        "nextRunAt": row.next_run_at or None,
        "lastRunAt": row.last_run_at or None,
    }


def _load_account(ops: Session, actor: User, profile: PlatformProfile, account_id: int) -> PlatformAccount | None:
    row = ops.get(PlatformAccount, account_id)
    if not visible(row, actor) or row.platform_type != profile.platform_type:
        return None
    return row


def _apply_secret(profile: PlatformProfile, row: PlatformAccount, cookie: str, auth_token: str) -> None:
    row.cookie_enc = pack_credential(cookie, auth_token)
    row.credential_ref = f"{profile.cred_prefix}{row.id}"


def ensure_task(
    profile: PlatformProfile,
    ops: Session,
    account: PlatformAccount,
    *,
    frequency: str | None,
    cron: str | None,
) -> CollectTask:
    row = ops.scalar(
        select(CollectTask).where(
            CollectTask.account_id == account.id,
            CollectTask.deleted == 0,
            CollectTask.platform_type == profile.platform_type,
            CollectTask.method == "INTERNAL",
            CollectTask.source == profile.source,
        )
    )
    freq = (frequency or "").strip() or "DAILY"
    cron_text = (cron or "").strip() or "0 2 * * *"
    if row is None:
        row = CollectTask(
            task_name=f"{account.account_name or account.account_no} · {profile.task_suffix}",
            platform_type=profile.platform_type,
            account_id=account.id,
            method="INTERNAL",
            source=profile.source,
            data_type=profile.data_type,
            frequency=freq if frequency else "DAILY",
            cron=cron_text if cron else "0 2 * * *",
            status="ENABLED",
            next_run_at=initial_next_run(freq if frequency else "DAILY"),
            tenant_id=account.tenant_id or 0,
        )
        ops.add(row)
        ops.flush()
        return row
    if frequency:
        row.frequency = frequency.strip() or row.frequency
    if cron:
        row.cron = cron.strip() or row.cron
    row.source = profile.source
    row.data_type = profile.data_type
    row.method = "INTERNAL"
    row.status = "ENABLED"
    if not row.next_run_at:
        row.next_run_at = initial_next_run(row.frequency or "DAILY")
    row.updated_at = utcnow()
    return row


def _int_field(item: dict, *names: str) -> int:
    for name in names:
        if name in item and item[name] is not None:
            try:
                return int(item[name])
            except (TypeError, ValueError):
                return 0
    return 0


def upsert_videos(profile: PlatformProfile, ops: Session, account: PlatformAccount, videos: list[dict]) -> int:
    """作品列表写入作品行，并按租户 + 账号 + video_id + 统计日幂等更新日快照。

    日快照已覆盖。Collector 的 video-stats、账号视频汇总与列表指标重复，这里不扩展字段、不另开拉取。
    """
    stat_date = utcnow().strftime("%Y-%m-%d")
    collected_at = utcnow().strftime("%Y-%m-%d %H:%M:%S")
    written = 0
    tenant_id = account.tenant_id or 0
    video_model = profile.video_model
    snap_model = profile.snapshot_model
    for item in videos:
        video_id = str(item.get("video_id") or item.get("videoId") or "").strip()
        if not video_id:
            continue
        play_count = _int_field(item, "play_count", "playCount")
        like_count = _int_field(item, "like_count", "likeCount")
        comment_count = _int_field(item, "comment_count", "commentCount")
        share_count = _int_field(item, "share_count", "shareCount")
        title = str(item.get("title") or "")[:255]
        cover = str(item.get("cover_url") or item.get("coverUrl") or "")[:512]
        publish_time = str(item.get("publish_time") or item.get("publishTime") or "")[:32]
        duration_sec = _int_field(item, "duration_sec", "durationSec")
        row = ops.scalar(
            select(video_model).where(
                video_model.tenant_id == tenant_id,
                video_model.account_id == account.id,
                video_model.video_id == video_id,
                video_model.deleted == 0,
            )
        )
        if row is None:
            row = video_model(
                tenant_id=tenant_id,
                account_id=account.id,
                video_id=video_id,
                deleted=0,
            )
            ops.add(row)
        row.title = title
        row.cover_url = cover
        row.play_count = play_count
        row.like_count = like_count
        row.comment_count = comment_count
        row.share_count = share_count
        row.publish_time = publish_time
        row.duration_sec = duration_sec
        row.updated_at = utcnow()
        snap = ops.scalar(
            select(snap_model).where(
                snap_model.tenant_id == tenant_id,
                snap_model.account_id == account.id,
                snap_model.video_id == video_id,
                snap_model.stat_date == stat_date,
                snap_model.deleted == 0,
            )
        )
        if snap is None:
            snap = snap_model(
                tenant_id=tenant_id,
                account_id=account.id,
                video_id=video_id,
                stat_date=stat_date,
                deleted=0,
            )
            ops.add(snap)
        snap.play_count = play_count
        snap.like_count = like_count
        snap.comment_count = comment_count
        snap.share_count = share_count
        snap.collected_at = collected_at
        snap.updated_at = utcnow()
        written += 1
        ops.flush()
    return written


def upsert_follower_daily(profile: PlatformProfile, ops: Session, account: PlatformAccount, call: CollectorCall) -> int:
    model = profile.follower_daily_model
    if model is None or call.follower_count is None:
        return 0
    stat_date = (call.stat_date or utcnow().strftime("%Y-%m-%d"))[:10]
    collected_at = utcnow().strftime("%Y-%m-%d %H:%M:%S")
    tenant_id = account.tenant_id or 0
    row = ops.scalar(
        select(model).where(
            model.tenant_id == tenant_id,
            model.account_id == account.id,
            model.stat_date == stat_date,
            model.deleted == 0,
        )
    )
    if row is None:
        row = model(
            tenant_id=tenant_id,
            account_id=account.id,
            stat_date=stat_date,
            deleted=0,
        )
        ops.add(row)
    row.follower_count = call.follower_count
    row.following_count = call.following_count or 0
    row.new_follower_count = call.new_follower_count or 0
    row.collected_at = collected_at
    row.updated_at = utcnow()
    ops.flush()
    return 1


def upsert_followers(profile: PlatformProfile, ops: Session, account: PlatformAccount, followers: list[dict]) -> int:
    model = profile.follower_model
    if model is None:
        return 0
    written = 0
    tenant_id = account.tenant_id or 0
    for item in followers:
        follower_id = str(item.get("follower_id") or item.get("followerId") or "").strip()
        if not follower_id:
            continue
        row = ops.scalar(
            select(model).where(
                model.tenant_id == tenant_id,
                model.account_id == account.id,
                model.follower_id == follower_id,
                model.deleted == 0,
            )
        )
        if row is None:
            row = model(
                tenant_id=tenant_id,
                account_id=account.id,
                follower_id=follower_id,
                deleted=0,
            )
            ops.add(row)
        row.nickname = str(item.get("nickname") or item.get("nick_name") or "")[:128]
        row.followed_at = str(item.get("followed_at") or item.get("followedAt") or "")[:32]
        row.updated_at = utcnow()
        written += 1
        ops.flush()
    return written


def _map_kind(kind: str, message: str) -> tuple[str, str]:
    if kind == "ok":
        return "SUCCESS", ""
    if kind == "cookie":
        return "COOKIE_EXPIRED", MSG_COOKIE
    if kind == "engine":
        return "ENGINE_UNAVAILABLE", MSG_ENGINE
    text = (message or "采集失败")[:200]
    return "FAILED", text


def _touch_bind(ops: Session, account: PlatformAccount, status: str) -> None:
    bind = _bind_of(ops, account.id)
    if bind is None:
        return
    if status in {"SUCCESS", "PARTIAL"}:
        bind.conn_status = "SUCCESS"
    elif status == "COOKIE_EXPIRED":
        bind.conn_status = "COOKIE_EXPIRED"
    elif status == "ENGINE_UNAVAILABLE":
        bind.conn_status = "ENGINE_UNAVAILABLE"
    elif status == "FAILED":
        bind.conn_status = "FAILED"
    else:
        return
    bind.last_probe_at = utcnow().strftime("%Y-%m-%d %H:%M:%S")
    bind.updated_at = utcnow()


def _write_log(
    profile: PlatformProfile,
    ops: Session,
    task: CollectTask,
    *,
    account_id: int | None,
    status: str,
    started_at: str,
    duration_ms: int,
    record_count: int,
    error_summary: str,
    steps: list[dict] | None = None,
) -> CollectLog:
    if steps is None:
        type_results = [
            {
                "dataType": profile.data_type,
                "status": status,
                "statusLabel": status_label(status),
                "recordCount": record_count,
                "error": error_summary or None,
            }
        ]
    else:
        type_results = steps
    log = CollectLog(
        task_id=task.id,
        account_id=account_id,
        status=status,
        started_at=started_at,
        duration_ms=max(duration_ms, 0),
        record_count=record_count,
        retry_count=0,
        error_summary=error_summary[:500],
        type_results_json=json.dumps(type_results, ensure_ascii=False),
        tenant_id=task.tenant_id or 0,
    )
    ops.add(log)
    ops.flush()
    return log


def _finish_task(task: CollectTask, status: str, started_at: str) -> None:
    task.last_run_at = started_at
    if status == "SUCCESS":
        task.success_count = (task.success_count or 0) + 1
    else:
        task.fail_count = (task.fail_count or 0) + 1
    task.next_run_at = initial_next_run(task.frequency or "DAILY")
    task.updated_at = utcnow()


def _aggregate(steps: list[dict]) -> tuple[str, str, int]:
    statuses = [str(step.get("status") or "") for step in steps]
    total = sum(int(step.get("recordCount") or 0) for step in steps)
    errors: list[str] = []
    for step in steps:
        err = step.get("error")
        if err and err not in errors:
            errors.append(str(err))
    error = "；".join(errors)[:500]
    if statuses and all(item == "SUCCESS" for item in statuses):
        return "SUCCESS", "", total
    if "SUCCESS" in statuses:
        return "PARTIAL", error, total
    if statuses and all(item == "COOKIE_EXPIRED" for item in statuses):
        return "COOKIE_EXPIRED", MSG_COOKIE, total
    if statuses and all(item == "ENGINE_UNAVAILABLE" for item in statuses):
        return "ENGINE_UNAVAILABLE", MSG_ENGINE, total
    if len(set(statuses)) == 1:
        return statuses[0], error or "采集失败", total
    return "FAILED", error or "采集失败", total


def _collect_steps(profile: PlatformProfile, ops: Session, account: PlatformAccount, collector_id: str) -> list[dict]:
    steps: list[dict] = []
    aborted = False

    def one(data_type: str, call: CollectorCall, write: Callable[[], int]) -> None:
        nonlocal aborted
        status, error = _map_kind(call.kind, call.message)
        count = write() if status == "SUCCESS" else 0
        item = {
            "dataType": data_type,
            "status": status,
            "statusLabel": status_label(status),
            "recordCount": count,
            "error": error or None,
        }
        if data_type == "FOLLOWER_STATS" and call.follower_count is not None and status == "SUCCESS":
            item["followerCount"] = call.follower_count
        steps.append(item)
        if status in {"COOKIE_EXPIRED", "ENGINE_UNAVAILABLE"}:
            aborted = True

    if profile.fetch_follower_stats is not None and not aborted:
        call = profile.fetch_follower_stats(account_id=collector_id)
        one("FOLLOWER_STATS", call, lambda: upsert_follower_daily(profile, ops, account, call))
    if profile.fetch_followers is not None and not aborted:
        call = profile.fetch_followers(account_id=collector_id)
        data_type = profile.follower_list_data_type or "DOUYIN_FOLLOWER_LIST"
        one(data_type, call, lambda: upsert_followers(profile, ops, account, call.followers))
    if not aborted:
        call = profile.fetch_videos(account_id=collector_id)
        one(profile.data_type, call, lambda: upsert_videos(profile, ops, account, call.videos))
    return steps


def run_one(profile: PlatformProfile, ops: Session, task: CollectTask, account: PlatformAccount) -> dict:
    started_clock = time.perf_counter()
    started_at = utcnow().strftime("%Y-%m-%d %H:%M:%S")
    status = "FAILED"
    error = ""
    record_count = 0
    steps: list[dict] | None = None
    try:
        bind = _bind_of(ops, account.id)
        if bind is None or bind.bind_status != "BOUND":
            status, error = "FAILED", "未绑定 Collector（oa_collector_account_bind）"
        elif not account.platform_account_id:
            status, error = "FAILED", "平台账号 ID 未配置"
        elif not bind.collector_account_id:
            status, error = "FAILED", "未绑定 Collector（oa_collector_account_bind）"
        else:
            try:
                cookie, _auth_token = unpack_credential(account.cookie_enc)
            except Exception:
                cookie = ""
                status, error = "FAILED", "凭证无法读取"
            if status != "FAILED" or not error:
                if not cookie:
                    status, error = "FAILED", "凭证未配置"
                else:
                    steps = _collect_steps(profile, ops, account, bind.collector_account_id)
                    status, error, record_count = _aggregate(steps)
    except Exception:
        status, error, record_count, steps = "FAILED", "采集失败", 0, None
    duration_ms = int((time.perf_counter() - started_clock) * 1000)
    _touch_bind(ops, account, status)
    log = _write_log(
        profile,
        ops,
        task,
        account_id=account.id,
        status=status,
        started_at=started_at,
        duration_ms=duration_ms,
        record_count=record_count,
        error_summary=error,
        steps=steps,
    )
    return {
        "logId": str(log.id),
        "taskId": str(task.id),
        "accountId": account.id,
        "status": status,
        "statusLabel": status_label(status),
        "recordCount": record_count,
        "durationMs": duration_ms,
        "errorSummary": error or None,
    }


def execute_task(profile: PlatformProfile, ops: Session, task: CollectTask) -> dict:
    started_at = utcnow().strftime("%Y-%m-%d %H:%M:%S")
    if task.is_unified:
        from app.ops_models import CollectTaskMember

        members = ops.scalars(
            select(CollectTaskMember).where(
                CollectTaskMember.task_id == task.id,
                CollectTaskMember.deleted == 0,
            )
        ).all()
        results = []
        for member in members:
            account = ops.get(PlatformAccount, member.account_id or 0)
            if account is None or account.deleted or account.platform_type != profile.platform_type:
                continue
            results.append(run_one(profile, ops, task, account))
        if not results:
            log = _write_log(
                profile,
                ops,
                task,
                account_id=None,
                status="FAILED",
                started_at=started_at,
                duration_ms=0,
                record_count=0,
                error_summary=profile.missing_member_error,
            )
            _finish_task(task, "FAILED", started_at)
            return {
                "logId": str(log.id),
                "taskId": str(task.id),
                "status": "FAILED",
                "statusLabel": status_label("FAILED"),
                "recordCount": 0,
                "durationMs": 0,
                "errorSummary": profile.missing_member_error,
            }
        statuses = {item["status"] for item in results}
        if statuses == {"SUCCESS"}:
            agg = "SUCCESS"
        elif "SUCCESS" in statuses:
            agg = "PARTIAL"
        elif statuses == {"COOKIE_EXPIRED"}:
            agg = "COOKIE_EXPIRED"
        elif statuses == {"ENGINE_UNAVAILABLE"}:
            agg = "ENGINE_UNAVAILABLE"
        else:
            agg = "FAILED"
        _finish_task(task, agg, started_at)
        last = results[-1]
        last["status"] = agg
        last["statusLabel"] = status_label(agg)
        last["recordCount"] = sum(item["recordCount"] for item in results)
        return last

    account = ops.get(PlatformAccount, task.account_id or 0)
    if account is None or account.deleted:
        log = _write_log(
            profile,
            ops,
            task,
            account_id=task.account_id,
            status="FAILED",
            started_at=started_at,
            duration_ms=0,
            record_count=0,
            error_summary="任务未绑定账号",
        )
        _finish_task(task, "FAILED", started_at)
        return {
            "logId": str(log.id),
            "taskId": str(task.id),
            "status": "FAILED",
            "statusLabel": status_label("FAILED"),
            "recordCount": 0,
            "durationMs": 0,
            "errorSummary": "任务未绑定账号",
        }
    result = run_one(profile, ops, task, account)
    _finish_task(task, result["status"], started_at)
    return result


def import_bind(profile: PlatformProfile, ops: Session, row: PlatformAccount, actor: User):
    if not row.platform_account_id:
        return fail(1001, "平台账号 ID 必填")
    try:
        cookie, auth_token = unpack_credential(row.cookie_enc)
    except Exception:
        return fail(1001, "凭证无法读取")
    if not cookie:
        return fail(1001, "凭证未配置")
    if not row.credential_ref:
        row.credential_ref = f"{profile.cred_prefix}{row.id}"
    call = import_account(
        platform=profile.import_platform,
        platform_account_id=row.platform_account_id,
        credential_ref=row.credential_ref,
        cookie=cookie,
        auth_token=auth_token,
    )
    if call.kind not in {"ok", "cookie", "engine"}:
        return fail(2022, call.message or "Collector 绑定失败")
    if call.kind != "ok" or not call.collector_account_id:
        if call.kind != "ok":
            return fail(2022, call.message or "Collector 绑定失败")
        return fail(2022, "Collector 未返回账号标识")
    bind = _bind_of(ops, row.id)
    if bind is None:
        bind = CollectorAccountBind(
            oa_account_id=row.id,
            tenant_id=tenant_of(actor),
            deleted=0,
            created_at=utcnow(),
        )
        ops.add(bind)
    bind.collector_account_id = call.collector_account_id
    bind.bind_status = "BOUND"
    if call.kind == "cookie":
        bind.conn_status = "COOKIE_EXPIRED"
    elif call.kind == "engine":
        bind.conn_status = "ENGINE_UNAVAILABLE"
    else:
        bind.conn_status = "SUCCESS"
    bind.last_probe_at = utcnow().strftime("%Y-%m-%d %H:%M:%S")
    bind.updated_at = utcnow()
    ops.flush()
    data = account_public(ops, row)
    return ok(data)


def probe_account(profile: PlatformProfile, ops: Session, row: PlatformAccount):
    bind = _bind_of(ops, row.id)
    if bind is None or bind.bind_status != "BOUND":
        return fail(1001, "未绑定 Collector")
    call = account_health(bind.collector_account_id)
    if call.kind == "cookie":
        bind.conn_status = "COOKIE_EXPIRED"
    elif call.kind == "engine":
        bind.conn_status = "ENGINE_UNAVAILABLE"
    elif call.kind == "ok":
        bind.conn_status = "SUCCESS"
    else:
        bind.conn_status = "FAILED"
    bind.last_probe_at = utcnow().strftime("%Y-%m-%d %H:%M:%S")
    bind.updated_at = utcnow()
    ops.flush()
    data = account_public(ops, row)
    if call.kind not in {"ok", "cookie", "engine"}:
        data["notice"] = call.message or "探活失败"
    return ok(data)


def tick_platform(profile: PlatformProfile, now=None) -> int:
    from app.ops_db import ops_session

    stamp = (now or utcnow()).strftime("%Y-%m-%d %H:%M:%S")
    ops = ops_session()
    ran = 0
    try:
        tasks = ops.scalars(
            select(CollectTask).where(
                CollectTask.deleted == 0,
                CollectTask.status == "ENABLED",
                CollectTask.platform_type == profile.platform_type,
                CollectTask.method == "INTERNAL",
                CollectTask.source == profile.source,
            )
        ).all()
        for task in tasks:
            if task.collect_config_id or task.is_external_unified:
                continue
            if task.next_run_at and task.next_run_at > stamp:
                continue
            execute_task(profile, ops, task)
            ran += 1
        ops.commit()
        return ran
    except Exception:
        ops.rollback()
        raise
    finally:
        ops.close()


def start_scheduler() -> None:
    global _SCHEDULER_STARTED
    if _SCHEDULER_STARTED:
        return
    flag = os.environ.get("IMS_COLLECT_SCHEDULER", "1").strip().lower()
    if flag in {"0", "false", "no"}:
        return
    _SCHEDULER_STARTED = True
    interval = max(5, int(os.environ.get("IMS_COLLECT_TICK_SEC", "30") or "30"))

    def loop() -> None:
        while True:
            for profile in list(_PROFILES):
                try:
                    tick_platform(profile)
                except Exception:
                    pass
            time.sleep(interval)

    threading.Thread(target=loop, name="ims-internal-collect", daemon=True).start()


def build_router(profile: PlatformProfile) -> APIRouter:
    router = APIRouter(prefix=f"/{profile.key}", tags=[f"{profile.key}-collect"])
    key = profile.key

    @router.get("/account/page", operation_id=f"{key}_account_page")
    def account_page(
        pageNo: int = 1,
        pageSize: int = 20,
        keyword: str = "",
        ops: Session = Depends(ops_db),
        actor: User = Depends(current_user),
    ):
        page_no, size = page_args(pageNo, pageSize)
        stmt = select(PlatformAccount).where(
            PlatformAccount.deleted == 0,
            PlatformAccount.tenant_id == tenant_of(actor),
            PlatformAccount.platform_type == profile.platform_type,
        )
        if keyword.strip():
            like = f"%{keyword.strip()}%"
            stmt = stmt.where(PlatformAccount.account_name.like(like))
        from app.corp import count_of

        total = count_of(ops, stmt)
        rows = ops.scalars(stmt.order_by(PlatformAccount.id.desc()).offset((page_no - 1) * size).limit(size)).all()
        return paged([account_public(ops, row) for row in rows], total, page_no, size)

    @router.post("/account", operation_id=f"{key}_account_create")
    def account_create(
        body: AccountBody,
        ops: Session = Depends(ops_db),
        actor: User = Depends(current_user),
    ):
        name = (body.accountName or "").strip()
        platform_id = (body.platformAccountId or "").strip()
        cookie = (body.cookie or "").strip()
        if not name or not platform_id or not cookie:
            return fail(1001, "昵称、平台账号 ID、凭证必填")
        for item in (
            check_company(ops, actor, body.companyId, True),
            check_ip_group(ops, actor, body.ipGroupId, True),
        ):
            if item is not None:
                return item
        row = PlatformAccount(
            tenant_id=tenant_of(actor),
            deleted=0,
            status="IN_USE",
            platform_type=profile.platform_type,
            account_name=name,
            platform_account_id=platform_id,
            company_id=body.companyId,
            ip_group_id=body.ipGroupId,
            holder_user_id=actor.id,
            created_at=utcnow(),
        )
        ops.add(row)
        ops.flush()
        row.account_no = f"ACCT-{utcnow().strftime('%Y')}-{row.id:04d}"
        _apply_secret(profile, row, cookie, (body.authToken or "").strip())
        task = ensure_task(profile, ops, row, frequency=body.frequency, cron=body.cron)
        return ok({"account": account_public(ops, row), "task": task_public(task)})

    @router.put("/account/{account_id}", operation_id=f"{key}_account_update")
    def account_update(
        account_id: int,
        body: AccountBody,
        ops: Session = Depends(ops_db),
        actor: User = Depends(current_user),
    ):
        row = _load_account(ops, actor, profile, account_id)
        if row is None:
            return fail(1504, "资源不可用")
        if body.accountName is not None and body.accountName.strip():
            row.account_name = body.accountName.strip()
        if body.platformAccountId is not None:
            platform_id = body.platformAccountId.strip()
            if not platform_id:
                return fail(1001, "平台账号 ID 必填")
            row.platform_account_id = platform_id
        if body.companyId is not None:
            if err := check_company(ops, actor, body.companyId, True):
                return err
            row.company_id = body.companyId
        if body.ipGroupId is not None:
            if err := check_ip_group(ops, actor, body.ipGroupId, True):
                return err
            row.ip_group_id = body.ipGroupId
        if body.cookie:
            try:
                _, old_token = unpack_credential(row.cookie_enc)
            except Exception:
                old_token = ""
            auth_token = body.authToken if body.authToken is not None else old_token
            _apply_secret(profile, row, body.cookie.strip(), (auth_token or "").strip())
        row.updated_at = utcnow()
        task = ensure_task(profile, ops, row, frequency=body.frequency, cron=body.cron)
        return ok({"account": account_public(ops, row), "task": task_public(task)})

    @router.post("/account/{account_id}/bind", operation_id=f"{key}_bind")
    def bind_account(
        account_id: int,
        ops: Session = Depends(ops_db),
        actor: User = Depends(current_user),
    ):
        row = _load_account(ops, actor, profile, account_id)
        if row is None:
            return fail(1504, "资源不可用")
        return import_bind(profile, ops, row, actor)

    @router.post("/account/{account_id}/probe", operation_id=f"{key}_probe")
    def probe(
        account_id: int,
        ops: Session = Depends(ops_db),
        actor: User = Depends(current_user),
    ):
        row = _load_account(ops, actor, profile, account_id)
        if row is None:
            return fail(1504, "资源不可用")
        return probe_account(profile, ops, row)

    @router.post("/account/{account_id}/run", operation_id=f"{key}_run")
    def run_account(
        account_id: int,
        ops: Session = Depends(ops_db),
        actor: User = Depends(current_user),
    ):
        row = _load_account(ops, actor, profile, account_id)
        if row is None:
            return fail(1504, "资源不可用")
        task = ensure_task(profile, ops, row, frequency=None, cron=None)
        if task.status == "DISABLED":
            return fail(1001, "任务已停用")
        try:
            return ok(execute_task(profile, ops, task))
        except Exception:
            return fail(2022, "采集失败")

    @router.get("/log/page", operation_id=f"{key}_log_page")
    def log_page(
        pageNo: int = 1,
        pageSize: int = 20,
        accountId: int | None = None,
        ops: Session = Depends(ops_db),
        actor: User = Depends(current_user),
    ):
        from app.collect import log_vo
        from app.corp import count_of

        page_no, size = page_args(pageNo, pageSize)
        tenant_id = tenant_of(actor)
        task_rows = ops.scalars(
            select(CollectTask).where(
                CollectTask.deleted == 0,
                CollectTask.tenant_id == tenant_id,
                CollectTask.platform_type == profile.platform_type,
                CollectTask.method == "INTERNAL",
                CollectTask.source == profile.source,
            )
        ).all()
        task_ids = [row.id for row in task_rows]
        if not task_ids:
            return paged([], 0, page_no, size)
        stmt = select(CollectLog).where(CollectLog.deleted == 0, CollectLog.task_id.in_(task_ids))
        if accountId:
            stmt = stmt.where(CollectLog.account_id == accountId)
        total = count_of(ops, stmt)
        rows = ops.scalars(stmt.order_by(CollectLog.id.desc()).offset((page_no - 1) * size).limit(size)).all()
        tasks = {row.id: row for row in task_rows}
        payload = []
        for row in rows:
            item = log_vo(ops, row, tasks)
            item["statusLabel"] = status_label(row.status)
            payload.append(item)
        return paged(payload, total, page_no, size)

    return router
