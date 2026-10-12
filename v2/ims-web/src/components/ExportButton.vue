<script setup lang="ts">
import { toast } from "@/utils/toast";
import { useDownloadStore } from "@/stores/download";

const props = defineProps<{
  exportApi: (params: Record<string, unknown>) => Promise<unknown>;
  params?: Record<string, unknown>;
}>();
const downloads = useDownloadStore();

async function run() {
  await props.exportApi(props.params || {});
  toast.success("已开始导出");
  downloads.collapsed = false;
  await downloads.track();
}
</script>

<template>
  <button class="btn btn-sec" type="button" @click="run"><slot>导出</slot></button>
</template>
