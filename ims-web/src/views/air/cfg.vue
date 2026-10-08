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
      <button v-else-if="tab === 'key'" class="btn btn-pri btn-sm" type="button" data-testid="air-key-generate" @click="openGenerate">
        生成 Key
      </button>
    </div>

    <div v-if="tab === 'key'" class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>编号</th>
              <th>持有人</th>
              <th>掩码</th>
              <th>QPM 限额</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading"><td colspan="6"><div class="empty"><div class="et">加载中</div></div></td></tr>
            <tr v-for="row in keys" v-else :key="row.id">
              <td class="mono">{{ row.keyCode }}</td>
              <td>{{ row.ownerUsername || row.ownerName || row.ownerUserId }}</td>
              <td class="mono" data-testid="air-key-mask">{{ row.keyMask || row.keyPrefix }}</td>
              <td class="num" data-testid="air-qpm-cell">{{ row.qpmLimit }}</td>
              <td>{{ keyStatusLabel(row) }}</td>
              <td>
                <button
                  v-if="row.status === 'ACTIVE'"
                  class="btn btn-sec btn-sm"
                  type="button"
                  data-testid="air-key-renew"
                  @click="openRenew(row)"
                >
                  换新
                </button>
                <button
                  v-if="row.status === 'ACTIVE'"
                  class="btn btn-sec btn-sm"
                  type="button"
                  data-testid="air-key-revoke"
                  @click="revokeKey(row)"
                >
                  吊销
                </button>
              </td>
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

    <div v-if="showKeyForm" class="modal-mask" @click.self="showKeyForm = false">
      <div class="card" style="width: 440px; padding: 20px" data-testid="air-key-form">
        <h3 style="margin: 0 0 12px">{{ keyForm.mode === 'renew' ? '换新并调整 QPM' : '生成 Key' }}</h3>
        <p class="hint">明文只在成功时展示一次。换新后新 Key 的 QPM 立即按新限额计数，旧 Key 宽限 24 小时。</p>
        <template v-if="keyForm.mode === 'generate'">
          <label class="fld">归属人员</label>
          <div style="display: flex; gap: 8px; margin-bottom: 8px">
            <input v-model="userKeyword" class="fld-in" data-testid="air-key-user-search" placeholder="用户名，如 e2e_author" />
            <button class="btn btn-sec btn-sm" type="button" @click="searchUsers">查找</button>
          </div>
          <select v-model="keyForm.userId" class="fld-in" data-testid="air-key-user">
            <option value="">请选择</option>
            <option v-for="user in userOptions" :key="user.id" :value="String(user.id)">
              {{ user.username }}{{ user.nickname ? ` · ${user.nickname}` : '' }}
            </option>
          </select>
        </template>
        <label class="fld">设备用途</label>
        <input v-model="keyForm.deviceName" class="fld-in" data-testid="air-key-device" />
        <label class="fld">QPM 限额（次/分钟）</label>
        <input v-model.number="keyForm.qpmLimit" class="fld-in" type="number" min="1" data-testid="air-qpm-limit" />
        <label class="fld">有效期至</label>
        <input v-model="keyForm.expireAt" class="fld-in" type="date" data-testid="air-key-expire" />
        <p v-if="keyError" class="hint" style="color: var(--red)" data-testid="air-key-error">{{ keyError }}</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="showKeyForm = false">取消</button>
          <button class="btn btn-pri btn-sm" type="button" data-testid="air-key-save" @click="submitKey">
            {{ keyForm.mode === 'renew' ? '换新' : '生成' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="issued" class="modal-mask">
      <div class="card" style="width: 520px; padding: 20px" data-testid="air-key-plain-modal">
        <h3 style="margin: 0 0 12px">Key 明文（仅此一次）</h3>
        <p class="hint">关闭后不可再次查看。列表只保留掩码。</p>
        <p class="mono" data-testid="air-key-code">{{ issued.keyCode }}</p>
        <p class="mono" data-testid="air-key-plain" style="word-break: break-all">{{ issued.plainKey }}</p>
        <p data-testid="air-key-issued-qpm">QPM {{ issued.qpmLimit }} 次/分钟</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-pri btn-sm" type="button" data-testid="air-key-plain-close" @click="issued = null">
            关闭（明文不再显示）
          </button>
        </div>
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
import { errorMessage, http } from '../../api/http'

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
type KeyRow = {
  id: number
  keyCode: string
  ownerUserId: number
  ownerName: string
  ownerUsername: string
  keyPrefix: string
  keyMask: string
  qpmLimit: number
  status: string
  graceUntil: string
}

type IssuedKey = {
  keyId: number
  keyCode: string
  plainKey: string
  qpmLimit: number
  keyMask: string
}

const keys = ref<KeyRow[]>([])
const showKeyForm = ref(false)
const keyError = ref('')
const userKeyword = ref('')
const userOptions = ref<{ id: string; username: string; nickname: string }[]>([])
const issued = ref<IssuedKey | null>(null)
const keyForm = reactive({
  mode: 'generate' as 'generate' | 'renew',
  keyId: 0,
  userId: '',
  deviceName: '个人通用',
  qpmLimit: 60,
  expireAt: '',
})
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

function defaultExpire(): string {
  const day = new Date()
  day.setFullYear(day.getFullYear() + 1)
  const month = String(day.getMonth() + 1).padStart(2, '0')
  const date = String(day.getDate()).padStart(2, '0')
  return `${day.getFullYear()}-${month}-${date}`
}

function keyStatusLabel(row: KeyRow): string {
  if (row.status === 'REVOKED') return '已吊销'
  if (row.status === 'FROZEN') return '冻结'
  if (row.graceUntil) return '启用（宽限）'
  return '启用'
}

function openGenerate() {
  keyError.value = ''
  issued.value = null
  keyForm.mode = 'generate'
  keyForm.keyId = 0
  keyForm.userId = ''
  keyForm.deviceName = '个人通用'
  keyForm.qpmLimit = 60
  keyForm.expireAt = defaultExpire()
  userKeyword.value = ''
  userOptions.value = []
  showKeyForm.value = true
}

function openRenew(row: KeyRow) {
  keyError.value = ''
  issued.value = null
  keyForm.mode = 'renew'
  keyForm.keyId = row.id
  keyForm.userId = String(row.ownerUserId)
  keyForm.deviceName = '个人通用'
  keyForm.qpmLimit = row.qpmLimit || 60
  keyForm.expireAt = defaultExpire()
  showKeyForm.value = true
}

async function searchUsers() {
  keyError.value = ''
  try {
    const res = await http.get('/system/user/page', {
      params: { pageNo: 1, pageSize: 20, username: userKeyword.value.trim() },
    })
    userOptions.value = res.data.data.list || []
    if (userOptions.value.length === 1) keyForm.userId = String(userOptions.value[0].id)
  } catch (error) {
    keyError.value = errorMessage(error)
  }
}

async function submitKey() {
  keyError.value = ''
  const qpm = Number(keyForm.qpmLimit)
  if (!Number.isInteger(qpm) || qpm < 1) {
    keyError.value = 'QPM 限额须为正整数'
    return
  }
  if (!keyForm.expireAt) {
    keyError.value = '请填写有效期'
    return
  }
  if (keyForm.mode === 'generate' && !keyForm.userId) {
    keyError.value = '请选择归属人员'
    return
  }
  try {
    const res =
      keyForm.mode === 'renew'
        ? await http.post(`/air/key/${keyForm.keyId}/renew`, {
            deviceName: keyForm.deviceName.trim() || '个人通用',
            qpmLimit: qpm,
            expireAt: keyForm.expireAt,
          })
        : await http.post('/air/key/generate', {
            userId: Number(keyForm.userId),
            deviceName: keyForm.deviceName.trim() || '个人通用',
            qpmLimit: qpm,
            expireAt: keyForm.expireAt,
            clientToken: `ui-${Date.now()}-${Math.random().toString(16).slice(2)}`,
          })
    issued.value = res.data.data
    showKeyForm.value = false
    await loadKeys()
  } catch (error) {
    keyError.value = errorMessage(error)
  }
}

async function revokeKey(row: KeyRow) {
  if (!window.confirm(`吊销 ${row.keyCode} 后不可恢复，调用立即失败。`)) return
  try {
    await http.post(`/air/key/${row.id}/revoke`, { reason: '页面吊销' })
    await loadKeys()
  } catch (error) {
    keyError.value = errorMessage(error)
  }
}

async function loadKeys() {
  loading.value = true
  try {
    const res = await http.get('/air/cfg/key/page', { params: { pageNo: 1, pageSize: 100 } })
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

<style>
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
