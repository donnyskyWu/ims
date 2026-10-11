<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>技能库</h1>
        <div class="sub">AI 技能登记、审核、授权 · /ims/air/skill</div>
      </div>
      <div class="acts">
        <button class="btn btn-pri btn-sm" type="button" data-testid="air-skill-create" @click="openCreate">新增技能</button>
      </div>
    </div>

    <p v-if="toast" class="hint" data-testid="air-skill-toast">{{ toast }}</p>

    <div v-if="summary" class="g4" style="margin-bottom: 12px" data-testid="air-skill-stats">
      <div class="card stat">
        <span class="l">技能 / 专家 / 知识库</span>
        <div class="n" style="font-size: 21px">{{ summary.skillCount }} / {{ summary.expertCount }} / {{ summary.kbCount }}</div>
      </div>
      <div class="card stat"><span class="l">启用中 Key</span><div class="n" style="color: var(--green)">{{ summary.activeKeyCount }}</div></div>
      <div class="card stat"><span class="l">累计调用</span><div class="n">{{ summary.invokeTotal }}</div></div>
      <div class="card stat"><span class="l">知识文档</span><div class="n">{{ summary.docCount }}</div></div>
    </div>

    <form class="qbar" @submit.prevent="loadList">
      <input v-model="filters.skillName" placeholder="技能名称" style="width: 140px" />
      <select v-model="filters.category" style="width: 140px" data-testid="air-skill-category-filter">
        <option value="">全部分类</option>
        <option v-for="item in skillCategories" :key="item" :value="item">{{ item }}</option>
      </select>
      <select v-model="filters.status" style="width: 120px">
        <option value="">全部状态</option>
        <option value="DRAFT">草稿</option>
        <option value="PENDING">审核中</option>
        <option value="PUBLISHED">已发布</option>
        <option value="DISABLED">已停用</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">查询</button>
    </form>

    <div class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>编号</th>
              <th>名称</th>
              <th>分类</th>
              <th>版本</th>
              <th>状态</th>
              <th>审核</th>
              <th>责任人</th>
              <th>授权</th>
              <th>累计调用</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading"><td colspan="10"><div class="empty"><div class="et">加载中</div></div></td></tr>
            <tr v-else-if="!rows.length"><td colspan="10"><div class="empty"><div class="et">暂无技能</div></div></td></tr>
            <tr v-for="row in rows" v-else :key="row.id">
              <td class="mono"><button class="skill-no" type="button" data-testid="air-skill-no" @click="openDetail(row)">{{ row.skillNo }}</button></td>
              <td style="font-weight: 500">{{ row.skillName }}</td>
              <td>{{ row.category }}</td>
              <td>{{ row.versionLabel }}</td>
              <td data-testid="air-skill-status" :data-status="row.status">{{ statusLabel(row.status) }}</td>
              <td>{{ auditLabel(row.auditStatus) }}</td>
              <td>{{ row.ownerName }}</td>
              <td class="num" data-testid="air-skill-grant-count">{{ row.grantCount }}</td>
              <td class="num" data-testid="air-skill-invoke">{{ row.invokeCount }}</td>
              <td>
                <div style="display: flex; gap: 4px; flex-wrap: wrap">
                  <button v-if="row.status === 'DRAFT'" class="btn btn-sec btn-sm" type="button" data-testid="air-skill-submit" @click="submitAudit(row.id)">提交审核</button>
                  <button v-if="canAudit(row)" class="btn btn-pri btn-sm" type="button" data-testid="air-skill-audit" @click="openAudit(row)">审核</button>
                  <button v-if="row.status === 'PUBLISHED'" class="btn btn-sec btn-sm" type="button" data-testid="air-skill-grant" @click="openGrant(row)">授权</button>
                  <button v-if="row.status === 'PUBLISHED'" class="btn btn-sec btn-sm" type="button" data-testid="air-skill-disable" @click="askDisable(row)">停用</button>
                  <button v-if="row.status === 'DISABLED'" class="btn btn-sec btn-sm" type="button" data-testid="air-skill-enable" @click="setStatus(row.id, 'ENABLED')">启用</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="showForm" class="modal-mask" @click.self="showForm = false">
      <div class="card" style="width: 480px; padding: 20px; max-height: 86vh; overflow: auto" data-testid="air-skill-form">
        <h3 style="margin: 0 0 12px">新增技能</h3>
        <label class="fld">技能名称 <i class="req">*</i></label>
        <input v-model="form.skillName" class="fld-in" data-testid="air-skill-name" />
        <p v-if="formErrors.skillName" class="hint" style="color: var(--red)">{{ formErrors.skillName }}</p>
        <label class="fld">技能分类 <i class="req">*</i></label>
        <select v-model="form.category" class="fld-in" data-testid="air-skill-category">
          <option value="">请选择</option>
          <option v-for="item in skillCategories" :key="item" :value="item">{{ item }}</option>
        </select>
        <p v-if="formErrors.category" class="hint" style="color: var(--red)">{{ formErrors.category }}</p>
        <label class="fld">初始版本</label>
        <input v-model="form.versionLabel" class="fld-in" data-testid="air-skill-version" placeholder="v1.0" />
        <label class="fld">维护责任人 <i class="req">*</i></label>
        <select v-model="form.ownerUserId" class="fld-in" data-testid="air-skill-owner">
          <option value="">请选择</option>
          <option v-for="item in owners" :key="item.id" :value="item.id">{{ item.label }}</option>
        </select>
        <p v-if="formErrors.ownerUserId" class="hint" style="color: var(--red)">{{ formErrors.ownerUserId }}</p>
        <label class="fld">能力说明 <i class="req">*</i></label>
        <textarea v-model="form.capability" class="fld-in" rows="3" data-testid="air-skill-capability" placeholder="输入输出契约、适用场景、边界约束" />
        <p v-if="formErrors.capability" class="hint" style="color: var(--red)">{{ formErrors.capability }}</p>
        <label class="fld">提示词模板 <i class="req">*</i></label>
        <textarea v-model="form.promptTemplate" class="fld-in" rows="4" data-testid="air-skill-prompt" placeholder="Prompt 模板（支持 {变量} 占位符）" />
        <p v-if="formErrors.promptTemplate" class="hint" style="color: var(--red)">{{ formErrors.promptTemplate }}</p>
        <p v-if="formError" class="hint" style="color: var(--red)">{{ formError }}</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="showForm = false">取消</button>
          <button class="btn btn-pri btn-sm" type="button" data-testid="air-skill-save" @click="submitCreate">提交审核</button>
        </div>
      </div>
    </div>

    <div v-if="detail" class="modal-mask" @click.self="detail = null">
      <div class="card" style="width: 620px; padding: 20px" data-testid="air-skill-detail">
        <h3 style="margin: 0 0 12px">技能详情 · {{ detail.skillNo }}</h3>
        <div class="kv">
          <div><div class="k">技能 ID</div><div class="v mono">{{ detail.skillNo }}</div></div>
          <div><div class="k">状态</div><div class="v">{{ statusLabel(detail.status) }}</div></div>
          <div><div class="k">安全审核</div><div class="v">{{ auditLabel(detail.auditStatus) }}</div></div>
          <div><div class="k">版本</div><div class="v">{{ detail.versionLabel }}</div></div>
          <div><div class="k">授权范围</div><div class="v">{{ grantScope(detail) }}</div></div>
          <div><div class="k">调用方式</div><div class="v mono">MCP skills.get</div></div>
        </div>
        <p v-if="detail.capability" style="font-size: 13px; line-height: 1.6">{{ detail.capability }}</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="detail = null">关闭</button>
          <button v-if="detail.status === 'PUBLISHED'" class="btn btn-pri btn-sm" type="button" @click="openGrantFromDetail">授权</button>
        </div>
      </div>
    </div>

    <div v-if="auditSkill" class="modal-mask" @click.self="auditSkill = null">
      <div class="card" style="width: 560px; padding: 20px" data-testid="air-skill-audit-form">
        <h3 style="margin: 0 0 12px">技能审核 · {{ auditSkill.skillName }}</h3>
        <p class="hint">责任人 {{ auditSkill.ownerName || '—' }} · 当前状态 {{ statusLabel(auditSkill.status) }}</p>
        <p v-if="auditSkill.capability" style="font-size: 13px; line-height: 1.6">{{ auditSkill.capability }}</p>
        <label class="fld">意见（驳回时必填）</label>
        <textarea v-model="auditNote" class="fld-in" rows="4" placeholder="说明通过与驳回原因" data-testid="air-skill-audit-note" />
        <p v-if="auditError" class="hint" style="color: var(--red)" data-testid="air-skill-audit-error">{{ auditError }}</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="auditSkill = null">取消</button>
          <button class="btn btn-sec btn-sm" type="button" data-testid="air-skill-reject" @click="submitAuditDecision(false)">驳回</button>
          <button class="btn btn-pri btn-sm" type="button" data-testid="air-skill-approve" @click="submitAuditDecision(true)">审核通过</button>
        </div>
      </div>
    </div>

    <div v-if="disableTarget" class="modal-mask" data-testid="air-skill-disable-confirm">
      <div class="card" style="width: 420px; padding: 20px">
        <h3 style="margin: 0 0 12px">停用技能</h3>
        <p class="hint">停用后连接器 skills.list / skills.get 即时不可见，授权记录保留。</p>
        <p style="margin: 8px 0 0">{{ disableTarget.skillName }}</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="disableTarget = null">取消</button>
          <button class="btn btn-pri btn-sm" type="button" data-testid="air-skill-disable-ok" @click="confirmDisable">确认停用</button>
        </div>
      </div>
    </div>

    <div v-if="grantSkill" class="modal-mask" @click.self="grantSkill = null">
      <div class="card" style="width: 520px; padding: 20px" data-testid="air-skill-grant-form">
        <h3 style="margin: 0 0 8px">技能授权</h3>
        <p class="hint">{{ grantSkill.skillName }} · 授权事件驱动同步，生效延迟 &lt;5 分钟（BR-024）</p>
        <label class="fld">授权类型</label>
        <select v-model="grantForm.grantType" class="fld-in" data-testid="air-grant-type" @change="onGrantType">
          <option value="DEPT">部门</option>
          <option value="ROLE">角色</option>
          <option value="PERSON">人员</option>
        </select>
        <label class="fld" style="display: flex; gap: 8px; align-items: center">
          <input v-model="grantForm.allStaff" type="checkbox" data-testid="air-grant-all-staff" />
          全员可见
        </label>
        <template v-if="!grantForm.allStaff && grantForm.grantType === 'PERSON'">
          <label class="fld">人员</label>
          <div style="display: flex; gap: 8px">
            <input v-model="userKeyword" class="fld-in" placeholder="用户名" data-testid="air-grant-user-search" />
            <button class="btn btn-sec btn-sm" type="button" data-testid="air-grant-user-find" @click="searchUsers">查找</button>
          </div>
        </template>
        <template v-if="!grantForm.allStaff && grantForm.grantType === 'DEPT'">
          <label class="fld">部门</label>
          <div style="display: flex; gap: 8px">
            <input v-model="deptKeyword" class="fld-in" placeholder="组织人员姓名" data-testid="air-grant-dept-search" />
            <button class="btn btn-sec btn-sm" type="button" data-testid="air-grant-dept-find" @click="searchDepts">查找</button>
          </div>
        </template>
        <label v-if="!grantForm.allStaff" class="fld">授权对象</label>
        <select v-if="!grantForm.allStaff" v-model="grantForm.grantId" class="fld-in" data-testid="air-grant-target">
          <option value="">请选择</option>
          <option v-for="opt in targetOptions" :key="opt.id" :value="opt.id">{{ opt.label }}</option>
        </select>
        <p v-if="grantError" class="hint" style="color: var(--red)" data-testid="air-grant-error">{{ grantError }}</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" data-testid="air-grant-close" @click="grantSkill = null">关闭</button>
          <button class="btn btn-pri btn-sm" type="button" data-testid="air-grant-save" @click="submitGrant">保存授权</button>
        </div>
        <div class="tbl-wrap" style="margin-top: 12px">
          <table>
            <thead>
              <tr><th>类型</th><th>对象</th><th>状态</th><th></th></tr>
            </thead>
            <tbody>
              <tr v-if="!grants.length"><td colspan="4">暂无授权</td></tr>
              <tr v-for="item in grants" :key="item.grantId" data-testid="air-grant-row">
                <td>{{ grantTypeLabel(item) }}</td>
                <td>{{ item.grantName }}</td>
                <td>{{ item.status === 'ACTIVE' ? '生效' : '已收回' }}</td>
                <td>
                  <button
                    v-if="item.status === 'ACTIVE'"
                    class="btn btn-sec btn-sm"
                    type="button"
                    data-testid="air-grant-revoke"
                    @click="revokeGrant(item.grantId)"
                  >收回</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { errorMessage, http } from '../../api/http'
