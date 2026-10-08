# -*- coding: utf-8 -*-
"""原型交互要素全量清点：Tab / 抽屉 / 死按钮 / 二级三级页入口。"""
import re, io, json, collections

SRC = r"D:/self/sy/文档/IMS系统产品/UI原型/IMS-完整系统-UI原型.html"
src = io.open(SRC, encoding="utf-8").read()
lines = src.split("\n")

# ---- A. Tab 定义（state.tab.<page> = '...'）与 setTab 调用 ----
tab_keys = collections.Counter(re.findall(r"state\.tab\.([A-Za-z0-9_]+)", src))
print("=== A. 页面 Tab 键（state.tab.*）: %d ===" % len(tab_keys))
for k, c in sorted(tab_keys.items()):
    print("  %-22s %d" % (k, c))

# ---- B. Tab 文案（setTab(x,'文案')） ----
tab_labels = collections.defaultdict(set)
for m in re.finditer(r"setTab\('([A-Za-z0-9_]+)',\s*'([^']+)'", src):
    tab_labels[m.group(1)].add(m.group(2))
print("\n=== B. setTab 文案（按页面）: %d 页 ===" % len(tab_labels))
for k in sorted(tab_labels):
    print("  %-22s %s" % (k, " | ".join(sorted(tab_labels[k]))))

# ---- C. 抽屉/弹窗函数清单 ----
drawers = sorted(set(re.findall(r"function\s+([A-Za-z0-9_]*(?:Drawer|Dlg|Dialog|Modal|Sheet))", src)))
print("\n=== C. 抽屉/弹窗函数: %d ===" % len(drawers))
print("  " + ", ".join(drawers))

# ---- D. 死按钮（onclick 调用未定义） ----
onclicks = re.findall(r'onclick="([^"]*)"', src)
called = set()
for oc in onclicks:
    called |= set(re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", oc))
defined = set(re.findall(r"function\s+([A-Za-z0-9_]+)", src))
defined |= set(re.findall(r"(?:const|let|var)\s+([A-Za-z0-9_]+)\s*=\s*(?:function|\()", src))
builtins = set("""go setTab toast openDrawer closeDrawer confirm alert console JSON parseInt parseFloat Number String Boolean Math Object Array setTimeout encodeURIComponent decodeURIComponent return if for while switch new typeof document window event filter function getElementById indexOf remove replace stopPropagation toggle this value checked target valueOf map forEach join push slice some every find sort filter trim split charAt substring toUpperCase toLowerCase classList add classList.toggle closest querySelector querySelectorAll parentNode nextSibling previousSibling children style innerHTML textContent focus blur select click preventDefault stopPropagation""".split())
missing = sorted(called - defined - builtins)
print("\n=== D. onclick 目标未定义（真死按钮）: %d ===" % len(missing))
print("  " + (", ".join(missing) if missing else "(none)"))

# ---- E. 纯 toast 占位 onclick（无 UI 变化） ----
pure_toast = []
for oc in onclicks:
    s = oc.strip()
    if re.match(r"^toast\(.*\)\s*;?$", s):
        pure_toast.append(s[:100])
print("\n=== E. 纯 toast 按钮（仅反馈，无 UI 变化）: %d ===" % len(pure_toast))
cnt = collections.Counter(re.sub(r"\d+", "#", p) for p in pure_toast)
for p, c in cnt.most_common(30):
    print("  %3d  %s" % (c, p))

# ---- F. 行操作（列表页 查看/编辑/删除） ----
rowacts = collections.Counter(re.findall(r"onclick=\"(\w+)\(", src))
print("\n=== F. 高频 onclick 目标 TOP40 ===")
for k, c in rowacts.most_common(40):
    print("  %3d  %s" % (c, k))
