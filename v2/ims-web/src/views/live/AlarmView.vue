<script setup lang="ts">
import { onMounted, ref } from "vue";
import PageHeader from "@/components/PageHeader.vue";
import AppTabs from "@/components/AppTabs.vue";
import DataTable, { type TableColumn } from "@/components/DataTable.vue";
import ChartPanel from "@/components/ChartPanel.vue";
import FormDrawer from "@/components/FormDrawer.vue";
import { resourceGet, resourcePage, resourceSend } from "@/api/resource";
import { hasPerm } from "@/utils/perm";
import { useAuthStore } from "@/stores/auth";
import { ruleError } from "./logic";

const auth = useAuthStore();
const tab = ref("records");
const rows = ref<Record<string, unknown>[]>([]);
const rules = ref<Record<string, unknown>[]>([]);
const stats = ref<Record<string, unknown>>({});
const drawer = ref(false);
const form = ref<Record<string, unknown>>({ ruleType: "THRESHOLD", metric: "VIEWER_DROP", operator: "PCT_DROP", threshold: 30, windowMinutes: 10, level: "2", notifyRoleIds: [104] });
const error = ref("");
const handleId = ref("");
const remark = ref("");

const columns: TableColumn[] = [
  { key: "id", label: "告警 ID" },
  { key: "sessionCode", label: "场次 ID", type: "mono" },
  { key: "ruleName", label: "规则" },
  { key: "levelLabel", label: "级别" },
  { key: "content", label: "内容" },
  { key: "occurAt", label: "发生时间" },
  { key: "handleStatusLabel", label: "处置" },
  { key: "escalatedLabel", label: "升级" },
  { key: "ops", label: "操作", type: "actions", actions: [{ label: "处置", perm: "ims:live:alarm:handle", onClick: (row) => { handleId.value = String(row.id); } }] },
];

async function load() {
  const data = await resourcePage<Record<string, unknown>>("/live/alarm/records", { pageNo: 1, pageSize: 20 });
  rows.value = data.list;
  if (hasPerm(auth, "ims:live:alarm:rule")) {
    const ruleData = await resourceGet<{ list: Record<string, unknown>[] }>("/live/alarm/rules");
    rules.value = ruleData.list || [];
  }
  stats.value = await resourceGet("/live/alarm/stats");
}

async function saveRule() {
  error.value = ruleError({
    ruleType: String(form.value.ruleType || ""),
    metric: String(form.value.metric || ""),
    operator: String(form.value.operator || ""),
    threshold: Number(form.value.threshold || 0),
    windowMinutes: form.value.windowMinutes == null ? null : Number(form.value.windowMinutes),
  });
  if (error.value) throw new Error(error.value);
  return resourceSend("POST", "/live/alarm/rule", form.value);
}

async function handle(action: string) {
  await resourceSend("PUT", `/live/alarm/record/${handleId.value}/handle`, { action, remark: remark.value });
  handleId.value = "";
  await load();
}

onMounted(load);
</script>

<template>
  <PageHeader title="风险告警" />
  <p v-if="stats.l3Banner">本人责任场次有未处理的严重告警</p>
  <AppTabs v-model:active="tab" :items="[{ key: 'records', label: '告警记录' }, { key: 'rules', label: '规则管理' }, { key: 'board', label: '统计看板' }]" />
  <DataTable v-if="tab === 'records'" :columns="columns" :data="rows" />
  <div v-if="handleId">
    <el-input v-model="remark" maxlength="512" placeholder="说明" />
    <button class="btn btn-sec" type="button" @click="handle('CONFIRMED')">已确认</button>
    <button class="btn btn-pri" type="button" @click="handle('HANDLED')">已处理</button>
    <button class="btn btn-sec" type="button" @click="handle('FALSE_ALARM')">误报</button>
  </div>
  <section v-if="tab === 'rules' && hasPerm(auth, 'ims:live:alarm:rule')">
    <button class="btn btn-pri" type="button" @click="drawer = true">新建规则</button>
    <p v-for="item in rules" :key="String(item.id)">{{ item.ruleName }} {{ item.levelLabel }} {{ item.status }}</p>
  </section>
  <section v-if="tab === 'board'">
    <ChartPanel type="pie" :data="(stats.byLevel as { name: string; value: number }[]) || []" />
    <ChartPanel type="line" :data="(stats.daily as { name: string; value: number }[]) || []" />
  </section>
  <FormDrawer v-model:open="drawer" title="告警规则" :model="form" :submit="saveRule" @saved="load">
    <p v-if="error">{{ error }}</p>
    <el-form-item label="规则名"><el-input v-model="form.ruleName" maxlength="64" /></el-form-item>
    <el-form-item label="类型"><el-input v-model="form.ruleType" /></el-form-item>
    <el-form-item label="指标"><el-input v-model="form.metric" /></el-form-item>
    <el-form-item label="操作符"><el-input v-model="form.operator" /></el-form-item>
    <el-form-item label="阈值"><el-input v-model="form.threshold" /></el-form-item>
    <el-form-item label="窗口"><el-input v-model="form.windowMinutes" /></el-form-item>
    <el-form-item label="级别"><el-input v-model="form.level" /></el-form-item>
  </FormDrawer>
</template>
