<script setup lang="ts">
defineProps<{
  type?: "empty" | "noPermission" | "error";
  desc?: string;
}>();
const emit = defineEmits<{ retry: [] }>();

const copy: Record<string, { title: string; desc: string }> = {
  empty: { title: "暂无数据", desc: "" },
  noPermission: { title: "暂无权限查看此内容", desc: "" },
  error: { title: "加载失败，请稍后重试", desc: "" },
};
</script>

<template>
  <div class="empty">
    <div class="et">{{ desc || copy[type || "empty"].title }}</div>
    <div v-if="copy[type || 'empty'].desc" class="es">{{ copy[type || "empty"].desc }}</div>
    <div v-if="type === 'error'" class="es">
      <button class="btn btn-sec btn-sm" type="button" @click="emit('retry')">重试</button>
    </div>
    <div class="es"><slot name="action" /></div>
  </div>
</template>
