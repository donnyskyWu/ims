<script setup lang="ts">
import { computed } from "vue";
import { emptyText } from "@/utils/format";

const props = defineProps<{ value: string | null | undefined }>();
const text = computed(() => emptyText(props.value));
const hidden = computed(() => text.value.includes("***"));
</script>

<template>
  <span :title="hidden ? '无查看权限' : ''">{{ text }}</span>
</template>
