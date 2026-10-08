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

    <div v-if="summary" class="g4" style="margin-bottom: 12px">
      <div class="card stat"><span class="l">技能总数</span><div class="n">{{ summary.skillCount }}</div></div>
      <div class="card stat"><span class="l">已发布</span><div class="n" style="color: var(--green)">{{ summary.publishedCount }}</div></div>
      <div class="card stat"><span class="l">待审核</span><div class="n">{{ summary.pendingAuditCount }}</div></div>
      <div class="card stat"><span class="l">累计调用</span><div class="n">{{ summary.invokeTotal }}</div></div>
    </div>

    <form class="qbar" @submit.prevent="loadList">
      <input v-model="filters.skillName" placeholder="技能名称" style="width: 140px" />
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
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading"><td colspan="9"><div class="empty"><div class="et">加载中</div></div></td></tr>
            <tr v-else-if="!rows.length"><td colspan="9"><div class="empty"><div class="et">暂无技能</div></div></td></tr>
            <tr v-for="row in rows" v-else :key="row.id">
              <td class="mono">{{ row.skillNo }}</td>
              <td style="font-weight: 500">{{ row.skillName }}</td>
              <td>{{ row.category }}</td>
              <td>{{ row.versionLabel }}</td>
              <td data-testid="air-skill-status" :data-status="row.status">{{ statusLabel(row.status) }}</td>
              <td>{{ auditLabel(row.auditStatus) }}</td>
              <td>{{ row.ownerName }}</td>
              <td class="num" data-testid="air-skill-grant-count">{{ row.grantCount }}</td>
              <td>
                <div style="display: flex; gap: 4px; flex-wrap: wrap">
                  <button v-if="row.status === 'DRAFT'" class="btn btn-sec btn-sm" type="button" data-testid="air-skill-submit" @click="submitAudit(row.id)">提交审核</button>
                  <button v-if="row.auditStatus === 'PENDING'" class="btn btn-pri btn-sm" type="button" data-testid="air-skill-approve" @click="audit(row.id, true)">通过</button>
                  <button v-if="row.auditStatus === 'PENDING'" class="btn btn-sec btn-sm" type="button" data-testid="air-skill-reject" @click="audit(row.id, false)">驳回</button>
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
      <div class="card" style="width: 400px; padding: 20px" data-testid="air-skill-form">
        <h3 style="margin: 0 0 12px">新增技能</h3>
        <label class="fld">技能名称</label>
        <input v-model="form.skillName" class="fld-in" data-testid="air-skill-name" />
        <label class="fld">分类</label>
        <input v-model="form.category" class="fld-in" />
        <p v-if="formError" class="hint" style="color: var(--red)">{{ formError }}</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="showForm = false">取消</button>
          <button class="btn btn-pri btn-sm" type="button" data-testid="air-skill-save" @click="submitCreate">保存</button>
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

type Row = {
  id: number
  skillNo: string
  skillName: string
  category: string
  versionLabel: string
  status: string
  auditStatus: string
  ownerName: string
  grantCount: number
}

type GrantRow = {
  grantId: number
  grantType: string
  grantName: string
  allStaff: boolean
  status: string
}

type Option = { id: string; label: string }

const summary = ref<{ skillCount: number; publishedCount: number; pendingAuditCount: number; invokeTotal: number } | null>(null)
const rows = ref<Row[]>([])
const loading = ref(false)
const showForm = ref(false)
const formError = ref('')
const filters = reactive({ skillName: '', status: '' })
const form = reactive({ skillName: '', category: '内容生产' })
const disableTarget = ref<Row | null>(null)
const grantSkill = ref<Row | null>(null)
const grants = ref<GrantRow[]>([])
const grantError = ref('')
const grantForm = reactive({ grantType: 'DEPT', grantId: '', allStaff: false })
const targetOptions = ref<Option[]>([])
const userKeyword = ref('')
const deptKeyword = ref('')

function statusLabel(status: string) {
  return ({ DRAFT: '草稿', PENDING: '审核中', PUBLISHED: '已发布', DISABLED: '已停用' } as Record<string, string>)[status] || status
}

function auditLabel(status: string) {
  return ({ NONE: '未提交', PENDING: '待审核', APPROVED: '已通过', REJECTED: '已驳回' } as Record<string, string>)[status] || status
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
      params: { pageNo: 1, pageSize: 20, skillName: filters.skillName || undefined, status: filters.status || undefined },
    })
    if (res.data.code === 0) rows.value = res.data.data.list || []
  } finally {
    loading.value = false
  }
}

function openCreate() {
  formError.value = ''
  form.skillName = ''
  form.category = '内容生产'
  showForm.value = true
}

async function submitCreate() {
  formError.value = ''
  try {
    await http.post('/air/skill', form)
    showForm.value = false
    await loadSummary()
    await loadList()
  } catch (error) {
    formError.value = errorMessage(error)
  }
}

async function submitAudit(id: number) {
  await http.put(`/air/skill/${id}/submit-audit`)
  await loadList()
  await loadSummary()
}

async function audit(id: number, approve: boolean) {
  await http.put(`/air/skill/${id}/audit`, { approve })
  await loadList()
  await loadSummary()
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
  await loadGrants(grantSkill.value.id)
  await loadList()
}

onMounted(async () => {
  await loadSummary()
  await loadList()
})
</script>
