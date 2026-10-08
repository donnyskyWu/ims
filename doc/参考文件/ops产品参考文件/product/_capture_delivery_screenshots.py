# -*- coding: utf-8 -*-
"""Capture OPS delivery screenshots at localhost:5777 (logged-in session)."""
from __future__ import annotations

import shutil
import sys
import time
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("playwright not installed; pip install playwright && playwright install chromium")
    sys.exit(1)

BASE = "http://127.0.0.1:5777"
ROOT = Path(__file__).resolve().parent
OUT_DIRS = [ROOT / "manual-screenshots", ROOT / "delivery-screenshots"]

# Main walkthrough from manual-screenshots/README.md
ROUTES: list[tuple[str, str, str | None]] = [
    ("01-login.png", "/auth/login", "欢迎回来"),
    ("02-home-welcome.png", "/welcome", "开始您一天的工作"),
    ("03-ops-sidebar.png", "/ops/dashboard", "首页仪表盘"),
    ("04-dashboard.png", "/ops/dashboard", "首页仪表盘"),
    ("05-plan.png", "/ops/production/plan", "计划管理"),
    ("06-task.png", "/ops/production/task", "我的任务"),
    ("07-content.png", "/ops/production/content", "内容管理"),
    ("08-content-review.png", "/ops/production/content/review", "内容审核"),
    ("09-ip-group.png", "/ops/operations/ip-group", "IP 组"),
    ("10-internal-account.png", "/ops/internal/internal-account", "平台账号"),
    ("11-monitor-hot-works.png", "/ops/monitor/hot-works", "爆款"),
    ("12-system-param.png", "/ops/system-oa/system-param", "系统参数"),
    ("13-perf-result.png", "/ops/performance/perf-result", "绩效"),
    ("14-account-cost.png", "/ops/finance/account-cost", "账号成本"),
    ("15-data-report.png", "/ops/analysis/data-report", "数据报表"),
    ("16-sop.png", "/ops/production/sop", "SOP"),
    ("17-knowledge.png", "/ops/production/knowledge", "知识库"),
    ("18-layout-template.png", "/ops/production/layout-template", "公推模板"),
    ("19-task-all.png", "/ops/production/task/all", "全部任务"),
    ("20-metric.png", "/ops/analysis/metric", "指标"),
    ("21-custom-query.png", "/ops/analysis/custom-query", "自定义查询"),
    ("22-work-task.png", "/ops/production/work-task", "工作任务"),
    ("23-company.png", "/ops/internal/company", "公司"),
    ("24-realname.png", "/ops/internal/realname", "实名人"),
    ("25-phone.png", "/ops/internal/phone", "手机"),
    ("26-simcard.png", "/ops/internal/simcard", "手机卡"),
]


def wait_ready(page, ms: int = 3500, hint: str | None = None) -> None:
    try:
        page.wait_for_load_state("domcontentloaded", timeout=30000)
    except Exception:
        pass
    if hint:
        try:
            page.get_by_text(hint, exact=False).first.wait_for(state="visible", timeout=20000)
        except Exception:
            pass
    try:
        page.locator(".vben-layout-content, main, [class*='layout-content']").first.wait_for(
            state="visible", timeout=15000
        )
    except Exception:
        pass
    time.sleep(ms / 1000.0)


def login(page) -> None:
    page.goto(f"{BASE}/auth/login", wait_until="domcontentloaded")
    wait_ready(page, 1500)
    if "/auth/login" not in page.url:
        return
    page.get_by_placeholder("请输入用户名").fill("admin")
    page.get_by_placeholder("请输入密码").fill("admin123")
    page.get_by_role("button", name="login").click()
    page.wait_for_url("**/welcome**", timeout=60000)
    wait_ready(page)


def capture(name: str, path: str, hint: str | None, page, ctx_login) -> None:
    if name == "01-login.png":
        fresh = ctx_login.new_page()
        try:
            fresh.goto(f"{BASE}{path}", wait_until="domcontentloaded")
            wait_ready(fresh, hint=hint)
            shot = fresh.screenshot(full_page=False)
        finally:
            fresh.close()
    else:
        page.goto(f"{BASE}{path}", wait_until="domcontentloaded")
        wait_ready(page, hint=hint)
        shot = page.screenshot(full_page=False)
    for d in OUT_DIRS:
        d.mkdir(parents=True, exist_ok=True)
        (d / name).write_bytes(shot)
    print(f"  {name} <- {path}")


def capture_system_param_tabs(page) -> None:
    page.goto(f"{BASE}/ops/system-oa/system-param", wait_until="domcontentloaded")
    wait_ready(page)
    for name in ("12-system-param.png",):
        shot = page.screenshot(full_page=False)
        for d in OUT_DIRS:
            (d / name).write_bytes(shot)
    for tab_label, fname in (
        ("钉钉", "12b-system-param-dingtalk.png"),
        ("内容审核", "12c-system-param-review.png"),
    ):
        tab = page.get_by_role("tab", name=tab_label)
        if tab.count():
            tab.first.click()
            wait_ready(page, 1200)
        shot = page.screenshot(full_page=False)
        for d in OUT_DIRS:
            (d / fname).write_bytes(shot)
        print(f"  {fname} (tab {tab_label})")


def main() -> int:
    for d in OUT_DIRS:
        d.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        ctx_login = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        login(page)
        for name, path, hint in ROUTES:
            if name.startswith("12-system-param"):
                continue
            capture(name, path, hint, page, ctx_login)
        capture_system_param_tabs(page)
        browser.close()

    # keep 05b if present from prior capture
    src_05b = ROOT / "manual-screenshots" / "05b-plan-create.png"
    if src_05b.exists():
        for d in OUT_DIRS:
            dst = d / "05b-plan-create.png"
            try:
                shutil.copy2(src_05b, dst)
            except OSError as exc:
                print(f"  skip copy 05b -> {dst}: {exc}")

    count = len(list(OUT_DIRS[1].glob("*.png")))
    print(f"delivery-screenshots PNG count: {count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
