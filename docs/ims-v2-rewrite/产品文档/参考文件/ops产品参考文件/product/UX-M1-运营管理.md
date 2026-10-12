# UX-M1-运营管理

> **版本**：v1.2 | 2026-10-02
> **关联 PRD**：`docs/product/PRD-M1-运营管理.md`
> **适用模块**：M1 运营管理（5.1 ~ 5.7）
> **设计原则**：按钮级规格 + 状态矩阵 + 角色适配

---


> **视觉规范参考**：[`开发规范/UI设计与开发规范.md`](../../开发规范/UI设计与开发规范.md)（仅原型/设计阶段）
> **实现技术栈**：[`TECH-CONSTRAINTS.md § 1.2`](../engineering/TECH-CONSTRAINTS.md)（Vue 3 + Element Plus）
> **决策记录**：[`ADR-002`](../../adr/ADR-002-前端规范源选择.md)


## 0. OPS 设计 SSOT

> **设计规范**：[UX-OPS-设计规范.md](./UX-OPS-设计规范.md)  
> **原型索引 / 截图 SSOT**：[UX-OPS-页面原型索引.md](./UX-OPS-页面原型索引.md)  
> **Football 路由 SSOT**：[OPS-MENU-ROUTE-INDEX.md](../delivery/OPS-MENU-ROUTE-INDEX.md)

## 1. 页面清单

> **路由列 SSOT**：[`OPS-MENU-ROUTE-INDEX`](../delivery/OPS-MENU-ROUTE-INDEX.md)「Football 完整路由」。作者无独立菜单项，主入口为 IP 组详情 Tab「关联作者」。

| 页面 ID | 名称 | Football 路由 | standalone（历史） | 关联 FR | permission |
|---------|------|---------------|-------------------|---------|------------|
| P-M1-001 | IP 组管理 | `/ops/operations/ip-group` | `/ip-group` | FR-M1-001 | `oa:ip-group:list` |
| P-M1-002 | 作者管理 | （嵌套 · 见 IP 组详情 Tab） | `/author` | FR-M1-002 | `oa:author:list` |
| P-M1-003 | 账号分析 | `/ops/operations/account-analysis` | `/account-analysis` | FR-M1-003 | `oa:account-analysis:list` |
| P-M1-004 | 粉丝分析 | `/ops/operations/fans-analysis` | `/fans-analysis` | FR-M1-004 | `oa:fans-analysis:list` |
| P-M1-005 | 作品分析 | （API `content-analysis` · 无独立菜单） | `/content-analysis` | FR-M1-005 | — |
| P-M1-006 | 内部作品分析 | `/ops/operations/internal-content` | `/internal-content` | FR-M1-006 | `oa:internal-content:list` |
| P-M1-007 | 人效盘点 | `/ops/operations/efficiency` | `/efficiency` | FR-M1-007 | `oa:efficiency:list` |

---

## 2. 公共布局规范

### 2.1 顶栏

```
+--------------------------------------------------+
| Logo | 业务域面包屑 | [全局 IP 组筛选] [用户菜单] |
+--------------------------------------------------+
```

| 控件 ID | 类型 | 文案 | 状态 | 关联 FR |
|---------|------|------|------|---------|
| TOP-IP | Select | IP 组筛选（默认"全部"） | default | 通用 |
| TOP-USER | Dropdown | 用户头像 + 姓名 | default | 通用 |

### 2.2 侧边菜单

```
运营管理
  ├─ IP 组管理（成员岗位 `dict_position`，V69）
  ├─ 作者管理
  ├─ 账号分析
  ├─ 粉丝分析
  ├─ 作品分析
  ├─ 内部内容分析
  └─ 人效盘点
```

### 2.3 主区域

- 顶部：**页头**（标题 + 主操作按钮）
- 主体：**筛选区** + **数据区**（表格/卡片/树）
- 底部：**分页**（page=1, size=20）

---

## 3. 页面 P-M1-001：IP 组管理

### 3.1 布局区块

