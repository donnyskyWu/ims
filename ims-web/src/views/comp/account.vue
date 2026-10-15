<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>竞品账号</h1>
        <div class="sub">全部、高粉、低粉</div>
      </div>
      <div class="acts">
        <button class="btn btn-sec btn-sm" type="button" data-testid="comp-account-export" @click="exportCsv">导出</button>
        <button class="btn btn-sec btn-sm" type="button" @click="go('/ims/collect/threshold')">阈值规则</button>
        <button class="btn btn-sec btn-sm" type="button" @click="go('/ims/collect/external/account')">竞品账号配置</button>
      </div>
    </div>
    <p v-if="exportNote" class="hint" data-testid="comp-account-export-note">{{ exportNote }}</p>
    <p class="hint" style="margin-bottom: 8px">
      高粉默认粉丝 ≥10w · 低粉 &lt;1000 · 阈值只读引用 COLLECT FANS 规则。日净增、增长率暂无采集字段，显示为 —。
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
    <form class="qbar" @submit.prevent="search">
      <select v-model="filters.platformType" style="width: 120px" data-testid="comp-account-platform">
        <option value="">全部平台</option>
        <option value="DOUYIN">抖音</option>
        <option value="WECHAT_OFFICIAL">公众号</option>
        <option value="WECHAT_CHANNELS">视频号</option>
        <option value="KUAISHOU">快手</option>
        <option value="XIAOHONGSHU">小红书</option>
      </select>
      <input v-model.number="filters.ipGroupId" type="number" placeholder="IP 组 id" style="width: 110px" />
      <input v-model="filters.accountName" placeholder="账号名称" style="width: 140px" />
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">查询</button>
      <button class="btn btn-sec btn-sm" type="button" @click="resetFilters">重置</button>
    </form>
    <div class="g4" style="margin: 12px 0">
      <div class="card stat"><span class="l">当前 Tab 账号</span><div class="n">{{ total }}</div></div>
    </div>
    <div class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>排名</th>
              <th>账号名称</th>
              <th>平台</th>
              <th>粉丝数</th>
              <th>日净增</th>
              <th>增长率</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="7"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!rows.length">
              <td colspan="7"><div class="empty"><div class="et">{{ error || '暂无竞品账号' }}</div></div></td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.id">
              <td class="num">{{ row.rank }}</td>
              <td style="font-weight: 500">{{ row.accountName }}</td>
              <td>{{ platformLabel(row.platformType) }}</td>
              <td class="num">{{ formatFans(row.followerCount) }}</td>
              <td class="num">{{ dash(row.dailyNet) }}</td>
              <td class="num">{{ dash(row.growthRate) }}</td>
              <td>
                <button class="btn btn-sec btn-sm" type="button" data-testid="comp-account-detail" @click="openDetail(row)">详情</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <ProtoDrawer :open="!!active" title="账号详情" width="520px" @close="active = null">
      <div v-if="active" data-testid="comp-account-drawer">
        <div class="kv">
          <div><div class="k">粉丝</div><div class="v">{{ formatFans(active.followerCount) }}</div></div>
          <div><div class="k">作品数</div><div class="v">{{ active.workCount }}</div></div>
          <div><div class="k">最近同步</div><div class="v">{{ active.lastSyncedAt || '—' }}</div></div>
          <div><div class="k">平台</div><div class="v">{{ platformLabel(active.platformType) }}</div></div>
        </div>
        <div class="dsec">趋势</div>
        <p class="hint">示意（暂无日快照，日净增与增长率无法计算）</p>
      </div>
      <template #footer>
        <button class="btn btn-sec btn-sm" type="button" @click="active = null">关闭</button>
        <button class="btn btn-pri btn-sm" type="button" data-testid="comp-account-config" @click="go('/ims/collect/external/account')">
          采集配置
        </button>
      </template>
    </ProtoDrawer>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { http } from '../../api/http'
import ProtoDrawer from '../../components/ProtoDrawer.vue'
import { downloadAdminCsv } from '../../utils/downloadExport'

const router = useRouter()
const platforms: Record<string, string> = {
  DOUYIN: '抖音',
  KUAISHOU: '快手',
  WECHAT_OFFICIAL: '公众号',
  WECHAT_CHANNELS: '视频号',
  XIAOHONGSHU: '小红书',
}
const tabs = [
  { value: 'ALL', label: '全部' },
  { value: 'HIGH_FANS', label: '高粉' },
  { value: 'LOW_FANS', label: '低粉' },
]
type AccountRow = {
  id: string
  rank: number
  accountName: string
  platformType: string
  followerCount: number
  workCount: number
  lastSyncedAt: string
  dailyNet: number | null
  growthRate: number | null
}
const segment = ref('ALL')
const rows = ref<AccountRow[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const exportNote = ref('')
const active = ref<AccountRow | null>(null)
const filters = reactive({ platformType: '', ipGroupId: null as number | null, accountName: '' })

function go(path: string) {
  router.push(path)
}

function platformLabel(code: string) {
  return platforms[code] || code || '—'
}

function formatFans(n: number) {
  if (n >= 10_000) return `${(n / 10_000).toFixed(1)}w`
  return String(n ?? 0)
}

function dash(value: number | null) {
  return value == null ? '—' : String(value)
}

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const params: Record<string, string | number> = { segment: segment.value, pageNo: 1, pageSize: 20 }
    if (filters.platformType) params.platformType = filters.platformType
    if (filters.ipGroupId) params.ipGroupId = filters.ipGroupId
    if (filters.accountName) params.accountName = filters.accountName
    const res = await http.get('/comp-analysis/account/page', { params })
    if (res.data.code !== 0) {
      error.value = res.data.msg || '加载失败'
      rows.value = []
      total.value = 0
      return
    }
    rows.value = res.data.data.list || []
    total.value = res.data.data.total || 0
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : '网络错误'
  } finally {
    loading.value = false
  }
}

function switchSegment(value: string) {
  segment.value = value
  loadList()
}

function search() {
  loadList()
}

function openDetail(row: AccountRow) {
  active.value = row
}

async function exportCsv() {
  exportNote.value = ''
  const result = await downloadAdminCsv(
    '/comp-analysis/account/export',
    {
      segment: segment.value,
      platformType: filters.platformType,
      ipGroupId: filters.ipGroupId,
      accountName: filters.accountName,
    },
    'comp_accounts.csv',
  )
  exportNote.value = result.message
}

function resetFilters() {
  filters.platformType = ''
  filters.ipGroupId = null
  filters.accountName = ''
  loadList()
}

onMounted(loadList)
</script>
