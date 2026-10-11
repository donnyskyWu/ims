<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>作品监测</h1>
        <div class="sub">按 IP 主题或行业查看</div>
      </div>
      <div class="acts">
        <button class="btn btn-sec btn-sm" type="button" data-testid="mon-export" @click="exportCsv">导出</button>
      </div>
    </div>
    <p v-if="exportNote" class="hint" data-testid="mon-export-note">{{ exportNote }}</p>
    <p class="hint" style="margin-bottom: 8px">
      页内切换内部作品 / 竞品作品，仍按 IP 主题或行业聚合。内部作品按 IP 组名称归类。
    </p>
    <div class="cattabs" data-testid="mon-source-tabs">
      <button
        v-for="tab in sourceTabs"
        :key="tab.value"
        type="button"
        class="cattab"
        :class="{ on: source === tab.value }"
        :data-testid="'mon-source-' + tab.value"
        @click="switchSource(tab.value)"
      >
        {{ tab.label }}
      </button>
    </div>
    <div class="cattabs">
      <button
        v-for="tab in tabs"
        :key="tab.value"
        type="button"
        class="cattab"
        :class="{ on: dimension === tab.value }"
        @click="switchDimension(tab.value)"
      >
        {{ tab.label }}
      </button>
    </div>
    <form class="qbar" @submit.prevent="loadList">
      <input v-model="filters.keyword" :placeholder="dimension === 'IP_THEME' ? 'IP 主题' : '行业'" style="width: 150px" />
      <select v-model="filters.platformType" style="width: 108px">
        <option value="">全部平台</option>
        <option value="DOUYIN">抖音</option>
        <option value="WECHAT_OFFICIAL">公众号</option>
        <option value="WECHAT_CHANNELS">视频号</option>
        <option value="KUAISHOU">快手</option>
        <option value="XIAOHONGSHU">小红书</option>
      </select>
      <select v-model="filters.ipGroupId" style="width: 140px" data-testid="mon-ip-group">
        <option value="">全部 IP 组</option>
        <option v-for="group in ipGroups" :key="group.id" :value="String(group.id)">{{ group.label }}</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">查询</button>
      <button class="btn btn-sec btn-sm" type="button" @click="resetFilters">重置</button>
    </form>
    <div class="g4" style="margin: 12px 0">
      <div class="card stat"><span class="l">聚合行数</span><div class="n">{{ total }}</div></div>
      <div class="card stat"><span class="l">维度</span><div class="n" style="font-size: 14px">{{ dimensionLabel }}</div></div>
    </div>
    <div class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>{{ dimension === 'IP_THEME' ? 'IP 主题' : '行业' }}</th>
              <th data-testid="mon-account-col">{{ accountCountLabel }}</th>
              <th>作品数</th>
              <th>爆款数</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="5"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!rows.length">
              <td colspan="5"><div class="empty"><div class="et">{{ error || '暂无监测数据' }}</div></div></td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.dimensionKey">
              <td style="font-weight: 500">{{ row.dimensionLabel }}</td>
              <td class="num">{{ row.externalAccountCount }}</td>
              <td class="num">{{ row.workCount }}</td>
              <td class="num">{{ row.hitCount }}</td>
              <td>
                <button class="btn btn-sec btn-sm" type="button" data-testid="mon-detail" @click="active = row">详情</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    <ProtoDrawer :open="!!active" :title="active ? active.dimensionLabel : '监测详情'" width="520px" @close="active = null">
      <div v-if="active" class="kv" data-testid="mon-drawer">
        <div><div class="k">关联账号</div><div class="v">{{ active.relatedAccounts.join('、') || active.externalAccountCount }}</div></div>
        <div><div class="k">作品</div><div class="v">{{ active.workCount }}</div></div>
        <div><div class="k">爆款</div><div class="v">{{ active.hitCount }}</div></div>
      </div>
      <ul v-if="active?.relatedWorks.length" class="timeline">
        <li v-for="work in active.relatedWorks" :key="work.title">{{ work.title }}{{ work.isHit ? ' · 爆款' : '' }}</li>
      </ul>
      <template #footer>
        <button class="btn btn-sec btn-sm" type="button" @click="active = null">关闭</button>
        <button class="btn btn-pri btn-sm" type="button" data-testid="mon-go-account" @click="go(accountHref)">{{ accountActionLabel }}</button>
      </template>
    </ProtoDrawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { http } from '../../api/http'
import ProtoDrawer from '../../components/ProtoDrawer.vue'
import { downloadRowsCsv } from '../../utils/downloadExport'

