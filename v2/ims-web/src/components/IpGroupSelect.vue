<script setup lang="ts">
import BizRemote from "./BizRemote.vue";
import { ipGroups } from "@/demo/master-data";

defineProps<{ multiple?: boolean }>();
const model = defineModel<string | string[] | null>({ default: null });
</script>

<template>
  <BizRemote v-model="model" :rows="ipGroups" tree :multiple="multiple" placeholder="请选择分组" />
</template>
