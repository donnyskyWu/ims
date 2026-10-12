<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useAuthStore, type MenuNode } from "@/stores/auth";
import { routeAllowed } from "@/router/access";
import EmptyState from "@/components/EmptyState.vue";
import DownloadBar from "@/components/DownloadBar.vue";
import MessageBell from "@/views/workbench/MessageBell.vue";
import AppIcon from "@/components/AppIcon.vue";
import { visibleNav } from "./nav";

const auth = useAuthStore();
const route = useRoute();
const router = useRouter();
const wide = ref(typeof window === "undefined" ? true : window.innerWidth >= 1024);
const drawer = ref(false);
const closedGroups = ref<Record<string, boolean>>({});
const closedSubs = ref<Record<string, boolean>>({});

const allowed = computed(() => routeAllowed(route, auth.menus, auth.permCodes));
const nav = computed(() => visibleNav(auth.menus, auth.permCodes));
const displayName = computed(() => auth.user?.nickname || auth.user?.username || "已登录");
const initial = computed(() => {
  const text = displayName.value.slice(0, 1);
  return /[a-z]/.test(text) ? text.toUpperCase() : text || "I";
});

function onResize() {
  wide.value = window.innerWidth >= 1024;
  if (wide.value) drawer.value = false;
}

function menuChildren(item: MenuNode) {
  return (item.children || []).filter((child) => child.type !== "BUTTON");
}

function active(node: MenuNode): boolean {
  return Boolean(node.path && route.path === node.path);
}

function childActive(item: MenuNode): boolean {
  return menuChildren(item).some((child) => active(child));
}

function navItems(group: MenuNode) {
  return (group.children || []).filter((item) => item.type !== "BUTTON");
}

function revealActive() {
  const groups = { ...closedGroups.value };
  const subs = { ...closedSubs.value };
  for (const group of nav.value) {
    for (const item of navItems(group)) {
      if (active(item) || childActive(item)) delete groups[group.id];
      if (childActive(item)) delete subs[item.id];
    }
  }
  closedGroups.value = groups;
  closedSubs.value = subs;
}

function toggleGroup(id: string) {
  closedGroups.value = { ...closedGroups.value, [id]: !closedGroups.value[id] };
}

function toggleSub(id: string) {
  closedSubs.value = { ...closedSubs.value, [id]: !closedSubs.value[id] };
}

function go(node: MenuNode) {
  drawer.value = false;
  if (node.path) void router.push(node.path);
}

async function logout() {
  await auth.logout();
  void router.push("/login");
}

watch(() => route.path, () => {
  drawer.value = false;
  revealActive();
});

onMounted(() => {
  onResize();
  window.addEventListener("resize", onResize);
  revealActive();
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", onResize);
});
</script>

