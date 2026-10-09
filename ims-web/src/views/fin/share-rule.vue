<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>分成规则</h1>
        <div class="sub">FIN-003 · 规则维护 · 比例合计 1.0000（1146）· 同范围冲突须确认（1147）· 阶梯试算</div>
      </div>
      <button class="btn btn-pri btn-sm" type="button" data-testid="fin-share-rule-create" @click="openCreate">
        创建规则
      </button>
    </div>

    <form class="qbar" @submit.prevent="loadList">
      <select v-model="query.shareTarget" data-testid="fin-share-rule-filter-target" style="width: 140px">
        <option value="">全部对象</option>
        <option value="DAREN">达人</option>
        <option value="REALNAME">实名人</option>
        <option value="TEAM">团队</option>
      </select>
      <select v-model="query.status" data-testid="fin-share-rule-filter-status" style="width: 120px">
        <option value="">全部状态</option>
        <option value="ENABLED">启用</option>
        <option value="DISABLED">停用</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="button" data-testid="fin-share-rule-query" @click="loadList">查询</button>
      <button class="btn btn-sec btn-sm" type="button" data-testid="fin-share-rule-reset" @click="resetQuery">重置</button>
    </form>

    <p class="hint" data-testid="fin-share-rule-sum" style="margin: 8px 0">同范围启用比例合计 {{ sumText }}</p>
    <div v-if="error" class="hint" style="color: var(--red); margin: 8px 0">{{ error }}</div>

    <div class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>规则名称</th>
              <th>分成对象</th>
              <th>基数</th>
              <th>比例方式</th>
              <th>适用范围</th>
              <th>优先级</th>
              <th>版本</th>
              <th>状态</th>
              <th>生效期</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="10"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!rows.length">
              <td colspan="10"><div class="empty"><div class="et">暂无分成规则</div></div></td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.id" :data-testid="'fin-share-rule-row-' + row.id">
              <td>{{ row.ruleName }}</td>
              <td><span class="tag" :style="targetStyle(row.shareTarget)">{{ targetLabel(row.shareTarget) }}</span></td>
              <td>{{ baseLabel(row.baseType) }}</td>
              <td data-testid="fin-share-rule-rate" :title="rateTitle(row)">{{ rateSummary(row) }}</td>
              <td data-testid="fin-share-rule-scope" :title="scopeTitle(row.scope)">{{ scopeSummary(row.scope) }}</td>
              <td class="num">{{ row.priority }}</td>
              <td>V{{ row.version }}</td>
              <td>
                <span class="tag" :style="row.status === 'ENABLED' ? 'color: var(--green)' : 'color: var(--gray)'">{{ row.status === 'ENABLED' ? '启用' : '停用' }}</span>
              </td>
              <td>{{ row.effectiveRange?.from }} ~ {{ row.effectiveRange?.to || '长期' }}</td>
              <td>
                <button class="btn btn-sec btn-sm" type="button" @click="openEdit(row)">编辑</button>
                <button class="btn btn-sec btn-sm" type="button" data-testid="fin-share-rule-simulate" @click="openSimulate(row)">
                  试算
                </button>
                <button
                  v-if="row.status === 'ENABLED'"
                  class="btn btn-sec btn-sm"
                  type="button"
                  data-testid="fin-share-rule-disable"
                  @click="askDisable(row)"
                >
                  停用
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="drawerOpen" class="mask on" @click.self="drawerOpen = false"></div>
    <div v-if="drawerOpen" class="drawer on" data-testid="fin-share-rule-drawer" style="width: 760px">
      <div class="drawer-h">
        <b>{{ editingId ? '编辑分成规则' : '创建分成规则' }}</b>
        <button type="button" class="btn btn-sec btn-sm" @click="drawerOpen = false">关闭</button>
      </div>
      <div class="drawer-b">
        <p class="hint">规则变更不影响已生成分成单，重算需人工触发</p>
        <label class="fld">
          <span>规则名称</span>
          <input v-model="form.ruleName" data-testid="fin-share-rule-name" maxlength="64" />
        </label>
        <label class="fld">
          <span>分成对象</span>
          <select v-model="form.shareTarget" data-testid="fin-share-rule-target">
            <option value="DAREN">达人</option>
            <option value="REALNAME">实名人</option>
            <option value="TEAM">团队</option>
          </select>
        </label>
        <label class="fld">
          <span>分成基数</span>
          <select v-model="form.baseType" data-testid="fin-share-rule-base">
            <option value="GMV">GMV</option>
            <option value="GROSS_PROFIT">毛利</option>
            <option value="NET_PROFIT">净利润</option>
          </select>
        </label>
        <label class="fld">
          <span>比例方式</span>
          <select v-model="form.rateType" data-testid="fin-share-rule-rate-type">
            <option value="FIXED">固定比例</option>
            <option value="LADDER">阶梯</option>
          </select>
        </label>
        <label v-if="form.rateType === 'FIXED'" class="fld">
          <span>固定比例（%）</span>
          <input v-model="form.fixedPercent" data-testid="fin-share-rule-fixed-rate" inputmode="decimal" />
        </label>
        <div v-else>
          <div v-for="(ladder, index) in form.ladders" :key="index" class="acts" style="gap: 8px; margin-bottom: 8px">
            <label class="fld" style="flex: 1">
              <span>下限</span>
              <input v-model="ladder.min" data-testid="fin-share-rule-ladder-min" />
            </label>
            <label class="fld" style="flex: 1">
              <span>上限（末档可空）</span>
              <input v-model="ladder.max" data-testid="fin-share-rule-ladder-max" />
            </label>
            <label class="fld" style="flex: 1">
              <span>比例（%）</span>
              <input v-model="ladder.rate" data-testid="fin-share-rule-ladder-rate" />
            </label>
            <button
              v-if="form.ladders.length > 1"
              class="btn btn-sec btn-sm"
              type="button"
              data-testid="fin-share-rule-ladder-remove"
              @click="form.ladders.splice(index, 1)"
            >
              删除
            </button>
          </div>
          <button class="btn btn-sec btn-sm" type="button" data-testid="fin-share-rule-ladder-add" @click="form.ladders.push({ min: '', max: '', rate: '' })">
            添加档
          </button>
          <p v-if="ladderOverlap" class="hint" data-testid="fin-share-rule-ladder-error" style="color: var(--red)">1146 阶梯区间重叠</p>
        </div>
        <label class="fld">
          <span>平台（逗号分隔，可空）</span>
          <input v-model="form.platforms" data-testid="fin-share-rule-platforms" placeholder="DYS,KS" />
        </label>
        <label class="fld">
          <span>账号 ID（逗号分隔，可空）</span>
          <input v-model="form.accountIds" data-testid="fin-share-rule-accounts" />
        </label>
        <label class="fld">
          <span>IP 组 ID（逗号分隔，可空，与平台、账号同时生效）</span>
          <input v-model="form.ipGroups" data-testid="fin-share-rule-groups" placeholder="88001,88002" />
        </label>
        <label class="fld">
          <span>优先级</span>
          <input v-model="form.priority" data-testid="fin-share-rule-priority" />
        </label>
        <label class="fld">
          <span>生效开始</span>
          <input v-model="form.effectiveFrom" data-testid="fin-share-rule-from" type="date" />
        </label>
        <label class="fld">
          <span>生效结束（可空）</span>
          <input v-model="form.effectiveTo" data-testid="fin-share-rule-to" type="date" />
        </label>
        <p v-if="formError" class="hint" data-testid="fin-share-rule-error" style="color: var(--red)">{{ formError }}</p>
      </div>
      <div class="drawer-f">
        <button class="btn btn-sec btn-sm" type="button" @click="openDraftSimulate">试算</button>
        <button class="btn btn-pri btn-sm" type="button" data-testid="fin-share-rule-save" @click="save(false)">保存</button>
      </div>
    </div>

    <div v-if="simOpen" class="mask on" style="z-index: 120" @click.self="simOpen = false"></div>
    <div v-if="simOpen" class="drawer on" data-testid="fin-share-rule-sim-drawer" style="width: 640px; z-index: 130">
      <div class="drawer-h">
        <b>规则试算</b>
        <button type="button" class="btn btn-sec btn-sm" @click="simOpen = false">关闭</button>
      </div>
      <div class="drawer-b">
        <label class="fld">
          <span>试算基数（元）</span>
          <input v-model="simBase" data-testid="fin-share-rule-sim-base" />
        </label>
        <p v-if="simError" class="hint" data-testid="fin-share-rule-sim-error" style="color: var(--red)">{{ simError }}</p>
        <template v-if="simResult">
          <p data-testid="fin-share-rule-sim-amount">分成金额 ¥{{ fmt(simResult.shareAmount) }}</p>
          <table data-testid="fin-share-rule-sim-detail">
            <thead>
              <tr>
                <th>区间</th>
                <th>适用比例</th>
                <th>金额</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(line, index) in simResult.calcDetail" :key="index">
                <td>{{ line.range }}</td>
                <td>{{ (Number(line.rateApplied) * 100).toFixed(2) }}%</td>
                <td>¥{{ fmt(line.amount) }}</td>
              </tr>
            </tbody>
          </table>
        </template>
      </div>
      <div class="drawer-f">
        <button class="btn btn-pri btn-sm" type="button" data-testid="fin-share-rule-sim-submit" @click="runSimulate">
          计算
        </button>
      </div>
    </div>

    <div v-if="conflictOpen" class="mask on" style="z-index: 140" data-testid="fin-share-rule-conflict">
      <div class="card" style="position: fixed; z-index: 150; left: 50%; top: 28%; transform: translateX(-50%); width: 400px; padding: 16px">
        <b>优先级冲突</b>
        <p>存在同范围同对象优先级冲突规则，确认强制保存？</p>
        <div class="acts" style="gap: 8px">
          <button class="btn btn-pri btn-sm" type="button" data-testid="fin-share-rule-conflict-confirm" @click="save(true)">
            确认强制保存
          </button>
          <button class="btn btn-sec btn-sm" type="button" @click="conflictOpen = false">取消</button>
        </div>
      </div>
    </div>

    <div v-if="disableOpen" class="mask on" style="z-index: 140" data-testid="fin-share-rule-disable-dialog">
      <div class="card" style="position: fixed; z-index: 150; left: 50%; top: 28%; transform: translateX(-50%); width: 400px; padding: 16px">
        <b>停用规则</b>
        <p>历史分成单引用不受影响（FIN-S-R5）</p>
        <div class="acts" style="gap: 8px">
          <button class="btn btn-pri btn-sm" type="button" data-testid="fin-share-rule-disable-confirm" @click="confirmDisable">
            确认停用
          </button>
          <button class="btn btn-sec btn-sm" type="button" @click="disableOpen = false">取消</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { http } from '../../api/http'

