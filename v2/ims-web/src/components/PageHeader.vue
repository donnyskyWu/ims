<script setup lang="ts">
import { useAuthStore } from "@/stores/auth";

withDefaults(defineProps<{ title: string; subTitle?: string; showScope?: boolean }>(), { showScope: true });
const auth = useAuthStore();
</script>

<template>
  <header class="pg-h">
    <div>
      <h1>{{ title }}</h1>
      <p v-if="subTitle" class="sub">{{ subTitle }}</p>
    </div>
    <div class="right">
      <span v-if="showScope && auth.dataScopeText" class="scope">统计范围：{{ auth.dataScopeText }}</span>
      <slot name="actions" />
    </div>
  </header>
</template>

<style scoped>
.pg-h { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; margin-bottom: 16px; }
h1 { margin: 0; font-size: 28px; font-weight: 700; letter-spacing: -0.6px; }
.sub { margin: 4px 0 0; font-size: 13px; color: var(--text2); }
.right { display: flex; align-items: center; gap: 8px; }
.scope { font-size: 13px; color: var(--text2); }
</style>
