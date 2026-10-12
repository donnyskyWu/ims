<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import PageHeader from "@/components/PageHeader.vue";
import AppTabs from "@/components/AppTabs.vue";
import QueryBar, { type QueryField } from "@/components/QueryBar.vue";
import DataTable, { type TableColumn } from "@/components/DataTable.vue";
import AppPagination from "@/components/AppPagination.vue";
import FormDrawer from "@/components/FormDrawer.vue";
import DetailDrawer from "@/components/DetailDrawer.vue";
import DescriptionList from "@/components/DescriptionList.vue";
import Timeline from "@/components/Timeline.vue";
import StatCard, { type StatItem } from "@/components/StatCard.vue";
import EmptyState from "@/components/EmptyState.vue";
import RealNameSelect from "@/components/RealNameSelect.vue";
import DictSelect from "@/components/DictSelect.vue";
import FileUpload from "@/components/FileUpload.vue";
import RoleSelect from "@/components/RoleSelect.vue";
import UserSelect from "@/components/UserSelect.vue";
import AppModal from "@/components/AppModal.vue";
import { confirm } from "@/components/confirm";
import { toast } from "@/utils/toast";
import { request } from "@/api/http";
import { resourceGet, resourcePage, resourceSend } from "@/api/resource";
import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();
const route = useRoute();
const can = (code: string) => auth.permCodes.includes(code);
const tabs = computed(() => {
  const items = [];
  if (can("ims:cert:archive:query")) items.push({ key: "archive", label: "证件档案" });
  if (can("ims:cert:expire:query")) items.push({ key: "expire", label: "到期预警" });
  if (can("ims:cert:security:config") || can("ims:cert:security:log")) items.push({ key: "security", label: "分级与审计" });
  return items;
});
const tab = ref("archive");
const query = ref<Record<string, unknown>>({ realnameId: "", certType: "", certNo: "", status: "", expireRange: ["", ""] });
const rows = ref<Record<string, unknown>[]>([]);
const total = ref(0);
const pageNo = ref(1);
const pageSize = ref(20);
const loading = ref(false);
const metrics = ref<Record<string, unknown> | null>(null);
const metricItems = computed<StatItem[]>(() => {
  if (!metrics.value) return [];
  const rate = metrics.value.rate;
  const value = typeof rate === "string" || typeof rate === "number" ? rate : "";
  return [{ title: "数字化率", value, format: "percent", desc: metrics.value.belowStandard ? "低于 95%" : "达标" }];
});
const metricsOpen = ref(false);
const drawer = ref(false);
const form = ref<Record<string, unknown>>({});
const renewOf = ref<Record<string, unknown> | null>(null);
const detailOpen = ref(false);
const current = ref<Record<string, unknown> | null>(null);
const viewer = ref(false);
const previewUrl = ref("");
const watermark = ref("");
const logId = ref("");
const viewingId = ref("");
let closeTimer = 0;
const expireQuery = ref<Record<string, unknown>>({ realnameId: "", level: "", status: "" });
const expireRows = ref<Record<string, unknown>[]>([]);
const expireTotal = ref(0);
const stats = ref<Record<string, unknown>>({});
const levelForm = ref<Record<string, unknown>>({ l2RoleIds: [], l3UserIds: [], opacity: "0.12", position: "BOTTOM_RIGHT", version: 1 });
const logs = ref<Record<string, unknown>[]>([]);
const risks = ref<Record<string, unknown>[]>([]);

const archiveFields: QueryField[] = [
  { key: "certType", label: "证件类型", type: "dict", dictType: "dict_cert_type" },
  { key: "certNo", label: "证件号", type: "input" },
  { key: "status", label: "状态", type: "dict", dictType: "dict_cert_status" },
  { key: "expireRange", label: "有效期", type: "daterange" },
];
const expireFields: QueryField[] = [
  { key: "level", label: "预警级别", type: "dict", dictType: "dict_cert_warn_level" },
  { key: "status", label: "预警状态", type: "dict", dictType: "dict_cert_expire_status" },
];

