# -*- coding: utf-8 -*-
"""查询构建器条件行：占位 toast → 真实增删。"""
import io, shutil, os

SRC = r"D:/self/sy/文档/IMS系统产品/UI原型/IMS-完整系统-UI原型.html"
BAK = r"D:/self/sy/文档/IMS系统产品/.workbuddy/backup-qb-20261005/IMS-完整系统-UI原型.html"
os.makedirs(os.path.dirname(BAK), exist_ok=True)
shutil.copy2(SRC, BAK)
s = io.open(SRC, encoding="utf-8").read()

reps = [
    (r"""onclick="toast(\'已移除\',\'info\')" """.strip(), r"""onclick="qbDelCond(this)\""""),
    (r"""onclick="toast(\'+ 添加条件\',\'info\')" """.strip(), r"""onclick="qbAddCond(this)\""""),
]

pairs = [
    ("onclick=\"toast(\\'已移除\\',\\'info\\')\"", "onclick=\"qbDelCond(this)\""),
    ("onclick=\"toast(\\'+ 添加条件\\',\\'info\\')\"", "onclick=\"qbAddCond(this)\""),
    ("onclick=\"toast(\\'已选字段 ' + f.name + '\\',\\'success\\')\"",
     "onclick=\"qbPickField(this,\\'' + f.name + '\\',\\'' + f.label + '\\')\""),
    ("onclick=\"toast(\\'已选字段 ' + p[0] + '\\',\\'success\\')\"",
     "onclick=\"qbPickField(this,\\'' + p[0] + '\\',\\'' + p[1] + '\\')\""),
]

total = 0
for old, new in pairs:
    n = s.count(old)
    if n:
        s = s.replace(old, new)
        total += n
    print("replaced %2d  %s" % (n, old[:70]))

io.open(SRC, "w", encoding="utf-8").write(s)
print("TOTAL", total, "-> backup:", BAK)
