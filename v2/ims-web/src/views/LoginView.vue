<script setup lang="ts">
import { ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { BizError } from "@/api/http";
import { dingtalkLoginUrl } from "@/api/generated/endpoints";

const username = ref("");
const password = ref("");
const error = ref("");
const auth = useAuthStore();
const route = useRoute();
const router = useRouter();

async function submit() {
  error.value = "";
  try {
    await auth.login(username.value.trim(), password.value);
    const redirect = typeof route.query.redirect === "string" ? route.query.redirect : "/";
    await router.replace(auth.pwdResetRequired ? "/account/password" : redirect);
  } catch (caught) {
    error.value = (caught as BizError).msg || "登录失败";
  }
}

function dingtalk() {
  const redirect = typeof route.query.redirect === "string" ? route.query.redirect : "/";
  window.location.href = dingtalkLoginUrl(redirect);
}
</script>

<template>
  <div class="login">
    <form class="card" @submit.prevent="submit">
      <h1>登录</h1>
      <label class="fld">账号<input v-model="username" /></label>
      <label class="fld">密码<input v-model="password" type="password" /></label>
      <p v-if="error" class="ferr">{{ error }}</p>
      <button class="btn btn-pri" type="submit">登录</button>
      <button class="btn btn-sec" type="button" @click="dingtalk">钉钉扫码登录</button>
    </form>
  </div>
</template>

<style scoped>
.login { min-height: 100%; display: grid; place-items: center; }
form { width: 360px; display: flex; flex-direction: column; gap: 12px; }
h1 { font-size: 28px; margin: 0; }
input { width: 100%; height: 34px; border: 1px solid var(--line2); border-radius: var(--r-s); padding: 0 10px; }
</style>
