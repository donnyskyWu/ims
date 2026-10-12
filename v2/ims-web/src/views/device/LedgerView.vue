<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
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
import RealNameSelect from "@/components/RealNameSelect.vue";
import FileUpload from "@/components/FileUpload.vue";
import AppModal from "@/components/AppModal.vue";
import { confirm } from "@/components/confirm";
import { toast } from "@/utils/toast";
import { resourceGet, resourcePage, resourceSend } from "@/api/resource";
import ForwardDrawer from "./ForwardDrawer.vue";
import ReverseDrawer from "./ReverseDrawer.vue";
import VerifyDrawer from "./VerifyDrawer.vue";

const route = useRoute();
const kind = computed(() => (route.meta.deviceKind === "live" ? "live" : "office"));
const title = computed(() => (kind.value === "live" ? "直播设备管理" : "办公设备管理"));
const query = ref<Record<string, unknown>>({ assetCode: "", assetName: "", assetType: "", ownerUserId: "", status: "", purchaseRange: [] });
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
const forwardOpen = ref(false);
const reverseOpen = ref(false);
const verifyOpen = ref(false);
const taskId = ref("");
const importOpen = ref(false);
const importFile = ref<File | null>(null);
const importResult = ref<Record<string, unknown> | null>(null);
const lifeOpen = ref(false);
const lifeAction = ref("");
const lifeForm = ref<Record<string, unknown>>({});

const fields = computed<QueryField[]>(() => {
  const base: QueryField[] = [
    { key: "assetCode", label: "资产编号", type: "input" },
    { key: "assetName", label: "名称", type: "input" },
  ];
  if (kind.value === "live") base.push({ key: "assetType", label: "类型", type: "dict", dictType: "dict_asset_type" });
  base.push(
    { key: "ownerUserId", label: "责任人", type: "user" },
    { key: "status", label: "状态", type: "dict", dictType: "dict_asset_status" },
    { key: "purchaseRange", label: "采购日期", type: "daterange" },
  );
  return base;
});

const columns: TableColumn[] = [
  { key: "assetCode", label: "资产编号", type: "mono" },
  { key: "assetName", label: "名称" },
  { key: "assetTypeLabel", label: "类型" },
  { key: "spec", label: "规格" },
  { key: "status", label: "状态", type: "status", dictType: "dict_asset_status" },
  { key: "ownerName", label: "责任人" },
  { key: "realnameName", label: "实名人" },
  { key: "needLink", label: "关联" },
  { key: "accountCount", label: "绑定账号数" },
  { key: "purchaseDate", label: "采购日期" },
  { key: "purchaseAmount", label: "采购金额" },
  {
    key: "ops",
    label: "操作",
    type: "actions",
    actions: [
      { label: "详情", perm: "ims:device:asset:query", onClick: (row) => void openDetail(row) },
      { label: "穿透", perm: "ims:asset:forward:query", onClick: (row) => openForward(row) },
      { label: "编辑", perm: "ims:device:asset:update", show: (row) => row.status !== "SCRAPPED", onClick: (row) => openEdit(row) },
      { label: "领用", perm: "ims:device:asset:lifecycle", show: (row) => ["PENDING_REVIEW", "RETURNED", "IDLE"].includes(String(row.status)), onClick: (row) => openLife(row, "checkout") },
      { label: "流转", perm: "ims:device:asset:lifecycle", show: (row) => row.status === "IN_USE", onClick: (row) => openLife(row, "transfer") },
      { label: "归还", perm: "ims:device:asset:lifecycle", show: (row) => row.status === "IN_USE", onClick: (row) => openLife(row, "return") },
      { label: "报废", perm: "ims:device:asset:lifecycle", show: (row) => ["RETURNED", "IDLE", "REPAIRING"].includes(String(row.status)), onClick: (row) => openLife(row, "scrap") },
      { label: "删除", perm: "ims:device:asset:delete", danger: true, show: (row) => row.status === "PENDING_REVIEW", onClick: (row) => void remove(row) },
    ],
  },
];

function blank() {
  return { assetName: "", assetType: "", spec: "", purchaseDate: "", purchaseAmount: "", ownerUserId: "", realnameId: "", photoFileKeys: [] as string[], remark: "", scope: kind.value };
}

