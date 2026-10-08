<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>{{ meta.title }}</h1>
        <div class="sub">{{ meta.sub }}</div>
      </div>
      <div class="acts">
        <button v-if="kind === 'phone'" class="btn btn-pri" type="button" @click="openCreate">新建手机</button>
        <template v-else>
          <button v-if="kind === 'office'" class="btn btn-sec" type="button" data-testid="corp-asset-forward-open" @click="openForwardPerson">正向穿透</button>
          <button class="btn btn-pri" type="button" data-testid="corp-asset-create-btn" @click="openAssetCreate">资产登记</button>
        </template>
      </div>
    </div>
    <form class="qbar" @submit.prevent="search">
      <input v-model="keyword" :placeholder="meta.placeholder" style="width: 180px" />
      <select v-if="kind === 'phone'" v-model="status" style="width: 120px">
        <option value="">全部状态</option>
        <option v-for="item in phoneStatus" :key="item.value" :value="item.value">{{ item.label }}</option>
      </select>
      <select v-else v-model="status" style="width: 120px" data-testid="corp-asset-status-filter">
        <option value="">全部状态</option>
        <option v-for="item in assetStatusOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
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
              <td v-for="key in meta.keys" :key="key" :data-testid="key === 'status' && kind !== 'phone' ? 'corp-asset-status' : undefined">
                {{ show(row, key) }}
              </td>
              <td v-if="kind === 'phone'">
                <button class="btn btn-txt" type="button" @click="openDetail(row)">详情</button>
              </td>
              <td v-else>
                <button v-if="row.status === 'PENDING_REVIEW'" class="btn btn-txt" type="button" data-testid="corp-asset-checkout-btn" @click="openCheckout(row)">领用</button>
                <button v-if="row.status === 'IN_USE'" class="btn btn-txt" type="button" data-testid="corp-asset-use-btn" @click="openUse(row)">使用</button>
                <button v-if="row.status === 'IN_USE'" class="btn btn-txt" type="button" data-testid="corp-asset-return-btn" @click="openReturn(row)">归还</button>
                <button v-if="row.status === 'RETURNED'" class="btn btn-txt" type="button" data-testid="corp-asset-scrap-btn" @click="openScrap(row)">报废</button>
                <button class="btn btn-txt" type="button" data-testid="corp-asset-detail-btn" @click="openAssetDetail(row)">详情</button>
                <button v-if="kind === 'office'" class="btn btn-txt" type="button" data-testid="corp-asset-forward-btn" @click="openForwardAsset(row)">正向穿透</button>
                <button v-if="kind === 'office'" class="btn btn-txt" type="button" data-testid="corp-asset-reverse-btn" @click="openReverse(row)">反向穿透</button>
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
    <ProtoDrawer :open="detailOpen" title="手机详情" width="480px" @close="detailOpen = false">
      <div v-if="detail" class="formrow one">
        <div v-for="key in meta.keys" :key="key" class="fld">
          <label>{{ labelOf(key) }}</label>
          <div>{{ show(detail, key) }}</div>
        </div>
      </div>
      <div class="hint">绑定账号 0 个。没有实名人字段。影像只保存 key，不提供上传。</div>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="detailOpen = false">关闭</button>
      </template>
    </ProtoDrawer>
    <ProtoDrawer :open="formOpen" title="新建手机" width="480px" @close="formOpen = false">
      <div class="formrow one"><div class="fld"><label>手机号<i class="req">*</i></label><input v-model="form.phoneNumber" /></div></div>
      <div class="formrow one"><div class="fld"><label>编码</label><input v-model="form.phoneCode" /></div></div>
      <div class="formrow one"><div class="fld"><label>型号</label><input v-model="form.phoneModel" /></div></div>
      <div class="formrow one"><div class="fld"><label>设备编号</label><input v-model="form.deviceNumber" /></div></div>
      <div class="formrow one">
        <div class="fld">
          <label>保管人<i class="req">*</i></label>
          <select v-model="form.keeperId">
            <option value="">请选择本地用户</option>
            <option v-for="user in users" :key="user.id" :value="user.id">{{ user.nickname || user.username }}</option>
          </select>
        </div>
      </div>
      <div class="formrow one">
        <div class="fld">
          <label>类型</label>
          <select v-model="form.phoneType">
            <option value="">可不选</option>
            <option v-for="item in phoneTypes" :key="item.value" :value="item.value">{{ item.label }}</option>
          </select>
        </div>
      </div>
      <div class="formrow one">
        <div class="fld">
          <label>状态<i class="req">*</i></label>
          <select v-model="form.status">
            <option v-for="item in phoneStatus" :key="item.value" :value="item.value">{{ item.label }}</option>
          </select>
        </div>
      </div>
      <div v-if="formError" class="hint bad">{{ formError }}</div>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="formOpen = false">取消</button>
        <button class="btn btn-pri" type="button" :disabled="saving" @click="save">{{ saving ? '保存中…' : '保存' }}</button>
      </template>
    </ProtoDrawer>
    <ProtoDrawer :open="assetCreateOpen" title="资产登记" width="480px" @close="assetCreateOpen = false">
      <div class="formrow one"><div class="fld"><label>资产编号<i class="req">*</i></label><input v-model="assetForm.assetCode" data-testid="corp-asset-code" /></div></div>
      <div class="formrow one"><div class="fld"><label>名称<i class="req">*</i></label><input v-model="assetForm.assetName" data-testid="corp-asset-name" /></div></div>
      <div class="formrow one"><div class="fld"><label>规格</label><input v-model="assetForm.spec" data-testid="corp-asset-spec" /></div></div>
      <div v-if="kind === 'live'" class="formrow one">
        <div class="fld">
          <label>类型</label>
          <select v-model="assetForm.assetType" data-testid="corp-asset-type">
            <option value="LIVE">直播设备</option>
            <option value="SHOOT">拍摄设备</option>
          </select>
        </div>
      </div>
      <div class="formrow one"><div class="fld"><label>采购日期</label><input v-model="assetForm.purchaseDate" type="date" data-testid="corp-asset-purchase" /></div></div>
      <div class="formrow one">
        <div class="fld">
          <label>实名人</label>
          <select v-model="assetForm.realnameId" data-testid="corp-asset-realname">
            <option value="">不挂接</option>
            <option v-for="person in persons" :key="person.id" :value="String(person.id)">{{ person.realName }}</option>
          </select>
        </div>
      </div>
      <div class="formrow one">
        <div class="fld">
          <label>上级资产编号</label>
          <input v-model="assetForm.parentAssetCode" data-testid="corp-asset-parent" placeholder="挂到已挂实名人的资产下" />
        </div>
      </div>
      <p class="hint">正向穿透从实名人向下最多 5 层。第 6 层可以登记，查询时返回 1013。</p>
      <div v-if="formError" class="hint bad">{{ formError }}</div>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="assetCreateOpen = false">取消</button>
        <button class="btn btn-pri" type="button" data-testid="corp-asset-save" :disabled="saving" @click="saveAsset">{{ saving ? '保存中…' : '保存' }}</button>
      </template>
    </ProtoDrawer>
    <ProtoDrawer :open="checkoutOpen" title="领用" width="480px" @close="checkoutOpen = false">
      <p class="hint">{{ activeAsset?.assetCode }} · {{ activeAsset?.assetName }}</p>
      <div class="formrow one">
        <div class="fld">
          <label>责任人<i class="req">*</i></label>
          <select v-model="assetForm.ownerUserId" data-testid="corp-asset-owner">
            <option value="">请选择本地用户</option>
            <option v-for="user in users" :key="user.id" :value="user.id">{{ user.nickname || user.username }}</option>
          </select>
        </div>
      </div>
      <div class="formrow one"><div class="fld"><label>用途</label><input v-model="assetForm.purpose" data-testid="corp-asset-purpose" /></div></div>
      <div v-if="formError" class="hint bad">{{ formError }}</div>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="checkoutOpen = false">取消</button>
        <button class="btn btn-pri" type="button" data-testid="corp-asset-checkout-save" :disabled="saving" @click="submitCheckout">确认领用</button>
      </template>
    </ProtoDrawer>
    <ProtoDrawer :open="useOpen" title="使用" width="480px" @close="useOpen = false">
      <p class="hint">登记使用后状态仍为在用，之后才能归还。</p>
      <div class="formrow one"><div class="fld"><label>使用说明</label><input v-model="assetForm.remark" data-testid="corp-asset-use-remark" /></div></div>
      <div v-if="formError" class="hint bad">{{ formError }}</div>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="useOpen = false">取消</button>
        <button class="btn btn-pri" type="button" data-testid="corp-asset-use-save" :disabled="saving" @click="submitUse">确认使用</button>
      </template>
    </ProtoDrawer>
    <ProtoDrawer :open="returnOpen" title="归还" width="480px" @close="returnOpen = false">
      <div class="formrow one"><div class="fld"><label>说明</label><input v-model="assetForm.remark" data-testid="corp-asset-return-remark" /></div></div>
      <div v-if="formError" class="hint bad">{{ formError }}</div>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="returnOpen = false">取消</button>
        <button class="btn btn-pri" type="button" data-testid="corp-asset-return-save" :disabled="saving" @click="submitReturn">确认归还</button>
      </template>
    </ProtoDrawer>
    <ProtoDrawer :open="scrapOpen" title="报废" width="480px" @close="scrapOpen = false">
      <div class="formrow one"><div class="fld"><label>报废原因<i class="req">*</i></label><input v-model="assetForm.remark" data-testid="corp-asset-scrap-reason" /></div></div>
      <div v-if="formError" class="hint bad">{{ formError }}</div>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="scrapOpen = false">取消</button>
        <button class="btn btn-pri" type="button" data-testid="corp-asset-scrap-save" :disabled="saving" @click="submitScrap">确认报废</button>
      </template>
    </ProtoDrawer>
    <ProtoDrawer :open="assetDetailOpen" title="资产详情" width="560px" @close="assetDetailOpen = false">
      <div v-if="assetDetail" class="formrow one">
        <div class="fld"><label>编号</label><div>{{ assetDetail.assetCode }}</div></div>
        <div class="fld"><label>名称</label><div>{{ assetDetail.assetName }}</div></div>
        <div class="fld"><label>状态</label><div data-testid="corp-asset-detail-status">{{ statusLabel(String(assetDetail.status || '')) }}</div></div>
        <div class="fld"><label>责任人</label><div>{{ assetDetail.ownerName || '—' }}</div></div>
      </div>
      <table data-testid="corp-asset-timeline">
        <thead><tr><th>事件</th><th>状态</th><th>说明</th></tr></thead>
        <tbody>
          <tr v-for="event in timeline" :key="String(event.id)">
            <td>{{ eventLabel(String(event.eventType || '')) }}</td>
            <td>{{ statusLabel(String(event.toStatus || '')) }}</td>
            <td>{{ event.remark || '—' }}</td>
          </tr>
        </tbody>
      </table>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="assetDetailOpen = false">关闭</button>
      </template>
    </ProtoDrawer>
    <ProtoDrawer v-if="kind === 'office'" :open="forwardOpen" title="正向穿透" width="560px" @close="forwardOpen = false">
      <div class="formrow one">
        <div class="fld">
          <label>实名人</label>
          <select v-model="forwardRealnameId" data-testid="asset-forward-realname">
            <option value="">请选择</option>
            <option v-for="person in persons" :key="person.id" :value="String(person.id)">{{ person.realName }}</option>
          </select>
        </div>
      </div>
      <button class="btn btn-pri btn-sm" type="button" data-testid="asset-forward-query" @click="queryForwardPerson">查询</button>
      <p v-if="forwardHint" class="hint">{{ forwardHint }}</p>
      <p v-if="forwardError" class="hint bad" data-testid="asset-forward-error">{{ forwardError }}</p>
      <ol v-if="forwardNodes.length" data-testid="asset-forward-chain">
        <li v-for="node in forwardNodes" :key="String(node.id)" data-testid="asset-forward-node">
          {{ node.layer === 'PERSON' ? '实名人' : `第${node.level}层` }} · {{ node.label }}
        </li>
      </ol>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="forwardOpen = false">关闭</button>
      </template>
    </ProtoDrawer>
    <ProtoDrawer v-if="kind === 'office'" :open="reverseOpen" title="反向穿透" width="560px" @close="reverseOpen = false">
      <p class="hint">{{ reverseHint }}</p>
      <p v-if="reverseError" class="hint bad" data-testid="asset-reverse-error">{{ reverseError }}</p>
      <table v-else data-testid="asset-reverse-holders">
        <thead><tr><th>使用人</th><th>状态</th></tr></thead>
        <tbody>
          <tr v-if="!reverseHolders.length">
            <td colspan="2">尚无使用人</td>
          </tr>
          <tr v-for="(holder, index) in reverseHolders" :key="index" data-testid="asset-reverse-row">
            <td data-testid="asset-reverse-user">{{ holder.userName || '—' }}</td>
            <td data-testid="asset-reverse-status">{{ holder.statusLabel }}</td>
          </tr>
        </tbody>
      </table>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="reverseOpen = false">关闭</button>
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
type UserOpt = { id: string; username: string; nickname: string }
type PersonOpt = { id: number; realName: string }

