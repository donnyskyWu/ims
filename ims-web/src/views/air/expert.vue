<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>专家库</h1>
        <div class="sub">专家包组装（Prompt+技能）与授权 · /ims/air/expert</div>
      </div>
      <div class="acts">
        <button class="btn btn-pri btn-sm" type="button" data-testid="air-expert-create" @click="openCreate">新增专家</button>
      </div>
    </div>

    <div v-if="summary" class="g4" style="margin-bottom: 12px">
      <div class="card stat">
        <span class="l">专家 / 技能 / 知识库</span>
        <div class="n" style="font-size: 21px">{{ summary.expertCount }} / {{ summary.skillCount }} / {{ summary.kbCount }}</div>
      </div>
      <div class="card stat">
        <span class="l">已发布专家</span>
        <div class="n" style="color: var(--green)">{{ summary.publishedCount }}</div>
      </div>
    </div>

    <form class="qbar" @submit.prevent="loadPage">
      <input v-model="filters.expertName" placeholder="专家名称" style="width: 140px" data-testid="air-expert-filter" />
      <select v-model="filters.status" style="width: 100px">
        <option value="">全部状态</option>
        <option value="DRAFT">草稿</option>
        <option value="PUBLISHED">已发布</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit" data-testid="air-expert-search">查询</button>
    </form>

    <div v-if="loading" class="empty"><div class="et">加载中</div></div>
    <div v-else-if="!rows.length" class="empty"><div class="et">暂无专家包</div></div>
    <div v-else style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px">
      <div
        v-for="row in rows"
        :key="row.id"
        class="card hov"
        data-testid="air-expert-card"
        :data-name="row.expertName"
        :data-status="row.status"
      >
        <div class="rowline" style="margin-bottom: 12px">
          <span class="av" style="width: 46px; height: 46px; border-radius: 12px; font-size: 20px; background: var(--blue)">
            {{ row.expertName.slice(0, 1) }}
          </span>
          <div style="min-width: 0; flex: 1">
            <b style="font-size: 15px; display: block">{{ row.expertName }}</b>
            <span class="mono" style="font-size: 11px; color: var(--text2)">{{ row.expertCode }} · {{ row.ver }}</span>
          </div>
          <span class="tag" :style="row.status === 'PUBLISHED' ? publishedTag : draftTag" data-testid="air-expert-status">
            {{ row.status === 'PUBLISHED' ? '已发布' : '草稿' }}
          </span>
        </div>
        <div style="font-size: 12px; color: var(--text2); margin-bottom: 12px; min-height: 36px">{{ row.scene || '—' }}</div>
        <div class="kv" style="grid-template-columns: 1fr 1fr 1fr; gap: 8px; margin-bottom: 12px">
          <div><div class="k">挂载技能</div><div class="v">{{ row.skillIds.length }}</div></div>
          <div><div class="k">挂载知识库</div><div class="v">{{ row.kbIds.length }}</div></div>
          <div><div class="k">累计组装</div><div class="v">{{ row.assembleCount }}</div></div>
        </div>
        <div style="display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 12px">
          <span v-for="chip in row.skillChips" :key="chip.id" class="chip">{{ chip.name }}</span>
          <span v-if="!row.skillChips.length" class="hint">未挂载技能</span>
        </div>
        <div class="rowline" style="justify-content: space-between">
          <span style="font-size: 11.5px; color: var(--text2)">
            授权 <b data-testid="air-expert-grant-count">{{ row.grantCount }}</b> · {{ row.ownerName }}
          </span>
          <span class="rowline" style="gap: 6px">
            <button class="btn btn-sec btn-sm" type="button" data-testid="air-expert-preview-open" @click="openPreview(row.id)">
              组装预览
            </button>
            <button
              v-if="row.status === 'DRAFT'"
              class="btn btn-sec btn-sm"
              type="button"
              data-testid="air-expert-publish"
              @click="publish(row.id)"
            >
              发布
            </button>
            <button
              v-if="row.status === 'PUBLISHED'"
              class="btn btn-pri btn-sm"
              type="button"
              data-testid="air-expert-grant"
              @click="openGrant(row)"
            >
              授权
            </button>
          </span>
        </div>
      </div>
    </div>

    <div v-if="showForm" class="modal-mask" @click.self="showForm = false">
      <div class="card" style="width: 520px; padding: 20px; max-height: 90vh; overflow: auto" data-testid="air-expert-form">
        <h3 style="margin: 0 0 12px">新增专家</h3>
        <label class="fld">名称</label>
        <input v-model="form.expertName" class="fld-in" data-testid="air-expert-name" />
        <label class="fld">适用场景</label>
        <input v-model="form.scene" class="fld-in" data-testid="air-expert-scene" />
        <label class="fld">System Prompt</label>
        <textarea v-model="form.systemPrompt" class="fld-in" rows="4" data-testid="air-expert-prompt" />
        <label class="fld">挂载技能（已发布）</label>
        <select v-model="form.skillIds" multiple class="fld-in" style="min-height: 72px" data-testid="air-expert-skill">
          <option v-for="s in skillOptions" :key="s.id" :value="String(s.id)">{{ s.skillName }} ({{ s.skillNo }})</option>
        </select>
        <p v-if="formError" class="hint" style="color: var(--red)" data-testid="air-expert-error">{{ formError }}</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="showForm = false">取消</button>
          <button class="btn btn-pri btn-sm" type="button" data-testid="air-expert-save" @click="submitCreate">保存</button>
        </div>
      </div>
    </div>

    <div v-if="preview" class="modal-mask" @click.self="preview = null">
      <div class="card" style="width: 560px; padding: 20px" data-testid="air-expert-preview">
        <h3 style="margin: 0 0 12px">组装预览</h3>
        <pre
          class="mono"
          data-testid="air-expert-preview-prompt"
          style="white-space: pre-wrap; font-size: 12px; background: var(--bg2); padding: 12px; border-radius: 8px"
          >{{ preview.systemPrompt }}</pre
        >
        <div style="margin-top: 12px">
          <div v-for="ref in preview.skillRefs" :key="ref.code" class="chip" data-testid="air-expert-skill-ref">
            {{ ref.code }} · {{ ref.name }} · {{ ref.ver }}
          </div>
          <p v-if="!preview.skillRefs.length" class="hint">未挂载已发布技能</p>
        </div>
        <p class="hint" style="margin-top: 12px" data-testid="air-expert-guidelines">{{ preview.guidelines }}</p>
        <p class="hint" data-testid="air-expert-no-knowledge">本期不返回 knowledgeContext</p>
        <button class="btn btn-sec btn-sm" type="button" data-testid="air-expert-preview-close" @click="preview = null">关闭</button>
      </div>
    </div>

    <div v-if="grantExpert" class="modal-mask" @click.self="grantExpert = null">
      <div class="card" style="width: 520px; padding: 20px" data-testid="air-expert-grant-form">
        <h3 style="margin: 0 0 8px">专家授权</h3>
        <p class="hint">{{ grantExpert.expertName }} · 授权落库后网关按表实时校验（BR-024）</p>
        <label class="fld">授权类型</label>
        <select v-model="grantForm.grantType" class="fld-in" data-testid="air-expert-grant-type" @change="onGrantType">
          <option value="DEPT">部门</option>
          <option value="ROLE">角色</option>
          <option value="PERSON">人员</option>
        </select>
        <template v-if="grantForm.grantType === 'PERSON'">
          <label class="fld">人员</label>
          <div style="display: flex; gap: 8px">
            <input v-model="userKeyword" class="fld-in" placeholder="用户名" data-testid="air-expert-grant-user-search" />
            <button class="btn btn-sec btn-sm" type="button" data-testid="air-expert-grant-user-find" @click="searchUsers">
              查找
            </button>
          </div>
        </template>
        <template v-if="grantForm.grantType === 'DEPT'">
          <label class="fld">部门</label>
          <div style="display: flex; gap: 8px">
            <input v-model="deptKeyword" class="fld-in" placeholder="组织人员姓名" data-testid="air-expert-grant-dept-search" />
            <button class="btn btn-sec btn-sm" type="button" data-testid="air-expert-grant-dept-find" @click="searchDepts">
              查找
            </button>
          </div>
        </template>
        <label class="fld">授权对象</label>
        <select v-model="grantForm.grantId" class="fld-in" data-testid="air-expert-grant-target">
          <option value="">请选择</option>
          <option v-for="opt in targetOptions" :key="opt.id" :value="opt.id">{{ opt.label }}</option>
        </select>
        <p v-if="grantError" class="hint" style="color: var(--red)" data-testid="air-expert-grant-error">{{ grantError }}</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" data-testid="air-expert-grant-close" @click="grantExpert = null">关闭</button>
          <button class="btn btn-pri btn-sm" type="button" data-testid="air-expert-grant-save" @click="submitGrant">保存授权</button>
        </div>
        <div class="tbl-wrap" style="margin-top: 12px">
          <table>
            <thead>
              <tr>
                <th>类型</th>
                <th>对象</th>
                <th>状态</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!grants.length">
                <td colspan="4">暂无授权</td>
              </tr>
              <tr v-for="item in grants" :key="item.grantId" data-testid="air-expert-grant-row">
                <td>{{ grantTypeLabel(item) }}</td>
                <td>{{ item.grantName }}</td>
                <td>{{ item.status === 'ACTIVE' ? '生效' : '已收回' }}</td>
                <td>
                  <button
                    v-if="item.status === 'ACTIVE'"
                    class="btn btn-sec btn-sm"
                    type="button"
                    data-testid="air-expert-grant-revoke"
                    @click="revokeGrant(item.grantId)"
                  >
                    收回
                  </button>
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

