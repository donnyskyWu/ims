"""视频号内部账号采集。作品与粉丝日统计共用 internal_collect 的同一条定时器。"""

from __future__ import annotations

from app.collector_client import wechat_channels_follower_stats, wechat_channels_internal_videos
from app.internal_collect import (
    PlatformProfile,
    build_router,
    execute_task,
    import_bind,
    probe_account,
    register,
    tick_platform,
)
from app.ops_models import WechatFollowerDaily, WechatVideoSnapshot, WechatVideoWork

PROFILE = PlatformProfile(
    key="wechat-channels",
    platform_type="WECHAT_CHANNELS",
    source="WECHAT_CHANNELS_API",
    data_type="WECHAT_VIDEO_LIST",
    cred_prefix="cred_wx_",
    task_suffix="视频号作品",
    missing_member_error="统一任务没有可采集的视频号账号",
    video_model=WechatVideoWork,
    snapshot_model=WechatVideoSnapshot,
    fetch_videos=wechat_channels_internal_videos,
    import_platform="wechat_channels",
    fetch_follower_stats=wechat_channels_follower_stats,
    follower_daily_model=WechatFollowerDaily,
)
register(PROFILE)
router = build_router(PROFILE)


def execute_wechat_channels_task(ops, task):
    return execute_task(PROFILE, ops, task)


def import_wechat_channels_bind(ops, row, actor):
    return import_bind(PROFILE, ops, row, actor)


def probe_wechat_channels(ops, row):
    return probe_account(PROFILE, ops, row)


def tick_due(now=None) -> int:
    return tick_platform(PROFILE, now)


def is_internal_account(row) -> bool:
    return bool(row and (row.credential_ref or "").startswith(PROFILE.cred_prefix))
