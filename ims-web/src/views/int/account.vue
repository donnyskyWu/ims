<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>内部账号</h1>
        <div class="sub">M1 账号分析 · 全部 / 高粉 / 低粉</div>
      </div>
      <div class="acts">
        <button class="btn btn-sec btn-sm" type="button" data-testid="int-account-export" @click="exportCsv">导出</button>
        <button class="btn btn-sec btn-sm" type="button" @click="go('/ims/collect/threshold')">阈值规则</button>
        <button class="btn btn-sec btn-sm" type="button" @click="go('/ims/corp/account/douyin')">平台账号</button>
        <button class="btn btn-sec btn-sm" type="button" @click="go('/ims/int/work')">内部作品</button>
      </div>
    </div>
    <p class="hint" style="margin-bottom: 8px" data-testid="int-account-hint">
      对照 M1 账号分析，并套用 M7 高粉、低粉规则。高粉为粉丝达到阈值（默认 ≥10 万）。低粉包含绝对阈值（默认粉丝 &lt;1000）和「7 日连降」。判定只读引用数据采集中的粉丝阈值。
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
      <select v-model="filters.ipGroupId" style="width: 140px" data-testid="int-account-ip-group">
        <option value="">全部 IP 组</option>
        <option v-for="group in ipGroups" :key="group.id" :value="group.id">{{ group.name }}</option>
      </select>
      <input v-model="filters.keyword" placeholder="账号名称" style="width: 140px" />
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">查询</button>
      <button class="btn btn-sec btn-sm" type="button" @click="resetFilters">重置</button>
    </form>
    <div class="g4" style="margin: 12px 0">
      <div class="card stat"><span class="l">当前 Tab 账号</span><div class="n">{{ total }}</div></div>
      <div class="card stat" data-testid="int-account-scope"><div class="n" style="font-size: 14px">{{ scopeText }}</div></div>
    </div>
    <div class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>账号名称</th>
              <th>平台</th>
              <th>IP 组</th>
              <th>粉丝数</th>
              <th>作品数</th>
              <th>标签</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="7"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!rows.length">
              <td colspan="7"><div class="empty" data-testid="int-account-empty"><div class="et">{{ error || '暂无内部账号' }}</div></div></td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.id">
              <td style="font-weight: 500">{{ row.accountName }}</td>
              <td>{{ platformLabel(row.platformType) }}</td>
              <td>{{ row.ipGroupName || '—' }}</td>
              <td class="num">{{ formatFans(row.followerCount) }}</td>
              <td class="num">{{ row.contentCount }}</td>
              <td>
                <span v-if="row.isHighFans" class="tag" style="background: rgba(255, 149, 0, 0.12); color: #c46a00">高粉</span>
                <span
                  v-else-if="row.isLowFans"
                  class="tag"
                  style="background: rgba(142, 142, 147, 0.12); color: #6d6d72"
                >低粉</span>
                <span v-else class="tag" style="background: rgba(52, 199, 89, 0.12); color: #1e8e3e">正常</span>
              </td>
              <td>
                <button class="btn-txt btn" type="button" data-testid="int-account-detail" @click="openDetail(row)">详情</button>
                <button class="btn-txt btn" type="button" data-testid="int-account-works" @click="goWorks(row)">作品</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    <p v-if="exportNote" class="hint" data-testid="int-account-export-note">{{ exportNote }}</p>
    <ProtoDrawer :open="detailOpen" title="账号详情" width="480px" @close="detailOpen = false">
      <div v-if="detail" data-testid="int-account-detail-body">
        <div class="kv">
          <div><div class="k">IP 组</div><div class="v">{{ detail.ipGroupName || '—' }}</div></div>
          <div><div class="k">粉丝</div><div class="v">{{ formatFans(detail.followerCount) }}</div></div>
          <div><div class="k">作品数</div><div class="v">{{ detail.contentCount }}</div></div>
          <div><div class="k">趋势</div><div class="v" data-testid="int-account-delta">{{ dailyLabel }}</div></div>
        </div>
        <button class="btn btn-sec btn-sm" type="button" data-testid="int-account-view-works" @click="goWorks(detail)">查看作品</button>
      </div>
    </ProtoDrawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { http, errorMessage } from '../../api/http'
