# CONTENT - 内容生产 页面规格

> 依据：《IMS第一期PRD-V1.md》5.20~5.25（CONTENT-001~006）、《共享技术规范-数据库与API.md》第 7/8 章、《共享技术规范-分期技术约束.md》1.3（ComfyUI 集成 V1-C1~C6）。
> **完整版叠加（2026-09-28）**：OPS 并入见同目录《CONTENT-OPS并入补充-页面规格.md》与《CONTENT-OPS并入补充-API契约.md》（CONTENT-100～110、Football WebAPI 同步）。**交互**以 UX-M2 + ADR-IMS-003；**API/写模型**以 IMS `/admin-api/ims/content/**` 为 canonical（2026-10-01，OPS 路径仅参照）。  
> **实现 SSOT（ADR-IMS-003）**：**禁止**以 `UI原型/IMS-完整系统-UI原型.html` 中 `content*` 页作为 M2 交互蓝本。切片与验收须 `@` 下列 OPS 文档 + 《CONTENT-OPS并入补充-页面规格.md》侧栏映射：
> - `docs/product/UX-M2-内容生产.md`
> - `docs/product/UX-M2-内容生产-amphipoda对齐增量.md`
> - `docs/product/PRD-M2-工作任务管理.md`
> - `docs/product/PRD-M2-内容生产.md`（若与 UX 冲突以 UX 为准）
> - Football 写路径：《FB-Football-WebAPI适配.md》§2  
> **信息架构（2026-09-29）**：内容域在侧栏 **「日常运营」→ 二级「内容生产」目录** 下挂子菜单（与 **直播管理** 并列，不混排），见《CONTENT-OPS并入补充-页面规格.md》§侧栏映射；本文件 P1～P6 为 **IMS 短视频增量**，默认 **不出现在主导航**，其中 CONTENT-004 视频能力 **内嵌于「内容管理」抽屉**（AI 视频脚本 / AI 视频生成）。  
> 技术栈基线：Vue 3 + TypeScript + Element Plus；API 前缀 `/admin-api/ims/content`。

## 交付切片与 Gate（2026-10-05 · v2.6.34）

> **口径（用户 2026-10-05 拍板 · 唯一口径）**：CONTENT 端到端不可整链验收（走查阻断 2026-09-29 §2），正式按 **5 切片**推进，每片独立 Gate；**放弃整系统全量开写**。
> **Gate 判据**：每片 = **规格评审通过 + 原型闭环 + 契约齐备 + 联调通过（四项全绿）**；**不以整链为 Gate**。
> **开工顺序 = 门禁优先**：**S1 规格先行 + S4 内容审核门禁并行**（S4 的 G1 不依赖 Football，是整链最高频阻断点，可最早解除）。
> **未开片模块**：导航可见但页面标「**建设中**」，不接业务入口。
> **导航**：CONTENT = **7 子菜单**（SOP管理 / 计划管理 / 工作任务登记 / 我的任务 / 内容管理 / 公推模板库 / 内容审核，v2.6.33）；「全部任务」= 我的任务页内 Tab，非独立菜单；**SOP 免审**（无 SOP 审核页）。

| Slice | FR/功能点 | 范围 | 关键产物 | Gate 判据 | 依赖 | 状态 |
|-------|-----------|------|----------|-----------|------|------|
| **S1** | CONTENT-100 + CONTENT-102 | SOP 管理 + 计划管理 | 页面规格 + API 契约 | 规格评审通过 + 原型闭环 | 无（先行） | **先行 · 进行中** |
| **S2** | CONTENT-104 / CONTENT-105 | 工作任务登记 + 作者×赛事矩阵出任务 | 矩阵 UI + 出任务接口 | 矩阵可操作、能生成任务 | S1 | 未开片 |
| **S3** | CONTENT-103 + CONTENT-106 | 我的任务 + 内容主工作区（玩法/AI/排版） | 执行 → 内容抽屉 → 玩法 | 任务可执行、内容可存 | S2 | 未开片 |
| **S4** | CONTENT-005 + CONTENT-006 | 内容审核（级数可配）+ 发布归档 → 门禁 G1 | 审核门禁 | 未审内容不可发布（可独立验收） | 无（**不依赖 Football**，先行） | **先行 · 进行中** |
| **S5** | CONTENT-109 / CONTENT-110 | Football 方案同步 + 补偿 | WebAPI + 补偿队列 | 同步成功 / 失败进队列 | S3、S4 | 未开片 |

> **本文件与《CONTENT-OPS并入补充-页面规格.md》的分工**：本文件 P1～P6 为 **IMS 短视频增量**（默认不出主导航，属未开片或内嵌能力，页面标「建设中」）；**OPS 主路径**（SOP / 计划 / 工作任务 / 我的任务 / 内容管理 / 公推模板 / 内容审核）以《CONTENT-OPS并入补充-页面规格.md》为规格 SSOT，本文件不重复其控件。切片 Gate 以补充规格的侧栏映射与页面级最小集为准。

## 0. 模块总览

### 0.1 OPS 主路径（侧栏子菜单 · 实现优先）

见《CONTENT-OPS并入补充-页面规格.md》— SOP管理、计划管理、工作任务登记、我的任务、**任务执行全页**（`/ims/content/task/:id/execute`）、内容管理（含 **amphipoda 玩法区**）、公推模板库、内容审核（**LayoutViewer 只读**）。字段级细节以补充规格为准，本文 P1～P6 不重复 OPS 主路径控件。

### 0.2 IMS 增量（P1～P6 · P1/P2 或内嵌）

| 页面 | 路由 | 级别 | 对应功能点 | 导航 |
|------|------|------|-----------|------|
| P1 SOP 模板管理 | `/ims/content/sop` | 与 OPS SOP 合并实现 | CONTENT-001 升级列 | **SOP管理** 子菜单 |
| P2 选题计划 | `/ims/content/topic` | 选题池 + 甘特（P1） | CONTENT-002 | 不出主导航 |
| P3 AI 辅助脚本 | `/ims/content/script` | 脚本列表 + 编辑器（P1） | CONTENT-003 | 不出主导航；短视频脚本 → **内容管理** AI 视频脚本 |
| P4 AI 生产链 | `/ims/content/ai-production` | ComfyUI DAG（P0 能力） | CONTENT-004 | 不出主导航 Tab；**内容管理** 内 AI 视频生成 + 队列状态 |
| P5 在线审核 | `/ims/content/review` | 与 OPS 审核合并 | CONTENT-005 | **内容审核** 子菜单 |
| P6 发布归档 | `/ims/content/publish` | 发布单（P0 IMS） | CONTENT-006 | 不出主导航；随 SOP 发布节点 / 后续迭代 |

通用 UI 约定：查询条件一行紧凑排布；交互优先内联抽屉（Drawer）不跳转；状态 tag 语义色；状态列遵循全局权威枚举。

---

## P1. SOP 模板管理页（CONTENT-001）

