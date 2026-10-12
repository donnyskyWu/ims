<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import PageHeader from "@/components/PageHeader.vue";
import QueryBar, { type QueryField } from "@/components/QueryBar.vue";
import DataTable, { type TableColumn } from "@/components/DataTable.vue";
import AppPagination from "@/components/AppPagination.vue";
import FormDrawer from "@/components/FormDrawer.vue";
import DetailDrawer from "@/components/DetailDrawer.vue";
import DescriptionList from "@/components/DescriptionList.vue";
import EmptyState from "@/components/EmptyState.vue";
import ExportButton from "@/components/ExportButton.vue";
import UserSelect from "@/components/UserSelect.vue";
import DictSelect from "@/components/DictSelect.vue";
import MaskedText from "@/components/MaskedText.vue";
import { confirm } from "@/components/confirm";
import { toast } from "@/utils/toast";
import { resourceGet, resourcePage, resourceSend } from "@/api/resource";

const router = useRouter();
const query = ref<Record<string, unknown>>({ name: "", idType: "", idNo: "", status: "" });
const rows = ref<Record<string, unknown>[]>([]);
const total = ref(0);
const pageNo = ref(1);
const pageSize = ref(20);
const loading = ref(false);
const drawer = ref(false);
const editing = ref<Record<string, unknown> | null>(null);
type PersonForm = Record<string, unknown> & { idType: string; userId: string };
const form = ref<PersonForm>({ name: "", idType: "ID_CARD", idNo: "", mobile: "", userId: "", agentName: "", agentMobile: "", remark: "", status: "ENABLED" });
const detailOpen = ref(false);
const current = ref<Record<string, unknown> | null>(null);
const plain = ref<Record<string, string> | null>(null);
let plainTimer = 0;

const fields: QueryField[] = [
  { key: "name", label: "姓名", type: "input" },
  { key: "idType", label: "证件类型", type: "dict", dictType: "dict_cert_type" },
  { key: "idNo", label: "证件号", type: "input" },
  { key: "status", label: "状态", type: "dict", dictType: "dict_corp_status" },
];

const columns: TableColumn[] = [
  { key: "realnameNo", label: "编号", type: "mono" },
  { key: "name", label: "姓名" },
  { key: "idType", label: "证件类型", type: "status", dictType: "dict_cert_type" },
  { key: "idNoMasked", label: "证件号", type: "masked" },
  { key: "mobileMasked", label: "手机号", type: "masked" },
  { key: "agentName", label: "中介人" },
  { key: "userName", label: "关联员工" },
  { key: "certStatusLabel", label: "证件状态" },
  { key: "status", label: "状态", type: "status", dictType: "dict_corp_status" },
  {
    key: "ops",
    label: "操作",
    type: "actions",
    actions: [
      { label: "详情", perm: "ims:corp:realname:query", onClick: (row) => void openDetail(row) },
      { label: "编辑", perm: "ims:corp:realname:update", onClick: (row) => openEdit(row) },
      { label: "停用", perm: "ims:corp:realname:update", show: (row) => row.status === "ENABLED", onClick: (row) => void toggle(row, "DISABLED") },
      { label: "启用", perm: "ims:corp:realname:update", show: (row) => row.status === "DISABLED", onClick: (row) => void toggle(row, "ENABLED") },
      { label: "删除", perm: "ims:corp:realname:delete", danger: true, onClick: (row) => void remove(row) },
    ],
  },
];

async function load() {
  loading.value = true;
  try {
    const data = await resourcePage<Record<string, unknown>>("/corp/resource/realname/page", { pageNo: pageNo.value, pageSize: pageSize.value, ...query.value });
    rows.value = data.list;
    total.value = data.total;
  } finally {
    loading.value = false;
  }
}
function blankForm() {
  form.value = { name: "", idType: "ID_CARD", idNo: "", mobile: "", userId: "", agentName: "", agentMobile: "", remark: "", status: "ENABLED" };
}
function openCreate() {
  editing.value = null;
  blankForm();
  drawer.value = true;
}
function openEdit(row: Record<string, unknown>) {
  editing.value = row;
  form.value = {
    name: row.name,
    idType: String(row.idType || "ID_CARD"),
    idNo: "",
    mobile: "",
    userId: String(row.userId || ""),
    agentName: row.agentName,
    agentMobile: "",
    remark: row.remark,
    status: row.status,
  };
  drawer.value = true;
}
async function save(model: Record<string, unknown>) {
  const body = { ...model };
  if (editing.value && !body.idNo) delete body.idNo;
  if (editing.value && !body.mobile) delete body.mobile;
  if (editing.value?.id) return resourceSend("PUT", `/corp/resource/realname/${editing.value.id}`, body);
  return resourceSend("POST", "/corp/resource/realname", body);
}
async function openDetail(row: Record<string, unknown>) {
  plain.value = null;
  current.value = await resourceGet(`/corp/resource/realname/${row.id}`);
  detailOpen.value = true;
}
async function showPlain() {
  if (!current.value) return;
  plain.value = await resourceGet(`/corp/resource/realname/${current.value.id}/plain`);
  window.clearTimeout(plainTimer);
  plainTimer = window.setTimeout(() => {
    plain.value = null;
  }, 30000);
}
async function toggle(row: Record<string, unknown>, status: string) {
  await confirm({
    title: status === "DISABLED" ? "停用实名人" : "启用实名人",
    message: status === "DISABLED" ? "停用后选择器不再出现。" : "确定重新启用？",
    action: async () => {
      await resourceSend("PUT", `/corp/resource/realname/${row.id}/status`, { status });
      await load();
    },
  });
}
async function remove(row: Record<string, unknown>) {
  await confirm({
    title: "删除实名人",
    message: "若仍被手机卡或证件引用将无法删除。",
    danger: true,
    action: async () => {
      await resourceSend("DELETE", `/corp/resource/realname/${row.id}`);
      toast.success("已删除");
      await load();
    },
  });
}
function certs() {
  return (current.value?.certs as Record<string, unknown>[]) || [];
}
function sims() {
  return (current.value?.simCards as Record<string, unknown>[]) || [];
}

