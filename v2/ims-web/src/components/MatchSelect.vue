<script setup lang="ts">
import BizRemote from "./BizRemote.vue";
import { matches } from "@/demo/master-data";

defineProps<{ multiple?: boolean }>();
const model = defineModel<string | string[] | null>({ default: null });
</script>

<template>
  <BizRemote v-model="model" :rows="matches" :multiple="multiple" placeholder="请选择赛事" />
</template>
