<template>
  <div data-testid="topic-gantt">
    <form class="qbar" @submit.prevent="load">
      <label>计划发布日</label>
      <input v-model="from" type="date" data-testid="topic-gantt-from" />
      <span class="to">至</span>
      <input v-model="to" type="date" data-testid="topic-gantt-to" />
      <input
        v-model="accountId"
        type="text"
        inputmode="numeric"
        placeholder="发布账号 ID"
        style="width: 140px"
        data-testid="topic-gantt-account"
      />
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit" data-testid="topic-gantt-query" :disabled="loading">查询</button>
    </form>
    <p v-if="error" class="hint bad" data-testid="topic-gantt-error">
      {{ error }}
      <button
        v-if="errorRetry"
        class="btn btn-sec btn-sm"
        type="button"
        data-testid="topic-gantt-retry"
        @click="load"
      >重试</button>
    </p>
    <p v-else-if="conflictCount" class="hint warn" data-testid="topic-gantt-conflict-summary">
      {{ conflictCount }} 条选题同账号同日超量，仅提示，不阻断排期
    </p>
    <p v-if="!loading && !error && items.length" class="hint" data-testid="topic-gantt-legend">
      蓝条为计划发布日，黄底为同账号同日超量。
    </p>
    <div class="tbl-block">
      <div class="tbl-wrap gantt-scroll">
        <table class="gantt" data-testid="topic-gantt-board">
          <thead>
            <tr>
              <th class="sticky">选题</th>
              <th v-for="day in days" :key="day" class="day">{{ day.slice(5) }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td :colspan="days.length + 1"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!items.length && !error">
              <td :colspan="Math.max(days.length + 1, 1)">
                <div class="empty" data-testid="topic-gantt-empty" :data-reason="emptyReason">
                  <div class="et">{{ emptyText }}</div>
                </div>
              </td>
            </tr>
            <tr
              v-for="item in items"
              v-else
              :key="item.topicNo"
              data-testid="topic-gantt-row"
              :data-topic="item.topicNo"
            >
              <td class="sticky">
                <b>{{ item.title }}</b>
                <div class="mono">{{ item.topicNo }}</div>
                <div class="meta">
                  {{ statusLabel(item.topicStatus) }}
                  <span v-if="item.sopName"> · {{ item.sopName }}</span>
                </div>
                <div v-if="item.conflictHint" class="hint warn" data-testid="topic-gantt-conflict">{{ item.conflictHint }}</div>
              </td>
              <td
                v-for="day in days"
                :key="day"
                class="day"
                :data-date="day"
                :class="cellClass(item, day)"
                :data-testid="item.planPublishDate === day ? 'topic-gantt-mark' : undefined"
                :title="item.planPublishDate === day ? item.title : ''"
              >
                <span v-if="item.planPublishDate === day" class="bar" />
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { errorMessage, http } from '../../api/http'

type GanttItem = {
  topicNo: string
  title: string
  planPublishDate: string
  topicStatus: string
  sopName?: string | null
  conflictHint?: string | null
}

const STATUS_LABEL: Record<string, string> = {
  PENDING_REVIEW: '待评审',
  APPROVED_PROJECT: '已立项',
  REJECTED: '落选',
  CANCELLED: '已取消',
}

const MAX_DAYS = 62

const from = ref('')
const to = ref('')
const accountId = ref('')
const items = ref<GanttItem[]>([])
const loading = ref(false)
const error = ref('')
const errorRetry = ref(false)

const days = computed(() => enumerate(from.value, to.value))
const conflictCount = computed(() => items.value.filter((item) => item.conflictHint).length)
const accountFilled = computed(() => String(accountId.value ?? '').trim() !== '')
const emptyReason = computed(() => {
  if (!days.value.length) return 'unset'
  return accountFilled.value ? 'account' : 'range'
})
const emptyText = computed(() => {
  if (!days.value.length) return '请选择计划发布日区间'
  if (accountFilled.value) return '该账号在此区间暂无排期'
  return '该区间暂无排期'
})

function statusLabel(status: string) {
  return STATUS_LABEL[status] || status
}

function pad(value: number) {
  return String(value).padStart(2, '0')
}

function localDay(date: Date) {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

function monthRange() {
  const now = new Date()
  const start = new Date(now.getFullYear(), now.getMonth(), 1)
  const end = new Date(now.getFullYear(), now.getMonth() + 1, 0)
  return [localDay(start), localDay(end)]
}

function enumerate(start: string, end: string) {
  if (!start || !end || start > end) return []
  const cursor = new Date(`${start}T00:00:00`)
  const last = new Date(`${end}T00:00:00`)
  if (Number.isNaN(cursor.getTime()) || Number.isNaN(last.getTime())) return []
  const out: string[] = []
  while (cursor <= last && out.length < MAX_DAYS) {
    out.push(localDay(cursor))
    cursor.setDate(cursor.getDate() + 1)
  }
  return out
}

function spanTooWide(start: string, end: string) {
  if (!start || !end || start > end) return false
  const cursor = new Date(`${start}T00:00:00`)
  const last = new Date(`${end}T00:00:00`)
  const diff = Math.round((last.getTime() - cursor.getTime()) / 86_400_000) + 1
  return diff > MAX_DAYS
}

function cellClass(item: GanttItem, day: string) {
  if (item.planPublishDate !== day) return {}
  return item.conflictHint ? { conflict: true } : { mark: true }
}

function formatBiz(err: unknown) {
  if (err && typeof err === 'object' && 'code' in err) {
    const body = err as { code?: number; msg?: string }
    if (body.code) return `${body.code} ${body.msg || '操作失败'}`
  }
  return errorMessage(err)
}

function invalidAccount(value: string) {
  const text = value.trim()
  if (!text) return false
  return !/^[1-9]\d*$/.test(text)
}

async function load() {
  error.value = ''
  errorRetry.value = false
  if (!from.value || !to.value || from.value > to.value) {
    error.value = '请选择有效的计划发布日区间'
    items.value = []
    return
  }
  if (spanTooWide(from.value, to.value)) {
    error.value = '区间超过 62 天，请缩小后再看甘特'
    items.value = []
    return
  }
  if (invalidAccount(String(accountId.value ?? ''))) {
    error.value = '请填写有效的发布账号 ID'
    items.value = []
    return
  }
  loading.value = true
  try {
    const params = new URLSearchParams()
    params.append('timeRange', from.value)
    params.append('timeRange', to.value)
    const account = String(accountId.value ?? '').trim()
    if (account) params.append('accountId', account)
    const { data } = await http.get('/content/topic/gantt', { params })
    items.value = data.data.items || []
  } catch (e) {
    error.value = formatBiz(e)
    errorRetry.value = true
    items.value = []
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  const [start, end] = monthRange()
  from.value = start
  to.value = end
  load()
})
</script>

<style scoped>
.to {
  font-size: 12px;
  color: var(--text2);
}
.hint.warn {
  color: #9a6700;
}
.hint .btn {
  margin-left: 8px;
}
.gantt-scroll {
  overflow-x: auto;
}
.gantt {
  border-collapse: separate;
  border-spacing: 0;
  min-width: 100%;
}
.gantt th,
.gantt td {
  border-bottom: 1px solid var(--line);
  border-right: 1px solid var(--line);
  vertical-align: middle;
}
.gantt .sticky {
  position: sticky;
  left: 0;
  z-index: 1;
  background: #fff;
  min-width: 200px;
  text-align: left;
}
.gantt .day {
  min-width: 36px;
  width: 36px;
  text-align: center;
  font-size: 11px;
  color: var(--text2);
  padding: 6px 2px;
}
.gantt .meta {
  font-size: 12px;
  color: var(--text2);
  margin-top: 2px;
}
.gantt td.mark {
  background: rgba(0, 113, 227, 0.16);
}
.gantt td.conflict {
  background: rgba(255, 204, 0, 0.55);
}
.gantt .bar {
  display: inline-block;
  width: 18px;
  height: 10px;
  border-radius: 3px;
  background: #0071e3;
}
.gantt td.conflict .bar {
  background: #c93400;
}
</style>
