<script setup lang="ts">
import { onMounted, ref } from "vue";
import PageHeader from "@/components/PageHeader.vue";
import QueryBar, { type QueryField } from "@/components/QueryBar.vue";
import DataTable, { type TableColumn } from "@/components/DataTable.vue";
import AppPagination from "@/components/AppPagination.vue";
import FormDrawer from "@/components/FormDrawer.vue";
import DetailDrawer from "@/components/DetailDrawer.vue";
import DescriptionList from "@/components/DescriptionList.vue";
import Timeline from "@/components/Timeline.vue";
import EmptyState from "@/components/EmptyState.vue";
import ExportButton from "@/components/ExportButton.vue";
import AppModal from "@/components/AppModal.vue";
import { confirm } from "@/components/confirm";
import { toast } from "@/utils/toast";
import { resourceGet, resourcePage, resourceSend } from "@/api/resource";

const query = ref<Record<string, unknown>>({ name: "", creditCode: "", status: "" });
const rows = ref<Record<string, unknown>[]>([]);
const total = ref(0);
const pageNo = ref(1);
const pageSize = ref(20);
const loading = ref(false);
const drawer = ref(false);
const editing = ref<Record<string, unknown> | null>(null);
const form = ref<Record<string, unknown>>({ name: "", creditCode: "", legalPerson: "", address: "", wxOfficialCapacity: 0, status: "ENABLED", remark: "" });
const detailOpen = ref(false);
const current = ref<Record<string, unknown> | null>(null);
const capacityOpen = ref(false);
const capacity = ref({ capacity: 0, reason: "" });

const fields: QueryField[] = [
  { key: "name", label: "名称", type: "input" },
  { key: "creditCode", label: "信用代码", type: "input" },
  { key: "status", label: "状态", type: "dict", dictType: "dict_corp_status" },
];

const columns: TableColumn[] = [
  { key: "companyNo", label: "公司编号", type: "mono" },
  { key: "name", label: "名称" },
  { key: "creditCode", label: "统一社会信用代码" },
  { key: "legalPerson", label: "法人" },
  { key: "capacityText", label: "公众号容量" },
  { key: "status", label: "状态", type: "status", dictType: "dict_corp_status" },
  { key: "updateTime", label: "更新时间", type: "time" },
  {
    key: "ops",
    label: "操作",
    type: "actions",
    actions: [
      { label: "详情", perm: "ims:corp:company:query", onClick: (row) => void openDetail(row) },
      { label: "编辑", perm: "ims:corp:company:update", onClick: (row) => openEdit(row) },
      { label: "停用", perm: "ims:corp:company:update", show: (row) => row.status === "ENABLED", onClick: (row) => void toggle(row, "DISABLED") },
      { label: "启用", perm: "ims:corp:company:update", show: (row) => row.status === "DISABLED", onClick: (row) => void toggle(row, "ENABLED") },
      { label: "删除", perm: "ims:corp:company:delete", danger: true, onClick: (row) => void remove(row) },
    ],
  },
];