const route = useRoute()
const kind = computed(() => String(route.params.kind || 'office'))
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
const formOpen = ref(false)
const saving = ref(false)
const formError = ref('')
const users = ref<UserOpt[]>([])
const phoneStatus = ref<Opt[]>([])
const phoneTypes = ref<Opt[]>([])
const assetTypes = ref<Opt[]>([])
const assetStatuses = ref<Opt[]>([])
const assetCreateOpen = ref(false)
const checkoutOpen = ref(false)
const useOpen = ref(false)
const returnOpen = ref(false)
const scrapOpen = ref(false)
const assetDetailOpen = ref(false)
const forwardOpen = ref(false)
const reverseOpen = ref(false)
const forwardRealnameId = ref('')
const forwardNodes = ref<Row[]>([])
const forwardError = ref('')
const forwardHint = ref('')
const reverseHolders = ref<Row[]>([])
const reverseError = ref('')
const reverseHint = ref('')
const persons = ref<PersonOpt[]>([])
const activeAsset = ref<Row | null>(null)
const assetDetail = ref<Row | null>(null)
const timeline = ref<Row[]>([])
const form = reactive({
  phoneNumber: '',
  phoneCode: '',
  phoneModel: '',
  deviceNumber: '',
  keeperId: '',
  phoneType: '',
  status: 'IN_USE',
})
const assetForm = reactive({
  assetCode: '',
  assetName: '',
  spec: '',
  assetType: 'OFFICE',
  purchaseDate: '',
  ownerUserId: '',
  purpose: '',
  remark: '',
  realnameId: '',
  parentAssetCode: '',
})