### 1. 页面概述
- 路由路径：`/ims/content/sop`
- 页面级别：一级菜单页
- 依赖模块：P2 选题立项（挂接 SOP）、P4 生产任务（节点流转带出标准）
- 权限矩阵引用：R1 R/W/D（全量）、R4 R/W（全量）、R5 R（直播 SOP）、R6 R/W（视频 SOP）、R7 R（只读）、R10 R（被指派 SOP）

### 2. ASCII 页面布局
```
+------------------------------------------------------------------+
| 查询行: SOP名称 | 适用内容类型 | 状态 | [查询] [重置] [新建SOP(R1/R4)] |
+------------------------------------------------------------------+
| 表格: SOP名称 | 适用内容类型 | 版本 | 节点数 | 质量清单项总数 | 状态 |  |
|       进行中项目数 | 更新时间 | 操作[查看节点][编辑(新版本)][停用][删除] |
+------------------------------------------------------------------+
| 分页: pageNo=1  pageSize=10  total=xxx                            |
+------------------------------------------------------------------+
节点编辑抽屉(90%可全屏):
  SOP 头部信息: 名称* | 内容类型* | 说明
  节点序列（垂直可拖拽排序）:
    每节点卡片: 节点名称* | 执行标准说明* | 交付物规格(格式/规格选择) |
      | 质量检查清单(逐项添加) | 责任角色* | SLA时效(小时)*
  [添加节点] | [保存为新版本]
```

### 3. TypeScript 类型定义

```typescript
// 请求类型
interface SopPageReq {
  pageNo: number; pageSize: number;
  sopName?: string; contentType?: string; status?: 'ENABLED' | 'DISABLED';
}
interface SopSaveReq {
  sopName: string;                 // 必填 ≤64 字
  contentType: string;             // 必填（带货短视频/口播/剧情/直播切片…）
  description?: string;
  nodes: SopNodeItem[];            // 必填 ≥1
  clientToken: string;
}
interface SopNodeItem {
  nodeOrder: number;               // 1 起
  nodeName: string;                // 必填 ≤64 字
  standardDesc: string;            // 执行标准说明 必填 ≤1024 字
  deliverableSpec: { format: string; spec: string };   // 交付物（MP4/图文，分辨率/时长）
  qualityChecklist: string[];      // 质量检查清单 ≥1 项
  ownerRole: string;               // 责任角色（R6/R8/R10…）
  slaHours: number;                // 必填 ≥1
}
interface SopNodeCheckReq {
  /** 与契约 2.1.6 结构对齐 */
  contentProjectId: number;              // 内容项目 ID（挂接该 SOP 的项目）
  checklistResults: Array<{ itemCode: string; passed: boolean; remark?: string }>;   // 逐项勾选结果
  deliverableFileKeys: string[];         // 交付物 fileKey（FileUpload 服务端上传回执）
}

// 响应类型
interface SopItem {
  id: number; sopName: string; contentType: string;
  version: number; nodeCount: number; checklistTotal: number;
  status: 'ENABLED' | 'DISABLED';
  inProgressProjectCount: number;  // 进行中项目数（影响删除）
  updateTime: string;
}

// 枚举类型
type SopStatus = 'ENABLED' | 'DISABLED';
type SopNodeRole = 'SCRIPT_WRITER' | 'PRODUCER' | 'EDITOR' | 'REVIEWER' | 'OUTSOURCE';
```

### 4. 交互流程

#### 4.1 页面加载
骨架屏 → `GET /content/sop/list`；失败重试。

#### 4.2 核心操作流程
**A. 新建/编辑 SOP（R1/R4）**
1. [新建 SOP] / [编辑] → 大抽屉；编辑头部提示"当前 v2，保存生成 v3"（SOP-R3：进行中项目沿用旧版本完成）；
2. 节点卡片垂直列表可拖拽排序（默认序列：选题→脚本→拍摄/生成→剪辑→审核→发布）；
3. 每节点填写：名称/执行标准/交付物规格/质量清单（动态添加条目，≥1）/责任角色/SLA 时效；
4. 保存校验：≥1 节点、节点字段完备、节点名不重复 → `POST /content/sop` / `PUT /content/sop/{id}`（clientToken）→ 版本 +1。

**B. 节点查看（全部有权角色）**
- [查看节点] → 只读抽屉，节点流程图（垂直步骤条）+ 每节点标准/清单展开。

**C. 停用/删除**
1. [停用]：确认弹窗"停用后新立项不可选，进行中项目不受影响"（SOP-R3）；
2. [删除]：inProgressProjectCount > 0 → 阻断提示（同 POS-R3 逻辑）；为 0 → 危险确认。

**D. 质量清单校验提交（生产任务执行侧，入口在 P4）**
- 节点完成时逐项勾选清单 + 上传交付物 → `POST /content/sop/node/{nodeId}/check`（SOP-R2：全通过+交付物齐备方可过节点；未通过项打回上游，留痕）。

### 5. 查询条件表

| 字段名 | 组件类型 | 必填 | 默认值 | 说明 |
|--------|---------|------|--------|------|
| sopName | Input | 否 | 空 | 模糊 |
| contentType | Select | 否 | 空 | 内容类型字典 |
| status | Select | 否 | 空 | 启用/停用 |

### 6. 表格列定义

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| sopName | SOP 名称 | 200 | — | 点击查看节点 |
| contentType | 适用内容类型 | 130 | — | 字典翻译 |
| version | 版本 | 70 | ✓ | v{version} |
| nodeCount | 节点数 | 80 | — | 数字 |
| checklistTotal | 清单项总数 | 100 | — | 数字 |
| status | 状态 | 80 | — | tag：启用(绿)/停用(灰) |
| inProgressProjectCount | 进行中项目 | 110 | — | >0 时删除禁用 |
| updateTime | 更新时间 | 150 | ✓ | yyyy-MM-dd HH:mm |
| actions | 操作 | 240 | — | 按角色动态 |

### 7. 抽屉/弹窗规格

| 抽屉/弹窗 | 类型 | 字段与验证 |
|-----------|------|-----------|
| SOP 编辑抽屉 | Drawer 90% | sopName 必填 ≤64 字；contentType 必选；nodes ≥1（每节点 nodeName/standardDesc/qualityChecklist/ownerRole/slaHours 必填，slaHours ≥1）；节点名唯一；拖拽排序 nodeOrder 自动重算 |
| 节点查看抽屉 | Drawer 720px | 只读步骤条 + 展开明细 |
| 停用/删除确认弹窗 | Modal 420px | 删除需输入 SOP 名确认 |

### 8. 错误处理
- 网络超时：抽屉提交防重、草稿保留；
- 节点校验失败：失败节点卡片红框定位；
- 权限不足：R5/R7 只读进入；R10 仅见被指派 SOP（服务端过滤）。

### 9. BR 业务规则覆盖
- **BR-008（内容标准化覆盖率 > 90%）**：P2 立项强制挂接启用版本 SOP（SOP-R1，立项表单校验）；本页 SOP 可用性是覆盖率的前置；
- SOP-R2/R3/R4（清单全通过、版本沿用、SLA 督办）在编辑抽屉与 P4 执行侧落实。