type Chip = { id: number; name: string; code?: string }
type Row = {
  id: number
  expertCode: string
  expertName: string
  scene: string
  ver: string
  status: string
  skillIds: number[]
  kbIds: number[]
  skillChips: Chip[]
  grantCount: number
  assembleCount: number
  ownerName: string
}
type SkillRef = { code: string; name: string; ver: string; md?: string }
type Preview = { systemPrompt: string; guidelines: string; skillRefs: SkillRef[] }
type GrantRow = { grantId: number; grantType: string; grantName: string; status: string }
type Option = { id: string; label: string }

const publishedTag = { background: 'rgba(52,199,89,.12)', color: '#1e8e3e' }
const draftTag = { background: 'rgba(142,142,147,.12)', color: '#6d6d72' }

const summary = ref<{ expertCount: number; publishedCount: number; skillCount: number; kbCount: number } | null>(null)
const rows = ref<Row[]>([])
const loading = ref(false)
const showForm = ref(false)
const formError = ref('')
const filters = reactive({ expertName: '', status: '' })
const form = reactive({ expertName: '', scene: '', systemPrompt: '', skillIds: [] as string[] })
const skillOptions = ref<{ id: number; skillName: string; skillNo: string }[]>([])
const preview = ref<Preview | null>(null)
const grantExpert = ref<Row | null>(null)
const grants = ref<GrantRow[]>([])
const grantError = ref('')
const grantForm = reactive({ grantType: 'PERSON', grantId: '' })
const targetOptions = ref<Option[]>([])
const userKeyword = ref('')
const deptKeyword = ref('')

