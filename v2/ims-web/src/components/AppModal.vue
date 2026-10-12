<script setup lang="ts">
const open = defineModel<boolean>("open", { required: true });
defineProps<{ title: string; width: 360 | 520 | 800 }>();
</script>

<template>
  <el-dialog :model-value="open" :title="title" :width="width" @update:model-value="open = $event">
    <slot />
    <template #footer><slot name="footer" /></template>
  </el-dialog>
</template>
