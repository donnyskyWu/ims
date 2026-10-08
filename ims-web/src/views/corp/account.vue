<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>{{ meta.title }}</h1>
        <div class="sub">{{ meta.sub }}</div>
      </div>
      <div class="acts">
        <button class="btn btn-pri" type="button" @click="openCreate">登记账号</button>
      </div>
    </div>
    <p class="hint" style="margin-bottom: 8px">
      UX-M4 P-M4-008 · <code>platformType={{ meta.platform }}</code> · 采集 Tab 见 ADR-047 ·
      <b>≠</b> 数据采集·竞品账号配置。
    </p>
    <form class="qbar" @submit.prevent="search">
      <input v-model="keyword" placeholder="账号编号/昵称" style="width: 130px" />
      <input v-model="ipGroupKeyword" placeholder="IP 组" style="width: 100px" />
      <select v-model="status" style="width: 100px">
        <option value="">全部状态</option>
        <option v-for="item in statusOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">查询</button>
      <button class="btn btn-sec btn-sm" type="button" @click="reset">重置</button>
    </form>
    <div class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>账号编号</th>
              <th>昵称</th>
              <th>责任人</th>
              <th>实名人</th>
              <th>状态</th>
              <th>采集</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="7" style="white-space: normal">
                <div class="empty"><div class="et">加载中</div></div>
              </td>
            </tr>
            <tr v-else-if="!rows.length">
              <td colspan="7" style="white-space: normal">
                <div class="empty">
                  <div class="et">{{ error || '暂无该平台账号' }}</div>
                  <div class="es">请先在资源管理完成主数据，再通过登记账号创建。</div>
                </div>
              </td>
            </tr>
            <tr v-for="row in rows" v-else :key="String(row.id)">
              <td class="mono num" style="color: var(--blue); cursor: pointer" @click="openDetail(row)">{{ row.accountNo }}</td>
              <td style="font-weight: 500">{{ row.nickname }}</td>
              <td>{{ row.holderUserName || '—' }}</td>
              <td>{{ row.realNameMasked || '—' }}</td>
              <td>{{ row.status }}</td>
              <td>{{ row.collectBindSummary }}</td>
              <td><button class="btn btn-sec btn-sm" type="button" @click="openDetail(row)">详情</button></td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="pager">
        <span class="pg-total">共 {{ total }} 条</span>
        <select class="pg-size" :value="pageSize" @change="changeSize">
          <option :value="10">10</option>
          <option :value="20">20</option>
          <option :value="50">50</option>
        </select>
        <span>条/页</span>
        <span class="pg-sp"></span>
        <span class="pg-n" :class="{ dis: pageNo <= 1 }" @click="goto(pageNo - 1)">‹</span>
        <span v-for="n in pageList" :key="n" class="pg-n" :class="{ on: n === pageNo }" @click="goto(n)">{{ n }}</span>
        <span class="pg-n" :class="{ dis: pageNo >= pageCount }" @click="goto(pageNo + 1)">›</span>
      </div>
    </div>
    <p class="hint">GET /corp/account/page?platformType={{ meta.platform }} → OPS platform list · 领用流程入口 BLOCKED（见 PRD Q3）。</p>

    <ProtoDrawer :open="detailOpen" :title="`${meta.title} · 详情`" width="640px" @close="detailOpen = false">
      <div v-if="detail" class="tabs">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          class="btn btn-sm"
          :class="activeTab === tab.id ? 'btn-pri' : 'btn-sec'"
          type="button"
          @click="activeTab = tab.id"
        >
          {{ tab.label }}
        </button>
      </div>
      <div v-if="detail && activeTab === 'basic'" class="formrow one">
        <div v-for="item in basicLines" :key="item.label" class="fld">
          <label>{{ item.label }}</label>
          <div>{{ item.value }}</div>
        </div>
      </div>
      <div v-if="detail && activeTab === 'collect'" class="formrow one">
        <p class="hint">凭证保存后须「导入 Collector」完成 bind，否则采集任务会报未绑定。</p>
        <div class="fld">
          <label>绑定状态</label>
          <div>{{ collectSummary }}</div>
        </div>
        <div v-if="bindInfo" class="fld">
          <label>Collector account_id</label>
          <div class="mono">{{ bindInfo.collectorAccountId || '—' }}</div>
        </div>
        <div v-if="bindInfo" class="fld">
          <label>最近探活</label>
          <div>{{ bindInfo.lastProbeAt || '—' }} {{ bindInfo.connStatus === 'SUCCESS' ? '成功' : bindInfo.connStatus === 'FAILED' ? '失败' : '' }}</div>
        </div>
        <div class="fld">
          <label>凭证</label>
          <div>{{ detail.hasCookie ? '已配置（脱敏）' : '未配置' }}</div>
        </div>
        <p class="hint">本 Tab 为 ADR-047 平台账号采集配置，不是 COLLECT 竞品账号配置。</p>
        <div class="acts" style="margin-top: 12px">
          <button class="btn btn-sec btn-sm" type="button" :disabled="!detail.hasCookie" @click="importCollector">导入 Collector</button>
          <button class="btn btn-sec btn-sm" type="button" @click="testConnection">测试连接</button>
        </div>
        <p v-if="collectMsg" class="hint">{{ collectMsg }}</p>
      </div>
      <div v-if="detail && activeTab === 'timeline'" class="hint">领用时间线契约为 GET /account/timeline/{accountId}，本片未接 ACCT 流程，暂为空。</div>
      <div v-if="detail && activeTab === 'asset'" class="hint">关联资产需 ASSET 反向穿透接口，契约未在本片实现。</div>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="detailOpen = false">关闭</button>
      </template>
    </ProtoDrawer>

    <ProtoDrawer :open="formOpen" title="登记平台账号" width="480px" @close="formOpen = false">
      <div class="formrow one"><div class="fld"><label>昵称<i class="req">*</i></label><input v-model="form.accountName" /></div></div>
      <div class="formrow one"><div class="fld"><label>公司 ID<i class="req">*</i></label><input v-model.number="form.companyId" placeholder="选择器：填已有公司 id" /></div></div>
      <div class="formrow one"><div class="fld"><label>IP 组 ID<i class="req">*</i></label><input v-model.number="form.ipGroupId" placeholder="选择器：填已有 IP 组 id" /></div></div>
      <div class="formrow one"><div class="fld"><label>实名人 ID</label><input v-model.number="form.realnameId" placeholder="可选" /></div></div>
      <div class="formrow one"><div class="fld"><label>责任人 ID<i class="req">*</i></label><input v-model.number="form.holderUserId" placeholder="ims_sys_user.id" /></div></div>
      <div class="formrow one"><div class="fld"><label>状态</label><select v-model="form.status"><option v-for="item in statusOptions" :key="item.value" :value="item.value">{{ item.label }}</option></select></div></div>
      <p class="hint">强关联须通过选择器；手输非法 id 时后端返回 1500/1501/1504。</p>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="formOpen = false">取消</button>
        <button class="btn btn-pri" type="button" @click="submitCreate">保存</button>
      </template>
    </ProtoDrawer>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { http } from '../../api/http'
