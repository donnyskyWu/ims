# B0b 覆盖对照

对照 `docs/ims-v2-rewrite/modules/B0b-前端基础层/01-功能点清单.md`（76 个功能点，评审状态：zhang wu 已通过）。实现在 `v2/ims-web/`。未改旧前端 `ims-web/`，未改 B1 业务页。

## 验证

在 `v2/ims-web` 执行：

| 命令 | 结果 |
| --- | --- |
| `pnpm exec vue-tsc --noEmit` | 通过 |
| `pnpm exec eslint . --max-warnings 0` | 通过 |
| `pnpm exec stylelint "src/**/*.{css,vue}"` | 通过 |
| `pnpm test` | 9 个文件、24 条通过 |
| `pnpm build` | 生产构建通过 |
| `pnpm exec vite --host 127.0.0.1 --port 6174` | 开发服务可启动 |

生产包产物中没有 `/demo/tokens`、`/demo/list`、`/demo/workbench` 等示例页路由。生成客户端仍带有 B0a 已发布的示例域接口路径，这是接口清单，不是页面路由。

本环境未做浏览器手工走查。组件冒烟覆盖金额、空态、页头、状态标签；请求层、字典、会话、权限、部门移动规则和 lint 规则有单测。

## 对齐说明（不单列未完成）

- 字典简表按清单调用 `GET /system/dict-data/simple-list`，封装在 `src/api/generated/endpoints.ts`。B0a 合并后的 OpenAPI 目录未收录该路径。
- 未读数使用已生成的 `GET /message/unread-count`，不是清单里的 `/message/my/unread-count`。
- `/auth/me` 按 B0a 实际返回做了归一：权限明细缺失时，拥有权限码即视为可读、可写、可删；强制改密标记来自登录响应。
- 部门来源「本地」的颜色跟字典 `colorType`。B0a 种子里 `LOCAL` 是 `primary`，页面不另写青色。
- 「待确认」是 `localOrphan` 标记，字典 `dict_dept_source` 没有对应值，文案用清单原文，颜色用警告色组。
- B0a 文件场景没有 `AVATAR`。示例页头像使用已注册的 `TEST_IMAGE`。
- 人员简表接口忽略关键字，人员选择在已返回页上再按关键字过滤。
- 本批只做前端，没有另写部门树造数脚本。示例页使用 B0a 接口和 `src/demo/master-data.ts`。

## 功能点