const router = useRouter()
const sourceTabs = [
  { value: 'EXTERNAL', label: '竞品作品' },
  { value: 'INTERNAL', label: '内部作品' },
]
const tabs = [
  { value: 'IP_THEME', label: 'IP 主题' },
  { value: 'INDUSTRY', label: '行业' },
]
const source = ref('EXTERNAL')
const dimension = ref('IP_THEME')
type MonitorRow = {
  dimensionKey: string
  dimensionLabel: string
  externalAccountCount: number
  workCount: number
  hitCount: number
  relatedAccounts: string[]
  relatedWorks: { title: string; isHit: boolean }[]
}
const rows = ref<MonitorRow[]>([])
const active = ref<MonitorRow | null>(null)
const ipGroups = ref<{ id: number; label: string }[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const exportNote = ref('')
const filters = reactive({ platformType: '', ipGroupId: '', keyword: '' })

const dimensionLabel = computed(() => (dimension.value === 'IP_THEME' ? 'IP 主题' : '行业'))
const internalMode = computed(() => source.value === 'INTERNAL')
const accountCountLabel = computed(() => (internalMode.value ? '内部账号数' : '外部账号数'))
const accountActionLabel = computed(() => (internalMode.value ? '内部账号' : '竞品账号'))
const accountHref = computed(() => (internalMode.value ? '/ims/int/account' : '/ims/comp/account'))

function go(path: string) {
  router.push(path)
}

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const path = dimension.value === 'IP_THEME' ? '/monitor/ip-theme/page' : '/monitor/industry/page'
    const params: Record<string, string | number> = { pageNo: 1, pageSize: 20, source: source.value }
    if (filters.platformType) params.platformType = filters.platformType
    if (filters.ipGroupId) params.ipGroupId = Number(filters.ipGroupId)
    if (filters.keyword) params.keyword = filters.keyword
    const res = await http.get(path, { params })
    if (res.data.code !== 0) {
      error.value = res.data.msg || '加载失败'
      rows.value = []
      total.value = 0
      return
    }
    rows.value = (res.data.data.list || []).map((row: MonitorRow) => ({
      ...row,
      relatedAccounts: row.relatedAccounts || [],
      relatedWorks: row.relatedWorks || [],
    }))
    total.value = res.data.data.total || 0
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : '网络错误'
  } finally {
    loading.value = false
  }
}

function switchDimension(value: string) {
  dimension.value = value
  active.value = null
  loadList()
}

function switchSource(value: string) {
  source.value = value
  active.value = null
  loadList()
}

type IpNode = { id: number; groupName?: string; children?: IpNode[] }

function flattenGroups(nodes: IpNode[], depth = 0): { id: number; label: string }[] {
  const out: { id: number; label: string }[] = []
  for (const node of nodes) {
    out.push({ id: node.id, label: `${'　'.repeat(depth)}${node.groupName || `IP 组 ${node.id}`}` })
    if (node.children?.length) out.push(...flattenGroups(node.children, depth + 1))
  }
  return out
}

async function loadIpGroups() {
  try {
    const res = await http.get('/ip-group/accessible-tree')
    const data = res.data.data
    ipGroups.value = flattenGroups(Array.isArray(data) ? data : [])
  } catch {
    ipGroups.value = []
  }
}

async function exportCsv() {
  exportNote.value = ''
  const path = dimension.value === 'IP_THEME' ? '/monitor/ip-theme/page' : '/monitor/industry/page'
  const collected: typeof rows.value = []
  let page = 1
  let expected = 0
  try {
    while (page <= 50) {
      const params: Record<string, string | number> = { pageNo: page, pageSize: 100, source: source.value }
      if (filters.platformType) params.platformType = filters.platformType
      if (filters.ipGroupId) params.ipGroupId = Number(filters.ipGroupId)
      if (filters.keyword) params.keyword = filters.keyword
      const res = await http.get(path, { params })
      if (res.data.code !== 0) {
        exportNote.value = res.data.msg || '导出失败'
        return
      }
      const list = res.data.data.list || []
      expected = res.data.data.total || 0
      collected.push(...list)
      if (collected.length >= expected || !list.length) break
      page += 1
    }
    const count = downloadRowsCsv(
      'monitor.csv',
      ['维度', accountCountLabel.value, '作品数', '爆款数'],
      collected.map((row) => [row.dimensionLabel, row.externalAccountCount, row.workCount, row.hitCount]),
    )
    exportNote.value = `已导出 ${count} 条，与当前筛选 ${expected} 条一致`
  } catch (e: unknown) {
    exportNote.value = e instanceof Error ? e.message : '导出失败'
  }
}

function resetFilters() {
  filters.platformType = ''
  filters.ipGroupId = ''
  filters.keyword = ''
  loadList()
}

onMounted(() => {
  loadIpGroups()
  loadList()
})
</script>