const fallbackStatus: Opt[] = [
  { value: 'PENDING_REVIEW', label: '待审核' },
  { value: 'IN_USE', label: '在用' },
  { value: 'RETURNED', label: '已归还' },
  { value: 'SCRAPPED', label: '已报废' },
]
const fallbackType: Opt[] = [
  { value: 'OFFICE', label: '办公设备' },
  { value: 'LIVE', label: '直播设备' },
  { value: 'SHOOT', label: '拍摄设备' },
  { value: 'DIGITAL', label: '数码设备' },
]
const eventLabels: Record<string, string> = {
  REGISTER: '登记',
  CHECKOUT: '领用',
  USE: '使用',
  RETURN: '归还',
  SCRAP: '报废',
}

const specs: Record<string, {
  title: string
  sub: string
  placeholder: string
  empty: string
  emptyHint: string
  hint: string
  columns: string[]
  keys: string[]
}> = {
  office: {
    title: '办公设备管理',
    sub: 'CORP-D · 领用 → 使用 → 归还 → 报废 · 实名人穿透',
    placeholder: '资产编号 / 名称',
    empty: '没有办公设备',
    emptyHint: '点「资产登记」写入台账，再按领用、使用、归还、报废流转。',
    hint: 'GET /corp/device/office/page 读取 assetType=OFFICE。正向穿透：实名人 → 资产，最多 5 层，超出返回 1013。反向穿透：资产 → 使用人，区分在用 / 已归还 / 已报废。',
    columns: ['编号', '名称', '类型', '规格', '状态', '责任人'],
    keys: ['assetCode', 'assetName', 'assetType', 'spec', 'status', 'ownerName'],
  },
  live: {
    title: '直播设备管理',
    sub: 'CORP-D · 直播与拍摄设备同一台账',
    placeholder: '资产编号 / 名称',
    empty: '没有直播设备',
    emptyHint: '登记时类型选直播设备或拍摄设备。流转与办公设备相同。',
    hint: 'GET /corp/device/live/page 合并 assetType=LIVE 与 SHOOT。',
    columns: ['编号', '名称', '类型', '规格', '状态', '责任人'],
    keys: ['assetCode', 'assetName', 'assetType', 'spec', 'status', 'ownerName'],
  },
  phone: {
    title: '手机设备管理',
    sub: 'MASTER-003 · 保管人只选本地用户 · 号码脱敏',
    placeholder: '设备编号 / 型号',
    empty: '没有手机',
    emptyHint: '可以新建。列表不显示实名人，手机资产没有这一列。',
    hint: 'POST /master/phone。CORP 的手机列表是同一份查询。',
    columns: ['号码', '编号', '型号', '类型', '保管人', '状态'],
    keys: ['phoneNumber', 'deviceNumber', 'phoneModel', 'phoneType', 'keeperName', 'status'],
  },
}

