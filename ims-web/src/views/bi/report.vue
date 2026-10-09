<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>报表中心</h1>
        <div class="sub">M6 八张标准报表 · 统一筛选条 · /ims/bi/report</div>
      </div>
    </div>

    <div class="qbar" style="flex-wrap: wrap; gap: 8px">
      <span class="csub">平台</span>
      <select v-model="platform" data-testid="bi-report-platform" style="width: 110px">
        <option value="">全部平台</option>
        <option value="DOUYIN">抖音</option>
        <option value="WECHAT_CHANNELS">视频号</option>
        <option value="KUAISHOU">快手</option>
        <option value="DOUYU">斗鱼</option>
      </select>
      <input v-model="dateFrom" data-testid="bi-report-from" type="date" />
      <span class="csub">至</span>
      <input v-model="dateTo" data-testid="bi-report-to" type="date" />
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="button" data-testid="bi-report-run" @click="reloadPreview">刷新预览</button>
    </div>
    <p v-if="reportError" class="hint bad" data-testid="bi-report-error">{{ reportError }}</p>

    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-top: 14px">
      <div
        v-for="item in reports"
        :key="item.code"
        class="card hov"
        style="cursor: pointer"
        :data-testid="`bi-report-card-${item.code}`"
        :style="{ outline: selected?.code === item.code ? '2px solid var(--blue)' : '' }"
        @click="selectReport(item)"
      >
        <b>{{ item.title }}</b>
        <div class="csub" style="margin-top: 8px">{{ item.desc }}</div>
        <div class="rowline" style="margin-top: 10px; gap: 6px; flex-wrap: wrap">
          <span v-for="tag in item.tags" :key="tag" class="tag tag-info">{{ tag }}</span>
        </div>
      </div>
    </div>

    <div v-if="preview" class="card" style="margin-top: 16px" data-testid="bi-report-result">
      <div class="bi0-result-hd"><b>{{ preview.title }}</b> · {{ preview.total }} 行 · {{ preview.dataAsOf }}</div>
      <p v-if="preview.filterNote" class="hint" data-testid="bi-report-filter-note">{{ preview.filterNote }}</p>
      <div v-if="preview.empty" class="empty" data-testid="bi-report-empty">
        <div class="et">{{ preview.emptyReason || '当前筛选下暂无数据' }}</div>
      </div>
      <div v-else class="tbl-wrap" style="margin-top: 8px">
        <table>
          <thead>
            <tr>
              <th v-for="c in preview.columns" :key="c">{{ c }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, idx) in preview.rows" :key="idx" data-testid="bi-report-row">
              <td v-for="c in preview.columns" :key="c">{{ row[c] }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { errorMessage, http } from '../../api/http'

type ReportCard = { code: string; title: string; desc: string; tags: string[] }
type Preview = {
  title: string
  columns: string[]
  rows: Record<string, unknown>[]
  total: number
  dataAsOf: string
  empty?: boolean
  emptyReason?: string
  filterNote?: string
}

const reports = ref<ReportCard[]>([])
const selected = ref<ReportCard | null>(null)
const preview = ref<Preview | null>(null)
const platform = ref('')
const dateFrom = ref('')
const dateTo = ref('')
const reportError = ref('')

async function loadCatalog() {
  const res = await http.get('/bi/report/catalog')
  if (res.data.code === 0) {
    reports.value = res.data.data.reports || []
    if (reports.value.length && !selected.value) {
      selected.value = reports.value[0]
      await reloadPreview()
    }
  }
}

async function selectReport(item: ReportCard) {
  selected.value = item
  await reloadPreview()
}

async function reloadPreview() {
  if (!selected.value) return
  reportError.value = ''
  const from = dateFrom.value
  const to = dateTo.value
  if ((from && !to) || (!from && to)) {
    reportError.value = '请同时填写开始和结束日期'
    return
  }
  if (from && to && from > to) {
    reportError.value = '开始日期不能晚于结束日期'
    return
  }
  try {
    const res = await http.get(`/bi/report/${selected.value.code}`, {
      params: {
        platform: platform.value || undefined,
        dateFrom: from || undefined,
        dateTo: to || undefined,
      },
    })
    if (res.data.code === 0) preview.value = res.data.data
  } catch (error: unknown) {
    const body = error as { code?: number; msg?: string }
    reportError.value = typeof body?.code === 'number' ? `${body.code} ${body.msg || ''}` : errorMessage(error)
  }
}

onMounted(loadCatalog)
</script>
