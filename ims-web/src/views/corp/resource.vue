<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>{{ meta.title }}</h1>
        <div class="sub">{{ meta.sub }}</div>
      </div>
      <div v-if="kind === 'sim-card'" class="acts">
        <button class="btn btn-pri" type="button" @click="openCreate">新建手机卡</button>
      </div>
      <div v-else-if="kind === 'certificate'" class="acts">
        <button class="btn btn-sec" type="button" data-testid="corp-cert-scan-btn" @click="openScan">扫描到期</button>
        <button class="btn btn-pri" type="button" data-testid="corp-cert-create-btn" @click="openCertCreate">录入证件</button>
      </div>
    </div>
    <form class="qbar" @submit.prevent="search">
      <input v-model="keyword" :placeholder="meta.placeholder" style="width: 180px" />
      <select v-if="meta.statusOptions.length" v-model="status" style="width: 120px">
        <option value="">全部状态</option>
        <option v-for="item in meta.statusOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
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
              <th v-for="col in meta.columns" :key="col">{{ col }}</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td :colspan="meta.columns.length + 1" style="white-space: normal">
                <div class="empty"><div class="et">加载中</div></div>
              </td>
            </tr>
            <tr v-else-if="!rows.length">
              <td :colspan="meta.columns.length + 1" style="white-space: normal">
                <div class="empty">
                  <div class="et">{{ error || meta.empty }}</div>
                  <div class="es">{{ meta.emptyHint }}</div>
                </div>
              </td>
            </tr>
            <tr v-for="row in rows" v-else :key="String(row.id)">
              <td v-for="key in meta.keys" :key="key">{{ show(row, key) }}</td>
              <td>
                <button
                  class="btn btn-txt btn-sm"
                  type="button"
                  :data-testid="kind === 'certificate' ? 'corp-cert-view-btn' : undefined"
                  @click="openDetail(row)"
                >
                  {{ kind === 'certificate' ? '查看' : '详情' }}
                </button>
                <button v-if="kind === 'sim-card'" class="btn btn-txt btn-sm" type="button" @click="openEdit(row)">编辑</button>
                <button
                  v-if="kind === 'certificate' && row.status === 'PENDING_REVIEW'"
                  class="btn btn-txt btn-sm"
                  type="button"
                  data-testid="corp-cert-review-btn"
                  @click="openReview(row)"
                >
                  审核
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
    <p class="hint">{{ meta.hint }}</p>
    <div v-if="kind === 'certificate'" data-testid="corp-cert-expire-panel">
      <div class="sec rowline" style="justify-content: space-between; align-items: baseline">
        <span>到期预警</span>
        <span data-testid="corp-cert-expire-stats">黄色 {{ expireStats.yellow }} · 红色 {{ expireStats.red }} · 锁定 {{ expireStats.locked }}</span>
      </div>
      <p v-if="scanMessage" class="hint" data-testid="corp-cert-scan-message">{{ scanMessage }}</p>
      <form class="qbar" @submit.prevent="searchExpire">
        <input v-model="expireHolder" placeholder="预警持有人" style="width: 180px" data-testid="corp-cert-expire-holder" />
        <span class="sp"></span>
        <button class="btn btn-pri btn-sm" type="submit">筛选</button>
        <button class="btn btn-sec btn-sm" type="button" @click="resetExpire">重置</button>
      </form>
      <div class="tbl-block">
        <div class="tbl-wrap">
          <table data-testid="corp-cert-expire-table">
            <thead>
              <tr>
                <th>持有人</th>
                <th>证件号</th>
                <th>有效期至</th>
                <th>剩余天数</th>
                <th>预警级别</th>
                <th>状态</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="expireLoading">
                <td colspan="6" style="white-space: normal"><div class="empty"><div class="et">加载中</div></div></td>
              </tr>
              <tr v-else-if="!expireRows.length">
                <td colspan="6" style="white-space: normal">
                  <div class="empty"><div class="et">{{ expireError || '当前无到期预警' }}</div></div>
                </td>
              </tr>
              <tr v-for="row in expireRows" v-else :key="String(row.id)">
                <td>{{ show(row, 'holderName') }}</td>
                <td>{{ show(row, 'certNoMasked') }}</td>
                <td>{{ show(row, 'expireDate') }}</td>
                <td>{{ show(row, 'remainDays') }}</td>
                <td>
                  <span data-testid="corp-cert-level" :style="levelStyle(String(row.level || ''))">{{ levelLabel(String(row.level || '')) }}</span>
                </td>
                <td>{{ expireStatusLabel(String(row.status || '')) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
    <ProtoDrawer
      :open="detailOpen"
      :title="meta.detailTitle"
      width="520px"
      :data-testid="kind === 'certificate' ? 'corp-cert-detail-drawer' : undefined"
      @close="detailOpen = false"
    >
      <div v-if="detail" class="formrow one">
        <div v-for="item in detailLines" :key="item.label" class="fld">
          <label>{{ item.label }}</label>
          <div>{{ item.value }}</div>
        </div>
      </div>
      <div
        v-if="kind === 'certificate' && detail"
        class="hint"
        data-testid="corp-cert-watermark-hint"
      >
        水印：{{ detail.watermarkText || '—' }}。本接口不返回原图。
      </div>
      <div v-if="kind === 'realname'" class="hint">中介人与关联账号暂无。契约没有实名人写入接口。</div>
      <div v-if="kind === 'sim-card' && detail" class="hint">关联账号 {{ linkedCount }} 个。平台账号在下一片接入前这里是空列表。</div>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="detailOpen = false">关闭</button>
      </template>
    </ProtoDrawer>
    <ProtoDrawer :open="formOpen" :title="editingId ? '编辑手机卡' : '新建手机卡'" width="480px" @close="formOpen = false">
      <div class="formrow one"><div class="fld"><label>手机号<i class="req">*</i></label><input v-model="form.phoneNumber" placeholder="11 位，编辑时留空表示不改" /></div></div>
      <div class="formrow one">
        <div class="fld">
          <label>是否主卡<i class="req">*</i></label>
          <select v-model="form.isPrimary">
            <option v-for="item in yesNo" :key="item.value" :value="item.value">{{ item.label }}</option>
          </select>
        </div>
      </div>
      <div class="formrow one">
        <div class="fld">
          <label>运营商<i class="req">*</i></label>
          <select v-model="form.operator">
            <option v-for="item in operators" :key="item.value" :value="item.value">{{ item.label }}</option>
          </select>
        </div>
      </div>
      <div class="formrow one">
        <div class="fld">
          <label>归属人<i class="req">*</i></label>
          <select v-model="form.assignedUserId">
            <option value="">请选择本地用户</option>
            <option v-for="user in users" :key="user.id" :value="user.id">{{ user.nickname || user.username }}</option>
          </select>
        </div>
      </div>
      <div class="formrow one">
        <div class="fld">
          <label>实名人</label>
          <select v-model="form.realnameId">
            <option value="">可不选</option>
            <option v-for="person in persons" :key="person.id" :value="person.id">{{ person.realName }}</option>
          </select>
        </div>
      </div>
      <div class="formrow one">
        <div class="fld">
          <label>状态<i class="req">*</i></label>
          <select v-model="form.status">
            <option v-for="item in simStatus" :key="item.value" :value="item.value">{{ item.label }}</option>
          </select>
        </div>
      </div>
      <div class="formrow one"><div class="fld"><label>套餐</label><input v-model="form.packageName" /></div></div>
      <div class="formrow one"><div class="fld"><label>月租</label><input v-model="form.monthlyRent" /></div></div>
      <div class="formrow one"><div class="fld"><label>ICCID</label><input v-model="form.iccid" /></div></div>
      <div v-if="formError" class="hint bad">{{ formError }}</div>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="formOpen = false">取消</button>
        <button class="btn btn-pri" type="button" :disabled="saving" @click="save">{{ saving ? '保存中…' : '保存' }}</button>
      </template>
    </ProtoDrawer>
    <ProtoDrawer :open="certFormOpen" title="录入证件" width="480px" @close="certFormOpen = false">
      <div class="formrow one"><div class="fld"><label>持有人<i class="req">*</i></label><input v-model="certForm.holderName" data-testid="corp-cert-holder" placeholder="姓名" /></div></div>
      <div class="formrow one">
        <div class="fld">
          <label>证件类型<i class="req">*</i></label>
          <select v-model="certForm.certType" data-testid="corp-cert-type">
            <option value="IDCARD">身份证</option>
            <option value="PASSPORT">护照</option>
            <option value="OTHER">其他</option>
          </select>
        </div>
      </div>
      <div class="formrow one"><div class="fld"><label>证件号<i class="req">*</i></label><input v-model="certForm.certNoPlain" data-testid="corp-cert-no" placeholder="至少 8 位，接口只回脱敏值" /></div></div>
      <div class="formrow one"><div class="fld"><label>签发日期<i class="req">*</i></label><input v-model="certForm.issueDate" type="date" data-testid="corp-cert-issue" /></div></div>
      <div class="formrow one"><div class="fld"><label>有效期至<i class="req">*</i></label><input v-model="certForm.expireDate" type="date" data-testid="corp-cert-expire-date" /></div></div>
      <div class="formrow one"><div class="fld"><label>扫描件标识<i class="req">*</i></label><input v-model="certForm.fileKey" data-testid="corp-cert-file-key" /></div></div>
      <div class="hint">提交后为待审。审核生效后才参与到期扫描。本期不返回原图。</div>
      <div v-if="certFormError" class="hint bad" data-testid="corp-cert-form-error">{{ certFormError }}</div>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="certFormOpen = false">取消</button>
        <button class="btn btn-pri" type="button" data-testid="corp-cert-save" :disabled="certSaving" @click="saveCert">{{ certSaving ? '提交中…' : '提交审核' }}</button>
      </template>
    </ProtoDrawer>
    <ProtoDrawer :open="reviewOpen" title="审核证件" width="420px" @close="reviewOpen = false">
      <div class="formrow one">
        <div class="fld"><label>持有人</label><div>{{ reviewRow?.holderName || '—' }}</div></div>
        <div class="fld"><label>证件号</label><div>{{ reviewRow?.certNoMasked || '—' }}</div></div>
        <div class="fld"><label>有效期至</label><div>{{ reviewRow?.expireDate || '—' }}</div></div>
      </div>
      <div v-if="reviewError" class="hint bad">{{ reviewError }}</div>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="reviewOpen = false">取消</button>
        <button class="btn btn-pri" type="button" data-testid="corp-cert-review-approve" :disabled="reviewSaving" @click="approveCert">通过</button>
      </template>
    </ProtoDrawer>
    <ProtoDrawer :open="scanOpen" title="扫描到期" width="420px" @close="scanOpen = false">
      <div class="hint">按今日扫描已生效证件：剩余 30 天黄色、7 天红色、当天锁定，并写入工作台提醒。同一级别不重复推送。</div>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="scanOpen = false">取消</button>
        <button class="btn btn-pri" type="button" data-testid="corp-cert-scan-confirm" :disabled="scanSaving" @click="confirmScan">{{ scanSaving ? '扫描中…' : '确认扫描' }}</button>
      </template>
    </ProtoDrawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import ProtoDrawer from '../../components/ProtoDrawer.vue'
import { http, errorMessage } from '../../api/http'
import { asList, asTotal } from '../../api/read'

type Row = Record<string, unknown>
type Opt = { value: string; label: string }

const route = useRoute()
const kind = computed(() => String(route.params.kind || 'company'))
const rows = ref<Row[]>([])
const total = ref(0)
const pageNo = ref(1)
const pageSize = ref(10)
const keyword = ref('')
const status = ref('')
const loading = ref(false)
const error = ref('')
const detailOpen = ref(false)
const detail = ref<Row | null>(null)
const certFormOpen = ref(false)
const certSaving = ref(false)
const certFormError = ref('')
const certForm = reactive({
  holderName: '',
  certType: 'IDCARD',
  certNoPlain: '',
  issueDate: '2020-01-01',
  expireDate: '',
  fileKey: 'local/cert/upload',
})
const reviewOpen = ref(false)
const reviewSaving = ref(false)
const reviewError = ref('')
const reviewRow = ref<Row | null>(null)
const scanOpen = ref(false)
const scanSaving = ref(false)
const scanMessage = ref('')
const expireRows = ref<Row[]>([])
const expireLoading = ref(false)
const expireError = ref('')
const expireHolder = ref('')
const expireStats = reactive({ yellow: 0, red: 0, locked: 0 })
const formOpen = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)
const formError = ref('')
const users = ref<{ id: string; username: string; nickname: string }[]>([])
const persons = ref<{ id: number; realName: string }[]>([])
const yesNo = ref<Opt[]>([])
const operators = ref<Opt[]>([])
const simStatus = ref<Opt[]>([])
const form = reactive({
  phoneNumber: '',
  isPrimary: 'NO',
  operator: 'MOBILE',
  assignedUserId: '',
  realnameId: '',
  status: 'IN_USE',
  packageName: '',
  monthlyRent: '',
  iccid: '',
})

const specs: Record<string, {
  title: string
  sub: string
  placeholder: string
  empty: string
  emptyHint: string
  hint: string
  detailTitle: string
  columns: string[]
  keys: string[]
  statusOptions: Opt[]
}> = {
  company: {
    title: '公司管理',
    sub: 'CORP-R · 只查询 · GET /corp/resource/company/page',
    placeholder: '公司名称',
    empty: '没有公司',
    emptyHint: '契约只有分页和详情，这里不能新建。',
    hint: '公司、实名人按契约只做查询。信用代码和法人来自详情，不提供写入。',
    detailTitle: '公司详情',
    columns: ['公司', '信用代码', '行业', '法人', '容量', '已注册', '剩余', '状态'],
    keys: ['companyName', 'creditCode', 'industry', 'legalName', 'mpCapacityStandard', 'mpRegisteredCount', 'mpRemaining', 'status'],
    statusOptions: [
      { value: 'ENABLED', label: '启用' },
      { value: 'DISABLED', label: '停用' },
    ],
  },
  realname: {
    title: '实名人管理',
    sub: 'CORP-R · 姓名、证件号、手机由接口脱敏',
    placeholder: '姓名',
    empty: '没有实名人',
    emptyHint: '契约只有分页和详情。',
    hint: '列表不返回证件号和手机明文。没有新建接口。',
    detailTitle: '实名人详情',
    columns: ['姓名', '证件类型', '证件号', '手机', '状态'],
    keys: ['realName', 'idType', 'idCardMasked', 'phoneMasked', 'status'],
    statusOptions: [
      { value: 'ENABLED', label: '启用' },
      { value: 'DISABLED', label: '停用' },
    ],
  },
  'sim-card': {
    title: '手机卡管理',
    sub: 'CORP-R · 号码脱敏 · 归属人只选本地用户',
    placeholder: '完整手机号',
    empty: '没有手机卡',
    emptyHint: '可以新建。号码和 ICCID 只以脱敏值返回。',
    hint: 'POST/PUT /corp/resource/sim-card。关联账号等平台账号片接入。',
    detailTitle: '手机卡详情',
    columns: ['号码', '实名人', '运营商', '归属人', '月租', '状态'],
    keys: ['phoneNumber', 'realNameMasked', 'operator', 'assignedUserName', 'monthlyRent', 'status'],
    statusOptions: [],
  },
  certificate: {
    title: '证件管理',
    sub: 'CORP-R · 索引分页 · 到期预警 · 查看带水印，不出原图',
    placeholder: '持有人',
    empty: '没有证件档案',
    emptyHint: '可以录入。审核生效后参与到期扫描。',
    hint: '录入 POST /cert/archive/upload，审核 PUT /cert/archive/{id}/review，扫描 POST /cert/expire/scan。证件号只显示脱敏值。',
    detailTitle: '证件查看',
    columns: ['持有人', '类型', '证件号', '有效期', '状态'],
    keys: ['holderName', 'certType', 'certNoMasked', 'expireDate', 'status'],
    statusOptions: [
      { value: 'PENDING_REVIEW', label: '待审' },
      { value: 'EFFECTIVE', label: '生效' },
      { value: 'EXPIRING', label: '即将到期' },
      { value: 'EXPIRED', label: '已过期' },
      { value: 'RECYCLED', label: '已回收' },
    ],
  },
}

const meta = computed(() => specs[kind.value] || specs.company)
const pageCount = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))
const pageList = computed(() => {
  const end = Math.min(pageCount.value, Math.max(pageNo.value + 2, 5))
  const start = Math.max(1, end - 4)
  const list: number[] = []
  for (let i = start; i <= Math.min(pageCount.value, start + 4); i += 1) list.push(i)
  return list
})
const linkedCount = computed(() => {
  const list = detail.value?.linkedAccounts
  return Array.isArray(list) ? list.length : 0
})
const detailLines = computed(() => {
  if (!detail.value) return []
  return meta.value.keys.map((key) => ({ label: labelOf(key), value: show(detail.value || {}, key) }))
})

