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
import UserSelect from "@/components/UserSelect.vue";
import DictSelect from "@/components/DictSelect.vue";
import SimCardSelect from "@/components/SimCardSelect.vue";
import AppModal from "@/components/AppModal.vue";
import { confirm } from "@/components/confirm";
import { toast } from "@/utils/toast";
import { resourceGet, resourcePage, resourceSend } from "@/api/resource";
import VerifyDrawer from "./VerifyDrawer.vue";

const query = ref<Record<string, unknown>>({ deviceNo: "", model: "", osType: "", custodianUserId: "", status: "" });
const rows = ref<Record<string, unknown>[]>([]);
const total = ref(0);
const pageNo = ref(1);
const pageSize = ref(20);
const loading = ref(false);
const drawer = ref(false);
const editing = ref<Record<string, unknown> | null>(null);
const form = ref(blank());
const tokenBag = { value: "" };
const detailOpen = ref(false);
const current = ref<Record<string, unknown> | null>(null);
const verifyOpen = ref(false);
const bindOpen = ref(false);
const simIds = ref<string[]>([]);
const statusOpen = ref(false);
const statusForm = ref({ status: "IDLE", reason: "" });

const fields: QueryField[] = [
  { key: "deviceNo", label: "设备编号", type: "input" },
  { key: "model", label: "型号", type: "input" },
  { key: "osType", label: "类型", type: "dict", dictType: "dict_phone_os" },
  { key: "custodianUserId", label: "保管人", type: "user" },
  { key: "status", label: "状态", type: "dict", dictType: "dict_phone_status" },
];

const columns: TableColumn[] = [
  { key: "deviceNo", label: "设备编号", type: "mono" },
  { key: "model", label: "型号" },
  { key: "osLabel", label: "类型" },
  { key: "custodianName", label: "保管人" },
  { key: "simText", label: "绑定手机卡" },
  { key: "accountCount", label: "绑定账号数" },
  { key: "status", label: "状态", type: "status", dictType: "dict_phone_status" },
  {
    key: "ops",
    label: "操作",
    type: "actions",
    actions: [
      { label: "详情", perm: "ims:device:phone:query", onClick: (row) => void openDetail(row) },
      { label: "编辑", perm: "ims:device:phone:update", show: (row) => row.status !== "SCRAPPED", onClick: (row) => openEdit(row) },
      { label: "绑卡", perm: "ims:device:phone:bind-sim", show: (row) => row.status !== "SCRAPPED", onClick: (row) => void openBind(row) },
      { label: "报废", perm: "ims:device:phone:update", show: (row) => row.status !== "SCRAPPED", onClick: (row) => openStatus(row, "SCRAPPED") },
      { label: "删除", perm: "ims:device:phone:delete", danger: true, onClick: (row) => void remove(row) },
    ],
  },
];

function blank() {
  return { deviceNo: "", model: "", osType: "", custodianUserId: "", imei: "", purchaseDate: "", purchaseAmount: "", remark: "" };
}

