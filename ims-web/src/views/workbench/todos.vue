<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>待办中心</h1>
        <div class="sub">AUTH-004 · 按类型、状态和标题筛选</div>
      </div>
      <router-link class="btn btn-sec btn-sm" to="/ims/workbench">工作台首页</router-link>
    </div>
    <div class="cattabs" data-testid="todo-type-tabs">
      <button
        v-for="tab in typeTabs"
        :key="tab.value || 'all'"
        class="cattab"
        :class="{ on: filters.taskType === tab.value }"
        type="button"
        :data-testid="tab.testId"
        @click="setType(tab.value)"
      >
        {{ tab.label }}
      </button>
    </div>
    <form class="qbar" @submit.prevent="search">
      <input v-model="filters.keyword" data-testid="todo-keyword" placeholder="标题 / 摘要" style="width: 180px" />
      <select v-model="filters.status" data-testid="todo-status" style="width: 120px">
        <option value="">全部状态</option>
        <option value="PENDING">待处理</option>
        <option value="DONE">已处理</option>
        <option value="EXPIRED">已过期</option>
      </select>
      <select :value="filters.taskType" style="width: 140px" data-testid="todo-task-type" @change="onTypeSelect">
        <option v-for="item in typeOptions" :key="item.value || 'all-types'" :value="item.value">{{ item.label }}</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit" data-testid="todo-search">查询</button>
    </form>
    <div class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>标题</th>
              <th>类型</th>
              <th>截止</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="5"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!rows.length">
              <td colspan="5">
                <div class="empty" data-testid="todo-empty">
                  <div class="et">{{ error || emptyTitle }}</div>
                  <div class="es">{{ emptyHint }}</div>
                </div>
              </td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.id" :data-testid="'todo-row'" :style="row.overdue ? 'background:#fff4f2' : ''">
              <td>{{ row.title }}</td>
              <td><span class="tag" :data-testid="'todo-type-' + row.taskType">{{ typeLabel(row.taskType) }}</span></td>
              <td class="mono">
                {{ row.deadline?.slice(0, 16) || '—' }}
                <span v-if="row.overdue" style="color: #d93025">逾期</span>
              </td>
              <td>{{ statusLabel(row) }}</td>
              <td>
                <router-link
                  v-if="row.taskType === 'exam'"
                  class="btn btn-sec btn-sm"
                  to="/ims/perf/exam"
                  data-testid="todo-exam-entry"
                >
                  去考试
                </router-link>
                <button
                  v-if="row.status === 'PENDING' && transferTodoPath(row)"
                  class="btn btn-pri btn-sm"
                  type="button"
                  data-testid="wb-center-acct-transfer-go"
                  @click="router.push(transferTodoPath(row))"
                >
                  去处理
                </button>
                <button
                  v-else-if="row.status === 'PENDING'"
                  class="btn btn-sec btn-sm"
                  type="button"
                  @click="done(row.id)"
                >
                  完成
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="pager">
        <span class="pg-total">共 {{ total }} 条</span>
        <span class="pg-sp"></span>
        <button class="pg-n" :class="{ dis: pageNo <= 1 }" type="button" @click="prev">上一页</button>
        <button class="pg-n" :class="{ dis: pageNo * pageSize >= total }" type="button" @click="next">下一页</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { http } from '../../api/http'

type Row = {
  id: number
  title: string
  taskType: string
  refId?: number
  content?: string
  deadline?: string
  status: string
  overdue?: boolean
}

const router = useRouter()

function platformSlug(platform: string) {
  const map: Record<string, string> = {
    DOUYIN: 'douyin',
    KUAISHOU: 'kuaishou',
    XIAOHONGSHU: 'xiaohongshu',
    WECHAT_OFFICIAL: 'wechat-official',
    WECHAT_CHANNELS: 'wechat-channels',
  }
  return map[platform.trim().toUpperCase()] || 'douyin'
}

function transferTodoPath(row: Row) {
  if (row.taskType !== 'acct_transfer' || !row.refId) return ''
  const platform = String(row.content || '').split('|')[0] || 'DOUYIN'
  return `/ims/corp/account/${platformSlug(platform)}?transferId=${row.refId}`
}

