<script setup lang="ts">
import { computed } from "vue";
import { fmtPercent } from "@/utils/format";

const props = defineProps<{ value: string | number | null | undefined }>();
const text = computed(() => fmtPercent(props.value));
</script>

<template>
  <span class="num">{{ text }}</span>
</template>
