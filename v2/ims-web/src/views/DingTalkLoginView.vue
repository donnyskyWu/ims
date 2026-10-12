<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { call } from "@/api/generated/endpoints";
import { BizError } from "@/api/http";
import { useAuthStore } from "@/stores/auth";
import { landingPath } from "./login-logic";

const auth = useAuthStore();
const route = useRoute();
const router = useRouter();
const error = ref("");
const corpId = ref("");

onMounted(async () => {
  try {
    const options = await call<{ corpId: string; dingtalkEnabled: boolean }>("login_options_admin_api_ims_auth_login_options_get", { silent: true });
    corpId.value = options.corpId || "";
    if (!options.dingtalkEnabled) {
      await router.replace({ path: "/login", query: { ...route.query, account: "1" } });
      return;
    }
    const bridge = (window as unknown as { dd?: { runtime?: { permission?: { requestAuthCode: (opts: { corpId: string }) => Promise<{ code: string }> } } } }).dd;
    if (!bridge?.runtime?.permission?.requestAuthCode) {
      error.value = "当前环境不能发起钉钉免登";
      return;
    }
    const code = await bridge.runtime.permission.requestAuthCode({ corpId: corpId.value });
    await finish(code.code);
  } catch (caught) {
    error.value = (caught as BizError).msg || "钉钉登录失败";
  }
});

async function finish(authCode: string) {
  const data = await call<{ accessToken: string; refreshToken: string; pwdResetRequired?: boolean }>(
    "h5_login_admin_api_ims_auth_sso_dingtalk_h5_login_post",
    { body: { authCode }, silent: true },
  );
  auth.applySession(data);
  await auth.fetchMe();
  const redirect = typeof route.query.redirect === "string" ? route.query.redirect : "/";
  await router.replace(auth.pwdResetRequired ? "/password-reset" : landingPath(auth.menus, redirect));
}

function account() {
  void router.replace({ path: "/login", query: { ...route.query, account: "1" } });
}

function retry() {
  window.location.reload();
}
</script>

<template>
  <div class="gate">
    <p>{{ error || "正在通过钉钉登录…" }}</p>
    <button v-if="error" class="btn btn-pri" type="button" @click="retry">重试</button>
    <button v-if="error" class="btn btn-sec" type="button" @click="account">使用账号登录</button>
  </div>
</template>

<style scoped>
.gate { min-height: 100%; display: grid; place-items: center; gap: 12px; }
</style>