---

## P2. 选题计划页（CONTENT-002）

### 1. 页面概述
- 路由路径：`/ims/content/topic`
- 页面级别：一级菜单页，视图切换：[列表] [排期甘特] [看板]
- 依赖模块：18 作品监测已建数据（热点参考）、P1 SOP（立项挂接）、P3 脚本、P4 生产任务
- 权限矩阵引用：R1 R（全量）、R4 R/W/D（全量，评审立项）、R5 R（直播选题）+ W 提报、R6 R/W（本人选题）、R7 W（可提报）、R9 R

### 2. ASCII 页面布局
```
+------------------------------------------------------------------+
| 视图切换: [列表] [排期甘特] [状态看板]        [提报选题(R5/R6/R7)] |
+------------------------------------------------------------------+
| 查询行: 选题编号 | 标题关键词 | 来源类型 | 状态 | 提报人 | [查询][重置]|
+------------------------------------------------------------------+
| 表格: 选题编号 | 标题 | 来源类型 | 提报人 | 计划发布日 | 挂接SOP |    |
|       状态 | 评审意见 | 操作[评审(R4)][编辑][详情]                    |
+------------------------------------------------------------------+
| 分页: pageNo=1  pageSize=20  total=xxx                            |
+------------------------------------------------------------------+
提报抽屉(600px): 标题* | 描述* | 来源类型* | 计划发布日* | [提交]
评审抽屉(R4): 选题详情 + 立项区(挂接SOP*+排期确认) 或 落选意见* 
甘特视图: 行=选题, 列=日期(计划发布日标记), 排期冲突高亮
看板视图: 待评审/已立项/落选/已取消 四列卡片
```

### 3. TypeScript 类型定义

```typescript
// 请求类型
interface TopicPageReq {
  pageNo: number; pageSize: number;
  topicNo?: string; keyword?: string;
  sourceType?: TopicSourceType; topicStatus?: TopicStatus;
  submitterUserId?: number;
}
interface TopicCreateReq {
  title: string;                   // 必填 ≤256 字
  description: string;             // 必填 ≤2000 字
  sourceType: TopicSourceType;     // 必填
  planPublishDate: string;         // 必填 yyyy-MM-dd
  clientToken: string;
}
interface TopicReviewReq {
  topicId: number;
  action: 'APPROVE_PROJECT' | 'REJECT';   // 同 CONTENT-API 契约 2.2.4
  planPublishDate?: string;       // 立项时必填（TOP-R1）
  sopId?: number;                 // 立项时必填（TOP-R1）
  reviewOpinion: string;          // 落选必填 ≤512 字
}

// 响应类型
interface TopicItem {
  id: number; topicNo: string;     // TP+日期+流水
  title: string;
  sourceType: TopicSourceType;
  submitterName: string;
  planPublishDate: string;
  sopName: string | null;
  topicStatus: TopicStatus;
  reviewOpinion: string | null;
}
interface TopicGanttItem {
  topicNo: string; title: string;
  planPublishDate: string;
  sopName: string | null; topicStatus: TopicStatus;
  conflictHint: string | null;     // 同账号同日超量（TOP-R3）
}

// 枚举类型
type TopicStatus = 'PENDING_REVIEW' | 'APPROVED_PROJECT' | 'REJECTED' | 'CANCELLED';   // 同 CONTENT-API 契约（已立项）
type TopicSourceType = 'HOTSPOT' | 'TALENT' | 'BRAND' | 'ORIGINAL';   // 热点/达人/品牌/自主（同契约大写值域）
```

### 4. 交互流程

#### 4.1 页面加载
骨架屏 → `GET /content/topic/list`（R6 本人、R5 直播类、R7 本人提报，服务端过滤）；失败重试。

#### 4.2 核心操作流程
**A. 提报选题（R5/R6/R7）**
1. [提报选题] → 抽屉：标题/描述/来源类型（热点参考：来源=热点时侧栏展示 18 作品监测热点榜只读卡片）/计划发布日；
2. 提交（clientToken）→ 状态"待评审"；
3. 编辑：待评审状态本人可改；已评审后锁定。

**B. 评审立项（R4）**
1. 待评审行 [评审] → 评审抽屉：选题详情只读；
2. 分支：
   - [立项]：必须选择挂接 SOP（启用版本下拉，TOP-R1 必填）+ 确认计划发布日 → 状态"已立项"，自动创建内容项目（挂 SOP、排期）→ 进入生产节点流转（P4）；
   - [落选]：评审意见必填 → 状态"落选"，归档保留可复活（TOP-R2：落选列表提供 [复活重启] 操作）；
3. 排期冲突提示（TOP-R3）：立项时同账号同日超量 → 黄色提示不阻断。

**C. 视图切换**
- 甘特：按计划发布日排布，冲突高亮；看板：四状态列卡片拖拽仅 R4 可改变状态。

### 5. 查询条件表

| 字段名 | 组件类型 | 必填 | 默认值 | 说明 |
|--------|---------|------|--------|------|
| topicNo | Input | 否 | 空 | 选题编号 |
| keyword | Input | 否 | 空 | 标题模糊 |
| sourceType | Select | 否 | 空 | 热点/达人/品牌/自主 |
| topicStatus | Select | 否 | 空 | 待评审/已立项/落选/已取消 |
| submitterUserId | PersonSelect | 否 | 空 | 提报人 |

### 6. 表格列定义

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| topicNo | 选题编号 | 140 | — | 等宽字体 |
| title | 标题 | 自适应 | — | 省略 + tooltip |
| sourceType | 来源类型 | 100 | — | tag：热点(橙)/达人(蓝)/品牌(紫)/自主(绿) |
| submitterName | 提报人 | 100 | — | — |
| planPublishDate | 计划发布日 | 110 | ✓ | yyyy-MM-dd；冲突黄底 |
| sopName | 挂接 SOP | 150 | — | 立项前"—" |
| topicStatus | 状态 | 100 | — | tag：待评审(蓝)/已立项(绿)/落选(灰)/已取消(灰红) |
| reviewOpinion | 评审意见 | 160 | — | 省略 + tooltip |
| actions | 操作 | 160 | — | [评审(R4)][编辑][详情]，落选行 [复活] |

### 7. 抽屉/弹窗规格

| 抽屉/弹窗 | 类型 | 字段与验证 |
|-----------|------|-----------|
| 提报/编辑抽屉 | Drawer 600px | title 必填 ≤256 字；description 必填 ≤2000 字；sourceType 必选；planPublishDate 必填（≥今日）；clientToken 防重 |
| 评审抽屉 | Drawer 640px | 立项分支：sopId 必填（启用版本）；落选分支：reviewOpinion 必填 ≤512 字 |
| 选题详情抽屉 | Drawer 560px | 只读：选题信息 + 评审记录 + 关联内容项目状态链 |
| 复活确认弹窗 | Modal 360px | 复活回"待评审"确认 |

