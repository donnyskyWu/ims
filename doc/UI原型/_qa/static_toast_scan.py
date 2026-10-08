# -*- coding: utf-8 -*-
# 静态扫描：toast 占位全量分类（含 onclick 属性内的转义单引号场景）
import re, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

p = r'D:\self\sy\一体化管理\outputs\UI原型\IMS-一体化管理系统-UI原型.html'
s = open(p, encoding='utf-8').read()
lines = s.split('\n')

# 匹配所有 toast(...) 第一个字符串实参（三种形式：'x' / \'x\' / "x"）
pat = re.compile(r"""toast\(\s*(?:\\?'([^\\']*)\\?'|"([^"]*)")""")

hits = []
for i, l in enumerate(lines, 1):
    for m in pat.finditer(l):
        t = m.group(1) if m.group(1) is not None else m.group(2)
        if t and ('原型' in t or '示意' in t or '占位' in t):
            hits.append((i, t))

# 去重相邻重复（同一逻辑位置重复拼接可接受，仅统计源位置）
print('toast 占位总数（按出现位置）:', len(hits))
for i, t in hits:
    print(f'L{i}: {t}')
