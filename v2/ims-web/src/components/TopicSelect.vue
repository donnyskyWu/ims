<script setup lang="ts">
import BizRemote from "./BizRemote.vue";
import { topics } from "@/demo/master-data";

defineProps<{ multiple?: boolean }>();
const model = defineModel<string | string[] | null>({ default: null });
</script>

<template>
  <BizRemote v-model="model" :rows="topics" :multiple="multiple" placeholder="请选择选题" />
</template>