const labels: Record<string, string> = {
  companyName: '公司',
  creditCode: '信用代码',
  industry: '行业',
  legalName: '法人',
  mpCapacityStandard: '容量',
  mpRegisteredCount: '已注册',
  mpRemaining: '剩余',
  status: '状态',
  realName: '姓名',
  idType: '证件类型',
  idCardMasked: '证件号',
  phoneMasked: '手机',
  phoneNumber: '号码',
  realNameMasked: '实名人',
  operator: '运营商',
  assignedUserName: '归属人',
  monthlyRent: '月租',
  holderName: '持有人',
  certType: '类型',
  certNoMasked: '证件号',
  expireDate: '有效期',
}

function labelOf(key: string) {
  return labels[key] || key
}

function show(row: Row, key: string) {
  const value = row[key]
  if (value === undefined || value === null || value === '') return '—'
  if (key === 'status') return statusLabel(String(value))
  if (key === 'operator') return operators.value.find((item) => item.value === value)?.label || String(value)
  if (key === 'idType' || key === 'certType') return typeLabel(String(value))
  return String(value)
}

function statusLabel(value: string) {
  const found = [...meta.value.statusOptions, ...simStatus.value].find((item) => item.value === value)
  if (found) return found.label
  if (value === 'ENABLED') return '启用'
  if (value === 'DISABLED') return '停用'
  return value
}