const meta = computed(() => specs[kind.value] || specs.office)
const assetStatusOptions = computed(() => (assetStatuses.value.length ? assetStatuses.value : fallbackStatus))
const pageCount = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))
const pageList = computed(() => {
  const end = Math.min(pageCount.value, Math.max(pageNo.value + 2, 5))
  const start = Math.max(1, end - 4)
  const list: number[] = []
  for (let i = start; i <= Math.min(pageCount.value, start + 4); i += 1) list.push(i)
  return list
})

const labels: Record<string, string> = {
  phoneNumber: '号码',
  deviceNumber: '编号',
  phoneModel: '型号',
  phoneType: '类型',
  keeperName: '保管人',
  status: '状态',
  assetCode: '编号',
  assetName: '名称',
  assetType: '类型',
  spec: '规格',
  ownerName: '责任人',
}

function labelOf(key: string) {
  return labels[key] || key
}

function statusLabel(value: string) {
  return assetStatusOptions.value.find((item) => item.value === value)?.label || value
}

function typeLabel(value: string) {
  const dict = assetTypes.value.length ? assetTypes.value : fallbackType
  return dict.find((item) => item.value === value)?.label || value
}

function eventLabel(value: string) {
  return eventLabels[value] || value
}

function show(row: Row, key: string) {
  const value = row[key]
  if (value === undefined || value === null || value === '') return '—'
  if (key === 'status' && kind.value === 'phone') {
    return phoneStatus.value.find((item) => item.value === value)?.label || String(value)
  }
  if (key === 'status') return statusLabel(String(value))
  if (key === 'phoneType') return phoneTypes.value.find((item) => item.value === value)?.label || String(value)
  if (key === 'assetType') return typeLabel(String(value))
  return String(value)
}

