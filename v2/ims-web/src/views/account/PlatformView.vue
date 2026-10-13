<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
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
import CompanySelect from "@/components/CompanySelect.vue";
import RealNameSelect from "@/components/RealNameSelect.vue";
import SimCardSelect from "@/components/SimCardSelect.vue";
import AssetSelect from "@/components/AssetSelect.vue";
import IpGroupSelect from "@/components/IpGroupSelect.vue";
import AuthorSelect from "@/components/AuthorSelect.vue";
import AppModal from "@/components/AppModal.vue";
import { confirm } from "@/components/confirm";
import { toast } from "@/utils/toast";
import { BizError } from "@/api/http";
import { resourceGet, resourcePage, resourceSend } from "@/api/resource";

const route = useRoute();
const router = useRouter();
const platform = computed(() => String(route.meta.platform || "DOUYIN"));
const title = computed(() => String(route.meta.title || "账号"));
const query = ref<Record<string, unknown>>({ keyword: "", status: "" });
const companyId = ref("");
const ipGroupId = ref("");
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
const logs = ref<Record<string, unknown>[]>([]);
const assets = ref<Record<string, unknown>[]>([]);
const credential = ref<Record<string, unknown>>({});
const cancelOpen = ref(false);
const cancelReason = ref("");
const bindOpen = ref(false);
const assetIds = ref<string[]>([]);
const cookie = ref("");

const fields: QueryField[] = [
  { key: "keyword", label: "编号/昵称", type: "input" },
  { key: "status", label: "状态", type: "dict", dictType: "dict_account_status" },
];
const columns: TableColumn[] = [
  { key: "accountNo", label: "账号编号", type: "mono" },
  { key: "nickname", label: "昵称" },
  { key: "companyName", label: "公司" },
  { key: "realnameName", label: "实名人" },
  { key: "ownerName", label: "责任人" },
  { key: "ipGroupText", label: "IP 组" },
  { key: "authorName", label: "作者" },
  { key: "status", label: "状态", type: "status", dictType: "dict_account_status" },
  { key: "collectLabel", label: "采集" },
  { key: "rechargeTotal", label: "累计充值" },
  {
    key: "ops",
    label: "操作",
    type: "actions",
    actions: [
      { label: "详情", onClick: (row) => void openDetail(row) },
      { label: "编辑", perm: "ims:corp:account:update", show: (row) => row.status !== "CANCELLED", onClick: (row) => openEdit(row) },
      { label: "领用", perm: "ims:account:apply:create", show: (row) => row.status === "IN_POOL", onClick: (row) => router.push({ path: "/ims/account/apply", query: { accountId: String(row.id) } }) },
    ],
  },
];

function blank() {
  return { platform: platform.value, nickname: "", accountNo: "", companyId: "", realnameId: "", simCardId: "", phoneId: "", ipGroupId: "", authorId: "", remark: "" };
}