function levelLabel(value: string) {
  if (value === 'YELLOW') return '黄色'
  if (value === 'RED') return '红色'
  if (value === 'LOCKED') return '锁定'
  return value || '—'
}

function levelStyle(value: string) {
  if (value === 'YELLOW') return 'color:#a16207;font-weight:600'
  if (value === 'RED') return 'color:#b91c1c;font-weight:600'
  if (value === 'LOCKED') return 'color:#7f1d1d;font-weight:700'
  return ''
}

function expireStatusLabel(value: string) {
  if (value === 'WARNING') return '预警中'
  if (value === 'EXPIRED_LOCKED') return '已锁定'
  if (value === 'RENEW_RESOLVED') return '已换证'
  return value || '—'
}

function openCertCreate() {
  certForm.holderName = ''
  certForm.certType = 'IDCARD'
  certForm.certNoPlain = ''
  certForm.issueDate = '2020-01-01'
  certForm.expireDate = ''
  certForm.fileKey = 'local/cert/upload'
  certFormError.value = ''
  certFormOpen.value = true
}

async function saveCert() {
  certSaving.value = true
  certFormError.value = ''
  try {
    await http.post('/cert/archive/upload', {
      holderName: certForm.holderName.trim(),
      certType: certForm.certType,
      certNoPlain: certForm.certNoPlain.trim(),
      fileKey: certForm.fileKey.trim(),
      issueDate: certForm.issueDate,
      expireDate: certForm.expireDate,
    })
    certFormOpen.value = false
    await load()
  } catch (e: unknown) {
    certFormError.value = errorMessage(e)
  } finally {
    certSaving.value = false
  }
}