type Scope = { platforms?: string[]; accountIds?: number[]; ipGroupIds?: number[] }
type Ladder = { min: number; max: number | null; rate: number }
type RuleRow = {
  id: number
  ruleName: string
  shareTarget: string
  baseType: string
  rateType: string
  fixedRate?: number | null
  ladderConfig?: Ladder[] | null
  scope: Scope
  priority: number
  version: number
  status: string
  effectiveRange?: { from?: string; to?: string | null }
}
type SimResult = { simulateBase: number; shareAmount: number; calcDetail: Array<{ range: string; rateApplied: number; amount: number }> }
type ApiErr = { code?: number; msg?: string }

const loading = ref(false)
const error = ref('')
const formError = ref('')
const rows = ref<RuleRow[]>([])
const query = reactive({ shareTarget: '', status: '' })
const drawerOpen = ref(false)
const editingId = ref<number | null>(null)
const clientToken = ref('')
const conflictOpen = ref(false)
const disableOpen = ref(false)
const disableRow = ref<RuleRow | null>(null)
const simOpen = ref(false)
const simRuleId = ref<number | null>(null)
const simBase = ref('10000')
const simError = ref('')
const simResult = ref<SimResult | null>(null)
const form = reactive({
  ruleName: '',
  shareTarget: 'DAREN',
  baseType: 'NET_PROFIT',
  rateType: 'FIXED',
  fixedPercent: '',
  platforms: '',
  accountIds: '',
  ipGroups: '',
  priority: '10',
  effectiveFrom: '2026-10-08',
  effectiveTo: '',
  ladders: [
    { min: '0', max: '10000', rate: '10' },
    { min: '10000', max: '', rate: '20' },
  ],
})

