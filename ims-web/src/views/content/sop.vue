<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>SOP 管理</h1>
        <div class="sub">SOP 模板列表与节点编排（CONTENT-100 · SOP 免审）</div>
      </div>
      <div class="acts">
        <button class="btn btn-pri" type="button" @click="openCreate">新增模板</button>
      </div>
    </div>
    <p class="hint" style="margin-bottom: 10px">
      运行时 SSOT：<code>/admin-api/ims/content/**</code> · 保存即启用/停用，无 SOP 审核页。
    </p>
    <form class="qbar" @submit.prevent="loadList">
      <input v-model="keyword" placeholder="模板名称" style="width: 160px" />
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">查询</button>
    </form>
    <div class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>编码</th>
              <th>名称</th>
              <th>内容类型</th>
              <th>级别</th>
              <th>版本</th>
              <th>节点数</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="8"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!rows.length">
              <td colspan="8">
                <div class="empty"><div class="et">{{ error || '暂无 SOP 模板' }}</div></div>
              </td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.id">
              <td class="mono">{{ row.sopCode }}</td>
              <td><b>{{ row.sopName }}</b></td>
              <td>{{ row.contentType }}</td>
              <td>{{ row.sopLevel }}</td>
              <td class="num">v{{ row.version }}</td>
              <td class="num">{{ row.nodeCount }}</td>
              <td>{{ row.status }}</td>
              <td>
                <button class="btn btn-sec btn-sm" type="button" @click="openNodes(row)">节点</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="pager"><span class="pg-total">共 {{ total }} 条</span></div>
    </div>

    <ProtoDrawer :open="createOpen" title="新增 SOP 模板" width="640px" @close="createOpen = false">
      <div class="formrow one">
        <div class="fld">
          <label>模板名称 *</label>
          <input v-model="form.sopName" maxlength="128" />
        </div>
        <div class="fld">
          <label>内容类型 *</label>
          <input v-model="form.contentType" placeholder="SHORT_VIDEO" />
        </div>
        <div class="fld">
          <label>级别</label>
          <select v-model="form.sopLevel">
            <option value="STANDARD">STANDARD</option>
            <option value="GUIDE">GUIDE</option>
          </select>
        </div>
        <div class="fld">
          <label>营销计划（工作任务匹配）</label>
          <select v-model="form.marketingPlan">
            <option value="">— 计划轨 —</option>
            <option value="LIVE_PUBLIC">LIVE_PUBLIC · 直播公推</option>
            <option value="PAID_SALES">PAID_SALES · 付费销售</option>
          </select>
        </div>
        <div class="fld">
          <label>首节点名称 *</label>
          <input v-model="form.nodeName" placeholder="脚本" />
        </div>
        <div class="fld">
          <label>首节点类型</label>
          <select v-model="form.nodeType">
            <option value="NORMAL">NORMAL</option>
            <option value="CONTENT_GENERATION">CONTENT_GENERATION</option>
          </select>
        </div>
        <div v-if="form.nodeType === 'CONTENT_GENERATION'" class="fld">
          <label>文档类型</label>
          <select v-model="form.documentType">
            <option value="COPY">COPY</option>
            <option value="SCRIPT">SCRIPT</option>
          </select>
        </div>
      </div>
      <template #footer>
        <button class="btn btn-sec" type="button" @click="createOpen = false">取消</button>
        <button class="btn btn-pri" type="button" :disabled="saving" @click="saveSop">保存</button>
      </template>
    </ProtoDrawer>

    <ProtoDrawer :open="nodesOpen" :title="nodeTitle" width="560px" @close="nodesOpen = false">
      <div v-if="nodesLoading" class="empty"><div class="et">加载中</div></div>
      <ul v-else class="tl">
        <li v-for="n in nodes" :key="n.id" class="tl-i">
          <b>{{ n.nodeOrder }}. {{ n.nodeName }}</b>
          <div class="hint">{{ n.standardDesc || '—' }}</div>
        </li>
      </ul>
    </ProtoDrawer>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { http, errorMessage } from '../../api/http'
import ProtoDrawer from '../../components/ProtoDrawer.vue'

const rows = ref<any[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const keyword = ref('')
const createOpen = ref(false)
const saving = ref(false)
const form = ref({
  sopName: '',
  contentType: 'SHORT_VIDEO',
  sopLevel: 'STANDARD',
  marketingPlan: '',
  nodeName: '脚本',
  nodeType: 'NORMAL',
  documentType: 'COPY',
})
const nodesOpen = ref(false)
const nodesLoading = ref(false)
const nodes = ref<any[]>([])
const nodeTitle = ref('节点详情')

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await http.get('/content/sop/list', { params: { pageNo: 1, pageSize: 50, keyword: keyword.value || undefined } })
    rows.value = data.data.list
    total.value = data.data.total
  } catch (e) {
    error.value = errorMessage(e)
    rows.value = []
  } finally {
    loading.value = false
  }
}

function openCreate() {
  form.value = {
    sopName: '',
    contentType: 'SHORT_VIDEO',
    sopLevel: 'STANDARD',
    marketingPlan: '',
    nodeName: '脚本',
    nodeType: 'NORMAL',
    documentType: 'COPY',
  }
  createOpen.value = true
}

async function saveSop() {
  saving.value = true
  try {
    await http.post('/content/sop', {
      sopName: form.value.sopName,
      contentType: form.value.contentType,
      sopLevel: form.value.sopLevel,
      marketingPlan: form.value.marketingPlan || undefined,
      nodes: [
        {
          nodeOrder: 1,
          nodeName: form.value.nodeName,
          nodeType: form.value.nodeType,
          documentType: form.value.nodeType === 'CONTENT_GENERATION' ? form.value.documentType : undefined,
          standardDesc: '执行标准',
          qualityChecklist: [{ itemCode: 'OK', itemDesc: '交付合格', required: true }],
          ownerRole: 'R6',
          slaHours: 24,
        },
      ],
    })
    createOpen.value = false
    await loadList()
  } catch (e) {
    alert(errorMessage(e))
  } finally {
    saving.value = false
  }
}

async function openNodes(row: { id: number; sopName: string }) {
  nodeTitle.value = `节点 · ${row.sopName}`
  nodesOpen.value = true
  nodesLoading.value = true
  try {
    const { data } = await http.get(`/content/sop/${row.id}/nodes`)
    nodes.value = data.data
  } catch (e) {
    nodes.value = []
    alert(errorMessage(e))
  } finally {
    nodesLoading.value = false
  }
}

loadList()
</script>
