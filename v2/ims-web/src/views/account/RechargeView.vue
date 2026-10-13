<script setup lang="ts">
import { onMounted, ref } from "vue";
import PageHeader from "@/components/PageHeader.vue";
import DataTable, { type TableColumn } from "@/components/DataTable.vue";
import AppPagination from "@/components/AppPagination.vue";
import FormDrawer from "@/components/FormDrawer.vue";
import AccountSelect from "@/components/AccountSelect.vue";
import DictSelect from "@/components/DictSelect.vue";
import FileUpload from "@/components/FileUpload.vue";
import ExportButton from "@/components/ExportButton.vue";
import StatCard from "@/components/StatCard.vue";
import MoneyText from "@/components/MoneyText.vue";
import AppModal from "@/components/AppModal.vue";
import { toast } from "@/utils/toast";
import { resourceGet, resourcePage, resourceSend } from "@/api/resource";

const rows = ref<Record<string, unknown>[]>([]);
const total = ref(0);
const pageNo = ref(1);
const pageSize = ref(20);
const overview = ref<Record<string, unknown>>({});
const drawer = ref(false);
const editing = ref<Record<string, unknown> | null>(null);
const form = ref(blank());
const month = ref("");
const summaryOpen = ref(false);
const summary = ref<Record<string, unknown>[]>([]);
const eventOpen = ref(false);
const events = ref<Record<string, unknown>[]>([]);

const columns: TableColumn[] = [
  { key: "accountNo", label: "账号" },
  { key: "amount", label: "金额" },
  { key: "channelLabel", label: "渠道" },
  { key: "rechargeDate", label: "日期" },
  { key: "verifyLabel", label: "核对" },
  { key: "operatorName", label: "经办人" },
  { key: "ops", label: "操作", type: "actions", actions: [{ label: "编辑", perm: "ims:account:recharge:update", show: (row) => row.verifyStatus !== "MATCHED", onClick: (row) => openEdit(row) }] },
];

async function load() {
  const data = await resourcePage<Record<string, unknown>>("/account/recharge/page", { pageNo: pageNo.value, pageSize: pageSize.value });
  rows.value = data.list;
  total.value = data.total;
  overview.value = await resourceGet("/account/recharge/overview");
}
function blank() {
  return { accountId: "", amount: "", channel: "ALIPAY", rechargeDate: "", voucherFileKey: "", remark: "" };
}
function openCreate() {
  editing.value = null;
  form.value = blank();
  drawer.value = true;
}
function openEdit(row: Record<string, unknown>) {
  editing.value = row;
  form.value = {
    accountId: "",
    amount: String(row.amount || ""),
    channel: String(row.channel || "ALIPAY"),
    rechargeDate: String(row.rechargeDate || ""),
    remark: String(row.remark || ""),
    voucherFileKey: String(row.voucherFileKey || ""),
  };
  drawer.value = true;
}
async function save(model: Record<string, unknown>) {
  const voucher = Array.isArray(model.voucherFileKey) ? model.voucherFileKey[0] : model.voucherFileKey;
  const body = { ...model, voucherFileKey: voucher || "" };
  if (editing.value?.id) return resourceSend("PUT", `/account/recharge/${editing.value.id}`, body);
  return resourceSend("POST", "/account/recharge", body, `rch-${Date.now()}`);
}
async function verify() {
  const data = await resourceSend<{ hintCode?: number; message?: string }>("POST", "/account/recharge/verify", { month: month.value, simulate: "diff" });
  toast.success(data.hintCode === 1026 ? "差异率达到 2%，已生成核查工单" : "核对完成");
  await load();
}
async function openSummary() {
  const data = await resourceGet<{ list: Record<string, unknown>[] }>("/account/recharge/summary", { dimension: "platform" });
  summary.value = data.list || [];
  summaryOpen.value = true;
}
async function searchEvents() {
  const data = await resourcePage<Record<string, unknown>>("/account/timeline/events", { pageNo: 1, pageSize: 20, eventType: "RECHARGE" });
  events.value = data.list;
  eventOpen.value = true;
}
onMounted(load);
</script>

<template>
  <section>
    <PageHeader title="冲话费" sub-title="公司资产 / 冲话费">
      <template #actions>
        <button v-perm="'ims:account:recharge:create'" class="btn btn-pri" type="button" @click="openCreate">登记</button>
        <ExportButton v-perm="'ims:account:recharge:export'" :export-api="() => resourceGet('/account/recharge/export')" />
        <button class="btn btn-sec" type="button" @click="openSummary">成本汇总</button>
        <button v-perm="'ims:account:timeline:query'" class="btn btn-sec" type="button" @click="searchEvents">事件检索</button>
      </template>
    </PageHeader>
    <p v-if="overview.banner">{{ overview.banner }}</p>
    <StatCard :items="[{ title: '本月未核对', value: Number(overview.pendingCount || 0) }, { title: '上月差异率', value: String(overview.lastDiffRate || '—') }]" />
    <DataTable :columns="columns" :data="rows" />
    <p v-for="row in rows" :key="String(row.id)"><MoneyText :value="String(row.amount || '')" /></p>
    <AppPagination v-model:page-no="pageNo" v-model:page-size="pageSize" :total="total" @change="load()" />
    <el-form-item label="核对月份"><el-input v-model="month" placeholder="YYYY-MM" /></el-form-item>
    <button v-perm="'ims:account:recharge:verify'" class="btn btn-pri" type="button" @click="verify">月度核对</button>
    <FormDrawer v-model:open="drawer" :title="editing ? '编辑充值' : '登记充值'" :model="form" :submit="save" @saved="load()">
      <el-form-item v-if="!editing" label="账号" required><AccountSelect v-model="form.accountId" /></el-form-item>
      <el-form-item label="金额" required><el-input v-model="form.amount" /></el-form-item>
      <el-form-item label="渠道"><DictSelect v-model="form.channel" dict-type="dict_recharge_channel" /></el-form-item>
      <el-form-item label="日期" required><el-input v-model="form.rechargeDate" placeholder="YYYY-MM-DD" /></el-form-item>
      <el-form-item v-perm="'ims:account:recharge:voucher'" label="凭证"><FileUpload v-model="form.voucherFileKey" scene="ACCOUNT" /></el-form-item>
      <el-form-item label="备注"><el-input v-model="form.remark" maxlength="256" /></el-form-item>
    </FormDrawer>
    <AppModal v-model:open="summaryOpen" title="成本汇总" :width="520">
      <p v-for="(item, index) in summary" :key="index">{{ item.name }} {{ item.amount }}</p>
    </AppModal>
    <AppModal v-model:open="eventOpen" title="事件检索" :width="800">
      <p v-for="item in events" :key="String(item.id)">{{ item.title }} {{ item.eventTime }}</p>
    </AppModal>
  </section>
</template>
