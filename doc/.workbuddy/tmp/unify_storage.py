# -*- coding: utf-8 -*-
"""统一 IMS 产品规格『本期不上对象存储』口径（2026-10-05 用户拍板）。
- 排除：全局开发规范.md（该文件含决策原文「不上对象存储」，需保留）
- 先备份到 .workbuddy/backup-oss-20261005/
"""
import os, shutil, sys

ROOT = r"D:/self/sy/文档/IMS系统产品"
SPEC = os.path.join(ROOT, "产品规格")
BK = os.path.join(ROOT, ".workbuddy", "backup-oss-20261005")
EXCLUDE = {"全局开发规范.md"}

RULES = [
    ("对象存储生命周期策略", "文件目录生命周期策略"),
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
    ("OSS 403", "下载 403"),
    ("OSS 产物", "服务端文件目录产物"),
    ("OSS 凭证", "上传回执"),
    ("OSS 文件 Key", "fileKey"),
    ("ossKeys", "fileKeys"),
    ("ossKey", "fileKey"),
    ("本地对象存储", "服务端文件目录"),
    ("对象存储", "服务端文件目录"),
]

def main():
    changed = []
    for dirpath, _, filenames in os.walk(SPEC):
        for fn in filenames:
            if not fn.endswith(".md") or fn in EXCLUDE:
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
    if not changed:
        print("NO CHANGE")
        return
    for rel, hits in changed:
        print("== " + rel)
        for k, v in hits.items():
            print("   %-28s x%d" % (k, v))
    print("\nTOTAL FILES CHANGED: %d" % len(changed))

if __name__ == "__main__":
    main()
