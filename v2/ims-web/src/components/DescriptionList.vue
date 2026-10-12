<script setup lang="ts">
import { emptyText, fmtMoney, fmtPercent, fmtTime } from "@/utils/format";
import StatusTag from "./StatusTag.vue";
import MaskedText from "./MaskedText.vue";

defineProps<{
  items: { label: string; value: unknown; type?: "money" | "percent" | "time" | "status" | "masked" | "file"; span?: number; dictType?: string }[];
  cols?: number;
}>();
</script>

<template>
  <div class="desc-grid">
    <template v-for="item in items" :key="item.label">
      <div class="k">{{ item.label }}</div>
      <div class="v" :style="item.span === 2 ? { gridColumn: '2 / -1' } : undefined">
        <StatusTag v-if="item.type === 'status'" :dict-type="item.dictType || ''" :value="item.value as string" />
        <MaskedText v-else-if="item.type === 'masked'" :value="item.value as string" />
        <span v-else-if="item.type === 'money'">{{ fmtMoney(item.value as string) }}</span>
        <span v-else-if="item.type === 'percent'">{{ fmtPercent(item.value as string) }}</span>
        <span v-else-if="item.type === 'time'">{{ fmtTime(item.value as string) }}</span>
        <span v-else>{{ emptyText(item.value) }}</span>
      </div>
    </template>
  </div>
</template>
