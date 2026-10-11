<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>内部作品</h1>
        <div class="sub">Tab：全部/爆款/低分 · internal-content · 18b INT</div>
      </div>
      <div class="acts">
        <button class="btn btn-sec btn-sm" type="button" data-testid="int-work-export" @click="exportCsv">导出</button>
        <button class="btn btn-sec btn-sm" type="button" @click="go('/ims/collect/threshold')">阈值规则</button>
        <button class="btn btn-sec btn-sm" type="button" @click="go('/ims/corp/account/douyin')">平台账号</button>
      </div>
    </div>
    <p class="hint" style="margin-bottom: 8px">
      爆款默认播放 ≥100w · 低分完播 &lt;20% · 阈值只读引用 COLLECT WORK 规则。
    </p>
    <div class="cattabs">
      <button
        v-for="tab in tabs"
        :key="tab.value"
        type="button"
        class="cattab"
        :class="{ on: segment === tab.value }"
        @click="switchSegment(tab.value)"
      >
        {{ tab.label }}
      </button>
    </div>
    <form class="qbar" @submit.prevent="loadList">
      <select v-model="filters.platformType" style="width: 110px">
        <option value="">全部平台</option>
        <option value="DOUYIN">抖音</option>
        <option value="KUAISHOU">快手</option>
        <option value="WECHAT_CHANNELS">视频号</option>
      </select>
      <input v-model.number="filters.ipGroupId" type="number" placeholder="IP 组 id" style="width: 110px" />
      <input v-model="filters.keyword" placeholder="标题关键词" style="width: 140px" />
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">查询</button>
      <button class="btn btn-sec btn-sm" type="button" @click="resetFilters">重置</button>
    </form>
    <div class="g4" style="margin: 12px 0">
      <div class="card stat"><span class="l">当前 Tab 作品</span><div class="n">{{ total }}</div></div>
      <div class="card stat"><span class="l">segment</span><div class="n" style="font-size: 14px">{{ segment }}</div></div>
    </div>
    <div class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>作品</th>
              <th>内部账号</th>
              <th>平台</th>
              <th>播放</th>
              <th>完播率</th>
              <th>标签</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="7"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!rows.length">
              <td colspan="7"><div class="empty" data-testid="int-work-empty"><div class="et">{{ error || '暂无作品' }}</div></div></td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.id">
              <td style="font-weight: 500">{{ row.title }}</td>
              <td>{{ row.accountName }}</td>
              <td>{{ row.platformType }}</td>
              <td class="num">{{ formatPlay(row.playCount) }}</td>
              <td class="num">{{ row.completionRate }}%</td>
              <td>
                <span v-if="row.isHit" class="tag" style="background: rgba(255, 149, 0, 0.12); color: #c46a00">爆款</span>
                <span
                  v-else-if="row.isLowScore"
                  class="tag"
                  style="background: rgba(142, 142, 147, 0.12); color: #6d6d72"
                >低分</span>
                <span v-else class="tag" style="background: rgba(52, 199, 89, 0.12); color: #1e8e3e">正常</span>
              </td>
              <td>
                <button class="btn-txt btn" type="button" data-testid="int-work-detail" @click="openDetail(row)">详情</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    <p v-if="exportNote" class="hint" data-testid="int-work-export-note">{{ exportNote }}</p>
    <ProtoDrawer :open="detailOpen" title="作品详情" width="480px" @close="detailOpen = false">
      <div v-if="detail" class="kv" data-testid="int-work-detail-body">
        <div><div class="k">账号</div><div class="v">{{ detail.accountName || '—' }}</div></div>
        <div><div class="k">平台</div><div class="v">{{ detail.platformType }}</div></div>
        <div><div class="k">播放</div><div class="v">{{ formatPlay(detail.playCount) }}</div></div>
        <div><div class="k">完播率</div><div class="v">{{ detail.completionRate }}%</div></div>
      </div>
      <div class="dsec">近 7 日趋势</div>
      <p v-if="trendNote" class="hint">{{ trendNote }}</p>
      <table v-if="trend.length" data-testid="int-work-trend">
        <thead><tr><th>日期</th><th>播放</th></tr></thead>
        <tbody>
          <tr v-for="point in trend" :key="point.date">
            <td>{{ point.date }}</td>
            <td class="num">{{ point.value }}</td>
          </tr>
        </tbody>
      </table>
    </ProtoDrawer>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { http, errorMessage } from '../../api/http'
