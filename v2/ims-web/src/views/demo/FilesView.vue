<script setup lang="ts">
import { ref } from "vue";
import FileUpload from "@/components/FileUpload.vue";
import FilePreview from "@/components/FilePreview.vue";
import ImportDialog from "@/components/ImportDialog.vue";
import ExportButton from "@/components/ExportButton.vue";
import { call } from "@/api/generated/endpoints";

const doc = ref<string | null>(null);
const avatar = ref<string | null>(null);
const open = ref(false);

function templateApi() {
  const body = "name,status,code\n示例,ACTIVE,A001\n";
  const url = URL.createObjectURL(new Blob([body], { type: "text/csv" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = "导入模板.csv";
  link.click();
}

function importApi(rows: Record<string, string>[]) {
  return call<{ successCount: number; errors: { row: number; column: string; message: string }[] }>("order_import_admin_api_ims_demo_order_import_post", {
    body: { rows, mode: "ALL_OR_NOTHING" },
    silent: true,
  });
}

function exportApi(params: Record<string, unknown>) {
  return call("order_export_admin_api_ims_demo_order_export_post", { body: params });
}
</script>

<template>
  <section class="page">
    <h1>文件</h1>
    <h2>培训资料</h2>
    <FileUpload v-model="doc" scene="TRAIN_DOC">
      <template #preview="{ fileKey }"><FilePreview :file-key="fileKey" /></template>
    </FileUpload>
    <h2>头像</h2>
    <FileUpload v-model="avatar" scene="TEST_IMAGE" />
    <div class="row">
      <button class="btn btn-sec" type="button" @click="open = true">导入</button>
      <ExportButton :export-api="exportApi" :params="{}" />
    </div>
    <ImportDialog v-model:open="open" :template-api="templateApi" :import-api="importApi" />
  </section>
</template>

<style scoped>
h1 { font-size: 28px; }
.row { display: flex; gap: 8px; margin-top: 12px; }
</style>
