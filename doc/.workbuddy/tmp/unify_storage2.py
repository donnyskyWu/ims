# -*- coding: utf-8 -*-
"""统一 IMS 下游文档（PRD/delivery/测试方案）『本期不上对象存储』口径。
用法: python unify_storage2.py <ROOT> <sub> <sub> ...
- 备份到 <ROOT>/.workbuddy/backup-oss2-20261005/
"""
import os, shutil, sys

ROOT = r"D:/self/sy/文档/IMS系统产品"
BK = os.path.join(ROOT, ".workbuddy", "backup-oss2-20261005")

RULES = [
    ("对象存储生命周期策略", "文件目录生命周期策略"),
    ("OSS 上传/签名失败", "文件上传/落盘失败"),
    ("OSS 60 秒签名 URL", "服务端鉴权下载链接"),
    ("OSS 60s 签名 URL", "服务端鉴权下载链接"),
    ("OSS 签名 URL 60s", "服务端鉴权下载链接"),
    ("OSS 60 秒签名", "服务端鉴权下载"),
    ("OSS 60s 签名", "服务端鉴权下载"),
    ("OSS 回执链接下载", "下载链接"),
    ("OSS 链接下载", "下载链接"),
    ("OSS 链接", "下载链接"),
    ("OSS 下载", "下载链接"),
    ("OSS 直传回执", "服务端上传回执"),
    ("先取短时效凭证 ≤60s 再直传回执 ", "POST IMS 上传端点落服务端文件目录得回执 "),
    ("先 OSS 直传再提交元信息", "先服务端上传再提交元信息"),
    ("OSS 直传", "服务端上传"),
    ("OSS 落盘", "落服务端文件目录"),
    ("OSS 上传失败", "文件落盘失败"),
    ("OSS 上传", "文件上传"),
    ("OSS 403", "下载 403"),
    ("OSS 产物", "服务端文件目录产物"),
    ("OSS 凭证", "上传回执"),
    ("OSS 文件 Key", "fileKey"),
    ("ossKeys", "fileKeys"),
    ("ossKey", "fileKey"),
    ("oss_key", "file_key"),
    ("本地对象存储", "服务端文件目录"),
    ("对象存储", "服务端文件目录"),
]

def main():
    subs = sys.argv[1:]
    if not subs:
        print("usage: unify_storage2.py <subdir> ..."); return
    changed = []
    for sub in subs:
        base = os.path.join(ROOT, sub)
        for dirpath, _, filenames in os.walk(base):
            for fn in filenames:
                if not fn.endswith(".md"):
                    continue
                p = os.path.join(dirpath, fn)
                with open(p, "r", encoding="utf-8") as f:
                    s = f.read()
                orig = s
                hits = {}
                for a, b in RULES:
                    c = s.count(a)
                    if c:
                        hits[a] = c
                        s = s.replace(a, b)
                if s != orig:
                    rel = os.path.relpath(p, ROOT)
                    dst = os.path.join(BK, rel)
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copy2(p, dst)
                    with open(p, "w", encoding="utf-8") as f:
                        f.write(s)
                    changed.append((rel, hits))
    for rel, hits in changed:
        print("== " + rel)
        for k, v in hits.items():
            print("   %-28s x%d" % (k, v))
    print("\nTOTAL FILES CHANGED: %d" % len(changed))

if __name__ == "__main__":
    main()
