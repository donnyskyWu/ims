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

    <ProtoDrawer :open="drawerOpen" :title="`审核 · ${active?.reviewNo || ''}`" width="720px" @close="drawerOpen = false">
      <p><b>{{ active?.contentTitle }}</b></p>
      <p class="hint">提交人：{{ active?.submitterName }} · 轮次 {{ active?.reviewRound }}</p>
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
import ProtoDrawer from '../../components/ProtoDrawer.vue'

const rows = ref<any[]>([])
const loading = ref(false)
const error = ref('')
const stage = ref(1)
const titleKw = ref('')
const stats = ref<{ firstPassRate?: number; total?: number }>({})
const drawerOpen = ref(false)
const active = ref<any>(null)
const checklist = ref<any[]>([])
const checklistModel = ref<Record<string, boolean>>({})
const submitting = ref(false)
const detailReady = ref(false)

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
  active.value = row
  detailReady.value = false
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
    detailReady.value = true
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

<style scoped>
.review-match-tabs {
  pointer-events: none;
  margin-bottom: 8px;
}
</style>
