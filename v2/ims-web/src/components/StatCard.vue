<script setup lang="ts">
import { fmtMoney, fmtPercent, EMPTY_MARK } from "@/utils/format";

export interface StatItem {
  title: string;
  value: string | number | null;
  unit?: string;
  desc?: string;
  ratio?: number | null;
  format?: "money" | "percent" | "number";
  onClick?: () => void;
}

withDefaults(defineProps<{ items: StatItem[]; cols?: 3 | 4 }>(), { cols: 4 });

function show(item: StatItem): string {
  if (item.value === null || item.value === undefined || item.value === "") return EMPTY_MARK;
  if (item.format === "money") return fmtMoney(item.value);
  if (item.format === "percent") return fmtPercent(item.value);
  return `${item.value}${item.unit || ""}`;
}

function ratioClass(ratio: number | null | undefined): string {
  if (ratio === null || ratio === undefined) return "";
  if (ratio > 0) return "up";
  if (ratio < 0) return "down";
  return "flat";
}

function ratioText(ratio: number | null | undefined): string {
  if (ratio === null || ratio === undefined) return "";
  if (ratio > 0) return `↑ ${ratio}%`;
  if (ratio < 0) return `↓ ${Math.abs(ratio)}%`;
  return "0%";
}
</script>

<template>
  <div class="stat-grid" :class="cols === 3 ? 'cols-3' : 'cols-4'">
    <button
      v-for="(item, index) in items"
      :key="index"
      class="stat"
      :class="{ clickable: Boolean(item.onClick) }"
      type="button"
      @click="item.onClick?.()"
    >
      <div class="st">{{ item.title }}</div>
      <div class="sv" :class="{ neg: item.format === 'money' && Number(item.value) < 0 }">{{ show(item) }}</div>
      <div class="sd">
        <span v-if="item.ratio !== undefined && item.ratio !== null" :class="ratioClass(item.ratio)">{{ ratioText(item.ratio) }}</span>
        <span v-if="item.desc"> {{ item.desc }}</span>
      </div>
    </button>
  </div>
</template>

<style scoped>
.stat { text-align: left; border: none; width: 100%; }
</style>
