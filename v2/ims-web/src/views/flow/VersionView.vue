<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import PageHeader from "@/components/PageHeader.vue";
import DataTable, { type TableColumn } from "@/components/DataTable.vue";
import FormDrawer from "@/components/FormDrawer.vue";
import Perm from "@/components/Perm.vue";
import { toast } from "@/utils/toast";
import { flowApi, type Row } from "./api";

const route = useRoute();
const router = useRouter();
const templateId = String(route.params.templateId || "");
const rows = ref<Row[]>([]);
const fromVersion = ref(1);
const toVersion = ref(2);
const diff = ref<Row | null>(null);
const open = ref(false);
const form = ref({ targetVersion: 1, changeDesc: "" });

const columns: TableColumn[] = [
  { key: "version", label: "版本", type: "number" },
  { key: "changeDesc", label: "说明" },
  { key: "publishedByName", label: "发布人" },
  { key: "publishedAt", label: "发布时间", type: "time" },
  { key: "status", label: "标记" },
  {
    key: "ops",
    label: "操作",
    type: "actions",
    actions: [
      { label: "快照", onClick: (row) => void snapshot(Number(row.version)) },
      { label: "回滚到此版本", perm: "ims:flow:version:rollback", show: (row) => row.versionStatus !== "DRAFT", onClick: (row) => openRollback(Number(row.version)) },
    ],
  },
];

async function load() {
  rows.value = await flowApi.versions(templateId);
  if (rows.value.length >= 2) {
    fromVersion.value = Number(rows.value[rows.value.length - 1].version);
    toVersion.value = Number(rows.value[0].version);
    await compare();
  }
}

async function compare() {
  diff.value = await flowApi.diff({ templateId, fromVersion: fromVersion.value, toVersion: toVersion.value });
}

async function snapshot(version: number) {
  const data = await flowApi.snapshot(templateId, version);
  toast.info(`版本 ${data.version} 共 ${Array.isArray(data.nodes) ? data.nodes.length : 0} 个节点`);
}

function openRollback(version: number) {
  form.value = { targetVersion: version, changeDesc: "" };
  open.value = true;
}

async function save(model: Record<string, unknown>) {
  const data = await flowApi.rollback(templateId, model);
  toast.success(`已回滚，新版本 ${data.newVersion}`);
  return data;
}

onMounted(load);
</script>

<template>
  <section>
    <PageHeader title="版本管理" sub-title="对比历史版本并回滚" :show-scope="false">
      <template #actions>
        <button class="btn btn-sec" type="button" @click="router.push('/ims/flow/template')">返回模板</button>
      </template>
    </PageHeader>
    <DataTable :columns="columns" :data="rows" @retry="load" />
    <div class="compare">
      <label>从<input v-model.number="fromVersion" type="number" /></label>
      <label>到<input v-model.number="toVersion" type="number" /></label>
      <button class="btn btn-sec btn-sm" type="button" @click="compare">对比</button>
    </div>
    <ul v-if="diff">
      <li v-for="(item, index) in (diff.nodeChanges as Row[]) || []" :key="index">{{ item.changeType }} · {{ item.nodeName }}</li>
    </ul>
    <Perm code="ims:flow:version:rollback" />
    <FormDrawer v-model:open="open" title="回滚版本" :model="form" :submit="save" @saved="load">
      <p>目标版本 {{ form.targetVersion }}</p>
      <label>变更说明<textarea v-model="form.changeDesc" maxlength="512" /></label>
    </FormDrawer>
  </section>
</template>

<style scoped>
.compare { display: flex; gap: 8px; align-items: end; margin: 12px 0; }
label { display: flex; flex-direction: column; gap: 4px; }
</style>