function grantTypeLabel(item: GrantRow) {
  return ({ DEPT: '部门', ROLE: '角色', PERSON: '人员' } as Record<string, string>)[item.grantType] || item.grantType
}

async function loadSummary() {
  const res = await http.get('/air/expert/summary')
  if (res.data.code === 0) summary.value = res.data.data
}

async function loadSkills() {
  const res = await http.get('/air/skill/list', { params: { status: 'PUBLISHED', pageNo: 1, pageSize: 50 } })
  if (res.data.code === 0) skillOptions.value = res.data.data.list || []
}

async function loadPage() {
  loading.value = true
  try {
    const res = await http.get('/air/expert/page', {
      params: {
        pageNo: 1,
        pageSize: 12,
        expertName: filters.expertName || undefined,
        status: filters.status || undefined,
      },
    })
    if (res.data.code === 0) rows.value = res.data.data.list || []
  } finally {
    loading.value = false
  }
}

function openCreate() {
  formError.value = ''
  form.expertName = ''
  form.scene = ''
  form.systemPrompt = ''
  form.skillIds = []
  showForm.value = true
  loadSkills()
}

async function submitCreate() {
  formError.value = ''
  try {
    await http.post('/air/expert', {
      expertName: form.expertName,
      scene: form.scene,
      systemPrompt: form.systemPrompt,
      skillIds: form.skillIds.map((id) => Number(id)),
      toolWhitelist: ['experts.assemble', 'skills.get'],
    })
    showForm.value = false
    await loadSummary()
    await loadPage()
  } catch (error) {
    formError.value = errorMessage(error)
  }
}

async function publish(id: number) {
  await http.put(`/air/expert/${id}/publish`)
  await loadSummary()
  await loadPage()
}

async function openPreview(id: number) {
  const res = await http.get(`/air/expert/${id}`)
  if (res.data.code === 0) preview.value = res.data.data.assemblePreview
}

async function loadGrants(id: number) {
  const res = await http.get(`/air/expert/${id}`)
  grants.value = res.data.data.grants || []
}

async function openGrant(row: Row) {
  grantError.value = ''
  grantExpert.value = row
  grantForm.grantType = 'PERSON'
  grantForm.grantId = ''
  userKeyword.value = ''
  deptKeyword.value = ''
  targetOptions.value = []
  await loadGrants(row.id)
}

async function onGrantType() {
  grantForm.grantId = ''
  targetOptions.value = []
  grantError.value = ''
  if (grantForm.grantType === 'ROLE') await loadRoles()
  if (grantForm.grantType === 'DEPT') await searchDepts()
}

async function loadRoles() {
  const res = await http.get('/system/role/list')
  const list = Array.isArray(res.data.data) ? res.data.data : []
  targetOptions.value = list
    .filter((item: { status?: string }) => item.status !== 'DISABLED')
    .map((item: { id: number; roleName: string }) => ({ id: String(item.id), label: item.roleName }))
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
  if (!grantExpert.value) return
  grantError.value = ''
  if (!grantForm.grantId) {
    grantError.value = '请选择授权对象'
    return
  }
  try {
    await http.post('/air/expert/grant', {
      expertId: grantExpert.value.id,
      grantType: grantForm.grantType,
      grantId: Number(grantForm.grantId),
    })
    grantForm.grantId = ''
    await loadGrants(grantExpert.value.id)
    await loadPage()
  } catch (error) {
    grantError.value = errorMessage(error)
  }
}

async function revokeGrant(grantId: number) {
  if (!grantExpert.value) return
  await http.delete(`/air/expert/grant/${grantId}`)
  await loadGrants(grantExpert.value.id)
  await loadPage()
}

onMounted(async () => {
  await loadSummary()
  await loadSkills()
  await loadPage()
})
</script>
