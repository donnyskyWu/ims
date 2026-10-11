<template>
  <div class="page page-bi0-query">
    <div class="pg-h">
      <div>
        <h1>自定义查询</h1>
        <div class="sub">按已映射实体配置条件并查询</div>
      </div>
      <div class="acts">
        <button class="btn btn-sec btn-sm" type="button" @click="goMetadata">元数据维护</button>
      </div>
    </div>
    <div class="tabs">
      <div class="tab" :class="{ on: tab === 'builder' }" @click="tab = 'builder'">自定义查询</div>
      <div class="tab" :class="{ on: tab === 'mine' }" @click="switchMine">我的查询</div>
    </div>

    <template v-if="tab === 'builder'">
      <div class="card bi0-config-card">
        <div class="bi0-config-hd">
          <div
            class="collapse-h"
            :class="{ collapsed: !configOpen }"
            data-testid="bi-query-config-toggle"
            @click="configOpen = !configOpen"
          >
            <span class="caret">▼</span><h3>查询配置</h3>
          </div>
          <div class="rowline">
            <button class="btn btn-pri btn-sm" type="button" :disabled="running" @click="runAdhoc">执行查询</button>
            <button class="btn btn-sec btn-sm" type="button" @click="copySql">复制 SQL</button>
            <button class="btn btn-sec btn-sm" type="button" @click="saveDraft">保存为我的查询</button>
          </div>
        </div>
        <div v-show="configOpen" class="bi0-config-body">
          <div class="bi0-qb-root qb-layout">
            <div class="qb-form bi0-form-panel">
              <div class="bi0-form-grid">
                <label class="fld wide">
                  <span>数据源 <em class="req">*</em></span>
                  <select
                    v-model="builder.entityCode"
                    data-testid="bi-query-entity"
                    @change="loadFields"
                  >
                    <option value="">请选择已映射实体</option>
                    <option v-for="e in entities" :key="e.entityCode" :value="e.entityCode">
                      {{ e.entityName }}（{{ e.entityCode }}）
                    </option>
                  </select>
                </label>
                <label class="fld">
                  <span>行数上限</span>
                  <input
                    v-model.number="builder.limit"
                    data-testid="bi-query-limit"
                    type="number"
                    min="1"
                    max="1000"
                  />
                </label>
                <label class="fld">
                  <span>统计日期（起）</span>
                  <input v-model="builder.dateFrom" data-testid="bi-query-from" type="date" />
                </label>
                <label class="fld">
                  <span>统计日期（止）</span>
                  <input v-model="builder.dateTo" data-testid="bi-query-to" type="date" />
                </label>
                <label class="fld wide">
                  <span>条件值</span>
                  <input
                    v-model="builder.condValue"
                    data-testid="bi-query-cond"
                    placeholder="可选，精确匹配首个展示字段"
                  />
                </label>
              </div>
              <div class="qb-row">
                <label>展示字段</label>
                <div class="qb-chips" data-testid="bi-query-select-fields">
                  <label
                    v-for="f in fields"
                    :key="f.fieldCode"
                    class="chip"
                    :class="{ off: !builder.selectFields.includes(f.fieldCode) }"
                    :data-field-code="f.fieldCode"
                    @click.prevent="onPickField"
                  >
                    <input type="checkbox" tabindex="-1" :checked="builder.selectFields.includes(f.fieldCode)" />
                    {{ f.displayName }}
                  </label>
                  <span v-if="fields.length" class="qb-val-muted">多选 · 点击加入展示</span>
                  <span v-else class="qb-val-muted">先选数据源</span>
                </div>
              </div>
              <div class="bi0-form-grid" style="margin-top: 12px">
                <label class="fld">
                  <span>计算方式</span>
                  <select v-model="builder.aggFunc" data-testid="bi-query-agg">
                    <option value="DETAIL">明细</option>
                    <option value="SUM">SUM</option>
                    <option value="COUNT">COUNT</option>
                  </select>
                </label>
                <label class="fld">
                  <span>计算字段</span>
                  <select v-model="builder.aggField" data-testid="bi-query-agg-field">
                    <option value="">请选择</option>
                    <option v-for="f in aggFieldOptions" :key="f.fieldCode" :value="f.fieldCode">
                      {{ f.displayName }}
                    </option>
                  </select>
                </label>
                <label class="fld">
                  <span>汇总字段</span>
                  <select v-model="builder.groupBy" multiple data-testid="bi-query-group" class="bi0-multi">
                    <option v-for="f in fields" :key="'g' + f.fieldCode" :value="f.fieldCode">{{ f.displayName }}</option>
                  </select>
                </label>
                <label class="fld">
                  <span>关联表</span>
                  <select v-model="builder.joinTable" data-testid="bi-query-join">
                    <option value="">不关联</option>
                    <option v-for="j in joinOptions" :key="j.table" :value="j.table">{{ j.label }}</option>
                  </select>
                </label>
                <label class="fld">
                  <span>排序字段</span>
                  <select v-model="builder.orderField" data-testid="bi-query-order">
                    <option value="">不排序</option>
                    <option v-for="f in fields" :key="'o' + f.fieldCode" :value="f.fieldCode">{{ f.displayName }}</option>
                  </select>
                </label>
                <label class="fld">
                  <span>排序方向</span>
                  <select v-model="builder.orderDir">
                    <option value="ASC">升序</option>
                    <option value="DESC">降序</option>
                  </select>
                </label>
              </div>
              <div class="qb-cond-hd"><b>条件</b></div>
              <table class="bi0-cond-table" data-testid="bi-query-conditions">
                <thead>
                  <tr><th>字段</th><th>运算符</th><th>值</th><th></th></tr>
                </thead>
                <tbody>
                  <tr v-for="(row, idx) in builder.condRows" :key="idx">
                    <td>
                      <select v-model="row.fieldCode">
                        <option value="">请选择</option>
                        <option v-for="f in fields" :key="f.fieldCode" :value="f.fieldCode">{{ f.displayName }}</option>
                      </select>
                    </td>
                    <td>
                      <select v-model="row.operator">
                        <option value="EQ">等于</option>
                        <option value="LIKE">包含</option>
                        <option value="RANGE">区间</option>
                      </select>
                    </td>
                    <td><input v-model="row.value" placeholder="条件值" /></td>
                    <td>
                      <button class="btn btn-sec btn-sm" type="button" @click="removeCond(idx)">删除</button>
                    </td>
                  </tr>
                </tbody>
              </table>
              <button class="btn btn-sec btn-sm" type="button" data-testid="bi-query-add-cond" @click="addCond">+ 添加条件</button>
              <p v-if="fieldHint" class="hint bi0-field-hint">{{ fieldHint }}</p>
              <p v-if="formError" class="hint bad" data-testid="bi-query-form-error">{{ formError }}</p>
              <div class="qb-cond-hd"><b>SQL 预览</b></div>
              <textarea class="code-edit fld-sql" readonly rows="4" :value="previewSql" />
            </div>
            <div class="qb-side">
              <div class="qb-side-hd">可选字段（只读 · entity/fields）</div>
              <button
                v-for="f in fields"
                :key="'s' + f.fieldCode"
                type="button"
                class="fi"
                :data-field-code="f.fieldCode"
                @click="onPickField"
              >
                {{ f.displayName }}
                <br /><span class="mono" style="font-size: 10px; color: var(--text2)">{{ f.fieldCode }}</span>
              </button>
              <p v-if="!fields.length" class="hint">先选数据源；未映射请去元数据维护</p>
            </div>
          </div>
        </div>
      </div>
      <div v-if="result && result.empty" class="card bi0-result-card">
        <div class="empty" data-testid="bi-query-result-empty">
          <div class="et">{{ result.emptyReason || '当前条件下暂无数据' }}</div>
          <div v-if="result.queryCostMs != null" class="csub">queryCostMs {{ result.queryCostMs }} ms</div>
        </div>
      </div>
      <div v-else-if="result" class="card bi0-result-card">
        <div class="hd-row bi0-result-hd">
          <div>
            <b>查询结果</b>
            <span class="csub" style="margin-left: 8px">
              共 {{ result.total }} 行
              <template v-if="result.queryCostMs != null"> · {{ result.queryCostMs }} ms</template>
            </span>
          </div>
        </div>
        <div class="tabs bi0-result-tabs">
          <div
            class="tab"
            :class="{ on: resultTab === 'list' }"
            data-testid="bi-query-result-tab-list"
            @click="resultTab = 'list'"
          >
            结果列表
          </div>
          <div
            class="tab"
            :class="{ on: resultTab === 'chart' }"
            data-testid="bi-query-result-tab-chart"
            @click="resultTab = 'chart'"
          >
            图表展示
          </div>
        </div>
        <template v-if="resultTab === 'list'">
          <div class="tbl-wrap">
            <table>
              <thead>
                <tr>
                  <th v-for="c in result.columns" :key="c">{{ columnLabel(c) }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, idx) in result.rows" :key="idx">
                  <td v-for="c in result.columns" :key="c">{{ row[c] }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-if="result.total > 0" class="pager" data-testid="bi-query-result-pager">
            <span class="pg-total">共 {{ result.total }} 条</span>
            <select class="pg-size" :value="resultPageSize" @change="changeResultPageSize">
              <option :value="10">10</option>
              <option :value="20">20</option>
              <option :value="50">50</option>
            </select>
            <span>条/页</span>
            <span class="pg-sp"></span>
            <span class="pg-n" :class="{ dis: resultPageNo <= 1 }" @click="gotoResultPage(resultPageNo - 1)">‹</span>
            <span
              v-for="n in resultPageList"
              :key="n"
              class="pg-n"
              :class="{ on: n === resultPageNo }"
              @click="gotoResultPage(n)"
            >
              {{ n }}
            </span>
            <span class="pg-n" :class="{ dis: resultPageNo >= resultPageCount }" @click="gotoResultPage(resultPageNo + 1)">
              ›
            </span>
          </div>
        </template>
        <template v-else>
          <div class="bi0-chart-pane">
            <div class="bi0-chart-bar">
              <div class="bi0-chart-type-row">
                <span class="csub bi0-chart-lbl">图表类型</span>
                <div class="pills bi0-chart-pills" data-testid="bi-query-chart-type">
                  <label
                    v-for="opt in chartTypeOptions"
                    :key="opt.value"
                    class="pill"
                    :class="{ on: chartType === opt.value }"
                  >
                    <input v-model="chartType" type="radio" :value="opt.value" />
                    <span>{{ opt.label }}</span>
                  </label>
                </div>
              </div>
              <div class="bi0-chart-axis-grid">
                <label class="fld">
                  <span>X 轴</span>
                  <select v-model="chartXCol" class="bi0-chart-qctl" data-testid="bi-query-chart-x">
                    <option v-for="c in result.columns" :key="'x' + c" :value="c">{{ columnLabel(c) }}</option>
                  </select>
                </label>
                <label class="fld">
                  <span>Y 轴</span>
                  <select v-model="chartYCol" class="bi0-chart-qctl" data-testid="bi-query-chart-y">
                    <option v-if="!numericColumnOptions.length" disabled value="">暂无数值字段</option>
                    <option v-for="c in numericColumnOptions" :key="'y' + c" :value="c">{{ columnLabel(c) }}</option>
                  </select>
                </label>
              </div>
            </div>
            <div v-if="chartSeries.length" class="bi0-chart-stage" data-testid="bi-query-chart-stage" v-html="chartSvg" />
            <div v-else class="bi0-chart-ph">
              <span>{{ chartEmptyHint }}</span>
            </div>
            <p class="hint bi0-chart-foot">
              图表基于当前页查询结果前 24 行生成；切换图表类型或轴字段即时重绘，无需重新执行查询。
            </p>
          </div>
        </template>
      </div>
    </template>

    <template v-else>
      <div class="card bi0-mine-card">
        <div class="bi0-mine-hd"><h3>已保存查询</h3></div>
        <div class="bi0-mine-body">
          <form class="qbar bi0-mine-qbar" @submit.prevent="loadMine">
            <label class="fld qbar-fld">
              <span class="sr-only">名称</span>
              <input v-model="mineFilter.queryName" data-testid="bi-query-name" placeholder="查询名称" />
            </label>
            <label class="fld qbar-fld qbar-fld--status">
              <span class="sr-only">状态</span>
              <select v-model="mineFilter.status" data-testid="bi-query-status">
                <option value="">全部状态</option>
                <option value="DRAFT">草稿</option>
                <option value="PUBLISHED">已发布</option>
              </select>
            </label>
            <button class="btn btn-sec btn-sm" type="submit" data-testid="bi-query-mine-search">查询</button>
          </form>
          <div class="tbl-wrap">
            <table>
              <thead>
                <tr>
                  <th>查询名称</th>
                  <th>实体</th>
                  <th>创建人</th>
                  <th>状态</th>
                  <th>更新时间</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="!mineRows.length">
                  <td colspan="6">
                    <div class="empty" data-testid="bi-query-mine-empty"><div class="et">{{ mineEmptyText }}</div></div>
                  </td>
                </tr>
                <tr v-for="row in mineRows" :key="row.id">
                  <td>{{ row.queryName }}</td>
                  <td class="mono">{{ row.entityCode }}</td>
                  <td>{{ row.creatorName }}</td>
                  <td>{{ row.status }}</td>
                  <td>{{ row.updatedAt }}</td>
                  <td>
                    <button class="btn-txt btn" type="button" @click="runSaved(row.id)">执行</button>
                    <button
                      v-if="row.status !== 'PUBLISHED'"
                      class="btn-txt btn"
                      type="button"
                      @click="publishRow(row.id)"
                    >
                      发布
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </template>
    <p v-if="toast" class="hint" style="margin-top: 10px">{{ toast }}</p>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { errorMessage, http } from '../../api/http'
import {
  bi0SvgBars,
  bi0SvgLine,
  bi0SvgPie,
  parseNumeric,
  truncateLabel,
  type ChartPoint,
} from './query-chart'

type FieldVo = { fieldCode: string; displayName: string; columnName: string; queryConditionType?: string }
type JoinOpt = { table: string; entityCode: string; label: string }
type EntityOpt = { entityCode: string; entityName: string; tableName?: string; joins?: JoinOpt[] }
type CondRow = { fieldCode: string; operator: string; value: string }
type QueryRow = {
  id: string
  queryName: string
  entityCode: string
  status: string
  creatorName: string
  updatedAt: string
}
type QueryResult = {
  columns: string[]
  rows: Record<string, unknown>[]
  total: number
  pageNo?: number
  pageSize?: number
  queryCostMs?: number
  empty?: boolean
  sql?: string
  emptyReason?: string
}

const router = useRouter()
const tab = ref<'builder' | 'mine'>('builder')
const entities = ref<EntityOpt[]>([])
const fields = ref<FieldVo[]>([])
const fieldHint = ref('')
const toast = ref('')
const formError = ref('')
const running = ref(false)
const result = ref<QueryResult | null>(null)
const previewSql = ref('SELECT … FROM …（执行后展示实际 SQL）')
const configOpen = ref(true)
const resultTab = ref<'list' | 'chart'>('list')
const resultPageNo = ref(1)
const resultPageSize = ref(20)
const lastRunQueryId = ref<string | null>(null)
const chartTypeOptions = [
  { value: 'bar' as const, label: '柱状图' },
  { value: 'line' as const, label: '折线图' },
  { value: 'pie' as const, label: '饼图' },
]
const chartType = ref<'bar' | 'line' | 'pie'>('bar')
const chartXCol = ref('')
const chartYCol = ref('')
const resultFieldMap = ref<Record<string, string>>({})

const builder = reactive({
  entityCode: '',
  selectFields: [] as string[],
  limit: 100,
  dateFrom: '',
  dateTo: '',
  condValue: '',
  aggFunc: 'DETAIL',
  aggField: '',
  groupBy: [] as string[],
  joinTable: '',
  orderField: '',
  orderDir: 'ASC',
  condRows: [{ fieldCode: '', operator: 'EQ', value: '' }] as CondRow[],
})

const joinOptions = computed(() => entities.value.find((e) => e.entityCode === builder.entityCode)?.joins || [])
const aggFieldOptions = computed(() => fields.value)

const mineFilter = reactive({ queryName: '', status: '' })
const appliedMine = reactive({ queryName: '', status: '' })
const mineRows = ref<QueryRow[]>([])
const mineEmptyText = computed(() =>
  appliedMine.queryName || appliedMine.status ? '当前筛选下暂无查询' : '暂无保存的查询',
)

const resultPageCount = computed(() =>
  result.value ? Math.max(1, Math.ceil(result.value.total / resultPageSize.value)) : 1,
)

const resultPageList = computed(() => {
  const count = resultPageCount.value
  const cur = resultPageNo.value
  const end = Math.min(count, Math.max(cur + 2, 5))
  const start = Math.max(1, end - 4)
  const list: number[] = []
  for (let n = start; n <= end; n += 1) list.push(n)
  return list
})

const numericColumnOptions = computed(() => {
  if (!result.value?.rows.length) return result.value?.columns ?? []
  return (result.value.columns ?? []).filter((c) =>
    result.value!.rows.some((row) => parseNumeric(row[c]) !== 0 || String(row[c] ?? '').match(/\d/)),
  )
})

const chartSeries = computed((): ChartPoint[] => {
  if (!result.value?.rows.length || !chartXCol.value || !chartYCol.value) return []
  return result.value.rows.slice(0, 24).map((row, idx) => ({
    k: truncateLabel(String(row[chartXCol.value] ?? `#${idx + 1}`)),
    v: Math.max(0, parseNumeric(row[chartYCol.value])),
  }))
})

const chartSvg = computed(() => {
  const series = chartSeries.value
  if (!series.length) return ''
  if (chartType.value === 'pie') return bi0SvgPie(series)
  if (chartType.value === 'line') return bi0SvgLine(series)
  return bi0SvgBars(series)
})

const chartEmptyHint = computed(() => {
  if (!numericColumnOptions.value.length) return '结果中未识别到数值列，请调整展示字段或执行聚合查询'
  if (!chartYCol.value) return '请选择含数值的 Y 轴字段'
  if (!chartXCol.value) return '请选择 X 轴维度字段'
  return '当前轴字段组合暂无可绘制的数据'
})

function columnLabel(code: string): string {
  return resultFieldMap.value[code] || fields.value.find((f) => f.fieldCode === code)?.displayName || code
}

function onPickField(ev: MouseEvent) {
  const code = (ev.currentTarget as HTMLElement).dataset.fieldCode || ''
  const field = fields.value.find((f) => f.fieldCode === code)
  if (!field) return
  if (!builder.selectFields.includes(code)) builder.selectFields.push(code)
  toast.value = `已加入展示：${field.displayName}`
}

function addCond() {
  builder.condRows.push({ fieldCode: '', operator: 'EQ', value: '' })
}

function removeCond(index: number) {
  if (builder.condRows.length <= 1) {
    toast.value = '至少保留一个条件行'
    return
  }
  builder.condRows.splice(index, 1)
}

function syncResultFieldMap() {
  const map: Record<string, string> = {}
  for (const f of fields.value) map[f.fieldCode] = f.displayName
  resultFieldMap.value = map
}

function resetChartAxes(cols: string[]) {
  chartXCol.value = cols[0] ?? ''
  const numeric = cols.filter((c) =>
    (result.value?.rows ?? []).some((row) => String(row[c] ?? '').match(/\d/)),
  )
  chartYCol.value = numeric[numeric.length - 1] ?? cols[1] ?? cols[0] ?? ''
}

watch(
  () => result.value?.columns,
  (cols) => {
    if (cols?.length) resetChartAxes(cols)
  },
)

function rejectedCode(error: unknown): number {
  if (error && typeof error === 'object' && 'code' in error) {
    return Number((error as { code?: number }).code || 0)
  }
  return 0
}

function dateEdge(): string {
  const from = builder.dateFrom
  const to = builder.dateTo
  if ((from && !to) || (!from && to)) return '请同时填写开始和结束日期'
  if (from && to && from > to) return '开始日期不能晚于结束日期'
  return ''
}

function limitEdge(): string {
  const limit = Number(builder.limit)
  if (!Number.isInteger(limit) || limit < 1 || limit > 1000) return '行数上限须为 1~1000'
  return ''
}

const payloadConfig = computed(() => {
  const selectFields = builder.selectFields.length ? builder.selectFields : fields.value.map((f) => f.fieldCode)
  const conditions: { fieldCode: string; operator: string; value: string }[] = []
  for (const row of builder.condRows) {
    if (!row.fieldCode) continue
    conditions.push({ fieldCode: row.fieldCode, operator: row.operator || 'EQ', value: row.value })
  }
  const probe = builder.condValue.trim()
  if (probe && selectFields.length) {
    conditions.push({ fieldCode: selectFields[0], operator: 'EQ', value: probe })
  }
  if (builder.dateFrom && builder.dateTo) {
    const rangeField = fields.value.find((f) => (f.queryConditionType || '').toUpperCase() === 'RANGE')
    if (rangeField) {
      conditions.push({
        fieldCode: rangeField.fieldCode,
        operator: 'RANGE',
        value: `${builder.dateFrom},${builder.dateTo}`,
      })
    }
  }
  const orderBy: string[] = []
  if (builder.orderField) {
    orderBy.push(builder.orderDir === 'DESC' ? `-${builder.orderField}` : builder.orderField)
  }
  return {
    selectFields,
    conditions,
    orderBy,
    limit: Number(builder.limit) || 100,
    aggFunc: builder.aggFunc === 'DETAIL' ? '' : builder.aggFunc,
    aggField: builder.aggField,
    groupBy: [...builder.groupBy],
    joinTable: builder.joinTable,
  }
})

function quoteIdent(name: string) {
  return /^[a-zA-Z_][a-zA-Z0-9_]*$/.test(name) ? name : ''
}

function refreshPreview() {
  const table = quoteIdent(entities.value.find((e) => e.entityCode === builder.entityCode)?.tableName || '')
  const cols = (payloadConfig.value.selectFields || [])
    .map((code) => {
      const field = fields.value.find((f) => f.fieldCode === code)
      const column = quoteIdent(field?.columnName || '')
      return column ? `\`${column}\` AS \`${code}\`` : ''
    })
    .filter(Boolean)
  if (!table || !cols.length) {
    previewSql.value = 'SELECT … FROM … WHERE tenant_id = :tenant_id'
    return
  }
  let sql = `SELECT ${cols.join(', ')} FROM \`${table}\` WHERE deleted = 0 AND tenant_id = :tenant_id`
  payloadConfig.value.conditions.forEach((cond, idx) => {
    const field = fields.value.find((f) => f.fieldCode === cond.fieldCode)
    const column = quoteIdent(field?.columnName || '')
    if (!column) return
    if (cond.operator === 'LIKE') sql += ` AND \`${column}\` LIKE :p${idx}`
    else if (cond.operator === 'RANGE') sql += ` AND \`${column}\` BETWEEN :p${idx}_lo AND :p${idx}_hi`
    else sql += ` AND \`${column}\` = :p${idx}`
  })
  if (payloadConfig.value.aggFunc === 'SUM' || payloadConfig.value.aggFunc === 'COUNT') {
    sql += ' /* GROUP BY */'
  }
  sql += ` LIMIT ${Number(builder.limit) || 100}`
  previewSql.value = sql
}

async function loadEntities() {
  try {
    const res = await http.get('/bi/query/sources')
    entities.value = res.data.data?.list || []
  } catch (error: unknown) {
    fieldHint.value = errorMessage(error)
  }
}

async function loadFields() {
  fields.value = []
  fieldHint.value = ''
  if (!builder.entityCode) return
  try {
    const res = await http.get(`/collect/metadata/entity/${builder.entityCode}/fields`)
    fields.value = res.data.data?.fields || []
    builder.selectFields = []
    builder.aggField = ''
    builder.groupBy = []
    builder.joinTable = ''
    builder.orderField = ''
    syncResultFieldMap()
    refreshPreview()
  } catch (error: unknown) {
    if (rejectedCode(error) === 1261) {
      fieldHint.value = '实体未映射（1261）· 请点击右上角「元数据维护」完成 COLLECT P4m 映射'
      return
    }
    fieldHint.value = errorMessage(error)
  }
}

async function copySql() {
  formError.value = ''
  if (!builder.entityCode) {
    formError.value = '请选择数据源'
    return
  }
  const limitMsg = limitEdge()
  if (limitMsg) {
    formError.value = limitMsg
    return
  }
  try {
    const res = await http.post('/bi/query/preview', {
      entityCode: builder.entityCode,
      config: payloadConfig.value,
    })
    const sql = String(res.data.data?.sql || '')
    previewSql.value = sql
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(sql)
    }
    toast.value = 'SQL 已复制到剪贴板'
  } catch (error: unknown) {
    formError.value = errorMessage(error)
    toast.value = formError.value
  }
}

