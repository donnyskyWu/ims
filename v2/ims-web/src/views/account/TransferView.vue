<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import PageHeader from "@/components/PageHeader.vue";
import DataTable, { type TableColumn } from "@/components/DataTable.vue";
import AppPagination from "@/components/AppPagination.vue";
import FormDrawer from "@/components/FormDrawer.vue";
import AccountSelect from "@/components/AccountSelect.vue";
import UserSelect from "@/components/UserSelect.vue";
import DictSelect from "@/components/DictSelect.vue";
import { toast } from "@/utils/toast";
import { resourcePage, resourceSend } from "@/api/resource";

const route = useRoute();
const rows = ref<Record<string, unknown>[]>([]);
const total = ref(0);
const pageNo = ref(1);
const pageSize = ref(20);
const drawer = ref(false);
const form = ref(blank());

const columns: TableColumn[] = [
  { key: "transferNo", label: "单号", type: "mono" },
  { key: "accountNo", label: "账号" },
  { key: "typeLabel", label: "类型" },
  { key: "fromName", label: "原责任人" },
  { key: "toName", label: "新责任人" },
  { key: "status", label: "状态", type: "status", dictType: "dict_transfer_status" },
  {
    key: "ops",
    label: "操作",
    type: "actions",
    actions: [
      { label: "确认", perm: "ims:account:transfer:confirm", show: (row) => row.status === "PENDING_CONFIRM", onClick: (row) => void confirmRow(row, true) },
      { label: "拒绝", perm: "ims:account:transfer:confirm", show: (row) => row.status === "PENDING_CONFIRM", onClick: (row) => void confirmRow(row, false) },
      { label: "撤销", perm: "ims:account:transfer:revoke", show: (row) => row.status === "PENDING_CONFIRM", onClick: (row) => void revoke(row) },
    ],
  },
];

function blank() {
  return { transferType: "TRANSFER", accountId: String(route.query.accountId || ""), toUserId: "", reasonType: "", remark: "", syncAssets: false };
}
async function load() {
  const data = await resourcePage<Record<string, unknown>>("/account/transfer/page", { pageNo: pageNo.value, pageSize: pageSize.value });
  rows.value = data.list;
  total.value = data.total;
}
async function save(model: Record<string, unknown>) {
  return resourceSend("POST", "/account/transfer", model, `tr-${Date.now()}`);
}
async function confirmRow(row: Record<string, unknown>, accept: boolean) {
  await resourceSend("PUT", `/account/transfer/${row.id}/confirm`, { accept });
  toast.success(accept ? "已确认" : "已拒绝");
  await load();
}
async function revoke(row: Record<string, unknown>) {
  await resourceSend("PUT", `/account/transfer/${row.id}/revoke`, { reason: "发起人撤销" });
  toast.success("已撤销");
  await load();
}
async function unfreeze() {
  const accountId = String(route.query.accountId || form.value.accountId || "");
  if (!accountId) return;
  await resourceSend("POST", `/account/${accountId}/unfreeze`, { remark: "解冻回池" });
  toast.success("已解冻");
}
onMounted(() => {
  form.value.accountId = String(route.query.accountId || "");
  if (route.query.accountId) drawer.value = true;
  void load();
});
</script>

<template>
  <section>
    <PageHeader title="账号流转" sub-title="公司资产 / 账号流转">
      <template #actions>
        <button v-perm="'ims:account:transfer:create'" class="btn btn-pri" type="button" @click="drawer = true">发起流转</button>
        <button v-if="route.query.action === 'unfreeze'" v-perm="'ims:account:unfreeze'" class="btn btn-sec" type="button" @click="unfreeze">解冻回池</button>
      </template>
    </PageHeader>
    <DataTable :columns="columns" :data="rows" />
    <AppPagination v-model:page-no="pageNo" v-model:page-size="pageSize" :total="total" @change="load()" />
    <FormDrawer v-model:open="drawer" title="发起流转或收回" :model="form" :submit="save" @saved="load()">
      <el-form-item label="类型"><DictSelect v-model="form.transferType" dict-type="dict_transfer_type" /></el-form-item>
      <el-form-item label="账号" required><AccountSelect v-model="form.accountId" status="IN_USE" /></el-form-item>
      <el-form-item v-if="form.transferType !== 'RECALL'" label="新责任人"><UserSelect v-model="form.toUserId" /></el-form-item>
      <el-form-item v-if="form.transferType !== 'RECALL'" label="原因"><DictSelect v-model="form.reasonType" dict-type="dict_transfer_reason" /></el-form-item>
      <el-form-item label="说明"><el-input v-model="form.remark" maxlength="512" type="textarea" /></el-form-item>
      <label><input v-model="form.syncAssets" type="checkbox" /> 同步在用资产责任人</label>
    </FormDrawer>
  </section>
</template>
