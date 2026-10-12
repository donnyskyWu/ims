<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useAuthStore, type MenuNode } from "@/stores/auth";
import { routeAllowed } from "@/router/access";
import EmptyState from "@/components/EmptyState.vue";
import DownloadBar from "@/components/DownloadBar.vue";
import MessageBell from "@/views/workbench/MessageBell.vue";

const auth = useAuthStore();
const route = useRoute();
const router = useRouter();
const collapsed = ref(localStorage.getItem("ims.sider.collapsed") === "1");
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

function menuChildren(item: MenuNode) {
  return (item.children || []).filter((child) => child.type !== "BUTTON");
}

onMounted(() => {
  const ids = auth.menus.map((item) => item.id);
  for (const group of auth.menus) {
    for (const item of group.children || []) {
      if (!item.path && menuChildren(item).length) ids.push(item.id);
    }
  }
  openIds.value = ids;
});

function active(node: MenuNode): boolean {
  return Boolean(node.path && route.path === node.path);
}

function navItems(group: MenuNode) {
  return (group.children || []).filter((item) => item.type !== "BUTTON");
}

function toggleGroup(item: MenuNode) {
  openIds.value = openIds.value.includes(item.id) ? openIds.value.filter((id) => id !== item.id) : [...openIds.value, item.id];
}
</script>

<template>
  <div class="shell" :class="{ collapsed }">
    <aside class="sider">
      <button class="btn btn-txt fold" type="button" @click="toggle">{{ collapsed ? "展开" : "收起" }}</button>
      <template v-for="group in auth.menus" :key="group.id">
        <div class="g">{{ group.name }}</div>
        <template v-for="item in navItems(group)" :key="item.id">
          <button
            type="button"
            class="item"
            :class="{ on: active(item) || menuChildren(item).some((child) => active(child)) }"
            @click="item.path ? go(item) : toggleGroup(item)"
          >
            {{ collapsed ? item.name.slice(0, 1) : item.name }}
          </button>
          <button
            v-for="child in openIds.includes(item.id) ? menuChildren(item) : []"
            :key="child.id"
            type="button"
            class="sub"
            :class="{ on: active(child) }"
            @click="go(child)"
          >
            {{ child.name }}
          </button>
        </template>
      </template>
    </aside>
    <div class="main">
      <header class="top">
        <span />
        <div class="tools">
          <MessageBell />
          <button class="btn btn-txt" type="button" @click="router.push('/ims/workbench/todos')">待办</button>
          <details>
            <summary>{{ auth.user?.nickname || "账号" }}</summary>
            <button type="button" @click="router.push('/ims/profile')">个人中心</button>
            <button type="button" @click="router.push('/password-reset')">修改密码</button>
            <button type="button" @click="logout">退出登录</button>
          </details>
        </div>
      </header>
      <div class="content">
        <EmptyState v-if="!auth.menus.length" desc="您的账号尚未分配权限，请联系管理员" />
        <EmptyState v-else-if="!allowed" type="noPermission" />
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
.content { padding: var(--content-y) var(--content-x); max-width: var(--page-max); }
.hint { font-size: 12px; color: var(--text2); padding: 8px; }
summary { cursor: pointer; font-size: 13px; }
details button { display: block; width: 100%; text-align: left; border: none; background: var(--card); padding: 6px 8px; cursor: pointer; }
</style>
