# UX-OPS 设计规范

> **版本**：v1.1 | 2026-10-02  
> **范围**：Football 壳（`:5777`）内「运营数据 / OPS」全部页面  
> **SSOT 互补**：路由 [`OPS-MENU-ROUTE-INDEX.md`](../delivery/OPS-MENU-ROUTE-INDEX.md) · 模块 UX `UX-M*.md` · 原型索引 [`UX-OPS-页面原型索引.md`](./UX-OPS-页面原型索引.md)  
> **Penpot**：无 OPS 专用库；**Spec 级线框 = 本规范 + 各 UX § + [`delivery-screenshots/`](./delivery-screenshots/README.md) 截图 SSOT**（未来 Penpot URL 登记在原型索引「Penpot」列）

---

## 1. 应用壳与导航

### 1.1 Football + OPS 双壳

```
+------------------------------------------------------------------+
| Football 顶栏：Logo | 租户 | 全局搜索(可选) | 用户/消息            |
+----------+-------------------------------------------------------+
| Football | OPS 业务区（本规范主体）                                 |
| 侧栏     | 面包屑 + 页头 + 筛选 + 主内容 + 分页/图表                 |
| (系统)   |                                                       |
| + OPS    |                                                       |
|   6100   |                                                       |
|   子菜单 |                                                       |
+----------+-------------------------------------------------------+
```

| 项 | 规范 |
|----|------|
| **Hash 路由** | `http://localhost:5777/#/ops/{domain}/{page}`（domain = `monitor` / `production` / `analysis` / …） |
| **菜单 SSOT** | seed `6100 运营数据` 嵌套 path 拼接；**禁止**沿用 standalone `:3000` 扁平路径写 E2E |
| **权限** | 菜单 `permission` + 按钮级 `v-hasPermi`；Dev Token 仅替代登录，权限从 DB（ADR-003） |
| **租户** | 全表 `tenant_id`；筛选/列表默认当前租户 |

### 1.2 OPS 一级分组（path 段）

| menu_id | 分组 | path 段 | 典型 domain |
| ---: | --- | --- | --- |
| 6168 | 首页 | `dashboard` | `/ops/dashboard` |
| 6101 | 作品监测 | `monitor` | `/ops/monitor/*` |
| 6102 | 内容生产 | `production` | `/ops/production/*` |
| 6103 | 数据分析 | `analysis` | `/ops/analysis/*` |
| 6104 | 数据采集 | `collect` | `/ops/collect/*` |
| 6106 | 绩效核算 | `performance` | `/ops/performance/*` |
| 6107 | 财务管理 | `finance` | `/ops/finance/*` |
| 6108 | 账号管理 | `internal` | `/ops/internal/*` |
| 6109 | 运营管理 | `operations` | `/ops/operations/*` |
| 6110 | 配置管理 | `config` | `/ops/config/*` |
| 6105 | 系统管理(OA) | `system-oa` | `/ops/system-oa/*` |

---

## 2. 布局网格与间距

| Token | 值 | 用途 |
|-------|-----|------|
| `--ops-page-padding` | 16px 20px | 主内容区内边距 |
| `--ops-filter-gap` | 12px | 筛选表单项间距 |
| `--ops-section-gap` | 16px | 筛选区与表格/卡片间距 |
| 表格区最小高度 | 400px | 空态居中 |

**标准列表页三区（线框区域 A/B/C）**：

```
+-- A: 页头 --------------------------------------------------------+
| 标题 (h2)                    [主按钮] [次按钮] [更多 ▾]            |
+-- B: 筛选 --------------------------------------------------------+
| el-form inline · 2~4 行 · [查询] [重置]                            |
+-- C: 数据 --------------------------------------------------------+
| el-table / 卡片 / 图表 · 底部分页 el-pagination                  |
+------------------------------------------------------------------+
```

| 变体 | 说明 |
|------|------|
| **树 + 详情** | A 全宽；B 左 280px 树 + C 右 Tab 详情（IP 组 P-M1-001） |
| **三 Tab** | A 下 `el-tabs` 占满 C（工作任务 P-M2-016） |
| **全屏大屏** | 隐藏 OPS 内边距；F11 / 路由 `screen`（M6） |

---

## 3.  typography 与色彩

| 元素 | Element Plus / 约定 |
|------|---------------------|
| 页标题 | `class="text-lg font-medium"` 或 EP 默认 Card header |
| 表格正文 | 13px / `--el-font-size-base` |
| 辅助说明 | `type="info"` `el-text` |
| 主色 | 跟随 Football 主题变量；OPS 不单独定品牌色 |
| **状态 Tag** | 枚举走字典 label + `el-tag`：`success`/`warning`/`danger`/`info` 与业务状态映射见各 UX |

**内容/任务状态 Tag（示例 · SSOT 字典 `dict_*`）**：

| 业务 | dict-type | Tag 建议 |
|------|-----------|----------|
| 内容状态 | `dict_content_status` | 草稿 info · 待审 warning · 通过 success · 驳回 danger |
| 任务状态 | `dict_task_status` | 进行中 primary · 完成 success · 逾期 danger |
| 采集状态 | `dict_collect_status` | 启用 success · 停用 info |

---

## 4. Element Plus 组件模式（OPS 现网）

### 4.1 表单与选择器（铁律）

| 场景 | 组件 | 禁止 |
|------|------|------|
| 枚举 | `<DictSelect dict-type="dict_*" />` | 硬编码 option |
| 用户 | `<UserSelect />` · Football `system_users.id`（ADR-056） | 手输 userId |
| IP 组 | `<IpGroupTreeSelect scope="all|led" />` | 仅 ID 无校验 |
| 实名人/手机/卡/公司/平台账号 | `RealNameSelect` / `PhoneSelect` / `SimCardSelect` / `CompanySelect` / `AccountSelect` | 自由文本关联 ID |
| 日期 | `el-date-picker` · `value-format="YYYY-MM-DD"` | — |