const archiveColumns: TableColumn[] = [
  { key: "holderName", label: "持有人" },
  { key: "certTypeLabel", label: "证件类型" },
  { key: "certNoMasked", label: "证件号", type: "masked" },
  { key: "issueDate", label: "签发日期" },
  { key: "expireDate", label: "有效期至" },
  { key: "remainText", label: "剩余天数" },
  { key: "status", label: "状态", type: "status", dictType: "dict_cert_status" },
  { key: "createTime", label: "入库时间", type: "time" },
  {
    key: "ops",
    label: "操作",
    type: "actions",
    actions: [
      { label: "查看", show: (row) => row.viewLevel !== "L1" && row.status !== "PENDING_REVIEW", onClick: (row) => void openViewer(row) },
      { label: "审核", perm: "ims:cert:archive:review", show: (row) => row.status === "PENDING_REVIEW" && String(row.uploadedBy || "") !== String(auth.user?.id || ""), onClick: (row) => void review(row) },
      { label: "换证", perm: "ims:cert:expire:renew", show: (row) => row.status === "EXPIRING" || row.status === "EXPIRED", onClick: (row) => openRenew(row) },
      { label: "详情", perm: "ims:cert:archive:query", onClick: (row) => void openDetail(row) },
    ],
  },
];
const expireColumns: TableColumn[] = [
  { key: "holderName", label: "持有人" },
  { key: "certType", label: "证件类型" },
  { key: "certNoMasked", label: "证件号", type: "masked" },
  { key: "expireDate", label: "有效期至" },
  { key: "remainText", label: "剩余天数" },
  { key: "levelLabel", label: "预警级别" },
  { key: "notifyText", label: "通知状态" },
  { key: "statusLabel", label: "换证状态" },
  {
    key: "ops",
    label: "操作",
    type: "actions",
    actions: [
      { label: "换证登记", perm: "ims:cert:expire:renew", show: (row) => row.status === "WARNING" || row.status === "EXPIRED_LOCKED", onClick: (row) => openRenew(row) },
      { label: "提醒", perm: "ims:cert:expire:remind", onClick: (row) => void remind(row) },
      { label: "详情", perm: "ims:cert:expire:query", onClick: (row) => void openExpireDetail(row) },
    ],
  },
];

const statItems = computed<StatItem[]>(() => [
  { title: "黄色", value: Number(stats.value.yellow || 0) },
  { title: "红色", value: Number(stats.value.red || 0) },
  { title: "已锁定", value: Number(stats.value.locked || 0) },
  { title: "本月换证", value: Number(stats.value.renewedMonth || 0) },
]);

