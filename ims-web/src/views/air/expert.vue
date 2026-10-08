<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>专家库</h1>
        <div class="sub">专家包组装（Prompt+技能+知识）与授权 · /ims/air/expert</div>
      </div>
      <div class="acts">
        <button class="btn btn-pri btn-sm" type="button" @click="openCreate">新增专家</button>
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
      <input v-model="filters.expertName" placeholder="专家名称" style="width: 140px" />
      <select v-model="filters.status" style="width: 100px">
        <option value="">全部状态</option>
        <option value="DRAFT">草稿</option>
        <option value="PUBLISHED">已发布</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">查询</button>
    </form>

    <div v-if="loading" class="empty"><div class="et">加载中</div></div>
    <div v-else-if="!rows.length" class="empty"><div class="et">暂无专家包</div></div>
    <div v-else style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px">
      <div v-for="row in rows" :key="row.id" class="card hov">
        <div class="rowline" style="margin-bottom: 12px">
          <span class="av" style="width: 46px; height: 46px; border-radius: 12px; font-size: 20px; background: var(--blue)">
            {{ row.expertName.slice(0, 1) }}
          </span>
          <div style="min-width: 0; flex: 1">
            <b style="font-size: 15px; display: block">{{ row.expertName }}</b>
            <span class="mono" style="font-size: 11px; color: var(--text2)">{{ row.expertCode }} · {{ row.ver }}</span>
          </div>
          <span class="tag" :style="row.status === 'PUBLISHED' ? publishedTag : draftTag">
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
        </div>
        <div class="rowline" style="justify-content: space-between">
          <span style="font-size: 11.5px; color: var(--text2)">授权 {{ row.grantCount }} 人 · {{ row.ownerName }}</span>
          <span class="rowline" style="gap: 6px">
            <button class="btn btn-sec btn-sm" type="button" @click="openPreview(row.id)">组装预览</button>
            <button v-if="row.status === 'DRAFT'" class="btn btn-sec btn-sm" type="button" @click="publish(row.id)">发布</button>
            <button class="btn btn-pri btn-sm" type="button" @click="grant(row.id)">授权</button>
          </span>
        </div>
      </div>
    </div>

    <div v-if="showForm" class="modal-mask" @click.self="showForm = false">
      <div class="card" style="width: 520px; padding: 20px; max-height: 90vh; overflow: auto">
        <h3 style="margin: 0 0 12px">新增专家</h3>
        <label class="fld">名称</label>
        <input v-model="form.expertName" class="fld-in" />
        <label class="fld">适用场景</label>
        <input v-model="form.scene" class="fld-in" />
        <label class="fld">System Prompt</label>
        <textarea v-model="form.systemPrompt" class="fld-in" rows="4" />
        <label class="fld">挂载技能（已发布）</label>
        <select v-model="form.skillIds" multiple class="fld-in" style="min-height: 72px">
          <option v-for="s in skillOptions" :key="s.id" :value="s.id">{{ s.skillName }} ({{ s.skillNo }})</option>
        </select>
        <p v-if="formError" class="hint" style="color: var(--red)">{{ formError }}</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="showForm = false">取消</button>
          <button class="btn btn-pri btn-sm" type="button" @click="submitCreate">保存</button>
        </div>
      </div>
    </div>

    <div v-if="preview" class="modal-mask" @click.self="preview = null">
      <div class="card" style="width: 560px; padding: 20px">
        <h3 style="margin: 0 0 12px">组装预览</h3>
        <pre class="mono" style="white-space: pre-wrap; font-size: 12px; background: var(--bg2); padding: 12px; border-radius: 8px">{{
          preview.systemPrompt
        }}</pre>
        <p class="hint" style="margin-top: 12px">{{ preview.guidelines }}</p>
        <button class="btn btn-sec btn-sm" type="button" @click="preview = null">关闭</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { http } from '../../api/http'

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

const publishedTag = { background: 'rgba(52,199,89,.12)', color: '#1e8e3e' }
const draftTag = { background: 'rgba(142,142,147,.12)', color: '#6d6d72' }

const summary = ref<{ expertCount: number; publishedCount: number; skillCount: number; kbCount: number } | null>(null)
const rows = ref<Row[]>([])
const loading = ref(false)
const showForm = ref(false)
const formError = ref('')
const filters = reactive({ expertName: '', status: '' })
const form = reactive({ expertName: '', scene: '', systemPrompt: '', skillIds: [] as number[] })
const skillOptions = ref<{ id: number; skillName: string; skillNo: string }[]>([])
const preview = ref<{ systemPrompt: string; guidelines: string } | null>(null)

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
}

async function submitCreate() {
  formError.value = ''
  const res = await http.post('/air/expert', {
    expertName: form.expertName,
    scene: form.scene,
    systemPrompt: form.systemPrompt,
    skillIds: form.skillIds.map((id) => Number(id)),
    toolWhitelist: ['experts.assemble', 'skills.get'],
  })
  if (res.data.code !== 0) {
    formError.value = res.data.msg || '保存失败'
    return
  }
  showForm.value = false
  await loadSummary()
  await loadPage()
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

async function grant(id: number) {
  const res = await http.post('/air/expert/grant', { expertId: id, grantType: 'USER', grantId: 1 })
  if (res.data.code === 0) await loadPage()
  else window.alert(res.data.msg || '授权失败')
}

onMounted(async () => {
  await loadSummary()
  await loadSkills()
  await loadPage()
})
</script>