import { useUserStore } from '../../stores/user'

type Row = {
  id: number
  skillNo: string
  skillName: string
  category: string
  versionLabel: string
  status: string
  auditStatus: string
  ownerUserId: number
  ownerName: string
  grantCount: number
  invokeCount: number
  capability?: string
  promptTemplate?: string
}

type GrantRow = {
  grantId: number
  grantType: string
  grantName: string
  allStaff: boolean
  status: string
}

type Option = { id: string; label: string }

const skillCategories = ['内容生产', '数据分析', '运营支持', '财务', '人事行政']
const userStore = useUserStore()
const summary = ref<{
  skillCount: number
  expertCount: number
  kbCount: number
  publishedCount: number
  pendingAuditCount: number
  invokeTotal: number
  docCount: number
  activeKeyCount: number
} | null>(null)
const rows = ref<Row[]>([])
const loading = ref(false)
const toast = ref('')
const showForm = ref(false)
const detail = ref<(Row & { grants?: GrantRow[] }) | null>(null)
const formError = ref('')
const formErrors = reactive({ skillName: '', category: '', ownerUserId: '', capability: '', promptTemplate: '' })
const filters = reactive({ skillName: '', category: '', status: '' })
const form = reactive({ skillName: '', category: '', versionLabel: 'v1.0', ownerUserId: '', capability: '', promptTemplate: '' })
const owners = ref<Option[]>([])
const disableTarget = ref<Row | null>(null)
const auditSkill = ref<Row | null>(null)
const auditNote = ref('')
const auditError = ref('')
const grantSkill = ref<Row | null>(null)
const grants = ref<GrantRow[]>([])
const grantError = ref('')
const grantForm = reactive({ grantType: 'DEPT', grantId: '', allStaff: false })
const targetOptions = ref<Option[]>([])
const userKeyword = ref('')
const deptKeyword = ref('')

