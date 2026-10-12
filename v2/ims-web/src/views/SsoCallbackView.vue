<script setup lang="ts">
import { onMounted } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { landingPath } from "./login-logic";

const router = useRouter();
const auth = useAuthStore();

onMounted(async () => {
  const params = new URLSearchParams(window.location.hash.replace(/^#/, ""));
  const accessToken = params.get("accessToken") || "";
  const refreshToken = params.get("refreshToken") || "";
  const redirect = params.get("redirect") || "/";
  history.replaceState(null, "", window.location.pathname);
  if (accessToken) {
    auth.applySession({ accessToken, refreshToken });
    await auth.fetchMe();
    await router.replace(auth.pwdResetRequired ? "/password-reset" : landingPath(auth.menus, redirect));
    return;
  }
  await router.replace("/login");
});
</script>

<template>
  <p class="muted">正在完成登录…</p>
</template>