async function load() {
  loading.value = true;
  try {
    const data = await resourcePage<Record<string, unknown>>("/corp/account/page", {
      pageNo: pageNo.value,
      pageSize: pageSize.value,
      platform: platform.value,
      companyId: companyId.value || undefined,
      ipGroupId: ipGroupId.value || undefined,
      ...query.value,
    });
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
  form.value = {
    platform: platform.value,
    nickname: String(row.nickname || ""),
    accountNo: String(row.accountNo || ""),
    companyId: row.companyId ? String(row.companyId) : "",
    realnameId: row.realnameId ? String(row.realnameId) : "",
    simCardId: row.simCardId ? String(row.simCardId) : "",
    phoneId: row.phoneId ? String(row.phoneId) : "",
    ipGroupId: row.ipGroupId ? String(row.ipGroupId) : "",
    authorId: row.authorId ? String(row.authorId) : "",
    remark: String(row.remark || ""),
  };
  drawer.value = true;
}
async function save(model: Record<string, unknown>) {
  if (!model.ipGroupId) {
    toast.error("请选择 IP 小组");
    throw new Error("请选择 IP 小组");
  }
  const body = { ...model, platform: platform.value };
  const nextCompany = String(model.companyId || "");
  const nextRealname = String(model.realnameId || "");
  if (editing.value?.id && editing.value.status === "IN_USE" && (nextCompany !== String(editing.value.companyId || "") || nextRealname !== String(editing.value.realnameId || ""))) {
    await confirm({ title: "在用账号", message: "修改公司或实名人后，已领用账号仍保持在用。", action: async () => undefined });
  }
  try {
    if (editing.value?.id) return await resourceSend("PUT", `/corp/account/${editing.value.id}`, body);
    return await resourceSend("POST", "/corp/account", body, `acct-${Date.now()}`);
  } catch (error) {
    const biz = error as BizError;
    toast.error(biz.code === 1223 ? `${biz.message}。请到 IP 组的关联作者页签设置主作者。` : biz.message || "保存失败");
    throw error;
  }
}
async function openDetail(row: Record<string, unknown>) {
  current.value = await resourceGet(`/corp/account/${row.id}`);
  const line = await resourceGet<{ list: Record<string, unknown>[] }>(`/account/timeline/${row.id}`);
  logs.value = line.list || [];
  assets.value = await resourceGet<Record<string, unknown>[]>(`/corp/account/${row.id}/assets`);
  credential.value = {};
  detailOpen.value = true;
}
async function cancel() {
  if (!current.value) return;
  await resourceSend("PUT", `/corp/account/${current.value.id}/cancel`, { reason: cancelReason.value });
  toast.success("已注销");
  cancelOpen.value = false;
  detailOpen.value = false;
  await load();
}
async function removeRow() {
  if (!current.value) return;
  await confirm({
    title: "删除账号",
    message: "仅在库且无后续记录的账号可删除。",
    action: async () => {
      await resourceSend("DELETE", `/corp/account/${current.value?.id}`);
      toast.success("已删除");
      detailOpen.value = false;
      await load();
    },
  });
}
async function saveCredential() {
  if (!current.value) return;
  credential.value = await resourceSend("PUT", `/corp/account/${current.value.id}/collect/credential`, { cookie: cookie.value });
  cookie.value = "";
  toast.success("凭证已保存，须导入 Collector");
}
async function probe() {
  if (!current.value) return;
  credential.value = await resourceSend("POST", `/corp/account/${current.value.id}/collect/probe`, {});
  toast.success(String(credential.value.message || "已测试"));
}
async function importCollector() {
  if (!current.value) return;
  credential.value = await resourceSend("POST", `/corp/account/${current.value.id}/collect/import`, {});
  toast.success(String(credential.value.message || "已导入"));
}
async function qr() {
  if (!current.value) return;
  credential.value = await resourceSend("POST", `/corp/account/${current.value.id}/collect/qr-login`, {});
  toast.success(String(credential.value.message || "已扫码"));
}
async function bindAssets() {
  if (!current.value) return;
  await resourceSend("PUT", `/corp/account/${current.value.id}/asset-bind`, { assetIds: assetIds.value });
  assets.value = await resourceGet(`/corp/account/${current.value.id}/assets`);
  bindOpen.value = false;
  toast.success("已更新绑定");
}

watch(platform, () => {
  pageNo.value = 1;
  void load();
});
onMounted(load);
</script>

<template>
  <section>
    <PageHeader :title="title" :sub-title="`公司资产 / 账号管理 / ${title}`">
      <template #actions>
        <button v-perm="'ims:corp:account:create'" class="btn btn-pri" type="button" @click="openCreate">登记</button>
        <ExportButton v-perm="'ims:corp:account:export'" :params="{ ...query, platform }" :export-api="() => resourceGet('/corp/account/export', { ...query, platform })" />
      </template>
    </PageHeader>
    <div class="filters">
      <QueryBar v-model="query" :fields="fields" @search="pageNo = 1; load()" @reset="companyId = ''; ipGroupId = ''; pageNo = 1; load()" />
      <CompanySelect v-model="companyId" />
      <IpGroupSelect v-model="ipGroupId" only-small />
    </div>
    <DataTable :columns="columns" :data="rows" :loading="loading" />
    <AppPagination v-model:page-no="pageNo" v-model:page-size="pageSize" :total="total" @change="load()" />
    <FormDrawer v-model:open="drawer" :title="editing ? '编辑账号' : '登记账号'" :model="form" :submit="save" @saved="load()">
      <el-form-item label="昵称" required><el-input v-model="form.nickname" maxlength="64" /></el-form-item>
      <el-form-item v-if="!editing" label="账号编号"><el-input v-model="form.accountNo" maxlength="32" placeholder="留空自动生成" /></el-form-item>
      <el-form-item label="公司" required><CompanySelect v-model="form.companyId" /></el-form-item>
      <el-form-item label="实名人" required><RealNameSelect v-model="form.realnameId" /></el-form-item>
      <el-form-item label="IP 小组" required><IpGroupSelect v-model="form.ipGroupId" only-small /></el-form-item>
      <el-form-item label="作者"><AuthorSelect v-model="form.authorId" :ip-group-id="String(form.ipGroupId || '')" /></el-form-item>
      <el-form-item label="手机卡"><SimCardSelect v-model="form.simCardId" /></el-form-item>
      <el-form-item label="备注"><el-input v-model="form.remark" maxlength="256" type="textarea" /></el-form-item>
    </FormDrawer>
    <DetailDrawer v-model:open="detailOpen" :title="String(current?.nickname || '账号详情')" status-dict="dict_account_status" :status-value="String(current?.status || '')" :tabs="[{ key: 'base', label: '基本信息' }, { key: 'collect', label: '采集' }, { key: 'time', label: '领用时间线' }, { key: 'asset', label: '关联资产' }]">
      <template #base>
        <DescriptionList :items="[{ label: '编号', value: current?.accountNo }, { label: '平台', value: current?.platformLabel }, { label: '公司', value: current?.companyName }, { label: '实名人', value: current?.realnameName }, { label: '责任人', value: current?.ownerName }, { label: '累计充值', value: current?.rechargeTotal }, { label: 'IP 组', value: current?.ipGroupText }, { label: '作者', value: current?.authorName }, { label: '备注', value: current?.remark }]" />
        <p v-if="(current?.warnings as string[] | undefined)?.includes('REALNAME_MISMATCH')">实名人不一致</p>
      </template>
      <template #collect>
        <p>采集状态：{{ current?.collectLabel }}</p>
        <p v-if="credential.hasCredential">凭证 {{ credential.cookieMask || credential.tokenMask }}</p>
        <el-form-item label="Cookie"><el-input v-model="cookie" type="textarea" /></el-form-item>
        <button v-perm="'ims:corp:account:collect'" class="btn btn-pri" type="button" @click="saveCredential">保存凭证</button>
        <button v-perm="'ims:corp:account:collect'" class="btn btn-sec" type="button" @click="probe">测试连接</button>
        <button v-perm="'ims:corp:account:collect'" class="btn btn-sec" type="button" @click="importCollector">导入 Collector</button>
        <button v-perm="'ims:corp:account:collect'" class="btn btn-sec" type="button" @click="qr">扫码登录</button>
        <p>{{ credential.hint || credential.message }}</p>
      </template>
      <template #time>
        <Timeline :items="logs.map((item) => ({ title: String(item.title || ''), time: String(item.eventTime || ''), detail: String(item.detail || '') }))" />
        <ExportButton v-perm="'ims:account:timeline:export'" :export-api="() => resourceGet(`/account/timeline/${current?.id}/export`)" />
      </template>
      <template #asset>
        <EmptyState v-if="!assets.length" desc="暂无绑定资产" />
        <p v-for="item in assets" :key="String(item.id)">{{ item.assetCode }} {{ item.assetName }}</p>
        <button v-perm="'ims:corp:account:update'" class="btn btn-sec" type="button" @click="bindOpen = true">绑定资产</button>
      </template>
      <template #footer>
        <button v-if="current?.canCancel" v-perm="'ims:corp:account:update'" class="btn btn-sec" type="button" @click="cancelOpen = true">注销</button>
        <button v-if="current?.status === 'IN_POOL'" v-perm="'ims:corp:account:delete'" class="btn btn-sec" type="button" @click="removeRow">删除</button>
        <button v-if="current?.canApply" v-perm="'ims:account:apply:create'" class="btn btn-pri" type="button" @click="router.push({ path: '/ims/account/apply', query: { accountId: String(current?.id || '') } })">领用</button>
        <button v-if="current?.canUnfreeze" v-perm="'ims:account:unfreeze'" class="btn btn-pri" type="button" @click="router.push({ path: '/ims/account/transfer', query: { accountId: String(current?.id || ''), action: 'unfreeze' } })">解冻</button>
      </template>
    </DetailDrawer>
    <AppModal v-model:open="cancelOpen" title="注销账号" :width="520">
      <el-form-item label="原因" required><el-input v-model="cancelReason" maxlength="256" /></el-form-item>
      <button class="btn btn-pri" type="button" @click="cancel">确认注销</button>
    </AppModal>
    <AppModal v-model:open="bindOpen" title="绑定资产" :width="520">
      <AssetSelect v-model="assetIds" multiple />
      <button class="btn btn-pri" type="button" @click="bindAssets">保存</button>
    </AppModal>
  </section>
</template>
