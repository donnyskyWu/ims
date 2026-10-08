# -*- coding: utf-8 -*-
"""定位所有纯 toast 占位按钮所属页面，并修正 Tab 提取。"""
import re, io, collections

SRC = r"D:/self/sy/文档/IMS系统产品/UI原型/IMS-完整系统-UI原型.html"
src = io.open(SRC, encoding="utf-8").read()
lines = src.split("\n")

# 页面函数边界（含非 PAGES. 的共享渲染体）
funcs = []
for i, l in enumerate(lines):
    m = re.match(r"^(?:PAGES\.)?([A-Za-z0-9_]+)\s*=\s*function", l) or re.match(r"^function\s+([A-Za-z0-9_]+)", l)
    if m:
        funcs.append((i, m.group(1)))
funcs.sort()
def owner(ln):
    cur = "?"
    for i, n in funcs:
        if i <= ln:
            cur = n
        else:
            break
    return cur

# 1) 全部纯 toast onclick，带页面归属
print("=== 纯 toast 占位按钮（带页面归属） ===")
pure = []
for i, l in enumerate(lines):
    for m in re.finditer(r'onclick="([^"]*)"', l):
        s = m.group(1).strip()
        if re.match(r"^toast\(.*\)\s*;?$", s):
            pure.append((owner(i), i+1, s))
seen = set()
for ow, ln, s in pure:
    key = (ow, re.sub(r"\d+", "#", s))
    if key in seen: continue
    seen.add(key)
    print("  [%s] L%d  %s" % (ow, ln, s[:130]))
print("  合计 %d 处（去重后 %d）" % (len(pure), len(seen)))

# 2) Tab 文案（处理 \' 转义）
print("\n=== Tab 文案（含转义引号） ===")
tl = collections.defaultdict(set)
for m in re.finditer(r"setTab\(\\?'([A-Za-z0-9_]+)\\?',\s*\\?'([^'\\]+)\\?'", src):
    tl[m.group(1)].add(m.group(2))
for k in sorted(tl):
    print("  %-24s %s" % (k, " | ".join(sorted(tl[k]))))

# 3) go() 目标是否存在（导航死链）
print("\n=== go() 目标校验 ===")
mods = set(re.findall(r"^\s{2}([A-Za-z0-9_]+):\s*\{", src, re.M))
gotargets = set(re.findall(r"go\(\\?'([A-Za-z0-9_]+)\\?'", src))
bad = sorted(t for t in gotargets if t not in mods)
print("  go 目标总数 %d，其中 MODS 未定义: %s" % (len(gotargets), ", ".join(bad) if bad else "(none)"))