function openReview(row: Row) {
  reviewRow.value = row
  reviewError.value = ''
  reviewOpen.value = true
}

async function approveCert() {
  const id = reviewRow.value?.id
  if (id === undefined || id === null || id === '') {
    reviewError.value = '缺少证件 id'
    return
  }
  reviewSaving.value = true
  reviewError.value = ''
  try {
    await http.put(`/cert/archive/${id}/review`, { action: 'APPROVE' })
    reviewOpen.value = false
    await load()
  } catch (e: unknown) {
    reviewError.value = errorMessage(e)
  } finally {
    reviewSaving.value = false
  }
}

function openScan() {
  scanOpen.value = true
}

async function loadExpire() {
  expireLoading.value = true
  expireError.value = ''
  try {
    const params: Record<string, string | number> = { pageNo: 1, pageSize: 20 }
    const text = expireHolder.value.trim()
    if (text) params.holderName = text
    const [listRes, statsRes] = await Promise.all([
      http.get('/cert/expire/list', { params }),
      http.get('/cert/expire/stats'),
    ])
    const data = listRes.data?.data
    expireRows.value = asList(data)
    const stats = statsRes.data?.data || {}
    expireStats.yellow = Number(stats.yellowCount || 0)
    expireStats.red = Number(stats.redCount || 0)
    expireStats.locked = Number(stats.lockedCount || 0)
  } catch (e: unknown) {
    expireRows.value = []
    expireError.value = errorMessage(e)
  } finally {
    expireLoading.value = false
  }
}