| 功能点 | 名称 | 实现位置 | 结果 |
| --- | --- | --- | --- |
| FP-T-01 | 全局 Token | `src/styles/tokens.css` | 通过 |
| FP-T-02 | Element Plus 主题覆盖 | `src/styles/element.css` | 通过 |
| FP-T-03 | 状态色 8 组 | `src/styles/tokens.css`、`src/utils/status-color.ts` | 通过 |
| FP-T-04 | lint 规则 | `eslint/plugin.js`、`stylelint.config.js`、`src/eslint-rules.test.ts` | 通过 |
| FP-R-01 | Axios 实例与统一解包 | `src/api/http.ts`、`src/api/generated/endpoints.ts` | 通过 |
| FP-R-02 | 错误码处理策略 | `src/api/error-policy.ts`、`src/api/error-codes.json` | 通过 |
| FP-R-03 | 令牌刷新与跳登录 | `src/api/http.ts`、`src/stores/auth.ts` | 通过 |
| FP-R-04 | 会话 Store | `src/stores/auth.ts` | 通过 |
| FP-R-05 | 权限判断 | `src/utils/perm.ts`、`src/directives/perm.ts`、`src/components/Perm.vue` | 通过 |
| FP-R-06 | 字典 Store | `src/stores/dict.ts` | 通过 |
| FP-R-07 | 路由守卫与动态路由 | `src/router/index.ts`、`src/router/access.ts`、`src/router/demo-routes.ts` | 通过 |
| FP-R-08 | 格式化工具 | `src/utils/format.ts` | 通过 |
| FP-C01-01 | AppLayout 应用框架 | `src/layouts/ShellLayout.vue` | 通过 |
| FP-C02-01 | PageHeader 页头 | `src/components/PageHeader.vue` | 通过 |
| FP-C03-01 | Tabs / CatTabs | `src/components/AppTabs.vue` | 通过 |
| FP-C04-01 | Breadcrumb / DrillPath | `src/components/DrillPath.vue` | 通过 |
| FP-C05-01 | PermissionGate | `src/directives/perm.ts`、`src/components/Perm.vue` | 通过 |
| FP-C06-01 | QueryBar 查询栏 | `src/components/QueryBar.vue` | 通过 |
| FP-C07-01 | DataTable 数据表格 | `src/components/DataTable.vue` | 通过 |
| FP-C08-01 | Pagination 分页 | `src/components/AppPagination.vue` | 通过 |
| FP-C09-01 | StatusTag 状态标签 | `src/components/StatusTag.vue` | 通过 |
| FP-C10-01 | StatCard / KPI 栅格 | `src/components/StatCard.vue` | 通过 |
| FP-C11-01 | EmptyState 空状态 | `src/components/EmptyState.vue` | 通过 |
| FP-C12-01 | Chip / FilterChip | `src/components/FilterChip.vue` | 通过 |
| FP-C13-01 | LeftTreeRightTable 左树右表组件 | `src/layouts/LeftTreeLayout.vue` | 通过 |
| FP-C14-01 | FormDrawer 表单抽屉 | `src/components/FormDrawer.vue` | 通过 |
| FP-C15-01 | DetailDrawer 详情抽屉 | `src/components/DetailDrawer.vue` | 通过 |
| FP-C16-01 | ConfirmDialog 确认框 | `src/components/confirm.ts`、`src/components/ConfirmHost.vue` | 通过 |
| FP-C17-01 | FormField / FormRules | `src/components/form/rules.ts` | 通过 |
| FP-C18-01 | Modal 居中弹窗 | `src/components/AppModal.vue` | 通过 |
| FP-C19-01 | StepsWizard 分步向导 | `src/components/StepsWizard.vue` | 通过 |
| FP-C20-01 | Toast / Message | `src/utils/toast.ts` | 通过 |
| FP-C21-01 | UserSelect 人员选择 | `src/components/UserSelect.vue` | 通过 |
| FP-C22-01 | DeptTreeSelect 部门树选择 | `src/components/DeptTreeSelect.vue`、`src/stores/dept.ts` | 通过 |
| FP-C23-01 | PositionSelect / RoleSelect | `src/components/PositionSelect.vue`、`src/components/RoleSelect.vue` | 通过 |
| FP-C24-01～C28-01、C31-01 | 业务主数据选择器 | `src/components/BizRemote.vue`、`RealNameSelect.vue`、`AccountSelect.vue`、`AuthorSelect.vue`、`IpGroupSelect.vue`、`CompanySelect.vue`、`AssetSelect.vue`、`SimCardSelect.vue`、`MatchSelect.vue`、`TopicSelect.vue`、`src/demo/master-data.ts` | 通过 |
| FP-C29-01 | DictSelect 字典下拉 | `src/components/DictSelect.vue` | 通过 |
| FP-C30-01 | DateRangePicker / PeriodPicker | `src/components/PeriodPicker.vue` | 通过 |
| FP-C32-01 | RemoteSelect 基座 | `src/components/RemoteSelect.vue` | 通过 |
| FP-C33-01 | FileUpload 上传 | `src/components/FileUpload.vue`、`src/api/scenes.ts`、`src/api/file-scenes.json` | 通过 |
| FP-C34-01 | FilePreview / SecureImage | `src/components/FilePreview.vue` | 通过 |
| FP-C35-01 | ImportDialog 导入 | `src/components/ImportDialog.vue` | 通过 |
| FP-C36-01 | ExportButton + DownloadBar | `src/components/ExportButton.vue`、`src/components/DownloadBar.vue`、`src/stores/download.ts` | 通过 |
| FP-C37-01 | Timeline 时间线 | `src/components/Timeline.vue` | 通过 |
| FP-C38-01 | DescriptionList 详情字段 | `src/components/DescriptionList.vue` | 通过 |
| FP-C39-01 | MaskedText / MoneyText / PercentText | `src/components/MaskedText.vue`、`MoneyText.vue`、`PercentText.vue` | 通过 |
| FP-C40-01 | Chart 图表封装 | `src/components/ChartPanel.vue` | 通过 |
| FP-C41-01 | TraceGraph / FlowDesigner（只读） | `src/components/TraceGraph.vue`、`src/components/FlowDesigner.vue` | 通过 |
| FP-C42-01 | 树渲染与节点信息 | `src/components/DeptTree.vue`、`DeptBranch.vue`、`src/stores/dept.ts` | 通过 |
| FP-C42-02 | 搜索 | `src/components/DeptTree.vue`、`src/components/dept/tree-logic.ts` | 通过 |
| FP-C42-03 | 选中与对外事件 | `src/components/DeptTree.vue`、`src/components/dept/tree-logic.ts` | 通过 |
| FP-C42-04 | 节点更多菜单 | `src/components/DeptTree.vue` | 通过 |
| FP-C42-05 | 新增下级 / 改名 | `src/components/DeptTree.vue` | 通过 |
| FP-C42-06 | 移动 | `src/components/DeptTree.vue`、`src/components/dept/tree-logic.ts` | 通过 |
| FP-C42-07 | 停用 / 启用 / 删除 / 确认保留 | `src/components/DeptTree.vue` | 通过 |
| FP-C42-08 | 同步钉钉组织 | `src/components/DeptTree.vue` | 通过 |
| FP-L01 | 标准列表页 | `src/views/demo/ListView.vue` | 通过 |
| FP-L02 | 统计卡 + Tab 列表页 | `src/views/demo/TabsListView.vue` | 通过 |
| FP-L03 | 左树右表页 | `src/views/demo/LeftTreeView.vue`、`src/layouts/LeftTreeLayout.vue` | 通过 |
| FP-L04 | 看板 / 统计页 | `src/views/demo/WorkbenchView.vue` | 通过 |
| FP-L05 | 工作台页 | `src/views/demo/WorkbenchView.vue` | 通过 |
| FP-L06 | 设计器 / 编辑器页 | `src/views/demo/WorkbenchView.vue`、`src/components/FlowDesigner.vue` | 通过 |
| FP-L07 | 填报 / 作答页 | `src/layouts/FillLayout.vue`、`src/views/demo/FillView.vue` | 通过 |
| FP-L08 | 详情抽屉模板 | `src/components/DetailDrawer.vue`、`src/views/demo/WorkbenchView.vue` | 通过 |
| FP-P-01 | `/demo/tokens` | `src/views/demo/TokensView.vue` | 通过 |
| FP-P-02 | `/demo/request` | `src/views/demo/RequestView.vue` | 通过 |
| FP-P-03 | `/demo/layout` | `src/views/demo/LayoutView.vue` | 通过 |
| FP-P-04 | `/demo/list` | `src/views/demo/ListView.vue` | 通过 |
| FP-P-05 | `/demo/tabs-list` | `src/views/demo/TabsListView.vue` | 通过 |
| FP-P-06 | `/demo/form` | `src/views/demo/FormView.vue` | 通过 |
| FP-P-07 | `/demo/selectors` | `src/views/demo/SelectorsView.vue` | 通过 |
| FP-P-08 | `/demo/files` | `src/views/demo/FilesView.vue` | 通过 |
| FP-P-09 | `/demo/display` | `src/views/demo/DisplayView.vue` | 通过 |
| FP-P-10 | `/demo/dept-tree` | `src/views/demo/DeptTreeView.vue` | 通过 |
| FP-P-11 | `/demo/left-tree-right-table` | `src/views/demo/LeftTreeView.vue` | 通过 |
| FP-P-12 | `/demo/workbench`、`/demo/fill` | `src/views/demo/WorkbenchView.vue`、`src/views/demo/FillView.vue` | 通过 |

通过 76，未完成 0。
