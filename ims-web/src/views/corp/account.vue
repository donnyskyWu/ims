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
              <td>{{ statusLabel(String(row.status)) }}</td>
              <td>{{ row.collectBindSummary }}</td>
              <td class="acts-cell">
                <button class="btn btn-sec btn-sm" type="button" @click="openDetail(row)">详情</button>
                <button
                  v-if="row.status === 'IN_POOL'"
                  class="btn btn-pri btn-sm"
                  type="button"
                  @click="openCheckout(row)"
                >
                  领用
                </button>
                <button
                  v-if="row.status === 'IN_USE'"
                  class="btn btn-sec btn-sm"
                  type="button"
                  @click="openReturn(row)"
                >
                  归还
                </button>
                <button
                  v-if="row.status !== 'CANCELLED'"
                  class="btn btn-sec btn-sm"
                  type="button"
                  data-testid="acct-recharge-open"
                  @click="openRecharge(row)"
                >
                  冲话费
                </button>
              </td>
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
    <p class="hint">
      GET /corp/account/page?platformType={{ meta.platform }} · 池内账号「领用」→ POST /account/apply · 归还 → POST /account/return/submit · 冲话费 → POST /account/recharge
    </p>

    <div data-testid="acct-recharge-list" class="recharge-list">
      <div class="pg-h" style="margin-top: 8px">
        <div>
          <h2 style="font-size: 16px; margin: 0">冲话费记录</h2>
          <div class="sub">GET /account/recharge/list · 金额 &gt; 5000 须凭证（1025）· 凭证仅财务角色可见</div>
        </div>
      </div>
      <div class="recharge-table">
        <table>
          <thead>
            <tr>
              <th>账号</th>
              <th>金额</th>
              <th>渠道</th>
              <th>充值日期</th>
              <th>凭证</th>
              <th>核对</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!rechargeRows.length">
              <td colspan="6">暂无冲话费记录</td>
            </tr>
            <tr v-for="item in rechargeRows" :key="String(item.id)">
              <td class="mono">{{ item.accountNo }}</td>
              <td class="num">¥{{ moneyText(item.amount) }}</td>
              <td>{{ channelLabel(String(item.channel || '')) }}</td>
              <td>{{ item.rechargeDate }}</td>
              <td>
                <span v-if="item.voucherUrl">{{ item.voucherUrl }}</span>
                <span v-else-if="item.voucherAttached">仅财务可见</span>
                <span v-else>—</span>
              </td>
              <td>{{ item.verifyStatus === 'UNVERIFIED' ? '未核对' : item.verifyStatus }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

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
      <div v-if="detail && activeTab === 'timeline'">
        <p v-if="timelineLoading" class="hint">加载时间线…</p>
        <p v-else-if="timelineError" class="hint">{{ timelineError }}</p>
        <ul v-else-if="timelineEvents.length" class="timeline-list">
          <li v-for="ev in timelineEvents" :key="ev.id">
            <span class="mono">{{ ev.eventTime }}</span>
            <strong>{{ ev.eventType }}</strong>
            {{ ev.snapshotSummary }}
            <span v-if="ev.refNo" class="hint">（{{ ev.refNo }}）</span>
          </li>
        </ul>
        <p v-else class="hint">暂无领用/归还事件</p>
      </div>
      <div v-if="detail && activeTab === 'asset'" class="hint">关联资产需 ASSET 反向穿透接口，契约未在本片实现。</div>
      <template #foot>
        <button
          v-if="detail && detail.status === 'IN_POOL'"
          class="btn btn-pri"
          type="button"
          @click="openCheckout(detail)"
        >
          领用
        </button>
        <button
          v-if="detail && detail.status === 'IN_USE'"
          class="btn btn-sec"
          type="button"
          @click="openReturn(detail)"
        >
          归还
        </button>
        <button class="btn btn-sec" type="button" @click="detailOpen = false">关闭</button>
      </template>
    </ProtoDrawer>

    <ProtoDrawer :open="checkoutOpen" title="发起账号领用" width="520px" @close="closeCheckout">
      <div v-if="checkoutAccount" class="formrow one">
        <div class="fld">
          <label>账号</label>
          <div>{{ checkoutAccount.accountNo }} · {{ checkoutAccount.nickname }}</div>
        </div>
      </div>
      <template v-if="!checkoutApplyId">
        <div class="formrow one">
          <div class="fld">
            <label>用途说明<i class="req">*</i></label>
            <input v-model="checkoutForm.purpose" placeholder="直播/内容用途" />
          </div>
        </div>
        <div class="formrow one">
          <div class="fld">
            <label>计划开始<i class="req">*</i></label>
            <input v-model="checkoutForm.planStart" type="date" />
          </div>
        </div>
        <div class="formrow one">
          <div class="fld">
            <label>计划结束<i class="req">*</i></label>
            <input v-model="checkoutForm.planEnd" type="date" />
          </div>
        </div>
        <p v-if="checkoutMsg" class="hint">{{ checkoutMsg }}</p>
      </template>
      <template v-else>
        <p class="hint">申请单 {{ checkoutApplyNo }} · 状态 {{ checkoutStepLabel }}</p>
        <div v-if="checkoutStep === 'PENDING_APPROVAL'" class="acts" style="margin-top: 12px">
          <button class="btn btn-pri btn-sm" type="button" :disabled="checkoutBusy" @click="approveCheckout">审批通过</button>
        </div>
        <div v-if="checkoutStep === 'PENDING_HANDOVER'" class="formrow one" style="margin-top: 12px">
          <label><input v-model="checkoutHandover.passwordReset" type="checkbox" /> 密码已重置</label>
          <label><input v-model="checkoutHandover.mobileRebound" type="checkbox" /> 绑定手机已换</label>
          <button class="btn btn-pri btn-sm" type="button" :disabled="checkoutBusy" @click="confirmCheckout">确认领用生效</button>
        </div>
        <div v-if="checkoutStep === 'DONE'" class="hint">领用已生效，账号状态应为「在用」。</div>
        <p v-if="checkoutMsg" class="hint">{{ checkoutMsg }}</p>
      </template>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="closeCheckout">取消</button>
        <button
          v-if="!checkoutApplyId"
          class="btn btn-pri"
          type="button"
          :disabled="checkoutBusy"
          @click="submitCheckout"
        >
          提交申请
        </button>
      </template>
    </ProtoDrawer>

    <ProtoDrawer :open="returnOpen" title="账号归还" width="480px" @close="returnOpen = false">
      <div v-if="returnAccount" class="formrow one">
        <div class="fld">
          <label>账号</label>
          <div>{{ returnAccount.accountNo }} · {{ returnAccount.nickname }}</div>
        </div>
        <div class="fld">
          <label>备注</label>
          <input v-model="returnRemark" placeholder="可选" />
        </div>
        <p v-if="returnMsg" class="hint">{{ returnMsg }}</p>
      </div>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="returnOpen = false">取消</button>
        <button class="btn btn-pri" type="button" :disabled="returnBusy" @click="submitReturn">确认归还</button>
      </template>
    </ProtoDrawer>

    <ProtoDrawer :open="rechargeOpen" title="登记冲话费" width="560px" @close="closeRecharge">
      <div v-if="rechargeAccount" data-testid="acct-recharge-drawer" class="formrow one">
        <div class="fld">
          <label>账号</label>
          <div>{{ rechargeAccount.accountNo }} · {{ rechargeAccount.nickname }}</div>
        </div>
        <div class="fld">
          <label>金额（元）<i class="req">*</i></label>
          <input v-model="rechargeForm.amount" data-testid="acct-recharge-amount" inputmode="decimal" placeholder="大于 0，两位小数" />
        </div>
        <div class="fld">
          <label>渠道<i class="req">*</i></label>
          <select v-model="rechargeForm.channel" data-testid="acct-recharge-channel">
            <option v-for="item in rechargeChannels" :key="item.value" :value="item.value">{{ item.label }}</option>
          </select>
        </div>
        <div class="fld">
          <label>充值日期<i class="req">*</i></label>
          <input v-model="rechargeForm.rechargeDate" data-testid="acct-recharge-date" type="date" />
        </div>
        <div class="fld">
          <label>凭证</label>
          <input v-model="rechargeForm.voucherUrl" data-testid="acct-recharge-voucher" placeholder="凭证号或 fileKey（金额大于 5000 必填）" />
        </div>
        <p v-if="rechargeNeedsVoucher" class="hint">金额超过 5000 元，未填凭证将返回 1025</p>
        <p v-if="rechargeMsg" class="hint" data-testid="acct-recharge-msg">{{ rechargeMsg }}</p>
      </div>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="closeRecharge">取消</button>
        <button class="btn btn-pri" type="button" data-testid="acct-recharge-submit" :disabled="rechargeBusy" @click="submitRecharge">
          提交登记
        </button>
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
import { errorMessage, http } from '../../api/http'
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

const timelineEvents = ref<
  { id: number; eventType: string; refNo: string; snapshotSummary: string; eventTime: string }[]
>([])
const timelineLoading = ref(false)
const timelineError = ref('')

const checkoutOpen = ref(false)
const checkoutAccount = ref<Record<string, unknown> | null>(null)
const checkoutApplyId = ref<number | null>(null)
const checkoutApplyNo = ref('')
const checkoutStep = ref('')
const checkoutBusy = ref(false)
const checkoutMsg = ref('')
const checkoutForm = reactive({
  purpose: 'E2E 内容直播领用',
  planStart: '',
  planEnd: '',
})
const checkoutHandover = reactive({ passwordReset: true, mobileRebound: false })

const returnOpen = ref(false)
const returnAccount = ref<Record<string, unknown> | null>(null)
const returnRemark = ref('')
const returnBusy = ref(false)
const returnMsg = ref('')

const rechargeChannels = [
  { value: 'ALIPAY', label: '支付宝' },
  { value: 'WECHAT', label: '微信' },
  { value: 'BANK', label: '银行卡' },
]
const rechargeRows = ref<Record<string, unknown>[]>([])
const rechargeOpen = ref(false)
const rechargeAccount = ref<Record<string, unknown> | null>(null)
const rechargeBusy = ref(false)
const rechargeMsg = ref('')
const rechargeForm = reactive({
  amount: '',
  channel: 'ALIPAY',
  rechargeDate: '',
  voucherUrl: '',
})

const rechargeNeedsVoucher = computed(() => {
  const amount = Number(rechargeForm.amount)
  return Number.isFinite(amount) && amount > 5000 && !rechargeForm.voucherUrl.trim()
})

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

const checkoutStepLabel = computed(() => {
  if (checkoutStep.value === 'PENDING_APPROVAL') return '待审批'
  if (checkoutStep.value === 'PENDING_HANDOVER') return '待交接确认'
  if (checkoutStep.value === 'DONE') return '已领用'
  return checkoutStep.value
})

function statusLabel(code: string) {
  const hit = statusOptions.find((o) => o.value === code)
  return hit ? hit.label : code
}

function channelLabel(code: string) {
  const hit = rechargeChannels.find((o) => o.value === code)
  return hit ? hit.label : code
}

function moneyText(value: unknown) {
  const amount = Number(value)
  return Number.isFinite(amount) ? amount.toFixed(2) : '—'
}

function todayUtc() {
  return new Date().toISOString().slice(0, 10)
}

function bizMessage(error: unknown) {
  if (error && typeof error === 'object' && 'code' in error) {
    const body = error as { code?: number; msg?: string }
    if (typeof body.code === 'number' && body.code !== 0) {
      return `${body.code} ${body.msg || ''}`.trim()
    }
  }
  return errorMessage(error)
}

function defaultPlanDates() {
  const start = new Date()
  const end = new Date()
  end.setDate(end.getDate() + 30)
  const fmt = (d: Date) => d.toISOString().slice(0, 10)
  checkoutForm.planStart = fmt(start)
  checkoutForm.planEnd = fmt(end)
}

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
    { label: '状态', value: statusLabel(String(d.status || '')) },
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
    await loadRecharges()
  }
}

