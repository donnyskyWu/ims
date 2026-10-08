# -*- coding: utf-8 -*-
"""QA 静态检查：IMS-一体化管理系统-UI原型.html"""
import re, os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

P = r'D:\self\sy\一体化管理\outputs\UI原型\IMS-一体化管理系统-UI原型.html'
QA = os.path.join(os.path.dirname(P), '_qa')
os.makedirs(os.path.join(QA, 'scripts'), exist_ok=True)
src = open(P, encoding='utf-8').read()

res = []
def chk(name, cond, detail=''):
    res.append(('PASS' if cond else 'FAIL', name, detail))

# ---- S1 文件完整性 ----
chk('S1 DOCTYPE 声明', src.lstrip().lower().startswith('<!doctype html>'))
chk('S2 根元素闭合 </html>', src.rstrip().endswith('</html>') and '</body>' in src)
opens = len(re.findall(r'<script>', src)); closes = len(re.findall(r'</script>', src))
scripts = re.findall(r'<script>(.*?)</script>', src, re.S)
chk('S3 4 个 script 块且配对', opens == closes == 4 and len(scripts) == 4, f'open={opens} close={closes}')
# 语法检查交给 node --check（在 bash 中执行），这里先导出
for i, s in enumerate(scripts, 1):
    open(os.path.join(QA, 'scripts', f's{i}.js'), 'w', encoding='utf-8').write(s)

# 静态 body 区标签配对（不含 JS 模板字符串）
body = src.split('<body>')[1].split('<script>')[0]
for tag in ['div', 'span', 'aside', 'main', 'header']:
    o = len(re.findall(r'<' + tag + r'[\s>]', body)); c = len(re.findall(r'</' + tag + r'>', body))
    if o or c:
        chk(f'S4 静态 body 区 <{tag}> 配对', o == c, f'open={o} close={c}')

# ---- S5~S9 设计令牌 ----
css = src.split('<style>')[1].split('</style>')[0]
chk('S5 双底色 #f5f5f7 / #ffffff', '#f5f5f7' in css and '#ffffff' in css)
chk('S6 主蓝 --blue:#0071e3', '--blue:#0071e3' in css)
chk('S7 弹簧动画 cubic-bezier(.32,.72,0,1)', 'cubic-bezier(.32,.72,0,1)' in css)
chk('S8 圆角体系 12/8/5', '--r:12px' in css and '--r-s:8px' in css and '--r-xs:5px' in css)
chk('S9 抽屉 720px / 消息抽屉 420px', 'width:720px' in css and 'width:420px' in css)

# ---- S10 零外部依赖 ----
ext = [m.group(0) for m in re.finditer(r'https?://[^\s"\')]+', src)]
urls = re.findall(r'url\((?!#)[^)]*\)', css)
chk('S10 无外部 CDN/字体/图标库引用', not ext and '<link' not in src and '@import' not in src and not urls,
    ('外部URL: ' + str(ext[:3]) + ' css url: ' + str(urls[:3])) if (ext or urls) else '')

# ---- S11 蓝色审计 ----
hexes = sorted(set(h.lower() for h in re.findall(r'#[0-9a-fA-F]{3}\b|#[0-9a-fA-F]{6}\b', src)))
other_blue = '#007aff' in hexes
chk('S11 唯一蓝 #0071e3（无第二种蓝）', not other_blue,
    '发现 #007aff @L895 SOP卡片渐变' if other_blue else '')
print('INFO 全部十六进制色:', ', '.join(hexes))

# ---- S12 模块清单 ----
mod_ids = re.search(r'const MODS = \{(.*?)\n\};', src, re.S).group(1)
n_mods = len(re.findall(r'\w+: \{ no:', mod_ids))
chk('S12 MODS 18 个模块（工作台+6+7+4）', n_mods == 18, f'count={n_mods}')
groups = re.search(r'const GROUPS = \[(.*?)\n\];', src, re.S).group(1)
gcounts = re.findall(r"\['(.*?)', \[(.*?)\]\]", groups)
total = sum(len(re.findall(r"'(\w+)'", ids)) for _, ids in gcounts)
chk('S13 GROUPS 分组求和=18 且分组数=4', total == 18 and len(gcounts) == 4, f'groups={len(gcounts)} total={total}')

# ---- S14 LIVE 场次 ID ----
live_ids = re.findall(r"id: '(IMS\d+[A-Z]+\d+)'", src)
pat = re.compile(r'^IMS\d{9}[A-Z]{2}\d{4}$')
bad = [i for i in live_ids if not pat.match(i)]
chk('S14 LIVE 场次 ID 匹配示例格式 IMS202609120DY0142', len(live_ids) >= 15 and not bad,
    f'checked={len(live_ids)} bad={bad}')
print('INFO 示例 IMS202609120DY0142 长度 =', len('IMS202609120DY0142'), '（验收文案写"19位"，示例本身18位）')

# ---- S15 R9 脱敏样式 ----
chk('S15 .masked 灰色斜体样式存在', '.masked{color:var(--text2);font-style:italic' in css)

# ---- S16 按钮 onclick 覆盖 ----
btns = len(re.findall(r'<button', src))
btns_no = len(re.findall(r'<button(?![^>]*onclick)', src))
print(f'INFO 按钮总数(含JS模板串)={btns}, 无 onclick 的按钮={btns_no}')

# ---- 输出 ----
fails = 0
for s, n, d in res:
    print(s, '|', n, ('| ' + d) if d else '')
    if s == 'FAIL':
        fails += 1
print('STATIC_FAIL_COUNT =', fails)
