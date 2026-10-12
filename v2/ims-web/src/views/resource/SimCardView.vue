<script setup lang="ts">
import { onMounted, ref } from "vue";
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
import RealNameSelect from "@/components/RealNameSelect.vue";
import MaskedText from "@/components/MaskedText.vue";
import MoneyText from "@/components/MoneyText.vue";
import { confirm } from "@/components/confirm";
import { toast } from "@/utils/toast";
import { resourceGet, resourcePage, resourceSend } from "@/api/resource";

const query = ref<Record<string, unknown>>({ phone: "", operator: "", realnameId: "", assignedUserId: "", status: "" });
const rows = ref<Record<string, unknown>[]>([]);
const total = ref(0);
const pageNo = ref(1);
const pageSize = ref(20);
const loading = ref(false);
const drawer = ref(false);
const editing = ref<Record<string, unknown> | null>(null);
const form = ref<Record<string, unknown>>({});
const detailOpen = ref(false);
const current = ref<Record<string, unknown> | null>(null);
const plain = ref<Record<string, string> | null>(null);

const fields: QueryField[] = [
  { key: "phone", label: "号码", type: "input" },
  { key: "operator", label: "运营商", type: "dict", dictType: "dict_sim_operator" },
  { key: "status", label: "状态", type: "dict", dictType: "dict_corp_status" },
];

const columns: TableColumn[] = [
  { key: "simNo", label: "卡编号", type: "mono" },
  { key: "phoneMasked", label: "号码", type: "masked" },
  { key: "operatorLabel", label: "运营商" },
  { key: "realnameName", label: "实名人" },
  { key: "keeperName", label: "保管人" },
  { key: "phoneName", label: "绑定手机" },
  { key: "monthlyRent", label: "月租", type: "money" },
  { key: "nextPaymentDate", label: "下次缴费日" },
  { key: "status", label: "状态", type: "status", dictType: "dict_corp_status" },
  {
    key: "ops",
    label: "操作",
    type: "actions",
    actions: [
      { label: "详情", perm: "ims:corp:sim:query", onClick: (row) => void openDetail(row) },
      { label: "编辑", perm: "ims:corp:sim:update", onClick: (row) => openEdit(row) },
      { label: "停用", perm: "ims:corp:sim:update", show: (row) => row.status === "ENABLED", onClick: (row) => void toggle(row, "DISABLED") },
      { label: "启用", perm: "ims:corp:sim:update", show: (row) => row.status === "DISABLED", onClick: (row) => void toggle(row, "ENABLED") },
      { label: "删除", perm: "ims:corp:sim:delete", danger: true, onClick: (row) => void remove(row) },
    ],
  },
];

function blank() {
  form.value = { phone: "", operator: "CMCC", iccid: "", isPrimary: false, realnameId: "", assignedUserId: "", packageName: "", monthlyRent: "0.00", paymentCycle: "MONTH", activatedAt: "", nextPaymentDate: "", status: "ENABLED" };
}
async function load() {
  loading.value = true;
  try {
    const data = await resourcePage<Record<string, unknown>>("/corp/resource/sim-card/page", { pageNo: pageNo.value, pageSize: pageSize.value, ...query.value });
    rows.value = data.list;
    total.value = data.total;
  } finally {
    loading.value = false;
  }
}
function openCreate() {
  editing.value = null;
  blank();
  drawer.value = true;
}
function openEdit(row: Record<string, unknown>) {
  editing.value = row;
  form.value = { ...row, phone: "", iccid: "" };
  drawer.value = true;
}
async function save(model: Record<string, unknown>) {
  const body = { ...model };
  if (editing.value && !body.phone) delete body.phone;
  if (editing.value && !body.iccid) delete body.iccid;
  if (editing.value?.id) return resourceSend("PUT", `/corp/resource/sim-card/${editing.value.id}`, body);
  return resourceSend("POST", "/corp/resource/sim-card", body);
}
async function openDetail(row: Record<string, unknown>) {
  plain.value = null;
  current.value = await resourceGet(`/corp/resource/sim-card/${row.id}`);
  detailOpen.value = true;
}
async function showPlain() {
  if (!current.value) return;
  plain.value = await resourceGet(`/corp/resource/sim-card/${current.value.id}/plain`);
  window.setTimeout(() => {
    plain.value = null;
  }, 30000);
}
async function toggle(row: Record<string, unknown>, status: string) {
  await confirm({
    title: status === "DISABLED" ? "停用手机卡" : "启用手机卡",
    message: "确定更新状态？",
    action: async () => {
      await resourceSend("PUT", `/corp/resource/sim-card/${row.id}/status`, { status });
      await load();
    },
  });
}
async function remove(row: Record<string, unknown>) {
  await confirm({
    title: "删除手机卡",
    message: "若仍被引用将无法删除。",
    danger: true,
    action: async () => {
      await resourceSend("DELETE", `/corp/resource/sim-card/${row.id}`);
      toast.success("已删除");
      await load();
    },
  });
}
function tone(row: Record<string, unknown>) {
  return String(row.paymentTone || "");
}

