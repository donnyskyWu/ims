<script setup lang="ts">
import BizRemote from "./BizRemote.vue";
import { assets } from "@/demo/master-data";

defineProps<{ multiple?: boolean }>();
const model = defineModel<string | string[] | null>({ default: null });
</script>

<template>
  <BizRemote v-model="model" :rows="assets" :multiple="multiple" placeholder="请选择设备" />
</template>
