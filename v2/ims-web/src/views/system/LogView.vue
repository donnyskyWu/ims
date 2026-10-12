<script setup lang="ts">
import { ref } from "vue";
import PageHeader from "@/components/PageHeader.vue";
import AppTabs from "@/components/AppTabs.vue";
import QueryBar, { type QueryField } from "@/components/QueryBar.vue";
import DataTable, { type TableColumn } from "@/components/DataTable.vue";
import AppPagination from "@/components/AppPagination.vue";
import DetailDrawer from "@/components/DetailDrawer.vue";
import DescriptionList from "@/components/DescriptionList.vue";
import Perm from "@/components/Perm.vue";
import ExportButton from "@/components/ExportButton.vue";
import { systemApi, type Row } from "@/api/system";

const tab = ref("operate");
const rows = ref<Row[]>([]);
const total = ref(0);
const pageNo = ref(1);
const pageSize = ref(10);
const loading = ref(false);
const query = ref<Row>({ operator: "", module: "", username: "", result: "" });
const detailOpen = ref(false);
const detail = ref<Row | null>(null);

const operateFields: QueryField[] = [
  { key: "operator", label: "操作人", type: "input" },
  { key: "module", label: "模块", type: "input" },
];
const loginFields: QueryField[] = [
  { key: "username", label: "用户名", type: "input" },
  { key: "result", label: "结果", type: "input" },
];

const operateColumns: TableColumn[] = [
  { key: "createTime", label: "时间", type: "time" },
  { key: "operatorName", label: "操作人" },
  { key: "module", label: "模块" },
  { key: "action", label: "操作" },
  { key: "resultText", label: "结果" },
  { key: "ip", label: "地址" },
  { key: "ops", label: "操作", type: "actions", actions: [{ label: "详情", onClick: (row) => void openDetail(row) }] },
];
const loginColumns: TableColumn[] = [
  { key: "createTime", label: "时间", type: "time" },
  { key: "username", label: "用户" },
  { key: "loginWay", label: "方式" },
  { key: "resultText", label: "结果" },
  { key: "ip", label: "地址" },
  { key: "device", label: "设备" },
];

async function load() {
  loading.value = true;
  try {
    const data = tab.value === "operate"
      ? await systemApi.operatePage({ ...query.value, pageNo: pageNo.value, pageSize: pageSize.value })
      : await systemApi.loginPage({ ...query.value, pageNo: pageNo.value, pageSize: pageSize.value });
    rows.value = data.list || [];
    total.value = Number(data.total || 0);
  } finally {
    loading.value = false;
  }
}

async function openDetail(row: Row) {
  detail.value = await systemApi.operateDetail(String(row.id));
  detailOpen.value = true;
}

function switchTab() {
  pageNo.value = 1;
  rows.value = [];
  void load();
}

void load();
</script>

<template>
  <section>
    <PageHeader title="日志" sub-title="列表不展示请求路径，详情中可见路径和参数摘要。导出默认最近 90 天。">
      <template #actions>
        <Perm code="ims:system:log:export">
          <ExportButton v-if="tab === 'operate'" :export-api="systemApi.operateExport" :params="query" />
          <ExportButton v-else :export-api="systemApi.loginExport" :params="query" />
        </Perm>
      </template>
    </PageHeader>
    <AppTabs v-model:active="tab" :items="[{ key: 'operate', label: '操作日志' }, { key: 'login', label: '登录日志' }]" @change="switchTab" />
    <QueryBar v-model="query" :fields="tab === 'operate' ? operateFields : loginFields" @search="pageNo = 1; load()" @reset="pageNo = 1; load()" />
    <DataTable :columns="tab === 'operate' ? operateColumns : loginColumns" :data="rows" :loading="loading" />
    <AppPagination v-model:page-no="pageNo" v-model:page-size="pageSize" :total="total" @change="load" />
    <DetailDrawer v-model:open="detailOpen" title="操作详情">
      <DescriptionList
        :items="[
          { label: '操作人', value: detail?.operatorName },
          { label: '模块', value: detail?.module },
          { label: '操作', value: detail?.action },
          { label: '结果', value: detail?.resultText },
          { label: '方法', value: detail?.method },
          { label: '路径', value: detail?.path },
          { label: '参数摘要', value: detail?.paramsDigest },
          { label: '地址', value: detail?.ip },
        ]"
      />
    </DetailDrawer>
  </section>
</template>