function say(message: string) {
  toast.value = message
}

function grantScope(row: Row & { grants?: GrantRow[] }) {
  const names = (row.grants || []).filter((item) => item.status === 'ACTIVE').map((item) => item.grantName || grantTypeLabel(item))
  return names.length ? names.join('、') : '暂无授权'
}

function statusLabel(status: string) {
  return ({ DRAFT: '草稿', PENDING: '审核中', PUBLISHED: '已发布', DISABLED: '已停用' } as Record<string, string>)[status] || status
}

function auditLabel(status: string) {
  return ({ NONE: '未提交', PENDING: '待审核', APPROVED: '已通过', REJECTED: '已驳回' } as Record<string, string>)[status] || status
}

function canAudit(row: Row) {
  if (row.auditStatus !== 'PENDING') return false
  const mine = userStore.profile?.userId
  if (mine && String(row.ownerUserId) === String(mine)) return false
  return true
}

function grantTypeLabel(item: GrantRow) {
  if (item.allStaff) return '全员'
  return ({ DEPT: '部门', ROLE: '角色', PERSON: '人员' } as Record<string, string>)[item.grantType] || item.grantType
}

async function loadSummary() {
  const res = await http.get('/air/skill/summary')
  if (res.data.code === 0) summary.value = res.data.data
}

