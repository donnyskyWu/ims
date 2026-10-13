"""侧栏图标名。只补空图标，不覆盖已有值。名字与原型 Ico 图标集一致。"""
from __future__ import annotations

# 有路由的菜单按 path 赋值。原型 catalog 里同名页面的 icon。
PATH_ICONS = {
    "/ims/workbench": "star",
    "/ims/auth/org": "people",
    "/ims/auth/position": "shield",
    "/ims/system/user": "user",
    "/ims/system/role": "shield",
    "/ims/system/menu": "doc",
    "/ims/system/dict": "db",
    "/ims/system/param": "spark",
    "/ims/system/log": "doc",
    "/ims/system/notify": "bell",
    "/ims/system/tenant": "shield",
    "/ims/flow/task": "flow",
    "/ims/flow/board": "chart",
    "/ims/flow/template": "doc",
    "/ims/flow/timeout": "clock",
    "/ims/corp/resource/company": "db",
    "/ims/corp/resource/realname": "user",
    "/ims/corp/resource/sim-card": "phone",
    "/ims/corp/resource/certificate": "shield",
    "/ims/corp/account/wechat-official": "doc",
    "/ims/corp/account/wechat-channels": "play",
    "/ims/corp/account/douyin": "play",
    "/ims/corp/account/kuaishou": "play",
    "/ims/corp/account/xiaohongshu": "doc",
    "/ims/corp/account/personal": "user",
    "/ims/live/sessions": "play",
    "/ims/live/alarm": "bell",
    "/ims/live/ledger": "doc",
}

# 没有路由的目录（如「资源管理」）按名称赋值。
NAME_ICONS = {
    "资源管理": "id",
    "账号管理": "user",
    "直播管理": "play",
}


def icon_for(path: str | None, name: str | None) -> str | None:
    if path and path in PATH_ICONS:
        return PATH_ICONS[path]
    if name and name in NAME_ICONS:
        return NAME_ICONS[name]
    return None
