# -*- coding: utf-8 -*-
"""Build 产品使用操作手册.docx from Markdown + screenshots.

Role / topic manuals (五本 + 通用入门 / 端到端 / 系统配置) → docs/product/_build_product_delivery_docx.py
"""
from __future__ import annotations

import re
from io import BytesIO
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor
from PIL import Image

ROOT = Path(__file__).resolve().parent
MD_PATH = ROOT / "产品使用操作手册.md"
SHOT_DIR = ROOT / "manual-screenshots"
OUT_DOCX = ROOT / "产品使用操作手册.docx"

# Insert screenshots after matching heading text (exact ## / ### title after strip)
SCREENSHOT_MAP: dict[str, list[tuple[str, str]]] = {
    "2. 登录与环境": [
        ("01-login.png", "图 2-1 登录页"),
        ("02-home-welcome.png", "图 2-2 登录后欢迎页"),
        ("03-ops-sidebar.png", "图 2-3 侧栏「运营数据」菜单"),
    ],
    "3. 内容生产 · 计划管理": [
        ("05-plan.png", "图 3-1 计划管理列表"),
        ("05b-plan-create.png", "图 3-2 新增计划对话框"),
    ],
    "4. 内容生产 · 我的任务 / 全部任务": [
        ("06-task.png", "图 4-1 我的任务"),
    ],
    "5. 内容生产 · 内容管理": [
        ("07-content.png", "图 5-1 内容管理"),
    ],
    "6. 内容生产 · 内容审核与发布/上架": [
        ("08-content-review.png", "图 6-1 内容审核"),
    ],
    "7.1 IP 组管理": [
        ("09-ip-group.png", "图 7-1 IP 组管理"),
    ],
    "8. 系统参数 · 钉钉通知与审核配置": [
        ("12-system-param.png", "图 8-1 系统参数（基础配置）"),
        ("12b-system-param-dingtalk.png", "图 8-2 系统参数 · 钉钉配置"),
        ("12c-system-param-review.png", "图 8-3 系统参数 · 内容审核"),
    ],
    "11. 账号管理常用页": [
        ("10-internal-account.png", "图 11-1 平台账号管理（代表页）"),
    ],
    "12. 作品监测 / 数据分析常用页": [
        ("11-monitor-hot-works.png", "图 12-1 作品监测 · 爆款作品分析"),
        ("15-data-report.png", "图 12-2 数据分析 · 数据报表"),
    ],
    "13. 绩效核算": [
        ("13-perf-result.png", "图 13-1 绩效结果"),
    ],
    "14. 财务管理": [
        ("14-account-cost.png", "图 14-1 账号成本管理"),
    ],
    "16. 首页与系统管理(OA)": [
        ("04-dashboard.png", "图 16-1 首页仪表盘"),
    ],
}


def set_run_font(run, name="微软雅黑", size_pt=11, bold=False, color=None):
    run.font.name = name
    run._element.rPr.rFonts.set(qn("w:eastAsia"), name)
    run.font.size = Pt(size_pt)
    run.bold = bold
    if color is not None:
        run.font.color.rgb = color


def add_caption(doc: Document, text: str):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(text)
    set_run_font(run, size_pt=9, color=RGBColor(0x66, 0x66, 0x66))
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(12)


def add_image(doc: Document, path: Path, caption: str, max_width_in=6.2):
    if not path.exists() or path.stat().st_size < 10000:
        note = doc.add_paragraph()
        run = note.add_run(f"[截图缺失或无效: {path.name}]")
        set_run_font(run, size_pt=9, color=RGBColor(0xCC, 0x00, 0x00))
        return
    with Image.open(path) as im:
        w, h = im.size
    # Prefer PNG as-is; scale to page width
    width_in = max_width_in
    height_in = width_in * (h / w)
    # Cap height so one screenshot doesn't eat a whole page awkwardly
    if height_in > 7.5:
        height_in = 7.5
        width_in = height_in * (w / h)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    run.add_picture(str(path), width=Inches(width_in))
    add_caption(doc, caption)


def strip_md_inline(text: str) -> str:
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = text.replace("**", "").replace("__", "")
    text = text.replace("`", "")
    return text


def add_paragraph_with_inline(doc: Document, text: str, style=None):
    p = doc.add_paragraph(style=style) if style else doc.add_paragraph()
    # Simple bold / code segments
    parts = re.split(r"(\*\*[^*]+\*\*|`[^`]+`)", text)
    for part in parts:
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            run = p.add_run(part[2:-2])
            set_run_font(run, bold=True)
        elif part.startswith("`") and part.endswith("`"):
            run = p.add_run(part[1:-1])
            set_run_font(run, name="Consolas", size_pt=10)
            run.font.color.rgb = RGBColor(0x33, 0x33, 0x99)
        else:
            # links -> text
            cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", part)
            run = p.add_run(cleaned)
            set_run_font(run)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
    return p