onMounted(load);
</script>

<template>
  <section class="page">
    <PageHeader title="手机卡管理">
      <template #actions>
        <button v-perm="'ims:corp:sim:create'" class="btn btn-pri" type="button" @click="openCreate">新增手机卡</button>
        <ExportButton v-perm="'ims:corp:sim:export'" :params="query" :export-api="() => resourceGet('/corp/resource/sim-card/export', query)" />
      </template>
    </PageHeader>
    <div class="filters">
      <QueryBar v-model="query" :fields="fields" @search="pageNo = 1; load()" @reset="pageNo = 1; load()" />
      <label>实名人 <RealNameSelect v-model="query.realnameId" :show-cert-warning="false" /></label>
      <label>保管人 <UserSelect v-model="query.assignedUserId" /></label>
    </div>
    <DataTable :columns="columns" :data="rows" :loading="loading">
      <template #cell-nextPaymentDate="{ row }">
        <span :class="tone(row)">{{ row.nextPaymentDate || "—" }}</span>
      </template>
    </DataTable>
    <AppPagination v-model:page-no="pageNo" v-model:page-size="pageSize" :total="total" @change="load()" />
    <FormDrawer v-model:open="drawer" :title="editing ? '编辑手机卡' : '新增手机卡'" size="L" :model="form" :submit="save" @saved="load()">
      <el-form-item label="号码" required><el-input v-model="form.phone" maxlength="11" :placeholder="editing ? '留空表示不修改' : ''" /></el-form-item>
      <el-form-item label="运营商" required><DictSelect v-model="form.operator" dict-type="dict_sim_operator" /></el-form-item>
      <el-form-item label="ICCID"><el-input v-model="form.iccid" :placeholder="editing ? '留空表示不修改' : ''" /></el-form-item>
      <el-form-item label="实名人"><RealNameSelect v-model="form.realnameId" /></el-form-item>
      <el-form-item label="保管人"><UserSelect v-model="form.assignedUserId" /></el-form-item>
      <el-form-item label="套餐"><el-input v-model="form.packageName" maxlength="64" /></el-form-item>
      <el-form-item label="月租"><el-input v-model="form.monthlyRent" /></el-form-item>
      <el-form-item label="缴费周期"><DictSelect v-model="form.paymentCycle" dict-type="dict_payment_cycle" /></el-form-item>
      <el-form-item label="开卡日"><el-input v-model="form.activatedAt" placeholder="YYYY-MM-DD" /></el-form-item>
      <el-form-item label="下次缴费日"><el-input v-model="form.nextPaymentDate" placeholder="YYYY-MM-DD" /></el-form-item>
    </FormDrawer>
    <DetailDrawer v-model:open="detailOpen" title="手机卡详情" status-dict="dict_corp_status" :status-value="String(current?.status || '')" :tabs="[{ key: 'base', label: '基本' }, { key: 'pay', label: '缴费' }, { key: 'rel', label: '关联账号' }]">
      <template #base>
        <DescriptionList :items="[{ label: '编号', value: current?.simNo }, { label: '运营商', value: current?.operatorLabel }, { label: '实名人', value: current?.realnameName }, { label: '保管人', value: current?.keeperName }, { label: '绑定手机', value: '—' }]" />
        <p>号码 <MaskedText :value="String(plain?.phone || current?.phoneMasked || '')" /> <button v-if="current?.canPlain" v-perm="'ims:corp:sim:plain'" class="btn btn-txt" type="button" @click="showPlain">显示</button></p>
        <p>ICCID <MaskedText :value="String(plain?.iccid || current?.iccidMasked || '')" /></p>
      </template>
      <template #pay>
        <p>月租 <MoneyText :value="String(current?.monthlyRent || '0')" /></p>
        <p>下次缴费 {{ current?.nextPaymentDate || "—" }}</p>
      </template>
      <template #rel>
        <EmptyState desc="暂无关联账号" />
      </template>
    </DetailDrawer>
  </section>
</template>

<style scoped>
.filters { display: flex; gap: 12px; align-items: flex-end; flex-wrap: wrap; }
.warning { color: var(--yellow); }
.danger { color: var(--red); }
</style>
