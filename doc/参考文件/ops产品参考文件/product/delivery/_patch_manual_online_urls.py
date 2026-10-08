# -*- coding: utf-8 -*-
"""Patch delivery manuals: add online URL lines after Hash routes."""
from __future__ import annotations

import re
from pathlib import Path

DELIVERY = Path(__file__).resolve().parent
BASE = "https://saas.shenyu.com/#"
ONLINE_LINE = "**线上完整 URL**：`{url}`"

# **URL**：`/ops/...`  or **入口**：`/ops/...`
PAT = re.compile(r"^(\*\*(?:URL|入口)\*\*：)(`(/ops[^`]+)`)\s*$")


def patch_file(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    out_lines: list[str] = []
    n = 0
    for line in text.splitlines():
        m = PAT.match(line)
        if m:
            prefix, route = m.group(1), m.group(3)
            out_lines.append(f"**Hash 路由**：`{route}`")
            out_lines.append("")
            out_lines.append(ONLINE_LINE.format(url=f"{BASE}{route}"))
            n += 1
            continue
        # appendix table | `/ops/...` | -> add online column note once - skip
        out_lines.append(line)
    if n:
        path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    return n


def main() -> None:
    total = 0
    for md in sorted(DELIVERY.glob("*.md")):
        if md.name.startswith("_") or md.name.startswith("ROUTE"):
            continue
        c = patch_file(md)
        if c:
            print(f"{md.name}: {c}")
            total += c
    print(f"patched {total} URL lines")


if __name__ == "__main__":
    main()
