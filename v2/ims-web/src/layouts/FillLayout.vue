<script setup lang="ts">
import { useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();
const router = useRouter();
async function logout() {
  await auth.logout();
  void router.push("/login");
}
</script>

<template>
  <div class="fill">
    <header class="top">
      <strong>填报</strong>
      <div>
        <span>{{ auth.user?.nickname }}</span>
        <button class="btn btn-txt" type="button" @click="logout">退出登录</button>
      </div>
    </header>
    <main><router-view /></main>
  </div>
</template>

<style scoped>
.fill { min-height: 100%; background: var(--bg); }
.top { height: var(--header-h); display: flex; align-items: center; justify-content: space-between; padding: 0 20px; background: var(--card); border-bottom: 1px solid var(--line); }
main { padding: var(--content-y) var(--content-x); }
</style>
