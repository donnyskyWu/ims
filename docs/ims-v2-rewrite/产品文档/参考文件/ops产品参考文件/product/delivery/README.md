# OPS 产品手册 · 交付目录说明

> **更新**：2026-09-20 · **结构版本**：v2.1

## 本目录有什么

| 类型 | 文件 |
|------|------|
| **汇总索引** | [`汇总产品使用手册.md`](./汇总产品使用手册.md) |
| **五本角色手册（v2.1）** | [`运营主管操作手册.md`](./运营主管操作手册.md) · [`运营操作手册.md`](./运营操作手册.md) · [`编辑操作手册.md`](./编辑操作手册.md) · [`账号管理员操作手册.md`](./账号管理员操作手册.md) · [`财务人员操作手册.md`](./财务人员操作手册.md) |
| **新增专题（v2.1）** | [`通用入门与权限说明.md`](./通用入门与权限说明.md) · [`端到端业务流程手册.md`](./端到端业务流程手册.md) · [`系统配置与权限管理手册.md`](./系统配置与权限管理手册.md) |
| **线上 URL** | [`ROUTE-线上地址索引.md`](./ROUTE-线上地址索引.md)（**70** 条 seed 菜单页；基址 `https://saas.shenyu.com/#`） |
| **全菜单 SSOT** | [`../产品使用操作手册.md`](../产品使用操作手册.md) |
| **专项** | [`../OPS业务操作手册-IP组与工作任务.md`](../OPS业务操作手册-IP组与工作任务.md) |
| **截图** | [`../delivery-screenshots/`](../delivery-screenshots/) |
| **Word 输出** | 同目录 `*.docx`（由 `_build_product_delivery_docx.py` 生成） |

## 新手册结构（每本角色手册）

1. **篇首**：线上登录、角色定位、业务价值、主流程、角色衔接  
2. **功能模块章**：说明、**菜单路径**、**Hash 路由**、**线上完整 URL**、操作步骤、截图、**维护字段（Spec）**、注意事项  

维护类字段无 Spec 时标 **待 Spec 确认**，汇总见各手册附录或 [`通用入门与权限说明.md`](./通用入门与权限说明.md) §5。

## 构建命令

```powershell
cd "d:\self\sy\运营数据平台\202606\wd"
python docs/product/delivery/_gen_online_route_index.py   # 可选：从 OPS-MENU-ROUTE-INDEX 重生成路由表
python docs/product/_build_manual_docx.py               # 总册 docx → docs/product/
python docs/product/_build_product_delivery_docx.py     # 总册 + 八本 docx → 本目录
python docs/delivery/product-handover/_pack_delivery_zip.py
```

## 截图补采

```powershell
python docs/product/_capture_delivery_screenshots.py
```

脚本路由列表见 [`../manual-screenshots/README.md`](../manual-screenshots/README.md)。
