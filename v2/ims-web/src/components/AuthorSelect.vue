<script setup lang="ts">
import BizRemote from "./BizRemote.vue";
import { authors } from "@/demo/master-data";

defineProps<{ accountId?: string; multiple?: boolean }>();
const model = defineModel<string | string[] | null>({ default: null });
</script>

<template>
  <BizRemote v-model="model" :rows="authors" :account-id="accountId" :multiple="multiple" placeholder="请选择作者" />
</template>
