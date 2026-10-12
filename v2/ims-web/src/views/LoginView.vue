<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { BizError } from "@/api/http";
import { call, dingtalkLoginUrl } from "@/api/generated/endpoints";
import errorCodes from "@/api/error-codes.json";
import { landingPath, preferredTab, ssoErrorText } from "./login-logic";

const CHANNEL = "ims.login.channel";
const username = ref("");
const password = ref("");
const error = ref("");
const lockSeconds = ref(0);
const dingtalkEnabled = ref(false);
const tab = ref<"ding" | "account">("account");
const qrState = ref("");
const auth = useAuthStore();
const route = useRoute();
const router = useRouter();
let timer = 0;

const messages = Object.fromEntries(errorCodes.map((item) => [item.code, item.msg]));
const ssoText = computed(() => ssoErrorText(typeof route.query.ssoError === "string" ? route.query.ssoError : null, messages));
const redirect = computed(() => (typeof route.query.redirect === "string" ? route.query.redirect : "/"));

onMounted(async () => {
  tab.value = preferredTab(localStorage.getItem(CHANNEL), false);
  try {
    const data = await call<{ dingtalkEnabled: boolean }>("login_options_admin_api_ims_auth_login_options_get", { silent: true });
    dingtalkEnabled.value = Boolean(data.dingtalkEnabled);
    tab.value = preferredTab(localStorage.getItem(CHANNEL), dingtalkEnabled.value);
    if (tab.value === "ding") await loadQr();
  } catch (caught) {
    error.value = (caught as BizError).msg || "登录方式读取失败";
  }
});

async function loadQr() {
  const data = await call<{ state: string }>("authorize_params_admin_api_ims_auth_sso_dingtalk_authorize_params_get", {
    query: { redirect: redirect.value },
    silent: true,
  });
  qrState.value = data.state;
}

function pick(next: "ding" | "account") {
  tab.value = next;
  localStorage.setItem(CHANNEL, next);
  if (next === "ding" && !qrState.value) void loadQr();
}

async function submit() {
  error.value = "";
  if (!username.value.trim()) {
    error.value = "请输入用户名";
    return;
  }
  if (!password.value) {
    error.value = "请输入密码";
    return;
  }
  if (lockSeconds.value > 0) return;
  try {
    await auth.login(username.value.trim(), password.value);
    localStorage.setItem(CHANNEL, "account");
    const target = auth.pwdResetRequired ? "/password-reset" : landingPath(auth.menus, redirect.value);
    await router.replace(target);
  } catch (caught) {
    const biz = caught as BizError;
    password.value = "";
    error.value = biz.msg || "登录失败";
    const remain = Number((biz.data as { remainMinutes?: number } | null)?.remainMinutes || 0);
    if (biz.code === 1215 && remain > 0) startLock(remain * 60);
  }
}

function startLock(seconds: number) {
  lockSeconds.value = seconds;
  window.clearInterval(timer);
  timer = window.setInterval(() => {
    lockSeconds.value -= 1;
    if (lockSeconds.value <= 0) window.clearInterval(timer);
  }, 1000);
}

function dingtalk() {
  window.location.href = dingtalkLoginUrl(redirect.value);
}
</script>

<template>
  <div class="login">
    <form class="card" @submit.prevent="submit">
      <h1>登录</h1>
      <div v-if="dingtalkEnabled" class="tabs">
        <button type="button" class="btn" :class="tab === 'ding' ? 'btn-pri' : 'btn-sec'" @click="pick('ding')">钉钉扫码</button>
        <button type="button" class="btn" :class="tab === 'account' ? 'btn-pri' : 'btn-sec'" @click="pick('account')">账号登录</button>
      </div>
      <p v-if="ssoText" class="ferr">{{ ssoText }}</p>
      <template v-if="tab === 'ding'">
        <div class="qr">请使用钉钉扫码</div>
        <p class="muted">状态 {{ qrState.slice(0, 8) }}</p>
        <button class="btn btn-sec" type="button" @click="dingtalk">跳转钉钉页面登录</button>
      </template>
      <template v-else>
        <label class="fld">账号<input v-model="username" autocomplete="username" /></label>
        <label class="fld">密码<input v-model="password" type="password" autocomplete="current-password" /></label>
        <p v-if="error" class="ferr">{{ error }}</p>
        <p v-if="lockSeconds > 0" class="muted">请 {{ lockSeconds }} 秒后再试</p>
        <button class="btn btn-pri" type="submit" :disabled="lockSeconds > 0">登录</button>
      </template>
    </form>
  </div>
</template>

<style scoped>
.login { min-height: 100%; display: grid; place-items: center; }
form { width: 360px; display: flex; flex-direction: column; gap: 12px; }
h1 { font-size: 28px; margin: 0; }
input { width: 100%; height: 34px; border: 1px solid var(--line2); border-radius: var(--r-s); padding: 0 10px; }
.tabs { display: flex; gap: 8px; }
.qr { height: 180px; display: grid; place-items: center; border: 1px dashed var(--line2); border-radius: var(--r); color: var(--text2); }
</style>