const sumText = computed(() => {
  const groups = new Map<string, Map<string, RuleRow>>()
  for (const row of rows.value) {
    if (row.status !== 'ENABLED' || row.rateType !== 'FIXED' || row.fixedRate == null) continue
    const key = scopeKey(row.scope)
    if (!groups.has(key)) groups.set(key, new Map())
    const bucket = groups.get(key)!
    const prev = bucket.get(row.shareTarget)
    if (!prev || row.priority >= prev.priority) bucket.set(row.shareTarget, row)
  }
  if (!groups.size) return '暂无'
  const parts: string[] = []
  for (const [key, bucket] of groups) {
    const basis = [...bucket.values()].reduce((acc, row) => acc + Math.round(Number(row.fixedRate) * 10000), 0)
    const parsed = JSON.parse(key) as Scope
    const account = parsed.accountIds?.[0]
    const group = parsed.ipGroupIds?.[0]
    const label = account
      ? `账号#${account}`
      : group
        ? `IP组#${group}`
        : parsed.platforms?.length
          ? parsed.platforms.join('+')
          : '全范围'
    parts.push(`${label} ${(basis / 10000).toFixed(4)}`)
  }
  return parts.join('；')
})

function scopeKey(scope: Scope | undefined) {
  return JSON.stringify({
    platforms: [...(scope?.platforms || [])].map(String).sort(),
    accountIds: [...(scope?.accountIds || [])].map(Number).sort((a, b) => a - b),
    ipGroupIds: [...(scope?.ipGroupIds || [])].map(Number).sort((a, b) => a - b),
  })
}