| 区块 | 组件 | 说明 |
|------|------|------|
| 页头 | 标题"IP 组管理" + 主按钮"+ 新建大组" | FR-M1-001 / AC-M1-001-1 |
| 左侧 | 树形结构（可展开/折叠） | 大组 → 嵌套小组 |
| 右侧（选中节点时） | 详情 Tab：[基本信息 / 成员 / 账号 / **关联作者** / 统计] | 选中后展开；基本信息含等级（`DictLabel`） |

### 3.2 控件级规格

| 控件 ID | 类型 | 文案 | 状态 | 点击行为 | 关联 FR/AC |
|---------|------|------|------|----------|------------|
| BTN-NEW-BIG | 主按钮 | "+ 新建大组" | default / 隐藏(无权限) | 打开 D-M1-001 (mode=create, type=BIG) | FR-M1-001 / AC-M1-001-1 |
| BTN-NEW-SMALL | 次按钮 | "+ 新建小组" | default(选中大组时) | 打开 D-M1-001 (mode=create, type=SMALL, parent=当前大组) | FR-M1-001 / AC-M1-001-1 |
| BTN-EDIT | 文字按钮 | "编辑" | default / 隐藏(无权限) | 打开 D-M1-001 (mode=edit) | FR-M1-001 |
| BTN-DELETE | 文字按钮 | "删除" | default(无数据时) / disabled(有数据时) / 隐藏(无权限) | 二次确认 → 删除 | FR-M1-001 / AC-M1-001-3 |
| TREE-NODE | Tree | 节点显示"组名 (成员/账号/作者 数)" + 等级标签（有值时） | default | 单击选中 → 右侧展示详情 | - |
| TAB-MEMBER | Tab | "成员" | default | 展示成员表 + "+ 添加成员" | FR-M1-001 |
| TAB-ACCOUNT | Tab | "账号" | default | 展示账号表 + "+ 关联账号" | FR-M1-001 |
| TAB-ANCHOR | Tab | "**关联作者**" | default | 展示作者表 + "+ 添加作者"（**作者下拉**，非 UserSelect） | FR-M1-001 / AC-M1-001-6 |
| TAB-STATS | Tab | "统计" | default | 展示粉丝、作品、ROI 聚合 | FR-M1-001 |

### 3.3 状态矩阵

| 状态 | 条件 | 界面表现 |
|------|------|----------|
| 空 | 树无任何节点 | 居中插图 + "暂无 IP 组" + "新建大组"按钮 |
| 加载 | 树首次加载 | Skeleton 树（3 层） |
| 错误 | 接口失败 | Banner "加载失败，请稍后重试" + 重试按钮 |
| 无权限 | 角色无任何 IP 组权限 | 整页（已替换为具体内容）

### 3.4 弹窗 D-M1-001

| 控件 ID | 类型 | 文案/默认值 | 必填 | 校验 |
|---------|------|-------------|------|------|
| F-NAME | Input | "IP 组名称" | ✅ | 1-50 字符 |
| F-TYPE | Radio | "大组 / 小组"（创建大组时禁用"小组"） | ✅ | - |
| F-PARENT | TreeSelect | "上级 IP 组"（小组必填） | 小组 ✅ | 必须选 BIG |
| F-LEADER | UserSelect | "组长" | ❌ | - |
| F-LEVEL | DictSelect | "等级"（`dict_ip_group_level`） | ❌ | S/A/B/C；大组/小组均可选 |
| F-DESC | Textarea | "描述" | ❌ | 0-200 字符 |
| BTN-SUBMIT | 主按钮 | "确认" | - | 提交 |
| BTN-CANCEL | 次按钮 | "取消" | - | 关闭弹窗 |

### 3.5 弹窗 D-M1-003（添加关联作者）

| 控件 ID | 类型 | 文案/默认值 | 必填 | 校验 |
|---------|------|-------------|------|------|
| F-AUTHOR | **作者下拉**（`getAuthorPage` 过滤已绑定） | "作者" | ✅ | 须为租户内已建作者（`author_user.id`） |
| F-AUTHOR-TYPE | DictSelect | "作者类型"（`dict_author_type`） | ❌ | 默认取所选作者类型 |
| BTN-SUBMIT | 主按钮 | "确定" | - | `POST .../ip-group/{id}/anchors` |
| BTN-CANCEL | 次按钮 | "取消" | - | 关闭弹窗 |

