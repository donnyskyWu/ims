# -*- coding: utf-8 -*-
import io, sys, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
src = open(r'D:\self\sy\一体化管理\outputs\UI原型\IMS-一体化管理系统-UI原型.html', encoding='utf-8').read()
lines = src.split('\n')
hits = []
for i, l in enumerate(lines):
    # match toast('msg','type') and toast(\'msg\',\'type\') and toast("msg","type")
    for m in re.finditer(r"toast\((?:\\?'([^\\']{1,80}?)\\?'|\"([^\"]{1,80}?)\")\s*(?:,\s*(?:\\?'([^\\']{1,30}?)\\?'|\"([^\"]{1,30}?)\"))?\)", l):
        msg = m.group(1) or m.group(2)
        if msg and ('示意' in msg or '占位' in msg):
            hits.append((i + 1, msg, l.strip()[:120]))
for h in hits:
    print(h[0], '|', h[1])
print('total placeholder toasts:', len(hits))
