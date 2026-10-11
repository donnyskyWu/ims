<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>分成规则</h1>
        <div class="sub">同一范围、同一基数合计超过 100% 不能保存；不足部分归公司。同范围冲突须确认。</div>
      </div>
      <button class="btn btn-pri btn-sm" type="button" data-testid="fin-share-rule-create" @click="openCreate">
        创建规则
      </button>
    </div>

    <form class="qbar" @submit.prevent="search">
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
      <button class="btn btn-pri btn-sm" type="button" data-testid="fin-share-rule-query" @click="search">查询</button>
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
              <td colspan="10">
                <div class="empty" data-testid="fin-share-rule-empty">
                  <div class="et">{{ emptyText }}</div>
                  <button
                    v-if="error"
                    class="btn btn-sec btn-sm"
                    type="button"
                    data-testid="fin-share-rule-retry"
                    @click="loadList"
                  >
                    重试
                  </button>
                </div>
              </td>
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
                <button
                  v-else
                  class="btn btn-sec btn-sm"
                  type="button"
                  data-testid="fin-share-rule-enable"
                  @click="enableRule(row)"
                >
                  启用
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    <p class="hint" data-testid="fin-share-rule-pager" style="margin: 8px 0">
      第 {{ pageNo }} 页 · 共 {{ total }} 条
      <button class="btn btn-sec btn-sm" type="button" data-testid="fin-share-rule-prev" :disabled="pageNo <= 1" @click="goPage(pageNo - 1)">
        上一页
      </button>
      <button
        class="btn btn-sec btn-sm"
        type="button"
        data-testid="fin-share-rule-next"
        :disabled="pageNo * pageSize >= total"
        @click="goPage(pageNo + 1)"
      >
        下一页
      </button>
      <input v-model="pageInput" data-testid="fin-share-rule-page" inputmode="numeric" style="width: 72px" />
      <button class="btn btn-sec btn-sm" type="button" data-testid="fin-share-rule-page-go" @click="goPage(Number(pageInput))">跳转</button>
    </p>

    <div v-if="drawerOpen" class="mask on" @click.self="drawerOpen = false"></div>
    <div v-if="drawerOpen" class="drawer on" data-testid="fin-share-rule-drawer" style="width: 760px">
      <div class="drawer-h">
        <b>{{ editingId ? '编辑分成规则' : '创建分成规则' }}</b>
        <button type="button" class="btn btn-sec btn-sm" @click="drawerOpen = false">关闭</button>
      </div>
      <div class="drawer-b">
        <p class="hint">规则变更不影响已生成分成单，重算需人工触发</p>
        <label class="fld">
          <span>规则名称<i class="req">*</i></span>
          <input v-model="form.ruleName" data-testid="fin-share-rule-name" maxlength="64" :class="{ err: fieldErrors.name }" />
          <div v-if="fieldErrors.name" class="ferr">{{ fieldErrors.name }}</div>
        </label>
        <label class="fld">
          <span>分成对象<i class="req">*</i></span>
          <select v-model="form.shareTarget" data-testid="fin-share-rule-target" :class="{ err: fieldErrors.target }">
            <option value="">请选择</option>
            <option value="DAREN">达人</option>
            <option value="REALNAME">实名人</option>
            <option value="TEAM">团队</option>
          </select>
          <div v-if="fieldErrors.target" class="ferr">{{ fieldErrors.target }}</div>
        </label>
        <label class="fld">
          <span>分成基数<i class="req">*</i></span>
          <select v-model="form.baseType" data-testid="fin-share-rule-base" :class="{ err: fieldErrors.base }">
            <option value="">请选择</option>
            <option value="GMV">GMV</option>
            <option value="GROSS_PROFIT">毛利</option>
            <option value="NET_PROFIT">净利润</option>
          </select>
          <div v-if="fieldErrors.base" class="ferr">{{ fieldErrors.base }}</div>
        </label>
        <label class="fld">
          <span>比例方式<i class="req">*</i></span>
          <select v-model="form.rateType" data-testid="fin-share-rule-rate-type" :class="{ err: fieldErrors.rateType }">
            <option value="">请选择</option>
            <option value="FIXED">固定比例</option>
            <option value="LADDER">阶梯</option>
          </select>
          <div v-if="fieldErrors.rateType" class="ferr">{{ fieldErrors.rateType }}</div>
        </label>
        <label v-if="form.rateType === 'FIXED'" class="fld">
          <span>比例或阶梯<i class="req">*</i></span>
          <input v-model="form.fixedPercent" data-testid="fin-share-rule-fixed-rate" inputmode="decimal" :class="{ err: fieldErrors.rate }" />
          <div v-if="fieldErrors.rate" class="ferr">{{ fieldErrors.rate }}</div>
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
          <p v-if="ladderOverlap" class="hint" data-testid="fin-share-rule-ladder-error" style="color: var(--red)">阶梯区间重叠</p>
          <div v-if="fieldErrors.rate" class="ferr">{{ fieldErrors.rate }}</div>
        </div>
        <div class="fld" data-testid="fin-share-rule-platforms">
          <span>平台</span>
          <div class="pills">
            <label v-for="opt in platformOptions" :key="opt.value" class="pill" :class="{ on: form.platforms.includes(opt.value) }">
              <input type="checkbox" :value="opt.value" :checked="form.platforms.includes(opt.value)" @change="togglePlatform(opt.value)" />
              <span>{{ opt.label }}</span>
            </label>
          </div>
        </div>
        <div class="fld" data-testid="fin-share-rule-accounts">
          <span>账号</span>
          <input
            v-model="accountKeyword"
            placeholder="按名称搜索"
            data-testid="fin-share-rule-account-search"
            @change="loadAccounts"
            @keydown.enter.prevent="loadAccounts"
          />
          <div class="pills" style="margin-top: 8px">
            <label v-for="opt in accountOptions" :key="opt.id" class="pill" :class="{ on: form.accountIds.includes(opt.id) }">
              <input
                type="checkbox"
                :data-testid="'fin-share-rule-account-' + opt.id"
                :checked="form.accountIds.includes(opt.id)"
                @change="toggleAccount(opt.id)"
              />
              <span>{{ opt.label }}</span>
            </label>
            <span v-if="!accountOptions.length" class="hint">暂无账号</span>
          </div>
        </div>
        <div class="fld" data-testid="fin-share-rule-groups">
          <span>IP 组</span>
          <input
            v-model="groupKeyword"
            placeholder="按名称搜索"
            data-testid="fin-share-rule-group-search"
            @change="loadGroups"
            @keydown.enter.prevent="loadGroups"
          />
          <div class="pills" style="margin-top: 8px">
            <label v-for="opt in groupOptions" :key="opt.id" class="pill" :class="{ on: form.ipGroups.includes(opt.id) }">
              <input
                type="checkbox"
                :data-testid="'fin-share-rule-group-' + opt.id"
                :checked="form.ipGroups.includes(opt.id)"
                @change="toggleGroup(opt.id)"
              />
              <span>{{ opt.label }}</span>
            </label>
            <span v-if="!groupOptions.length" class="hint">暂无 IP 组</span>
          </div>
        </div>
        <p class="hint" data-testid="fin-share-rule-draft-sum">{{ draftSumText }}</p>
        <label class="fld">
          <span>优先级<i class="req">*</i></span>
          <input v-model="form.priority" data-testid="fin-share-rule-priority" :class="{ err: fieldErrors.priority }" />
          <div v-if="fieldErrors.priority" class="ferr">{{ fieldErrors.priority }}</div>
        </label>
        <label class="fld">
          <span>生效期起<i class="req">*</i></span>
          <input v-model="form.effectiveFrom" data-testid="fin-share-rule-from" type="date" :class="{ err: fieldErrors.from }" />
          <div v-if="fieldErrors.from" class="ferr">{{ fieldErrors.from }}</div>
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

    <div v-if="enableConflictOpen" class="mask on" style="z-index: 140" data-testid="fin-share-rule-enable-conflict">
      <div class="card" style="position: fixed; z-index: 150; left: 50%; top: 28%; transform: translateX(-50%); width: 400px; padding: 16px">
        <b>优先级冲突</b>
        <p>存在同范围同对象优先级冲突规则，确认强制保存？</p>
        <div class="acts" style="gap: 8px">
          <button class="btn btn-pri btn-sm" type="button" data-testid="fin-share-rule-enable-confirm" @click="confirmEnable">
            确认强制启用
          </button>
          <button class="btn btn-sec btn-sm" type="button" @click="enableConflictOpen = false">取消</button>
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
const pageNo = ref(1)
const pageSize = 20
const total = ref(0)
const pageInput = ref('1')
const drawerOpen = ref(false)
const editingId = ref<number | null>(null)
const clientToken = ref('')
const conflictOpen = ref(false)
const enableConflictOpen = ref(false)
const enableRow = ref<RuleRow | null>(null)
const disableOpen = ref(false)
const disableRow = ref<RuleRow | null>(null)
const simOpen = ref(false)
const simRuleId = ref<number | null>(null)
const simBase = ref('10000')
const simError = ref('')
const simResult = ref<SimResult | null>(null)
const platformOptions = [
  { value: 'DYS', label: '抖音直播' },
  { value: 'KS', label: '快手' },
  { value: 'WX', label: '视频号' },
  { value: 'TM', label: '淘宝' },
  { value: 'JD', label: '京东' },
  { value: 'OTA', label: '其他' },
]
/** 分成平台码 → 账号档案 platformType。淘宝/京东无对应档案平台。 */
const CORP_BY_SHARE: Record<string, string[]> = {
  DYS: ['DOUYIN'],
  KS: ['KUAISHOU'],
  WX: ['WECHAT_CHANNELS'],
  OTA: ['XIAOHONGSHU', 'WECHAT_OFFICIAL'],
}
const ALL_CORP_PLATFORMS = ['DOUYIN', 'KUAISHOU', 'WECHAT_CHANNELS', 'WECHAT_OFFICIAL', 'XIAOHONGSHU']
const accountOptions = ref<{ id: number; label: string }[]>([])
const groupOptions = ref<{ id: number; label: string }[]>([])
const accountNames = ref<Record<number, string>>({})
const groupNames = ref<Record<number, string>>({})
const accountKeyword = ref('')
const groupKeyword = ref('')
const fieldErrors = reactive({
  name: '',
  target: '',
  base: '',
  rateType: '',
  rate: '',
  priority: '',
  from: '',
})
const form = reactive({
  ruleName: '',
  shareTarget: '',
  baseType: '',
  rateType: '',
  fixedPercent: '',
  platforms: [] as string[],
  accountIds: [] as number[],
  ipGroups: [] as number[],
  priority: '',
  effectiveFrom: '',
  effectiveTo: '',
  ladders: [
    { min: '0', max: '10000', rate: '10' },
    { min: '10000', max: '', rate: '20' },
  ],
})

