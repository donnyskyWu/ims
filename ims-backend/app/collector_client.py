"""unify-collector HTTP 客户端。

与本地桩、`scripts/collector_smoke_kuaishou.py`、`scripts/collector_smoke_douyin.py`、
`scripts/collector_smoke_wechat_channels.py` 使用同一路径：

- `POST /api/v1/accounts/import`
- `GET  /api/v1/accounts/health?account_id=`
- `GET  /api/v1/internal/douyin/accounts/{account_id}/videos`
- `GET  /api/v1/internal/douyin/accounts/{account_id}/followers`
- `GET  /api/v1/internal/douyin/follower-stats?account_id=`
- `GET  /api/v1/internal/kuaishou/video-list?account_id=`
- `GET  /api/v1/internal/kuaishou/follower-stats?account_id=`
- `GET  /api/v1/internal/wechat-channels/video-list?account_id=`
- `GET  /api/v1/internal/wechat-channels/follower-stats?account_id=`

鉴权头 `Authorization: Bearer <IMS_COLLECTOR_TOKEN>`，地址 `IMS_COLLECTOR_BASE_URL`。
业务错误可以是 HTTP 200，正文 `message` 为「Cookie 已失效」或「浏览器引擎不可用」。
上游若用 4xx/5xx 带同样文案，这里只归类，不向调用方抛未捕获异常。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from urllib.parse import quote

import httpx

IMPORT_PATH = "/api/v1/accounts/import"
HEALTH_PATH = "/api/v1/accounts/health"
DOUYIN_VIDEOS_PATH = "/api/v1/internal/douyin/accounts/{account_id}/videos"
DOUYIN_FOLLOWERS_PATH = "/api/v1/internal/douyin/accounts/{account_id}/followers"
DOUYIN_FOLLOWER_STATS_PATH = "/api/v1/internal/douyin/follower-stats"
KUAISHOU_VIDEO_LIST_PATH = "/api/v1/internal/kuaishou/video-list"
KUAISHOU_FOLLOWER_STATS_PATH = "/api/v1/internal/kuaishou/follower-stats"
WECHAT_CHANNELS_VIDEO_LIST_PATH = "/api/v1/internal/wechat-channels/video-list"
WECHAT_CHANNELS_FOLLOWER_STATS_PATH = "/api/v1/internal/wechat-channels/follower-stats"
# 旧名保留给仍按常量引用视频列表的调用；值已是真实 GET 路径。
KUAISHOU_VIDEOS_PATH = KUAISHOU_VIDEO_LIST_PATH

MSG_COOKIE = "Cookie 已失效"
MSG_ENGINE = "浏览器引擎不可用"
MSG_FOLLOWER = "粉丝统计失败"
CODE_COOKIE = 40101
CODE_ENGINE = 50301
CODE_FOLLOWER = 1002


@dataclass
class CollectorCall:
    kind: str
    message: str
    videos: list[dict] = field(default_factory=list)
    followers: list[dict] = field(default_factory=list)
    follower_count: int | None = None
    following_count: int | None = None
    new_follower_count: int | None = None
    stat_date: str = ""
    collector_account_id: str = ""
    http_status: int = 0


def base_url() -> str:
    return os.environ.get("IMS_COLLECTOR_BASE_URL", "").strip().rstrip("/")


def token() -> str:
    return os.environ.get("IMS_COLLECTOR_TOKEN", "").strip()


def classify(message: str, code: int | None = None) -> str:
    text = message or ""
    if MSG_COOKIE in text or code == CODE_COOKIE:
        return "cookie"
    if MSG_ENGINE in text or code == CODE_ENGINE:
        return "engine"
    return "error"


def _headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    secret = token()
    if secret:
        headers["Authorization"] = f"Bearer {secret}"
    return headers


def _read_body(response: httpx.Response) -> dict:
    try:
        data = response.json()
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _optional_int(data: dict, *names: str) -> int | None:
    for name in names:
        if name in data and data[name] is not None:
            try:
                return int(data[name])
            except (TypeError, ValueError):
                return None
    nested = data.get("stats")
    if isinstance(nested, dict):
        return _optional_int(nested, *names)
    return None


def _dict_list(data: dict, *names: str) -> list[dict]:
    for name in names:
        value = data.get(name)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def _account_path(template: str, account_id: str) -> str:
    return template.format(account_id=quote(account_id or "", safe=""))


def _call(method: str, path: str, *, json_body: dict | None = None, params: dict | None = None) -> CollectorCall:
    root = base_url()
    if not root:
        return CollectorCall(kind="error", message="未配置 Collector 地址（IMS_COLLECTOR_BASE_URL）")
    url = f"{root}{path}"
    try:
        with httpx.Client(timeout=8.0) as client:
            response = client.request(method, url, headers=_headers(), json=json_body, params=params)
    except httpx.HTTPError:
        return CollectorCall(kind="error", message="无法连接 Collector")
    body = _read_body(response)
    message = str(body.get("message") or body.get("msg") or "")
    code = body.get("code")
    code_int = code if isinstance(code, int) else None
    data = body.get("data") if isinstance(body.get("data"), dict) else {}
    kind = "ok"
    if code_int not in (None, 0) or response.status_code >= 400:
        kind = classify(message, code_int)
        if kind == "error" and not message:
            message = f"采集失败（HTTP {response.status_code}）"
    if kind != "ok":
        data = {}
    return CollectorCall(
        kind=kind if kind != "ok" or response.status_code < 400 else "error",
        message=message or ("ok" if kind == "ok" else "采集失败"),
        videos=_dict_list(data, "videos"),
        followers=_dict_list(data, "followers"),
        follower_count=_optional_int(
            data,
            "follower_count",
            "followerCount",
            "fans_count",
            "fansCount",
            "total_followers",
            "totalFollowers",
        ),
        following_count=_optional_int(data, "following_count", "followingCount"),
        new_follower_count=_optional_int(
            data,
            "new_follower_count",
            "newFollowerCount",
            "new_followers_today",
            "newFollowersToday",
        ),
        stat_date=str(data.get("stat_date") or data.get("statDate") or "")[:10],
        collector_account_id=str(data.get("collector_account_id") or data.get("collectorAccountId") or ""),
        http_status=response.status_code,
    )


def import_account(
    *,
    platform_account_id: str,
    credential_ref: str,
    cookie: str,
    auth_token: str,
    platform: str = "kuaishou",
) -> CollectorCall:
    return _call(
        "POST",
        IMPORT_PATH,
        json_body={
            "platform": platform,
            "platform_account_id": platform_account_id,
            "credential_ref": credential_ref,
            "cookie": cookie,
            "auth_token": auth_token,
        },
    )


def account_health(collector_account_id: str) -> CollectorCall:
    return _call("GET", HEALTH_PATH, params={"account_id": collector_account_id})


def kuaishou_internal_videos(*, account_id: str) -> CollectorCall:
    return _call("GET", KUAISHOU_VIDEO_LIST_PATH, params={"account_id": account_id})


def kuaishou_follower_stats(*, account_id: str) -> CollectorCall:
    return _call("GET", KUAISHOU_FOLLOWER_STATS_PATH, params={"account_id": account_id})


def douyin_internal_videos(*, account_id: str) -> CollectorCall:
    return _call("GET", _account_path(DOUYIN_VIDEOS_PATH, account_id))


def douyin_followers(*, account_id: str) -> CollectorCall:
    return _call("GET", _account_path(DOUYIN_FOLLOWERS_PATH, account_id))


def douyin_follower_stats(*, account_id: str) -> CollectorCall:
    return _call("GET", DOUYIN_FOLLOWER_STATS_PATH, params={"account_id": account_id})


def _normalize_wechat_video(item: dict) -> dict:
    """把视频号 video-list 字段收成公共写入形状。

    OpenAPI 作品主键是 export_id，播放是 read_count，转发是 forward_count，
    发布时间是 create_time，时长是 duration。
    """
    video_id = str(
        item.get("video_id")
        or item.get("videoId")
        or item.get("export_id")
        or item.get("exportId")
        or item.get("object_id")
        or item.get("objectId")
        or ""
    ).strip()
    out = dict(item)
    if video_id:
        out["video_id"] = video_id
    if out.get("play_count") is None and out.get("playCount") is None:
        if "read_count" in out or "readCount" in out:
            out["play_count"] = out.get("read_count") if "read_count" in out else out.get("readCount")
    if out.get("share_count") is None and out.get("shareCount") is None:
        if "forward_count" in out or "forwardCount" in out:
            out["share_count"] = out.get("forward_count") if "forward_count" in out else out.get("forwardCount")
    if not (out.get("publish_time") or out.get("publishTime")):
        created = out.get("create_time") or out.get("createTime")
        if created:
            out["publish_time"] = created
    if out.get("duration_sec") is None and out.get("durationSec") is None and out.get("duration") is not None:
        out["duration_sec"] = out.get("duration")
    return out


def wechat_channels_internal_videos(*, account_id: str) -> CollectorCall:
    call = _call("GET", WECHAT_CHANNELS_VIDEO_LIST_PATH, params={"account_id": account_id})
    call.videos = [_normalize_wechat_video(item) for item in call.videos]
    return call


def wechat_channels_follower_stats(*, account_id: str) -> CollectorCall:
    return _call("GET", WECHAT_CHANNELS_FOLLOWER_STATS_PATH, params={"account_id": account_id})
