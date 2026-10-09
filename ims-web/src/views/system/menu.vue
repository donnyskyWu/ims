<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>菜单</h1>
        <div class="sub">SYS-003 · GET /system/menu/tree · 权限码兼容 ops:*</div>
      </div>
    </div>
    <form class="qbar" data-testid="menu-filters" style="margin-bottom: 10px" @submit.prevent>
      <input v-model="keyword" data-testid="menu-filter-keyword" placeholder="名称 / 路由 / 权限码" style="width: 220px" />
      <button class="btn btn-sec btn-sm" type="button" data-testid="menu-filter-reset" @click="keyword = ''">重置</button>
    </form>
    <p v-if="keyword.trim()" class="hint" data-testid="menu-filter-summary">正在按「{{ keyword.trim() }}」筛选权限菜单。</p>
    <p v-if="error" class="hint bad">{{ error }}</p>
    <div class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>菜单 ID</th>
              <th>名称</th>
              <th>路由</th>
              <th>权限码</th>
              <th>类型</th>
              <th>可见</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!ready">
              <td colspan="6"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!visible.length">
              <td colspan="6">
                <div class="empty" data-testid="menu-list-empty">
                  <div class="et">{{ error || (keyword.trim() ? '没有匹配的权限菜单' : '没有菜单') }}</div>
                  <div v-if="keyword.trim()" class="es">换一个名称、路由或权限码。</div>
                </div>
              </td>
            </tr>
            <tr v-for="row in visible" v-else :key="String(row.id)" data-testid="menu-row">
              <td class="mono">{{ row.id }}</td>
              <td :style="{ paddingLeft: `${12 + Number(row.depth || 0) * 16}px` }">{{ row.name }}</td>
              <td class="mono">{{ row.route || '—' }}</td>
              <td class="mono">{{ row.permCode || '—' }}</td>
              <td>{{ row.menuType }}</td>
              <td>{{ row.visible ? '可见' : '隐藏' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { readData } from '../../api/read'

type Node = { id: number; name: string; route?: string; permCode?: string; menuType?: string; visible?: number; children?: Node[]; depth?: number }

const rows = ref<Node[]>([])
const ready = ref(false)
const error = ref('')
const keyword = ref('')

const visible = computed(() => {
  const query = keyword.value.trim().toLowerCase()
  if (!query) return rows.value
  return rows.value.filter((row) => `${row.name || ''} ${row.route || ''} ${row.permCode || ''}`.toLowerCase().includes(query))
})

function flatten(nodes: Node[], depth = 0): Node[] {
  const out: Node[] = []
  for (const node of nodes) {
    out.push({ ...node, depth })
    out.push(...flatten(node.children || [], depth + 1))
  }
  return out
}

onMounted(async () => {
  const res = await readData('/system/menu/tree')
  ready.value = true
  error.value = res.error
  rows.value = flatten((res.data as Node[]) || [])
})
</script>