import ProtoDrawer from '../../components/ProtoDrawer.vue'

const route = useRoute()

const PLATFORM_MAP: Record<string, { title: string; platform: string; sub: string }> = {
  'wechat-official': { title: '公众号', platform: 'WECHAT_OFFICIAL', sub: 'P-M4-008 · WECHAT_OFFICIAL · 08 CORP-A' },
  'wechat-channels': { title: '视频号', platform: 'WECHAT_CHANNELS', sub: 'P-M4-008 · WECHAT_CHANNELS + 采集 Tab · 08 CORP-A' },
  douyin: { title: '抖音', platform: 'DOUYIN', sub: 'P-M4-008 · DOUYIN + ADR-047 采集 Tab · 08 CORP-A' },
  kuaishou: { title: '快手', platform: 'KUAISHOU', sub: 'P-M4-008 · KUAISHOU · 08 CORP-A' },
  xiaohongshu: { title: '小红书', platform: 'XIAOHONGSHU', sub: 'P-M4-008 · XIAOHONGSHU · 08 CORP-A' },
}

const meta = computed(() => {
  const slug = String(route.params.platform || 'douyin')
  return PLATFORM_MAP[slug] || PLATFORM_MAP.douyin
})

const statusOptions = [
  { value: 'IN_USE', label: '在用' },
  { value: 'IN_POOL', label: '池可领用' },
  { value: 'FROZEN', label: '冻结' },
  { value: 'RETURNED', label: '已归还' },
]

const tabs = [
  { id: 'basic', label: '基本信息' },
  { id: 'collect', label: '采集' },
  { id: 'timeline', label: '领用时间线' },
  { id: 'asset', label: '关联资产' },
]

const rows = ref<Record<string, unknown>[]>([])
const total = ref(0)
const pageNo = ref(1)
const pageSize = ref(10)
const loading = ref(false)
const error = ref('')
const keyword = ref('')
const ipGroupKeyword = ref('')
const status = ref('')

const detailOpen = ref(false)
const detail = ref<Record<string, unknown> | null>(null)
const bindInfo = ref<Record<string, unknown> | null>(null)
const activeTab = ref('basic')
const collectMsg = ref('')
const collectSummary = ref('—')

const formOpen = ref(false)
const form = reactive({
  accountName: '',
  companyId: undefined as number | undefined,
  ipGroupId: undefined as number | undefined,
  realnameId: undefined as number | undefined,
  holderUserId: 1,
  status: 'IN_USE',
})

