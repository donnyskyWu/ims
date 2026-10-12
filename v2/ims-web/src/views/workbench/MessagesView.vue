<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import AppPagination from "@/components/AppPagination.vue";
import AppTabs from "@/components/AppTabs.vue";
import EmptyState from "@/components/EmptyState.vue";
import PageHeader from "@/components/PageHeader.vue";
import QueryBar, { type QueryField } from "@/components/QueryBar.vue";
import StatusTag from "@/components/StatusTag.vue";
import { useDictStore } from "@/stores/dict";
import { loadMessages, readAllMessages, type MessageRow } from "./api";
import MessageDetail from "./MessageDetail.vue";
import { MESSAGE_TABS, messageEmpty, relativeTime } from "./logic";

const route = useRoute();
const router = useRouter();
const dict = useDictStore();
const tab = ref(String(route.query.readStatus || "ALL"));
const query = ref<Record<string, unknown>>({ keyword: String(route.query.keyword || "") });
const rows = ref<MessageRow[]>([]);
const total = ref(0);
const pageNo = ref(1);
const pageSize = ref(20);
const loading = ref(false);
const failed = ref(false);
const current = ref<MessageRow | null>(null);
const detailOpen = ref(false);
const fields: QueryField[] = [{ key: "keyword", label: "关键词", type: "input" }];
const filtered = computed(() => Boolean(String(query.value.keyword || "").trim()));
const emptyText = computed(() => messageEmpty(tab.value, String(query.value.keyword || "")));

async function load() {
  loading.value = true;
  failed.value = false;
  try {
    const page = await loadMessages({
      readStatus: tab.value,
      keyword: query.value.keyword,
      pageNo: pageNo.value,
      pageSize: pageSize.value,
    });
    rows.value = page.list || [];
    total.value = Number(page.total || 0);
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
  query.value = { keyword: "" };
  pageNo.value = 1;
  void load();
}

function openRow(row: MessageRow) {
  current.value = row;
  detailOpen.value = true;
}

function onRead(id: string) {
  const found = rows.value.find((item) => item.id === id);
  if (!found || found.readStatus === "READ") return;
  found.readStatus = "READ";
  if (tab.value === "UNREAD") {
    rows.value = rows.value.filter((item) => item.id !== id);
    total.value = Math.max(0, total.value - 1);
  }
}

async function readAll() {
  await readAllMessages();
  if (tab.value === "UNREAD") {
    rows.value = [];
    total.value = 0;
    return;
  }
  rows.value = rows.value.map((item) => ({ ...item, readStatus: "READ" }));
}

onMounted(() => {
  void dict.getDict("dict_msg_type");
  void load();
});
</script>

<template>
  <section>
    <p class="crumb">个人工作台 / 消息中心</p>
    <PageHeader title="消息中心" sub-title="只显示发给您的站内信" :show-scope="false">
      <template #actions>
        <button class="btn btn-sec btn-sm" type="button" @click="readAll">全部已读</button>
        <button class="btn btn-sec btn-sm" type="button" @click="router.push('/ims/workbench')">返回工作台</button>
      </template>
    </PageHeader>
    <AppTabs v-model:active="tab" :items="[...MESSAGE_TABS]" sync-query="readStatus" @change="search" />
    <QueryBar v-model="query" :fields="fields" @search="search" @reset="search" />
    <el-skeleton v-if="loading && !rows.length" :rows="5" animated />
    <EmptyState v-else-if="failed" type="error" desc="加载失败，点击重试" @retry="load" />
    <EmptyState v-else-if="!rows.length" :desc="emptyText">
      <template v-if="filtered || tab !== 'ALL'" #action>
        <button class="btn btn-txt" type="button" @click="resetAll">重置筛选</button>
      </template>
    </EmptyState>
    <button v-for="row in rows" :key="row.id" class="card msg" type="button" @click="openRow(row)">
      <i v-if="row.readStatus === 'UNREAD'" class="dot" />
      <span>
        <strong>{{ row.title }}</strong>
        <StatusTag dict-type="dict_msg_type" :value="row.msgType" />
        <small>{{ row.summary || "—" }}</small>
        <em>{{ row.sourceModuleLabel }} · {{ relativeTime(row.createTime) }}</em>
      </span>
    </button>
    <AppPagination v-model:page-no="pageNo" v-model:page-size="pageSize" :total="total" @change="load" />
    <MessageDetail v-model:open="detailOpen" :message="current" @read="onRead" />
  </section>
</template>

<style scoped>
.crumb { margin: 0 0 8px; color: var(--text2); font-size: 12px; }
.msg { width: 100%; display: flex; gap: 8px; text-align: left; border: none; margin-bottom: 8px; cursor: pointer; }
.msg span { display: flex; flex-direction: column; gap: 2px; }
small, em { color: var(--text2); font-size: 12px; font-style: normal; }
.dot { width: 8px; height: 8px; margin-top: 6px; border-radius: 50%; background: var(--blue); flex: none; }
</style>