async function ensureSaved(name: string) {
  try {
    const res = await http.post('/bi/query', {
      queryName: name,
      entityCode: builder.entityCode,
      status: 'DRAFT',
      config: payloadConfig.value,
    })
    return res.data.data.id as string
  } catch (error: unknown) {
    const msg = rejectedCode(error) === 1261 ? '实体未映射（1261）' : errorMessage(error)
    formError.value = msg
    toast.value = msg
    return null
  }
}

async function fetchRunResult(queryId: string, pageNo = resultPageNo.value, pageSize = resultPageSize.value) {
  const run = await http.post(`/bi/query/${queryId}/run`, { pageNo, pageSize })
  result.value = run.data.data
  previewSql.value = run.data.data.sql || previewSql.value
  resultPageNo.value = run.data.data.pageNo ?? pageNo
  resultPageSize.value = run.data.data.pageSize ?? pageSize
  lastRunQueryId.value = queryId
  if (run.data.data.columns?.length) resetChartAxes(run.data.data.columns)
}

async function runAdhoc() {
  formError.value = ''
  toast.value = ''
  result.value = null
  resultPageNo.value = 1
  resultTab.value = 'list'
  const dates = dateEdge()
  if (dates) {
    formError.value = dates
    return
  }
  const limitMsg = limitEdge()
  if (limitMsg) {
    formError.value = limitMsg
    return
  }
  if (!builder.entityCode) {
    formError.value = '请选择数据源'
    return
  }
  if (builder.dateFrom && builder.dateTo && !fields.value.some((f) => (f.queryConditionType || '').toUpperCase() === 'RANGE')) {
    formError.value = '当前实体没有日期字段'
    return
  }
  running.value = true
  try {
    const id = await ensureSaved(`临时查询 ${new Date().toLocaleTimeString()}`)
    if (!id) return
    syncResultFieldMap()
    await fetchRunResult(id, 1, resultPageSize.value)
  } catch (error: unknown) {
    formError.value = errorMessage(error)
  } finally {
    running.value = false
  }
}

