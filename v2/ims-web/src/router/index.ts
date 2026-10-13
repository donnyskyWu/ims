import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { inDingTalk, landingPath } from "@/views/login-logic";

const RESET_PATHS = new Set(["/account/password", "/password-reset"]);

function placeholderRoutes(): RouteRecordRaw[] {
  const soon = () => import("@/views/workbench/SoonView.vue");
  const pages: Array<[string, string, string]> = [
    ["ims/workbench/soon", "workbench-soon", "后续功能"],
    ["ims/asset/mine", "asset-mine", "我名下资产"],
    ["ims/cert/archive", "cert-archive", "我的证件"],
    ["ims/live/ledger", "live-ledger", "我的场次"],
    ["ims/content/review", "content-review", "内容审核"],
    ["ims/content/task", "content-task", "任务确认"],
    ["ims/live/alarm", "live-alarm", "直播告警"],
    ["ims/alert/realtime", "alert-realtime", "实时告警"],
    ["ims/train/learn", "train-learn", "学习任务"],
  ];
  return pages.map(([path, name, title]) => ({ path, name, component: soon, meta: { menuless: true, title } }));
}

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
    { path: "ims/system/job", name: "sys-job", component: () => import("@/views/system/JobView.vue"), meta: { perm: "ims:system:job:query", title: "定时任务" } },
    { path: "ims/auth/org", name: "auth-org", component: () => import("@/views/auth/OrgSyncView.vue"), meta: { perm: "ims:system:org-sync:query" } },
    {
      path: "ims/auth/position",
      name: "auth-position",
      component: () => import("@/views/auth/PositionRuleView.vue"),
      meta: { perm: "ims:auth:position-rule:query" },
    },
    { path: "ims/workbench", name: "workbench", component: () => import("@/views/workbench/HomeView.vue"), meta: { menuless: true, title: "工作台" } },
    { path: "ims/workbench/todos", name: "workbench-todos", component: () => import("@/views/workbench/TodosView.vue"), meta: { menuless: true, title: "待办中心" } },
    { path: "ims/workbench/messages", name: "workbench-messages", component: () => import("@/views/workbench/MessagesView.vue"), meta: { menuless: true, title: "消息中心" } },
    { path: "ims/flow/task", name: "flow-task", component: () => import("@/views/flow/TaskView.vue"), meta: { title: "我的流程" } },
    { path: "ims/flow/board", name: "flow-board", component: () => import("@/views/flow/BoardView.vue"), meta: { title: "流程看板", perm: "ims:flow:board:query" } },
    { path: "ims/flow/template", name: "flow-template", component: () => import("@/views/flow/TemplateView.vue"), meta: { title: "模板管理", perm: "ims:flow:template:query" } },
    { path: "ims/flow/timeout", name: "flow-timeout", component: () => import("@/views/flow/TimeoutView.vue"), meta: { title: "超时督办", perm: "ims:flow:timeout:query" } },
    { path: "ims/flow/version/:templateId", name: "flow-version", component: () => import("@/views/flow/VersionView.vue"), meta: { menuless: true, title: "版本管理" } },
    { path: "ims/flow/mine", redirect: "/ims/flow/task" },
    { path: "ims/corp/resource/company", name: "corp-company", component: () => import("@/views/resource/CompanyView.vue"), meta: { title: "公司管理", perm: "ims:corp:company:query" } },
    { path: "ims/corp/resource/realname", name: "corp-realname", component: () => import("@/views/resource/RealnameView.vue"), meta: { title: "实名人管理", perm: "ims:corp:realname:query" } },
    { path: "ims/corp/resource/sim-card", name: "corp-sim", component: () => import("@/views/resource/SimCardView.vue"), meta: { title: "手机卡管理", perm: "ims:corp:sim:query" } },
    {
      path: "ims/corp/resource/certificate",
      name: "corp-certificate",
      component: () => import("@/views/resource/CertificateView.vue"),
      meta: {
        title: "证件管理",
        anyPerm: ["ims:cert:archive:query", "ims:cert:expire:query", "ims:cert:security:config", "ims:cert:security:log"],
      },
    },
    { path: "ims/corp/device/office", name: "device-office", component: () => import("@/views/device/LedgerView.vue"), meta: { title: "办公设备管理", perm: "ims:device:asset:query", deviceKind: "office" } },
    { path: "ims/corp/device/live", name: "device-live", component: () => import("@/views/device/LedgerView.vue"), meta: { title: "直播设备管理", perm: "ims:device:asset:query", deviceKind: "live" } },
    { path: "ims/corp/device/phone", name: "device-phone", component: () => import("@/views/device/PhoneView.vue"), meta: { title: "手机设备管理", perm: "ims:device:phone:query" } },
    { path: "ims/corp/account/wechat-official", name: "account-wechat-official", component: () => import("@/views/account/PlatformView.vue"), meta: { title: "公众号", perm: "ims:corp:account:query", platform: "WECHAT_MP" } },
    { path: "ims/corp/account/wechat-channels", name: "account-wechat-channels", component: () => import("@/views/account/PlatformView.vue"), meta: { title: "视频号", perm: "ims:corp:account:query", platform: "WECHAT_CHANNELS" } },
    { path: "ims/corp/account/douyin", name: "account-douyin", component: () => import("@/views/account/PlatformView.vue"), meta: { title: "抖音", perm: "ims:corp:account:query", platform: "DOUYIN" } },
    { path: "ims/corp/account/kuaishou", name: "account-kuaishou", component: () => import("@/views/account/PlatformView.vue"), meta: { title: "快手", perm: "ims:corp:account:query", platform: "KUAISHOU" } },
    { path: "ims/corp/account/xiaohongshu", name: "account-xiaohongshu", component: () => import("@/views/account/PlatformView.vue"), meta: { title: "小红书", perm: "ims:corp:account:query", platform: "XIAOHONGSHU" } },
    { path: "ims/corp/account/personal", name: "account-personal", component: () => import("@/views/account/PersonalView.vue"), meta: { title: "个人账号", perm: "ims:corp:account:personal:query" } },
    { path: "ims/account/apply", name: "account-apply", component: () => import("@/views/account/ApplyView.vue"), meta: { menuless: true, title: "账号领用", perm: "ims:account:apply:query" } },
    { path: "ims/account/transfer", name: "account-transfer", component: () => import("@/views/account/TransferView.vue"), meta: { menuless: true, title: "账号流转", perm: "ims:account:transfer:query" } },
    { path: "ims/account/return", name: "account-return", component: () => import("@/views/account/ReturnView.vue"), meta: { menuless: true, title: "账号归还", perm: "ims:account:return:query" } },
    { path: "ims/account/recharge", name: "account-recharge", component: () => import("@/views/account/RechargeView.vue"), meta: { menuless: true, title: "冲话费", perm: "ims:account:recharge:query" } },
    { path: "ims/account/ledger", redirect: "/ims/corp/account/douyin" },
    { path: "ims/master/platform-account", redirect: "/ims/corp/account/douyin" },
    { path: "ims/master/personal-account", redirect: "/ims/corp/account/personal" },
    { path: "ims/asset/ledger", redirect: (to) => ({ path: "/ims/corp/device/office", query: { ...to.query, drawer: "ledger" } }) },
    { path: "ims/asset/reverse", redirect: (to) => ({ path: "/ims/corp/device/office", query: { ...to.query, drawer: "reverse" } }) },
    { path: "ims/asset/verify", redirect: (to) => ({ path: "/ims/corp/device/office", query: { ...to.query, drawer: "verify" } }) },
    {
      path: "ims/cert/expire",
      name: "cert-expire",
      redirect: (to) => ({ path: "/ims/corp/resource/certificate", query: { ...to.query, tab: "expire" } }),
    },
    ...placeholderRoutes(),
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
