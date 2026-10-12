<script setup lang="ts">
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import PageHeader from "@/components/PageHeader.vue";
import { SOON_HINT } from "./logic";

const route = useRoute();
const router = useRouter();
const title = computed(() => String(route.meta.title || "后续功能"));
</script>

<template>
  <section>
    <p class="crumb">个人工作台 / {{ title }}</p>
    <PageHeader :title="title" :show-scope="false" />
    <div class="card soon">
      <h2>{{ SOON_HINT }}</h2>
      <p>当前只保留入口。回到工作台后，待办仍保持原来的状态。</p>
      <button class="btn btn-pri" type="button" @click="router.push('/ims/workbench')">返回工作台</button>
    </div>
  </section>
</template>

<style scoped>
.crumb { margin: 0 0 8px; color: var(--text2); font-size: 12px; }
.soon { padding: 28px; }
.soon h2 { margin: 0 0 8px; font-size: 18px; }
.soon p { color: var(--text2); }
</style>
