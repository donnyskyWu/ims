<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>阈值规则</h1>
        <div class="sub">UX-M8 §5 · ALERT/MON 只读消费 · 16 COLLECT</div>
      </div>
      <div class="acts">
        <button class="btn btn-pri btn-sm" type="button" @click="openCreate">新增规则</button>
      </div>
    </div>
    <div class="tabs" style="margin-bottom: 12px">
      <button
        v-for="c in categories"
        :key="c.value"
        type="button"
        class="btn btn-sm"
        :class="activeCategory === c.value ? 'btn-pri' : 'btn-sec'"
        @click="switchCategory(c.value)"
      >
        {{ c.label }}
      </button>
    </div>
    <div class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>平台</th>
              <th>摘要</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!rows.length && !loading">
              <td colspan="5"><div class="empty"><div class="et">{{ error || '暂无阈值规则' }}</div></div></td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.id">
              <td class="mono">{{ row.id }}</td>
              <td>{{ row.platformType || '—' }}</td>
              <td style="font-size: 12px">{{ summaryOf(row) }}</td>
              <td>{{ row.status }}</td>
              <td>
                <button class="btn-txt btn" type="button" @click="remove(row)">删除</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    <div v-if="drawerOpen" class="drawer-mask" @click.self="drawerOpen = false">
      <div class="drawer">
        <h3>新增 · {{ activeCategory }}</h3>
        <div class="formrow">
          <label>平台</label>
          <select v-model="form.platformType">
            <option value="">全部</option>
            <option v-for="p in platforms" :key="p" :value="p">{{ p }}</option>
          </select>
        </div>
        <template v-if="activeCategory === 'ALERT'">
          <div class="formrow"><label>指标</label><input v-model="form.metricName" /></div>
          <div class="formrow"><label>阈值</label><input v-model="form.thresholdValue" /></div>
        </template>
        <template v-else-if="activeCategory === 'FANS'">
          <div class="formrow"><label>低粉</label><input v-model.number="form.lowFans" type="number" /></div>
          <div class="formrow"><label>高粉</label><input v-model.number="form.highFans" type="number" /></div>
        </template>
        <template v-else-if="activeCategory === 'WORK'">
          <div class="formrow"><label>爆款线</label><input v-model="form.hotValue" /></div>
          <div class="formrow"><label>低分线</label><input v-model="form.lowValue" /></div>
        </template>
        <div class="drawer-acts">
          <button class="btn btn-sec btn-sm" type="button" @click="drawerOpen = false">取消</button>
          <button class="btn btn-pri btn-sm" type="button" @click="save">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { http } from '../../api/http'

const categories = [
  { value: 'ALERT', label: '预警阈值' },
  { value: 'FANS', label: '粉丝阈值' },
  { value: 'WORK', label: '作品阈值' },
  { value: 'OVERRIDE', label: '账号覆盖' },
]
const platforms = ['DOUYIN', 'KUAISHOU', 'XIAOHONGSHU']
const activeCategory = ref('ALERT')
const rows = ref<Record<string, unknown>[]>([])
const loading = ref(false)
const error = ref('')
const drawerOpen = ref(false)
const form = reactive<Record<string, unknown>>({
  platformType: 'DOUYIN',
  metricName: '',
  thresholdValue: '',
  lowFans: 1000,
  highFans: 100000,
  hotValue: '10000',
  lowValue: '100',
  status: 'ENABLED',
})

function summaryOf(row: Record<string, unknown>) {
  if (activeCategory.value === 'ALERT') return `${row.metricName || ''} ${row.thresholdValue || ''}`.trim()
  if (activeCategory.value === 'FANS') return `低${row.lowFans} / 高${row.highFans}`
  if (activeCategory.value === 'WORK') return `爆${row.hotValue} / 低${row.lowValue}`
  return String(row.overrideValue || '—')
}

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const res = await http.get('/collect/threshold/list', {
      params: { thresholdCategory: activeCategory.value },
    })
    rows.value = res.data.data.list || []
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
    rows.value = []
  } finally {
    loading.value = false
  }
}

function switchCategory(cat: string) {
  activeCategory.value = cat
  loadList()
}

function openCreate() {
  drawerOpen.value = true
}

async function save() {
  await http.post('/collect/threshold', {
    thresholdCategory: activeCategory.value,
    ...form,
    status: 'ENABLED',
  })
  drawerOpen.value = false
  await loadList()
}

async function remove(row: Record<string, unknown>) {
  await http.delete(`/collect/threshold/${row.id}`)
  await loadList()
}

onMounted(loadList)
</script>
