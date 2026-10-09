<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>大屏配置</h1>
        <div class="sub">bi0Screen 隐藏路由 · reportType=DASHBOARD · 只读首片</div>
      </div>
      <div class="acts">
        <router-link class="btn btn-sec btn-sm" to="/ims/bi/report/list">报表管理</router-link>
        <router-link class="btn btn-sec btn-sm" data-testid="bi-screen-dc-dashboard" to="/ims/dc/dashboard">全链路看板</router-link>
        <button class="btn btn-pri btn-sm" type="button" disabled>新建大屏</button>
      </div>
    </div>
    <p class="hint" style="margin-bottom: 8px">
      PRD v2.6.27 侧栏归一化到 <code>biList</code>；本页供深链 <code>go('bi0Screen')</code> 兼容 · API
      <code>/admin-api/ims/bi/screen/*</code>（只读）。
    </p>
    <form class="qbar" @submit.prevent="loadList">
      <input v-model="filters.keyword" data-testid="bi-screen-keyword" placeholder="名称/编号" style="width: 140px" />
      <select v-model="filters.status" style="width: 110px">
        <option value="">全部状态</option>
        <option value="PUBLISHED">已发布</option>
        <option value="DRAFT">草稿</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit" data-testid="bi-screen-search">查询</button>
      <button class="btn btn-sec btn-sm" type="button" @click="resetFilters">重置</button>
    </form>

    <div class="g2r" style="margin-top: 12px; align-items: start">
      <div class="tbl-block">
        <div class="tbl-wrap">
          <table>
            <thead>
              <tr>
                <th>编号</th>
                <th>名称</th>
                <th>状态</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="loading">
                <td colspan="4"><div class="empty"><div class="et">加载中</div></div></td>
              </tr>
              <tr v-else-if="!rows.length">
                <td colspan="4">
                  <div class="empty" data-testid="bi-screen-empty"><div class="et">{{ emptyText }}</div></div>
                </td>
              </tr>
              <tr
                v-for="row in rows"
                v-else
                :key="row.id"
                :style="selectedId === row.id ? 'background: var(--blue-bg)' : ''"
              >
                <td class="mono">{{ row.reportNo }}</td>
                <td>{{ row.reportName }}</td>
                <td>{{ row.status }}</td>
                <td>
                  <button class="btn btn-sec btn-sm" type="button" @click="selectRow(row.id)">配置预览</button>
                  <router-link class="btn btn-sec btn-sm" :to="`/ims/bi/screen/${row.id}/view`">全屏展示</router-link>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <div v-if="detail" class="card screen-panel">
        <div class="rowline" style="justify-content: space-between; margin-bottom: 10px">
          <b>{{ detail.reportName }}</b>
          <span class="tag tag-info">{{ detail.theme === 'dark' ? '暗色主题' : '浅色' }}</span>
        </div>
        <div v-if="!detail.widgets?.length" class="empty" data-testid="bi-screen-widget-empty">
          <div class="et">{{ detail.emptyReason || '暂无组件' }}</div>
        </div>
        <div v-else class="screen-widgets">
          <div v-for="(w, i) in detail.widgets" :key="i" class="widget" :class="w.type">
            <div class="k">{{ w.title }}</div>
            <div v-if="w.type === 'KPI'" class="v">{{ w.value }}<small>{{ w.unit }}</small></div>
            <div v-else-if="w.type === 'CHART'" class="chart-ph">图表占位 · {{ w.chartType }}</div>
            <ul v-else-if="w.type === 'LIST'" class="list-ph">
              <li v-for="(line, j) in w.rows || []" :key="j">{{ line }}</li>
            </ul>
            <div v-else class="v">—</div>
          </div>
        </div>
      </div>
      <div v-else class="card screen-panel empty"><div class="et">选择左侧大屏查看 Widget 配置</div></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { http } from '../../api/http'

type Row = { id: number; reportNo: string; reportName: string; status: string }
type Detail = { reportName: string; theme: string; widgets: Record<string, unknown>[]; emptyReason?: string }

const rows = ref<Row[]>([])
const detail = ref<Detail | null>(null)
const selectedId = ref<number | null>(null)
const loading = ref(false)
const error = ref('')
const filters = ref({ keyword: '', status: '' })
const listFiltered = ref(false)
const emptyText = computed(() => error.value || (listFiltered.value ? '当前筛选下暂无大屏' : '暂无大屏'))

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const params: Record<string, string | number> = { pageNo: 1, pageSize: 20 }
    if (filters.value.keyword) params.keyword = filters.value.keyword
    if (filters.value.status) params.status = filters.value.status
    const res = await http.get('/bi/screen/list', { params })
    if (res.data.code !== 0) {
      error.value = res.data.msg || '加载失败'
      rows.value = []
      return
    }
    rows.value = res.data.data.list || []
    listFiltered.value = Boolean(filters.value.keyword.trim() || filters.value.status)
    if (!rows.value.some((row) => row.id === selectedId.value)) {
      selectedId.value = null
      detail.value = null
    }
    if (rows.value.length && !selectedId.value) selectRow(rows.value[0].id)
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : '网络错误'
  } finally {
    loading.value = false
  }
}

async function selectRow(id: number) {
  selectedId.value = id
  detail.value = null
  try {
    const res = await http.get(`/bi/screen/${id}`)
    if (res.data.code === 0) detail.value = res.data.data
  } catch {
    /* ignore */
  }
}

function resetFilters() {
  filters.value = { keyword: '', status: '' }
  loadList()
}

onMounted(loadList)
</script>

<style scoped>
.screen-panel {
  padding: 16px;
  min-height: 280px;
  background: #1c1c1e;
  color: #f5f5f7;
}
.screen-panel :deep(.et) {
  color: #f5f5f7;
}
.screen-widgets {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}
.widget {
  background: rgba(255, 255, 255, 0.06);
  border-radius: 8px;
  padding: 12px;
}
.widget .k {
  font-size: 11px;
  opacity: 0.7;
  margin-bottom: 6px;
}
.widget .v {
  font-size: 20px;
  font-weight: 600;
}
.widget small {
  font-size: 12px;
  margin-left: 4px;
  opacity: 0.8;
}
.chart-ph,
.list-ph {
  font-size: 12px;
  opacity: 0.85;
}
.list-ph {
  margin: 0;
  padding-left: 16px;
}
</style>
