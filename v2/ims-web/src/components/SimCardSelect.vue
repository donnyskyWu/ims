<script setup lang="ts">
import BizRemote from "./BizRemote.vue";
import { simCards } from "@/demo/master-data";

defineProps<{ multiple?: boolean }>();
const model = defineModel<string | string[] | null>({ default: null });
</script>

<template>
  <BizRemote v-model="model" :rows="simCards" :multiple="multiple" placeholder="请选择手机卡" />
</template>
