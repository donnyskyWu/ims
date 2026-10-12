<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import AppTabs from "@/components/AppTabs.vue";
import EmptyState from "@/components/EmptyState.vue";
import StatCard, { type StatItem } from "@/components/StatCard.vue";
import StatusTag from "@/components/StatusTag.vue";
import { useDictStore } from "@/stores/dict";
import { useInboxStore } from "@/stores/inbox";
import { toast } from "@/utils/toast";
import { closeTodo, goHandle, loadDashboard, loadMessages, loadTodoCount, loadTodos, readAllMessages, type DashboardData, type MessageRow, type TodoRow } from "./api";
import MessageDetail from "./MessageDetail.vue";
import { BIZ_CARDS, PLACEHOLDER_HINT, TODO_TABS, dateLine, identityLine, relativeTime, summaryLine, tabCount } from "./logic";

const router = useRouter();
const dict = useDictStore();
const inbox = useInboxStore();
const tab = ref("ALL");
const dash = ref<DashboardData | null>(null);
const todos = ref<TodoRow[]>([]);
const messages = ref<MessageRow[]>([]);
const counts = ref({ total: 0, byType: {} as Record<string, number> });
const dashError = ref(false);
const todoError = ref(false);
const messageError = ref(false);
const dashLoading = ref(true);
const todoLoading = ref(true);
const messageLoading = ref(true);
const current = ref<MessageRow | null>(null);
const detailOpen = ref(false);

const tabs = computed(() => TODO_TABS.map((item) => ({ key: item.key, label: item.label, count: tabCount(counts.value.byType, item.key, counts.value.total) })));
const who = computed(() => identityLine(dash.value?.displayName || "", dash.value?.deptName || "", dash.value?.roleSummary || ""));
const sub = computed(() => summaryLine(dateLine(), dash.value?.todoCount || 0, dash.value?.unreadMessageCount || 0));
const cards = computed<StatItem[]>(() => {
  const data = dash.value;
  if (!data) return [];
  return BIZ_CARDS.map((item) => {
    const warn = "warnField" in item ? Number(data[item.warnField] || 0) : 0;
    return {
      title: item.title,
      value: Number(data[item.field] || 0),
      desc: warn > 0 ? `即将到期 ${warn}` : "",
      onClick: () => {
        toast.info(PLACEHOLDER_HINT);
        void router.push(item.path);
      },
    };
  });
});

async function loadDash() {
  dashLoading.value = true;
  dashError.value = false;
  try {
    dash.value = await loadDashboard();
    inbox.setUnread(dash.value.unreadMessageCount);
  } catch {
    dashError.value = true;
  } finally {
    dashLoading.value = false;
  }
}

async function loadTodo() {
  todoLoading.value = true;
  todoError.value = false;
  try {
    const [page, counted] = await Promise.all([
      loadTodos({ type: tab.value === "ALL" ? "" : tab.value, status: "PENDING", pageNo: 1, pageSize: 10 }),
      loadTodoCount(),
    ]);
    todos.value = page.list || [];
    counts.value = { total: Number(counted.total || 0), byType: counted.byType || {} };
  } catch {
    todoError.value = true;
  } finally {
    todoLoading.value = false;
  }
}

async function loadMessage() {
  messageLoading.value = true;
  messageError.value = false;
  try {
    const page = await loadMessages({ pageNo: 1, pageSize: 10 });
    messages.value = page.list || [];
  } catch {
    messageError.value = true;
  } finally {
    messageLoading.value = false;
  }
}

function reload() {
  void loadDash();
  void loadTodo();
  void loadMessage();
}

async function handle(row: TodoRow) {
  const result = await goHandle(row.id, (path) => void router.push(path));
  if (result === "closed") reload();
}

async function close(row: TodoRow) {
  const ok = await closeTodo(row.id);
  if (ok) reload();
}

function moreTodos() {
  void router.push({ path: "/ims/workbench/todos", query: tab.value === "ALL" ? {} : { type: tab.value } });
}

function openMessage(row: MessageRow) {
  current.value = row;
  detailOpen.value = true;
}

function onRead(id: string) {
  const found = messages.value.find((item) => item.id === id);
  if (found && found.readStatus !== "READ") {
    found.readStatus = "READ";
    if (dash.value) dash.value.unreadMessageCount = Math.max(0, dash.value.unreadMessageCount - 1);
  }
}

async function readAll() {
  await readAllMessages();
  messages.value = messages.value.map((item) => ({ ...item, readStatus: "READ" }));
  if (dash.value) dash.value.unreadMessageCount = 0;
}