async function load() {
  loading.value = true;
  try {
    const data = await resourcePage<Record<string, unknown>>("/corp/resource/company/page", { pageNo: pageNo.value, pageSize: pageSize.value, ...query.value });
    rows.value = data.list;
    total.value = data.total;
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  editing.value = null;
  form.value = { name: "", creditCode: "", legalPerson: "", address: "", wxOfficialCapacity: 0, status: "ENABLED", remark: "" };
  drawer.value = true;
}
function openEdit(row: Record<string, unknown>) {
  editing.value = row;
  form.value = { name: row.name, creditCode: row.creditCode, legalPerson: row.legalPerson, address: row.address, status: row.status, remark: row.remark };
  drawer.value = true;
}
async function save(model: Record<string, unknown>) {
  if (editing.value?.id) return resourceSend("PUT", `/corp/resource/company/${editing.value.id}`, model);
  return resourceSend("POST", "/corp/resource/company", model);
}
async function openDetail(row: Record<string, unknown>) {
  current.value = await resourceGet(`/corp/resource/company/${row.id}`);
  detailOpen.value = true;
}
async function toggle(row: Record<string, unknown>, status: string) {
  await confirm({
    title: status === "DISABLED" ? "停用公司" : "启用公司",
    message: status === "DISABLED" ? "停用后新建时不可再选择。" : "确定重新启用？",
    action: async () => {
      await resourceSend("PUT", `/corp/resource/company/${row.id}/status`, { status });
      toast.success("已更新");
      await load();
    },
  });
}
async function remove(row: Record<string, unknown>) {
  await confirm({
    title: "删除公司",
    message: "删除后不可恢复。若仍被引用将无法删除。",
    danger: true,
    action: async () => {
      await resourceSend("DELETE", `/corp/resource/company/${row.id}`);
      toast.success("已删除");
      await load();
    },
  });
}
function openCapacity() {
  capacity.value = { capacity: Number(current.value?.wxOfficialCapacity || 0), reason: "" };
  capacityOpen.value = true;
}
async function saveCapacity() {
  if (!current.value) return;
  current.value = await resourceSend("PUT", `/corp/resource/company/${current.value.id}/capacity`, capacity.value);
  capacityOpen.value = false;
  toast.success("容量已调整");
  await load();
}
function logs() {
  const items = (current.value?.capacityLogs as { time?: string; title?: string; operator?: string; detail?: string }[]) || [];
  return items.map((item) => ({ time: item.time || "", title: item.title || "", operator: item.operator || "", detail: item.detail || "" }));
}

onMounted(load);
</script>

<template>
  <section class="page">
    <PageHeader title="公司管理">
      <template #actions>
        <button v-perm="'ims:corp:company:create'" class="btn btn-pri" type="button" @click="openCreate">新建公司</button>
        <ExportButton v-perm="'ims:corp:company:export'" :params="query" :export-api="() => resourceGet('/corp/resource/company/export', query)" />
      </template>
    </PageHeader>
    <QueryBar v-model="query" :fields="fields" @search="pageNo = 1; load()" @reset="pageNo = 1; load()" />
    <DataTable :columns="columns" :data="rows" :loading="loading" />
    <AppPagination v-model:page-no="pageNo" v-model:page-size="pageSize" :total="total" @change="load()" />
    <FormDrawer v-model:open="drawer" :title="editing ? '编辑公司' : '新建公司'" size="M" :model="form" :submit="save" @saved="load()">
      <el-form-item label="名称" required><el-input v-model="form.name" maxlength="64" /></el-form-item>
      <el-form-item label="统一社会信用代码" required><el-input v-model="form.creditCode" maxlength="18" /></el-form-item>
      <el-form-item label="法人"><el-input v-model="form.legalPerson" maxlength="32" /></el-form-item>
      <el-form-item label="地址"><el-input v-model="form.address" maxlength="128" /></el-form-item>
      <el-form-item v-if="!editing" label="公众号总容量"><el-input v-model="form.wxOfficialCapacity" /></el-form-item>
      <el-form-item label="备注"><el-input v-model="form.remark" maxlength="255" type="textarea" /></el-form-item>
    </FormDrawer>
    <DetailDrawer v-model:open="detailOpen" :title="String(current?.name || '公司详情')" status-dict="dict_corp_status" :status-value="String(current?.status || '')" :tabs="[{ key: 'base', label: '基本信息' }, { key: 'cap', label: '公众号容量' }, { key: 'rel', label: '关联账号' }]">
      <template #base>
        <DescriptionList :items="[{ label: '编号', value: current?.companyNo }, { label: '信用代码', value: current?.creditCode }, { label: '法人', value: current?.legalPerson }, { label: '地址', value: current?.address }, { label: '备注', value: current?.remark }]" />
      </template>
      <template #cap>
        <p>已用 / 总量：{{ current?.capacityText }}</p>
        <button v-perm="'ims:corp:company:capacity'" class="btn btn-sec" type="button" @click="openCapacity">调整容量</button>
        <Timeline :items="logs()" />
      </template>
      <template #rel>
        <EmptyState v-if="!(current?.accountSummary as unknown[])?.length" desc="暂无关联账号" />
      </template>
    </DetailDrawer>
    <AppModal v-model:open="capacityOpen" title="调整容量" :width="520">
      <el-form-item label="新容量"><el-input v-model="capacity.capacity" /></el-form-item>
      <el-form-item label="原因"><el-input v-model="capacity.reason" maxlength="128" /></el-form-item>
      <button class="btn btn-pri" type="button" @click="saveCapacity">保存</button>
    </AppModal>
  </section>
</template>
