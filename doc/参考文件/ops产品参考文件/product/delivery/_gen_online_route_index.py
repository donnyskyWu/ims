# -*- coding: utf-8 -*-
"""Generate ROUTE-线上地址索引.md from docs/delivery/OPS-MENU-ROUTE-INDEX.md."""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SRC = REPO / "docs" / "delivery" / "OPS-MENU-ROUTE-INDEX.md"
OUT = Path(__file__).resolve().parent / "ROUTE-线上地址索引.md"
BASE = "https://saas.shenyu.com/#"

ROW_RE = re.compile(
    r"^\|\s*(\d+)\s*\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|\s*(`/ops[^`]+`|`-`)\s*\|",
)


def main() -> None:
    text = SRC.read_text(encoding="utf-8")
    rows: list[tuple[str, str, str, str]] = []
    for line in text.splitlines():
        m = ROW_RE.match(line.strip())
        if not m:
            continue
        menu_id, name, module, _seed, route = m.groups()
        name = name.strip()
        module = module.strip()
        route = route.strip("`")
        if route == "-":
            continue
        rows.append((menu_id, name, module, route))

    lines = [
        "# OPS 功能 → 线上 Hash 地址索引",
        "",
        "> **更新**：2026-09-20",
        "> **基址**：`https://saas.shenyu.com/#` + Football 嵌套路由（与 seed 菜单一致）",
        "> **路由 SSOT 来源**：[`../../delivery/OPS-MENU-ROUTE-INDEX.md`](../../delivery/OPS-MENU-ROUTE-INDEX.md)",
        "> **本地联调**：`http://localhost:5777` + 同路径（**无** `#`，history 模式）",
        "",
        f"## 统计",
        "",
        f"- 可导航页面条目：**{len(rows)}**（menu_id 6100–6999，不含纯按钮权限行）",
        "",
        "## 全量映射",
        "",
        "| menu_id | 模块 | 功能名称 | Hash 路由 | 线上完整 URL |",
        "| ---: | --- | --- | --- | --- |",
    ]
    for menu_id, name, module, route in rows:
        url = f"{BASE}{route}"
        lines.append(f"| {menu_id} | {module} | {name} | `{route}` | `{url}` |")

    lines.extend(
        [
            "",
            "## 常用快捷（角色手册高频）",
            "",
            "| 功能 | 线上完整 URL |",
            "| --- | --- |",
            f"| 首页仪表盘 | `{BASE}/ops/dashboard` |",
            f"| 计划管理 | `{BASE}/ops/production/plan` |",
            f"| 我的任务 | `{BASE}/ops/production/task` |",
            f"| 内容管理 | `{BASE}/ops/production/content` |",
            f"| 内容审核 | `{BASE}/ops/production/content/review` |",
            f"| IP 组管理 | `{BASE}/ops/operations/ip-group` |",
            f"| 平台账号 | `{BASE}/ops/internal/internal-account` |",
            f"| 手机管理 | `{BASE}/ops/internal/phone` |",
            f"| 系统参数 | `{BASE}/ops/system-oa/system-param` |",
            f"| 账号成本 | `{BASE}/ops/finance/account-cost` |",
            "",
            "## 说明",
            "",
            "1. 隐藏页（如内容编辑 `/ops/production/content/edit`）见 `oa-menu-permission-map.csv` 中 `hide_in_menu=Y`。",
            "2. CSV 扁平路径与 seed 不一致时，**以本表嵌套路由为准**（OPS-MENU-ROUTE-INDEX ⚠️ 列）。",
            "3. Phase 2 **数据采集**菜单可配置隐藏；M10 运维 Out of Scope。",
            "",
        ]
    )
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT} ({len(rows)} routes)")


if __name__ == "__main__":
    main()
