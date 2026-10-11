<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>竞品作品</h1>
        <div class="sub">Tab：全部/爆款/低分 · oa_external_work · 18a COMPA</div>
      </div>
      <div class="acts">
        <button class="btn btn-sec btn-sm" type="button" data-testid="comp-work-export" @click="exportCsv">导出</button>
        <button class="btn btn-sec btn-sm" type="button" @click="go('/ims/collect/threshold')">阈值规则</button>
        <button class="btn btn-sec btn-sm" type="button" @click="go('/ims/collect/external/account')">竞品账号配置</button>
      </div>
    </div>
    <p v-if="exportNote" class="hint" data-testid="comp-work-export-note">{{ exportNote }}</p>
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
    <form class="qbar" @submit.prevent="search">
      <select v-model="filters.platformType" style="width: 110px" data-testid="comp-work-platform">
        <option value="">全部平台</option>
        <option value="DOUYIN">抖音</option>
        <option value="WECHAT_OFFICIAL">公众号</option>
        <option value="WECHAT_CHANNELS">视频号</option>
        <option value="KUAISHOU">快手</option>
        <option value="XIAOHONGSHU">小红书</option>
      </select>
      <select v-model="filters.contentType" style="width: 120px" data-testid="comp-work-type">
        <option value="">作品类型</option>
        <option v-for="item in contentTypes" :key="item.value" :value="item.value">{{ item.label }}</option>
      </select>
      <span class="tag" data-testid="comp-work-threshold">爆款阈值 · {{ summary.hitThresholdLabel }}</span>
      <input v-model.number="filters.ipGroupId" type="number" placeholder="IP 组 id" style="width: 110px" />
      <input v-model="filters.accountIdentifier" placeholder="外部账号标识" style="width: 140px" />
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">查询</button>
      <button class="btn btn-sec btn-sm" type="button" @click="resetFilters">重置</button>
    </form>
    <div class="g4" style="margin: 12px 0">
      <div class="card stat"><span class="l">爆款总数</span><div class="n" data-testid="comp-work-hit">{{ summary.hitCount }}</div></div>
      <div class="card stat"><span class="l">总播放量</span><div class="n">{{ formatPlay(summary.totalPlay) }}</div></div>
      <div class="card stat"><span class="l">平均点赞</span><div class="n">{{ formatPlay(summary.avgLike) }}</div></div>
      <div class="card stat"><span class="l">平均分享</span><div class="n">{{ formatPlay(summary.avgShare) }}</div></div>
    </div>
    <div class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>排名</th>
              <th>作品标题</th>
              <th>类型</th>
              <th>平台</th>
              <th>播放量</th>
              <th>点赞</th>
              <th>爆款指数</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="8"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!rows.length">
              <td colspan="8"><div class="empty"><div class="et">{{ error || '暂无竞品作品' }}</div></div></td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.id">
              <td class="num">{{ row.rank }}</td>
              <td style="font-weight: 500">{{ row.title }}</td>
              <td>{{ row.contentTypeLabel || row.contentType || '—' }}</td>
              <td>{{ platformLabel(row.platformType) }}</td>
              <td class="num">{{ formatPlay(row.playCount) }}</td>
              <td class="num">{{ formatPlay(row.likeCount) }}</td>
              <td class="num">{{ row.hitIndex }}</td>
              <td>
                <button class="btn btn-sec btn-sm" type="button" data-testid="comp-work-detail" @click="openDetail(row)">详情</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="pager">
        <span class="pg-total">共 {{ total }} 条</span>
        <span class="pg-sp"></span>
        <button class="pg-n" type="button" :class="{ dis: pageNo <= 1 }" @click="changePage(pageNo - 1)">上一页</button>
        <span class="pg-n on">{{ pageNo }}</span>
        <button class="pg-n" type="button" :class="{ dis: pageNo * pageSize >= total }" @click="changePage(pageNo + 1)">下一页</button>
      </div>
    </div>

    <ProtoDrawer :open="!!active" title="作品详情" width="520px" @close="active = null">
      <div v-if="active" class="kv" data-testid="comp-work-drawer">
        <div><div class="k">账号</div><div class="v">{{ active.accountName }}</div></div>
        <div><div class="k">平台</div><div class="v">{{ platformLabel(active.platformType) }}</div></div>
        <div><div class="k">播放</div><div class="v">{{ formatPlay(active.playCount) }}</div></div>
        <div><div class="k">完播率</div><div class="v">{{ active.completionRate }}%</div></div>
      </div>
      <template #footer>
        <button class="btn btn-sec btn-sm" type="button" @click="active = null">关闭</button>
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
  { value: 'HIT', label: '爆款' },
  { value: 'LOW_SCORE', label: '低分' },
]
type WorkRow = {
  id: string
  rank: number
  title: string
  accountName: string
  platformType: string
  contentType: string
  contentTypeLabel: string
  playCount: number
  likeCount: number
  hitIndex: number
  completionRate: number
}
const segment = ref('ALL')
const rows = ref<WorkRow[]>([])
const total = ref(0)
const pageNo = ref(1)
const pageSize = 10
const loading = ref(false)
const error = ref('')
const exportNote = ref('')
const active = ref<WorkRow | null>(null)
const filters = reactive({ platformType: '', contentType: '', ipGroupId: null as number | null, accountIdentifier: '' })
const summary = reactive({ hitCount: 0, totalPlay: 0, avgLike: 0, avgShare: 0, hitThresholdLabel: '播放量 ≥ 100w' })
type ContentTypeOption = { value: string; label: string }
const fallbackContentTypes: ContentTypeOption[] = [
  { value: 'ARTICLE', label: '文章' },
  { value: 'SHORT_VIDEO', label: '短视频' },
  { value: 'VIDEO', label: '视频' },
]
const contentTypes = ref<ContentTypeOption[]>(fallbackContentTypes)

