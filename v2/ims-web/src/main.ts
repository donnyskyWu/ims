import { createApp } from "vue";
import { createPinia } from "pinia";
import ElementPlus from "element-plus";
import zhCn from "element-plus/es/locale/lang/zh-cn";
import "element-plus/dist/index.css";
import "@/styles/tokens.css";
import "@/styles/global.css";
import "@/styles/element.css";
import App from "./App.vue";
import { createAppRouter } from "./router";
import { setupPerm } from "./directives/perm";
import { installAuthBridge, useAuthStore } from "./stores/auth";

const app = createApp(App);
const pinia = createPinia();
app.use(pinia);
const router = await createAppRouter();
const auth = useAuthStore();
installAuthBridge(auth, () => {
  const redirect = router.currentRoute.value.fullPath;
  void router.replace({ path: "/login", query: { redirect } });
});
app.use(router);
app.use(ElementPlus, { locale: zhCn });
setupPerm(app);
app.mount("#app");