async function loadDict(dictType: string) {
  const res = await http.get('/system/dict-data/list', { params: { dictType } })
  return asList(res.data?.data)
    .filter((row) => row.status === 'ENABLED')
    .map((row) => ({ value: String(row.dictValue), label: String(row.dictLabel) }))
}

async function preparePhone() {
  const [st, types, userPage] = await Promise.all([
    loadDict('dict_phone_status'),
    loadDict('dict_phone_type'),
    http.get('/system/user/page', { params: { pageNo: 1, pageSize: 100 } }),
  ])
  phoneStatus.value = st
  phoneTypes.value = types
  users.value = asList(userPage.data?.data) as unknown as UserOpt[]
}

function bizError(error: unknown) {
  if (error && typeof error === 'object' && 'code' in error) {
    const body = error as { code?: number; msg?: string }
    if (body.code && body.code !== 0) return `${body.code} ${body.msg || ''}`.trim()
  }
  return errorMessage(error)
}

async function prepareAsset() {
  const [types, statuses, userPage, personPage] = await Promise.all([
    loadDict('dict_asset_type').catch(() => fallbackType),
    loadDict('dict_asset_status').catch(() => fallbackStatus),
    http.get('/system/user/page', { params: { pageNo: 1, pageSize: 100 } }),
    http.get('/corp/resource/realname/page', { params: { pageNo: 1, pageSize: 100, status: 'ENABLED' } }).catch(() => null),
  ])
  assetTypes.value = types
  assetStatuses.value = statuses
  users.value = asList(userPage.data?.data) as unknown as UserOpt[]
  persons.value = personPage ? (asList(personPage.data?.data) as unknown as PersonOpt[]) : []
}

