# -*- coding: utf-8 -*-
"""Capture 05b-plan-create.png only (plan create dialog)."""
from __future__ import annotations

import shutil
import sys
import tempfile
import time
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("playwright not installed")
    sys.exit(1)

BASE = "http://127.0.0.1:5777"
ROOT = Path(__file__).resolve().parent
OUT_DIRS = [ROOT / "manual-screenshots", ROOT / "delivery-screenshots"]
NAME = "05b-plan-create.png"


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
    loc = page.get_by_text("神鱼体育", exact=False)
    if loc.count():
        try:
            loc.first.click()
            time.sleep(0.5)
        except Exception:
            pass
    page.get_by_placeholder("请输入用户名").fill("admin")
    page.get_by_placeholder("请输入密码").fill("admin123")
    page.get_by_role("button", name="login").click()
    page.wait_for_url("**/welcome**", timeout=60000)
    wait_ready(page)


def write_shot(data: bytes) -> None:
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
        tf.write(data)
        tmp = Path(tf.name)
    primary = OUT_DIRS[0] / NAME
    primary.parent.mkdir(parents=True, exist_ok=True)
    if primary.exists():
        primary.unlink()
    shutil.move(str(tmp), str(primary))
    print(f"  wrote {primary}")
    for d in OUT_DIRS[1:]:
        d.mkdir(parents=True, exist_ok=True)
        dst = d / NAME
        if dst.exists():
            dst.unlink()
        shutil.copy2(primary, dst)
        print(f"  wrote {dst}")


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        login(page)
        page.goto(f"{BASE}/ops/production/plan", wait_until="domcontentloaded")
        wait_ready(page, hint="计划管理")
        opened = False
        for label in ("新增计划", "新增", "创建计划", "新建"):
            btn = page.get_by_role("button", name=label)
            if btn.count():
                btn.first.click()
                opened = True
                break
        if not opened:
            link = page.get_by_text("新增计划", exact=False)
            if link.count():
                link.first.click()
                opened = True
        if not opened:
            print("Could not find add-plan control")
            browser.close()
            return 3
        wait_ready(page, 2000)
        try:
            page.locator(".el-dialog, [role='dialog'], .ant-modal").first.wait_for(
                state="visible", timeout=10000
            )
        except Exception:
            pass
        shot = page.screenshot(full_page=False)
        browser.close()

    write_shot(shot)
    print("05b capture OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