async function saveDraft() {
  const blocked = dateEdge() || limitEdge()
  if (blocked) {
    formError.value = blocked
    return
  }
  if (!builder.entityCode) {
    formError.value = '请选择数据源'
    return
  }
  const name = window.prompt('查询名称', '我的查询')
  if (!name?.trim()) return
  const id = await ensureSaved(name.trim())
  if (id) toast.value = '已保存'
}

async function loadMine() {
  appliedMine.queryName = mineFilter.queryName.trim()
  appliedMine.status = mineFilter.status
  try {
    const res = await http.get('/bi/query/page', {
      params: { pageNo: 1, pageSize: 50, queryName: appliedMine.queryName, status: appliedMine.status },
    })
    mineRows.value = res.data.data?.list || []
  } catch (error: unknown) {
    mineRows.value = []
    toast.value = errorMessage(error)
  }
}

function switchMine() {
  tab.value = 'mine'
  loadMine()
}

async function gotoResultPage(page: number) {
  if (!lastRunQueryId.value || page < 1 || page > resultPageCount.value || page === resultPageNo.value) return
  running.value = true
  try {
    await fetchRunResult(lastRunQueryId.value, page, resultPageSize.value)
  } catch (error: unknown) {
    formError.value = errorMessage(error)
  } finally {
    running.value = false
  }
}

