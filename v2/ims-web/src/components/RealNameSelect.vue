<script setup lang="ts">
import BizRemote from "./BizRemote.vue";
import { realNames } from "@/demo/master-data";

withDefaults(defineProps<{ showCertWarning?: boolean; multiple?: boolean }>(), { showCertWarning: true, multiple: false });
const model = defineModel<string | string[] | null>({ default: null });
</script>

<template>
  <BizRemote v-model="model" :rows="realNames" :multiple="multiple" :show-cert-warning="showCertWarning" placeholder="请选择实名人" />
</template>