async function loadList() {
  loading.value = true
  try {
    const res = await http.get('/air/skill/list', {
      params: {
        pageNo: 1,
        pageSize: 20,
        skillName: filters.skillName || undefined,
        category: filters.category || undefined,
        status: filters.status || undefined,
      },
    })
    if (res.data.code === 0) rows.value = res.data.data.list || []
  } finally {
    loading.value = false
  }
}

async function loadOwners() {
  const res = await http.get('/system/user/page', { params: { pageNo: 1, pageSize: 50 } })
  const list = res.data.data?.list || []
  owners.value = list.map((item: { id: string | number; username: string; nickname?: string }) => ({
    id: String(item.id),
    label: item.nickname ? `${item.nickname}（${item.username}）` : item.username,
  }))
}

async function openCreate() {
  formError.value = ''
  formErrors.skillName = ''
  formErrors.category = ''
  formErrors.ownerUserId = ''
  formErrors.capability = ''
  formErrors.promptTemplate = ''
  form.skillName = ''
  form.category = ''
  form.versionLabel = 'v1.0'
  form.capability = ''
  form.promptTemplate = ''
  if (!owners.value.length) await loadOwners().catch(() => undefined)
  const mine = userStore.profile?.userId ? String(userStore.profile.userId) : ''
  if (mine && !owners.value.some((item) => item.id === mine)) {
    const label = userStore.profile?.nickname || userStore.profile?.username || '当前用户'
    owners.value.unshift({ id: mine, label })
  }
  form.ownerUserId = mine
  showForm.value = true
}

