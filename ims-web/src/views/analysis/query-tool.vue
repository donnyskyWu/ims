<template>
  <div class="page page-query-tool">
    <div class="pg-h">
      <div>
        <h1>查询工具</h1>
        <div class="sub">分级下钻与逐级穿透 · 模板列表</div>
      </div>
      <div class="acts">
        <router-link class="btn btn-sec btn-sm" to="/ims/collect/metadata">元数据维护</router-link>
        <router-link class="btn btn-sec btn-sm" to="/ims/dc/trace">穿透查询 L3</router-link>
      </div>
    </div>

    <div class="card bi0-mine-card">
      <div class="bi0-mine-hd">
        <div class="hd-row" style="justify-content: space-between; align-items: center; gap: 12px">
          <div>
            <h3 style="font-size: 17px; font-weight: 600; margin: 0">查询模板</h3>
            <span class="csub">共 {{ total }} 条 · 下钻 · 穿透</span>
          </div>
          <button class="btn btn-pri btn-sm" type="button" @click="openCreate">+ 新增查询模板</button>
        </div>
      </div>
      <div class="bi0-mine-body">
        <form class="qbar" @submit.prevent="loadList">
          <input v-model="filters.keyword" placeholder="名称" style="width: 180px" />
          <select v-model="filters.status" class="qt-qctl" style="width: 120px">
            <option value="">全部状态</option>
            <option value="DRAFT">草稿</option>
            <option value="PUBLISHED">已发布</option>
          </select>
          <select v-model="filters.mode" style="width: 110px">
            <option value="">全部模式</option>
            <option value="DRILL">DRILL</option>
            <option value="TRACE">TRACE</option>
          </select>
          <span class="sp"></span>
          <button class="btn btn-pri btn-sm" type="submit">查询</button>
          <button class="btn btn-sec btn-sm" type="button" @click="resetFilters">重置</button>
        </form>

        <div class="tbl-block">
          <div class="tbl-wrap">
            <table>
              <thead>
                <tr>
                  <th>查询名称</th>
                  <th>类型</th>
                  <th>状态</th>
                  <th>更新时间</th>
                  <th>菜单路径</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="loading">
                  <td colspan="6"><div class="empty"><div class="et">加载中</div></div></td>
                </tr>
                <tr v-else-if="!rows.length">
                  <td colspan="6"><div class="empty"><div class="et">暂无模板</div></div></td>
                </tr>
                <tr v-for="row in rows" v-else :key="row.templateCode">
                  <td style="font-weight: 500">{{ row.name }}</td>
                  <td><span class="tag" :style="modeStyle(row.mode)"><span class="dot"></span>{{ row.mode }}</span></td>
                  <td><span class="tag" :style="statusStyle(row.status)"><span class="dot"></span>{{ statusLabel(row.status) }}</span></td>
                  <td class="num">{{ formatTime(row.updatedAt) }}</td>
                  <td>{{ row.menuPathLabel || '—' }}</td>
                  <td class="qt-ops">
                    <span class="btn-txt btn" @click="runRow(row)">执行</span>
                    <span class="btn-txt btn" @click="openEdit(row)">编辑</span>
                    <span v-if="row.status === 'DRAFT'" class="btn-txt btn" @click="publishRow(row)">发布</span>
                    <span v-else class="btn-txt btn" @click="unpublishRow(row)">取消发布</span>
                    <span v-if="row.status === 'PUBLISHED' && !row.menuSeed" class="btn-txt btn" @click="seedMenu(row)">发布到侧栏</span>
                    <span v-if="row.menuSeed" class="btn-txt btn" @click="revokeMenu(row)">撤销侧栏</span>
                    <span class="btn-txt btn btn-danger-txt" @click="deleteRow(row)">删除</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="pager">
            <span class="pg-total">共 {{ total }} 条</span>
            <select class="pg-size" :value="pageSize" @change="changePageSize">
              <option :value="10">10</option>
              <option :value="20">20</option>
            </select>
            <span>条/页</span>
            <span class="pg-sp"></span>
            <span class="pg-n" :class="{ dis: pageNo <= 1 }" @click="gotoPage(pageNo - 1)">‹</span>
            <span class="pg-n on">{{ pageNo }}</span>
            <span class="pg-n" :class="{ dis: pageNo >= pageCount }" @click="gotoPage(pageNo + 1)">›</span>
          </div>
        </div>
      </div>
    </div>

    <ProtoDrawer :open="wizardOpen" title="查询模板" width="720px" @close="closeWizard">
      <div class="qt-steps" data-testid="qt-wizard-steps">
        <span v-for="(label, i) in stepLabels" :key="label" :class="{ on: step === i }">{{ i + 1 }}. {{ label }}</span>
      </div>
      <p v-if="wizardError" class="hint bad" data-testid="qt-wizard-error">{{ wizardError }}</p>

      <div v-if="step === 0" class="qt-type-grid">
        <button type="button" class="qt-type-card" :class="{ on: form.mode === 'DRILL' }" @click="form.mode = 'DRILL'">
          <b>分级下钻</b>
          <span>DRILL · 最多 5 层</span>
        </button>
        <button type="button" class="qt-type-card" :class="{ on: form.mode === 'TRACE' }" @click="form.mode = 'TRACE'">
          <b>逐级穿透</b>
          <span>TRACE · 最多 6 步</span>
        </button>
      </div>
      <p v-if="step === 0" class="hint">
        平铺查询不在此向导提供，请使用
        <router-link to="/ims/bi/query">自定义查询</router-link>
      </p>

      <div v-else-if="step === 1" class="qt-step">
        <label class="fld">
          <span>模板名称 <em class="req">*</em></span>
          <input v-model="form.name" data-testid="qt-wizard-name" placeholder="请填写模板名称" />
        </label>
        <label class="fld">
          <span>说明</span>
          <input v-model="form.desc" placeholder="可选" />
        </label>
      </div>

      <div v-else-if="step === 2" class="qt-step">
        <template v-if="form.mode === 'DRILL'">
          <div class="hd-row">
            <b>下钻层级</b>
            <button class="btn btn-sec btn-sm" type="button" @click="addLevel">添加层级</button>
          </div>
          <div v-for="(level, idx) in form.levels" :key="idx" class="qt-level">
            <input v-model="level.label" placeholder="层级名称" />
            <select v-model="level.entityCode" @change="onEntityPick(level.entityCode)">
              <option value="">选择已映射实体</option>
              <option v-for="e in entities" :key="e.entityCode" :value="e.entityCode">
                {{ e.entityName }}（{{ e.entityCode }}）
              </option>
            </select>
            <button class="btn btn-sec btn-sm" type="button" @click="removeLevel(idx)">删除</button>
          </div>
        </template>
        <template v-else>
          <div class="hd-row">
            <b>穿透步骤</b>
            <button class="btn btn-sec btn-sm" type="button" @click="addStep">添加步骤</button>
          </div>
          <div v-for="(item, idx) in form.pathSteps" :key="idx" class="qt-level">
            <select v-model="item.entity">
              <option v-for="opt in traceEntities" :key="opt" :value="opt">{{ opt }}</option>
            </select>
            <button class="btn btn-sec btn-sm" type="button" @click="removeStep(idx)">删除</button>
          </div>
        </template>
        <p v-if="unmappedHint" class="hint bad">
          实体未映射（1261）· 请前往
          <router-link to="/ims/collect/metadata">数据采集 → 元数据维护</router-link>
        </p>
      </div>

      <div v-else-if="step === 3" class="qt-step">
        <label class="fld">
          <span>根来源</span>
          <select v-model="form.rootEntity">
            <option value="">请选择</option>
            <option v-for="opt in rootOptions" :key="opt" :value="opt">{{ opt }}</option>
          </select>
        </label>
        <label class="fld">
          <span>关联</span>
          <select v-model="form.joinTable">
            <option value="">不关联</option>
            <option v-for="j in joinOptions" :key="j.table" :value="j.table">{{ j.label }}</option>
          </select>
        </label>
      </div>

      <div v-else-if="step === 4" class="qt-step">
        <p class="hint">预览使用当前向导配置试跑，不会另存一条临时模板。</p>
        <button class="btn btn-pri btn-sm" type="button" :disabled="previewing" @click="previewRun">试跑</button>
        <div v-if="preview" class="tbl-wrap" style="margin-top: 12px">
          <p class="csub">queryCostMs={{ preview.queryCostMs }} · {{ preview.queryMode }}</p>
          <table>
            <thead>
              <tr><th v-for="c in preview.columns || []" :key="c.key || c">{{ c.label || c }}</th></tr>
            </thead>
            <tbody>
              <tr v-for="(r, idx) in preview.rows || []" :key="idx">
                <td v-for="c in preview.columns" :key="c.key || c">{{ r[c.key || c] }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div v-else class="qt-step">
        <p>确认保存「{{ form.name }}」· {{ form.mode === 'DRILL' ? '分级下钻' : '逐级穿透' }}。</p>
        <p class="hint">草稿可稍后发布。保存并发布后可在列表执行。</p>
      </div>

      <template #footer>
        <button class="btn btn-sec btn-sm" type="button" @click="closeWizard">取消</button>
        <button v-if="step > 0" class="btn btn-sec btn-sm" type="button" @click="prev">上一步</button>
        <button v-if="step >= 2 && step < 5" class="btn btn-sec btn-sm" type="button" @click="saveDraft">存草稿</button>
        <button v-if="step < 5" class="btn btn-pri btn-sm" type="button" @click="next">下一步</button>
        <template v-else>
          <button class="btn btn-sec btn-sm" type="button" @click="saveDraft">存草稿</button>
          <button class="btn btn-pri btn-sm" type="button" @click="savePublished">保存并发布</button>
        </template>
      </template>
    </ProtoDrawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import ProtoDrawer from '../../components/ProtoDrawer.vue'
import { errorMessage, http } from '../../api/http'

type Row = {
  templateCode: string
  name: string
  mode: string
  status: string
  updatedAt: string
  menuPathLabel?: string
  menuSeed?: boolean
}
type EntityOpt = { entityCode: string; entityName: string; joins?: { table: string; label: string }[] }
type Level = { levelIndex: number; label: string; entityCode: string }
type PathStep = { entity: string }

const stepLabels = ['选类型', '基本信息', '配置载荷', '展示与来源', '预览试跑', '完成']
const traceEntities = ['PERSON', 'ACCOUNT', 'SESSION', 'COST']

const router = useRouter()
const rows = ref<Row[]>([])
const total = ref(0)
const loading = ref(false)
const pageNo = ref(1)
const pageSize = ref(10)
const filters = reactive({ keyword: '', status: '', mode: '' })
const wizardOpen = ref(false)
const step = ref(0)
const editingCode = ref('')
const wizardError = ref('')
const unmappedHint = ref(false)
const entities = ref<EntityOpt[]>([])
const preview = ref<Record<string, any> | null>(null)
const previewing = ref(false)

const form = reactive({
  mode: 'DRILL',
  name: '',
  desc: '',
  levels: [{ levelIndex: 0, label: '', entityCode: '' }] as Level[],
  pathSteps: [{ entity: 'PERSON' }, { entity: 'ACCOUNT' }] as PathStep[],
  rootEntity: '',
  joinTable: '',
})

const pageCount = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))
const rootOptions = computed(() => {
  if (form.mode === 'TRACE') return form.pathSteps.map((s) => s.entity).filter(Boolean)
  return form.levels.map((l) => l.entityCode).filter(Boolean)
})
const joinOptions = computed(() => {
  const code = form.rootEntity || form.levels[0]?.entityCode
  return entities.value.find((e) => e.entityCode === code)?.joins || []
})

