import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router";
import { useAuthStore } from "@/stores/auth";

export async function createAppRouter() {
  const children: RouteRecordRaw[] = [
    { path: "", name: "home", component: () => import("@/views/HomeView.vue"), meta: { menuless: true } },
    { path: "account/password", name: "password", component: () => import("@/views/PasswordView.vue"), meta: { menuless: true } },
  ];
  const routes: RouteRecordRaw[] = [
    { path: "/login", component: () => import("@/views/LoginView.vue"), meta: { public: true } },
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
    if (to.meta.public) return true;
    if (!auth.accessToken) return { path: "/login", query: { redirect: to.fullPath } };
    if (!auth.ready) {
      try {
        await auth.fetchMe();
      } catch {
        auth.clearLocal();
        return { path: "/login", query: { redirect: to.fullPath } };
      }
    }
    if (auth.pwdResetRequired && to.path !== "/account/password") return "/account/password";
    return true;
  });
  return router;
}
