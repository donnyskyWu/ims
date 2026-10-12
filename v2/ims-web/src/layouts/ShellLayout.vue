<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useAuthStore, type MenuNode } from "@/stores/auth";
import { routeAllowed } from "@/router/access";
import EmptyState from "@/components/EmptyState.vue";
import DownloadBar from "@/components/DownloadBar.vue";
import { call } from "@/api/generated/endpoints";

const auth = useAuthStore();
const route = useRoute();
const router = useRouter();
const collapsed = ref(localStorage.getItem("ims.sider.collapsed") === "1");
const unread = ref(0);
const openIds = ref<string[]>([]);

const allowed = computed(() => routeAllowed(route, auth.menus, auth.permCodes));

function toggle() {
  collapsed.value = !collapsed.value;
  localStorage.setItem("ims.sider.collapsed", collapsed.value ? "1" : "0");
}

function go(node: MenuNode) {
  if (node.path) void router.push(node.path);
}

async function logout() {
  await auth.logout();
  void router.push("/login");
}

async function poll() {
  if (!auth.loggedIn) return;
  try {
    const data = await call<{ count: number }>("message_unread_count_admin_api_ims_message_unread_count_get", { silent: true });
    unread.value = Number(data.count || 0);
  } catch {
    unread.value = 0;
  }
}

onMounted(() => {
  openIds.value = auth.menus.map((item) => item.id);
  void poll();
  window.setInterval(() => void poll(), 60_000);
});

function active(node: MenuNode): boolean {
  return Boolean(node.path && route.path === node.path);
}
</script>

<template>
  <div class="shell" :class="{ collapsed }">
    <aside class="sider">
      <button class="btn btn-txt fold" type="button" @click="toggle">{{ collapsed ? "展开" : "收起" }}</button>
      <p v-if="!auth.menus.length" class="hint">您的账号尚未分配权限，请联系管理员</p>
      <template v-for="group in auth.menus" :key="group.id">
        <div class="g">{{ group.name }}</div>
        <button
          v-for="item in group.children"
          :key="item.id"
          type="button"
          class="item"
          :class="{ on: active(item) || item.children.some((child) => active(child)) }"
          @click="item.children.length ? (openIds = openIds.includes(item.id) ? openIds.filter((id) => id !== item.id) : [...openIds, item.id]) : go(item)"
        >
          {{ collapsed ? item.name.slice(0, 1) : item.name }}
        </button>
        <button
          v-for="child in (openIds.includes(group.id) ? [] : group.children.flatMap((item) => item.children))"
          :key="child.id"
          type="button"
          class="sub"
          :class="{ on: active(child) }"
          @click="go(child)"
        >
          {{ child.name }}
        </button>
      </template>
    </aside>
    <div class="main">
      <header class="top">
        <span />
        <div class="tools">
          <button class="btn btn-txt" type="button">消息 {{ unread }}</button>
          <button class="btn btn-txt" type="button" @click="router.push('/demo/workbench')">待办</button>
          <details>
            <summary>{{ auth.user?.nickname || "账号" }}</summary>
            <button type="button" @click="router.push('/account/password')">个人中心</button>
            <button type="button" @click="logout">退出登录</button>
          </details>
        </div>
      </header>
      <div class="content">
        <EmptyState v-if="!allowed" type="noPermission" />
        <router-view v-else />
      </div>
    </div>
    <DownloadBar />
  </div>
</template>

<style scoped>
.shell { display: flex; min-height: 100%; background: var(--bg); }
.sider { width: var(--sider-w); background: var(--bg); padding: 12px 10px; flex: none; }
.collapsed .sider { width: var(--sider-collapsed); }
.g { font-size: 11px; font-weight: 600; color: var(--text2); padding: 10px 10px 4px; }
.item, .sub { width: 100%; text-align: left; border: none; background: transparent; cursor: pointer; border-radius: var(--r-s); }
.item { font-size: 13px; padding: 7px 10px; color: var(--text); }
.sub { font-size: 12.5px; padding: 6px 10px 6px 28px; color: var(--text2); }
.on { background: var(--blue-bg); color: var(--blue); }
.main { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.top { height: var(--header-h); display: flex; align-items: center; justify-content: flex-end; padding: 0 20px; background: var(--card); border-bottom: 1px solid var(--line); }
.tools { display: flex; align-items: center; gap: 8px; }
.content { padding: var(--content-y) var(--content-x); }
.hint { font-size: 12px; color: var(--text2); padding: 8px; }
summary { cursor: pointer; font-size: 13px; }
details button { display: block; width: 100%; text-align: left; border: none; background: var(--card); padding: 6px 8px; cursor: pointer; }
</style>
