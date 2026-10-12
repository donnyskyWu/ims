<script setup lang="ts">
import { onMounted, onUnmounted, ref } from "vue";
import { useRouter } from "vue-router";
import EmptyState from "@/components/EmptyState.vue";
import { useInboxStore } from "@/stores/inbox";
import { loadMessages, readAllMessages, type MessageRow } from "./api";
import { relativeTime } from "./logic";
import MessageDetail from "./MessageDetail.vue";

const inbox = useInboxStore();
const router = useRouter();
const rows = ref<MessageRow[]>([]);
const loading = ref(false);
const failed = ref(false);
const current = ref<MessageRow | null>(null);
const detailOpen = ref(false);
let timer = 0;

async function load() {
  loading.value = true;
  failed.value = false;
  try {
    const data = await loadMessages({ pageNo: 1, pageSize: 20 });
    rows.value = data.list || [];
  } catch {
    failed.value = true;
  } finally {
    loading.value = false;
  }
}

function openDrawer() {
  inbox.show();
  void load();
}

function openRow(row: MessageRow) {
  current.value = row;
  detailOpen.value = true;
}

function onRead(id: string) {
  const found = rows.value.find((item) => item.id === id);
  if (found) found.readStatus = "READ";
}

async function readAll() {
  await readAllMessages();
  rows.value = rows.value.map((item) => ({ ...item, readStatus: "READ" }));
}

function viewAll() {
  inbox.open = false;
  void router.push("/ims/workbench/messages");
}

onMounted(() => {
  void inbox.refresh();
  timer = window.setInterval(() => void inbox.refresh(), 60_000);
});

onUnmounted(() => {
  window.clearInterval(timer);
});
</script>

<template>
  <button class="btn btn-txt bell" type="button" @click="openDrawer">
    消息
    <em v-if="inbox.unread > 0" class="badge">{{ inbox.unread }}</em>
  </button>
  <el-drawer :model-value="inbox.open" :size="420" title="消息" @update:model-value="inbox.open = $event">
    <div class="tools">
      <button class="btn btn-txt" type="button" @click="readAll">全部已读</button>
      <button class="btn btn-txt" type="button" @click="viewAll">查看全部</button>
    </div>
    <EmptyState v-if="failed" type="error" desc="加载失败，点击重试" @retry="load" />
    <EmptyState v-else-if="!loading && !rows.length" desc="暂无消息" />
    <button v-for="row in rows" :key="row.id" class="row" type="button" @click="openRow(row)">
      <i v-if="row.readStatus === 'UNREAD'" class="dot" />
      <span>
        <strong>{{ row.title }}</strong>
        <small>{{ row.summary }}</small>
        <em>{{ relativeTime(row.createTime) }}</em>
      </span>
    </button>
  </el-drawer>
  <MessageDetail v-model:open="detailOpen" :message="current" @read="onRead" />
</template>

<style scoped>
.badge { margin-left: 4px; background: var(--red); color: #fff; border-radius: 8px; padding: 0 5px; font-style: normal; font-size: 11px; }
.tools { display: flex; justify-content: flex-end; gap: 4px; }
.row { width: 100%; display: flex; gap: 8px; text-align: left; border: none; background: transparent; padding: 10px 0; border-bottom: 1px solid var(--line); cursor: pointer; }
.row strong, .row small, .row em { display: block; }
.row small, .row em { color: var(--text2); font-size: 12px; font-style: normal; }
.dot { width: 8px; height: 8px; margin-top: 6px; border-radius: 50%; background: var(--blue); flex: none; }
</style>
