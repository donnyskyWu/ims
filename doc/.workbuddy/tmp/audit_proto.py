# -*- coding: utf-8 -*-
"""原型交互覆盖度静态审计：按页面函数切块统计交互要素 + 死按钮探测。"""
import re, io, sys, json, collections

SRC = r"D:/self/sy/文档/IMS系统产品/UI原型/IMS-完整系统-UI原型.html"
src = io.open(SRC, encoding="utf-8").read()
lines = src.split("\n")

# 1) 页面函数边界
pats = [(i, m.group(1)) for i, l in enumerate(lines) for m in [re.match(r"^PAGES\.([A-Za-z0-9_]+) *= *function", l)] if m]
pats.sort()
blocks = []
for idx, (ln, name) in enumerate(pats):
    end = pats[idx+1][0] if idx+1 < len(pats) else len(lines)
    blocks.append((name, ln, end))

def stat_seg(a, b):
    seg = "\n".join(lines[a:b])
    return {
        "loc": b - a,
        "btn": len(re.findall(r"<button", seg)),
        "onclick": len(re.findall(r"onclick=", seg)),
        "setTab": len(re.findall(r"setTab\(", seg)),
        "drawer": len(re.findall(r"[Oo]penDrawer\(|Drawer\b", seg)),
        "select": len(re.findall(r"<select", seg)),
        "input": len(re.findall(r"<input", seg)),
        "go": len(re.findall(r"\bgo\(", seg)),
        "toast": len(re.findall(r"toast\(", seg)),
        "todo": len(re.findall(r"TODO|待补|未实现|占位|placeholder-only", seg)),
    }

print("| 页面 | 行数 | button | onclick | setTab | drawer | select | input | go | TODO |")
print("|---|---|---|---|---|---|---|---|---|---|")
rows = []
for name, a, b in blocks:
    s = stat_seg(a, b)
    rows.append((name, s))
    print("| {name} | {loc} | {btn} | {onclick} | {setTab} | {drawer} | {select} | {input} | {go} | {todo} |".format(name=name, **s))

# 2) 全量 onclick 目标 → 是否已定义
onclicks = re.findall(r'onclick="([^"]*)"', src)
called = set()
for oc in onclicks:
    for f in re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", oc):
        called.add(f)
    for f in re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\(\)", oc):
        called.add(f)
defined = set(re.findall(r"function\s+([A-Za-z0-9_]+)", src))
defined |= set(re.findall(r"(?:const|let|var)\s+([A-Za-z0-9_]+)\s*=\s*function", src))
defined |= set(re.findall(r"(?:const|let|var)\s+([A-Za-z0-9_]+)\s*=\s*\(", src))
builtins = {"go","setTab","toast","openDrawer","closeDrawer","confirm","alert","console","JSON","parseInt","parseFloat","Number","String","Boolean","Math","Object","Array","setTimeout","encodeURIComponent","decodeURIComponent","return","if","for","while","switch","new","typeof","document","window","event"}
missing = sorted(called - defined - builtins)

print("\n\n=== onclick 调用但未定义（疑似死按钮）: %d ===\n" % len(missing))
print(", ".join(missing) if missing else "(none)")

# 3) onclick 为空的按钮
empty = [oc for oc in onclicks if not oc.strip() or oc.strip() in ("return false", "void(0)", "return", "javascript:void(0)")]
print("\n=== onclick 空/无效: %d ===\n" % len(empty))

# 4) 页面出现次数（导航可达）
print("\n=== 模块键出现次数（GROUPS/MODS/路由引用） ===")
mods = re.findall(r"^\s{2}([A-Za-z0-9_]+):\s*\{", src, re.M)
cnt = collections.Counter()
for m in set(mods):
    cnt[m] = len(re.findall(r"\b%s\b" % re.escape(m), src))
for m, c in sorted(cnt.items(), key=lambda x: x[1])[:25]:
    print("%-22s %d" % (m, c))
