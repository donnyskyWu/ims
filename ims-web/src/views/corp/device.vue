<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>{{ meta.title }}</h1>
        <div class="sub">{{ meta.sub }}</div>
      </div>
      <div v-if="kind === 'phone'" class="acts">
        <button class="btn btn-pri" type="button" @click="openCreate">新建手机</button>
      </div>
    </div>
    <div v-if="kind !== 'phone'" class="hint">{{ meta.block }}</div>
    <form class="qbar" @submit.prevent="search">
      <input v-model="keyword" :placeholder="meta.placeholder" style="width: 180px" />
      <select v-if="kind === 'phone'" v-model="status" style="width: 120px">
        <option value="">全部状态</option>
        <option v-for="item in phoneStatus" :key="item.value" :value="item.value">{{ item.label }}</option>
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
              <th v-if="kind === 'phone'">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td :colspan="meta.columns.length + (kind === 'phone' ? 1 : 0)" style="white-space: normal">
                <div class="empty"><div class="et">加载中</div></div>
              </td>
            </tr>
            <tr v-else-if="!rows.length">
              <td :colspan="meta.columns.length + (kind === 'phone' ? 1 : 0)" style="white-space: normal">
                <div class="empty">
                  <div class="et">{{ error || meta.empty }}</div>
                  <div class="es">{{ meta.emptyHint }}</div>
                </div>
              </td>
            </tr>
            <tr v-for="row in rows" v-else :key="String(row.id)">
              <td v-for="key in meta.keys" :key="key">{{ show(row, key) }}</td>
              <td v-if="kind === 'phone'">
                <button class="btn btn-txt" type="button" @click="openDetail(row)">详情</button>
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
const users = ref<{ id: string; username: string; nickname: string }[]>([])
const phoneStatus = ref<Opt[]>([])
const phoneTypes = ref<Opt[]>([])
const form = reactive({
  phoneNumber: '',
  phoneCode: '',
  phoneModel: '',
  deviceNumber: '',
  keeperId: '',
  phoneType: '',
  status: 'IN_USE',
})

const specs: Record<string, {
  title: string
  sub: string
  placeholder: string
  empty: string
  emptyHint: string
  hint: string
  block: string
  columns: string[]
  keys: string[]
}> = {
  office: {
    title: '办公设备管理',
    sub: 'CORP-D · 台账写入已阻断',
    placeholder: '资产编号',
    empty: '没有办公设备',
    emptyHint: '接口只返回空分页，不能在这里新增或修改。',
    hint: 'GET /corp/device/office/page。资产台账未开放，页面不提供增删改。',
    block: '办公设备增删改已阻断。下面的分页是空列表，不是一笔成功的登记。',
    columns: ['编号', '名称', '类型', '状态', '责任人'],
    keys: ['assetNo', 'name', 'assetType', 'status', 'ownerName'],
  },
  live: {
    title: '直播设备管理',
    sub: 'CORP-D · 直播与拍摄设备写入已阻断',
    placeholder: '资产编号',
    empty: '没有直播设备',
    emptyHint: '接口只返回空分页，不能在这里新增或修改。',
    hint: 'GET /corp/device/live/page。不合并假数据，也不提供保存。',
    block: '直播设备和拍摄设备增删改已阻断。下面的分页是空列表，不是一笔成功的登记。',
    columns: ['编号', '名称', '类型', '状态', '责任人'],
    keys: ['assetNo', 'name', 'assetType', 'status', 'ownerName'],
  },
  phone: {
    title: '手机设备管理',
    sub: 'MASTER-003 · 保管人只选本地用户 · 号码脱敏',
    placeholder: '设备编号 / 型号',
    empty: '没有手机',
    emptyHint: '可以新建。列表不显示实名人，手机资产没有这一列。',
    hint: 'POST /master/phone。CORP 的手机列表是同一份查询。',
    block: '',
    columns: ['号码', '编号', '型号', '类型', '保管人', '状态'],
    keys: ['phoneNumber', 'deviceNumber', 'phoneModel', 'phoneType', 'keeperName', 'status'],
  },
}

const meta = computed(() => specs[kind.value] || specs.office)
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
}

function labelOf(key: string) {
  return labels[key] || key
}

function show(row: Row, key: string) {
  const value = row[key]
  if (value === undefined || value === null || value === '') return '—'
  if (key === 'status') return phoneStatus.value.find((item) => item.value === value)?.label || String(value)
  if (key === 'phoneType') return phoneTypes.value.find((item) => item.value === value)?.label || String(value)
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
  users.value = asList(userPage.data?.data) as unknown as { id: string; username: string; nickname: string }[]
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

watch(kind, async () => {
  keyword.value = ''
  status.value = ''
  pageNo.value = 1
  detailOpen.value = false
  formOpen.value = false
  if (kind.value === 'phone' && !phoneStatus.value.length) {
    try {
      await preparePhone()
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
  }
  await load()
})
</script>