---

## 4. 页面 P-M1-002：作者管理

### 4.1 布局区块

| 区块 | 组件 | 说明 |
|------|------|------|
| 页头 | 标题"作者管理" + 主按钮"+ 新建作者" | FR-M1-002 |
| 筛选 | IP 组 / 关键词 / 状态 | 顶栏 |
| 列表 | 表格（作者、IP 组、主推号、运营、粉丝/作品/直播/短视频） | - |
| 行内操作 | "看板" "编辑" "删除" | - |

### 4.2 控件级规格

| 控件 ID | 类型 | 文案 | 状态 | 关联 FR/AC |
|---------|------|------|------|------------|
| BTN-NEW | 主按钮 | "+ 新建作者" | default / 隐藏(无权限) | FR-M1-002 / AC-M1-002-1 |
| F-IP | Select | "IP 组" | default | FR-M1-002 |
| F-KEY | Input | "作者名" | default | FR-M1-002 |
| F-STATUS | Select | "状态" | default | FR-M1-002 |
| BTN-DASHBOARD | Link | "看板" | default | FR-M1-002 |
| BTN-EDIT | 文字按钮 | "编辑" | default | FR-M1-002 |
| BTN-DELETE | 文字按钮 | "删除" | default(无关联任务) | FR-M1-002 |
| TAB-RELS | Tab（详情页） | "运营→主播关联" | default | FR-M1-002 / AC-M1-002-3 |

### 4.3 弹窗 D-M1-002

| 控件 ID | 类型 | 文案 | 必填 | 校验 |
|---------|------|------|------|------|
| F-AUTHOR-NAME | Input | "作者名" | ✅ | 1-50 字符 |
| F-IP | TreeSelect | "IP 组" | ✅ | 仅可选 SMALL |
| F-TYPE | Select | "作者类型 LIVE/SHORT_VIDEO/BOTH" | ✅ | - |
| F-PRIMARY | Select | "主推号" | ❌ | 仅 OFFICIAL_ACCOUNT 类型 |
| F-USER | UserSelect | "绑定系统用户" | ❌ | - |
| F-STATUS | Switch | "启用" | - | - |

---

## 5. 页面 P-M1-003：账号分析

### 5.1 布局区块

| 区块 | 组件 | 说明 |
|------|------|------|
| 页头 | 标题"账号分析" + 导出按钮 | - |
| Tab | 公众号/视频号/抖音/快手/小红书/服务号/企微/个微/全部 | - |
| 筛选 | IP 组、关键词、状态、实名人、运营人 | - |
| 列表 | 表格（账号、IP 组、粉丝、作品、状态、实名人、运营人、操作） | - |
| 行操作 | "查看粉丝分析" "查看作品分析" | - |

### 5.2 控件级规格

| 控件 ID | 类型 | 文案 | 关联 FR/AC |
|---------|------|------|------------|
| TAB-001 ~ TAB-009 | Tab | 各平台名 | FR-M1-003 / AC-M1-003-1 |
| F-IP / F-KEY / F-STATUS | 筛选 | 见表 | FR-M1-003 |
| ROW-FOLLOWER | Link | "查看粉丝分析" | FR-M1-004 / AC-M1-003-2 |
| ROW-CONTENT | Link | "查看作品分析" | FR-M1-005 / AC-M1-003-2 |
| BTN-EXPORT | 主按钮 | "导出 Excel" | FR-M1-003 / AC-M1-003-3 |

### 5.3 状态矩阵

| 状态 | 条件 | 表现 |
|------|------|------|
| 空 | 列表为空 | "该筛选下暂无账号" + "重置筛选" 按钮 |
| 加载 | 首次 / 切换 Tab | Skeleton 表格 |
| 错误 | 接口 500 | Banner + 重试 |
| 无权限 | 角色无权限 | 整页 "无访问权限" |

---

## 6. 页面 P-M1-004：粉丝分析

