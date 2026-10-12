<script setup lang="ts">
import { useDownloadStore } from "@/stores/download";
import { call } from "@/api/generated/endpoints";

const downloads = useDownloadStore();

async function download(id: string) {
  const data = await call<{ content?: string }>("export_download_admin_api_ims_export_task_download_get", {
    query: { id },
    silent: true,
  });
  const blob = new Blob([data.content || ""], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "导出.csv";
  link.click();
}

function statusText(status: string) {
  if (status === "SUCCESS") return "完成";
  if (status === "FAILED") return "失败";
  if (status === "RUNNING") return "进行中";
  return "排队中";
}
</script>

<template>
  <aside v-if="downloads.tasks.length" class="dlbar">
    <header>
      <strong>下载</strong>
      <button class="btn btn-txt" type="button" @click="downloads.collapsed = !downloads.collapsed">{{ downloads.collapsed ? "展开" : "收起" }}</button>
    </header>
    <ul v-if="!downloads.collapsed">
      <li v-for="task in downloads.tasks" :key="task.id">
        <span>{{ statusText(task.status) }} {{ task.progress }}%</span>
        <span v-if="task.error">{{ task.error }}</span>
        <button v-if="task.status === 'SUCCESS'" class="btn btn-txt" type="button" @click="download(task.id)">下载</button>
      </li>
    </ul>
  </aside>
</template>

<style scoped>
header { display: flex; justify-content: space-between; align-items: center; }
ul { list-style: none; padding: 0; margin: 8px 0 0; }
</style>
