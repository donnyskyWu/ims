import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { inDingTalk, landingPath } from "@/views/login-logic";

const RESET_PATHS = new Set(["/account/password", "/password-reset"]);

export async function createAppRouter() {
  const children: RouteRecordRaw[] = [
    { path: "", name: "home", component: () => import("@/views/HomeView.vue"), meta: { menuless: true } },
    { path: "account/password", name: "password", component: () => import("@/views/PasswordView.vue"), meta: { menuless: true } },
    { path: "password-reset", name: "password-reset", component: () => import("@/views/PasswordView.vue"), meta: { menuless: true } },
    { path: "ims/profile", name: "profile", component: () => import("@/views/system/ProfileView.vue"), meta: { menuless: true } },
    { path: "ims/system/user", name: "sys-user", component: () => import("@/views/system/UserView.vue"), meta: { perm: "ims:system:user:query" } },
    { path: "ims/system/role", name: "sys-role", component: () => import("@/views/system/RoleView.vue"), meta: { perm: "ims:system:role:query" } },
    { path: "ims/system/menu", name: "sys-menu", component: () => import("@/views/system/MenuView.vue"), meta: { perm: "ims:system:menu:query" } },
    { path: "ims/system/dict", name: "sys-dict", component: () => import("@/views/system/DictView.vue"), meta: { perm: "ims:system:dict:query" } },
    { path: "ims/system/param", name: "sys-param", component: () => import("@/views/system/ParamView.vue"), meta: { perm: "ims:system:param:query" } },
    { path: "ims/system/log", name: "sys-log", component: () => import("@/views/system/LogView.vue"), meta: { perm: "ims:system:log:query" } },
    { path: "ims/system/notify", name: "sys-notify", component: () => import("@/views/system/NotifyView.vue"), meta: { perm: "ims:system:notify:query" } },
    { path: "ims/system/tenant", name: "sys-tenant", component: () => import("@/views/system/TenantView.vue"), meta: { perm: "ims:tenant:query" } },
    { path: "ims/auth/org", name: "auth-org", component: () => import("@/views/auth/OrgSyncView.vue"), meta: { perm: "ims:system:org-sync:query" } },
    {
      path: "ims/auth/position",
      name: "auth-position",
      component: () => import("@/views/auth/PositionRuleView.vue"),
      meta: { perm: "ims:auth:position-rule:query" },
    },
  ];
  const routes: RouteRecordRaw[] = [
    { path: "/login", component: () => import("@/views/LoginView.vue"), meta: { public: true } },
    { path: "/dingtalk-login", component: () => import("@/views/DingTalkLoginView.vue"), meta: { public: true } },
    { path: "/sso-callback", component: () => import("@/views/SsoCallbackView.vue"), meta: { public: true } },
    { path: "/", component: () => import("@/layouts/ShellLayout.vue"), children },
  ];
  if (!import.meta.env.PROD) {
    const demo = await import("./demo-routes");
    children.push(...demo.demoChildRoutes);
    routes.push(demo.demoFillRoute);
  }
  const router = createRouter({ history: createWebHistory(), routes });
  router.beforeEach(async (to) => {
    const auth = useAuthStore();
    if (!auth.accessToken && to.path === "/login" && inDingTalk(navigator.userAgent) && to.query.account !== "1") {
      return { path: "/dingtalk-login", query: to.query };
    }
    if (to.meta.public && !auth.accessToken) return true;
    if (!auth.accessToken) {
      if (inDingTalk(navigator.userAgent) && to.path !== "/dingtalk-login") {
        return { path: "/dingtalk-login", query: { redirect: to.fullPath } };
      }
      return { path: "/login", query: { redirect: to.fullPath } };
    }
    if (!auth.ready) {
      try {
        await auth.fetchMe();
      } catch {
        auth.clearLocal();
        return { path: "/login", query: { redirect: to.fullPath } };
      }
    }
    if (auth.pwdResetRequired && !RESET_PATHS.has(to.path)) return "/password-reset";
    if (to.path === "/login" || to.path === "/dingtalk-login") return landingPath(auth.menus, "/");
    return true;
  });
  return router;
}
