<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>内容审核</h1>
        <div class="sub">审核队列与结论（CONTENT-005 · 未审不可发布 G1）</div>
      </div>
      <div class="acts">
        <span class="csub">一次通过率 {{ stats.firstPassRate != null ? (stats.firstPassRate * 100).toFixed(1) : '—' }}%</span>
      </div>
    </div>
    <div class="tabs">
      <div class="tab" :class="{ on: stage === 1 }" @click="stage = 1; loadQueue()">一级审核</div>
      <div class="tab" :class="{ on: stage === 2 }" @click="stage = 2; loadQueue()">二级审核</div>
    </div>
    <form class="qbar" @submit.prevent="loadQueue">
      <input v-model="titleKw" placeholder="标题" style="width: 140px" />
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">查询</button>
    </form>
    <div class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>审核单号</th>
              <th>标题</th>
              <th>提交人</th>
              <th>轮次</th>
              <th>提交时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="6"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!filteredRows.length">
              <td colspan="6"><div class="empty"><div class="et">{{ error || '暂无待审' }}</div></div></td>
            </tr>
            <tr v-for="row in filteredRows" v-else :key="row.reviewNo">
              <td class="mono">{{ row.reviewNo }}</td>
              <td>{{ row.contentTitle }}</td>
              <td>{{ row.submitterName }}</td>
              <td class="num">{{ row.reviewRound }}</td>
              <td class="num" style="font-size: 12px">{{ row.createdAt }}</td>
              <td><button class="btn btn-pri btn-sm" type="button" @click="openReview(row)">审核</button></td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="pager"><span class="pg-total">共 {{ filteredRows.length }} 条</span></div>
    </div>

    <ProtoDrawer :open="drawerOpen" :title="`审核 · ${active?.reviewNo || ''}`" width="760px" @close="drawerOpen = false">
      <p><b>{{ active?.contentTitle }}</b></p>
      <p class="hint">提交人：{{ active?.submitterName }} · 轮次 {{ active?.reviewRound }}</p>
      <div class="dsec">正文</div>
      <LayoutViewer :html="active?.layoutHtml" :plain="active?.body" :loading="layoutLoading" />
      <div class="dsec">质量清单</div>
      <label v-for="item in checklist" :key="item.itemCode" class="rowline" style="gap: 8px; margin-bottom: 6px">
        <input v-model="checklistModel[item.itemCode]" type="checkbox" />
        <span>{{ item.itemDesc }}</span>
      </label>
      <template #footer>
        <button class="btn btn-sec" type="button" @click="submit('REJECT_BACK')">打回</button>
        <button class="btn btn-pri" type="button" :disabled="submitting" @click="submit('PASS')">通过</button>
      </template>
    </ProtoDrawer>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { http, errorMessage } from '../../api/http'
import LayoutViewer from '../../components/LayoutViewer.vue'
import ProtoDrawer from '../../components/ProtoDrawer.vue'

const rows = ref<any[]>([])
const loading = ref(false)
const error = ref('')
const stage = ref(1)
const titleKw = ref('')
const stats = ref<{ firstPassRate?: number; total?: number }>({})
const drawerOpen = ref(false)
const layoutLoading = ref(false)
const active = ref<any>(null)
const checklist = ref<any[]>([])
const checklistModel = ref<Record<string, boolean>>({})
const submitting = ref(false)

const filteredRows = computed(() => {
  let list = rows.value.filter((r) => (stage.value === 1 ? r.reviewRound <= 1 : r.reviewRound >= 2))
  if (titleKw.value.trim()) {
    const kw = titleKw.value.trim()
    list = list.filter((r) => (r.contentTitle || '').includes(kw))
  }
  return list
})

async function loadStats() {
  try {
    const { data } = await http.get('/content/review/first-pass-stats')
    stats.value = data.data
  } catch {
    stats.value = {}
  }
}

async function loadQueue() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await http.get('/content/review/queue', { params: { pageNo: 1, pageSize: 100 } })
    rows.value = data.data.list
    await loadStats()
  } catch (e) {
    error.value = errorMessage(e)
    rows.value = []
  } finally {
    loading.value = false
  }
}

async function openReview(row: any) {
  active.value = { ...row, layoutHtml: '', body: '' }
  layoutLoading.value = true
  drawerOpen.value = true
  try {
    const { data } = await http.get(`/content/review/${row.reviewNo}`)
    active.value = { ...row, ...data.data }
    checklist.value = data.data.checklist || []
    const model: Record<string, boolean> = {}
    for (const item of checklist.value) {
      model[item.itemCode] = Boolean(item.passed)
    }
    checklistModel.value = model
  } catch (e) {
    alert(errorMessage(e))
  } finally {
    layoutLoading.value = false
  }
}

async function submit(conclusion: 'PASS' | 'REJECT_BACK') {
  if (!active.value) return
  submitting.value = true
  const checklistResult: Record<string, boolean> = { ...checklistModel.value }
  const body: any = { conclusion, checklistResult }
  if (conclusion === 'REJECT_BACK') {
    const failed = Object.entries(checklistResult)
      .filter(([, v]) => !v)
      .map(([code]) => ({ itemCode: code, reason: '未通过' }))
    if (!failed.length) {
      failed.push({ itemCode: 'QUALITY', reason: '需修改' })
    }
    body.rejectItems = failed
  }
  try {
    await http.put(`/content/review/${active.value.reviewNo}/conclusion`, body)
    drawerOpen.value = false
    await loadQueue()
  } catch (e) {
    alert(errorMessage(e))
  } finally {
    submitting.value = false
  }
}

loadQueue()
</script>
