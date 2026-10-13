<script setup lang="ts">
import { ref } from "vue";
import PageHeader from "@/components/PageHeader.vue";
import QueryBar, { type QueryField } from "@/components/QueryBar.vue";
import DataTable, { type TableColumn } from "@/components/DataTable.vue";
import ExportButton from "@/components/ExportButton.vue";
import FormDrawer from "@/components/FormDrawer.vue";
import StepsWizard from "@/components/StepsWizard.vue";
import AccountSelect from "@/components/AccountSelect.vue";
import { resourceGet, resourcePage, resourceSend } from "@/api/resource";
import { durationText } from "./logic";

const query = ref<Record<string, unknown>>({});
const rows = ref<Record<string, unknown>[]>([]);
const total = ref(0);
const drawer = ref(false);
const step = ref(0);
const form = ref<Record<string, unknown>>({});
const fields: QueryField[] = [
  { key: "sessionCode", label: "场次编号", type: "input" },
  { key: "platform", label: "平台", type: "dict", dictType: "dict_platform_type" },
  { key: "dateFrom", label: "开始日期", type: "date" },
  { key: "dateTo", label: "结束日期", type: "date" },
];
const columns: TableColumn[] = [
  { key: "sessionCode", label: "场次 ID", type: "mono" },
  { key: "date", label: "日期" },
  { key: "platformLabel", label: "平台" },
  { key: "accountName", label: "账号" },
  { key: "responsibleName", label: "责任人" },
  { key: "topic", label: "主题" },
  { key: "sessionStatusLabel", label: "状态" },
  { key: "riskLevelLabel", label: "风险" },
  { key: "durationText", label: "时长" },
  { key: "viewerCount", label: "观看数", type: "number" },
];

async function load() {
  const data = await resourcePage<Record<string, unknown>>("/live/ledger/list", { ...query.value, pageNo: 1, pageSize: 20 });
  rows.value = data.list.map((item) => ({ ...item, durationText: item.durationText || durationText(item.durationMinutes as number | null) }));
  total.value = data.total;
}

async function submit() {
  return resourceSend("POST", "/live/ledger/supplement", { register: form.value, report: form.value, supplementReason: form.value.supplementReason, costs: [] }, "live-supplement");
}

load();
</script>

<template>
  <PageHeader title="直播台账">
    <template #actions>
      <button v-perm="'ims:live:ledger:supplement'" class="btn btn-pri" type="button" @click="drawer = true">历史补录</button>
      <ExportButton v-perm="'ims:live:ledger:export'" :export-api="() => resourceGet('/live/ledger/export', query)" />
    </template>
  </PageHeader>
  <QueryBar v-model="query" :fields="fields" @search="load" />
  <DataTable :columns="columns" :data="rows" />
  <p>共 {{ total }} 场</p>
  <FormDrawer v-model:open="drawer" title="历史补录" size="L" :model="form" :submit="submit" @saved="load">
    <StepsWizard v-model:current="step" :steps="[{ key: 'data', title: '登记与下播' }, { key: 'reason', title: '补录说明' }]">
      <template #data>
        <AccountSelect v-model="form.accountId" />
        <el-input v-model="form.topic" maxlength="256" placeholder="主题" />
        <el-date-picker v-model="form.planStartTime" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" />
        <el-date-picker v-model="form.planEndTime" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" />
        <el-input v-model="form.gmv" placeholder="GMV" />
      </template>
      <template #reason>
        <el-input v-model="form.supplementReason" maxlength="256" placeholder="补录说明" />
      </template>
    </StepsWizard>
  </FormDrawer>
</template>