def add_table(doc: Document, rows: list[list[str]]):
    if not rows:
        return
    cols = max(len(r) for r in rows)
    table = doc.add_table(rows=len(rows), cols=cols)
    table.style = "Table Grid"
    for i, row in enumerate(rows):
        for j in range(cols):
            cell = table.rows[i].cells[j]
            cell.text = ""
            p = cell.paragraphs[0]
            val = row[j] if j < len(row) else ""
            run = p.add_run(strip_md_inline(val))
            set_run_font(run, size_pt=9, bold=(i == 0))
            if i == 0:
                shading = cell._element.get_or_add_tcPr()
                # light gray header
                from docx.oxml import OxmlElement

                shd = OxmlElement("w:shd")
                shd.set(qn("w:fill"), "E7EEF7")
                shd.set(qn("w:val"), "clear")
                shading.append(shd)
    doc.add_paragraph()


def maybe_insert_shots(doc: Document, heading_title: str):
    shots = SCREENSHOT_MAP.get(heading_title)
    if not shots:
        return
    for fname, caption in shots:
        add_image(doc, SHOT_DIR / fname, caption)


def convert():
    md = MD_PATH.read_text(encoding="utf-8")
    lines = md.splitlines()

    doc = Document()
    section = doc.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.left_margin = Cm(2.0)
    section.right_margin = Cm(2.0)
    section.top_margin = Cm(1.8)
    section.bottom_margin = Cm(1.8)

    # Styles
    styles = doc.styles
    styles["Normal"].font.name = "微软雅黑"
    styles["Normal"]._element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")
    styles["Normal"].font.size = Pt(11)

    i = 0
    in_code = False
    code_buf: list[str] = []
    table_buf: list[list[str]] = []

    def flush_table():
        nonlocal table_buf
        if table_buf:
            # drop separator rows like |---|
            cleaned = []
            for row in table_buf:
                if all(re.fullmatch(r":?-+:?", c.strip()) for c in row if c.strip()):
                    continue
                cleaned.append(row)
            add_table(doc, cleaned)
            table_buf = []

    def flush_code():
        nonlocal code_buf
        if not code_buf:
            return
        p = doc.add_paragraph()
        run = p.add_run("\n".join(code_buf))
        set_run_font(run, name="Consolas", size_pt=9)
        run.font.color.rgb = RGBColor(0x22, 0x22, 0x22)
        p.paragraph_format.left_indent = Cm(0.4)
        p.paragraph_format.space_after = Pt(8)
        # light background via shading on paragraph is complex; keep monospace
        code_buf = []

    while i < len(lines):
        line = lines[i]

        # code fence
        if line.strip().startswith("```"):
            if in_code:
                flush_code()
                in_code = False
            else:
                flush_table()
                in_code = True
                code_buf = []
            i += 1
            continue

        if in_code:
            code_buf.append(line)
            i += 1
            continue

        # table lines
        if line.strip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            table_buf.append(cells)
            i += 1
            continue
        else:
            flush_table()

        # horizontal rule
        if re.fullmatch(r"-{3,}", line.strip()):
            i += 1
            continue

        # headings
        m = re.match(r"^(#{1,4})\s+(.*)$", line)
        if m:
            level = len(m.group(1))
            title = m.group(2).strip()
            # drop markdown anchors like {#...} if any
            title_plain = strip_md_inline(title)
            style = {
                1: "Heading 1",
                2: "Heading 2",
                3: "Heading 3",
                4: "Heading 4",
            }.get(level, "Heading 4")
            p = doc.add_paragraph(title_plain, style=style)
            for run in p.runs:
                set_run_font(run, size_pt={1: 18, 2: 14, 3: 12, 4: 11}[level], bold=True)
            maybe_insert_shots(doc, title_plain)
            i += 1
            continue

        # blockquote
        if line.startswith(">"):
            text = line.lstrip("> ").strip()
            p = add_paragraph_with_inline(doc, text)
            for run in p.runs:
                run.italic = True
                run.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
            i += 1
            continue

        # list items
        if re.match(r"^(\s*)[-*]\s+", line) or re.match(r"^(\s*)\d+\.\s+", line):
            text = re.sub(r"^(\s*)([-*]|\d+\.)\s+", "", line)
            # Use Word list style lightly as plain indented para (avoid numbering complexity)
            p = add_paragraph_with_inline(doc, "• " + text)
            p.paragraph_format.left_indent = Cm(0.5)
            i += 1
            continue

        # empty
        if not line.strip():
            i += 1
            continue

        add_paragraph_with_inline(doc, line)
        i += 1

    flush_table()
    flush_code()

    # footer note
    note = doc.add_paragraph()
    run = note.add_run(
        "\n—— 截图于本地联调环境（http://127.0.0.1:5777）采集，数据为空属演示环境常态；"
        "账号口令请以实际环境为准，勿将密钥写入手册。"
    )
    set_run_font(run, size_pt=9, color=RGBColor(0x88, 0x88, 0x88))

    doc.save(str(OUT_DOCX))
    print(f"Wrote {OUT_DOCX} ({OUT_DOCX.stat().st_size} bytes)")


if __name__ == "__main__":
    convert()
