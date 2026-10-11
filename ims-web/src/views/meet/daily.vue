<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>我的日报</h1>
        <div class="sub">MEET-001 · 三段式日报 · 与 09 数据上报分离</div>
      </div>
      <div class="acts">
        <button class="btn btn-pri btn-sm" type="button" @click="goSubmit">填写今日日报</button>
      </div>
    </div>
    <p class="hint" style="margin-bottom: 10px">
      截止 {{ templateInfo.deadlineTime || '22:00' }} · 已提交后正文只读，修改走补充说明（1112）。
    </p>
    <form class="qbar" @submit.prevent="loadList">
      <input v-model="filters.dateFrom" type="date" style="width: 140px" />
      <input v-model="filters.dateTo" type="date" style="width: 140px" />
      <select v-model="filters.reportType" style="width: 120px">
        <option value="">全部类型</option>
        <option value="LIVE">直播</option>
        <option value="SHORT_VIDEO">短视频</option>
        <option value="OPS">运营</option>
        <option value="ADMIN">行政</option>
      </select>
      <select v-model="filters.submitStatus" style="width: 120px">
        <option value="">全部状态</option>
        <option value="SUBMITTED">已提交</option>
        <option value="DRAFT">草稿</option>
        <option value="SUPPLEMENT">已补交</option>
        <option value="LATE">迟交</option>
      </select>
      <select v-model="filters.reviewState" style="width: 120px">
        <option value="">全部审阅</option>
        <option value="PENDING">待审阅</option>
        <option value="REVIEWED">已审阅</option>
        <option value="RETURNED">已退回</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">查询</button>
      <button class="btn btn-sec btn-sm" type="button" @click="resetFilters">重置</button>
    </form>
    <div class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>日期</th>
              <th>类型</th>
              <th>状态</th>
              <th>审阅</th>
              <th>按时</th>
              <th>今日完成</th>
              <th>提交时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="8"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!rows.length">
              <td colspan="8"><div class="empty"><div class="et">{{ error || '暂无日报' }}</div></div></td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.id">
              <td class="num">{{ row.reportDate }}</td>
              <td>{{ row.reportTypeLabel || '—' }}</td>
              <td><span class="tag" :class="statusClass(row.submitStatus)">{{ displayStatus(row) }}</span></td>
              <td>{{ reviewLabel(row.reviewStatus) }}</td>
              <td>{{ row.submitStatus === 'SUBMITTED' || row.submitStatus === 'READ' ? (row.isOnTime ? '是' : '否') : '—' }}</td>
              <td style="max-width: 280px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap">{{ row.contentDone }}</td>
              <td class="num" style="font-size: 12px">{{ row.submittedAt || '—' }}</td>
              <td>
                <button class="btn btn-sec btn-sm" type="button" @click="openDetail(row)">查看</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    <div v-if="drawerOpen" class="drawer-mask" @click.self="drawerOpen = false">
      <div class="drawer on" style="width: min(720px, 100vw)">
        <div class="drawer-h">
          <b>日报 · {{ detail?.reportDate }}</b>
          <button type="button" class="btn btn-sec btn-sm" @click="drawerOpen = false">关闭</button>
        </div>
        <div v-if="detail" class="drawer-b">
          <p><strong>提交人</strong> {{ detail.userName || '—' }} · <strong>字段完成度</strong> {{ detail.fieldCompleteness ?? '—' }}%</p>
          <p><strong>今日完成</strong><br />{{ detail.contentDone }}</p>
          <p><strong>明日计划</strong><br />{{ detail.contentPlan }}</p>
          <p><strong>问题与风险</strong><br />{{ detail.contentIssue }}</p>
          <p v-if="detail.weekSummary"><strong>周小结</strong><br />{{ detail.weekSummary }}</p>
          <p v-if="detail.supplement"><strong>补充说明</strong><br />{{ detail.supplement }}</p>
          <p><strong>审阅流</strong></p>
          <p v-for="step in reviewSteps" :key="step.level">
            {{ step.title }}：{{ step.reviewer }} · {{ step.action }} · {{ step.comment }} · {{ step.time }}
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { http } from '../../api/http'

