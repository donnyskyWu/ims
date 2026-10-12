<script setup lang="ts">
import { computed } from "vue";
import { fmtMoney, moneyNegative } from "@/utils/format";

const props = defineProps<{ value: string | number | null | undefined }>();
const text = computed(() => fmtMoney(props.value));
const neg = computed(() => moneyNegative(props.value));
</script>

<template>
  <span class="num" :class="{ neg }">{{ text }}</span>
</template>
