# -*- coding: utf-8 -*-
import io, sys, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
src = open(r'D:\self\sy\一体化管理\outputs\UI原型\IMS-一体化管理系统-UI原型.html', encoding='utf-8').read()
lines = src.split('\n')
hits = []
for i, l in enumerate(lines):
    # broad scan: any '原型示意' or '原型占位' occurrence
    if '原型示意' in l or '原型占位' in l:
        hits.append((i + 1, l.strip()[:150]))
for h in hits:
    print(h[0], '|', h[1])
print('total lines containing placeholder markers:', len(hits))