async function loadRecharges() {
  try {
    const res = await http.get('/account/recharge/list', { params: { pageNo: 1, pageSize: 20 } })
    const data = res.data?.data as { list: Record<string, unknown>[] }
    rechargeRows.value = data?.list || []
  } catch {
    rechargeRows.value = []
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

async function loadTimeline(accountId: unknown) {
  timelineLoading.value = true
  timelineError.value = ''
  timelineEvents.value = []
  try {
    const res = await http.get(`/account/timeline/${accountId}`)
    const data = res.data?.data as { list: typeof timelineEvents.value }
    timelineEvents.value = data?.list || []
  } catch (e: unknown) {
    timelineError.value = e instanceof Error ? e.message : '时间线加载失败'
  } finally {
    timelineLoading.value = false
  }
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
  if (tab === 'timeline') {
    await loadTimeline(row.id)
  }
  detailOpen.value = true
}

function openCheckout(row: Record<string, unknown>) {
  checkoutAccount.value = row
  checkoutApplyId.value = null
  checkoutApplyNo.value = ''
  checkoutStep.value = ''
  checkoutMsg.value = ''
  checkoutHandover.passwordReset = true
  checkoutHandover.mobileRebound = false
  defaultPlanDates()
  checkoutOpen.value = true
}

function closeCheckout() {
  checkoutOpen.value = false
  checkoutAccount.value = null
  checkoutApplyId.value = null
}

async function submitCheckout() {
  if (!checkoutAccount.value) return
  checkoutBusy.value = true
  checkoutMsg.value = ''
  try {
    const res = await http.post('/account/apply', {
      accountId: checkoutAccount.value.id,
      purpose: checkoutForm.purpose,
      planStart: checkoutForm.planStart,
      planEnd: checkoutForm.planEnd,
    })
    const vo = res.data?.data as { id: number; applyNo: string; applyStatus: string }
    checkoutApplyId.value = vo.id
    checkoutApplyNo.value = vo.applyNo
    checkoutStep.value = vo.applyStatus
  } catch (e: unknown) {
    checkoutMsg.value = e instanceof Error ? e.message : '提交失败'
  } finally {
    checkoutBusy.value = false
  }
}

async function approveCheckout() {
  if (!checkoutApplyId.value) return
  checkoutBusy.value = true
  checkoutMsg.value = ''
  try {
    await http.put(`/account/apply/${checkoutApplyId.value}/approve`, { action: 'APPROVE' })
    checkoutStep.value = 'PENDING_HANDOVER'
  } catch (e: unknown) {
    checkoutMsg.value = e instanceof Error ? e.message : '审批失败'
  } finally {
    checkoutBusy.value = false
  }
}

async function confirmCheckout() {
  if (!checkoutApplyId.value) return
  checkoutBusy.value = true
  checkoutMsg.value = ''
  try {
    await http.put(`/account/apply/${checkoutApplyId.value}/confirm`, {
      passwordReset: checkoutHandover.passwordReset,
      mobileRebound: checkoutHandover.mobileRebound,
    })
    checkoutStep.value = 'DONE'
    checkoutOpen.value = false
    await load()
    if (detail.value && String(detail.value.id) === String(checkoutAccount.value?.id)) {
      const res = await http.get(`/corp/account/${detail.value.id}`)
      detail.value = res.data?.data as Record<string, unknown>
    }
  } catch (e: unknown) {
    checkoutMsg.value = e instanceof Error ? e.message : '确认失败'
  } finally {
    checkoutBusy.value = false
  }
}

function openReturn(row: Record<string, unknown>) {
  returnAccount.value = row
  returnRemark.value = ''
  returnMsg.value = ''
  returnOpen.value = true
}

async function submitReturn() {
  if (!returnAccount.value) return
  returnBusy.value = true
  returnMsg.value = ''
  try {
    await http.post('/account/return/submit', {
      accountId: returnAccount.value.id,
      remark: returnRemark.value || undefined,
    })
    returnOpen.value = false
    detailOpen.value = false
    await load()
  } catch (e: unknown) {
    returnMsg.value = e instanceof Error ? e.message : '归还失败'
  } finally {
    returnBusy.value = false
  }
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

function openRecharge(row: Record<string, unknown>) {
  rechargeAccount.value = row
  rechargeForm.amount = ''
  rechargeForm.channel = 'ALIPAY'
  rechargeForm.rechargeDate = todayUtc()
  rechargeForm.voucherUrl = ''
  rechargeMsg.value = ''
  rechargeOpen.value = true
}

function closeRecharge() {
  rechargeOpen.value = false
  rechargeAccount.value = null
}

async function submitRecharge() {
  if (!rechargeAccount.value) return
  rechargeBusy.value = true
  rechargeMsg.value = ''
  try {
    const amount = Number(rechargeForm.amount)
    if (!Number.isFinite(amount) || amount <= 0) {
      rechargeMsg.value = '1001 金额格式不合法'
      return
    }
    await http.post(
      '/account/recharge',
      {
        accountId: rechargeAccount.value.id,
        amount,
        channel: rechargeForm.channel,
        rechargeDate: rechargeForm.rechargeDate,
        voucherUrl: rechargeForm.voucherUrl.trim() || undefined,
      },
      { headers: { clientToken: crypto.randomUUID().replace(/-/g, '') } },
    )
    rechargeMsg.value = '冲话费已登记'
    rechargeOpen.value = false
    await loadRecharges()
  } catch (e: unknown) {
    rechargeMsg.value = bizMessage(e)
  } finally {
    rechargeBusy.value = false
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

watch(activeTab, (tab) => {
  if (tab === 'timeline' && detail.value?.id) {
    loadTimeline(detail.value.id)
  }
})
</script>

<style scoped>
.tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}
.acts-cell {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.timeline-list {
  list-style: none;
  padding: 0;
  margin: 0;
}
.timeline-list li {
  padding: 8px 0;
  border-bottom: 1px solid var(--border, #eee);
}
.recharge-list {
  margin-top: 12px;
}
.recharge-table {
  overflow: auto;
}
</style>