const typeTabs = [
  { value: '', label: '全部', testId: 'todo-tab-all' },
  { value: 'approval', label: '审批', testId: 'todo-tab-approval' },
  { value: 'return', label: '归还', testId: 'todo-tab-return' },
  { value: 'review', label: '审核', testId: 'todo-tab-review' },
  { value: 'cert_expire', label: '证件预警', testId: 'todo-tab-cert' },
  { value: 'live_alarm', label: '直播告警', testId: 'todo-tab-live' },
  { value: 'exam', label: '考试', testId: 'todo-tab-exam' },
]

const extraTypeOptions = [
  { value: 'supplement', label: '补录' },
  { value: 'recharge_verify', label: '充值核对' },
  { value: 'acct_transfer', label: '账号流转' },
]

const typeOptions = [
  { value: '', label: '全部类型' },
  ...typeTabs.filter((tab) => tab.value).map((tab) => ({ value: tab.value, label: tab.label })),
  ...extraTypeOptions,
]

const typeNames: Record<string, string> = {
  approval: '审批',
  return: '归还',
  review: '审核',
  cert_expire: '证件预警',
  live_alarm: '直播告警',
  supplement: '补录',
  recharge_verify: '充值核对',
  exam: '考试',
  acct_transfer: '账号流转',
}

const rows = ref<Row[]>([])
const loading = ref(false)
const error = ref('')
const total = ref(0)
const pageNo = ref(1)
const pageSize = 20
const filters = reactive({ status: 'PENDING', taskType: '', keyword: '' })

const emptyTitle = computed(() => {
  if (filters.taskType) return '该类型下暂无待办'
  if (filters.status === 'EXPIRED') return '没有已过期待办'
  if (filters.status === 'DONE' && filters.keyword.trim()) return '没有匹配的已处理待办'
  if (filters.status === 'DONE') return '没有已处理待办'
  if (filters.keyword.trim() && filters.status === 'PENDING') return '没有匹配的待处理待办'
  if (filters.keyword.trim()) return '没有匹配的待办'
  return '暂无待办'
})

const emptyHint = computed(() => {
  if (filters.status === 'DONE' && filters.keyword.trim() && !filters.taskType) return '已处理列表里没有这个标题或摘要。'
  if (filters.status === 'DONE' && !filters.taskType) return '已关闭或已完成的待办会出现在这里。'
  if (filters.keyword.trim() && filters.status === 'PENDING' && !filters.taskType) return '待处理列表里没有这个标题或摘要。'
  if (filters.taskType || filters.keyword.trim() || filters.status === 'EXPIRED') return '换一个类型、状态或关键词再查。'
  return '待处理事项会出现在这里。'
})

function typeLabel(value: string) {
  return typeNames[value] || value || '—'
}

function statusLabel(row: Row) {
  if (row.status === 'EXPIRED' || row.overdue) return '已过期'
  if (row.status === 'DONE') return '已处理'
  if (row.status === 'PENDING') return '待处理'
  return row.status || '—'
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const params: Record<string, unknown> = { pageNo: pageNo.value, pageSize }
    if (filters.status) params.status = filters.status
    if (filters.taskType) params.taskType = filters.taskType
    if (filters.keyword.trim()) params.keyword = filters.keyword.trim()
    const res = await http.get('/auth/workbench/todos', { params })
    if (res.data.code !== 0) {
      error.value = res.data.msg || '加载失败'
      rows.value = []
      total.value = 0
      return
    }
    rows.value = res.data.data?.list || []
    total.value = Number(res.data.data?.total || 0)
  } catch {
    error.value = '网络错误'
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

function setType(value: string) {
  filters.taskType = value
  search()
}

function onTypeSelect(event: Event) {
  const value = (event.target as HTMLSelectElement).value
  setType(value)
}

function prev() {
  if (pageNo.value <= 1) return
  pageNo.value -= 1
  load()
}

function next() {
  if (pageNo.value * pageSize >= total.value) return
  pageNo.value += 1
  load()
}

async function done(id: number) {
  await http.put(`/auth/workbench/todos/${id}`, { action: 'DONE' })
  await load()
}

onMounted(load)
</script>
