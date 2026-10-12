<script setup lang="ts">
import { ref } from "vue";
import AppModal from "./AppModal.vue";

const props = defineProps<{
  templateApi: () => Promise<void> | void;
  importApi: (rows: Record<string, string>[], mode?: string) => Promise<{ successCount: number; errors: { row: number; column: string; message: string }[] }>;
  scene?: string;
}>();
const open = defineModel<boolean>("open", { default: false });
const emit = defineEmits<{ done: [] }>();
const step = ref(1);
const errors = ref<{ row: number; column: string; message: string }[]>([]);
const successCount = ref(0);
const rows = ref<Record<string, string>[]>([]);

function parseCsv(text: string) {
  const lines = text.split(/\r?\n/).filter((line) => line.trim());
  const header = (lines.shift() || "").split(",");
  return lines.map((line) => {
    const cells = line.split(",");
    const row: Record<string, string> = {};
    header.forEach((key, index) => {
      row[key.trim()] = (cells[index] || "").trim();
    });
    return row;
  });
}

async function onFile(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0];
  if (!file) return;
  rows.value = parseCsv(await file.text());
  const result = await props.importApi(rows.value, "ALL_OR_NOTHING");
  errors.value = result.errors || [];
  successCount.value = result.successCount || 0;
  step.value = 3;
}

async function confirmImport() {
  if (errors.value.length) return;
  await props.importApi(rows.value, "PARTIAL");
  emit("done");
  open.value = false;
}

function exportErrors() {
  const body = ["行号,列,原因", ...errors.value.map((item) => `${item.row},${item.column},${item.message}`)].join("\n");
  const url = URL.createObjectURL(new Blob([body], { type: "text/csv" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = "导入错误.csv";
  link.click();
}
</script>

<template>
  <AppModal v-model:open="open" title="导入" :width="800">
    <ol class="steps">
      <li :class="{ on: step === 1 }">下载模板</li>
      <li :class="{ on: step === 2 }">上传</li>
      <li :class="{ on: step === 3 }">校验结果</li>
      <li :class="{ on: step === 4 }">确认</li>
    </ol>
    <button class="btn btn-sec" type="button" @click="templateApi(); step = 2">下载模板</button>
    <input type="file" accept=".csv,.xlsx" @change="onFile" />
    <p v-if="step >= 3">成功 {{ successCount }} 行 / 错误 {{ errors.length }} 行</p>
    <table v-if="errors.length" class="err">
      <thead><tr><th>行号</th><th>列</th><th>原因</th></tr></thead>
      <tbody>
        <tr v-for="item in errors" :key="item.row + item.column"><td>{{ item.row }}</td><td>{{ item.column }}</td><td>{{ item.message }}</td></tr>
      </tbody>
    </table>
    <button v-if="errors.length" class="btn btn-txt" type="button" @click="exportErrors">导出错误清单</button>
    <template #footer>
      <button class="btn btn-pri" type="button" :disabled="errors.length > 0 || !rows.length" @click="confirmImport">确认导入</button>
    </template>
  </AppModal>
</template>

<style scoped>
.steps { display: flex; gap: 12px; padding: 0; list-style: none; color: var(--text2); }
.on { color: var(--blue); }
.err { width: 100%; border-collapse: collapse; font-size: 13px; }
.err td, .err th { border-bottom: 1px solid var(--line); padding: 6px; text-align: left; }
</style>