function go(path: string) {
  router.push(path)
}

function platformLabel(code: string) {
  return platforms[code] || code || '—'
}

function formatPlay(n: number) {
  if (n >= 10_000) return `${(n / 10_000).toFixed(1)}w`
  return String(n ?? 0)
}

function queryParams(page: number) {
  const params: Record<string, string | number> = {
    segment: segment.value,
    pageNo: page,
    pageSize,
  }
  if (filters.platformType) params.platformType = filters.platformType
  if (filters.contentType) params.contentType = filters.contentType
  if (filters.ipGroupId) params.ipGroupId = filters.ipGroupId
  if (filters.accountIdentifier) params.accountIdentifier = filters.accountIdentifier
  return params
}

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const res = await http.get('/comp-analysis/work/page', { params: queryParams(pageNo.value) })
    if (res.data.code !== 0) {
      error.value = res.data.msg || '加载失败'
      rows.value = []
      total.value = 0
      return
    }
    rows.value = res.data.data.list || []
    total.value = res.data.data.total || 0
    Object.assign(summary, res.data.data.summary || {})
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : '网络错误'
  } finally {
    loading.value = false
  }
}

function switchSegment(value: string) {
  segment.value = value
  pageNo.value = 1
  loadList()
}

function search() {
  pageNo.value = 1
  loadList()
}

function changePage(next: number) {
  if (next < 1 || (next - 1) * pageSize >= total.value) return
  pageNo.value = next
  loadList()
}

function openDetail(row: WorkRow) {
  active.value = row
}

async function exportCsv() {
  exportNote.value = ''
  const result = await downloadAdminCsv('/comp-analysis/work/export', queryParams(1), 'comp_works.csv')
  exportNote.value = result.message
}

function resetFilters() {
  filters.platformType = ''
  filters.contentType = ''
  filters.ipGroupId = null
  filters.accountIdentifier = ''
  pageNo.value = 1
  loadList()
}

async function loadContentTypes() {
  try {
    const res = await http.get('/system/dict-data/list', { params: { dictType: 'dict_content_type' } })
    const rows = ((res.data.data || []) as { status?: string; dictValue: string; dictLabel: string }[]).filter(
      (row) => row.status === 'ENABLED',
    )
    if (rows.length) {
      contentTypes.value = rows.map((row) => ({ value: row.dictValue, label: row.dictLabel }))
    }
  } catch {
    contentTypes.value = fallbackContentTypes
  }
}

onMounted(() => {
  loadContentTypes()
  loadList()
})
</script>
