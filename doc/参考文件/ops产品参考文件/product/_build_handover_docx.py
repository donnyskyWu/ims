# -*- coding: utf-8 -*-
"""Build OPS product handover docx from Markdown (三件套)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HANDOVER = ROOT.parent / "delivery" / "product-handover"

SPECS: list[tuple[str, str]] = [
    ("OPS产品交付-需求文档.md", "OPS产品交付-需求文档.docx"),
    ("OPS产品交付-技术文档.md", "OPS产品交付-技术文档.docx"),
    ("OPS产品交付-部署运维手册.md", "OPS产品交付-部署运维手册.docx"),
]


def convert_one(md_name: str, out_name: str) -> None:
    import _build_manual_docx as bm

    md_path = HANDOVER / md_name
    out_path = HANDOVER / out_name
    if not md_path.exists():
        raise FileNotFoundError(md_path)

    orig_md = bm.MD_PATH
    orig_out = bm.OUT_DOCX
    orig_map = bm.SCREENSHOT_MAP
    try:
        bm.MD_PATH = md_path
        bm.OUT_DOCX = out_path
        bm.SCREENSHOT_MAP = {}
        bm.convert()
    finally:
        bm.MD_PATH = orig_md
        bm.OUT_DOCX = orig_out
        bm.SCREENSHOT_MAP = orig_map


def main() -> int:
    HANDOVER.mkdir(parents=True, exist_ok=True)
    for md_name, out_name in SPECS:
        convert_one(md_name, out_name)
    print(f"Done: {len(SPECS)} handover docx in {HANDOVER}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