### 8. 错误处理
- 网络超时：提交防重；
- 立项未挂 SOP（1007）：抽屉内红框定位 sopId；
- 热点榜加载失败：侧栏独立重试，不阻断提报表单；
- 权限不足：R7 无列表查看权仅本人提报记录（服务端过滤）。

### 9. BR 业务规则覆盖
- **BR-008（标准化覆盖率）**：立项必挂 SOP（TOP-R1）为覆盖率的直接控制点；
- TOP-R2 落选归档可复活、TOP-R3 排期冲突提示不阻断，均在列表/评审落点。

---

## P3. AI 辅助脚本页（CONTENT-003）

### 1. 页面概述
- 路由路径：`/ims/content/script`
- 页面级别：一级菜单页（脚本列表 + 生成抽屉 + 在线编辑器抽屉 + 版本历史）
- 依赖模块：P2 选题（关联）、LLM 生成服务、P4 生产任务（定稿输入）
- 权限矩阵引用：R1 R（全量）、R4 R（全量）、R5 R/W、R6 R/W（本人，主责）；其余不可见

### 2. ASCII 页面布局
```
+------------------------------------------------------------------+
| 查询行: 关联选题 | 脚本类型 | 状态(草稿/定稿) | AI生成 | [查询][重置]  |
|                                    [AI生成脚本(R6/R5)] [导出]      |
+------------------------------------------------------------------+
| 表格: 脚本编号/标题 | 关联选题 | 脚本类型 | 版本 | AI生成 | 状态 |    |
|       作者 | 更新时间 | 操作[编辑][定稿][版本历史][详情]              |
+------------------------------------------------------------------+
| 分页: pageNo=1  pageSize=20  total=xxx                            |
+------------------------------------------------------------------+
生成抽屉(640px): 关联选题* | 脚本类型*(口播/剧情/带货话术) | 内容要求* |
  | 生成候选数(2~3) | [生成] → 候选卡片列表 → [采用并编辑]
编辑器抽屉(90%): Markdown 编辑器 | 版本对比视图 | [保存新版本][定稿锁定]
```

### 3. TypeScript 类型定义

```typescript
// 请求类型
interface ScriptPageReq {
  pageNo: number; pageSize: number;
  topicId?: number; scriptType?: ScriptType;
  status?: ScriptStatus; aiGenerated?: boolean;
}
interface ScriptGenerateReq {
  topicId: number;                  // 必填
  scriptType: ScriptType;           // 必填
  requirement: string;              // 内容要求 必填 ≤2000 字
  candidateCount: number;           // 默认 3，2~3
  clientToken: string;
}
interface ScriptUpdateReq { id: number; content: string; }    // Markdown
interface ScriptFinalizeReq { id: number; }

// 响应类型
interface ScriptItem {
  id: number;
  title: string;                   // 选题标题派生
  topicNo: string; topicId: number;
  scriptType: ScriptType;
  version: number;
  aiGenerated: boolean;
  status: ScriptStatus;
  authorName: string;
  updateTime: string;
}
interface ScriptCandidate {
  candidateIndex: number;
  content: string;                 // Markdown
  promptSnapshot: string;          // 提示词快照（可复现，SCR-R3）
}
interface ScriptVersionItem { version: number; content: string; authorName: string; createdAt: string; }

// 枚举类型
type ScriptType = 'VOICEOVER' | 'DRAMA' | 'SELLING_SCRIPT';    // 口播/剧情/带货话术
type ScriptStatus = 'DRAFT' | 'FINALIZED';
```

### 4. 交互流程

#### 4.1 页面加载
骨架屏 → `GET /content/script/list`（R6 本人、R5 本团队，服务端过滤）；失败重试。

#### 4.2 核心操作流程
**A. AI 生成候选（R6/R5）**
1. [AI 生成脚本] → 抽屉：选关联选题（带出选题描述预填内容要求可改）、脚本类型、内容要求、候选数；
2. [生成] → loading（生成中禁用关闭）→ 返回 2~3 版候选卡片（每版附提示词快照可展开）；
3. [采用并编辑] → 打开编辑器抽屉载入该候选 → 状态草稿、aiGenerated=1。

**B. 在线编辑与版本（R6 本人）**
1. 编辑器抽屉：Markdown 编辑 + [版本对比]（当前 vs 任一历史版本左右 diff）；
2. [保存新版本] → version +1（历史可回溯，SCR-R2）；
3. [定稿锁定]：
   - 校验：AI 生成脚本必须经过人工编辑（SCR-R1：比对内容 hash，未改动提示"请先人工润色后再定稿"）；
   - 定稿后内容锁定只读，传递下游（P4 生产任务可选定稿脚本为输入）。

**C. 版本历史**
- [版本历史] → 抽屉版本列表，任意版本可查看/对比。

### 5. 查询条件表

| 字段名 | 组件类型 | 必填 | 默认值 | 说明 |
|--------|---------|------|--------|------|
| topicId | TopicSelect | 否 | 空 | 关联选题搜索 |
| scriptType | Select | 否 | 空 | 口播/剧情/带货话术 |
| status | Select | 否 | 空 | 草稿/定稿 |
| aiGenerated | Select | 否 | 空 | AI/人工 |

### 6. 表格列定义

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| title | 脚本标题 | 自适应 | — | 选题标题派生，省略 + tooltip |
| topicNo | 关联选题 | 140 | — | 可点击跳选题详情 |
| scriptType | 脚本类型 | 110 | — | tag 三色 |
| version | 版本 | 70 | ✓ | v{version} |
| aiGenerated | AI 生成 | 90 | — | tag：AI(紫)/人工(绿) |
| status | 状态 | 90 | — | tag：草稿(蓝)/定稿(绿) |
| authorName | 作者 | 100 | — | — |
| updateTime | 更新时间 | 150 | ✓ | yyyy-MM-dd HH:mm |
| actions | 操作 | 220 | — | [编辑][定稿][版本历史][详情] 按状态 |

### 7. 抽屉/弹窗规格

| 抽屉/弹窗 | 类型 | 字段与验证 |
|-----------|------|-----------|
| 生成抽屉 | Drawer 640px | topicId 必选；scriptType 必选；requirement 必填 ≤2000 字；candidateCount 默认 3（2~3）；生成中禁用提交 |
| 编辑器抽屉 | Drawer 90% | Markdown 编辑 + diff 对比；保存新版本（内容非空）；[定稿锁定]（SCR-R1 人工编辑校验） |
| 版本历史抽屉 | Drawer 720px | 版本列表只读 + 双版本 diff 视图 |
| 定稿确认弹窗 | Modal 360px | "定稿后锁定，将作为下游生产输入" |

### 8. 错误处理
- 网络超时：生成失败提示重试（提示词不丢）；编辑保存失败草稿本地暂存；
- LLM 服务超时（5003 类）：生成 loading 中断 + 明确错误文案；
- 定稿校验失败：弹窗提示人工润色要求；
- 权限不足：R5 只读本人团队，R1/R4 只读。

### 9. BR 业务规则覆盖
- **BR-010（ComfyUI 链路支撑）**：定稿脚本作为 AI 生产链输入（P4 创建任务可选 scriptId）；
- SCR-R1（AI 必须人工确认定稿）、SCR-R2（版本可回溯、定稿锁定）、SCR-R3（提示词快照留痕可复现）均落点。

