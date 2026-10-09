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

    <ProtoDrawer :open="drawerOpen" :title="`审核 · ${active?.reviewNo || ''}`" width="840px" @close="drawerOpen = false">
      <p><b>{{ active?.contentTitle }}</b></p>
      <p class="hint">提交人：{{ active?.submitterName }} · 轮次 {{ active?.reviewRound }}</p>

      <div class="dsec">赛事与玩法（只读）</div>
      <div data-testid="content-review-sessions">
        <div class="tabs" data-testid="content-review-play-tabs">
          <div
            v-for="tab in matchTabs"
            :key="tab.id"
            class="tab"
            :class="{ on: (preview.matchType || 1) === tab.id }"
            style="pointer-events: none"
          >
            {{ tab.label }}
          </div>
        </div>
        <p class="hint">只读 · {{ preview.matchSummary || '无赛事摘要' }} · 场次与玩法不可切换</p>
        <p v-if="!sessions.length" class="hint" data-testid="content-review-session-empty">暂无场次</p>
        <div v-else class="tbl-wrap">
          <table>
            <thead>
              <tr>
                <th>对阵</th>
                <th>时间</th>
                <th>主玩法</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, index) in sessions" :key="index" data-testid="content-review-session">
                <td>{{ sessionTitle(item) }}</td>
                <td class="num">{{ item.matchTime || '—' }}</td>
                <td>{{ item.mainPlayMethod || '—' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="dsec">正文预览（LayoutViewer readOnly）</div>
      <div class="layout-view" data-testid="content-review-layout">
        <iframe
          v-if="preview.layoutHtml"
          class="layout-frame"
          sandbox=""
          referrerpolicy="no-referrer"
          :srcdoc="preview.layoutHtml"
          title="layout_html"
        />
        <pre v-else class="layout-fallback">{{ preview.body || '（无正文）' }}</pre>
      </div>

      <div class="dsec">付费内容 / 免费内容</div>
      <p class="hint">
        <span class="chip" data-testid="content-review-paywall">{{ preview.paywall ? '含付费' : '无付费标记' }}</span>
        双栏只读，不可编辑
      </p>
      <div class="review-dual" data-testid="content-review-paid-free" :data-split="preview.columnSplit">
        <div>
          <div class="csub">付费内容 · body_paid</div>
          <textarea
            data-testid="content-review-paid"
            :value="preview.paidBody"
            readonly
            disabled
            rows="6"
            placeholder="暂无付费内容"
          />
        </div>
        <div>
          <div class="csub">免费内容 · free_body</div>
          <textarea
            data-testid="content-review-free"
            :value="preview.freeBody"
            readonly
            disabled
            rows="6"
            placeholder="暂无免费内容"
          />
        </div>
      </div>
      <p class="hint">
        无独立付费/免费字段。优先按 layout 的 data-zone / data-paywall 分区；否则正文
        <span class="mono">---FREE---</span>
        分隔；都没有时 OFFICIAL_PLAN 进付费栏，其余进免费栏。
      </p>

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

type SessionItem = {
  homeName?: string
  awayName?: string
  matchTime?: string
  mainPlayMethod?: string
  matchId?: string
  competitionName?: string
}

type ContentPreview = {
  layoutHtml: string
  body: string
  documentType: string
  contentType: string
  matchType: number | null
  matchScheme: SessionItem[]
  matchSummary: string
  paidBody: string
  freeBody: string
  paywall: boolean
  columnSplit: string
}

const matchTabs = [
  { id: 1, label: '竞足' },
  { id: 2, label: '传足' },
  { id: 3, label: '北单' },
  { id: 4, label: '足球' },
]

function emptyPreview(): ContentPreview {
  return {
    layoutHtml: '',
    body: '',
    documentType: '',
    contentType: '',
    matchType: null,
    matchScheme: [],
    matchSummary: '',
    paidBody: '',
    freeBody: '',
    paywall: false,
    columnSplit: 'default-free',
  }
}

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
const preview = ref<ContentPreview>(emptyPreview())

const filteredRows = computed(() => {
  let list = rows.value.filter((r) => (stage.value === 1 ? r.reviewRound <= 1 : r.reviewRound >= 2))
  if (titleKw.value.trim()) {
    const kw = titleKw.value.trim()
    list = list.filter((r) => (r.contentTitle || '').includes(kw))
  }
  return list
})

const sessions = computed(() => preview.value.matchScheme || [])

function sessionTitle(item: SessionItem) {
  const home = item.homeName || ''
  const away = item.awayName || ''
  if (home || away) return `${home} VS ${away}`
  return item.competitionName || item.matchId || '场次'
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

async function openReview(row: any) {
  active.value = row
  preview.value = emptyPreview()
  drawerOpen.value = true
  try {
    const { data } = await http.get(`/content/review/${row.reviewNo}`)
    checklist.value = data.data.checklist || []
    const model: Record<string, boolean> = {}
    for (const item of checklist.value) {
      model[item.itemCode] = Boolean(item.passed)
    }
    checklistModel.value = model
    preview.value = { ...emptyPreview(), ...(data.data.contentPreview || {}) }
  } catch (e) {
    alert(errorMessage(e))
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
.review-dual {
  display: flex;
  gap: 12px;
  align-items: stretch;
  flex-wrap: wrap;
}
.review-dual > div {
  flex: 1;
  min-width: 260px;
}
.review-dual textarea {
  width: 100%;
  min-height: 120px;
  resize: vertical;
}
.layout-view {
  max-width: 677px;
  margin: 10px auto 0;
  padding: 16px 18px;
  border: 1px solid var(--line);
  background: #fafafa;
  border-radius: 6px;
}
.layout-frame {
  width: 100%;
  min-height: 140px;
  border: 0;
  background: transparent;
}
.layout-fallback {
  margin: 0;
  white-space: pre-wrap;
  font-family: inherit;
  font-size: 13px;
  line-height: 1.7;
}
</style>
