# -*- coding: utf-8 -*-
"""第三轮：清理裸 OSS 残留（PRD/delivery/测试方案）。"""
import os, shutil, sys
ROOT = r"D:/self/sy/文档/IMS系统产品"
BK = os.path.join(ROOT, ".workbuddy", "backup-oss3-20261005")
RULES = [
    ("服务端文件目录/OSS 能力", "服务端文件存储能力"),
    ("服务端文件目录 OSS 竞品资产", "服务端文件目录 竞品资产"),
    ("服务端文件目录 OSS", "服务端文件目录"),
    ("Redis/OSS/MinIO", "Redis/本地文件目录"),
    ("钉钉/ComfyUI/OSS/Redis", "钉钉/ComfyUI/服务端文件目录/Redis"),
    ("ComfyUI→OSS→发布", "ComfyUI→服务端文件目录→发布"),
    ("OSS/MinIO", "本地文件目录"),
    ("产物回传 OSS", "产物回传服务端文件目录"),
    ("OSS 归档", "服务端文件目录归档"),
    ("OSS 回执", "服务端上传回执"),
    ("OSS 版本化", "服务端文件目录版本化"),
    ("实际 OSS 对象", "实际服务端文件"),
    ("OSS 对象", "服务端文件"),
    ("OSS 增量", "文件存储增量"),
    ("OSS 能力", "文件存储能力"),
    ("OSS/链接直读", "服务端文件目录/链接直读"),
    ("存 OSS", "存服务端文件目录"),
    ("走 OSS", "落服务端文件目录"),
    ("容器、OSS、MQ、OLAP 引擎", "容器、服务端文件目录、MQ、OLAP 引擎"),
    ("容器、OSS、MQ", "容器、服务端文件目录、MQ"),
    ("OSS", "服务端文件目录"),
]
def main():
    subs = sys.argv[1:]
    changed = []
    for sub in subs:
        for dirpath, _, filenames in os.walk(os.path.join(ROOT, sub)):
            for fn in filenames:
                if not fn.endswith(".md"): continue
                p = os.path.join(dirpath, fn)
                with open(p, "r", encoding="utf-8") as f: s = f.read()
                orig = s
                hits = {}
                for a, b in RULES:
                    c = s.count(a)
                    if c: hits[a] = c; s = s.replace(a, b)
                if s != orig:
                    rel = os.path.relpath(p, ROOT)
                    dst = os.path.join(BK, rel)
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copy2(p, dst)
                    with open(p, "w", encoding="utf-8") as f: f.write(s)
                    changed.append((rel, hits))
    for rel, hits in changed:
        print("== " + rel)
        for k, v in hits.items(): print("   %-26s x%d" % (k, v))
    print("\nTOTAL: %d" % len(changed))
if __name__ == "__main__": main()
