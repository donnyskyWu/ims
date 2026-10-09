"""抖音内部账号作品采集。与快手共用 internal_collect，只换 Collector 接口和 oa_douyin_* 表。"""

from __future__ import annotations

from app.collector_client import douyin_internal_videos
from app.internal_collect import (
    PlatformProfile,
    build_router,
    execute_task,
    import_bind,
    probe_account,
    register,
    tick_platform,
)
from app.ops_models import DouyinVideo, DouyinVideoSnapshot

PROFILE = PlatformProfile(
    key="douyin",
    platform_type="DOUYIN",
    source="DOUYIN_OPEN_API",
    data_type="DOUYIN_VIDEO_LIST",
    cred_prefix="cred_dy_",
    task_suffix="抖音作品",
    missing_member_error="统一任务没有可采集的抖音账号",
    video_model=DouyinVideo,
    snapshot_model=DouyinVideoSnapshot,
    fetch_videos=douyin_internal_videos,
    import_platform="douyin",
)
register(PROFILE)
router = build_router(PROFILE)


def execute_douyin_task(ops, task):
    return execute_task(PROFILE, ops, task)


def import_douyin_bind(ops, row, actor):
    return import_bind(PROFILE, ops, row, actor)


def probe_douyin(ops, row):
    return probe_account(PROFILE, ops, row)


def tick_due(now=None) -> int:
    return tick_platform(PROFILE, now)


def is_internal_account(row) -> bool:
    return bool(row and (row.credential_ref or "").startswith(PROFILE.cred_prefix))