---

## P4. AI 生产链页（CONTENT-004）

### 1. 页面概述
- 路由路径：`/ims/content/ai-production`
- 页面级别：一级菜单页（任务列表 + 创建抽屉 + 任务详情抽屉含 DAG 视图与终审）
- 依赖模块：P2 选题、P3 脚本、ComfyUI 工作流（`ims_content_workflow` 登记与参数 schema）、GPU 队列（V1-C2/C3）、服务端文件目录产物（V1-C5）、P5 终审/P6 发布
- 权限矩阵引用：R1 R/W/D（全量）、R4 R/W（全量）、R6 R/W（本人任务）、R10 W（被指派环节，可见被指派任务）

### 2. ASCII 页面布局
```
+------------------------------------------------------------------+
| 查询行: 任务编号 | 关联选题/脚本 | 任务状态 | 时间范围 | [查询][重置]  |
|                                     [创建生产任务(R6/R10)] [导出]   |
+------------------------------------------------------------------+
| 队列状态条(顶部): 等待 N | 执行中 N | 今日完成 N | 失败 N | GPU 状态  |
+------------------------------------------------------------------+
| 表格: 任务编号 | 关联选题 | 工作流 | 提示词摘要 | 状态 | 当前节点 |  |
|       终审状态 | 创建人 | 创建时间 | 操作[详情][终审][重试节点]         |
+------------------------------------------------------------------+
| 分页: pageNo=1  pageSize=20  total=xxx                            |
+------------------------------------------------------------------+
创建抽屉(720px): 关联选题*(可选脚本) | 内容要求* | 风格参数* |
  | ComfyUI工作流*(下拉,含参数schema表单) | [生成提示词]
  → 提示词编辑区(可改,版本留痕) → [创建并提交队列]
任务详情抽屉(90%):
  Tab: [任务信息] [提示词版本] [DAG 执行视图] [产物预览]
  DAG 视图: 节点流程图(分镜生成→视频合成→配音字幕→成片) 每节点状态/耗时/重试
  产物预览: 成片在线播放 + 中间产物缩略图
  底部操作: [人工终审(通过/打回)] [打回指定节点重生成] 
```

### 3. TypeScript 类型定义

```typescript
// 请求类型
interface AiTaskPageReq {
  pageNo: number; pageSize: number;
  taskNo?: string; topicId?: number;
  taskStatus?: AiJobStatus; timeRange?: [string, string];
}
interface AiTaskCreateReq {
  topicId: number;                  // 必填
  scriptId?: number;                // 可选定稿脚本
  requirement: string;              // 内容要求 必填 ≤2000 字
  styleParams: Record<string, string | number>;   // 工作流参数 schema 驱动
  workflowId: number;               // 必填
  promptFinal?: string;             // 生成后可人工调整
  clientToken: string;
}
interface AiPromptUpdateReq { taskNo: string; promptFinal: string; }   // 修改留版本（AIP-R1）
interface AiRunReq { taskNo: string; }
interface AiReviewReq {
  taskNo: string;
  conclusion: 'PASS' | 'REJECT';
  opinion: string;                  // 打回必填
  rejectNodeName?: string;          // 打回指定 DAG 节点（AIP-R3 定向重生成）
}
interface AiRetryNodeReq { taskNo: string; nodeName: string; }

// 响应类型
interface AiTaskItem {
  id: number; taskNo: string;       // AIP+日期+流水
  topicNo: string; topicId: number;
  workflowName: string;
  promptSummary: string;            // 提示词前 50 字
  taskStatus: AiJobStatus;
  currentNodeName: string | null;
  reviewerName: string | null;
  creatorName: string;
  createdAt: string;
}
interface AiQueueStats { waiting: number; running: number; doneToday: number; failed: number; gpuStatus: 'OK' | 'BUSY' | 'OFFLINE'; }
interface AiWorkflowRunNode {
  nodeName: string;                 // 分镜生成/视频合成/配音字幕/成片
  nodeType: 'comfyui' | 'llm' | 'audio';
  runStatus: 'WAITING' | 'RUNNING' | 'SUCCESS' | 'FAILED' | 'TIMEOUT';
  retryCount: number;               // 自动重试 ≤2（AIP-R2）
  startedAt: string | null; finishedAt: string | null;
  durationSeconds: number | null;
  errorMsg: string | null;
  outputPreviewUrl: string | null;  // 产物缩略/预览（服务端文件目录鉴权下载链）
}
interface AiPromptVersion { version: number; prompt: string; editorName: string; createdAt: string; }

// 枚举类型（= 全局权威枚举 AiJobStatus，同 CONTENT-API 契约值域）
type AiJobStatus =
  | 'WAITING'            // 待生成（提示词编辑/队列排队，V1-C2 显示队列位置）
  | 'GENERATING'         // 生成中
  | 'PENDING_FINAL_REVIEW' // 待终审
  | 'REVIEW_PASSED'      // 终审通过
  | 'REVIEW_REJECTED'    // 终审打回
  | 'FAILED';            // 失败
```

### 4. 交互流程

#### 4.1 页面加载
骨架屏 → 并行 `GET /content/ai-production/task/page` + 队列状态条；DAG 视图进详情时加载；失败分区重试；GPU 状态 OFFLINE 显示橙色提示（V1-C3）。

#### 4.2 核心操作流程
**A. 创建生产任务（R6/R10 被指派）**
1. [创建生产任务] → 抽屉：选关联选题（可附定稿脚本）、内容要求、选择 ComfyUI 工作流（下拉，带说明）→ 依工作流参数 schema 动态渲染风格参数表单（V1-C1）；
2. [生成提示词] → 系统模板化生成提示词（loading）→ 提示词编辑区展示（可人工调整，AIP-R1 调整留版本）；
3. [创建并提交队列] → 任务创建（taskNo=AIP…）→ 状态 WAITING（提示词定稿、排队待调度），进入优先级队列（V1-C2：P0~P4，前端显示队列位置）→ [启动] 可自动或手动（AiRunReq）；
4. DAG 调度执行：分镜生成→视频合成→配音字幕→成片（节点失败自动重试 ≤2 次，AIP-R2；超 60 分钟全链超时失败告警，AIP-R4）。

**B. 任务详情与监控**
1. [详情] → 90% 大抽屉四 Tab：
   - 任务信息：基础信息 + 状态链；
   - 提示词版本：版本列表（生成版/人工修改版）；
   - DAG 执行视图：节点流程图，每节点状态色（等待灰/执行中蓝/成功绿/失败红/超时橙）、耗时、重试次数、错误信息；节点产物缩略图（服务端文件目录鉴权下载链）；
   - 产物预览：成片在线播放（禁止未终审下载，AIP-R5）；
2. 生成中任务 DAG 视图 10s 轮询刷新（WebSocket 可选）。

