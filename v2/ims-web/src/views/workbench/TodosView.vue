<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import AppPagination from "@/components/AppPagination.vue";
import AppTabs from "@/components/AppTabs.vue";
import DataTable, { type TableColumn } from "@/components/DataTable.vue";
import PageHeader from "@/components/PageHeader.vue";
import QueryBar, { type QueryField } from "@/components/QueryBar.vue";
import StatusTag from "@/components/StatusTag.vue";
import { useDictStore } from "@/stores/dict";
import { toast } from "@/utils/toast";
import { closeTodo, goHandle, loadTodoCount, loadTodos, type TodoRow } from "./api";
import { TODO_TABS, tabCount, todoEmpty } from "./logic";

const route = useRoute();
const router = useRouter();
const dict = useDictStore();
const tab = ref(String(route.query.type || "ALL"));
const query = ref<Record<string, unknown>>({ keyword: String(route.query.keyword || ""), status: String(route.query.status || "") });
const rows = ref<TodoRow[]>([]);
const total = ref(0);
const pageNo = ref(1);
const pageSize = ref(20);
const loading = ref(false);
const failed = ref(false);
const counts = ref({ total: 0, byType: {} as Record<string, number> });
const viewing = ref<TodoRow | null>(null);

const fields: QueryField[] = [
  { key: "keyword", label: "关键词", type: "input" },
  {
    key: "status",
    label: "状态",
    type: "select",
    options: [
      { label: "待处理", value: "PENDING" },
      { label: "已处理", value: "DONE" },
      { label: "已作废", value: "CANCELLED" },
      { label: "已过期", value: "OVERDUE" },
    ],
  },
];
const tabs = computed(() => TODO_TABS.map((item) => ({ key: item.key, label: item.label, count: tabCount(counts.value.byType, item.key, counts.value.total) })));
const filtered = computed(() => tab.value !== "ALL" || Boolean(String(query.value.keyword || "").trim()) || Boolean(query.value.status));
const columns: TableColumn[] = [
  { key: "type", label: "类型", type: "status", dictType: "dict_todo_type", width: 110 },
  { key: "title", label: "标题" },
  { key: "deadlineText", label: "截止时间", width: 220 },
  { key: "status", label: "状态", type: "status", dictType: "dict_todo_status", width: 110 },
  {
    key: "ops",
    label: "操作",
    type: "actions",
    width: 180,
    actions: [
      { label: "去处理", show: (row) => row.status === "PENDING", onClick: (row) => void handle(row as unknown as TodoRow) },
      { label: "关闭", show: (row) => row.status === "PENDING", onClick: (row) => void close(row as unknown as TodoRow) },
      { label: "查看", show: (row) => row.status !== "PENDING", onClick: (row) => view(row as unknown as TodoRow) },
    ],
  },
];

async function load() {
  loading.value = true;
  failed.value = false;
  try {
    const [page, counted] = await Promise.all([
      loadTodos({
        type: tab.value === "ALL" ? "" : tab.value,
        status: query.value.status,
        keyword: query.value.keyword,
        pageNo: pageNo.value,
        pageSize: pageSize.value,
      }),
      loadTodoCount(),
    ]);
    rows.value = page.list || [];
    total.value = Number(page.total || 0);
    counts.value = { total: Number(counted.total || 0), byType: counted.byType || {} };
  } catch {
    failed.value = true;
  } finally {
    loading.value = false;
  }
}

function search() {
  pageNo.value = 1;
  void load();
}

function resetAll() {
  tab.value = "ALL";
  query.value = { keyword: "", status: "" };
  pageNo.value = 1;
  void router.replace({ query: {} });
  void load();
}

async function handle(row: TodoRow) {
  const result = await goHandle(row.id, (path) => void router.push(path));
  if (result === "closed") void load();
}

async function close(row: TodoRow) {
  const ok = await closeTodo(row.id);
  if (ok) void load();
}

function view(row: TodoRow) {
  if (row.route) {
    viewing.value = row;
    return;
  }
  toast.info(`${row.title}${row.summary ? ` ${row.summary}` : ""}`);
}

onMounted(() => {
  void dict.getDict("dict_todo_type");
  void dict.getDict("dict_todo_status");
  void load();
});
</script>

<template>
  <section>
    <p class="crumb">个人工作台 / 待办中心</p>
    <PageHeader title="待办中心" sub-title="只显示指派给您的待办" :show-scope="false">
      <template #actions>
        <button class="btn btn-sec btn-sm" type="button" @click="router.push('/ims/workbench')">返回工作台</button>
      </template>
    </PageHeader>
    <AppTabs v-model:active="tab" :items="tabs" sync-query="type" @change="search" />
    <QueryBar v-model="query" :fields="fields" @search="search" @reset="search" />
    <DataTable :columns="columns" :data="rows as unknown as Record<string, unknown>[]" :loading="loading" :empty-type="failed ? 'error' : 'empty'" :empty-text="failed ? '加载失败，点击重试' : todoEmpty(filtered)" @retry="load">
      <template #cell-title="{ row }">
        <el-tooltip :content="String(row.title || '')" placement="top">
          <span class="ellipsis">{{ row.title }}</span>
        </el-tooltip>
      </template>
      <template #cell-deadlineText="{ row }">
        <span :class="{ late: row.overdue }">{{ row.deadlineText || "—" }}</span>
      </template>
    </DataTable>
    <button v-if="!loading && total === 0 && filtered" class="btn btn-txt" type="button" @click="resetAll">重置筛选</button>
    <AppPagination v-model:page-no="pageNo" v-model:page-size="pageSize" :total="total" @change="load" />
    <el-drawer :model-value="Boolean(viewing)" size="520px" title="待办说明" @update:model-value="viewing = $event ? viewing : null">
      <template v-if="viewing">
        <StatusTag dict-type="dict_todo_status" :value="viewing.status" />
        <h2>{{ viewing.title }}</h2>
        <p>{{ viewing.summary || "—" }}</p>
        <p class="meta">{{ viewing.sourceModuleLabel }} · {{ viewing.deadlineText || "无截止时间" }}</p>
      </template>
      <template #footer>
        <button v-if="viewing?.route" class="btn btn-sec btn-sm" type="button" @click="router.push(viewing.route)">查看说明</button>
        <button class="btn btn-pri btn-sm" type="button" @click="viewing = null">关闭</button>
      </template>
    </el-drawer>
  </section>
</template>

<style scoped>
.crumb { margin: 0 0 8px; color: var(--text2); font-size: 12px; }
.ellipsis { display: inline-block; max-width: 360px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; vertical-align: bottom; }
.late { color: var(--red); }
.meta { color: var(--text2); }
</style>