<template>
  <div class="shell">
    <div v-if="!wide && drawer" class="nav-mask" @click="drawer = false" />
    <aside class="sider" :class="{ 'is-drawer': !wide, on: drawer }">
      <div class="logo">
        <b>IMS 一体化管理系统</b>
        <small>神鱼体育</small>
      </div>
      <nav class="nav">
        <div v-for="group in nav" :key="group.id" class="nav-g" :class="{ closed: closedGroups[group.id] }">
          <button class="nav-g-h" type="button" :aria-expanded="!closedGroups[group.id]" @click="toggleGroup(group.id)">
            <span>{{ group.name }}</span>
            <span class="caret"><AppIcon name="chev" :size="12" /></span>
          </button>
          <div class="nav-fold">
            <template v-for="item in navItems(group)" :key="item.id">
              <button
                v-if="!menuChildren(item).length"
                type="button"
                class="nav-item"
                :class="{ active: active(item) }"
                @click="go(item)"
              >
                <AppIcon :name="item.icon" />
                <span>{{ item.name }}</span>
              </button>
              <div v-else class="nav-sub-g" :class="{ closed: closedSubs[item.id] }">
                <button
                  type="button"
                  class="nav-item nav-parent"
                  :class="{ active: active(item) || childActive(item) }"
                  :aria-expanded="!closedSubs[item.id]"
                  @click="toggleSub(item.id)"
                >
                  <AppIcon :name="item.icon" />
                  <span>{{ item.name }}</span>
                  <span class="caret"><AppIcon name="chev" :size="12" /></span>
                </button>
                <button
                  v-for="child in menuChildren(item)"
                  :key="child.id"
                  type="button"
                  class="nav-item sub"
                  :class="{ active: active(child) }"
                  @click="go(child)"
                >
                  <AppIcon :name="child.icon" :size="14" />
                  <span>{{ child.name }}</span>
                </button>
              </div>
            </template>
          </div>
        </div>
      </nav>
      <div class="uCard">
        <span class="av">{{ initial }}</span>
        <div>
          <div class="un">{{ displayName }}</div>
          <div class="ur">{{ auth.user?.username || "已登录" }}</div>
        </div>
      </div>
    </aside>
    <div class="main">
      <header class="top">
        <button v-if="!wide" class="menu-btn" type="button" aria-label="打开菜单" @click="drawer = true">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round">
            <path d="M4 7h16M4 12h16M4 17h16" />
          </svg>
        </button>
        <span v-else />
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
.shell { display: flex; height: 100%; min-height: 0; overflow: hidden; background: var(--bg); }
.sider {
  width: var(--sider-w);
  flex: none;
  height: 100%;
  background: var(--bg);
  border-right: 1px solid var(--line);
  display: flex;
  flex-direction: column;
}
.sider.is-drawer {
  position: fixed;
  left: 0;
  top: 0;
  bottom: 0;
  z-index: 130;
  height: 100vh;
  transform: translateX(-105%);
  transition: transform 0.28s var(--spring);
  box-shadow: var(--sider-shadow);
}
.sider.is-drawer.on { transform: none; }
.nav-mask { position: fixed; inset: 0; background: var(--mask); z-index: 120; }
.logo { padding: 20px 18px 12px; }
.logo b { font-size: 16px; font-weight: 700; letter-spacing: -0.4px; display: block; line-height: 1.15; }
.logo small { display: block; font-size: 10px; color: var(--text2); font-weight: 500; letter-spacing: 1.5px; margin-top: 3px; }
.nav { flex: 1; min-height: 0; overflow-y: auto; padding: 4px 10px 10px; }
.nav-g-h {
  display: flex;
  align-items: center;
  width: 100%;
  padding: 12px 8px 4px;
  border: 0;
  background: transparent;
  font: inherit;
  font-size: 11px;
  font-weight: 600;
  color: var(--text2);
  letter-spacing: 0.6px;
  cursor: pointer;
  user-select: none;
}
.caret { display: inline-flex; margin-left: auto; color: var(--text2); transition: transform 0.2s ease; }
.nav-g.closed .caret { transform: rotate(-90deg); }
.nav-g.closed .nav-fold { display: none; }
.nav-item {
  display: flex;
  align-items: center;
  gap: 9px;
  width: 100%;
  margin: 1px 0;
  padding: 7px 10px;
  border: 0;
  border-radius: var(--r-s);
  background: transparent;
  color: var(--text);
  font: inherit;
  font-size: 13px;
  text-align: left;
  cursor: pointer;
  transition: background 0.15s;
}
.nav-item:hover { background: var(--nav-hover); }
.nav-item.active { background: var(--blue-bg); color: var(--blue); font-weight: 500; }
.nav-item.sub { padding: 7px 10px 7px 28px; font-size: 12.5px; color: var(--text); }
.nav-sub-g { margin: 2px 0 6px; }
.nav-parent { font-weight: 500; }
.nav-parent .caret { margin-left: 6px; flex: none; }
.nav-sub-g.closed .nav-item.sub { display: none; }
.nav-sub-g.closed .nav-parent .caret { transform: rotate(-90deg); }
.nav-item svg, .nav-g-h svg { flex: none; }
.uCard {
  margin: 10px;
  padding: 10px 12px;
  background: var(--card);
  border-radius: var(--r-s);
  box-shadow: var(--sh);
  display: flex;
  align-items: center;
  gap: 10px;
}
.av {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  color: var(--on-primary);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  background: var(--blue);
  flex: none;
}
.un { font-size: 12.5px; font-weight: 600; line-height: 1.3; }
.ur { font-size: 11px; color: var(--text2); }
.main { flex: 1; min-width: 0; min-height: 0; display: flex; flex-direction: column; }
.top {
  height: var(--header-h);
  flex: none;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  background: var(--card);
  border-bottom: 1px solid var(--line);
}
.menu-btn {
  display: inline-flex;
  padding: 7px;
  border: 0;
  border-radius: var(--r-s);
  background: transparent;
  color: var(--text2);
  cursor: pointer;
}
.menu-btn:hover { background: var(--bg); color: var(--text); }
.tools { display: flex; align-items: center; gap: 8px; }
.content { flex: 1; min-height: 0; overflow: auto; padding: var(--content-y) var(--content-x); max-width: var(--page-max); }
summary { cursor: pointer; font-size: 13px; }
details button { display: block; width: 100%; text-align: left; border: none; background: var(--card); padding: 6px 8px; cursor: pointer; }
</style>