function searchExpire() {
  loadExpire()
}

function resetExpire() {
  expireHolder.value = ''
  loadExpire()
}

async function confirmScan() {
  scanSaving.value = true
  try {
    const res = await http.post('/cert/expire/scan')
    scanMessage.value = String(res.data?.data?.message || '扫描完成')
    scanOpen.value = false
    await Promise.all([load(), loadExpire()])
  } catch (e: unknown) {
    scanMessage.value = errorMessage(e)
    scanOpen.value = false
  } finally {
    scanSaving.value = false
  }
}

function typeLabel(value: string) {
  const map: Record<string, string> = {
    ID_CARD: '身份证',
    PASSPORT: '护照',
    HK_MACAO: '港澳通行证',
    TAIWAN: '台湾通行证',
    IDCARD: '身份证',
    OTHER: '其他',
  }
  return map[value] || value
}

function params() {
  const query: Record<string, string | number> = { pageNo: pageNo.value, pageSize: pageSize.value }
  const text = keyword.value.trim()
  if (text) {
    if (kind.value === 'company') query.companyName = text
    if (kind.value === 'realname') query.realName = text
    if (kind.value === 'sim-card') query.phoneNumber = text
    if (kind.value === 'certificate') query.holderName = text
  }
  if (status.value) query.status = status.value
  return query
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await http.get(`/corp/resource/${kind.value}/page`, { params: params() })
    const data = res.data?.data
    rows.value = asList(data)
    total.value = asTotal(data, rows.value.length)
  } catch (e: unknown) {
    rows.value = []
    total.value = 0
    error.value = errorMessage(e)
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
  status.value = ''
  search()
}