### 4.2 表格 + 分页

| 项 | 规范 |
|----|------|
| 分页参数 | 与 API 一致：`pageNo` + `pageSize`（M2 内容 list 部分接口为 `pageNum` · 以 API-M2 为准） |
| 默认 pageSize | 10（账号 20） |
| 操作列 | 固定右侧 · 文字链 `link` · 危险操作用 `danger` + 二次确认 |
| 批量 | 勾选 + 顶栏批量按钮（内容审核/删除 · ADR-081） |

### 4.3 抽屉与对话框

| 类型 | 宽度 | 用途 |
|------|------|------|
| `el-drawer` | 480px / 720px | 监测详情、内容创作、工作任务登记 |
| `el-dialog` | 520px | 单表单 CRUD |
| 全屏 dialog | 90% | SOP DAG、大屏预览 |

### 4.4 空态 / 错误 / 加载

| 状态 | UI |
|------|-----|
| 加载 | 表格 `v-loading` · 图表 skeleton |
| 空列表 | `el-empty` + 引导主按钮（有 create 权限时） |
| 403 | `el-result`「无权限」+ 返回首页 |
| API 1500–1504 | `ElMessage.error` 展示后端 msg（GLOBAL-CONVENTIONS） |
| Stub（ADR-060） | Alert「功能迁移中」+ 文档链接，**不**伪造数据 |

---

## 5. 权限门控

```
路由 meta.permission  -->  无菜单则不可达
页面内 v-hasPermi       -->  隐藏按钮
行级 / 数据权限         -->  后端 1504 + 空列表
```

| 模式 | 示例 |
|------|------|
| 列表 | `oa:content:list` / `ops:work-task:list` |
| 写 | `oa:content:update` · `:create` · `:delete` |
| 特殊 | `oa:content:typeset` · `ops:content:typeset`（AI/一键排版） |

---

## 6. 路由命名约定

| 规则 | 示例 |
|------|------|
| 前缀 | `#/ops/{一级 path 段}/{页面 path 段}` |
| 配置类重复段 | `#/ops/config/config-ai-model`（目录 `config` + 页 `config-ai-model`） |
| 隐藏页 | `#/ops/production/content/edit` · menu `hide_in_menu` |
| 深链参数 | `:id` · query `?tab=matrix`（实现允许时） |

**反模式（Spec 历史）**：`/account-analysis`、`/config-metadata`、`/collect/task` 等 **无** `/ops/{group}/` 前缀的 standalone 路径 — 仅兼容 :3000，**E2E 与 PRD 以 Football 嵌套路由为准**。

---

## 7. 图表与导出（M1/M6/M7）

| 库 | 用途 |
|----|------|
| ECharts 5 | 折线/柱/饼/双轴；响应 `resize` |
| 客户端导出 | `xlsx` / 表格 copy（直播时长等 · UX-M6） |
| 服务端导出 | 按钮触发 POST/GET export · **须与 Controller 参数位置一致**（见 SPEC-VS-IMPL P0-5） |

---

## 8. 「完整页面规范」Checklist（最小集）

> 计分 SSOT：[`OPS-UX-PAGE-COVERAGE-20261002.md`](../delivery/OPS-UX-PAGE-COVERAGE-20261002.md) · 达标线 **≥85/100**

| # | 项 | 验收要点 |
|---|-----|----------|
| 1 | 路由 + 权限 | Football 嵌套路由 + `permission` + 按钮 `v-hasPermi` |
| 2 | 布局 A/B/C | 页头 / 筛选 / 数据区（或文档变体：树+Tab、全屏大屏） |
| 3 | 筛选区 | 每项组件类型（DictSelect/UserSelect/…）+ query 字段名 |
| 4 | 表格列 | 列名、字典渲染、脱敏列标注 |
| 5 | 行操作 | 链接按钮、显隐条件、危险色 |
| 6 | 主按钮 | A 区 create/import/export 等 + 权限 |
| 7 | 新建/编辑 | drawer/dialog 字段表 + 组件 + 必填 |
| 8 | 三态 | empty / loading / error（含 403、1500–1504） |
| 9 | 确认流 | 删除、驳回、批量、替换等 MessageBox |
| 10 | API 引用 | 列表/写操作 endpoint + 分页参数名 |
| 11 | 边缘 | ADR、stub、数据范围、深链 query |
| 12 | 二级面 | Tab/抽屉/隐藏路由单独一节（若交互独立） |

---

## 9. 关联文档

| 文档 | 作用 |
|------|------|
| [`UX-OPS-页面原型索引.md`](./UX-OPS-页面原型索引.md) | 菜单 → 线框区 A/B/C → 截图 |
| [`OPS-UX-PAGE-COVERAGE-20261002.md`](../delivery/OPS-UX-PAGE-COVERAGE-20261002.md) | 全路由覆盖矩阵 |
| [`GLOBAL-CONVENTIONS.md`](../engineering/GLOBAL-CONVENTIONS.md) | 字典 · 选择器 · 错误码 · 加密 |
| [`TECH-CONSTRAINTS.md`](../engineering/TECH-CONSTRAINTS.md) | Vue 3 + Element Plus |
| 各 `UX-M*.md` | 页面级控件 ID · FR/AC |

---

## CHANGELOG

| 日期 | 说明 |
|------|------|
| 2026-10-02 | v1.1 §8 完整页面规范 Checklist · 覆盖报告链接 |
| 2026-10-02 | v1.0 初版：OPS 壳、网格、组件、路由、空态/权限 |
