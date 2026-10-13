<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import PageHeader from "@/components/PageHeader.vue";
import DataTable, { type TableColumn } from "@/components/DataTable.vue";
import AppPagination from "@/components/AppPagination.vue";
import FormDrawer from "@/components/FormDrawer.vue";
import DetailDrawer from "@/components/DetailDrawer.vue";
import DescriptionList from "@/components/DescriptionList.vue";
import AccountSelect from "@/components/AccountSelect.vue";
import AppModal from "@/components/AppModal.vue";
import { toast } from "@/utils/toast";
import { resourceGet, resourcePage, resourceSend } from "@/api/resource";

const route = useRoute();
const rows = ref<Record<string, unknown>[]>([]);
const total = ref(0);
const pageNo = ref(1);
const pageSize = ref(20);
const drawer = ref(false);
const form = ref(blankApply());
const current = ref<Record<string, unknown> | null>(null);
const detailOpen = ref(false);
const confirmOpen = ref(false);
const note = ref("");
const passwordReset = ref(false);
const eventOpen = ref(false);
const events = ref<Record<string, unknown>[]>([]);

const columns: TableColumn[] = [
  { key: "applyNo", label: "单号", type: "mono" },
  { key: "accountNo", label: "账号" },
  { key: "applicantName", label: "申请人" },
  { key: "applyStatus", label: "状态", type: "status", dictType: "dict_apply_status" },
  { key: "currentStep", label: "当前步骤" },
  { key: "ops", label: "操作", type: "actions", actions: [{ label: "详情", onClick: (row) => void openDetail(row) }] },
];

async function load() {
  const data = await resourcePage<Record<string, unknown>>("/account/apply/page", { pageNo: pageNo.value, pageSize: pageSize.value });
  rows.value = data.list;
  total.value = data.total;
  const id = String(route.query.id || "");
  if (id) await openDetail({ id });
}
function blankApply() {
  return { accountId: String(route.query.accountId || ""), purpose: "", planStart: "", planEnd: "", assetId: String(route.query.assetId || "") };
}
function openCreate() {
  form.value = blankApply();
  drawer.value = true;
}
async function save(model: Record<string, unknown>) {
  return resourceSend("POST", "/account/apply", model, `apply-${Date.now()}`);
}
async function openDetail(row: Record<string, unknown>) {
  current.value = await resourceGet(`/account/apply/${row.id}`);
  detailOpen.value = true;
}
async function handover() {
  if (!current.value) return;
  current.value = await resourceSend("PUT", `/account/apply/${current.value.id}/confirm`, { handover: { passwordReset: passwordReset.value, note: note.value } });
  confirmOpen.value = false;
  toast.success("交接已确认");
  await load();
}
async function searchEvents() {
  const data = await resourcePage<Record<string, unknown>>("/account/timeline/events", { pageNo: 1, pageSize: 20 });
  events.value = data.list;
  eventOpen.value = true;
}
onMounted(() => {
  if (route.query.accountId) openCreate();
  void load();
});
</script>

<template>
  <section>
    <PageHeader title="账号领用" sub-title="公司资产 / 账号领用">
      <template #actions>
        <button v-perm="'ims:account:apply:create'" class="btn btn-pri" type="button" @click="openCreate">发起领用</button>
        <button v-perm="'ims:account:timeline:query'" class="btn btn-sec" type="button" @click="searchEvents">事件检索</button>
      </template>
    </PageHeader>
    <DataTable :columns="columns" :data="rows" />
    <AppPagination v-model:page-no="pageNo" v-model:page-size="pageSize" :total="total" @change="load()" />
    <FormDrawer v-model:open="drawer" title="发起领用" :model="form" :submit="save" @saved="load()">
      <el-form-item label="账号" required><AccountSelect v-model="form.accountId" status="IN_POOL" /></el-form-item>
      <el-form-item label="用途" required><el-input v-model="form.purpose" maxlength="256" /></el-form-item>
      <el-form-item label="计划开始" required><el-input v-model="form.planStart" placeholder="YYYY-MM-DD" /></el-form-item>
      <el-form-item label="计划结束" required><el-input v-model="form.planEnd" placeholder="YYYY-MM-DD" /></el-form-item>
    </FormDrawer>
    <DetailDrawer v-model:open="detailOpen" :title="String(current?.applyNo || '领用单')" status-dict="dict_apply_status" :status-value="String(current?.applyStatus || '')">
      <DescriptionList :items="[{ label: '账号', value: current?.accountNo }, { label: '申请人', value: current?.applicantName }, { label: '用途', value: current?.purpose }, { label: '步骤', value: current?.currentStep }]" />
      <p v-if="current?.idle">领用后长期未使用</p>
      <template #footer>
        <button v-if="current?.applyStatus === 'PENDING_HANDOVER'" class="btn btn-pri" type="button" @click="confirmOpen = true">交接确认</button>
      </template>
    </DetailDrawer>
    <AppModal v-model:open="confirmOpen" title="交接确认" :width="520">
      <label><input v-model="passwordReset" type="checkbox" /> 密码已重置</label>
      <el-form-item label="说明"><el-input v-model="note" maxlength="512" /></el-form-item>
      <button class="btn btn-pri" type="button" @click="handover">确认</button>
    </AppModal>
    <AppModal v-model:open="eventOpen" title="事件检索" :width="800">
      <p v-for="item in events" :key="String(item.id)">{{ item.eventLabel }} {{ item.title }} {{ item.eventTime }}</p>
    </AppModal>
  </section>
</template>