function goto(page: number) {
  if (page < 1 || page > pageCount.value || page === pageNo.value) return
  pageNo.value = page
  load()
}

function changeSize(event: Event) {
  pageSize.value = Number((event.target as HTMLSelectElement).value)
  pageNo.value = 1
  load()
}

async function openDetail(row: Row) {
  detail.value = null
  detailOpen.value = true
  const id = row.id
  const url = kind.value === 'certificate' ? `/corp/resource/certificate/${id}/view` : `/corp/resource/${kind.value}/${id}`
  try {
    const res = await http.get(url)
    const data = res.data?.data || {}
    detail.value = kind.value === 'certificate' ? { ...(data.indexInfo || {}), watermarkText: data.watermarkText } : data
  } catch (e: unknown) {
    detail.value = { status: errorMessage(e) }
  }
}

async function loadDict(dictType: string) {
  const res = await http.get('/system/dict-data/list', { params: { dictType } })
  return asList(res.data?.data)
    .filter((row) => row.status === 'ENABLED')
    .map((row) => ({ value: String(row.dictValue), label: String(row.dictLabel) }))
}

async function prepareSim() {
  const [yn, ops, st, userPage, personPage] = await Promise.all([
    loadDict('dict_yes_no'),
    loadDict('dict_sim_operator'),
    loadDict('dict_sim_status'),
    http.get('/system/user/page', { params: { pageNo: 1, pageSize: 100 } }),
    http.get('/corp/resource/realname/page', { params: { pageNo: 1, pageSize: 100, status: 'ENABLED' } }),
  ])
  yesNo.value = yn
  operators.value = ops
  simStatus.value = st
  specs['sim-card'].statusOptions = st
  users.value = asList(userPage.data?.data) as unknown as { id: string; username: string; nickname: string }[]
  persons.value = asList(personPage.data?.data) as unknown as { id: number; realName: string }[]
}