### 6.1 布局区块

| 区块 | 组件 | 说明 |
|------|------|------|
| 筛选 | `TableSearch`：IP 组、平台、日期范围、时间维度 | 导出在 `#extra` 槽 |
| 快捷范围 | 近 7 日 / 近 30 日 / 自定义 | 默认 30 日 |
| 指标卡 | `el-row` + `statColSpan` 自适应（5 KPI） | 等高对齐 |
| 趋势图 | 折线图 | 7/30 日切换 |
| 表格 | 按账号/IP 组维度聚合 | - |

---

## 7. 页面 P-M1-005：作品分析

### 7.1 布局区块

| 区块 | 组件 | 说明 |
|------|------|------|
| 统计卡片 | 5 KPI 横排（阅读/点赞/评论/转发/作品数） | 位于筛选区上方 |
| 筛选 | `TableSearch`：IP 组、平台、内容类型、日期范围、快捷(全部/7d/30d)、关键词 | 导出在 `#extra` |
| 列表 | 表格（标题、内容类型、账号、IP 组、发布时间、阅读/点赞/评论/转发、是否爆款） | - |
| 详情弹窗 | 基本信息 + **互动趋势**工具栏（日期范围 + 7d/30d） | 默认 7 日 |

### 7.2 关键规则

- 列表日期默认**空=全部**；重置恢复全部
- "是否爆款" 命中 BR-003 显示红色 ✅ 标签，未命中灰色 ❌ 标签
- "是否爆款" 字段点击可跳转爆款详情

---

## 8. 页面 P-M1-006：内部内容分析

### 8.1 布局区块

| 区块 | 组件 | 说明 |
|------|------|------|
| 统计卡片 | 4 卡片区（阅读/点赞/评论/转发汇总） | **2026-06-15** 新增 |
| 页头 | 标题"内部内容分析" + 我的补录 + 补录审核 + 导出 | - |
| Tab | 多平台切换 | - |
| 筛选 | 日期范围（**默认可清空=全部**）、IP 组、关键词 | `clearable`；补录类型筛选项已移除（S-R7） |
| 详情抽屉 | 作品指标 + 趋势图 | 行操作「详情」替代单独「趋势」（2026-06-15） |
| 列表 | 表格（标题、账号、**IP 组**、发布时间、阅读/点赞/评论/转发、**爆款**、操作） | - |
| 行操作 | "**详情**" "**补录**" | - |

### 8.2 补录标记样式

| 数据来源 | 标签样式 |
|----------|----------|
| API | 浅蓝标签 "API" |
| IMPORT（API_EXCEPTION） | 橙色标签 "接口补录" |
| IMPORT（ACCOUNT_BANNED） | 红色标签 "封号补录" |
| IMPORT（OFFLINE_PRACTICE） | 黄色标签 "线下补录" |
| IMPORT（OTHER） | 灰色标签 "其他补录" |

### 8.3 弹窗 D-M1-003 补录

| 控件 ID | 类型 | 文案 | 必填 | 校验 |
|---------|------|------|------|------|
| F-CONTENT | Select | "作品" | ✅ | 仅可选未删除作品 |
| F-DATE | DatePicker | "数据日期" | ✅ | ≤ 今日 且 ≥ 今日-90天 |
| F-TYPE | Select | "补录类型"（API_EXCEPTION/ACCOUNT_BANNED/OFFLINE_PRACTICE/OTHER） | ✅ | - |
| F-READ | InputNumber | "阅读/播放量" | ❌ | ≥ 0 |
| F-LIKE | InputNumber | "点赞数" | ❌ | ≥ 0 |
| F-COMMENT | InputNumber | "评论数" | ❌ | ≥ 0 |
| F-FORWARD | InputNumber | "转发/分享数" | ❌ | ≥ 0 |
| F-FOLLOWER | InputNumber | "粉丝变化" | ❌ | 整数 |
| F-REMARK | Textarea | "补录原因说明" | ❌ | 0-200 字符 |

---

## 9. 页面 P-M1-007：人效盘点

### 9.1 布局区块