function today() {
  const date = new Date()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${date.getFullYear()}-${month}-${day}`
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const query: Record<string, string | number> = { pageNo: pageNo.value, pageSize: pageSize.value }
    const text = keyword.value.trim()
    if (kind.value === 'phone' && text) {
      if (/^[A-Za-z0-9-]+$/.test(text) && !/^\d{11}$/.test(text)) query.deviceNumber = text
      else query.phoneModel = text
    }
    if (kind.value !== 'phone' && text) query.keyword = text
    if (status.value) query.status = status.value
    const url = kind.value === 'phone' ? '/corp/device/phone/page' : `/corp/device/${kind.value}/page`
    const res = await http.get(url, { params: query })
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
  detailOpen.value = true
  detail.value = null
  try {
    const res = await http.get(`/corp/device/phone/${row.id}`)
    detail.value = res.data?.data
  } catch (e: unknown) {
    detail.value = { status: errorMessage(e) }
  }
}

function openCreate() {
  form.phoneNumber = ''
  form.phoneCode = ''
  form.phoneModel = ''
  form.deviceNumber = ''
  form.keeperId = users.value[0]?.id || ''
  form.phoneType = ''
  form.status = 'IN_USE'
  formError.value = ''
  formOpen.value = true
}

async function save() {
  saving.value = true
  formError.value = ''
  try {
    await http.post('/master/phone', {
      phoneNumber: form.phoneNumber.trim(),
      phoneCode: form.phoneCode,
      phoneModel: form.phoneModel,
      deviceNumber: form.deviceNumber,
      keeperId: Number(form.keeperId),
      phoneType: form.phoneType || undefined,
      status: form.status,
    })
    formOpen.value = false
    await load()
  } catch (e: unknown) {
    formError.value = errorMessage(e)
  } finally {
    saving.value = false
  }
}

function closeAssetDrawers() {
  assetCreateOpen.value = false
  checkoutOpen.value = false
  useOpen.value = false
  returnOpen.value = false
  scrapOpen.value = false
  forwardOpen.value = false
  reverseOpen.value = false
}

function openAssetCreate() {
  closeAssetDrawers()
  assetForm.assetCode = ''
  assetForm.assetName = ''
  assetForm.spec = ''
  assetForm.assetType = kind.value === 'live' ? 'LIVE' : 'OFFICE'
  assetForm.purchaseDate = today()
  assetForm.realnameId = ''
  assetForm.parentAssetCode = ''
  formError.value = ''
  assetCreateOpen.value = true
}

function openCheckout(row: Row) {
  closeAssetDrawers()
  activeAsset.value = row
  assetForm.ownerUserId = users.value[0]?.id || ''
  assetForm.purpose = ''
  formError.value = ''
  checkoutOpen.value = true
}

function openUse(row: Row) {
  closeAssetDrawers()
  activeAsset.value = row
  assetForm.remark = '现场使用'
  formError.value = ''
  useOpen.value = true
}

function openReturn(row: Row) {
  closeAssetDrawers()
  activeAsset.value = row
  assetForm.remark = '归还入库'
  formError.value = ''
  returnOpen.value = true
}

function openScrap(row: Row) {
  closeAssetDrawers()
  activeAsset.value = row
  assetForm.remark = ''
  formError.value = ''
  scrapOpen.value = true
}

async function openAssetDetail(row: Row) {
  assetDetailOpen.value = true
  assetDetail.value = null
  timeline.value = []
  try {
    const res = await http.get(`/asset/ledger/${row.id}`)
    assetDetail.value = res.data?.data
    timeline.value = (res.data?.data?.timeline || []) as Row[]
  } catch (e: unknown) {
    assetDetail.value = { assetCode: errorMessage(e), assetName: '', status: '' }
  }
}

async function saveAsset() {
  saving.value = true
  formError.value = ''
  try {
    const payload: Record<string, unknown> = {
      assetCode: assetForm.assetCode.trim(),
      assetName: assetForm.assetName.trim(),
      assetType: kind.value === 'live' ? assetForm.assetType : 'OFFICE',
      spec: assetForm.spec,
      purchaseDate: assetForm.purchaseDate || undefined,
    }
    const parent = assetForm.parentAssetCode.trim()
    if (parent) payload.parentAssetCode = parent
    else if (assetForm.realnameId) payload.realnameId = Number(assetForm.realnameId)
    await http.post('/asset/ledger', payload)
    assetCreateOpen.value = false
    keyword.value = assetForm.assetCode.trim()
    await load()
  } catch (e: unknown) {
    formError.value = bizError(e)
  } finally {
    saving.value = false
  }
}

async function loadTrace(url: string, params?: Record<string, unknown>) {
  try {
    const res = await http.get(url, { params })
    forwardNodes.value = (res.data?.data?.nodes || []) as Row[]
    forwardError.value = ''
  } catch (e: unknown) {
    forwardNodes.value = []
    forwardError.value = bizError(e)
  }
}

function openForwardPerson() {
  closeAssetDrawers()
  forwardOpen.value = true
  forwardNodes.value = []
  forwardError.value = ''
  forwardHint.value = '实名人 → 资产，最多 5 层'
  forwardRealnameId.value = persons.value[0] ? String(persons.value[0].id) : ''
}

async function queryForwardPerson() {
  const id = Number(forwardRealnameId.value)
  if (!id) {
    forwardError.value = '请选择实名人'
    forwardNodes.value = []
    return
  }
  forwardHint.value = '实名人 → 资产，最多 5 层'
  await loadTrace('/asset/forward/trace/0', { realnameId: id })
}

async function openForwardAsset(row: Row) {
  closeAssetDrawers()
  forwardOpen.value = true
  forwardNodes.value = []
  forwardError.value = ''
  forwardHint.value = `${row.assetCode || ''} 的链路（实名人 → 资产）`
  forwardRealnameId.value = ''
  await loadTrace(`/asset/forward/trace/${row.id}`)
}

async function openReverse(row: Row) {
  closeAssetDrawers()
  reverseOpen.value = true
  reverseHolders.value = []
  reverseError.value = ''
  reverseHint.value = `${row.assetCode || ''} → 使用人（在用 / 已归还 / 已报废）`
  try {
    const res = await http.get(`/asset/ledger/${row.id}`)
    reverseHolders.value = (res.data?.data?.holders || []) as Row[]
  } catch (e: unknown) {
    reverseError.value = bizError(e)
  }
}

async function postAction(path: string, payload: Record<string, unknown>, close: () => void) {
  if (!activeAsset.value) return
  saving.value = true
  formError.value = ''
  try {
    await http.post(`/asset/ledger/${activeAsset.value.id}${path}`, payload)
    close()
    await load()
  } catch (e: unknown) {
    formError.value = errorMessage(e)
  } finally {
    saving.value = false
  }
}

function submitCheckout() {
  postAction('/checkout', { ownerUserId: Number(assetForm.ownerUserId), purpose: assetForm.purpose }, () => {
    checkoutOpen.value = false
  })
}

function submitUse() {
  postAction('/use', { remark: assetForm.remark }, () => {
    useOpen.value = false
  })
}

function submitReturn() {
  postAction('/return', { remark: assetForm.remark }, () => {
    returnOpen.value = false
  })
}

function submitScrap() {
  postAction('/scrap', { remark: assetForm.remark }, () => {
    scrapOpen.value = false
  })
}

watch(kind, async () => {
  keyword.value = ''
  status.value = ''
  pageNo.value = 1
  detailOpen.value = false
  formOpen.value = false
  closeAssetDrawers()
  assetDetailOpen.value = false
  if (kind.value === 'phone' && !phoneStatus.value.length) {
    try {
      await preparePhone()
    } catch {
      /* 列表仍可打开 */
    }
  }
  if (kind.value !== 'phone' && !users.value.length) {
    try {
      await prepareAsset()
    } catch {
      /* 列表仍可打开 */
    }
  }
  load()
})

onMounted(async () => {
  if (kind.value === 'phone') {
    try {
      await preparePhone()
    } catch {
      /* 列表仍可打开 */
    }
  } else {
    try {
      await prepareAsset()
    } catch {
      /* 列表仍可打开 */
    }
  }
  await load()
})
</script>
