<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import PageHeader from "@/components/PageHeader.vue";
import DataTable, { type TableColumn } from "@/components/DataTable.vue";
import AppPagination from "@/components/AppPagination.vue";
import DetailDrawer from "@/components/DetailDrawer.vue";
import DescriptionList from "@/components/DescriptionList.vue";
import UserSelect from "@/components/UserSelect.vue";
import AppModal from "@/components/AppModal.vue";
import { toast } from "@/utils/toast";
import { resourceGet, resourcePage, resourceSend } from "@/api/resource";

const route = useRoute();
const rows = ref<Record<string, unknown>[]>([]);
const total = ref(0);
const pageNo = ref(1);
const pageSize = ref(20);
const current = ref<Record<string, unknown> | null>(null);
const detailOpen = ref(false);
const generateOpen = ref(false);
const userId = ref("");
const resignDate = ref("");
const reason = ref("");

const columns: TableColumn[] = [
  { key: "returnNo", label: "单号", type: "mono" },
  { key: "userName", label: "离职人" },
  { key: "resignDate", label: "离职日" },
  { key: "status", label: "状态", type: "status", dictType: "dict_return_order_status" },
  { key: "overdue", label: "逾期" },
  { key: "ops", label: "操作", type: "actions", actions: [{ label: "详情", onClick: (row) => void openDetail(row) }] },
];

async function load() {
  const data = await resourcePage<Record<string, unknown>>("/account/return/page", { pageNo: pageNo.value, pageSize: pageSize.value });
  rows.value = data.list;
  total.value = data.total;
  const id = String(route.query.id || "");
  if (id) await openDetail({ id });
}
async function openDetail(row: Record<string, unknown>) {
  current.value = await resourceGet(`/account/return/${row.id}`);
  detailOpen.value = true;
}
async function generate() {
  await resourceSend("POST", "/account/return/generate", { userId: userId.value, resignDate: resignDate.value }, `ret-${Date.now()}`);
  generateOpen.value = false;
  toast.success("已补建");
  await load();
}
async function act(item: Record<string, unknown>, action: string) {
  if (!current.value) return;
  current.value = await resourceSend("PUT", `/account/return/item/${item.id}`, { action, remark: action === "DISPUTE" ? "争议待核" : "" });
  toast.success("已处理");
}
async function closeOrder() {
  if (!current.value) return;
  current.value = await resourceSend("PUT", `/account/return/${current.value.id}/close`, {});
  toast.success("已闭环");
  await load();
}
async function suspend(resume = false) {
  if (!current.value) return;
  current.value = await resourceSend("PUT", `/account/return/${current.value.id}/suspend`, resume ? { action: "RESUME" } : { reason: reason.value });
  toast.success(resume ? "已恢复" : "已挂起");
}
onMounted(load);
</script>

<template>
  <section>
    <PageHeader title="账号归还" sub-title="公司资产 / 账号归还">
      <template #actions>
        <button v-perm="'ims:account:return:generate'" class="btn btn-pri" type="button" @click="generateOpen = true">补建归还单</button>
      </template>
    </PageHeader>
    <DataTable :columns="columns" :data="rows" />
    <AppPagination v-model:page-no="pageNo" v-model:page-size="pageSize" :total="total" @change="load()" />
    <DetailDrawer v-model:open="detailOpen" :title="String(current?.returnNo || '归还单')" status-dict="dict_return_order_status" :status-value="String(current?.status || '')">
      <DescriptionList :items="[{ label: '离职人', value: current?.userName }, { label: '离职日', value: current?.resignDate }]" />
      <div v-for="item in (current?.items as Record<string, unknown>[]) || []" :key="String(item.id)">
        <p>{{ item.itemType }} {{ item.itemStatus }}</p>
        <button v-if="item.itemStatus === 'PENDING'" v-perm="'ims:account:return:handle'" class="btn btn-sec" type="button" @click="act(item, 'RETURN')">归还</button>
        <button v-if="item.itemStatus === 'PENDING'" v-perm="'ims:account:return:handle'" class="btn btn-sec" type="button" @click="act(item, 'DISPUTE')">争议</button>
      </div>
      <template #footer>
        <button v-perm="'ims:account:return:close'" class="btn btn-pri" type="button" @click="closeOrder">闭环</button>
        <el-input v-model="reason" maxlength="256" placeholder="挂起原因" />
        <button v-perm="'ims:account:return:handle'" class="btn btn-sec" type="button" @click="suspend(false)">挂起</button>
        <button v-perm="'ims:account:return:handle'" class="btn btn-sec" type="button" @click="suspend(true)">恢复</button>
      </template>
    </DetailDrawer>
    <AppModal v-model:open="generateOpen" title="补建归还单" :width="520">
      <el-form-item label="离职人"><UserSelect v-model="userId" allow-disabled /></el-form-item>
      <el-form-item label="离职日"><el-input v-model="resignDate" placeholder="YYYY-MM-DD" /></el-form-item>
      <button class="btn btn-pri" type="button" @click="generate">生成</button>
    </AppModal>
  </section>
</template>