async function load() {
  loading.value = true;
  try {
    const range = query.value.purchaseRange;
    const params: Record<string, unknown> = { pageNo: pageNo.value, pageSize: pageSize.value, ...query.value };
    if (Array.isArray(range)) {
      params.purchaseDateStart = range[0] || "";
      params.purchaseDateEnd = range[1] || "";
    }
    const data = await resourcePage<Record<string, unknown>>(`/corp/device/${kind.value}/page`, params);
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
  form.value = { ...blank(), ...row, photoFileKeys: [] };
  drawer.value = true;
}
async function save(model: Record<string, unknown>, tokenKey?: string) {
  const payload = { ...model, scope: kind.value };
  if (editing.value?.id) return resourceSend("PUT", `/asset/ledger/${editing.value.id}`, payload);
  return resourceSend("POST", "/asset/ledger", payload, tokenKey);
}
async function openDetail(row: Record<string, unknown>) {
  current.value = await resourceGet(`/asset/ledger/${row.id}`);
  detailOpen.value = true;
}
function openForward(row: Record<string, unknown>) {
  current.value = row;
  forwardOpen.value = true;
}
function openLife(row: Record<string, unknown>, action: string) {
  current.value = row;
  lifeAction.value = action;
  lifeForm.value = { userId: "", checkoutDate: "", purpose: "", reason: "", returnDate: "", condition: "GOOD", remark: "", status: "IDLE", version: row.version };
  lifeOpen.value = true;
}
async function saveLife() {
  if (!current.value) return;
  const path = lifeAction.value === "status" ? "status" : lifeAction.value;
  const method = lifeAction.value === "status" ? "PUT" : "POST";
  await resourceSend(method, `/asset/ledger/${current.value.id}/${path}`, lifeForm.value);
  lifeOpen.value = false;
  toast.success("已更新");
  await load();
  if (detailOpen.value) current.value = await resourceGet(`/asset/ledger/${current.value.id}`);
}
async function remove(row: Record<string, unknown>) {
  await confirm({
    title: "删除资产",
    message: "仅待审核且未领用的资产可以删除。",
    danger: true,
    action: async () => {
      await resourceSend("DELETE", `/asset/ledger/${row.id}`);
      toast.success("已删除");
      await load();
    },
  });
}
function onImport(event: Event) {
  importFile.value = (event.target as HTMLInputElement).files?.[0] || null;
}
async function startImport() {
  if (!importFile.value) return;
  const body = new FormData();
  body.append("file", importFile.value);
  body.append("scope", kind.value);
  importResult.value = await resourceSend("POST", "/asset/ledger/import", body);
  toast.success(String(importResult.value?.message || "导入完成"));
  await load();
}
function logs() {
  const items = (current.value?.timeline as { time?: string; title?: string; operator?: string; detail?: string }[]) || [];
  return items.map((item) => ({ time: item.time || "", title: item.title || "", operator: item.operator || "", detail: item.detail || "" }));
}
function ownerText(row: Record<string, unknown> | null) {
  if (!row) return "";
  return row.ownerResigned ? `${row.ownerName}（已离职）` : String(row.ownerName || "");
}

async function openFromQuery() {
  const drawerName = String(route.query.drawer || "");
  taskId.value = String(route.query.taskId || "");
  if (drawerName === "reverse") reverseOpen.value = true;
  if (drawerName === "verify" || taskId.value) verifyOpen.value = true;
  const assetId = String(route.query.assetId || "");
  if (assetId) {
    current.value = await resourceGet(`/asset/ledger/${assetId}`);
    if (drawerName === "forward") forwardOpen.value = true;
    else detailOpen.value = true;
  }
}

watch(kind, () => {
  pageNo.value = 1;
  void load();
});
onMounted(async () => {
  await load();
  await openFromQuery();
});
</script>

<template>
  <section class="page">
    <PageHeader :title="title" :sub-title="`设备管理 / ${title}`">
      <template #actions>
        <button v-perm="'ims:device:asset:create'" class="btn btn-pri" type="button" @click="openCreate">资产登记</button>
        <button v-perm="'ims:device:asset:import'" class="btn btn-sec" type="button" @click="importOpen = true">采购导入</button>
        <ExportButton v-perm="'ims:device:asset:export'" :params="query" :export-api="() => resourceGet('/asset/ledger/export', { ...query, scope: kind })" />
        <button v-perm="'ims:asset:reverse:query'" class="btn btn-sec" type="button" @click="reverseOpen = true">反查资产</button>
        <button v-perm="'ims:asset:verify:query'" class="btn btn-sec" type="button" @click="verifyOpen = true">关联校验</button>
      </template>
    </PageHeader>
    <QueryBar v-model="query" :fields="fields" @search="pageNo = 1; load()" @reset="pageNo = 1; load()" />
    <DataTable :columns="columns" :data="rows" :loading="loading">
      <template #cell-ownerName="{ row }">{{ row.ownerResigned ? `${row.ownerName}（已离职）` : row.ownerName }}</template>
      <template #cell-needLink="{ row }"><span v-if="row.needLink">待补关联</span></template>
    </DataTable>
    <AppPagination v-model:page-no="pageNo" v-model:page-size="pageSize" :total="total" @change="load()" />
    <FormDrawer v-model:open="drawer" :title="editing ? '编辑资产' : '资产登记'" size="M" :model="form" :submit="save" @saved="load()">
      <el-form-item label="资产名称" required><el-input v-model="form.assetName" maxlength="64" /></el-form-item>
      <el-form-item label="资产类型" required>
        <el-input v-if="kind === 'office'" model-value="办公设备" disabled />
        <DictSelect v-else v-model="form.assetType" dict-type="dict_asset_type" />
      </el-form-item>
      <el-form-item label="规格"><el-input v-model="form.spec" maxlength="128" /></el-form-item>
      <el-form-item label="采购日期" required><el-input v-model="form.purchaseDate" placeholder="YYYY-MM-DD" /></el-form-item>
      <el-form-item label="采购金额"><el-input v-model="form.purchaseAmount" /></el-form-item>
      <el-form-item v-if="!editing" label="责任人" required><UserSelect v-model="form.ownerUserId" /></el-form-item>
      <el-form-item label="实名人"><RealNameSelect v-model="form.realnameId" /></el-form-item>
      <el-form-item label="照片"><FileUpload v-model="form.photoFileKeys" scene="ASSET" :limit="5" /></el-form-item>
      <el-form-item label="备注"><el-input v-model="form.remark" maxlength="256" type="textarea" /></el-form-item>
    </FormDrawer>
    <DetailDrawer v-model:open="detailOpen" :title="String(current?.assetName || '资产详情')" status-dict="dict_asset_status" :status-value="String(current?.status || '')" :tabs="[{ key: 'base', label: '基本信息' }, { key: 'acct', label: '绑定账号' }, { key: 'time', label: '时间线' }]">
      <template #base>
        <DescriptionList :items="[{ label: '编号', value: current?.assetCode }, { label: '类型', value: current?.assetTypeLabel }, { label: '规格', value: current?.spec }, { label: '责任人', value: ownerText(current) }, { label: '实名人', value: current?.realnameName }, { label: '采购日期', value: current?.purchaseDate }, { label: '采购金额', value: current?.purchaseAmount }]" />
      </template>
      <template #acct>
        <EmptyState :desc="String(current?.accountEmpty || '暂无绑定账号（账号模块上线后显示）')" />
      </template>
      <template #time>
        <Timeline :items="logs()" />
      </template>
      <template #footer>
        <button v-if="['PENDING_REVIEW', 'RETURNED', 'IDLE'].includes(String(current?.status))" v-perm="'ims:device:asset:lifecycle'" class="btn btn-pri" type="button" @click="openLife(current || {}, 'checkout')">领用</button>
        <button v-perm="'ims:asset:forward:query'" class="btn btn-sec" type="button" @click="forwardOpen = true">正向穿透</button>
      </template>
    </DetailDrawer>
    <AppModal v-model:open="lifeOpen" title="资产生命周期" :width="520">
      <template v-if="lifeAction === 'checkout' || lifeAction === 'transfer'">
        <el-form-item label="人员"><UserSelect v-model="lifeForm.userId" /></el-form-item>
        <el-form-item v-if="lifeAction === 'checkout'" label="领用日期"><el-input v-model="lifeForm.checkoutDate" placeholder="YYYY-MM-DD" /></el-form-item>
        <el-form-item v-if="lifeAction === 'checkout'" label="用途"><el-input v-model="lifeForm.purpose" maxlength="256" /></el-form-item>
        <el-form-item v-else label="原因"><DictSelect v-model="lifeForm.reason" dict-type="dict_asset_transfer_reason" /></el-form-item>
      </template>
      <template v-else-if="lifeAction === 'return'">
        <el-form-item label="归还日期"><el-input v-model="lifeForm.returnDate" placeholder="YYYY-MM-DD" /></el-form-item>
        <el-form-item label="状况">
          <el-select v-model="lifeForm.condition">
            <el-option label="完好" value="GOOD" />
            <el-option label="有损坏" value="DAMAGED" />
          </el-select>
        </el-form-item>
        <el-form-item label="说明"><el-input v-model="lifeForm.remark" maxlength="256" /></el-form-item>
      </template>
      <template v-else-if="lifeAction === 'scrap'">
        <el-form-item label="报废原因"><el-input v-model="lifeForm.reason" maxlength="256" /></el-form-item>
      </template>
      <button class="btn btn-pri" type="button" @click="saveLife">确认</button>
    </AppModal>
    <AppModal v-model:open="importOpen" title="采购导入" :width="640">
      <a href="/templates/asset-purchase.csv" download>下载模板</a>
      <input type="file" accept=".csv,text/csv" @change="onImport" />
      <button class="btn btn-pri" type="button" @click="startImport">开始导入</button>
      <p v-if="importResult">{{ importResult.message }}</p>
      <table v-if="(importResult?.errors as unknown[])?.length" class="err">
        <tr v-for="item in (importResult?.errors as Record<string, unknown>[])" :key="String(item.row) + String(item.field)">
          <td>第 {{ item.row }} 行</td>
          <td>{{ item.field }}</td>
          <td>{{ item.message }}</td>
        </tr>
      </table>
    </AppModal>
    <ForwardDrawer v-model:open="forwardOpen" :asset-id="String(current?.id || '')" />
    <ReverseDrawer v-model:open="reverseOpen" />
    <VerifyDrawer v-model:open="verifyOpen" :task-id="taskId" />
  </section>
</template>