function openCreate() {
  editingId.value = null
  form.phoneNumber = ''
  form.isPrimary = 'NO'
  form.operator = 'MOBILE'
  form.assignedUserId = users.value[0]?.id || ''
  form.realnameId = ''
  form.status = 'IN_USE'
  form.packageName = ''
  form.monthlyRent = ''
  form.iccid = ''
  formError.value = ''
  formOpen.value = true
}

function openEdit(row: Row) {
  editingId.value = Number(row.id)
  form.phoneNumber = ''
  form.isPrimary = String(row.isPrimary || 'NO')
  form.operator = String(row.operator || 'MOBILE')
  form.assignedUserId = String(row.assignedUserId || '')
  form.realnameId = row.realnameId ? String(row.realnameId) : ''
  form.status = String(row.status || 'IN_USE')
  form.packageName = String(row.packageName || '')
  form.monthlyRent = String(row.monthlyRent || '')
  form.iccid = ''
  formError.value = ''
  formOpen.value = true
}

async function save() {
  saving.value = true
  formError.value = ''
  const payload: Record<string, unknown> = {
    isPrimary: form.isPrimary,
    operator: form.operator,
    assignedUserId: Number(form.assignedUserId),
    status: form.status,
    packageName: form.packageName,
    realnameId: form.realnameId ? Number(form.realnameId) : undefined,
  }
  if (form.phoneNumber.trim()) payload.phoneNumber = form.phoneNumber.trim()
  if (form.monthlyRent.trim()) payload.monthlyRent = form.monthlyRent.trim()
  if (form.iccid.trim()) payload.iccid = form.iccid.trim()
  try {
    if (editingId.value) await http.put(`/corp/resource/sim-card/${editingId.value}`, payload)
    else await http.post('/corp/resource/sim-card', payload)
    formOpen.value = false
    await load()
  } catch (e: unknown) {
    formError.value = errorMessage(e)
  } finally {
    saving.value = false
  }
}

watch(kind, async () => {
  keyword.value = ''
  status.value = ''
  pageNo.value = 1
  detailOpen.value = false
  formOpen.value = false
  certFormOpen.value = false
  reviewOpen.value = false
  scanOpen.value = false
  if (kind.value === 'sim-card' && !operators.value.length) {
    try {
      await prepareSim()
    } catch {
      /* 字典失败时列表仍可打开 */
    }
  }
  load()
})

onMounted(async () => {
  if (kind.value === 'sim-card') {
    try {
      await prepareSim()
    } catch {
      /* 字典失败时列表仍可打开 */
    }
  }
  await load()
  if (kind.value === 'certificate') await loadExpire()
})
</script>