function fmt(n: unknown) {
  return Number(n || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function targetLabel(value: string) {
  return ({ DAREN: '达人', REALNAME: '实名人', TEAM: '团队' } as Record<string, string>)[value] || value
}

function baseLabel(value: string) {
  return ({ GMV: 'GMV', GROSS_PROFIT: '毛利', NET_PROFIT: '净利润' } as Record<string, string>)[value] || value
}

function rateSummary(row: RuleRow) {
  if (row.rateType === 'FIXED') return `固定 ${(Number(row.fixedRate || 0) * 100).toFixed(2)}%`
  return `阶梯 ${row.ladderConfig?.length || 0} 档`
}

function rateTitle(row: RuleRow) {
  if (row.rateType !== 'LADDER') return rateSummary(row)
  const lines = (row.ladderConfig || []).map((item) => {
    const upper = item.max == null ? '∞' : item.max
    return `${item.min}~${upper} ${(Number(item.rate) * 100).toFixed(2)}%`
  })
  return lines.length ? lines.join('；') : '阶梯'
}

function scopeSummary(scope: Scope | undefined) {
  const platforms = scope?.platforms?.length || 0
  const accounts = scope?.accountIds?.length || 0
  const groups = scope?.ipGroupIds?.length || 0
  if (!platforms && !accounts && !groups) return '全部'
  return `平台×${platforms}+账号×${accounts}+IP组×${groups}`
}

function scopeTitle(scope: Scope | undefined) {
  const platforms = scope?.platforms?.length ? scope.platforms.join(',') : '—'
  const accounts = scope?.accountIds?.length ? scope.accountIds.join(',') : '—'
  const groups = scope?.ipGroupIds?.length ? scope.ipGroupIds.join(',') : '—'
  return `平台 ${platforms}；账号 ${accounts}；IP组 ${groups}`
}

function targetStyle(value: string) {
  if (value === 'DAREN') return 'color:#722ed1'
  if (value === 'REALNAME') return 'color:#13c2c2'
  if (value === 'TEAM') return 'color:#1677ff'
  return ''
}

const ladderOverlap = computed(() => {
  if (form.rateType !== 'LADDER') return false
  const rows = form.ladders
    .map((row) => ({
      min: Number(row.min),
      max: row.max === '' ? null : Number(row.max),
    }))
    .filter((row) => Number.isFinite(row.min))
    .sort((a, b) => a.min - b.min)
  for (let index = 0; index < rows.length - 1; index += 1) {
    const upper = rows[index].max
    if (upper == null || rows[index + 1].min < upper) return true
  }
  return false
})

function resetForm() {
  form.ruleName = ''
  form.shareTarget = 'DAREN'
  form.baseType = 'NET_PROFIT'
  form.rateType = 'FIXED'
  form.fixedPercent = ''
  form.platforms = ''
  form.accountIds = ''
  form.ipGroups = ''
  form.priority = '10'
  form.effectiveFrom = '2026-10-08'
  form.effectiveTo = ''
  form.ladders = [
    { min: '0', max: '10000', rate: '10' },
    { min: '10000', max: '', rate: '20' },
  ]
}

function splitIds(raw: string) {
  return raw
    .split(/[,，\s]+/)
    .map((item) => item.trim())
    .filter(Boolean)
}

function parseIdList(raw: string) {
  const ids: number[] = []
  for (const token of splitIds(raw)) {
    if (!/^[1-9]\d*$/.test(token)) return null
    ids.push(Number(token))
  }
  return ids
}

function buildPayload(confirmConflict: boolean) {
  const accountIds = parseIdList(form.accountIds)
  const ipGroupIds = parseIdList(form.ipGroups)
  if (!accountIds || !ipGroupIds) {
    formError.value = '1001 适用范围编号非法'
    return null
  }
  const payload: Record<string, unknown> = {
    ruleName: form.ruleName.trim(),
    shareTarget: form.shareTarget,
    baseType: form.baseType,
    rateType: form.rateType,
    scope: {
      platforms: splitIds(form.platforms),
      accountIds,
      ipGroupIds,
    },
    priority: Number(form.priority),
    effectiveRange: { from: form.effectiveFrom, to: form.effectiveTo || undefined },
    confirmConflict,
  }
  if (!editingId.value) payload.clientToken = clientToken.value
  if (form.rateType === 'FIXED') {
    payload.fixedRate = Number((Number(form.fixedPercent) / 100).toFixed(4))
  } else {
    payload.ladderConfig = form.ladders.map((row) => ({
      min: Number(row.min),
      max: row.max === '' ? null : Number(row.max),
      rate: Number((Number(row.rate) / 100).toFixed(4)),
    }))
  }
  return payload
}

function errText(err: unknown) {
  const body = err as ApiErr
  if (body?.code) return `${body.code} ${body.msg || ''}`.trim()
  return '请求失败'
}

function resetQuery() {
  query.shareTarget = ''
  query.status = ''
  loadList()
}

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const res = await http.get('/fin/share/rules', {
      params: {
        pageNo: 1,
        pageSize: 50,
        shareTarget: query.shareTarget || undefined,
        status: query.status || undefined,
      },
    })
    rows.value = res.data?.data?.list || []
  } catch (err) {
    error.value = errText(err)
    rows.value = []
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = null
  clientToken.value = `${Date.now()}-${Math.random().toString(16).slice(2)}`
  formError.value = ''
  conflictOpen.value = false
  resetForm()
  drawerOpen.value = true
}

function openEdit(row: RuleRow) {
  editingId.value = row.id
  formError.value = ''
  conflictOpen.value = false
  form.ruleName = row.ruleName
  form.shareTarget = row.shareTarget
  form.baseType = row.baseType
  form.rateType = row.rateType
  form.fixedPercent = row.fixedRate == null ? '' : (Number(row.fixedRate) * 100).toFixed(2)
  form.platforms = (row.scope?.platforms || []).join(',')
  form.accountIds = (row.scope?.accountIds || []).join(',')
  form.ipGroups = (row.scope?.ipGroupIds || []).join(',')
  form.priority = String(row.priority)
  form.effectiveFrom = row.effectiveRange?.from || ''
  form.effectiveTo = row.effectiveRange?.to || ''
  form.ladders = (row.ladderConfig || []).map((item) => ({
    min: String(item.min),
    max: item.max == null ? '' : String(item.max),
    rate: (Number(item.rate) * 100).toFixed(2),
  }))
  if (!form.ladders.length) {
    form.ladders = [
      { min: '0', max: '10000', rate: '10' },
      { min: '10000', max: '', rate: '20' },
    ]
  }
  drawerOpen.value = true
}

async function save(confirmConflict: boolean) {
  formError.value = ''
  try {
    const payload = buildPayload(confirmConflict)
    if (!payload) return
    if (editingId.value) await http.put(`/fin/share/rule/${editingId.value}`, payload)
    else await http.post('/fin/share/rule', payload)
    conflictOpen.value = false
    drawerOpen.value = false
    await loadList()
  } catch (err) {
    const body = err as ApiErr
    if (body?.code === 1147) {
      conflictOpen.value = true
      return
    }
    formError.value = errText(err)
  }
}

function openSimulate(row: RuleRow) {
  simRuleId.value = row.id
  simBase.value = '10000'
  simError.value = ''
  simResult.value = null
  simOpen.value = true
}

function openDraftSimulate() {
  simRuleId.value = null
  simError.value = ''
  simResult.value = null
  simOpen.value = true
}

async function runSimulate() {
  simError.value = ''
  simResult.value = null
  try {
    const payload: Record<string, unknown> = { simulateBase: Number(simBase.value) }
    if (simRuleId.value) payload.ruleId = simRuleId.value
    else {
      const draft = buildPayload(false)
      if (!draft) {
        simError.value = formError.value || '1001 适用范围编号非法'
        return
      }
      payload.draftRule = draft
    }
    const res = await http.post('/fin/share/simulate', payload)
    simResult.value = res.data?.data || null
  } catch (err) {
    simError.value = errText(err)
  }
}

function askDisable(row: RuleRow) {
  disableRow.value = row
  disableOpen.value = true
}

async function confirmDisable() {
  if (!disableRow.value) return
  error.value = ''
  try {
    await http.delete(`/fin/share/rule/${disableRow.value.id}`)
    disableOpen.value = false
    await loadList()
  } catch (err) {
    error.value = errText(err)
  }
}

onMounted(loadList)
</script>
