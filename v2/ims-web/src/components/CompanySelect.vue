<script setup lang="ts">
import BizRemote from "./BizRemote.vue";
import { companies } from "@/demo/master-data";

defineProps<{ multiple?: boolean }>();
const model = defineModel<string | string[] | null>({ default: null });
</script>

<template>
  <BizRemote v-model="model" :rows="companies" :multiple="multiple" placeholder="请选择公司" />
</template>