import ProtoDrawer from '../../components/ProtoDrawer.vue'
import { showToast } from '../../components/form/toast'

const router = useRouter()
const tabs = [
  { value: 'ALL', label: '全部' },
  { value: 'HIGH_FANS', label: '高粉' },
  { value: 'LOW_FANS', label: '低粉' },
]
const segment = ref('ALL')
const rows = ref<
  {
    id: string
    accountName: string
    platformType: string
    ipGroupName: string
    followerCount: number
    contentCount: number
    isHighFans: boolean
    isLowFans: boolean
  }[]
>([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const exportNote = ref('')
const detailOpen = ref(false)
const detail = ref<(typeof rows.value)[number] | null>(null)
const filters = reactive({ platformType: '', ipGroupId: '', keyword: '' })
const ipGroups = ref<{ id: string; name: string }[]>([])
const scopeLabels: Record<string, string> = { ALL: '全部', HIGH_FANS: '高粉', LOW_FANS: '低粉' }
const platformLabels: Record<string, string> = {
  DOUYIN: '抖音',
  KUAISHOU: '快手',
  WECHAT_CHANNELS: '视频号',
  WECHAT_OFFICIAL: '公众号',
  XIAOHONGSHU: '小红书',
}
const scopeText = computed(() => `统计范围：${scopeLabels[segment.value] || '全部'}`)

function platformLabel(code: string) {
  return platformLabels[code] || '—'
}

const dailyLabel = computed(() => {
  const followers = detail.value?.followerCount || 0
  const prev = Math.round(followers * (0.7 + 0.3 * 5 / 6))
  const delta = Math.round(followers) - prev
  const sign = delta > 0 ? '+' : ''
  return `${sign}${delta}/日`
})

function go(path: string) {
  router.push(path)
}

function formatFans(n: number) {
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
    if (filters.ipGroupId) params.ipGroupId = Number(filters.ipGroupId)
    if (filters.keyword) params.keyword = filters.keyword
    const res = await http.get('/int-analysis/account/page', { params })
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
  filters.ipGroupId = ''
  filters.keyword = ''
  loadList()
}

function goWorks(row: { id: string }) {
  detailOpen.value = false
  router.push({ path: '/ims/int/work', query: { accountId: row.id } })
}

function openDetail(row: (typeof rows.value)[number]) {
  detail.value = row
  detailOpen.value = true
}

async function exportCsv() {
  exportNote.value = ''
  const token = localStorage.getItem('ims_access')
  const params = new URLSearchParams()
  params.set('segment', segment.value)
  if (filters.platformType) params.set('platformType', filters.platformType)
  if (filters.ipGroupId) params.set('ipGroupId', filters.ipGroupId)
  if (filters.keyword) params.set('keyword', filters.keyword)
  try {
    const res = await fetch(`/admin-api/ims/int-analysis/account/export?${params.toString()}`, {
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
    a.download = 'int_accounts.csv'
    a.click()
    URL.revokeObjectURL(a.href)
    exportNote.value = `已导出 ${count} 条`
    showToast(exportNote.value)
  } catch (e: unknown) {
    exportNote.value = errorMessage(e)
  }
}

async function loadIpGroups() {
  try {
    const res = await http.get('/ip-group/list', { params: { pageNo: 1, pageSize: 200 } })
    const list = (res.data?.data?.list || []) as { id: number | string; groupName: string }[]
    ipGroups.value = list.map((row) => ({ id: String(row.id), name: row.groupName }))
  } catch {
    ipGroups.value = []
  }
}

onMounted(() => {
  loadIpGroups()
  loadList()
})
</script>