async function changeResultPageSize(ev: Event) {
  const size = Number((ev.target as HTMLSelectElement).value)
  if (!lastRunQueryId.value || !size) return
  resultPageSize.value = size
  resultPageNo.value = 1
  running.value = true
  try {
    await fetchRunResult(lastRunQueryId.value, 1, size)
  } catch (error: unknown) {
    formError.value = errorMessage(error)
  } finally {
    running.value = false
  }
}

async function runSaved(id: string) {
  try {
    const detail = await http.get(`/bi/query/${id}`)
    const entityCode = detail.data.data?.entityCode as string | undefined
    if (entityCode && entityCode !== builder.entityCode) {
      builder.entityCode = entityCode
      await loadFields()
    } else {
      syncResultFieldMap()
    }
    tab.value = 'builder'
    resultPageNo.value = 1
    resultTab.value = 'list'
    await fetchRunResult(id, 1, resultPageSize.value)
    toast.value = '已加载结果'
  } catch (error: unknown) {
    toast.value = errorMessage(error)
  }
}

async function publishRow(id: string) {
  try {
    await http.put(`/bi/query/${id}/publish`, {})
    toast.value = '已发布'
    await loadMine()
  } catch (error: unknown) {
    toast.value = errorMessage(error)
  }
}

function goMetadata() {
  router.push('/ims/collect/metadata')
}