async function submitCreate() {
  formError.value = ''
  formErrors.skillName = form.skillName.trim() ? '' : '必填项，请填写'
  formErrors.category = form.category ? '' : '必填项，请填写'
  formErrors.ownerUserId = form.ownerUserId ? '' : '必填项，请填写'
  formErrors.capability = form.capability.trim() ? '' : '必填项，请填写'
  formErrors.promptTemplate = form.promptTemplate.trim() ? '' : '必填项，请填写'
  if (formErrors.skillName || formErrors.category || formErrors.ownerUserId || formErrors.capability || formErrors.promptTemplate) {
    return
  }
  try {
    const created = await http.post('/air/skill', {
      skillName: form.skillName.trim(),
      category: form.category,
      versionLabel: form.versionLabel.trim() || 'v1.0',
      ownerUserId: Number(form.ownerUserId),
      capability: form.capability.trim(),
      promptTemplate: form.promptTemplate.trim(),
    })
    const id = created.data.data?.id
    if (id) await http.put(`/air/skill/${id}/submit-audit`)
    showForm.value = false
    say('技能已提交，进入强制审核')
    await loadSummary()
    await loadList()
  } catch (error) {
    formError.value = errorMessage(error)
  }
}

async function submitAudit(id: number) {
  await http.put(`/air/skill/${id}/submit-audit`)
  say('已提交审核')
  await loadList()
  await loadSummary()
}

async function openDetail(row: Row) {
  try {
    const res = await http.get(`/air/skill/${row.id}`)
    detail.value = res.data.code === 0 ? res.data.data : row
  } catch (error) {
    say(errorMessage(error))
  }
}

function openGrantFromDetail() {
  if (!detail.value) return
  const row = detail.value
  detail.value = null
  openGrant(row)
}

function openAudit(row: Row) {
  auditSkill.value = row
  auditNote.value = ''
  auditError.value = ''
}

async function submitAuditDecision(approve: boolean) {
  if (!auditSkill.value) return
  auditError.value = ''
  if (!approve && !auditNote.value.trim()) {
    auditError.value = '必填项，请填写'
    return
  }
  try {
    await http.put(`/air/skill/${auditSkill.value.id}/audit`, {
      approve,
      auditNote: auditNote.value.trim(),
    })
    auditSkill.value = null
    say(approve ? '审核通过，技能已发布' : '已驳回，技能退回草稿')
    await loadList()
    await loadSummary()
  } catch (error) {
    auditError.value = errorMessage(error)
  }
}

function askDisable(row: Row) {
  disableTarget.value = row
}

async function confirmDisable() {
  if (!disableTarget.value) return
  const id = disableTarget.value.id
  disableTarget.value = null
  await setStatus(id, 'DISABLED')
}

