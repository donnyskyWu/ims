<script setup lang="ts">
import { onMounted, ref } from "vue";
import PageHeader from "@/components/PageHeader.vue";
import QueryBar, { type QueryField } from "@/components/QueryBar.vue";
import DataTable, { type TableColumn } from "@/components/DataTable.vue";
import AppPagination from "@/components/AppPagination.vue";
import FormDrawer from "@/components/FormDrawer.vue";
import DetailDrawer from "@/components/DetailDrawer.vue";
import DescriptionList from "@/components/DescriptionList.vue";
import ExportButton from "@/components/ExportButton.vue";
import UserSelect from "@/components/UserSelect.vue";
import DictSelect from "@/components/DictSelect.vue";
import MaskedText from "@/components/MaskedText.vue";
import { confirm } from "@/components/confirm";
import { toast } from "@/utils/toast";
import { resourceGet, resourcePage, resourceSend } from "@/api/resource";

const query = ref<Record<string, unknown>>({ keyword: "", accountType: "", status: "" });
const rows = ref<Record<string, unknown>[]>([]);
const total = ref(0);
const pageNo = ref(1);
const pageSize = ref(20);
const loading = ref(false);
const drawer = ref(false);
const editing = ref<Record<string, unknown> | null>(null);
const form = ref(blank());
const detailOpen = ref(false);
const current = ref<Record<string, unknown> | null>(null);

const fields: QueryField[] = [
  { key: "keyword", label: "编号/昵称", type: "input" },
  { key: "accountType", label: "类型", type: "dict", dictType: "dict_personal_account_type" },
  { key: "status", label: "状态", type: "dict", dictType: "dict_common_status" },
];
const columns: TableColumn[] = [
  { key: "accountNo", label: "编号", type: "mono" },
  { key: "accountTypeLabel", label: "类型" },
  { key: "nickname", label: "昵称" },
  { key: "ownerName", label: "归属员工" },
  { key: "status", label: "状态", type: "status", dictType: "dict_common_status" },
  {
    key: "ops",
    label: "操作",
    type: "actions",
    actions: [
      { label: "详情", onClick: (row) => void openDetail(row) },
      { label: "编辑", perm: "ims:corp:account:personal:update", onClick: (row) => openEdit(row) },
      { label: "删除", perm: "ims:corp:account:personal:delete", danger: true, onClick: (row) => void remove(row) },
    ],
  },
];

async function load() {
  loading.value = true;
  try {
    const data = await resourcePage<Record<string, unknown>>("/corp/account/personal/page", { pageNo: pageNo.value, pageSize: pageSize.value, ...query.value });
    rows.value = data.list;
    total.value = data.total;
  } finally {
    loading.value = false;
  }
}
function blank() {
  return { accountType: "", nickname: "", ownerUserId: "", mobile: "", remark: "" };
}
function openCreate() {
  editing.value = null;
  form.value = blank();
  drawer.value = true;
}
function openEdit(row: Record<string, unknown>) {
  editing.value = row;
  form.value = {
    accountType: String(row.accountType || ""),
    nickname: String(row.nickname || ""),
    ownerUserId: row.ownerUserId ? String(row.ownerUserId) : "",
    mobile: "",
    remark: String(row.remark || ""),
  };
  drawer.value = true;
}
async function save(model: Record<string, unknown>) {
  if (editing.value?.id) return resourceSend("PUT", `/corp/account/personal/${editing.value.id}`, model);
  return resourceSend("POST", "/corp/account/personal", model, `per-${Date.now()}`);
}
async function openDetail(row: Record<string, unknown>) {
  current.value = await resourceGet(`/corp/account/personal/${row.id}`);
  detailOpen.value = true;
}
async function toggle() {
  if (!current.value) return;
  const status = current.value.status === "ENABLED" ? "DISABLED" : "ENABLED";
  current.value = await resourceSend("PUT", `/corp/account/personal/${current.value.id}/status`, { status });
  toast.success("已更新");
  await load();
}
async function remove(row: Record<string, unknown>) {
  await confirm({
    title: "删除个人账号",
    message: "删除后不再出现在台账。",
    action: async () => {
      await resourceSend("DELETE", `/corp/account/personal/${row.id}`);
      toast.success("已删除");
      await load();
    },
  });
}
onMounted(load);
</script>

<template>
  <section>
    <PageHeader title="个人账号" sub-title="公司资产 / 账号管理 / 个人账号">
      <template #actions>
        <button v-perm="'ims:corp:account:personal:create'" class="btn btn-pri" type="button" @click="openCreate">新建</button>
        <ExportButton v-perm="'ims:corp:account:personal:export'" :params="query" :export-api="() => resourceGet('/corp/account/personal/export', query)" />
      </template>
    </PageHeader>
    <QueryBar v-model="query" :fields="fields" @search="pageNo = 1; load()" @reset="pageNo = 1; load()" />
    <DataTable :columns="columns" :data="rows" :loading="loading" />
    <AppPagination v-model:page-no="pageNo" v-model:page-size="pageSize" :total="total" @change="load()" />
    <FormDrawer v-model:open="drawer" :title="editing ? '编辑个人账号' : '新建个人账号'" :model="form" :submit="save" @saved="load()">
      <el-form-item label="类型" required><DictSelect v-model="form.accountType" dict-type="dict_personal_account_type" /></el-form-item>
      <el-form-item label="昵称" required><el-input v-model="form.nickname" maxlength="64" /></el-form-item>
      <el-form-item label="归属员工"><UserSelect v-model="form.ownerUserId" /></el-form-item>
      <el-form-item label="手机号"><el-input v-model="form.mobile" maxlength="11" /></el-form-item>
      <el-form-item label="备注"><el-input v-model="form.remark" maxlength="256" type="textarea" /></el-form-item>
    </FormDrawer>
    <DetailDrawer v-model:open="detailOpen" :title="String(current?.nickname || '个人账号')" status-dict="dict_common_status" :status-value="String(current?.status || '')">
      <DescriptionList :items="[{ label: '编号', value: current?.accountNo }, { label: '类型', value: current?.accountTypeLabel }, { label: '归属员工', value: current?.ownerName }, { label: '备注', value: current?.remark }]" />
      <MaskedText :value="String(current?.mobileMask || '')" />
      <template #footer>
        <button v-perm="'ims:corp:account:personal:update'" class="btn btn-sec" type="button" @click="toggle">{{ current?.status === "ENABLED" ? "停用" : "启用" }}</button>
      </template>
    </DetailDrawer>
  </section>
</template>