onMounted(() => {
  loadEntities()
})
</script>

<style scoped>
.bi0-form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px 16px;
}
.bi0-form-grid .fld.wide {
  grid-column: 1 / -1;
}
.bi0-form-panel .fld > span {
  display: block;
}
.bi0-field-hint {
  margin: 4px 0 0;
}
.hint.bad {
  color: var(--red);
  margin-top: 10px;
}
.fld-sql {
  width: 100%;
  min-height: 88px;
  margin-top: 0;
}
.bi0-mine-qbar {
  align-items: flex-end;
  gap: 12px;
  flex-wrap: wrap;
}
.bi0-mine-qbar .qbar-fld {
  margin: 0;
  min-width: 160px;
}
.bi0-mine-qbar .qbar-fld--status {
  min-width: 130px;
}
.bi0-mine-qbar .fld input,
.bi0-mine-qbar .fld select {
  width: 100%;
}
.qb-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.qb-chips .chip {
  margin: 0;
}
.fi {
  display: block;
  width: 100%;
  text-align: left;
  border: 0;
  background: transparent;
  cursor: pointer;
}
.bi0-multi {
  min-height: 72px;
}
.bi0-cond-table {
  width: 100%;
  margin: 8px 0;
}
.bi0-cond-table select,
.bi0-cond-table input {
  width: 100%;
}
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
</style>
