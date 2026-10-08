<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>技能库</h1>
        <div class="sub">AI 技能登记、审核 · /ims/air/skill</div>
      </div>
      <div class="acts">
        <button class="btn btn-pri btn-sm" type="button" @click="openCreate">新增技能</button>
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
      <select v-model="filters.status" style="width: 100px">
        <option value="">全部状态</option>
        <option value="DRAFT">草稿</option>
        <option value="PENDING">审核中</option>
        <option value="PUBLISHED">已发布</option>
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
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading"><td colspan="8"><div class="empty"><div class="et">加载中</div></div></td></tr>
            <tr v-else-if="!rows.length"><td colspan="8"><div class="empty"><div class="et">暂无技能</div></div></td></tr>
            <tr v-for="row in rows" v-else :key="row.id">
              <td class="mono">{{ row.skillNo }}</td>
              <td style="font-weight: 500">{{ row.skillName }}</td>
              <td>{{ row.category }}</td>
              <td>{{ row.versionLabel }}</td>
              <td>{{ row.status }}</td>
              <td>{{ row.auditStatus }}</td>
              <td>{{ row.ownerName }}</td>
              <td>
                <button v-if="row.status === 'DRAFT'" class="btn btn-sec btn-sm" type="button" @click="submitAudit(row.id)">提交审核</button>
                <button v-if="row.auditStatus === 'PENDING'" class="btn btn-pri btn-sm" type="button" @click="audit(row.id, true)">通过</button>
                <button v-if="row.auditStatus === 'PENDING'" class="btn btn-sec btn-sm" type="button" @click="audit(row.id, false)">驳回</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="showForm" class="modal-mask" @click.self="showForm = false">
      <div class="card" style="width: 400px; padding: 20px">
        <h3 style="margin: 0 0 12px">新增技能</h3>
        <label class="fld">技能名称</label>
        <input v-model="form.skillName" class="fld-in" />
        <label class="fld">分类</label>
        <input v-model="form.category" class="fld-in" />
        <p v-if="formError" class="hint" style="color: var(--red)">{{ formError }}</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="showForm = false">取消</button>
          <button class="btn btn-pri btn-sm" type="button" @click="submitCreate">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { http } from '../../api/http'

type Row = {
  id: number
  skillNo: string
  skillName: string
  category: string
  versionLabel: string
  status: string
  auditStatus: string
  ownerName: string
}

const summary = ref<{ skillCount: number; publishedCount: number; pendingAuditCount: number; invokeTotal: number } | null>(null)
const rows = ref<Row[]>([])
const loading = ref(false)
const showForm = ref(false)
const formError = ref('')
const filters = reactive({ skillName: '', status: '' })
const form = reactive({ skillName: '', category: '内容生产' })

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
  showForm.value = true
}

async function submitCreate() {
  formError.value = ''
  const res = await http.post('/air/skill', form)
  if (res.data.code !== 0) {
    formError.value = res.data.msg || '保存失败'
    return
  }
  showForm.value = false
  await loadSummary()
  await loadList()
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

onMounted(async () => {
  await loadSummary()
  await loadList()
})
</script>
