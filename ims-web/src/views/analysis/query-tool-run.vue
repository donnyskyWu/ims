<template>
  <div class="page page-query-tool-run">
    <div class="pg-h">
      <div>
        <h1>查询执行</h1>
        <div class="sub">{{ templateCode }}</div>
      </div>
      <div class="acts">
        <button class="btn btn-sec btn-sm" type="button" @click="back">返回模板列表</button>
      </div>
    </div>

    <div class="card" style="padding: 16px">
      <form class="qbar" @submit.prevent="load">
        <label class="fld">
          <span>查询条件</span>
          <input v-model="keyword" data-testid="qt-run-keyword" placeholder="名称关键字" />
        </label>
        <label class="fld">
          <span>入口</span>
          <input v-model="entryId" data-testid="qt-run-entry" placeholder="entryId" />
        </label>
        <button class="btn btn-pri btn-sm" type="submit">查询</button>
      </form>
      <p v-if="error" class="hint bad">{{ error }}</p>
      <p v-if="pack" class="csub" data-testid="qt-run-meta">
        queryCostMs {{ pack.queryCostMs }} ms · {{ pack.queryMode }} · {{ pack.mode }}
        · 层数 {{ (pack.levels || []).length }}
        · 根实体 {{ pack.levelState?.rootEntity || '—' }}
        · 当前层级 {{ current.label || pack.levelState?.currentLevel || '—' }}
      </p>
      <div class="qt-crumbs" data-testid="qt-run-crumbs">
        <button
          v-for="(crumb, idx) in crumbs"
          :key="idx"
          type="button"
          class="btn-txt btn"
          @click="jump(idx)"
        >
          {{ crumb }}
        </button>
      </div>
      <div class="tabs">
        <div class="tab" :class="{ on: view === 'list' }" @click="view = 'list'">列表</div>
        <div class="tab" :class="{ on: view === 'chart' }" @click="view = 'chart'">图表</div>
      </div>
      <div v-if="view === 'list'" class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th v-for="col in current.columns" :key="col.key">{{ col.label }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!(current.rows || []).length">
              <td :colspan="Math.max(current.columns.length, 1)">当前层级暂无数据</td>
            </tr>
            <tr v-for="(row, idx) in current.rows" :key="idx" @click="drill(row)">
              <td v-for="col in current.columns" :key="col.key">{{ row[col.key] }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="qt-chart" data-testid="qt-run-chart">
        <div v-for="(bar, idx) in chartBars" :key="idx" class="qt-bar-row">
          <span>{{ bar.label }}</span>
          <span class="qt-bar" :style="{ width: bar.width }"></span>
          <span>{{ bar.value }}</span>
        </div>
        <p v-if="!chartBars.length" class="hint">当前层级没有可绘制的数据</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { errorMessage, http } from '../../api/http'

type Col = { key: string; label: string }
type Level = { label?: string; columns: Col[]; rows: Record<string, unknown>[] }
type Pack = {
  queryCostMs?: number
  queryMode?: string
  mode?: string
  columns?: Col[]
  rows?: Record<string, unknown>[]
  levels?: Level[]
  levelState?: { breadcrumbs?: string[]; rootEntity?: string; currentLevel?: string }
}

const route = useRoute()
const router = useRouter()
const templateCode = computed(() => String(route.params.templateCode || ''))
const keyword = ref('')
const entryId = ref('')
const pack = ref<Pack | null>(null)
const active = ref(0)
const crumbs = ref<string[]>([])
const view = ref<'list' | 'chart'>('list')
const error = ref('')

const current = computed<Level>(() => {
  const levels = pack.value?.levels || []
  if (levels[active.value]) return levels[active.value]
  return { label: '', columns: pack.value?.columns || [], rows: pack.value?.rows || [] }
})

const chartBars = computed(() => {
  const rows = current.value.rows || []
  const cols = current.value.columns || []
  const numeric = cols.find((col) => rows.some((row) => typeof row[col.key] === 'number'))
  const labelCol = cols[0]
  const max = Math.max(
    1,
    ...rows.map((row) => (numeric ? Number(row[numeric.key]) || 0 : 1)),
  )
  return rows.slice(0, 12).map((row, idx) => {
    const value = numeric ? Number(row[numeric.key]) || 0 : 1
    return {
      label: String(labelCol ? row[labelCol.key] ?? idx + 1 : idx + 1),
      value,
      width: `${Math.max(8, Math.round((value / max) * 100))}%`,
    }
  })
})

async function load() {
  error.value = ''
  try {
    const res = await http.post('/analysis/query-tool/run', {
      mode: 'DRILL',
      templateCode: templateCode.value,
      runtime: {
        keyword: keyword.value.trim(),
        entryId: entryId.value.trim() || undefined,
      },
    })
    pack.value = res.data.data
    active.value = 0
    const first = res.data.data?.levelState?.breadcrumbs?.[0] || res.data.data?.levels?.[0]?.label || '结果'
    crumbs.value = [first]
  } catch (err: unknown) {
    pack.value = null
    error.value = errorMessage(err)
  }
}

function drill(row: Record<string, unknown>) {
  const levels = pack.value?.levels || []
  if (active.value >= levels.length - 1) return
  const cols = current.value.columns || []
  const label = cols.length ? String(row[cols[0].key] ?? '') : ''
  active.value += 1
  crumbs.value = [...crumbs.value, label || current.value.label || `L${active.value}`]
}

function jump(index: number) {
  if (index < 0 || index > active.value) return
  active.value = index
  crumbs.value = crumbs.value.slice(0, index + 1)
}

function back() {
  router.push('/ims/analysis/query-tool')
}

watch(templateCode, () => {
  keyword.value = ''
  entryId.value = ''
  load()
})

onMounted(load)
</script>

<style scoped>
.qt-crumbs {
  display: flex;
  gap: 8px;
  margin: 8px 0;
}
.qt-bar-row {
  display: grid;
  grid-template-columns: 160px 1fr 48px;
  gap: 8px;
  align-items: center;
  margin: 6px 0;
}
.qt-bar {
  display: block;
  height: 10px;
  background: #0071e3;
  border-radius: 6px;
}
.hint.bad {
  color: var(--red, #ff3b30);
}
.fld > span {
  display: block;
  margin-bottom: 4px;
}
</style>