**C. 人工终审（R8 审核员主责，或指定终审人）**
1. 状态"待终审"行 [终审] → 详情抽屉底部终审区：
   - [通过]：状态 REVIEW_PASSED → 移交发布（P6，AIP-R5：终审通过前不可发布的硬约束）；
   - [打回]：必填意见 + 选择打回的 DAG 节点（下拉：分镜生成/视频合成/配音字幕）→ `POST /content/ai-production/task/{taskNo}/retry-node` 定向重生成（AIP-R3，非全链重跑）；
2. 终审通过后成片解锁移交发布。

**D. 失败重试**
- 失败任务行 [重试节点] 或从详情 DAG 视图失败节点上 [重试]（R6/R1）。

### 5. 查询条件表

| 字段名 | 组件类型 | 必填 | 默认值 | 说明 |
|--------|---------|------|--------|------|
| taskNo | Input | 否 | 空 | 任务编号 |
| topicId | TopicSelect | 否 | 空 | 关联选题 |
| taskStatus | Select | 否 | 空 | 六状态（AiJobStatus） |
| timeRange | DateRangePicker | 否 | 近 7 天 | 创建时间 |

### 6. 表格列定义

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| taskNo | 任务编号 | 160 | — | 等宽字体 |
| topicNo | 关联选题 | 140 | — | 可点击 |
| workflowName | 工作流 | 140 | — | — |
| promptSummary | 提示词摘要 | 自适应 | — | 前 50 字省略 |
| taskStatus | 状态 | 110 | — | tag：待提示词(灰)/队列中(蓝)/生成中(青)/待终审(橙)/通过(绿)/打回(黄)/失败(红) |
| currentNodeName | 当前节点 | 110 | — | DAG 节点名 |
| creatorName | 创建人 | 100 | — | — |
| createdAt | 创建时间 | 150 | ✓ | yyyy-MM-dd HH:mm |
| actions | 操作 | 200 | — | [详情][终审][重试节点] 按状态 |

### 7. 抽屉/弹窗规格

| 抽屉/弹窗 | 类型 | 字段与验证 |
|-----------|------|-----------|
| 创建任务抽屉 | Drawer 720px | topicId 必选；requirement 必填 ≤2000 字；workflowId 必选（选中后渲染参数 schema 表单，必填项强制）；promptFinal 生成后可编辑；clientToken 防重 |
| 任务详情抽屉 | Drawer 90% | 四 Tab；DAG 节点流程图 + 轮询刷新；产物在线预览（无下载控件，AIP-R5）；底部终审操作区 |
| 终审打回弹窗 | Modal 480px | opinion 必填 ≤512 字；rejectNodeName 必选（DAG 节点下拉） |
| 重试确认弹窗 | Modal 360px | 确认重试该节点（自动重试 ≤2 次提示） |

### 8. 错误处理
- 网络超时：创建防重（clientToken）；DAG 轮询断线自动恢复；
- ComfyUI 队列满（5004）：提交时提示"GPU 队列繁忙，任务已排队（当前等待 N）"（V1-C6：P2 及以下暂停派发时提示延后）；
- 产物校验失败：节点标红 + 错误信息（V1-C4）；
- 全链超时（AIP-R4）：任务置 FAILED + 告警，DAG 视图超时节点橙色；
- 权限不足：R10 仅见被指派任务；终审仅审核角色。

### 9. BR 业务规则覆盖
- **BR-010（ComfyUI 链路至少跑通 1 条完整链路）**：本页即链路载体——要求/提示词→工作流 DAG→产物→人工终审→移交发布全链贯通；DAG 视图与状态链是链路可验证性的页面落点；
- AIP-R1~R5（提示词留版本、重试 ≤2、定向打回、60 分钟超时、终审前不可发布）全部在创建/详情/终审流程落点；
- V1-C1~C6（API 桥接、优先级队列、GPU 监控、超时重试、服务端文件目录产物、并发约束）由页面队列状态条与 DAG 视图透出运行态。

---

## P5. 在线审核页（CONTENT-005）

### 1. 页面概述
- 路由路径：`/ims/content/review`
- 页面级别：一级菜单页（审核队列 + 审核抽屉 + 统计看板）
- 依赖模块：P1 SOP 质量清单、P4 AI 成片/人工成片、工作台待办、P6 发布前置
- 权限矩阵引用：R1 R（全量）、R4 R（全量）+ 裁决、R6 R（本人提交）、R8 R/W/D（终审主责）；其余不可见

### 2. ASCII 页面布局
```
+------------------------------------------------------------------+
| Tab: [审核队列] [统计看板]                                         |
| 查询行: 审核单号 | 内容项目 | 轮次 | 结论 | 提交时间范围 | [查询][重置]|
+------------------------------------------------------------------+
| 审核队列表格(按发布排期排序,超期高亮):                               |
|   审核单号 | 内容项目 | 提交人 | 轮次 | 排期日 | 超期标记 | 状态 |    |
|   操作[审核][详情]                                                |
+------------------------------------------------------------------+
| 分页: pageNo=1  pageSize=20  total=xxx                            |
+------------------------------------------------------------------+
审核抽屉(90%):
  左侧: 内容在线预览(视频播放器/图文)
  右侧: 审核检查清单
    维度1 合规(广告法/平台规则): 逐项勾选
    维度2 质量清单(对照SOP): 逐项勾选
    维度3 品牌一致性: 逐项勾选
  结论: [通过] [打回(选未通过项+指定回退节点)] [驳回终止(说明*)]
看板: 一次通过率(BR-009) | 打回原因 TOP | 平均审核时长 | 超时率
```

### 3. TypeScript 类型定义

```typescript
// 请求类型
interface ReviewPageReq {
  pageNo: number; pageSize: number;
  reviewNo?: string; contentProjectId?: number;
  reviewRound?: number; conclusion?: ReviewConclusion;
  submittedRange?: [string, string];
}
interface ReviewConclusionReq {
  reviewNo: string;
  conclusion: ReviewConclusion;
  checklistResult: { itemId: string; pass: boolean }[];     // 全部清单项
  rejectItems?: { itemId: string; reason: string }[];       // 打回必填（REV-R2 结构化）
  rejectToNodeName?: string;                                // 打回回退节点
  remark?: string;                                          // 驳回终止必填
}

// 响应类型
interface ReviewItem {
  id: number; reviewNo: string;             // RV+日期+流水
  contentProjectLabel: string;              // 内容项目（选题标题）
  submitterName: string;
  reviewRound: number;                      // 审核轮次
  planPublishDate: string;                  // 排期（排序键）
  overdue: boolean;                         // 超 SLA 12h（REV-R4）
  conclusion: ReviewConclusion | null;      // 未审为 null
  firstPass: boolean | null;                // 第 1 轮通过（BR-009 统计）
  contentPreviewUrl: string;                // 60s 签名预览
  checklistGroups: {
    dimension: 'COMPLIANCE' | 'QUALITY' | 'BRAND';
    items: { itemId: string; label: string; required: boolean }[];
  }[];
}
interface ReviewStatsResp {
  firstPassRate: number;                    // BR-009 目标 > 70%
  rejectReasonTop: { reason: string; count: number }[];
  avgReviewHours: number;
  overdueRate: number;
}

// 枚举类型
type ReviewConclusion = 'PASS' | 'REJECT_BACK' | 'TERMINATE';   // 同契约值域
// 通过 / 打回 / 驳回终止
```

