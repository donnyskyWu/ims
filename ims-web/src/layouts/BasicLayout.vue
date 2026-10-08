<template>
  <div class="app proto-root">
    <div v-if="!wide && drawer" class="nav-mask" @click="drawer = false" />
    <aside class="sidebar" :class="{ 'is-drawer': !wide, on: drawer }">
      <div class="logo">
        <b>IMS 一体化管理系统</b>
        <small>神鱼体育</small>
      </div>
      <nav class="nav">
        <div v-for="group in visibleGroups" :key="group.name" class="nav-g" :class="{ closed: !filtering && closedGroups[group.name] }">
          <div class="nav-g-h" @click="toggleGroup(group.name)">
            {{ group.name }}
            <span class="caret"><Ico name="chev" :size="12" /></span>
          </div>
          <template v-for="item in group.items" :key="item.key">
            <div
              v-if="item.kind === 'leaf'"
              class="nav-item"
              :class="{ active: item.id === currentId }"
              @click="go(item.id)"
            >
              <Ico :name="item.icon" />
              <span>{{ item.label }}</span>
              <span v-if="item.code" class="nc">{{ item.code }}</span>
            </div>
            <div v-else class="nav-sub-g" :class="{ closed: !filtering && closedSubs[item.id] }">
              <div class="nav-item nav-parent" :class="{ active: item.active }" @click="toggleSub(item.id)">
                <Ico :name="item.icon" />
                <span>{{ item.label }}</span>
                <span v-if="item.code" class="nc">{{ item.code }}</span>
                <span class="caret"><Ico name="chev" :size="12" /></span>
              </div>
              <div
                v-for="child in item.children"
                :key="child.id"
                class="nav-item sub"
                :class="{ active: child.id === currentId }"
                @click="go(child.id)"
              >
                <Ico :name="child.icon" :size="14" />
                <span>{{ child.label }}</span>
              </div>
            </div>
          </template>
        </div>
      </nav>
      <div class="uCard">
        <span class="av">{{ initial }}</span>
        <div>
          <div class="un">{{ displayName }}</div>
          <div class="ur">{{ user.profile?.username || '已登录' }}</div>
        </div>
      </div>
    </aside>
    <div class="main">
      <header class="topbar">
        <button v-if="!wide" class="tb-ic menu-btn" type="button" aria-label="打开菜单" @click="drawer = true">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round">
            <path d="M4 7h16M4 12h16M4 17h16" />
          </svg>
        </button>
        <div class="crumb"><b>{{ crumb.parent }}</b> / {{ crumb.page }}</div>
        <div class="search">
          <Ico name="search" :size="14" />
          <input v-model="query" placeholder="搜索菜单…" />
        </div>
        <div ref="roleBtn" class="rolebtn" @click="userMenu = !userMenu">
          <span class="av" style="background:#34c759">{{ initial }}</span>
          <span>{{ displayName }}</span>
          <Ico name="chev" :size="13" />
        </div>
        <div v-if="userMenu" ref="menuEl" class="rolemenu on">
          <div class="rm-h">账号</div>
          <div class="rm-i" @click="exit">
            <div class="rn">退出登录</div>
          </div>
        </div>
      </header>
      <main class="content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Ico from '../components/Ico.vue'
import { codeLabel, crumbOf, groups, isSub, modIdFromPath, mods, pathOf } from '../nav/menu'
import { useUserStore } from '../stores/user'

type Leaf = { kind: 'leaf'; key: string; id: string; label: string; icon: string; code: string }
type Child = { id: string; label: string; icon: string }
type Folder = { kind: 'folder'; key: string; id: string; label: string; icon: string; code: string; active: boolean; children: Child[] }

const user = useUserStore()
const route = useRoute()
const router = useRouter()
const wide = ref(window.innerWidth >= 1024)
const drawer = ref(false)
const query = ref('')
const userMenu = ref(false)
const roleBtn = ref<HTMLElement | null>(null)
const menuEl = ref<HTMLElement | null>(null)
const closedGroups = ref<Record<string, boolean>>({})
const closedSubs = ref<Record<string, boolean>>({})

const currentId = computed(() => modIdFromPath(route.path))
const crumb = computed(() => crumbOf(currentId.value))
const filtering = computed(() => query.value.trim().length > 0)
const displayName = computed(() => user.profile?.nickname || user.profile?.username || '已登录')
const initial = computed(() => (displayName.value || 'I').slice(0, 1).toUpperCase())

const visibleGroups = computed(() => {
  const keyword = query.value.trim().toLowerCase()
  const hit = (text: string) => !keyword || text.toLowerCase().includes(keyword)
  return groups
    .map(([name, items]) => {
      const visible: (Leaf | Folder)[] = []
      for (const item of items) {
        if (!isSub(item)) {
          const mod = mods[item]
          const label = mod?.name || item
          if (hit(label) || hit(name)) {
            visible.push({ kind: 'leaf', key: item, id: item, label, icon: mod?.icon || 'doc', code: codeLabel(mod) })
          }
          continue
        }
        const folder = mods[item.id]
        const children = item.children
          .filter((id) => hit(mods[id]?.name || id) || hit(item.label) || hit(name))
          .map((id) => ({ id, label: mods[id]?.name || id, icon: mods[id]?.icon || 'doc' }))
        if (children.length) {
          visible.push({
            kind: 'folder',
            key: item.id,
            id: item.id,
            label: item.label,
            icon: folder?.icon || 'doc',
            code: codeLabel(folder),
            active: item.children.includes(currentId.value),
            children,
          })
        }
      }
      return { name, items: visible }
    })
    .filter((group) => group.items.length)
})

function onResize() {
  wide.value = window.innerWidth >= 1024
  if (wide.value) drawer.value = false
}
function toggleGroup(name: string) {
  closedGroups.value = { ...closedGroups.value, [name]: !closedGroups.value[name] }
}
function toggleSub(id: string) {
  closedSubs.value = { ...closedSubs.value, [id]: !closedSubs.value[id] }
}
function go(id: string) {
  drawer.value = false
  userMenu.value = false
  router.push(pathOf(id))
}
function onDoc(event: MouseEvent) {
  const target = event.target as Node
  if (userMenu.value && menuEl.value && roleBtn.value && !menuEl.value.contains(target) && !roleBtn.value.contains(target)) {
    userMenu.value = false
  }
}
async function exit() {
  userMenu.value = false
  await user.logout()
  router.push('/login')
}
onMounted(() => {
  window.addEventListener('resize', onResize)
  document.addEventListener('click', onDoc)
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  document.removeEventListener('click', onDoc)
})
</script>