function statusLabel(s: string) {
  return s === 'PUBLISHED' ? '已发布' : '草稿'
}
function statusStyle(s: string) {
  return s === 'PUBLISHED'
    ? { background: 'rgba(52,199,89,.12)', color: '#1e8e3e' }
    : { background: 'rgba(142,142,147,.12)', color: '#6d6d72' }
}
function modeStyle(m: string) {
  return m === 'TRACE'
    ? { background: 'rgba(0,113,227,.12)', color: '#0071e3' }
    : { background: 'rgba(175,82,218,.12)', color: '#8944ab' }
}
function formatTime(iso: string) {
  return iso ? iso.replace('T', ' ').slice(0, 16) : '—'
}

function payloadJson() {
  return {
    levels: form.levels.map((level, idx) => ({ ...level, levelIndex: idx })),
    pathSteps: form.pathSteps.map((item) => ({ entity: item.entity })),
    rootEntity: form.rootEntity,
    joinTable: form.joinTable,
  }
}

async function loadEntities() {
  try {
    const res = await http.get('/bi/query/sources')
    entities.value = res.data.data?.list || []
  } catch (error: unknown) {
    if ((error as { code?: number })?.code === 1261) unmappedHint.value = true
  }
}

async function loadList() {
  loading.value = true
  try {
    const res = await http.get('/analysis/query-tool/template/page', {
      params: {
        keyword: filters.keyword || undefined,
        status: filters.status || undefined,
        mode: filters.mode || undefined,
        pageNo: pageNo.value,
        pageSize: pageSize.value,
      },
    })
    rows.value = res.data.data.list || []
    total.value = res.data.data.total || 0
  } catch (error: unknown) {
    rows.value = []
    wizardError.value = errorMessage(error)
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  filters.keyword = ''
  filters.status = ''
  filters.mode = ''
  pageNo.value = 1
  loadList()
}

function gotoPage(page: number) {
  if (page < 1 || page > pageCount.value || page === pageNo.value) return
  pageNo.value = page
  loadList()
}

function changePageSize(ev: Event) {
  pageSize.value = Number((ev.target as HTMLSelectElement).value) || 10
  pageNo.value = 1
  loadList()
}

function resetForm() {
  form.mode = 'DRILL'
  form.name = ''
  form.desc = ''
  form.levels = [{ levelIndex: 0, label: '', entityCode: '' }]
  form.pathSteps = [{ entity: 'PERSON' }, { entity: 'ACCOUNT' }]
  form.rootEntity = ''
  form.joinTable = ''
  wizardError.value = ''
  unmappedHint.value = false
  preview.value = null
}

function openCreate() {
  editingCode.value = ''
  step.value = 0
  resetForm()
  wizardOpen.value = true
  loadEntities()
}

async function openEdit(row: Row) {
  resetForm()
  editingCode.value = row.templateCode
  step.value = 1
  wizardOpen.value = true
  await loadEntities()
  try {
    const res = await http.get(`/analysis/query-tool/template/${row.templateCode}`)
    const data = res.data.data
    form.mode = data.mode === 'TRACE' ? 'TRACE' : 'DRILL'
    form.name = data.name || ''
    form.desc = data.desc || ''
    const payload = data.payloadJson || {}
    if (Array.isArray(payload.levels) && payload.levels.length) form.levels = payload.levels
    if (Array.isArray(payload.pathSteps) && payload.pathSteps.length) form.pathSteps = payload.pathSteps
    form.rootEntity = payload.rootEntity || ''
    form.joinTable = payload.joinTable || ''
  } catch (error: unknown) {
    wizardError.value = errorMessage(error)
  }
}

function closeWizard() {
  wizardOpen.value = false
}

function addLevel() {
  if (form.levels.length >= 5) {
    wizardError.value = '分级下钻最多 5 层'
    return
  }
  wizardError.value = ''
  form.levels.push({ levelIndex: form.levels.length, label: '', entityCode: '' })
}

function removeLevel(index: number) {
  if (form.levels.length <= 1) {
    wizardError.value = '至少保留一个层级'
    return
  }
  form.levels.splice(index, 1)
}

function addStep() {
  if (form.pathSteps.length >= 6) {
    wizardError.value = '逐级穿透最多 6 步'
    return
  }
  wizardError.value = ''
  form.pathSteps.push({ entity: 'SESSION' })
}

function removeStep(index: number) {
  if (form.pathSteps.length <= 2) {
    wizardError.value = '逐级穿透至少 2 步'
    return
  }
  form.pathSteps.splice(index, 1)
}

async function onEntityPick(code: string) {
  unmappedHint.value = false
  if (!code) return
  try {
    await http.get(`/collect/metadata/entity/${code}/fields`)
  } catch (error: unknown) {
    if ((error as { code?: number })?.code === 1261) unmappedHint.value = true
  }
}

function next() {
  wizardError.value = ''
  if (step.value === 1 && !form.name.trim()) {
    wizardError.value = '请填写模板名称'
    return
  }
  if (step.value === 2 && form.mode === 'DRILL') {
    if (!form.levels.length || form.levels.some((level) => !level.entityCode)) {
      wizardError.value = '请为每一层选择已映射实体'
      return
    }
    if (form.levels.length > 5) {
      wizardError.value = '分级下钻最多 5 层'
      return
    }
  }
  if (step.value === 2 && form.mode === 'TRACE') {
    if (form.pathSteps.length < 2) {
      wizardError.value = '逐级穿透至少 2 步'
      return
    }
    if (form.pathSteps.length > 6) {
      wizardError.value = '逐级穿透最多 6 步'
      return
    }
  }
  if (step.value === 3 && form.mode === 'TRACE' && !form.rootEntity) {
    wizardError.value = '请选择根来源'
    return
  }
  if (step.value < 5) step.value += 1
}

function prev() {
  wizardError.value = ''
  if (step.value > 0) step.value -= 1
}

async function persist(publish: boolean) {
  if (!form.name.trim()) {
    wizardError.value = '请填写模板名称'
    step.value = 1
    return
  }
  const body = { name: form.name.trim(), mode: form.mode, desc: form.desc.trim(), payloadJson: payloadJson() }
  try {
    if (editingCode.value) {
      await http.put(`/analysis/query-tool/template/${editingCode.value}`, {
        name: body.name,
        desc: body.desc,
        payloadJson: body.payloadJson,
      })
      if (publish) await http.post(`/analysis/query-tool/template/${editingCode.value}/publish`)
    } else {
      const created = await http.post('/analysis/query-tool/template', body)
      const code = created.data.data.templateCode as string
      editingCode.value = code
      if (publish) await http.post(`/analysis/query-tool/template/${code}/publish`)
    }
    wizardOpen.value = false
    await loadList()
  } catch (error: unknown) {
    wizardError.value = errorMessage(error)
  }
}

function saveDraft() {
  persist(false)
}

function savePublished() {
  persist(true)
}

async function previewRun() {
  previewing.value = true
  wizardError.value = ''
  try {
    const res = await http.post('/analysis/query-tool/run', {
      mode: form.mode,
      runtime: {},
      inlineTemplate: { mode: form.mode, name: form.name, payloadJson: payloadJson() },
    })
    preview.value = res.data.data
  } catch (error: unknown) {
    wizardError.value = errorMessage(error)
  } finally {
    previewing.value = false
  }
}

async function publishRow(row: Row) {
  try {
    await http.post(`/analysis/query-tool/template/${row.templateCode}/publish`)
    await loadList()
  } catch (error: unknown) {
    alert(errorMessage(error))
  }
}

async function unpublishRow(row: Row) {
  try {
    await http.post(`/analysis/query-tool/template/${row.templateCode}/unpublish`)
    await loadList()
  } catch (error: unknown) {
    alert(errorMessage(error))
  }
}

async function deleteRow(row: Row) {
  if (!confirm(`删除模板「${row.name}」？`)) return
  try {
    await http.delete(`/analysis/query-tool/template/${row.templateCode}`)
    await loadList()
  } catch (error: unknown) {
    alert(errorMessage(error))
  }
}

async function seedMenu(row: Row) {
  const title = window.prompt('菜单标题（不超过 16 字）', row.name.slice(0, 16))
  if (title == null) return
  if (!title.trim()) {
    alert('请填写菜单标题')
    return
  }
  try {
    await http.post('/analysis/query-tool/menu-seed', {
      templateCode: row.templateCode,
      menuTitle: title.trim().slice(0, 16),
      parentMenuCode: 'ims:analysis:query-tool-group',
    })
    await loadList()
  } catch (error: unknown) {
    alert(errorMessage(error))
  }
}

async function revokeMenu(row: Row) {
  try {
    await http.delete(`/analysis/query-tool/menu-seed/${row.templateCode}`)
    await loadList()
  } catch (error: unknown) {
    alert(errorMessage(error))
  }
}

function runRow(row: Row) {
  if (row.status !== 'PUBLISHED') {
    alert('请先发布后再执行')
    return
  }
  router.push(`/ims/analysis/query-tool/run/${row.templateCode}`)
}

onMounted(loadList)
</script>

<style scoped>
.qt-ops {
  white-space: nowrap;
}
.qt-steps {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}
.qt-steps span {
  font-size: 12px;
  color: var(--text2);
}
.qt-steps span.on {
  color: var(--blue, #0071e3);
  font-weight: 600;
}
.qt-type-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.qt-type-card {
  text-align: left;
  border: 1px solid var(--line, #e5e5ea);
  border-radius: 12px;
  padding: 16px;
  background: #fff;
  cursor: pointer;
}
.qt-type-card.on {
  border-color: #0071e3;
  box-shadow: inset 0 0 0 1px #0071e3;
}
.qt-type-card b,
.qt-type-card span {
  display: block;
}
.qt-type-card span {
  margin-top: 6px;
  color: var(--text2);
  font-size: 12px;
}
.qt-level {
  display: grid;
  grid-template-columns: 1fr 1fr auto;
  gap: 8px;
  margin: 8px 0;
}
.hint.bad {
  color: var(--red, #ff3b30);
}
.fld > span {
  display: block;
  margin-bottom: 4px;
}
</style>