async function load() {
  loading.value = true;
  try {
    const data = await resourcePage<Record<string, unknown>>("/corp/device/phone/page", { pageNo: pageNo.value, pageSize: pageSize.value, ...query.value });
    rows.value = data.list;
    total.value = data.total;
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  editing.value = null;
  form.value = blank();
  drawer.value = true;
}
function openEdit(row: Record<string, unknown>) {
  editing.value = row;
  const next = blank();
  next.deviceNo = String(row.deviceNo || "");
  next.model = String(row.model || "");
  next.osType = String(row.osType || "");
  next.custodianUserId = String(row.custodianUserId || "");
  next.imei = String(row.imei || "");
  next.purchaseDate = String(row.purchaseDate || "");
  next.purchaseAmount = String(row.purchaseAmount || "");
  next.remark = String(row.remark || "");
  form.value = next;
  drawer.value = true;
}
async function save(model: Record<string, unknown>) {
  if (editing.value?.id) return resourceSend("PUT", `/corp/device/phone/${editing.value.id}`, model);
  return resourceSend("POST", "/corp/device/phone", model, tokenBag.value);
}
async function openDetail(row: Record<string, unknown>) {
  current.value = await resourceGet(`/corp/device/phone/${row.id}`);
  detailOpen.value = true;
}
async function openBind(row: Record<string, unknown>) {
  const detail = await resourceGet<Record<string, unknown>>(`/corp/device/phone/${row.id}`);
  current.value = detail;
  const sims = (detail.sims as { id?: string }[]) || [];
  simIds.value = sims.map((item) => String(item.id || ""));
  bindOpen.value = true;
}
async function saveBind() {
  if (!current.value) return;
  current.value = await resourceSend("PUT", `/corp/device/phone/${current.value.id}/sim-bind`, { simIds: simIds.value });
  bindOpen.value = false;
  toast.success("已更新绑定");
  await load();
}
function openStatus(row: Record<string, unknown>, status: string) {
  current.value = row;
  statusForm.value = { status, reason: "" };
  statusOpen.value = true;
}
async function saveStatus() {
  if (!current.value) return;
  await resourceSend("PUT", `/corp/device/phone/${current.value.id}/status`, statusForm.value);
  statusOpen.value = false;
  toast.success("状态已更新");
  await load();
}
async function remove(row: Record<string, unknown>) {
  await confirm({
    title: "删除手机",
    message: "仅未发生后续操作、且未绑定手机卡的设备可以删除。",
    danger: true,
    action: async () => {
      await resourceSend("DELETE", `/corp/device/phone/${row.id}`);
      toast.success("已删除");
      await load();
    },
  });
}
function logs() {
  const items = (current.value?.timeline as { time?: string; title?: string; operator?: string; detail?: string }[]) || [];
  return items.map((item) => ({ time: item.time || "", title: item.title || "", operator: item.operator || "", detail: item.detail || "" }));
}

onMounted(load);
</script>

<template>
  <section class="page">
    <PageHeader title="手机设备管理" sub-title="设备管理 / 手机设备">
      <template #actions>
        <button v-perm="'ims:device:phone:create'" class="btn btn-pri" type="button" @click="openCreate">登记手机</button>
        <ExportButton v-perm="'ims:device:phone:export'" :params="query" :export-api="() => resourceGet('/corp/device/phone/export', query)" />
        <button v-perm="'ims:asset:verify:query'" class="btn btn-sec" type="button" @click="verifyOpen = true">关联校验</button>
      </template>
    </PageHeader>
    <QueryBar v-model="query" :fields="fields" @search="pageNo = 1; load()" @reset="pageNo = 1; load()" />
    <DataTable :columns="columns" :data="rows" :loading="loading" />
    <AppPagination v-model:page-no="pageNo" v-model:page-size="pageSize" :total="total" @change="load()" />
    <FormDrawer v-model:open="drawer" :title="editing ? '编辑手机' : '登记手机'" size="M" :model="form" :token-bag="tokenBag" :submit="save" @saved="load()">
      <el-form-item label="设备编号"><el-input v-model="form.deviceNo" maxlength="32" :disabled="Boolean(editing)" placeholder="留空自动生成" /></el-form-item>
      <el-form-item label="型号" required><el-input v-model="form.model" maxlength="64" /></el-form-item>
      <el-form-item label="类型" required><DictSelect v-model="form.osType" dict-type="dict_phone_os" /></el-form-item>
      <el-form-item label="保管人" required><UserSelect v-model="form.custodianUserId" /></el-form-item>
      <el-form-item label="IMEI"><el-input v-model="form.imei" maxlength="15" /></el-form-item>
      <el-form-item label="采购日期"><el-input v-model="form.purchaseDate" placeholder="YYYY-MM-DD" /></el-form-item>
      <el-form-item label="采购金额"><el-input v-model="form.purchaseAmount" /></el-form-item>
      <el-form-item label="备注"><el-input v-model="form.remark" maxlength="256" type="textarea" /></el-form-item>
    </FormDrawer>
    <DetailDrawer v-model:open="detailOpen" :title="String(current?.deviceNo || '手机详情')" status-dict="dict_phone_status" :status-value="String(current?.status || '')" :tabs="[{ key: 'base', label: '基本信息' }, { key: 'sim', label: '绑定手机卡' }, { key: 'acct', label: '绑定账号' }]">
      <template #base>
        <DescriptionList :items="[{ label: '型号', value: current?.model }, { label: '类型', value: current?.osLabel }, { label: '保管人', value: current?.custodianName }, { label: 'IMEI', value: current?.imeiMasked }, { label: '采购日期', value: current?.purchaseDate }, { label: '备注', value: current?.remark }]" />
        <Timeline :items="logs()" />
      </template>
      <template #sim>
        <EmptyState v-if="!(current?.sims as unknown[])?.length" desc="未绑定手机卡" />
        <p v-for="item in (current?.sims as Record<string, unknown>[]) || []" :key="String(item.id)">{{ item.phoneMasked }} {{ item.operatorLabel }} {{ item.realnameName }}</p>
        <button v-if="current?.status !== 'SCRAPPED'" v-perm="'ims:device:phone:bind-sim'" class="btn btn-sec" type="button" @click="openBind(current || {})">绑定 / 解绑</button>
      </template>
      <template #acct>
        <EmptyState v-if="!(current?.accounts as unknown[])?.length" :desc="String(current?.accountEmpty || '暂无绑定账号')" />
        <p v-for="item in (current?.accounts as Record<string, unknown>[]) || []" :key="String(item.id)">{{ item.accountNo }} {{ item.nickname }}</p>
      </template>
    </DetailDrawer>
    <AppModal v-model:open="bindOpen" title="绑定手机卡" :width="520">
      <SimCardSelect v-model="simIds" multiple :params="{ unboundOnly: true }" />
      <button class="btn btn-pri" type="button" @click="saveBind">保存</button>
    </AppModal>
    <AppModal v-model:open="statusOpen" title="报废手机" :width="520">
      <el-form-item label="原因" required><el-input v-model="statusForm.reason" maxlength="256" /></el-form-item>
      <button class="btn btn-pri" type="button" @click="saveStatus">确认</button>
    </AppModal>
    <VerifyDrawer v-model:open="verifyOpen" />
  </section>
</template>