const pageCount = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))
const pageList = computed(() => {
  const count = pageCount.value
  const current = pageNo.value
  const start = Math.max(1, current - 2)
  const end = Math.min(count, start + 4)
  return Array.from({ length: end - start + 1 }, (_, i) => start + i)
})

const basicLines = computed(() => {
  if (!detail.value) return []
  const d = detail.value
  return [
    { label: '账号编号', value: d.accountNo },
    { label: '昵称', value: d.nickname },
    { label: '平台', value: d.platformType },
    { label: 'IP 组', value: d.ipGroupName || d.ipGroupId },
    { label: '公司', value: d.companyName || d.companyId },
    { label: '实名人', value: d.realNameMasked || '—' },
    { label: '责任人', value: d.holderUserName || d.holderUserId },
    { label: '状态', value: d.status },
    { label: '采集摘要', value: d.collectBindSummary },
  ]
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await http.get('/corp/account/page', {
      params: {
        pageNo: pageNo.value,
        pageSize: pageSize.value,
        platformType: meta.value.platform,
        keyword: keyword.value || undefined,
        status: status.value || undefined,
      },
    })
    const data = res.data?.data as { list: Record<string, unknown>[]; total: number }
    let list = data?.list || []
    if (ipGroupKeyword.value.trim()) {
      const key = ipGroupKeyword.value.trim()
      list = list.filter((row) => String(row.ipGroupName || '').includes(key))
    }
    rows.value = list
    total.value = data?.total || 0
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : '加载失败'
    rows.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function search() {
  pageNo.value = 1
  load()
}

function reset() {
  keyword.value = ''
  ipGroupKeyword.value = ''
  status.value = ''
  search()
}

function goto(n: number) {
  if (n < 1 || n > pageCount.value) return
  pageNo.value = n
  load()
}

function changeSize(ev: Event) {
  pageSize.value = Number((ev.target as HTMLSelectElement).value)
  pageNo.value = 1
  load()
}

async function openDetail(row: Record<string, unknown>, tab = 'basic') {
  activeTab.value = tab
  collectMsg.value = ''
  const res = await http.get(`/corp/account/${row.id}`)
  const data = res.data?.data as Record<string, unknown>
  detail.value = data
  collectSummary.value = String(data.collectBindSummary || '—')
  try {
    const bindRes = await http.get(`/corp/account/${row.id}/collector-bind`)
    bindInfo.value = bindRes.data?.data as Record<string, unknown>
  } catch {
    bindInfo.value = null
  }
  detailOpen.value = true
}

async function importCollector() {
  if (!detail.value) return
  collectMsg.value = ''
  try {
    const bindRes = await http.post(`/corp/account/${detail.value.id}/collector-bind`, {})
    bindInfo.value = bindRes.data?.data as Record<string, unknown>
    collectSummary.value = '已绑定'
    collectMsg.value = '已导入 Collector，请用测试连接确认探活。'
    await load()
  } catch (e: unknown) {
    collectMsg.value = e instanceof Error ? e.message : '导入失败'
  }
}

async function testConnection() {
  if (!detail.value) return
  collectMsg.value = ''
  try {
    const bindRes = await http.post(`/corp/account/${detail.value.id}/collector-bind/test-connection`, {})
    bindInfo.value = bindRes.data?.data as Record<string, unknown>
    collectMsg.value = '探活成功'
  } catch (e: unknown) {
    collectMsg.value = e instanceof Error ? e.message : '探活失败'
  }
}

function openCreate() {
  form.accountName = ''
  form.companyId = undefined
  form.ipGroupId = undefined
  form.realnameId = undefined
  form.holderUserId = 1
  form.status = 'IN_USE'
  formOpen.value = true
}

async function submitCreate() {
  await http.post('/master/platform-account', {
    platformType: meta.value.platform,
    accountName: form.accountName,
    companyId: form.companyId,
    ipGroupId: form.ipGroupId,
    realnameId: form.realnameId || undefined,
    holderUserId: form.holderUserId,
    status: form.status,
  })
  formOpen.value = false
  load()
}

async function applyDeepLink() {
  const openId = route.query.openId
  if (!openId) return
  const tab = String(route.query.tab || 'basic')
  const hit = rows.value.find((r) => String(r.id) === String(openId))
  if (hit) {
    await openDetail(hit, tab)
    return
  }
  try {
    const res = await http.get(`/corp/account/${openId}`)
    const data = res.data?.data as Record<string, unknown>
    if (data) await openDetail({ id: openId, ...data }, tab)
  } catch {
    /* ignore */
  }
}

watch(
  () => route.params.platform,
  () => {
    pageNo.value = 1
    load().then(() => applyDeepLink())
  },
  { immediate: true },
)

watch(
  () => [route.query.openId, route.query.tab],
  () => {
    applyDeepLink()
  },
)
</script>

<style scoped>
.tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}
</style>
