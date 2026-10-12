<script setup lang="ts">
import BizRemote from "./BizRemote.vue";
import { accounts } from "@/demo/master-data";

defineProps<{ platform?: string; status?: string; ipGroupId?: string; multiple?: boolean }>();
const model = defineModel<string | string[] | null>({ default: null });
</script>

<template>
  <BizRemote v-model="model" :rows="accounts" :multiple="multiple" :platform="platform" :status="status" :ip-group-id="ipGroupId" placeholder="请选择平台账号" />
</template>