onMounted(load);
</script>

<template>
  <section class="page">
    <PageHeader title="实名人管理">
      <template #actions>
        <button v-perm="'ims:corp:realname:create'" class="btn btn-pri" type="button" @click="openCreate">新增实名人</button>
        <ExportButton v-perm="'ims:corp:realname:export'" :params="query" :export-api="() => resourceGet('/corp/resource/realname/export', query)" />
      </template>
    </PageHeader>
    <QueryBar v-model="query" :fields="fields" @search="pageNo = 1; load()" @reset="pageNo = 1; load()" />
    <DataTable :columns="columns" :data="rows" :loading="loading" />
    <AppPagination v-model:page-no="pageNo" v-model:page-size="pageSize" :total="total" @change="load()" />
    <FormDrawer v-model:open="drawer" :title="editing ? '编辑实名人' : '新增实名人'" size="M" :model="form" :submit="save" @saved="load()">
      <el-form-item label="姓名" required><el-input v-model="form.name" maxlength="32" /></el-form-item>
      <el-form-item label="证件类型" required><DictSelect v-model="form.idType" dict-type="dict_cert_type" /></el-form-item>
      <el-form-item label="证件号" required><el-input v-model="form.idNo" :placeholder="editing ? '留空表示不修改' : ''" /></el-form-item>
      <el-form-item label="手机号"><el-input v-model="form.mobile" maxlength="11" /></el-form-item>
      <el-form-item label="关联员工"><UserSelect v-model="form.userId" /></el-form-item>
      <el-form-item label="中介人"><el-input v-model="form.agentName" maxlength="32" /></el-form-item>
      <el-form-item label="中介人电话"><el-input v-model="form.agentMobile" maxlength="11" /></el-form-item>
      <el-form-item label="备注"><el-input v-model="form.remark" type="textarea" /></el-form-item>
    </FormDrawer>
    <DetailDrawer v-model:open="detailOpen" :title="String(current?.name || '实名人')" status-dict="dict_corp_status" :status-value="String(current?.status || '')" :tabs="[{ key: 'base', label: '基本信息' }, { key: 'cert', label: '证件档案' }, { key: 'sim', label: '手机卡' }, { key: 'rel', label: '关联账号' }]">
      <template #base>
        <DescriptionList :items="[{ label: '编号', value: current?.realnameNo }, { label: '证件类型', value: current?.idType }, { label: '关联员工', value: current?.userName }]" />
        <p>证件号 <MaskedText :value="String(plain?.idNo || current?.idNoMasked || '')" /> <button v-if="current?.canPlain" v-perm="'ims:corp:realname:plain'" class="btn btn-txt" type="button" @click="showPlain">显示</button></p>
        <p>手机号 <MaskedText :value="String(plain?.mobile || current?.mobileMasked || '')" /></p>
      </template>
      <template #cert>
        <EmptyState v-if="!certs().length" desc="未建档" />
        <button v-for="item in certs()" :key="String(item.id)" class="btn btn-txt" type="button" @click="router.push({ path: '/ims/corp/resource/certificate', query: { realnameId: String(current?.id || '') } })">{{ item.certType }} {{ item.statusLabel }}</button>
      </template>
      <template #sim>
        <EmptyState v-if="!sims().length" desc="暂无手机卡" />
        <p v-for="item in sims()" :key="String(item.id)">{{ item.simNo }} {{ item.phoneMasked }} {{ item.statusLabel }}</p>
      </template>
      <template #rel>
        <EmptyState desc="暂无关联账号" />
      </template>
    </DetailDrawer>
  </section>
</template>