function blankForm(locked?: Record<string, unknown>) {
  form.value = {
    realnameId: locked?.realnameId || query.value.realnameId || "",
    certType: locked?.certType || "ID_CARD",
    certNoPlain: "",
    issueDate: "",
    expireDate: "",
    longTerm: false,
    fileKey: "",
    renewOfCertId: locked?.certId || locked?.id || "",
  };
}
async function loadArchive() {
  if (!can("ims:cert:archive:query")) return;
  loading.value = true;
  try {
    const range = (query.value.expireRange as string[]) || ["", ""];
    const data = await resourcePage<Record<string, unknown>>("/cert/archive/list", {
      pageNo: pageNo.value,
      pageSize: pageSize.value,
      realnameId: query.value.realnameId,
      certType: query.value.certType,
      certNo: query.value.certNo,
      status: query.value.status,
      expireFrom: range[0],
      expireTo: range[1],
    });
    rows.value = data.list;
    total.value = data.total;
    if (can("ims:cert:archive:metrics")) metrics.value = await resourceGet("/cert/archive/digital-metrics");
  } finally {
    loading.value = false;
  }
}
async function loadExpire() {
  if (!can("ims:cert:expire:query")) return;
  stats.value = await resourceGet("/cert/expire/stats");
  const data = await resourcePage<Record<string, unknown>>("/cert/expire/list", { pageNo: 1, pageSize: 20, ...expireQuery.value });
  expireRows.value = data.list;
  expireTotal.value = data.total;
}
async function loadSecurity() {
  if (can("ims:cert:security:config")) levelForm.value = await resourceGet("/cert/security/level-config");
  if (can("ims:cert:security:log")) {
    const data = await resourcePage<Record<string, unknown>>("/cert/security/view-logs", { pageNo: 1, pageSize: 20 });
    logs.value = data.list;
    const risk = await resourceGet<{ list: Record<string, unknown>[] }>("/cert/security/risk-report");
    risks.value = risk.list || [];
  }
}
async function reload() {
  if (tab.value === "archive") await loadArchive();
  if (tab.value === "expire") await loadExpire();
  if (tab.value === "security") await loadSecurity();
}
function openUpload() {
  renewOf.value = null;
  blankForm();
  drawer.value = true;
}
function openRenew(row: Record<string, unknown>) {
  renewOf.value = row;
  blankForm(row.certId ? row : { ...row, certId: row.id });
  drawer.value = true;
}
function onUploaded(payload: Record<string, unknown>) {
  const ocr = payload.ocr as { ok?: boolean; certNo?: string; issueDate?: string; expireDate?: string } | undefined;
  if (!ocr?.ok) return;
  if (!form.value.certNoPlain) form.value.certNoPlain = ocr.certNo || "";
  if (!form.value.issueDate) form.value.issueDate = ocr.issueDate || "";
  if (!form.value.expireDate && !form.value.longTerm) form.value.expireDate = ocr.expireDate || "";
}
async function saveCert(model: Record<string, unknown>) {
  const created = await resourceSend<Record<string, unknown>>("POST", "/cert/archive/upload", model);
  if (renewOf.value?.id && model.renewOfCertId) {
    const taskId = renewOf.value.certId ? renewOf.value.id : "";
    if (taskId) await resourceSend("PUT", `/cert/expire/${taskId}/renew`, { newCertId: created.id });
  }
  toast.success(renewOf.value ? "新证需审核生效后旧证自动归档" : "已提交审核");
  return created;
}
async function openDetail(row: Record<string, unknown>) {
  current.value = await resourceGet(`/cert/archive/${row.id}`);
  detailOpen.value = true;
}
async function openExpireDetail(row: Record<string, unknown>) {
  current.value = row;
  detailOpen.value = true;
}
async function review(row: Record<string, unknown>) {
  await openViewer(row, "review");
  await confirm({
    title: "审核证件",
    message: "通过后生效；驳回将作废并通知上传人。",
    reasonRequired: false,
    action: async () => {
      await resourceSend("PUT", `/cert/archive/${row.id}/review`, { action: "APPROVE" });
      toast.success("已通过");
      await loadArchive();
    },
  });
}
async function reject(row: Record<string, unknown>) {
  await confirm({
    title: "驳回证件",
    message: "驳回后档案作废，并通知上传人。",
    danger: true,
    reasonRequired: true,
    action: async (reason) => {
      await resourceSend("PUT", `/cert/archive/${row.id}/review`, { action: "REJECT", reason });
      toast.success("已驳回");
      await loadArchive();
    },
  });
}
async function openViewer(row: Record<string, unknown>, scene = "") {
  const certId = String(row.certId || row.id);
  const data = await resourceGet<Record<string, unknown>>(`/cert/security/view/${certId}`, scene ? { scene } : undefined);
  viewingId.value = certId;
  watermark.value = String(data.watermarkText || "");
  logId.value = String(data.logId || "");
  const file = await request<Blob>({ url: `/cert/archive/${certId}/file-url`, params: { token: data.token, scene }, responseType: "blob", silent: true });
  previewUrl.value = URL.createObjectURL(file);
  viewer.value = true;
  window.clearTimeout(closeTimer);
  closeTimer = window.setTimeout(() => void closeViewer(), 300000);
}
async function closeViewer() {
  window.clearTimeout(closeTimer);
  if (logId.value && viewingId.value) {
    await resourceGet(`/cert/security/view/${viewingId.value}`, { logId: logId.value, durationSec: 1 }).catch(() => undefined);
  }
  viewer.value = false;
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value);
  previewUrl.value = "";
}
async function remind(row: Record<string, unknown>) {
  const data = await resourceSend<Record<string, unknown>>("PUT", `/cert/expire/${row.id}/remind`, { channel: "BOTH" });
  toast.success(String(data.hint || "已催办"));
  await loadExpire();
}
async function scan() {
  await resourceSend("POST", "/cert/expire/scan");
  toast.success("扫描完成");
  await loadExpire();
}
async function saveLevel(model: Record<string, unknown>) {
  const saved = await resourceSend<Record<string, unknown>>("PUT", "/cert/security/level-config", model);
  toast.success(String(saved.hint || "下次查看即按新级别"));
  levelForm.value = saved;
  return saved;
}
async function exportRisk() {
  await resourceGet("/cert/security/risk-report", { export: 1 });
  toast.success("已开始导出");
}