async function setStatus(id: number, status: 'ENABLED' | 'DISABLED') {
  await http.put(`/air/skill/${id}/status`, { status })
  say(status === 'DISABLED' ? '已停用' : '已启用')
  await loadList()
  await loadSummary()
}

async function loadGrants(id: number) {
  const res = await http.get(`/air/skill/${id}`)
  grants.value = res.data.data.grants || []
}

async function openGrant(row: Row) {
  grantError.value = ''
  grantSkill.value = row
  grantForm.grantType = 'DEPT'
  grantForm.grantId = ''
  grantForm.allStaff = false
  userKeyword.value = ''
  deptKeyword.value = ''
  targetOptions.value = []
  await loadGrants(row.id)
  await loadRolesOrDepts()
}

async function onGrantType() {
  grantForm.grantId = ''
  targetOptions.value = []
  grantError.value = ''
  if (grantForm.grantType === 'ROLE') await loadRolesOrDepts()
}

async function loadRolesOrDepts() {
  if (grantForm.grantType === 'ROLE') {
    const res = await http.get('/system/role/list')
    const list = Array.isArray(res.data.data) ? res.data.data : []
    targetOptions.value = list
      .filter((item: { status?: string }) => item.status !== 'DISABLED')
      .map((item: { id: number; roleName: string }) => ({ id: String(item.id), label: item.roleName }))
    return
  }
  if (grantForm.grantType === 'DEPT') await searchDepts()
}

async function searchUsers() {
  grantError.value = ''
  const res = await http.get('/system/user/page', {
    params: { pageNo: 1, pageSize: 20, username: userKeyword.value.trim() || undefined },
  })
  const list = res.data.data.list || []
  targetOptions.value = list.map((item: { id: string | number; username: string; nickname?: string }) => ({
    id: String(item.id),
    label: item.nickname ? `${item.nickname}（${item.username}）` : item.username,
  }))
  grantForm.grantId = targetOptions.value.length === 1 ? targetOptions.value[0].id : ''
  if (!targetOptions.value.length) grantError.value = '没有匹配的人员'
}

async function searchDepts() {
  grantError.value = ''
  const res = await http.get('/auth/org/users', {
    params: { pageNo: 1, pageSize: 100, keyword: deptKeyword.value.trim() || undefined },
  })
  const list = res.data.data.list || []
  const map = new Map<string, string>()
  for (const user of list) {
    const ids = (user.deptIds || []) as Array<number | string>
    const names = (user.deptNames || []) as string[]
    ids.forEach((raw, index) => {
      const id = String(raw)
      const name = names[index] || `部门#${id}`
      if (!map.has(id)) map.set(id, name.includes(id) ? name : `${name}（${id}）`)
    })
  }
  targetOptions.value = [...map.entries()].map(([id, label]) => ({ id, label }))
  grantForm.grantId = targetOptions.value.length === 1 ? targetOptions.value[0].id : ''
}

async function submitGrant() {
  if (!grantSkill.value) return
  grantError.value = ''
  if (!grantForm.allStaff && !grantForm.grantId) {
    grantError.value = '请选择授权对象'
    return
  }
  try {
    await http.post('/air/skill/grant', {
      skillId: grantSkill.value.id,
      grantType: grantForm.grantType,
      grantId: grantForm.allStaff ? 0 : Number(grantForm.grantId),
      allStaff: grantForm.allStaff,
    })
    grantForm.grantId = ''
    grantForm.allStaff = false
    say('授权成功')
    await loadGrants(grantSkill.value.id)
    await loadList()
    await loadSummary()
  } catch (error) {
    grantError.value = errorMessage(error)
  }
}

async function revokeGrant(grantId: number) {
  if (!grantSkill.value) return
  await http.delete(`/air/skill/grant/${grantId}`)
  say('已收回授权')
  await loadGrants(grantSkill.value.id)
  await loadList()
}

onMounted(async () => {
  await loadSummary()
  await loadList()
})
</script>

<style>
.skill-no {
  background: none;
  border: none;
  color: var(--blue);
  cursor: pointer;
  font: inherit;
  padding: 0;
}
.kv {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 16px;
  margin-bottom: 12px;
}
.kv .k {
  font-size: 12px;
  color: var(--text2);
}
.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
</style>
