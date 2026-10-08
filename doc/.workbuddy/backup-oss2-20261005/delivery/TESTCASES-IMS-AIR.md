# TESTCASES-IMS-AIR — AI资源

> **v2.6.34（2026-10-05）**：AIR 知识库的**语义检索已整体移出范围（不做）**——KNOW-003 检索、KB-001 RAGFlow 底座、`knowledge_context`、错误码 5007/5008 全部**移除**（非延后）；范围锁定为**文件管理**，底座 `KbProvider=LOCAL`，MCP 固定四工具。

## TC-P0-01

- **Given** R4 已登录
- **When** `GET /air/skill/list`
- **Then** code=0 或 UI 含 技能库


---

> **业务故事映射**（2026-10-01 自动生成 P0 主路径）

## US-AIR-01 选用 AI 技能完成任务

### TC-IMS-AIR-01-01-01 P0 主路径

- **Given** AIR 四叶；Key/审计 Deferred 页无菜单。
- **When** 用户按故事主路径操作（页面 `airSkill`）
- **Then** 配置持久化或 mock 一致；Deferred 路由重定向 skill。

## US-AIR-02 从专家库匹配专家策略

### TC-IMS-AIR-02-01-01 P0 主路径

- **Given** AIR 四叶；Key/审计 Deferred 页无菜单。
- **When** 用户按故事主路径操作（页面 `airExpert`）
- **Then** 配置持久化或 mock 一致；Deferred 路由重定向 skill。

## US-AIR-03 配置模型与提示词

### TC-IMS-AIR-03-01-01 P0 主路径

- **Given** AIR 四叶；Key/审计 Deferred 页无菜单。
- **When** 用户按故事主路径操作（页面 `airCfg`）
- **Then** 配置持久化或 mock 一致；Deferred 路由重定向 skill。

## US-AIR-04 维护知识库与知识分类

### TC-IMS-AIR-04-01-01 P0 主路径

- **Given** R11 已登录；AIR 四叶含知识库菜单。
- **When** 进入 `airKb`，执行「分类管理」新增两级分类并保存
- **Then** 分类树持久化或 mock 一致；条目可挂入所选分类。

## US-AIR-05 从系统资料转入知识库 / 手动上传

### TC-IMS-AIR-05-01-01 P0 主路径

- **Given** AIR 四叶；来源模块（培训资料/绩效考核模板/内容记录）存在待转入条目。
- **When** 点击「从系统转入」→ 4 步向导（选来源→勾选条目→选目标库+分类+密级→提交）
- **Then** 生成入库审批单；`source_type`=TRAIN/PERF/CONTENT、`source_ref` 正确溯源。

### TC-IMS-AIR-05-02-01 P1 手动上传三方式

- **Given** AIR 四叶知识库页。
- **When** 分别以「文件上传 / URL 地址 / 粘贴文本」三种方式上传
- **Then** 三种方式均生成待审批条目；`source_type` 分别落 FILE/URL/TEXT；文件方式落 `oss_key/file_size/content_type`。

### TC-IMS-AIR-05-03-01 P0 文件管理期边界（检索已移除）

- **Given** AIR 知识库页（v2.6.34 文件管理期，语义检索已移除）。
- **When** 打开 `airKb` 页并提交入库审批通过
- **Then** ① 页头**无**「底座巡检」按钮；② 页内**无** RAGFlow 底座健康卡、**无**「检索演示」入口；③ 审批通过后文档状态 `PENDING→PUBLISHED`（**不经 PARSING**）；④ Provider 显示固定 `LOCAL`（IMS 本地对象存储）；⑤ MCP 工具清单为 **四工具**（无 `knowledge.search`/`knowledge.get`）。

---

