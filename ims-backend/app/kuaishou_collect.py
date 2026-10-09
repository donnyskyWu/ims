"""快手内部账号采集。调度、绑定、幂等写入走 internal_collect，这里只登记平台。"""

from __future__ import annotations

from app.collector_client import kuaishou_follower_stats, kuaishou_internal_videos
from app.internal_collect import (
    PlatformProfile,
    build_router,
    credential_mask,
    execute_task,
    health_label,
    import_bind,
    initial_next_run,
    probe_account,
    register,
    start_scheduler,
    tick_platform,
)
from app.ops_models import KuaishouFollowerDaily, KuaishouVideo, KuaishouVideoSnapshot

PROFILE = PlatformProfile(
    key="kuaishou",
    platform_type="KUAISHOU",
    source="KUAISHOU_OPEN_API",
    data_type="KUAISHOU_VIDEO_LIST",
    cred_prefix="cred_ks_",
    task_suffix="快手作品",
    missing_member_error="统一任务没有可采集的快手账号",
    video_model=KuaishouVideo,
    snapshot_model=KuaishouVideoSnapshot,
    fetch_videos=kuaishou_internal_videos,
    import_platform="kuaishou",
    fetch_follower_stats=kuaishou_follower_stats,
    follower_daily_model=KuaishouFollowerDaily,
)
register(PROFILE)
router = build_router(PROFILE)


def execute_kuaishou_task(ops, task):
    return execute_task(PROFILE, ops, task)


def import_kuaishou_bind(ops, row, actor):
    return import_bind(PROFILE, ops, row, actor)


def probe_kuaishou(ops, row):
    return probe_account(PROFILE, ops, row)


def tick_due(now=None) -> int:
    return tick_platform(PROFILE, now)


__all__ = [
    "PROFILE",
    "credential_mask",
    "execute_kuaishou_task",
    "health_label",
    "import_kuaishou_bind",
    "initial_next_run",
    "probe_kuaishou",
    "router",
    "start_scheduler",
    "tick_due",
]