### 4. 交互流程

#### 4.1 页面加载
骨架屏 → `GET /content/review/queue`（队列按发布排期升序，REV 排序约定）；超期项红标置顶；失败重试。

#### 4.2 核心操作流程
**A. 在线审核（R8 主责）**
1. 行 [审核] → 90% 审核抽屉：左侧内容在线预览（视频/图文，禁止下载）；右侧三维度检查清单逐项勾选（合规/质量对照 SOP/品牌一致性）；
2. 回避校验（REV-R1）：提交人=当前审核人 → 该行 [审核] 按钮禁用 tooltip"不可审核自己提交的内容"；
3. 出结论三选一：
   - [通过]：清单全勾（未勾项存在时提示确认）→ 内容进入发布准备（P6 可建发布单，PUB-R1）；
   - [打回]：必须勾选具体未通过项（REV-R2 结构化原因）+ 每项说明 + 选择回退节点（脚本/剪辑/生成节点下拉）→ 内容回到指定节点重做；轮次 +1；
   - [驳回终止]：说明必填 → 项目终止归档；
4. 第 3 轮仍打回（REV-R3）→ 提交时服务端自动升级运营总监裁决（R4 收到待办，本页 R4 对该单出现 [裁决] 按钮）；
5. 审核时效 SLA 12 小时（REV-R4）→ 超期红标 + 工作台督办。

**B. 统计看板**
- 一次通过率大数字（BR-009 目标 > 70%，未达标红色）、打回原因 TOP 条形图、平均审核时长、超时率。

**C. 详情**
- 已审单 [详情] → 只读：结论、清单结果、打回项与轮次历史。

### 5. 查询条件表

| 字段名 | 组件类型 | 必填 | 默认值 | 说明 |
|--------|---------|------|--------|------|
| reviewNo | Input | 否 | 空 | 审核单号 |
| contentProjectId | TopicSelect | 否 | 空 | 内容项目 |
| reviewRound | InputNumber | 否 | 空 | 轮次 |
| conclusion | Select | 否 | 空 | 通过/打回/驳回 |
| submittedRange | DateRangePicker | 否 | 近 7 天 | 提交时间 |

### 6. 表格列定义

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| reviewNo | 审核单号 | 150 | — | 等宽字体 |
| contentProjectLabel | 内容项目 | 自适应 | — | 省略 + tooltip |
| submitterName | 提交人 | 100 | — | 回避时名字橙色 |
| reviewRound | 轮次 | 70 | ✓ | 第 N 轮；≥3 轮紫色 |
| planPublishDate | 排期日 | 110 | ✓ | yyyy-MM-dd |
| overdue | 超期 | 80 | — | 超 SLA 红标"超 12h" |
| conclusion | 结论 | 100 | — | tag：未审(蓝)/通过(绿)/打回(黄)/驳回(红) |
| actions | 操作 | 150 | — | [审核]（回避禁用）[详情]；R4 裁决单 [裁决] |

### 7. 抽屉/弹窗规格

| 抽屉/弹窗 | 类型 | 字段与验证 |
|-----------|------|-----------|
| 审核抽屉 | Drawer 90% | 左预览右清单；checklistResult 全项必填（每项 pass/fail）；打回：rejectItems ≥1 且每项 reason 必填、rejectToNodeName 必选；驳回终止：remark 必填 ≤512 字；提交前结论确认 |
| 裁决抽屉（R4） | Drawer 640px | 轮次历史只读 + 裁决结论（终审通过/维持打回）+ 意见必填 |
| 审核详情抽屉 | Drawer 720px | 只读：结论 + 清单结果 + 轮次历史时间线 |
| 未勾项确认弹窗 | Modal 360px | 通过时存在未勾项 → 二次确认 |

### 8. 错误处理
- 网络超时：结论提交防重（结论提交幂等）；
- 并发审核冲突（他人已出结论）：提示刷新；
- 预览 URL 过期：重新加载预览；
- 权限不足：R6 仅本人提交记录只读。

### 9. BR 业务规则覆盖
- **BR-009（一次审核通过率 > 70%）**：统计看板首卡常显一次通过率与目标线，未达标红色；打回原因 TOP 支撑改进；
- REV-R1（回避）、REV-R2（结构化打回项）、REV-R3（第 3 轮升级裁决）、REV-R4（12h SLA 超期督办）全部落点。

---

## P6. 发布归档页（CONTENT-006）

### 1. 页面概述
- 路由路径：`/ims/content/publish`
- 页面级别：一级菜单页（发布单列表 + 发布计划抽屉 + 回填弹窗 + 归档详情）
- 依赖模块：P5 审核通过前置（PUB-R1）、ACCT 账号台账（发布账号）、18 作品监测（发布后效果跟踪联动）
- 权限矩阵引用：R1 R/W/D（全量，归档删除审批）、R4 R/W（全量）、R6 R/W（执行发布）、R8 R（只读）、R9 R

### 2. ASCII 页面布局
```
+------------------------------------------------------------------+
| 查询行: 发布单号 | 内容项目 | 发布账号 | 状态 | 计划发布范围          |
|         [查询] [重置]                       [创建发布单(R6/R4)]     |
+------------------------------------------------------------------+
| 待办提示条: 待发布 N | 已发布待回填 N(超24h红标)                     |
+------------------------------------------------------------------+
| 表格: 发布单号 | 内容项目 | 发布账号 | 平台 | 计划发布时间 | 文案摘要 | |
|       发布状态 | 链接回执 | 归档 | 操作[执行发布回填][详情][归档包]   |
+------------------------------------------------------------------+
| 分页: pageNo=1  pageSize=20  total=xxx                            |
+------------------------------------------------------------------+
创建发布单抽屉(640px): 内容项目*(仅审核通过) | 发布账号*(使用中) |       |
  平台* | 计划发布时间* | 文案/话题 | [创建]
回填弹窗: 发布链接*(URL校验) → 保存后自动触发归档打包
归档详情抽屉: 归档包内容清单(源片/脚本/审核单/回执) + 下载 + 效果跟踪链接
```

### 3. TypeScript 类型定义

