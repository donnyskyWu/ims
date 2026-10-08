<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>菜单</h1>
        <div class="sub">SYS-003 · GET /system/menu/tree · 权限码兼容 ops:*</div>
      </div>
    </div>
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
            <tr v-else-if="!rows.length">
              <td colspan="6"><div class="empty"><div class="et">{{ error || '没有菜单' }}</div></div></td>
            </tr>
            <tr v-for="row in rows" v-else :key="String(row.id)">
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
import { onMounted, ref } from 'vue'
import { readData } from '../../api/read'

type Node = { id: number; name: string; route?: string; permCode?: string; menuType?: string; visible?: number; children?: Node[]; depth?: number }

const rows = ref<Node[]>([])
const ready = ref(false)
const error = ref('')

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