| 区块 | 组件 | 说明 |
|------|------|------|
| 页头 | 标题"人效盘点" + 导出 | - |
| 筛选 | 日期范围、IP 组、用户、时间维度(week/month) | - |
| 列表 | 表格（经办人、IP 组、岗位、任务完成/进行/超时、完成率、账号成本、营收、ROI、内容产出、平均播放/阅读、爆款数、操作） | - |
| 行操作 | "+ 展开" | - |

### 9.2 展开卡片（v2.0）

展开后展示 4 个 Card：

| Card | 字段 |
|------|------|
| 任务详情 | 任务列表（标题、状态、起止时间） |
| 财务指标 | 账号总成本、营收、ROI、IP 组/账号维度对比 |
| 内容指标 | 作品列表、平均播放/阅读、爆款数 |
| 趋势 | 周/月聚合线：任务完成数、ROI、内容产出 |

---

## 10. 跨页通用组件

### 10.1 数据来源标识

| 来源 | 标签颜色 |
|------|----------|
| API | 浅蓝 (#909399) |
| IMPORT-API_EXCEPTION | 橙 (#E6A23C) |
| IMPORT-ACCOUNT_BANNED | 红 (#F56C6C) |
| IMPORT-OFFLINE_PRACTICE | 黄 (#F0B939) |
| IMPORT-OTHER | 灰 (#C0C4CC) |

### 10.2 通用加载/空/错误状态

| 组件 | 文案 |
|------|------|
| Empty | 插图 + 引导文字 + 主操作按钮（如适用） |
| Skeleton | 表格 → 6 行；卡片 → 3 行 |
| ErrorBanner | "加载失败，请稍后重试" + 重试按钮 |
| NoPermission | "无访问权限，请联系管理员" |

### 10.3 导出行为约定

- 同步导出 ≤ 5s：直接下载
- 同步导出 > 5s：弹窗"文件较大，将通过异步任务生成"，点击"确认"后进入异步流程
- 文件名格式：`{功能}_{yyyyMMddHHmmss}.xlsx`

---

## 11. 设计走查清单

- [ ] 所有按钮文案与本表一致
- [ ] 状态矩阵 4 种状态已实现
- [ ] 权限受控按钮置灰 + tooltip
- [ ] 补录标签颜色与第 10.1 节一致
- [ ] 导出文件名格式与第 10.3 节一致
- [ ] 移动端：本版本不支持（Out of Scope）

---

*下一步：基于本 UX 规格生成 API Spec（`docs/engineering/API-M1-运营管理.md`）。*


---

## 🔴 M1 全局规范补丁（2026-06-07）

> 本模块必须严格遵循 [`GLOBAL-CONVENTIONS.md`](../engineering/GLOBAL-CONVENTIONS.md) 的三大铁律。

### 三大铁律（必查）

#### 铁律一：关联属性必须用"选择器"，禁止手动填写

M1 中所有 `*_id` 字段必须通过选择器：

| 字段 | 选择器 |
|------|--------|
| `ip_group_id` | `<IpGroupTreeSelect />` |
| `parent_id` | `<IpGroupTreeSelect />` |
| `account_id` | `<AccountSelect />`（**强关联** ⭐，需从 M4 选择） |
| `author_id` | `<UserSelect />` |
| `assignee_id` | `<UserSelect />` |
| `anchor_user_id` | **作者选择器**（作者列表） |
| `ops_user_id` | `<UserSelect />` |
| `metric_id` | `<MetricSelect />` |

#### 铁律二：枚举属性（方式/状态/类型/平台）必须从数据字典选择

| 字段 | 字典 type |
|------|----------|
| `platform_type` | `dict_platform_type` |
| `account_type` | `dict_account_type` |
| `account_status` | `dict_account_status` |
| `ip_group_type` | `dict_ip_group_type` |
| `ip_group_status` | `dict_ip_group_status` |
| `level` | `dict_ip_group_level` |
| `author_type` | `dict_author_type` |
| `author_status` | `dict_author_status` |
| `content_type` | `dict_content_type` |
| `import_type` | `dict_content_import_type` |
| `data_source` | `dict_data_source` |
| `position` | `dict_position` |
| `is_primary` | `dict_yes_no` |
| `need_review` | `dict_yes_no` |
| `is_public` | `dict_yes_no` |

#### 铁律三：实体关系必须在 ER 图中明确

所有跨实体的关联已在 `PRD-M1-运营管理.md § 5 集成与数据` 中明确。

### 与 M4 账号管理的关键关联

M1 中所有平台账号必须通过 M4 的"实名人/手机/手机卡/公司"选择：

```
M1 IP 组 → M1 账号 → M4 实名人（强关联）
                     → M4 手机（强关联）
                     → M4 手机卡（强关联）
                     → M4 公司（强关联）
```

**校验**：
- 已停用实名人/手机/手机卡 不可被新账号引用（错误码 1501）
- 已绑定到其他账号的实名人/手机/手机卡 需"强制替换"（错误码 1502）
- 跨租户过滤（错误码 1504）

### 错误码

| 错误码 | 含义 |
|--------|------|
| 1500 | 关联的实体不存在 |
| 1501 | 关联的实体已停用/注销 |
| 1502 | 关联的实体已被其他记录引用 |
| 1503 | 字典值不合法 |
| 1504 | 跨租户访问禁止 |

详见 [`GLOBAL-CONVENTIONS.md § 5.3`](../engineering/GLOBAL-CONVENTIONS.md)

---

## 10. 薄页补全（DOC-UX-PAGE-FULL-01 · Vue/API 对齐）

> **API 前缀**：`/admin-api/ops/operations/**`（[`API-M1-运营管理.md`](../engineering/API-M1-运营管理.md)）

### 10.1 P-M1-003 账号分析

| 项 | 规格 |
|----|------|
| Vue | `ops/operations/AccountAnalysis.vue` |
| B | IP 组 · 关键词 · 状态 · 实名人 · **运营人**(`UserSelect` → `operatorUserId`) · 平台 Tab |
| C 列 | 账号 · IP 组 · 粉丝 · 作品数 · 状态 · 实名人 · 运营人 · 操作(粉丝/作品链) |
| 图表 drill-down | Tab 切换刷新 list · 行链跳转 `#/ops/operations/fans-analysis?accountId=` |
| API | `GET .../operations/account-analysis/list` · 导出 list 全量 Excel |

### 10.2 P-M1-004 粉丝分析

| B | IP 组 · 平台 · 日期 · 时间维度(DAY/WEEK/MONTH) · 快捷 7/30 日 |
| C | 5 KPI 卡 · 趋势折线 · 聚合表（账号/IP 组维度） |
| 筛选联动 | 改 IP 组 → 重置账号维度假选 · 导出需 confirm「当前筛选结果」 |
| API | `GET .../operations/fans-analysis/stats` · `.../trend` · `.../list` |

### 10.3 P-M1-006 内部作品分析

| C 列 | 标题 · 账号 · IP 组 · 发布时间 · 阅读/点赞/评论/转发 · 爆款标签 · 数据来源标签 · 操作(详情/补录) |
| 抽屉 | 指标描述 + 互动趋势图（日期 7d/30d） |
| API | `GET .../operations/internal-content/list` · 补录 `POST .../internal-content/supplement` |

### 10.4 P-M1-007 人效盘点

| C 列 | 经办人 · IP 组 · 岗位 · 任务完成/进行/超时 · 完成率 · 账号成本 · 营收 · ROI · 内容产出 · 均播放 · 爆款数 · 展开 |
| 展开 | §9.2 四 Card（任务/财务/内容/趋势） |
| API | `GET .../operations/efficiency/list` · 展开详情 `GET .../efficiency/{userId}/detail` |

## CHANGELOG

| 日期 | 说明 |
|------|------|
| 2026-10-02 | v1.2：§10 四页列/筛选/API/联动补全 |
| 2026-06-07 | v1.1：初版控件级 |

---

*补丁完成：M1 全套文档（M0/M1/M2/M3/M4/M5/M6/M7/M8/M9/M10）已统一遵循全局规范。*