type DailyRow = {
  id: number
  reportDate: string
  userName?: string
  reportTypeLabel?: string
  fieldCompleteness?: number
  reviewStatus?: string
  contentDone: string
  contentPlan: string
  contentIssue: string
  weekSummary?: string
  supplement?: string
  submitStatus: string
  submittedAt?: string
  isOnTime: boolean
}

type ReviewRecord = {
  reviewLevel: number
  reviewerName?: string
  action?: string
  comment?: string
  reviewedAt?: string
}

const router = useRouter()
const rows = ref<DailyRow[]>([])
const loading = ref(false)
const error = ref('')
const drawerOpen = ref(false)
const detail = ref<DailyRow | null>(null)
const templateInfo = reactive({ deadlineTime: '22:00' })
const filters = reactive({ dateFrom: '', dateTo: '', submitStatus: '', reportType: '', reviewState: '' })
const reviews = ref<ReviewRecord[]>([])
const reviewSteps = computed(() => {
  const actionName: Record<string, string> = { READ: '已读', COMMENT: '点评', MARK_FOLLOW_UP: '标记跟进' }
  return [1, 2].map((level) => {
    const row = reviews.value.find((item) => item.reviewLevel === level)
    return {
      level,
      title: level === 1 ? '一级直属上级' : '二级部门负责人',
      reviewer: row?.reviewerName || '待审',
      action: row ? actionName[row.action || ''] || row.action || '—' : '—',
      comment: row?.comment || '—',
      time: row?.reviewedAt || '—',
    }
  })
})

function displayStatus(row: DailyRow) {
  if (row.submitStatus === 'DRAFT') return '草稿'
  if (row.supplement) return '已补交'
  if (row.submitStatus !== 'DRAFT' && row.isOnTime === false) return '迟交'
  if (row.submitStatus === 'SUBMITTED' || row.submitStatus === 'READ') return '已提交'
  return row.submitStatus
}

function reviewLabel(state?: string) {
  if (state === 'PENDING') return '待审阅'
  if (state === 'REVIEWED') return '已审阅'
  if (state === 'RETURNED') return '已退回'
  return '—'
}

function statusLabel(s: string) {
  if (s === 'DRAFT') return '草稿'
  if (s === 'SUBMITTED') return '已提交'
  if (s === 'READ') return '已审阅'
  return s
}

function statusClass(s: string) {
  if (s === 'DRAFT') return 'tag-warn'
  if (s === 'SUBMITTED') return 'tag-ok'
  return ''
}

function goSubmit() {
  router.push('/ims/meet/daily/submit')
}

async function loadTemplate() {
  const res = await http.get('/meet/daily/template')
  if (res.data.code === 0) {
    templateInfo.deadlineTime = res.data.data.deadlineTime
  }
}

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const params: Record<string, string | number | boolean> = { pageNo: 1, pageSize: 20, onlyMine: true }
    if (filters.dateFrom) params.dateFrom = filters.dateFrom
    if (filters.dateTo) params.dateTo = filters.dateTo
    if (filters.submitStatus) params.submitStatus = filters.submitStatus
    if (filters.reportType) params.reportType = filters.reportType
    if (filters.reviewState) params.reviewState = filters.reviewState
    const res = await http.get('/meet/daily/list', { params })
    if (res.data.code !== 0) {
      error.value = res.data.msg || '加载失败'
      rows.value = []
      return
    }
    rows.value = res.data.data.list || []
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : '网络错误'
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  filters.dateFrom = ''
  filters.dateTo = ''
  filters.submitStatus = ''
  filters.reportType = ''
  filters.reviewState = ''
  loadList()
}

async function openDetail(row: DailyRow) {
  detail.value = row
  reviews.value = []
  drawerOpen.value = true
  try {
    const res = await http.get('/meet/review/records', { params: { reportId: row.id, pageNo: 1, pageSize: 10 } })
    reviews.value = res.data.data?.list || []
  } catch {
    reviews.value = []
  }
}

onMounted(() => {
  loadTemplate()
  loadList()
})
</script>

<style scoped>
.drawer-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  z-index: 90;
}
</style>
