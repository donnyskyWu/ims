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
              <th>赛事摘要</th>
              <th>提交人</th>
              <th>轮次</th>
              <th>提交时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="7"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!filteredRows.length">
              <td colspan="7"><div class="empty"><div class="et">{{ error || '暂无待审' }}</div></div></td>
            </tr>
            <tr v-for="row in filteredRows" v-else :key="row.reviewNo">
              <td class="mono">{{ row.reviewNo }}</td>
              <td>{{ row.contentTitle }}</td>
              <td data-testid="review-queue-match">{{ row.matchSummary || '—' }}</td>
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
      <div data-testid="content-review-meta">
        <p><b>{{ active?.contentTitle }}</b></p>
        <p class="hint">
          作者：{{ preview.authorName || active?.submitterName || '—' }}
          · IP 组：{{ preview.ipGroupName || '—' }}
          · {{ preview.documentType || '—' }} / {{ preview.contentType || '—' }}
          · 轮次 {{ active?.reviewRound }}
        </p>
        <p class="hint">Football：{{ preview.fbSyncStatusLabel || '未同步' }}</p>
      </div>

      <div class="dsec">审核流程</div>
      <ol v-if="steps.length" class="review-steps" data-testid="content-review-steps">
        <li v-for="step in steps" :key="step.round" :data-status="step.status">
          <span class="tag">{{ stepStatusLabel(step.status) }}</span>
          <span>{{ step.label }}</span>
        </li>
      </ol>
      <p v-else class="hint" data-testid="content-review-steps">审核级数未开启，可直接发布</p>

      <div v-if="preview.matchSummary" class="dsec">玩法</div>
      <p v-if="preview.matchSummary" class="hint" data-testid="content-review-match">{{ preview.matchSummary }}</p>

      <div class="dsec">赛事与玩法</div>
      <p v-if="!detailReady" class="hint">场次加载中</p>
      <template v-else>
        <div class="tabs review-match-tabs" data-testid="review-match-tabs">
          <div
            v-for="tab in MATCH_TABS"
            :key="tab.value"
            class="tab"
            :class="{ on: active?.matchType === tab.value }"
            data-testid="review-match-tab"
          >
            {{ tab.label }}
          </div>
        </div>
        <p class="hint" data-testid="review-play-summary">玩法摘要：{{ active?.matchSummary || '—' }}</p>
        <div class="tbl-wrap">
          <table data-testid="review-session-list">
            <thead>
              <tr>
                <th>赛事</th>
                <th>场次</th>
                <th>时间</th>
                <th>玩法</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!sessions.length">
                <td colspan="4"><div class="empty"><div class="et">暂无场次</div></div></td>
              </tr>
              <tr v-for="(item, index) in sessions" v-else :key="index" data-testid="review-session-row">
                <td>{{ item.className || '—' }}</td>
                <td>{{ sessionLabel(item) }}</td>
                <td>{{ formatMatchTime(item.matchTime) }}</td>
                <td>{{ playLabel(item) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>

      <div class="dsec">正文</div>
      <div data-testid="content-review-preview">
        <LayoutViewer :html="active?.layoutHtml" :plain="active?.body" :loading="layoutLoading" />
        <ContentLayoutPreview :layout-html="preview.layoutHtml || previewLayout" :body="preview.body || previewBody" />
      </div>

      <div class="dsec" data-testid="content-review-conclusion">审核结论</div>
      <p class="hint">先看正文，再勾选清单并下结论。</p>
      <div class="dsec">质量清单</div>
      <label v-for="item in checklist" :key="item.itemCode" class="rowline" style="gap: 8px; margin-bottom: 6px">
        <input v-model="checklistModel[item.itemCode]" type="checkbox" />
        <span>{{ item.itemDesc }}</span>
      </label>
      <div class="fld" style="margin-top: 12px">
        <label>驳回意见</label>
        <textarea
          v-model="remark"
          data-testid="content-review-reject-opinion"
          rows="3"
          maxlength="512"
          placeholder="驳回时必填，不超过 512 字"
        />
      </div>
      <template #footer>
        <button
          class="btn btn-sec"
          type="button"
          data-testid="content-review-reject"
          :disabled="submitting || !detailReady"
          @click="submit('REJECT_BACK')"
        >
          驳回
        </button>
        <button
          class="btn btn-pri"
          type="button"
          data-testid="content-review-pass"
          :disabled="submitting || !detailReady"
          @click="submit('PASS')"
        >
          通过
        </button>
      </template>
    </ProtoDrawer>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { http, errorMessage } from '../../api/http'
import LayoutViewer from '../../components/LayoutViewer.vue'
import ContentLayoutPreview from '../../components/ContentLayoutPreview.vue'
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
const previewLayout = ref('')
const previewBody = ref('')
const detailReady = ref(false)
const remark = ref('')
const steps = ref<any[]>([])
const preview = ref<Record<string, any>>({})

const MATCH_TABS = [
  { value: 1, label: '竞足' },
  { value: 2, label: '传足' },
  { value: 3, label: '北单' },
  { value: 4, label: '足球' },
]

const sessions = computed(() => {
  const scheme = Array.isArray(active.value?.matchScheme) ? active.value.matchScheme : []
  if (scheme.length) return scheme
  const legacy = String(active.value?.competitionName || '').trim()
  if (legacy) return [{ legacyLabel: legacy }]
  return []
})

function sessionLabel(item: any) {
  if (item?.legacyLabel) return item.legacyLabel
  const home = item?.homeName || ''
  const away = item?.awayName || ''
  if (home || away) return `${home} VS ${away}`.trim()
  return String(item?.matchId || item?.scheduleId || '—')
}

function playLabel(item: any) {
  if (item?.legacyLabel) return '—'
  const main = item?.mainPlayMethod || ''
  const plays = Array.isArray(item?.matchPlays) ? item.matchPlays : []
  const bits = plays.map((play: any) => play?.result).filter(Boolean)
  if (main && bits.length) return `${main} · ${bits.join('、')}`
  return main || bits.join('、') || '—'
}

function formatMatchTime(value: unknown) {
  if (value == null || value === '') return '—'
  if (typeof value === 'number') {
    const ms = value < 1e12 ? value * 1000 : value
    const date = new Date(ms)
    if (Number.isNaN(date.getTime())) return String(value)
    const pad = (n: number) => String(n).padStart(2, '0')
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
  }
  return String(value)
}

const filteredRows = computed(() => {
  let list = rows.value.filter((r) => (stage.value === 1 ? r.reviewRound <= 1 : r.reviewRound >= 2))
  if (titleKw.value.trim()) {
    const kw = titleKw.value.trim()
    list = list.filter((r) => (r.contentTitle || '').includes(kw))
  }
  return list
})

function stepStatusLabel(status: string) {
  if (status === 'CURRENT') return '当前'
  if (status === 'DONE') return '已完成'
  return '待审'
}

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

async function loadPreview(contentId: number | null | undefined) {
  previewLayout.value = ''
  previewBody.value = ''
  if (!contentId) return
  try {
    const { data } = await http.get(`/content/${contentId}`)
    previewLayout.value = data.data?.layoutHtml || ''
    previewBody.value = data.data?.body || ''
  } catch {
    previewLayout.value = ''
    previewBody.value = ''
  }
}

async function openReview(row: any) {
  active.value = { ...row, layoutHtml: '', body: '' }
  layoutLoading.value = true
  detailReady.value = false
  remark.value = ''
  steps.value = []
  preview.value = {}
  checklist.value = []
  checklistModel.value = {}
  drawerOpen.value = true
  previewLayout.value = ''
  previewBody.value = ''
  try {
    const { data } = await http.get(`/content/review/${row.reviewNo}`)
    const payload = data.data || {}
    active.value = { ...row, ...payload }
    checklist.value = payload.checklist || []
    const model: Record<string, boolean> = {}
    for (const item of checklist.value) {
      model[item.itemCode] = Boolean(item.passed)
    }
    checklistModel.value = model
    preview.value = payload.preview || {}
    steps.value = payload.reviewSteps || []
    previewLayout.value = payload.layoutHtml || payload.preview?.layoutHtml || ''
    previewBody.value = payload.body || payload.preview?.body || ''
    detailReady.value = true
  } catch (e) {
    alert(errorMessage(e))
  } finally {
    layoutLoading.value = false
  }
}

async function submit(conclusion: 'PASS' | 'REJECT_BACK') {
  if (!active.value || !detailReady.value) return
  const checklistResult: Record<string, boolean> = { ...checklistModel.value }
  const opinion = remark.value.trim()
  if (conclusion === 'PASS') {
    const missed = checklist.value.filter((item) => !checklistResult[item.itemCode])
    if (missed.length && !window.confirm('仍有未勾选清单项，确认通过？')) return
  }
  const body: any = { conclusion, checklistResult }
  if (conclusion === 'REJECT_BACK') {
    if (!opinion) {
      window.alert('请先填写驳回意见')
      return
    }
    if (opinion.length > 512) {
      window.alert('驳回意见不超过 512 字')
      return
    }
    if (!window.confirm('确认驳回？意见将退回作者修改。')) return
    const failed = Object.entries(checklistResult)
      .filter(([, passed]) => !passed)
      .map(([code]) => ({ itemCode: code, reason: opinion }))
    if (!failed.length) {
      failed.push({ itemCode: 'QUALITY', reason: opinion })
    }
    body.rejectItems = failed
    body.remark = opinion
  }
  submitting.value = true
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

<style scoped>
.review-steps {
  margin: 0 0 8px;
  padding: 0;
  list-style: none;
}
.review-steps li {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  margin-bottom: 6px;
  font-size: 13px;
}
.fld textarea {
  width: 100%;
  box-sizing: border-box;
  margin-top: 6px;
}
.review-match-tabs {
  pointer-events: none;
  margin-bottom: 8px;
}
</style>
