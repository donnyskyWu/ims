import type { RouteRecordRaw } from "vue-router";

export const demoChildRoutes: RouteRecordRaw[] = [
  { path: "demo/tokens", component: () => import("@/views/demo/TokensView.vue") },
  { path: "demo/request", component: () => import("@/views/demo/RequestView.vue") },
  { path: "demo/layout", component: () => import("@/views/demo/LayoutView.vue") },
  { path: "demo/list", component: () => import("@/views/demo/ListView.vue"), meta: { perm: "ims:demo:order:query" } },
  { path: "demo/tabs-list", component: () => import("@/views/demo/TabsListView.vue"), meta: { perm: "ims:demo:order:query" } },
  { path: "demo/form", component: () => import("@/views/demo/FormView.vue") },
  { path: "demo/selectors", component: () => import("@/views/demo/SelectorsView.vue") },
  { path: "demo/files", component: () => import("@/views/demo/FilesView.vue"), meta: { perm: "ims:demo:order:query" } },
  { path: "demo/display", component: () => import("@/views/demo/DisplayView.vue") },
  {
    path: "demo/dept-tree",
    component: () => import("@/views/demo/DeptTreeView.vue"),
    meta: { anyPerm: ["ims:system:dept:query", "ims:system:user:query"] },
  },
  { path: "demo/left-tree-right-table", component: () => import("@/views/demo/LeftTreeView.vue"), meta: { perm: "ims:system:user:query" } },
  { path: "demo/workbench", component: () => import("@/views/demo/WorkbenchView.vue") },
];

export const demoFillRoute: RouteRecordRaw = {
  path: "/demo/fill",
  component: () => import("@/layouts/FillLayout.vue"),
  meta: { menuless: true },
  children: [{ path: "", component: () => import("@/views/demo/FillView.vue"), meta: { menuless: true } }],
};
