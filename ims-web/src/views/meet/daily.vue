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
      <select v-model="filters.submitStatus" style="width: 120px">
        <option value="">全部状态</option>
        <option value="DRAFT">草稿</option>
        <option value="SUBMITTED">已提交</option>
        <option value="READ">已审阅</option>
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
              <th>状态</th>
              <th>按时</th>
              <th>今日完成</th>
              <th>提交时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="6"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!rows.length">
              <td colspan="6"><div class="empty"><div class="et">{{ error || '暂无日报' }}</div></div></td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.id">
              <td class="num">{{ row.reportDate }}</td>
              <td><span class="tag" :class="statusClass(row.submitStatus)">{{ statusLabel(row.submitStatus) }}</span></td>
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
      <div class="drawer">
        <div class="drawer-h">
          <b>日报 · {{ detail?.reportDate }}</b>
          <button type="button" class="btn btn-sec btn-sm" @click="drawerOpen = false">关闭</button>
        </div>
        <div v-if="detail" class="drawer-b">
          <p><strong>今日完成</strong><br />{{ detail.contentDone }}</p>
          <p><strong>明日计划</strong><br />{{ detail.contentPlan }}</p>
          <p><strong>问题与风险</strong><br />{{ detail.contentIssue }}</p>
          <p v-if="detail.weekSummary"><strong>周小结</strong><br />{{ detail.weekSummary }}</p>
          <p v-if="detail.supplement"><strong>补充说明</strong><br />{{ detail.supplement }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { http } from '../../api/http'

type DailyRow = {
  id: number
  reportDate: string
  contentDone: string
  contentPlan: string
  contentIssue: string
  weekSummary?: string
  supplement?: string
  submitStatus: string
  submittedAt?: string
  isOnTime: boolean
}

const router = useRouter()
const rows = ref<DailyRow[]>([])
const loading = ref(false)
const error = ref('')
const drawerOpen = ref(false)
const detail = ref<DailyRow | null>(null)
const templateInfo = reactive({ deadlineTime: '22:00' })
const filters = reactive({ dateFrom: '', dateTo: '', submitStatus: '' })

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
  loadList()
}

function openDetail(row: DailyRow) {
  detail.value = row
  drawerOpen.value = true
}

onMounted(() => {
  loadTemplate()
  loadList()
})
</script>