```typescript
// 请求类型
interface PublishPageReq {
  pageNo: number; pageSize: number;
  publishNo?: string; contentProjectId?: number;
  accountId?: number; publishStatus?: PublishStatus;
  planRange?: [string, string];
}
interface PublishCreateReq {
  contentProjectId: number;         // 必填，仅审核通过（PUB-R1）
  accountId: number;                // 必填，使用中账号
  platform: string;                 // 必填
  planPublishAt: string;            // 必填
  caption: string;                  // 文案/话题 必填 ≤512 字
  clientToken: string;
}
interface PublishReceiptReq {
  publishId: number;
  publishUrl: string;               // 必填，URL 格式校验
}
interface PublishPendingReq { type: 'PENDING_PUBLISH' | 'PENDING_RECEIPT'; pageNo: number; pageSize: number; }

// 响应类型
interface PublishItem {
  id: number; publishNo: string;    // PB+日期+流水
  contentProjectLabel: string;
  accountNickname: string;
  platform: string;
  planPublishAt: string;
  captionSummary: string;
  publishStatus: PublishStatus;
  publishUrl: string | null;
  archiveNo: string | null;
  receiptOverdue: boolean;          // 发布后 24h 未回填（PUB-R2）
}
interface ArchiveDetail {
  archiveNo: string;
  fileList: { fileType: 'VIDEO' | 'SCRIPT' | 'REVIEW' | 'RECEIPT'; fileName: string; fileSize: string; downloadUrl: string }[];
  archivedAt: string;
  retentionUntil: string;           // 保留期 ≥2 年（PUB-R4）
  monitorUrl: string | null;        // 18 作品监测效果跟踪链接
}

// 枚举类型
type PublishStatus = 'PENDING_PUBLISH' | 'PUBLISHED' | 'ARCHIVED' | 'PUBLISH_FAILED';
// 待发布 / 已发布(待归档) / 已归档 / 发布失败（同 CONTENT-API 契约值域）
```

### 4. 交互流程

#### 4.1 页面加载
骨架屏 → 并行列表 + 待办提示条（`GET /content/publish/pending`）；待回填超 24h 红标（PUB-R2）；失败分区重试。

#### 4.2 核心操作流程
**A. 创建发布单（R6/R4）**
1. [创建发布单] → 抽屉：内容项目选择器（仅列出审核通过项目，PUB-R1 硬约束）、发布账号（使用中，ACCT 联动）、平台、计划发布时间、文案/话题；
2. 提交（clientToken）→ 状态"待发布"，排期进入待办提示。

**B. 执行发布与回填（R6）**
1. 到期执行发布（人工在各平台操作）→ 行 [执行发布回填] → 回填弹窗粘贴发布链接（URL 格式校验）；
2. 保存 → `PUT /content/publish/{id}/receipt` → 状态"已发布"（已回执）→ **自动触发归档打包**（PUB-R3：源片+脚本+审核单+回执，服务端异步）；
3. 发布后 24h 未回填 → 红标 + 工作台督办（PUB-R2）；
4. 发布失败分支：行 [标记发布失败] → 状态 PUBLISH_FAILED，退回重新排期。

**C. 归档详情**
1. 归档完成后（状态"已归档"）行 [归档包] → 抽屉：归档清单四类文件（源片/脚本/审核单/回执）+ 下载 + 效果跟踪链接（跳 18 作品监测，已建系统外链）；
2. 保留期展示（≥2 年，PUB-R4）；归档删除仅 R1 审批（危险操作，见下）。

**D. 归档删除（R1，审批制）**
- [删除归档] → 危险确认（输入归档号）→ 生成删除审批待办 → R1 二次确认后逻辑删除留审计。

### 5. 查询条件表

| 字段名 | 组件类型 | 必填 | 默认值 | 说明 |
|--------|---------|------|--------|------|
| publishNo | Input | 否 | 空 | 发布单号 |
| contentProjectId | TopicSelect | 否 | 空 | 内容项目 |
| accountId | AccountSelect | 否 | 空 | 发布账号 |
| publishStatus | Select | 否 | 空 | 四状态 |
| planRange | DateRangePicker | 否 | 本月 | 计划发布时间 |

### 6. 表格列定义

| 列字段 | 列标题 | 宽度 | 排序 | 格式化 |
|--------|--------|------|------|--------|
| publishNo | 发布单号 | 150 | — | 等宽字体 |
| contentProjectLabel | 内容项目 | 自适应 | — | 省略 + tooltip |
| accountNickname | 发布账号 | 130 | — | — |
| platform | 平台 | 90 | — | 字典翻译 |
| planPublishAt | 计划发布时间 | 150 | ✓ | yyyy-MM-dd HH:mm |
| captionSummary | 文案摘要 | 150 | — | 省略 + tooltip |
| publishStatus | 发布状态 | 110 | — | tag：待发布(蓝)/已发布(青)/已归档(绿)/发布失败(红) |
| publishUrl | 链接回执 | 140 | — | 链接图标可点；未回填显示"待回填"，超 24h 红字 |
| archiveNo | 归档号 | 140 | — | 归档后可点开归档包 |
| actions | 操作 | 220 | — | [执行发布回填][详情][归档包][标记失败] 按状态 |

### 7. 抽屉/弹窗规格

| 抽屉/弹窗 | 类型 | 字段与验证 |
|-----------|------|-----------|
| 创建发布单抽屉 | Drawer 640px | contentProjectId 必选（仅审核通过）；accountId 必选（使用中）；platform 必选；planPublishAt 必填；caption 必填 ≤512 字；clientToken 防重 |
| 回填弹窗 | Modal 480px | publishUrl 必填 URL 格式校验；提示"回填后自动归档打包" |
| 归档详情抽屉 | Drawer 720px | 只读清单 + 文件下载（60s 签名）+ 效果跟踪外链 + 保留期 |
| 发布失败弹窗 | Modal 420px | 失败原因必填 |
| 归档删除危险弹窗 | Modal 420px | 输入归档号确认 + 提示走 R1 审批留痕 |

### 8. 错误处理
- 网络超时：创建防重；回填失败重试（链接不丢）；
- 内容项目未审核通过（1007）：创建时项目选择器即过滤，兜底服务端校验提示；
- 归档打包失败（5005）：状态停留"已发布"+ 失败标记，可 [重新打包]；
- 权限不足：R8/R9 只读；删除仅 R1。

### 9. BR 业务规则覆盖
- **BR-010（链路收口）**：发布归档是 ComfyUI 自动化链路最后一环（终审通过→发布→归档），本页与 P4/P5 共同构成 BR-010 验证链路；
- PUB-R1（仅审核通过可建发布单，选择器过滤+服务端校验）、PUB-R2（24h 回填督办红标）、PUB-R3（回填自动归档打包）、PUB-R4（保留 ≥2 年，R1 审批删除）全部落点。

---

## 模块通用备注
- 本模块 6 个一级页面，抽屉/弹窗共 17 个（SOP 编辑、节点查看、提报、评审、生成、编辑器、版本历史、任务创建、任务详情、终审打回、审核、裁决、发布创建、回填、归档详情等）+ 确认弹窗若干。
- 全模块复用全局权威枚举：`TopicStatus`、`ScriptStatus`、`AiJobStatus`、`ReviewConclusion`、`PublishStatus`（均已与 CONTENT-API 契约值域对齐）；
- 内容生产链顺序约定：P2 选题立项 → P1 SOP 挂接 → P3 脚本定稿 → P4 AI 生产 → P5 在线审核 → P6 发布归档 → 18 作品监测（已建）效果跟踪；
- 与 18 作品监测、16 数据采集均为**增量消费**（外链/数据只读），不重复建设。
