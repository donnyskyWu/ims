<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>模型与提示词</h1>
        <div class="sub">OPS M8 收编 · 禁止两套 Key · /ims/air/cfg</div>
      </div>
    </div>

    <div class="rowline" style="gap: 8px; margin-bottom: 12px; flex-wrap: wrap">
      <button class="btn btn-sm" :class="tab === 'model' ? 'btn-pri' : 'btn-sec'" type="button" @click="switchTab('model')">
        模型连接
      </button>
      <button class="btn btn-sm" :class="tab === 'prompt' ? 'btn-pri' : 'btn-sec'" type="button" @click="switchTab('prompt')">
        提示词
      </button>
      <button class="btn btn-sm" :class="tab === 'key' ? 'btn-pri' : 'btn-sec'" type="button" @click="switchTab('key')">
        Key 管理
      </button>
      <button class="btn btn-sm" :class="tab === 'audit' ? 'btn-pri' : 'btn-sec'" type="button" @click="switchTab('audit')">
        审计监控
      </button>
      <span class="sp"></span>
      <button v-if="tab === 'model'" class="btn btn-pri btn-sm" type="button" @click="openModelForm()">新增模型</button>
      <button v-else-if="tab === 'prompt'" class="btn btn-pri btn-sm" type="button" @click="openPromptForm()">新增提示词</button>
    </div>

    <div v-if="tab === 'key'" class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>编号</th>
              <th>持有人</th>
              <th>前缀</th>
              <th>白名单</th>
              <th>状态</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading"><td colspan="5"><div class="empty"><div class="et">加载中</div></div></td></tr>
            <tr v-for="row in keys" v-else :key="row.id">
              <td class="mono">{{ row.keyCode }}</td>
              <td>{{ row.ownerName || row.ownerUserId }}</td>
              <td class="mono">{{ row.keyPrefix }}</td>
              <td class="mono">{{ row.whitelist }}</td>
              <td>{{ row.status }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-else-if="tab === 'audit'" class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>Trace</th>
              <th>场景</th>
              <th>模型</th>
              <th>Token</th>
              <th>耗时 ms</th>
              <th>状态</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading"><td colspan="6"><div class="empty"><div class="et">加载中</div></div></td></tr>
            <tr v-for="row in audits" v-else :key="row.id">
              <td class="mono">{{ row.traceId }}</td>
              <td>{{ row.scene }}</td>
              <td>{{ row.modelName }}</td>
              <td class="num">{{ row.tokenIn }}/{{ row.tokenOut }}</td>
              <td class="num">{{ row.latencyMs }}</td>
              <td>{{ row.status }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-else-if="tab === 'model'" class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>编号</th>
              <th>厂商</th>
              <th>模型</th>
              <th>场景</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading"><td colspan="6"><div class="empty"><div class="et">加载中</div></div></td></tr>
            <tr v-for="row in models" v-else :key="row.id">
              <td class="mono">{{ row.configCode }}</td>
              <td>{{ row.vendor }}</td>
              <td>{{ row.modelName }}</td>
              <td>{{ row.useCase }}</td>
              <td>{{ row.status }}</td>
              <td><button class="btn btn-sec btn-sm" type="button" @click="openModelForm(row)">编辑</button></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-else-if="tab === 'prompt'" class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>编号</th>
              <th>场景</th>
              <th>文档类型</th>
              <th>版本</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading"><td colspan="6"><div class="empty"><div class="et">加载中</div></div></td></tr>
            <tr v-for="row in prompts" v-else :key="row.id">
              <td class="mono">{{ row.promptCode }}</td>
              <td>{{ row.scene }}</td>
              <td>{{ row.docType || '—' }}</td>
              <td>{{ row.versionLabel }}</td>
              <td>{{ row.status }}</td>
              <td><button class="btn btn-sec btn-sm" type="button" @click="openPromptForm(row)">编辑</button></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="showModel" class="modal-mask" @click.self="showModel = false">
      <div class="card" style="width: 440px; padding: 20px">
        <h3 style="margin: 0 0 12px">{{ modelForm.id ? '编辑模型' : '新增模型' }}</h3>
        <label class="fld">厂商</label>
        <input v-model="modelForm.vendor" class="fld-in" placeholder="QWEN / GPT …" />
        <label class="fld">模型名</label>
        <input v-model="modelForm.modelName" class="fld-in" />
        <label class="fld">Endpoint</label>
        <input v-model="modelForm.endpointUrl" class="fld-in" />
        <label class="fld">状态</label>
        <select v-model="modelForm.status" class="fld-in">
          <option value="CONNECTED">CONNECTED</option>
          <option value="DISCONNECTED">DISCONNECTED</option>
        </select>
        <p v-if="formError" class="hint" style="color: var(--red)">{{ formError }}</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="showModel = false">取消</button>
          <button class="btn btn-pri btn-sm" type="button" @click="saveModel">保存</button>
        </div>
      </div>
    </div>

    <div v-if="showPrompt" class="modal-mask" @click.self="showPrompt = false">
      <div class="card" style="width: 480px; padding: 20px">
        <h3 style="margin: 0 0 12px">{{ promptForm.id ? '编辑提示词' : '新增提示词' }}</h3>
        <label class="fld">场景</label>
        <input v-model="promptForm.scene" class="fld-in" />
        <label class="fld">文档类型</label>
        <input v-model="promptForm.docType" class="fld-in" />
        <label class="fld">正文</label>
        <textarea v-model="promptForm.content" class="fld-in" rows="5" />
        <p v-if="formError" class="hint" style="color: var(--red)">{{ formError }}</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="showPrompt = false">取消</button>
          <button class="btn btn-pri btn-sm" type="button" @click="savePrompt">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { http } from '../../api/http'

type ModelRow = {
  id: number
  configCode: string
  vendor: string
  modelName: string
  useCase: string
  endpointUrl: string
  status: string
}

type PromptRow = {
  id: number
  promptCode: string
  scene: string
  docType: string
  versionLabel: string
  content: string
  status: string
}

type TabId = 'model' | 'prompt' | 'key' | 'audit'

const route = useRoute()
const router = useRouter()
const tab = ref<TabId>('model')
const loading = ref(false)
const models = ref<ModelRow[]>([])
const prompts = ref<PromptRow[]>([])
const keys = ref<
  { id: number; keyCode: string; ownerUserId: number; ownerName: string; keyPrefix: string; whitelist: string; status: string }[]
>([])
const audits = ref<
  {
    id: number
    traceId: string
    scene: string
    modelName: string
    tokenIn: number
    tokenOut: number
    latencyMs: number
    status: string
  }[]
>([])
const showModel = ref(false)
const showPrompt = ref(false)
const formError = ref('')

const modelForm = reactive({
  id: 0,
  vendor: '',
  modelName: '',
  endpointUrl: '',
  status: 'CONNECTED',
})

const promptForm = reactive({
  id: 0,
  scene: '',
  docType: '',
  content: '',
  status: 'ENABLED',
})

function tabFromRoute(): TabId {
  const q = String(route.query.tab || '')
  if (q === 'key' || q === 'audit' || q === 'prompt') return q
  return 'model'
}

function switchTab(name: TabId) {
  tab.value = name
  router.replace({ path: '/ims/air/cfg', query: name === 'model' ? {} : { tab: name } })
  loadTabData(name)
}

async function loadKeys() {
  loading.value = true
  try {
    const res = await http.get('/air/cfg/key/page', { params: { pageNo: 1, pageSize: 50 } })
    if (res.data.code === 0) keys.value = res.data.data.list || []
  } finally {
    loading.value = false
  }
}

async function loadAudits() {
  loading.value = true
  try {
    const res = await http.get('/air/cfg/audit/page', { params: { pageNo: 1, pageSize: 50 } })
    if (res.data.code === 0) audits.value = res.data.data.list || []
  } finally {
    loading.value = false
  }
}

function loadTabData(name: TabId) {
  if (name === 'model') loadModels()
  else if (name === 'prompt') loadPrompts()
  else if (name === 'key') loadKeys()
  else loadAudits()
}

async function loadModels() {
  loading.value = true
  try {
    const res = await http.get('/air/cfg/model/page', { params: { pageNo: 1, pageSize: 50 } })
    if (res.data.code === 0) models.value = res.data.data.list || []
  } finally {
    loading.value = false
  }
}

async function loadPrompts() {
  loading.value = true
  try {
    const res = await http.get('/air/cfg/prompt/page', { params: { pageNo: 1, pageSize: 50 } })
    if (res.data.code === 0) prompts.value = res.data.data.list || []
  } finally {
    loading.value = false
  }
}

function openModelForm(row?: ModelRow) {
  formError.value = ''
  modelForm.id = row?.id || 0
  modelForm.vendor = row?.vendor || ''
  modelForm.modelName = row?.modelName || ''
  modelForm.endpointUrl = row?.endpointUrl || ''
  modelForm.status = row?.status || 'CONNECTED'
  showModel.value = true
}

function openPromptForm(row?: PromptRow) {
  formError.value = ''
  promptForm.id = row?.id || 0
  promptForm.scene = row?.scene || ''
  promptForm.docType = row?.docType || ''
  promptForm.content = row?.content || ''
  promptForm.status = row?.status || 'ENABLED'
  showPrompt.value = true
}

async function saveModel() {
  formError.value = ''
  const body = {
    vendor: modelForm.vendor,
    modelName: modelForm.modelName,
    endpointUrl: modelForm.endpointUrl,
    status: modelForm.status,
  }
  const res = modelForm.id
    ? await http.put(`/air/cfg/model/${modelForm.id}`, body)
    : await http.post('/air/cfg/model', body)
  if (res.data.code !== 0) {
    formError.value = res.data.msg || '保存失败'
    return
  }
  showModel.value = false
  await loadModels()
}

async function savePrompt() {
  formError.value = ''
  const body = {
    scene: promptForm.scene,
    docType: promptForm.docType,
    content: promptForm.content,
    status: promptForm.status,
  }
  const res = promptForm.id
    ? await http.put(`/air/cfg/prompt/${promptForm.id}`, body)
    : await http.post('/air/cfg/prompt', body)
  if (res.data.code !== 0) {
    formError.value = res.data.msg || '保存失败'
    return
  }
  showPrompt.value = false
  await loadPrompts()
}

watch(
  () => route.fullPath,
  () => {
    tab.value = tabFromRoute()
  },
  { immediate: true }
)

onMounted(() => {
  tab.value = tabFromRoute()
  loadTabData(tab.value)
})
</script>