onMounted(() => {
  void dict.getDict("dict_todo_type");
  void dict.getDict("dict_todo_status");
  void dict.getDict("dict_msg_type");
  reload();
});
</script>

<template>
  <section>
    <div class="bar">
      <p class="crumb">个人工作台</p>
      <button class="btn btn-txt" type="button" @click="reload">刷新</button>
    </div>
    <el-skeleton v-if="dashLoading && !dash" :rows="3" animated />
    <EmptyState v-else-if="dashError" type="error" desc="加载失败，点击重试" @retry="loadDash" />
    <template v-else>
      <header class="hello">
        <h1>{{ dash?.greeting || "你好" }}，{{ dash?.displayName || "同事" }}</h1>
        <p>{{ who }}</p>
        <p class="sub">{{ sub }}</p>
      </header>
      <StatCard v-if="dash?.bizCardsVisible" :items="cards" />
    </template>
    <div class="split">
      <section class="card pane">
        <div class="pane-h">
          <h2>我的待办</h2>
          <button class="btn btn-txt" type="button" @click="moreTodos">查看更多</button>
        </div>
        <AppTabs v-model:active="tab" :items="tabs" @change="loadTodo" />
        <el-skeleton v-if="todoLoading && !todos.length && !todoError" :rows="4" animated />
        <EmptyState v-else-if="todoError" type="error" desc="加载失败，点击重试" @retry="loadTodo" />
        <EmptyState v-else-if="!todos.length" desc="暂无待办" />
        <button v-for="row in todos" :key="row.id" class="todo" :class="{ late: row.overdue }" type="button">
          <span class="main">
            <StatusTag dict-type="dict_todo_type" :value="row.type" />
            <strong>{{ row.title }}</strong>
            <small>{{ row.summary || "—" }}</small>
            <em>{{ row.sourceModuleLabel }} · {{ relativeTime(row.createTime) }}</em>
          </span>
          <span class="ops" @click.stop>
            <button class="btn btn-txt" type="button" @click="handle(row)">去处理</button>
            <button class="btn btn-txt" type="button" @click="close(row)">关闭</button>
          </span>
        </button>
      </section>
      <section class="card pane">
        <div class="pane-h">
          <h2>我的消息 <em v-if="(dash?.unreadMessageCount || 0) > 0" class="badge">{{ dash?.unreadMessageCount }}</em></h2>
          <button class="btn btn-txt" type="button" @click="readAll">全部已读</button>
          <button class="btn btn-txt" type="button" @click="router.push('/ims/workbench/messages')">查看更多</button>
        </div>
        <el-skeleton v-if="messageLoading && !messages.length && !messageError" :rows="4" animated />
        <EmptyState v-else-if="messageError" type="error" desc="加载失败，点击重试" @retry="loadMessage" />
        <EmptyState v-else-if="!messages.length" desc="暂无消息" />
        <button v-for="row in messages" :key="row.id" class="msg" type="button" @click="openMessage(row)">
          <i v-if="row.readStatus === 'UNREAD'" class="dot" />
          <span>
            <strong>{{ row.title }}</strong>
            <StatusTag dict-type="dict_msg_type" :value="row.msgType" />
            <small>{{ row.summary || "—" }}</small>
            <em>{{ relativeTime(row.createTime) }}</em>
          </span>
        </button>
      </section>
    </div>
    <MessageDetail v-model:open="detailOpen" :message="current" @read="onRead" />
  </section>
</template>

<style scoped>
.bar, .pane-h { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.crumb { margin: 0; color: var(--text2); font-size: 12px; }
.hello h1 { margin: 8px 0 4px; font-size: 28px; }
.hello p { margin: 0; color: var(--text2); }
.sub { margin-top: 4px; }
.split { display: grid; grid-template-columns: 3fr 2fr; gap: 16px; margin-top: 16px; }
.pane { padding: 16px; }
.pane h2 { margin: 0; font-size: 16px; }
.todo, .msg { width: 100%; display: flex; gap: 8px; text-align: left; border: none; background: transparent; padding: 10px 8px; border-bottom: 1px solid var(--line); cursor: pointer; }
.late { background: rgba(255, 59, 48, 0.08); }
.main, .msg span { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.main strong, .msg strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
small, em { color: var(--text2); font-size: 12px; font-style: normal; }
.ops { margin-left: auto; display: flex; align-items: center; }
.dot { width: 8px; height: 8px; margin-top: 6px; border-radius: 50%; background: var(--blue); flex: none; }
.badge { margin-left: 6px; background: var(--red); color: #fff; border-radius: 8px; padding: 0 6px; font-style: normal; font-size: 12px; }
</style>
