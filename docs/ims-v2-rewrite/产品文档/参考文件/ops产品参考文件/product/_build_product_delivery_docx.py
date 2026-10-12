# -*- coding: utf-8 -*-
"""Build product delivery docx: full manual + role manuals + optional PDF hint."""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DELIVERY = ROOT / "delivery"
SHOT = ROOT / "delivery-screenshots"
FULL_MD = ROOT / "产品使用操作手册.md"

ROLE_SPECS: list[tuple[str, Path, dict[str, list[tuple[str, str]]]]] = [
    (
        "运营主管操作手册.docx",
        DELIVERY / "运营主管操作手册.md",
        {
            "2. IP 组维护": [
                ("09-ip-group.png", "图 2-1 IP 组管理"),
                ("A01-ip-group-tree.png", "图 2-2 IP 组树"),
            ],
            "3. SOP 流程配置": [("16-sop.png", "图 3-1 SOP 管理")],
            "4. 计划任务（计划管理）": [
                ("05-plan.png", "图 4-1 计划管理"),
                ("05b-plan-create.png", "图 4-2 新建计划"),
            ],
            "5. 任务登记管理（工作任务矩阵）": [
                ("22-work-task.png", "图 5-1 工作任务管理"),
                ("B01-manager-work-task-matrix.png", "图 5-2 任务管理矩阵"),
            ],
            "6. 内容审核": [
                ("08-content-review.png", "图 6-1 内容审核"),
                ("12c-system-param-review.png", "图 6-2 审核系统参数"),
            ],
            "7. 数据报表查看": [("15-data-report.png", "图 7-1 数据报表")],
            "8. 自定义查询": [("21-custom-query.png", "图 8-1 自定义查询")],
            "9. 指标管理": [("20-metric.png", "图 9-1 指标管理")],
        },
    ),
    (
        "运营操作手册.docx",
        DELIVERY / "运营操作手册.md",
        {
            "2. 账号信息维护": [("10-internal-account.png", "图 2-1 平台账号")],
            "4. 账号数据查看": [("11-monitor-hot-works.png", "图 4-1 监测/分析代表页")],
            "5. 任务登记（IP 组长）": [
                ("A06-work-task-register.png", "图 5-1 任务登记"),
                ("A07-work-task-register-loaded.png", "图 5-2 登记页"),
            ],
            "6. 任务执行": [
                ("06-task.png", "图 6-1 我的任务"),
                ("A11-task-execute.png", "图 6-2 任务执行"),
            ],
        },
    ),
    (
        "编辑操作手册.docx",
        DELIVERY / "编辑操作手册.md",
        {
            "3. 任务执行": [
                ("06-task.png", "图 3-1 我的任务"),
                ("A11-task-execute.png", "图 3-2 执行页"),
            ],
            "4. 内容编辑与排版": [
                ("07-content.png", "图 4-1 内容管理"),
                ("A13-content-create-drawer.png", "图 4-2 内容创作"),
            ],
            "6. 公推模板与知识库": [
                ("18-layout-template.png", "图 6-1 公推模板"),
                ("17-knowledge.png", "图 6-2 知识库"),
            ],
        },
    ),
    (
        "账号管理员操作手册.docx",
        DELIVERY / "账号管理员操作手册.md",
        {
            "2. 平台账号管理与维护": [("10-internal-account.png", "图 2-1 平台账号")],
            "3. 公司管理": [("23-company.png", "图 3-1 公司管理")],
            "4. 实名人管理": [("24-realname.png", "图 4-1 实名人")],
            "5. 手机管理": [("25-phone.png", "图 5-1 手机管理")],
            "6. 手机卡管理": [("26-simcard.png", "图 6-1 手机卡管理")],
        },
    ),
    (
        "财务人员操作手册.docx",
        DELIVERY / "财务人员操作手册.md",
        {
            "2. 账号成本管理维护": [("14-account-cost.png", "图 2-1 账号成本管理")],
        },
    ),
    (
        "通用入门与权限说明.docx",
        DELIVERY / "通用入门与权限说明.md",
        {
            "1. 登录与租户": [
                ("01-login.png", "图 1-1 登录"),
                ("03-ops-sidebar.png", "图 1-2 侧栏"),
            ],
            "2. 菜单与路由": [("04-dashboard.png", "图 2-1 首页")],
        },
    ),
    (
        "端到端业务流程手册.docx",
        DELIVERY / "端到端业务流程手册.md",
        {
            "2. 阶段 A：基础配置（IP 组 + SOP）": [
                ("A01-ip-group-tree.png", "图 2-1 IP 组树"),
                ("16-sop.png", "图 2-2 SOP"),
            ],
            "3. 阶段 B：驱动任务（计划 或 工作任务登记）": [
                ("05-plan.png", "图 3-1 计划"),
                ("22-work-task.png", "图 3-2 工作任务"),
                ("B01-manager-work-task-matrix.png", "图 3-3 矩阵"),
            ],
            "4. 阶段 C：任务执行与内容生产": [
                ("06-task.png", "图 4-1 我的任务"),
                ("A13-content-create-drawer.png", "图 4-2 内容创作"),
            ],
            "5. 阶段 D：内容审核与发布": [
                ("12c-system-param-review.png", "图 5-1 审核参数"),
                ("08-content-review.png", "图 5-2 内容审核"),
            ],
            "6. 阶段 E：报表与复盘": [("15-data-report.png", "图 6-1 数据报表")],
        },
    ),
    (
        "系统配置与权限管理手册.docx",
        DELIVERY / "系统配置与权限管理手册.md",
        {
            "2. 系统参数（OA）": [
                ("12-system-param.png", "图 2-1 系统参数"),
                ("12b-system-param-dingtalk.png", "图 2-2 钉钉"),
                ("12c-system-param-review.png", "图 2-3 内容审核"),
            ],
        },
    ),
]


