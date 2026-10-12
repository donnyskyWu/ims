<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import AppTabs from "@/components/AppTabs.vue";
import EmptyState from "@/components/EmptyState.vue";
import ChartPanel from "@/components/ChartPanel.vue";
import StatCard from "@/components/StatCard.vue";
import PeriodPicker from "@/components/PeriodPicker.vue";
import FlowDesigner from "@/components/FlowDesigner.vue";
import DetailDrawer from "@/components/DetailDrawer.vue";
import DescriptionList from "@/components/DescriptionList.vue";
import Timeline from "@/components/Timeline.vue";
import Perm from "@/components/Perm.vue";
import { call } from "@/api/generated/endpoints";
import { useDictStore } from "@/stores/dict";
import { toast } from "@/utils/toast";
import { routeAllowed } from "@/router/access";
import { useAuthStore } from "@/stores/auth";
import { fmtTime } from "@/utils/format";

const router = useRouter();
const dict = useDictStore();
const auth = useAuthStore();
const section = ref("todo");
const todoTab = ref("APPROVAL");
const counts = ref<Record<string, number>>({});
const todos = ref<Record<string, unknown>[]>([]);
const messages = ref<Record<string, unknown>[]>([]);
const msgTab = ref("ALL");
const period = ref("2026-10");
const asOf = ref(fmtTime(new Date().toISOString()));
const chartFailed = ref(false);
const detail = ref(false);
const dirty = ref(false);
const selected = ref("");

const todoTypes = [
  { key: "APPROVAL", label: "审批" },
  { key: "RETURN", label: "归还" },
  { key: "REVIEW", label: "审核" },
  { key: "CONFIRM", label: "确认" },
  { key: "WARNING", label: "预警" },
  { key: "ALERT", label: "告警" },
];

async function loadTodos() {
  const count = await call<{ byType?: Record<string, number> }>("todo_my_count_admin_api_ims_todo_my_count_get", { silent: true });
  counts.value = count.byType || {};
  const page = await call<{ list: Record<string, unknown>[] }>("todo_my_page_admin_api_ims_todo_my_page_get", { silent: true });
  todos.value = page.list || [];
}

async function loadMessages() {
  const page = await call<{ list: Record<string, unknown>[] }>("message_my_page_admin_api_ims_message_my_page_get", {
    query: { readStatus: msgTab.value },
    silent: true,
  });
  messages.value = page.list || [];
}

async function openTodo(row: Record<string, unknown>) {
  const target = String(row.route || "/");
  const fake = { meta: { perm: String(row.permCode || "") }, path: target } as never;
  if (row.permCode && !routeAllowed(fake, auth.menus, auth.permCodes)) {
    toast.error("暂无权限");
    return;
  }
  await router.push(target);
}

function reloadBoard() {
  asOf.value = fmtTime(new Date().toISOString());
}

onMounted(() => {
  void dict.getDict("dict_todo_type");
  void loadTodos();
  void loadMessages();
  window.addEventListener("beforeunload", (event) => {
    if (!dirty.value) return;
    event.preventDefault();
    event.returnValue = "";
  });
});
</script>

<template>
  <section class="page">
    <div class="cattabs">
      <button class="pill" :class="{ on: section === 'todo' }" type="button" @click="section = 'todo'">工作台</button>
      <button class="pill" :class="{ on: section === 'board' }" type="button" @click="section = 'board'">看板</button>
      <button class="pill" :class="{ on: section === 'design' }" type="button" @click="section = 'design'">设计器</button>
    </div>
    <template v-if="section === 'todo'">
      <AppTabs v-model:active="todoTab" :items="todoTypes.map((item) => ({ ...item, count: counts[item.key] || 0 }))" />
      <ul>
        <li v-for="item in todos.filter((row) => !todoTab || row.type === todoTab)" :key="String(item.id)">
          <button type="button" @click="openTodo(item)">{{ item.title }}</button>
        </li>
      </ul>
      <AppTabs v-model:active="msgTab" type="pill" :items="[{ key: 'ALL', label: '全部' }, { key: 'UNREAD', label: '未读' }, { key: 'READ', label: '已读' }]" @change="loadMessages()" />
      <ul>
        <li v-for="item in messages" :key="String(item.id)">{{ item.title }}</li>
      </ul>
      <div class="links">
        <Perm code="ims:demo:order:query"><router-link to="/demo/list">列表示例</router-link></Perm>
      </div>
      <button class="btn btn-sec" type="button" @click="detail = true">查看详情</button>
    </template>
    <template v-else-if="section === 'board'">
      <PeriodPicker v-model="period" type="month" @update:model-value="reloadBoard" />
      <p class="muted">截至 {{ asOf }}</p>
      <StatCard :items="[{ title: '本月', value: 8 }, { title: '上月', value: 6 }, { title: '环比', value: 3, format: 'percent', ratio: 2 }, { title: '空', value: null }]" />
      <EmptyState v-if="chartFailed" type="error" @retry="chartFailed = false" />
      <ChartPanel v-else type="bar" :data="[{ name: '一组', value: 4 }, { name: '二组', value: 6 }]" />
      <button class="btn btn-txt" type="button" @click="chartFailed = true">模拟失败</button>
    </template>
    <template v-else>
      <div class="toolbar">
        <button class="btn btn-pri" type="button" @click="dirty = false">保存</button>
        <button class="btn btn-sec" type="button">预览</button>
        <button class="btn btn-sec" type="button" @click="router.push('/')">返回</button>
      </div>
      <input placeholder="标题" @input="dirty = true" />
      <FlowDesigner :nodes="[{ id: 'a', label: '开始', x: 40, y: 40 }]" :edges="[]" :selected="selected" @node-click="selected = $event; dirty = true" />
    </template>
    <DetailDrawer v-model:open="detail" title="示例详情" status-dict="dict_demo_status" status-value="ACTIVE" :tabs="[{ key: 'base', label: '基本信息' }, { key: 'rel', label: '关联' }, { key: 'log', label: '时间线' }]">
      <template #base><DescriptionList :items="[{ label: '名称', value: '示例' }]" /></template>
      <template #rel><p>暂无关联</p></template>
      <template #log><Timeline :items="[]" /></template>
      <template #footer>
        <Perm code="ims:demo:order:update"><button class="btn btn-pri" type="button">保存</button></Perm>
      </template>
    </DetailDrawer>
  </section>
</template>

<style scoped>
ul { padding-left: 18px; }
.toolbar { display: flex; gap: 8px; margin: 12px 0; }
input { height: 34px; border: 1px solid var(--line2); border-radius: var(--r-s); padding: 0 8px; }
</style>