const emptyText = computed(() => {
  if (error.value) return '规则列表加载失败'
  if (query.shareTarget || query.status) return '无匹配规则'
  if (total.value === 0) return '暂无分成规则'
  return '本页无规则'
})

function scopeLabel(scope: Scope | undefined) {
  const platforms = (scope?.platforms || []).map((code) => platformOptions.find((item) => item.value === code)?.label || code)
  const accounts = (scope?.accountIds || []).map((id) => accountNames.value[id] || `账号#${id}`)
  const groups = (scope?.ipGroupIds || []).map((id) => groupNames.value[id] || `IP组#${id}`)
  const parts = [...platforms, ...accounts, ...groups]
  return parts.length ? parts.join(' / ') : '全范围'
}

function sumParts(rowsIn: RuleRow[], extra?: { scope: Scope; baseType: string; shareTarget: string; priority: number; rate: number }) {
  const groups = new Map<string, Map<string, { priority: number; rate: number }>>()
  const consider = (scope: Scope | undefined, baseType: string, target: string, priority: number, rate: number) => {
    const key = `${scopeKey(scope)}|${baseType}`
    if (!groups.has(key)) groups.set(key, new Map())
    const bucket = groups.get(key)!
    const prev = bucket.get(target)
    if (!prev || priority >= prev.priority) bucket.set(target, { priority, rate })
  }
  for (const row of rowsIn) {
    if (row.status !== 'ENABLED' || row.rateType !== 'FIXED' || row.fixedRate == null) continue
    consider(row.scope, row.baseType, row.shareTarget, row.priority, Number(row.fixedRate))
  }
  if (extra && Number.isFinite(extra.rate)) {
    consider(extra.scope, extra.baseType, extra.shareTarget, extra.priority, extra.rate)
  }
  const parts: string[] = []
  for (const [key, bucket] of groups) {
    const basis = [...bucket.values()].reduce((acc, row) => acc + Math.round(row.rate * 10000), 0)
    const [rawScope, baseType] = key.split('|')
    const parsed = JSON.parse(rawScope) as Scope
    const percent = (basis / 100).toFixed(2)
    const remain = basis < 10000 ? '，剩余归公司' : ''
    parts.push(`${scopeLabel(parsed)} · ${baseLabel(baseType)} ${percent}%${remain}`)
  }
  return parts
}

