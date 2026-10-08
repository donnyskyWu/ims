<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>待我审阅</h1>
        <div class="sub">MEET-002 · 一级 24h 超时标红 · 二级审阅完成后状态 READ</div>
      </div>
    </div>
    <div class="tabs">
      <div class="tab" :class="{ on: level === 1 }" @click="level = 1; loadQueue()">一级审阅</div>
      <div class="tab" :class="{ on: level === 2 }" @click="level = 2; loadQueue()">二级审阅</div>
    </div>
    <form class="qbar" @submit.prevent="loadQueue">
      <input v-model="filters.dateFrom" type="date" style="width: 140px" />
      <input v-model="filters.dateTo" type="date" style="width: 140px" />
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">刷新</button>
    </form>
    <div class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>日期</th>
              <th>提交人</th>
              <th>等待(h)</th>
              <th>超时</th>
              <th>今日完成</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="6"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!rows.length">
              <td colspan="6"><div class="empty"><div class="et">{{ error || '暂无待审' }}</div></div></td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.id">
              <td class="num">{{ row.reportDate }}</td>
              <td>{{ row.userName }}</td>
              <td class="num">{{ row.waitingHours }}</td>
              <td><span v-if="row.isTimeout" class="tag tag-warn">超时</span><span v-else>—</span></td>
              <td style="max-width: 240px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap">{{ row.contentDone }}</td>
              <td><button class="btn btn-pri btn-sm" type="button" @click="openReview(row)">审阅</button></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    <div v-if="drawerOpen" class="drawer-mask" @click.self="drawerOpen = false">
      <div class="drawer">
        <div class="drawer-h">
          <b>审阅 · {{ active?.userName }} · {{ active?.reportDate }}</b>
          <button type="button" class="btn btn-sec btn-sm" @click="drawerOpen = false">关闭</button>
        </div>
        <div v-if="active" class="drawer-b">
          <p><strong>今日完成</strong><br />{{ active.contentDone }}</p>
          <p><strong>明日计划</strong><br />{{ active.contentPlan }}</p>
          <p><strong>问题与风险</strong><br />{{ active.contentIssue }}</p>
          <label class="rowline" style="margin-top: 12px">
            <span style="min-width: 72px">点评</span>
            <textarea v-model="comment" rows="3" style="flex: 1" placeholder="可选" />
          </label>
          <div class="acts" style="margin-top: 16px; gap: 8px">
            <button class="btn btn-pri btn-sm" type="button" :disabled="submitting" @click="submit('READ')">已读</button>
            <button class="btn btn-sec btn-sm" type="button" :disabled="submitting" @click="submit('COMMENT')">点评</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { http } from '../../api/http'

type QueueRow = {
  id: number
  reportDate: string
  userName: string
  contentDone: string
  contentPlan: string
  contentIssue: string
  reviewLevel: number
  waitingHours: number
  isTimeout: boolean
}

const rows = ref<QueueRow[]>([])
const loading = ref(false)
const error = ref('')
const level = ref(1)
const filters = reactive({ dateFrom: '', dateTo: '' })
const drawerOpen = ref(false)
const active = ref<QueueRow | null>(null)
const comment = ref('')
const submitting = ref(false)

async function loadQueue() {
  loading.value = true
  error.value = ''
  try {
    const params: Record<string, string | number> = { pageNo: 1, pageSize: 20, reviewLevel: level.value }
    if (filters.dateFrom) params.dateFrom = filters.dateFrom
    if (filters.dateTo) params.dateTo = filters.dateTo
    const res = await http.get('/meet/review/queue', { params })
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

function openReview(row: QueueRow) {
  active.value = row
  comment.value = ''
  drawerOpen.value = true
}

async function submit(action: string) {
  if (!active.value) return
  submitting.value = true
  try {
    const res = await http.put(`/meet/review/${active.value.id}`, {
      reviewLevel: level.value,
      action,
      comment: comment.value,
    })
    if (res.data.code !== 0) {
      error.value = res.data.msg || '审阅失败'
      return
    }
    drawerOpen.value = false
    await loadQueue()
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : '网络错误'
  } finally {
    submitting.value = false
  }
}

onMounted(loadQueue)
</script>