def build_full_manual():
    """Reuse existing converter; copy to delivery folder."""
    import _build_manual_docx as bm

    bm.SHOT_DIR = SHOT if SHOT.exists() else bm.SHOT_DIR
    bm.OUT_DOCX = ROOT / "产品使用操作手册.docx"
    bm.convert()
    out = DELIVERY / "汇总产品使用手册.docx"
    shutil.copy2(bm.OUT_DOCX, out)
    print(f"Wrote {out}")


def build_role_manual(out_name: str, md_path: Path, shot_map: dict):
    import _build_manual_docx as bm

    orig_map = bm.SCREENSHOT_MAP
    orig_shot = bm.SHOT_DIR
    orig_md = bm.MD_PATH
    orig_out = bm.OUT_DOCX
    try:
        bm.SCREENSHOT_MAP = shot_map
        bm.SHOT_DIR = SHOT if SHOT.exists() else ROOT / "manual-screenshots"
        bm.MD_PATH = md_path
        bm.OUT_DOCX = DELIVERY / out_name
        bm.convert()
    finally:
        bm.SCREENSHOT_MAP = orig_map
        bm.SHOT_DIR = orig_shot
        bm.MD_PATH = orig_md
        bm.OUT_DOCX = orig_out


def try_pdf(docx_path: Path):
    """Optional: docx2pdf on Windows if installed."""
    try:
        import docx2pdf  # type: ignore

        pdf_path = docx_path.with_suffix(".pdf")
        docx2pdf.convert(str(docx_path), str(pdf_path))
        print(f"Wrote {pdf_path}")
        return True
    except Exception as e:
        print(f"PDF skip ({docx_path.name}): {e}", file=sys.stderr)
        return False


def main():
    DELIVERY.mkdir(parents=True, exist_ok=True)
    if not FULL_MD.exists():
        sys.exit(f"Missing {FULL_MD}")
    build_full_manual()
    for out_name, md_path, shot_map in ROLE_SPECS:
        if not md_path.exists():
            print(f"Skip missing {md_path}")
            continue
        build_role_manual(out_name, md_path, shot_map)
    full = DELIVERY / "汇总产品使用手册.docx"
    if full.exists():
        try_pdf(full)


if __name__ == "__main__":
    main()