const sumText = computed(() => {
  const parts = sumParts(rows.value)
  return parts.length ? parts.join('；') : '暂无'
})

const draftSumText = computed(() => {
  if (form.rateType !== 'FIXED' || form.fixedPercent === '' || !form.baseType || !form.shareTarget) {
    return '同一基数合计不足 100% 时，剩余归公司'
  }
  const rate = Number(form.fixedPercent) / 100
  if (!Number.isFinite(rate)) return '同一基数合计不足 100% 时，剩余归公司'
  const parts = sumParts(rows.value.filter((row) => editingId.value == null || row.id !== editingId.value), {
    scope: { platforms: form.platforms, accountIds: form.accountIds, ipGroupIds: form.ipGroups },
    baseType: form.baseType,
    shareTarget: form.shareTarget,
    priority: Number(form.priority || 0),
    rate,
  })
  const current = parts.find((item) => item.includes(baseLabel(form.baseType)))
  return current || '同一基数合计不足 100% 时，剩余归公司'
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
  return scopeLabel(scope)
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

function clearFieldErrors() {
  fieldErrors.name = ''
  fieldErrors.target = ''
  fieldErrors.base = ''
  fieldErrors.rateType = ''
  fieldErrors.rate = ''
  fieldErrors.priority = ''
  fieldErrors.from = ''
}

function resetForm() {
  form.ruleName = ''
  form.shareTarget = ''
  form.baseType = ''
  form.rateType = ''
  form.fixedPercent = ''
  form.platforms = []
  form.accountIds = []
  form.ipGroups = []
  form.priority = ''
  form.effectiveFrom = ''
  form.effectiveTo = ''
  form.ladders = [
    { min: '0', max: '10000', rate: '10' },
    { min: '10000', max: '', rate: '20' },
  ]
  clearFieldErrors()
}

function togglePlatform(value: string) {
  form.platforms = form.platforms.includes(value)
    ? form.platforms.filter((item) => item !== value)
    : [...form.platforms, value]
  void loadAccounts()
}

function toggleAccount(id: number) {
  form.accountIds = form.accountIds.includes(id) ? form.accountIds.filter((item) => item !== id) : [...form.accountIds, id]
}

function toggleGroup(id: number) {
  form.ipGroups = form.ipGroups.includes(id) ? form.ipGroups.filter((item) => item !== id) : [...form.ipGroups, id]
  void loadAccounts()
}

function rateOutOfRange(raw: string) {
  if (raw.trim() === '') return false
  const value = Number(raw)
  return !Number.isFinite(value) || value <= 0 || value > 100
}

function validateForm() {
  clearFieldErrors()
  if (!form.ruleName.trim()) fieldErrors.name = '必填项，请填写'
  if (!form.shareTarget) fieldErrors.target = '必填项，请填写'
  if (!form.baseType) fieldErrors.base = '必填项，请填写'
  if (!form.rateType) fieldErrors.rateType = '必填项，请填写'
  if (form.rateType === 'FIXED') {
    if (form.fixedPercent.trim() === '') fieldErrors.rate = '必填项，请填写'
    else if (rateOutOfRange(form.fixedPercent)) fieldErrors.rate = '分成比例须在 0~100% 之间'
  } else if (form.rateType === 'LADDER') {
    if (!form.ladders.length || form.ladders.some((row) => row.rate.trim() === '' || row.min.trim() === '')) {
      fieldErrors.rate = '必填项，请填写'
    } else if (form.ladders.some((row) => rateOutOfRange(row.rate))) {
      fieldErrors.rate = '分成比例须在 0~100% 之间'
    }
  }
  if (form.priority.trim() === '') fieldErrors.priority = '必填项，请填写'
  if (!form.effectiveFrom) fieldErrors.from = '必填项，请填写'
  const messages = Object.values(fieldErrors).filter(Boolean)
  formError.value = messages.length ? messages.join('；') : ''
  return messages.length === 0
}

function buildPayload(confirmConflict: boolean) {
  if (!validateForm()) return null
  const payload: Record<string, unknown> = {
    ruleName: form.ruleName.trim(),
    shareTarget: form.shareTarget,
    baseType: form.baseType,
    rateType: form.rateType,
    scope: {
      platforms: [...form.platforms],
      accountIds: [...form.accountIds],
      ipGroupIds: [...form.ipGroups],
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

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const res = await http.get('/fin/share/rules', {
      params: {
        pageNo: pageNo.value,
        pageSize,
        shareTarget: query.shareTarget || undefined,
        status: query.status || undefined,
      },
    })
    rows.value = res.data?.data?.list || []
    total.value = Number(res.data?.data?.total || 0)
  } catch (err) {
    error.value = errText(err)
    rows.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function search() {
  pageNo.value = 1
  pageInput.value = '1'
  return loadList()
}

function resetQuery() {
  query.shareTarget = ''
  query.status = ''
  return search()
}

function goPage(raw: number) {
  const next = Number.isFinite(raw) && raw > 0 ? Math.floor(raw) : 1
  pageNo.value = next
  pageInput.value = String(next)
  return loadList()
}

function corpPlatformsForScope() {
  if (!form.platforms.length) return ALL_CORP_PLATFORMS
  const picked = new Set<string>()
  for (const code of form.platforms) {
    for (const corp of CORP_BY_SHARE[code] || []) picked.add(corp)
  }
  return [...picked]
}

async function loadAccounts() {
  const platforms = corpPlatformsForScope()
  if (!platforms.length) {
    accountOptions.value = []
    return
  }
  const groups: Array<number | undefined> = form.ipGroups.length ? [...form.ipGroups] : [undefined]
  try {
    const lists = await Promise.all(
      platforms.flatMap((platformType) =>
        groups.map((ipGroupId) =>
          http.get('/corp/account/page', {
            params: {
              pageNo: 1,
              pageSize: 100,
              platformType,
              keyword: accountKeyword.value || undefined,
              ipGroupId,
            },
          }),
        ),
      ),
    )
    const seen = new Set<number>()
    const options: { id: number; label: string }[] = []
    for (const res of lists) {
      for (const row of (res.data?.data?.list || []) as Array<{ id: number; accountNo?: string; accountName?: string; nickname?: string }>) {
        const id = Number(row.id)
        if (seen.has(id)) continue
        seen.add(id)
        options.push({
          id,
          label: `${row.accountNo || row.id} ${row.nickname || row.accountName || ''}`.trim(),
        })
      }
    }
    accountOptions.value = options
    const names = { ...accountNames.value }
    for (const item of options) names[item.id] = item.label
    accountNames.value = names
  } catch {
    accountOptions.value = []
  }
}

async function loadGroups() {
  try {
    const res = await http.get('/ip-group/list', {
      params: { pageNo: 1, pageSize: 200, keyword: groupKeyword.value || undefined },
    })
    groupOptions.value = (res.data?.data?.list || []).map((row: { id: number; groupName?: string }) => ({
      id: Number(row.id),
      label: row.groupName || `IP组#${row.id}`,
    }))
    const names = { ...groupNames.value }
    for (const item of groupOptions.value) names[item.id] = item.label
    groupNames.value = names
  } catch {
    groupOptions.value = []
  }
}

function openCreate() {
  editingId.value = null
  clientToken.value = `${Date.now()}-${Math.random().toString(16).slice(2)}`
  formError.value = ''
  conflictOpen.value = false
  resetForm()
  drawerOpen.value = true
  void loadAccounts()
  void loadGroups()
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
  form.platforms = [...(row.scope?.platforms || [])]
  form.accountIds = [...(row.scope?.accountIds || [])].map(Number)
  form.ipGroups = [...(row.scope?.ipGroupIds || [])].map(Number)
  clearFieldErrors()
  void loadAccounts()
  void loadGroups()
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
    pageNo.value = 1
    pageInput.value = '1'
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

async function enableRule(row: RuleRow) {
  error.value = ''
  enableRow.value = row
  try {
    await http.put(`/fin/share/rule/${row.id}/enable`, {})
    enableConflictOpen.value = false
    enableRow.value = null
    await loadList()
  } catch (err) {
    const body = err as ApiErr
    if (body?.code === 1147) {
      enableConflictOpen.value = true
      return
    }
    error.value = errText(err)
  }
}

async function confirmEnable() {
  if (!enableRow.value) return
  error.value = ''
  try {
    await http.put(`/fin/share/rule/${enableRow.value.id}/enable`, { confirmConflict: true })
    enableConflictOpen.value = false
    enableRow.value = null
    await loadList()
  } catch (err) {
    enableConflictOpen.value = false
    error.value = errText(err)
  }
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

<style scoped>
.fld > span {
  display: block;
  font-size: 12px;
  color: var(--text2);
  margin-bottom: 5px;
  font-weight: 500;
}
</style>