watch(tab, () => void reload());
onMounted(async () => {
  const wanted = String(route.query.tab || "");
  if (wanted && tabs.value.some((item) => item.key === wanted)) tab.value = wanted;
  else if (!can("ims:cert:archive:query") && can("ims:cert:expire:query")) tab.value = "expire";
  else if (tabs.value[0]) tab.value = tabs.value[0].key;
  if (route.query.realnameId) query.value.realnameId = String(route.query.realnameId);
  await reload();
});
</script>

<template>
  <section class="page">
    <PageHeader title="证件管理" sub-title="档案、到期预警、分级与审计" />
    <AppTabs v-model:active="tab" :items="tabs" sync-query="tab" />
    <template v-if="tab === 'archive'">
      <StatCard v-if="metrics && can('ims:cert:archive:metrics')" :items="metricItems" />
      <button v-if="metrics" v-perm="'ims:cert:archive:metrics'" class="btn btn-txt" type="button" @click="metricsOpen = true">分组统计</button>
      <div class="bar">
        <button v-perm="'ims:cert:archive:upload'" class="btn btn-pri" type="button" @click="openUpload">上传证件</button>
        <RealNameSelect v-model="query.realnameId" />
      </div>
      <QueryBar v-model="query" :fields="archiveFields" @search="pageNo = 1; loadArchive()" @reset="pageNo = 1; loadArchive()" />
      <DataTable :columns="archiveColumns" :data="rows" :loading="loading">
        <template #cell-remainText="{ row }"><span :class="String(row.remainTone || '')">{{ row.remainText }}</span></template>
      </DataTable>
      <AppPagination v-model:page-no="pageNo" v-model:page-size="pageSize" :total="total" @change="loadArchive()" />
    </template>
    <template v-else-if="tab === 'expire'">
      <StatCard :items="statItems" />
      <button v-perm="'ims:cert:expire:scan'" class="btn btn-sec" type="button" @click="scan">手动扫描</button>
      <div class="bar"><RealNameSelect v-model="expireQuery.realnameId" /></div>
      <QueryBar v-model="expireQuery" :fields="expireFields" @search="loadExpire()" @reset="loadExpire()" />
      <DataTable :columns="expireColumns" :data="expireRows" />
      <p class="muted">共 {{ expireTotal }} 条</p>
    </template>
    <template v-else>
      <FormDrawer v-if="can('ims:cert:security:config')" v-model:open="detailOpen" title="级别配置" :model="levelForm" :submit="saveLevel">
        <el-form-item label="可查看原件的角色"><RoleSelect v-model="levelForm.l2RoleIds" multiple /></el-form-item>
        <el-form-item label="无水印白名单"><UserSelect v-model="levelForm.l3UserIds" multiple /></el-form-item>
        <el-form-item label="透明度"><el-input v-model="levelForm.opacity" /></el-form-item>
        <el-form-item label="位置"><el-input v-model="levelForm.position" /></el-form-item>
      </FormDrawer>
      <button v-if="can('ims:cert:security:config')" class="btn btn-pri" type="button" @click="detailOpen = true">级别配置</button>
      <h3 v-if="can('ims:cert:security:log')">查看审计</h3>
      <DataTable v-if="can('ims:cert:security:log')" :columns="[{ key: 'viewerName', label: '查看人' }, { key: 'certLabel', label: '证件' }, { key: 'viewLevel', label: '级别' }, { key: 'watermarkText', label: '水印' }, { key: 'durationSec', label: '时长' }, { key: 'ip', label: 'IP' }, { key: 'time', label: '时间', type: 'time' }]" :data="logs" />
      <h3 v-if="can('ims:cert:security:log')">异常访问</h3>
      <button v-if="can('ims:cert:security:log')" class="btn btn-sec" type="button" @click="exportRisk">导出报告</button>
      <DataTable v-if="can('ims:cert:security:log')" :columns="[{ key: 'viewerName', label: '查看人' }, { key: 'certLabel', label: '证件' }, { key: 'time', label: '时间', type: 'time' }]" :data="risks" />
      <EmptyState v-if="!can('ims:cert:security:config') && !can('ims:cert:security:log')" type="noPermission" />
    </template>
    <FormDrawer v-model:open="drawer" :title="renewOf ? '换证登记' : '上传证件'" size="M" :model="form" :submit="saveCert" @saved="reload()">
      <el-form-item label="持有人" required><RealNameSelect v-model="form.realnameId" /></el-form-item>
      <el-form-item label="证件类型" required><DictSelect v-model="form.certType" dict-type="dict_cert_type" /></el-form-item>
      <el-form-item label="证件号" required><el-input v-model="form.certNoPlain" /></el-form-item>
      <el-form-item label="签发日期" required><el-input v-model="form.issueDate" placeholder="YYYY-MM-DD" /></el-form-item>
      <el-form-item label="长期有效"><el-switch v-model="form.longTerm" /></el-form-item>
      <el-form-item v-if="!form.longTerm" label="有效期至" required><el-input v-model="form.expireDate" placeholder="YYYY-MM-DD" /></el-form-item>
      <el-form-item label="扫描件" required><FileUpload v-model="form.fileKey" scene="CERT" @uploaded="onUploaded" /></el-form-item>
    </FormDrawer>
    <DetailDrawer v-model:open="detailOpen" v-if="tab !== 'security'" :title="String(current?.holderName || '证件详情')" :tabs="[{ key: 'base', label: '信息' }, { key: 'trace', label: '轨迹' }]">
      <template #base>
        <DescriptionList :items="[{ label: '类型', value: current?.certTypeLabel || current?.certType }, { label: '证件号', value: current?.certNoMasked, type: 'masked' }, { label: '状态', value: current?.statusLabel }, { label: '查看级别', value: current?.viewLevel }]" />
        <button v-if="current?.status === 'PENDING_REVIEW'" v-perm="'ims:cert:archive:review'" class="btn btn-danger-txt" type="button" @click="current && reject(current)">驳回</button>
      </template>
      <template #trace>
        <Timeline :items="((current?.trace as { time?: string; title?: string; detail?: string }[]) || []).map((item) => ({ time: item.time || '', title: item.title || '', detail: item.detail || '' }))" />
      </template>
    </DetailDrawer>
    <AppModal v-model:open="viewer" title="证件原件" :width="800">
      <div class="viewer" @contextmenu.prevent>
        <img v-if="previewUrl" :src="previewUrl" alt="证件" />
        <p v-if="watermark">{{ watermark }}</p>
        <button class="btn btn-sec" type="button" @click="closeViewer">关闭</button>
      </div>
    </AppModal>
    <AppModal v-model:open="metricsOpen" title="数字化率" :width="520">
      <p>分母 {{ metrics?.denominator }} 名启用实名人，分子 {{ metrics?.numerator }}</p>
      <p v-for="item in (metrics?.groups as { certTypeLabel: string; count: number }[]) || []" :key="item.certTypeLabel">{{ item.certTypeLabel }} {{ item.count }}</p>
    </AppModal>
  </section>
</template>

<style scoped>
.bar { display: flex; gap: 8px; margin: 12px 0; align-items: center; }
.warning { color: var(--yellow); }
.danger, .success { }
.danger { color: var(--red); }
.success { color: var(--green); }
.viewer img { max-width: 100%; user-select: none; }
.muted { color: var(--text2); }
</style>
