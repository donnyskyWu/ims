<script setup lang="ts">
import { computed } from "vue";
import { useAuthStore } from "@/stores/auth";
import { hasAllPerm, hasAnyPerm, isPermCode, type PermAction } from "@/utils/perm";

const props = defineProps<{ code: string | string[]; all?: boolean; action?: PermAction }>();
const auth = useAuthStore();
const visible = computed(() => {
  const codes = Array.isArray(props.code) ? props.code : [props.code];
  for (const item of codes) {
    if (!isPermCode(item) && import.meta.env.DEV) console.error("权限码格式不正确");
  }
  const state = { permCodes: auth.permCodes, permDetails: auth.permDetails };
  return props.all ? hasAllPerm(state, codes, props.action) : hasAnyPerm(state, codes, props.action);
});
</script>

<template>
  <slot v-if="visible" />
</template>