import ProtoDrawer from '../../components/ProtoDrawer.vue'
import { showToast } from '../../components/form/toast'

const router = useRouter()
const route = useRoute()
const tabs = [
  { value: 'ALL', label: '全部' },
  { value: 'HIT', label: '爆款' },
  { value: 'LOW_SCORE', label: '低分' },
]
const segment = ref('ALL')
const rows = ref<
  {
    id: string
    title: string
    accountId?: string
    accountName: string
    platformType: string
    playCount: number
    completionRate: number
    isHit: boolean
    isLowScore: boolean
  }[]
>([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const exportNote = ref('')
const detailOpen = ref(false)
const detail = ref<(typeof rows.value)[number] | null>(null)
const trend = ref<{ date: string; value: number }[]>([])
const trendNote = ref('')
const filters = reactive({
  platformType: '',
  ipGroupId: null as number | null,
  keyword: '',
  accountId: '' as string,
  accountName: '',
})

function go(path: string) {
  router.push(path)
}

function formatPlay(n: number) {
  if (n >= 10_000) return `${(n / 10_000).toFixed(1)}w`
  return String(n)
}

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const params: Record<string, string | number> = {
      segment: segment.value,
      pageNo: 1,
      pageSize: 20,
    }
    if (filters.platformType) params.platformType = filters.platformType
    if (filters.ipGroupId) params.ipGroupId = filters.ipGroupId
    if (filters.keyword) params.keyword = filters.keyword
    if (filters.accountId) params.accountId = filters.accountId
    if (filters.accountName) params.accountName = filters.accountName
    const res = await http.get('/int-analysis/work/page', { params })
    if (res.data.code !== 0) {
      error.value = res.data.msg || '加载失败'
      rows.value = []
      total.value = 0
      return
    }
    rows.value = res.data.data.list || []
    total.value = res.data.data.total || 0
  } catch (e: unknown) {
    error.value = errorMessage(e)
    rows.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function switchSegment(value: string) {
  segment.value = value
  loadList()
}

function resetFilters() {
  filters.platformType = ''
  filters.ipGroupId = null
  filters.keyword = ''
  filters.accountId = ''
  filters.accountName = ''
  loadList()
}

function listParams() {
  const params = new URLSearchParams()
  params.set('segment', segment.value)
  if (filters.platformType) params.set('platformType', filters.platformType)
  if (filters.ipGroupId) params.set('ipGroupId', String(filters.ipGroupId))
  if (filters.keyword) params.set('keyword', filters.keyword)
  if (filters.accountId) params.set('accountId', filters.accountId)
  if (filters.accountName) params.set('accountName', filters.accountName)
  return params
}

async function exportCsv() {
  exportNote.value = ''
  const token = localStorage.getItem('ims_access')
  const qs = listParams().toString()
  try {
    const res = await fetch(`/admin-api/ims/int-analysis/work/export?${qs}`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    const contentType = res.headers.get('content-type') || ''
    if (contentType.includes('application/json')) {
      const body = (await res.json()) as { msg?: string }
      exportNote.value = body.msg || '导出失败'
      return
    }
    const count = Number(res.headers.get('X-Export-Rows') || '0')
    const blob = await res.blob()
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = 'int_works.csv'
    a.click()
    URL.revokeObjectURL(a.href)
    exportNote.value = `已导出 ${count} 条`
    showToast(exportNote.value)
  } catch (e: unknown) {
    exportNote.value = errorMessage(e)
  }
}

async function openDetail(row: (typeof rows.value)[number]) {
  detail.value = row
  trend.value = []
  trendNote.value = ''
  detailOpen.value = true
  try {
    const res = await http.get(`/int-analysis/work/${row.id}/trend`)
    trend.value = res.data?.data?.points || []
    const delta = Number(res.data?.data?.dailyDelta || 0)
    const sign = delta > 0 ? '+' : ''
    trendNote.value = `${sign}${delta}/日`
  } catch (e: unknown) {
    trendNote.value = errorMessage(e)
  }
}

onMounted(() => {
  const accountId = route.query.accountId
  const accountName = route.query.accountName
  if (typeof accountId === 'string' && accountId) filters.accountId = accountId
  if (typeof accountName === 'string' && accountName) filters.accountName = accountName
  loadList()
})
</script>
