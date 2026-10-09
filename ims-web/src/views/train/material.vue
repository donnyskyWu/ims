<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>培训资料库</h1>
        <div class="sub">TRAIN-001 · DOC/VIDEO/LINK · 02 TRAIN</div>
      </div>
      <div class="acts">
        <button class="btn btn-pri btn-sm" type="button" @click="openCreate">上传资料</button>
      </div>
    </div>
    <p class="hint" style="margin-bottom: 8px">岗位分类树只读展示；更新资料生成新版本并留档（TRN-M-R2）。列表可按标题、类型、状态、岗位和分类筛选。</p>
    <div
      class="card weekly-card"
      :class="{ warn: weeklyStatus === 'ready' && weekly.shouldUpdateCount > 0 && weekly.weeklyUpdateRate < 100 }"
      data-testid="train-weekly-rate"
    >
      <div>
        <div class="weekly-label">周更新率 BR-101 · {{ weekly.weekStart || '本周' }}</div>
        <div v-if="weeklyStatus === 'loading'" class="hint">加载中</div>
        <div v-else-if="weeklyStatus === 'error'" class="hint" data-testid="train-weekly-error">
          周更新率加载失败
          <button class="btn btn-sec btn-sm" type="button" @click="loadWeekly">重试</button>
        </div>
        <template v-else>
          <div class="weekly-num">{{ weekly.weeklyUpdateRate }}%</div>
          <div v-if="weekly.shouldUpdateCount === 0" class="hint" data-testid="train-weekly-empty">
            本周暂无已发布资料
          </div>
          <div v-else class="hint">
            已更新 {{ weekly.updatedCount }} / 应更新 {{ weekly.shouldUpdateCount }}
            <span v-if="weekly.weeklyUpdateRate < 100"> · 未达 100%，请督办</span>
          </div>
        </template>
      </div>
      <button class="btn btn-sec btn-sm" type="button" data-testid="train-unupdated-open" @click="openUnupdated">
        未更新清单
      </button>
    </div>
    <div class="g2" style="margin-bottom: 12px; align-items: flex-start">
      <div class="card" style="padding: 12px; max-height: 280px; overflow: auto">
        <div style="font-weight: 600; margin-bottom: 8px">分类树</div>
        <div v-if="cateStatus === 'loading'" class="empty"><div class="et">加载分类…</div></div>
        <div v-else-if="cateStatus === 'error'" class="empty" data-testid="train-cate-empty">
          <div class="et">分类加载失败</div>
          <button class="btn btn-sec btn-sm" type="button" @click="loadCates">重试</button>
        </div>
        <div v-else-if="!cates.length" class="empty" data-testid="train-cate-empty">
          <div class="et">暂无分类</div>
        </div>
        <ul v-else class="tree">
          <li v-for="root in cates" :key="root.id">
            <span>{{ root.cateName }} <small>({{ root.positionCode }})</small></span>
            <ul>
              <li v-for="child in root.children" :key="child.id">
                <button
                  type="button"
                  class="linkish"
                  :class="{ on: filters.cateId === child.id }"
                  data-testid="train-cate-node"
                  @click="pickCate(child)"
                >
                  {{ child.cateName }} · {{ child.materialCount }}
                </button>
              </li>
            </ul>
          </li>
        </ul>
      </div>
      <div style="flex: 1">
        <form class="qbar" data-testid="train-material-filters" @submit.prevent="loadList">
          <input v-model="filters.title" placeholder="标题" style="width: 140px" data-testid="train-filter-title" />
          <select v-model="filters.materialType" style="width: 100px" data-testid="train-filter-type">
            <option value="">全部类型</option>
            <option value="DOC">文档</option>
            <option value="VIDEO">视频</option>
            <option value="LINK">外链</option>
          </select>
          <select v-model="filters.status" style="width: 100px" data-testid="train-filter-status">
            <option value="">全部状态</option>
            <option value="DRAFT">草稿</option>
            <option value="PUBLISHED">已发布</option>
            <option value="OFFLINE">已下架</option>
          </select>
          <select v-model="filters.positionCode" style="width: 150px" data-testid="train-filter-position">
            <option value="">全部岗位</option>
            <option v-for="item in positionOptions" :key="item.code" :value="item.code">{{ item.label }}</option>
          </select>
          <span class="sp"></span>
          <button class="btn btn-pri btn-sm" type="submit">查询</button>
          <button class="btn btn-sec btn-sm" type="button" data-testid="train-filter-reset" @click="resetFilters">
            重置
          </button>
        </form>
        <p v-if="hasActiveFilters" class="filter-note" data-testid="train-filter-summary">
          当前筛选：{{ filterSummary }}
          <button type="button" class="linkish" @click="resetFilters">清除筛选</button>
        </p>
        <div class="tbl-block">
          <div class="tbl-wrap">
            <table>
              <thead>
                <tr>
                  <th>编号</th>
                  <th>标题</th>
                  <th>类型</th>
                  <th>版本</th>
                  <th>岗位</th>
                  <th>状态</th>
                  <th>更新人</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="loading">
                  <td colspan="8"><div class="empty"><div class="et">加载中</div></div></td>
                </tr>
                <tr v-else-if="!rows.length">
                  <td colspan="8">
                    <div class="empty" data-testid="train-material-empty">
                      <div data-testid="train-list-empty">
                        <div class="et">{{ error || listEmptyText }}</div>
                        <div v-if="!error && hasActiveFilters" class="es">调整标题、类型、状态、岗位或分类后再查询</div>
                        <button
                          v-if="!error && hasActiveFilters"
                          class="btn btn-sec btn-sm"
                          type="button"
                          data-testid="train-filter-clear-empty"
                          @click="resetFilters"
                        >
                          清除筛选
                        </button>
                      </div>
                    </div>
                  </td>
                </tr>
                <tr v-for="row in rows" v-else :key="row.id">
                  <td class="mono">{{ row.materialNo }}</td>
                  <td style="font-weight: 500">{{ row.title }}</td>
                  <td>{{ typeLabel(row.materialType) }}</td>
                  <td class="mono" data-testid="train-material-version">V{{ row.version || 1 }}</td>
                  <td>
                    <template v-if="(row.positionCodes || []).length">
                      <span
                        v-for="code in (row.positionCodes || []).slice(0, 3)"
                        :key="code"
                        class="tag pos-tag"
                        data-testid="train-material-position"
                      >
                        {{ code }}
                      </span>
                      <span v-if="(row.positionCodes || []).length > 3" class="hint">+{{ (row.positionCodes || []).length - 3 }}</span>
                    </template>
                    <span v-else class="hint">—</span>
                  </td>
                  <td>
                    <span class="tag" :style="statusStyle(row.status)" data-testid="train-material-status">
                      <span class="dot"></span>{{ statusLabel(row.status) }}
                    </span>
                  </td>
                  <td>{{ row.uploaderName }}</td>
                  <td>
                    <button class="btn btn-sec btn-sm" type="button" data-testid="train-material-detail" @click="openDetail(row)">
                      详情
                    </button>
                    <button class="btn btn-sec btn-sm" type="button" data-testid="train-material-edit" @click="openEdit(row)">
                      编辑
                    </button>
                    <button
                      v-if="row.status !== 'OFFLINE'"
                      class="btn btn-sec btn-sm"
                      type="button"
                      @click="offline(row)"
                    >
                      下架
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-if="!loading" class="pager">
            <span class="pg-total" data-testid="train-material-total">共 {{ total }} 条</span>
          </div>
        </div>
      </div>
    </div>

    <div v-if="showForm" class="modal-mask" @click.self="showForm = false">
      <div class="card" style="width: 400px; padding: 20px">
        <h3 style="margin: 0 0 12px">{{ editingId ? '更新资料' : '上传资料' }}</h3>
        <label class="fld">分类 ID</label>
        <input v-model.number="form.cateId" type="number" class="fld-in" />
        <p v-if="formPositionCode" class="hint" data-testid="train-material-position-hint">
          关联岗位 {{ formPositionCode }}，发布后该岗位学员可见；存草稿则学员不可见
        </p>
        <p v-else-if="Number(form.cateId) > 0" class="hint" data-testid="train-material-position-missing">该分类未关联岗位</p>
        <label class="fld">标题</label>
        <input v-model="form.title" class="fld-in" />
        <label class="fld">类型</label>
        <select v-model="form.materialType" class="fld-in" data-testid="train-form-type">
          <option value="DOC">文档</option>
          <option value="VIDEO">视频</option>
          <option value="LINK">外链</option>
        </select>
        <label v-if="form.materialType === 'LINK'" class="fld">外链</label>
        <input
          v-if="form.materialType === 'LINK'"
          v-model="form.linkUrl"
          class="fld-in"
          data-testid="train-form-link"
          placeholder="https://"
        />
        <template v-else>
          <label class="fld">fileKey</label>
          <input v-model="form.fileKey" class="fld-in" placeholder="直传回执 key" />
        </template>
        <p v-if="editingId" class="hint">将生成新版本 V{{ editingVersion + 1 }}，旧版本留档</p>
        <p v-if="formError" class="hint" style="color: var(--red)" data-testid="train-material-form-error">{{ formError }}</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="showForm = false">取消</button>
          <template v-if="editingId">
            <button class="btn btn-pri btn-sm" type="button" @click="submitUpdate">保存新版本</button>
          </template>
          <template v-else>
            <button class="btn btn-sec btn-sm" type="button" @click="submit(false)">草稿</button>
            <button class="btn btn-pri btn-sm" type="button" @click="submit(true)">发布</button>
          </template>
        </div>
      </div>
    </div>

    <div v-if="detail" class="modal-mask" @click.self="detail = null">
      <div class="card detail-card" data-testid="train-material-detail-drawer">
        <h3 style="margin: 0 0 12px">资料详情</h3>
        <p class="mono">{{ detail.materialNo }} · V{{ detail.version || 1 }}</p>
        <p>{{ detail.title }}</p>
        <p class="hint">{{ detail.materialType }} · {{ detail.status }} · {{ detail.uploaderName }}</p>
        <div data-testid="train-material-preview">
          <h4 style="margin: 12px 0 8px">预览</h4>
          <p class="hint">只读预览，历史版本不可修改</p>
          <template v-if="preview">
            <p>{{ preview.archived ? '历史' : '当前' }} V{{ preview.version }} · {{ preview.title }}</p>
            <template v-if="previewKind === 'link'">
              <p class="mono">{{ preview.linkUrl }}</p>
              <a class="linkish" :href="preview.linkUrl" target="_blank" rel="noopener">打开外链</a>
            </template>
            <template v-else-if="previewKind === 'file'">
              <p class="mono">文件留档 {{ preview.fileKey }}</p>
              <p class="hint">本地留档，暂无在线播放地址</p>
            </template>
            <div v-else class="empty" data-testid="train-preview-empty"><div class="et">暂无可预览内容</div></div>
          </template>
        </div>
        <h4 style="margin: 12px 0 8px">版本历史</h4>
        <ul data-testid="train-version-history">
          <li>
            <button
              type="button"
              class="linkish"
              :class="{ on: previewVersion == null }"
              data-testid="train-version-current"
              @click="previewVersion = null"
            >
              当前 V{{ detail.version || 1 }} {{ detail.title }}
            </button>
          </li>
          <li v-for="item in detail.versions || []" :key="item.version">
            <button
              type="button"
              class="linkish"
              :class="{ on: previewVersion === item.version }"
              data-testid="train-version-archive"
              @click="previewVersion = item.version"
            >
              V{{ item.version }} {{ item.title }} · {{ item.editorName || '—' }} · {{ item.updatedAt }}
            </button>
          </li>
        </ul>
        <p v-if="!detail.versions?.length" class="hint">尚无历史版本</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-pri btn-sm" type="button" @click="detail = null">关闭</button>
        </div>
      </div>
    </div>

    <div v-if="showUnupdated" class="modal-mask" @click.self="showUnupdated = false">
      <div class="card" style="width: 560px; padding: 20px; max-height: 80vh; overflow: auto" data-testid="train-unupdated-drawer">
        <h3 style="margin: 0 0 12px">未更新清单</h3>
        <table>
          <thead>
            <tr>
              <th>编号</th>
              <th>标题</th>
              <th>负责人</th>
              <th>最后更新</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="weeklyStatus !== 'ready'">
              <td colspan="4">{{ weeklyStatus === 'error' ? '周更新率加载失败' : '加载中' }}</td>
            </tr>
            <tr v-else-if="weekly.shouldUpdateCount === 0">
              <td colspan="4" data-testid="train-unupdated-empty">本周暂无已发布资料</td>
            </tr>
            <tr v-else-if="!weekly.unupdatedList.length">
              <td colspan="4" data-testid="train-unupdated-empty">本周已发布资料都已更新</td>
            </tr>
            <tr v-for="item in weekly.unupdatedList" v-else :key="item.materialNo">
              <td class="mono">{{ item.materialNo }}</td>
              <td>{{ item.title }}</td>
              <td>{{ item.ownerName || '—' }}</td>
              <td class="mono">{{ item.lastUpdatedAt }}</td>
            </tr>
          </tbody>
        </table>
        <p v-if="copyHint" class="hint" data-testid="train-unupdated-copy-hint">{{ copyHint }}</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="copyUnupdated">复制清单</button>
          <button class="btn btn-pri btn-sm" type="button" @click="showUnupdated = false">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { errorMessage, http } from '../../api/http'

type Cate = {
  id: number
  cateName: string
  positionCode?: string
  materialCount: number
  children: Cate[]
}

type VersionItem = {
  version: number
  title: string
  materialType?: string
  fileKey?: string
  linkUrl?: string
  editorName?: string
  updatedAt: string
}

type Row = {
  id: number
  materialNo: string
  title: string
  cateId?: number
  materialType: string
  fileKey?: string
  linkUrl?: string
  version?: number
  versions?: VersionItem[]
  positionCodes?: string[]
  status: string
  uploaderName: string
}

type Weekly = {
  weekStart: string
  shouldUpdateCount: number
  updatedCount: number
  weeklyUpdateRate: number
  unupdatedList: Array<{ materialNo: string; title: string; lastUpdatedAt: string; ownerName: string }>
}

const route = useRoute()
const cates = ref<Cate[]>([])
const cateStatus = ref<'loading' | 'ready' | 'error'>('loading')
const rows = ref<Row[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const showForm = ref(false)
const editingId = ref(0)
const editingVersion = ref(1)
const detail = ref<Row | null>(null)
const previewVersion = ref<number | null>(null)
const showUnupdated = ref(false)
const copyHint = ref('')
const formError = ref('')
const weeklyStatus = ref<'loading' | 'ready' | 'error'>('loading')
const weekly = reactive<Weekly>({
  weekStart: '',
  shouldUpdateCount: 0,
  updatedCount: 0,
  weeklyUpdateRate: 100,
  unupdatedList: [],
})
const filters = reactive({ title: '', materialType: '', status: '', positionCode: '', cateId: 0 })
const form = reactive({
  cateId: 0,
  title: '',
  materialType: 'DOC',
  fileKey: 'demo/file.pdf',
  linkUrl: '',
})

const positionOptions = computed(() => {
  const seen = new Map<string, string>()
  for (const root of cates.value) {
    const code = (root.positionCode || '').trim()
    if (!code || seen.has(code)) continue
    seen.set(code, root.cateName ? `${root.cateName} · ${code}` : code)
  }
  return [...seen.entries()].map(([code, label]) => ({ code, label }))
})

const selectedCateName = computed(() => {
  if (!filters.cateId) return ''
  for (const root of cates.value) {
    if (root.id === filters.cateId) return root.cateName
    for (const child of root.children || []) {
      if (child.id === filters.cateId) return child.cateName
    }
  }
  return ''
})

const hasActiveFilters = computed(
  () =>
    Boolean(
      filters.title.trim() ||
        filters.materialType ||
        filters.status ||
        filters.positionCode ||
        filters.cateId,
    ),
)

const filterSummary = computed(() => {
  const parts: string[] = []
  if (filters.title.trim()) parts.push(`标题「${filters.title.trim()}」`)
  if (filters.materialType) parts.push(typeLabel(filters.materialType))
  if (filters.status) parts.push(statusLabel(filters.status))
  if (filters.positionCode) parts.push(`岗位 ${filters.positionCode}`)
  if (selectedCateName.value) parts.push(`分类 ${selectedCateName.value}`)
  return parts.join(' · ')
})

function typeLabel(value: string) {
  if (value === 'DOC') return '文档'
  if (value === 'VIDEO') return '视频'
  if (value === 'LINK') return '外链'
  return value || '—'
}

function statusLabel(value: string) {
  if (value === 'DRAFT') return '草稿'
  if (value === 'PUBLISHED') return '已发布'
  if (value === 'OFFLINE') return '已下架'
  return value || '—'
}

function statusStyle(value: string) {
  if (value === 'PUBLISHED') return 'background: rgba(52,199,89,.15); color: #248a3d'
  if (value === 'OFFLINE') return 'background: rgba(255,59,48,.12); color: #d70015'
  return 'background: rgba(142,142,147,.12); color: #6d6d72'
}

const listEmptyText = computed(() => {
  const cateOnly =
    Boolean(filters.cateId) &&
    !filters.title.trim() &&
    !filters.materialType &&
    !filters.status &&
    !filters.positionCode
  if (cateOnly) return '该分类暂无资料'
  if (hasActiveFilters.value) return '没有符合筛选的资料'
  return '暂无资料'
})

const preview = computed(() => {
  const row = detail.value
  if (!row) return null
  if (previewVersion.value == null) {
    return {
      version: row.version || 1,
      title: row.title,
      materialType: row.materialType,
      fileKey: row.fileKey,
      linkUrl: row.linkUrl,
      archived: false,
    }
  }
  const found = (row.versions || []).find((item) => item.version === previewVersion.value)
  if (!found) return null
  return {
    version: found.version,
    title: found.title,
    materialType: found.materialType || row.materialType,
    fileKey: found.fileKey,
    linkUrl: found.linkUrl,
    archived: true,
  }
})

const previewKind = computed(() => {
  const item = preview.value
  if (!item) return 'empty'
  if (item.materialType === 'LINK') return item.linkUrl?.trim() ? 'link' : 'empty'
  return item.fileKey?.trim() ? 'file' : 'empty'
})

function findCate(id: number): Cate | null {
  if (!id) return null
  for (const root of cates.value) {
    if (root.id === id) return root
    for (const child of root.children || []) {
      if (child.id === id) return child
    }
  }
  return null
}

const formPositionCode = computed(() => (findCate(form.cateId)?.positionCode || '').trim())

function isHttpUrl(value: string) {
  const text = value.trim()
  if (!text || /\s/.test(text)) return false
  const lowered = text.toLowerCase()
  return (lowered.startsWith('https://') || lowered.startsWith('http://')) && text.length > (lowered.startsWith('https://') ? 8 : 7)
}

async function loadCates() {
  cateStatus.value = 'loading'
  try {
    const res = await http.get('/train/material/cates')
    if (res.data.code !== 0) {
      cates.value = []
      cateStatus.value = 'error'
      return
    }
    cates.value = res.data.data || []
    cateStatus.value = 'ready'
  } catch {
    cates.value = []
    cateStatus.value = 'error'
  }
}

function pickCate(child: Cate) {
  filters.cateId = child.id
  form.cateId = child.id
  loadList()
}

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const params: Record<string, string | number> = { pageNo: 1, pageSize: 20 }
    if (filters.title.trim()) params.title = filters.title.trim()
    if (filters.materialType) params.materialType = filters.materialType
    if (filters.status) params.status = filters.status
    if (filters.positionCode) params.positionCode = filters.positionCode
    if (filters.cateId) params.cateId = filters.cateId
    const res = await http.get('/train/material/list', { params })
    if (res.data.code !== 0) {
      error.value = res.data.msg || '加载失败'
      rows.value = []
      total.value = 0
      return
    }
    rows.value = (res.data.data.list || []).map((row: Row) => ({
      ...row,
      positionCodes: Array.isArray(row.positionCodes) ? row.positionCodes : [],
    }))
    total.value = res.data.data.total || 0
  } catch {
    error.value = '网络错误'
    rows.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  filters.title = ''
  filters.materialType = ''
  filters.status = ''
  filters.positionCode = ''
  filters.cateId = 0
  loadList()
}

function openCreate() {
  editingId.value = 0
  editingVersion.value = 1
  form.title = ''
  form.materialType = 'DOC'
  form.fileKey = 'demo/file.pdf'
  form.linkUrl = ''
  if (!form.cateId && cates.value[0]?.children?.[0]) {
    form.cateId = cates.value[0].children[0].id
  }
  formError.value = ''
  showForm.value = true
}

function openEdit(row: Row) {
  editingId.value = row.id
  editingVersion.value = row.version || 1
  form.cateId = row.cateId || form.cateId
  form.title = row.title
  form.materialType = row.materialType || 'DOC'
  form.fileKey = row.fileKey || 'demo/file.pdf'
  form.linkUrl = row.linkUrl || ''
  formError.value = ''
  showForm.value = true
}

function openDetail(row: Row) {
  previewVersion.value = null
  detail.value = row
}

function openUnupdated() {
  copyHint.value = ''
  showUnupdated.value = true
}

async function loadWeekly() {
  weeklyStatus.value = 'loading'
  try {
    const res = await http.get('/train/material/weekly-update-metrics')
    if (res.data.code !== 0) {
      weeklyStatus.value = 'error'
      return
    }
    const data = res.data.data || {}
    weekly.weekStart = data.weekStart || ''
    weekly.shouldUpdateCount = data.shouldUpdateCount || 0
    weekly.updatedCount = data.updatedCount || 0
    weekly.weeklyUpdateRate = data.weeklyUpdateRate ?? 100
    weekly.unupdatedList = data.unupdatedList || []
    weeklyStatus.value = 'ready'
  } catch {
    weeklyStatus.value = 'error'
  }
}

async function copyUnupdated() {
  if (weeklyStatus.value !== 'ready' || !weekly.unupdatedList.length) {
    copyHint.value = weekly.shouldUpdateCount === 0 ? '本周暂无已发布资料' : '没有可复制的未更新资料'
    return
  }
  const text = weekly.unupdatedList
    .map((item) => `${item.materialNo}\t${item.title}\t${item.ownerName || ''}\t${item.lastUpdatedAt}`)
    .join('\n')
  try {
    await navigator.clipboard.writeText(text)
    copyHint.value = '已复制清单'
  } catch {
    copyHint.value = '无法写入剪贴板，请从清单中复制'
  }
}

function materialPayload(publish: boolean) {
  const body: Record<string, unknown> = {
    title: form.title.trim(),
    cateId: form.cateId,
    materialType: form.materialType,
    positionCodes: formPositionCode.value ? [formPositionCode.value] : [],
    publish,
  }
  if (form.materialType === 'LINK') body.linkUrl = form.linkUrl.trim()
  else body.fileKey = form.fileKey.trim()
  return body
}

function formInvalid() {
  if (!form.title.trim() || !form.cateId) return '标题与分类必填'
  const cate = findCate(form.cateId)
  if (cate && !formPositionCode.value) return '请选择已关联岗位的分类'
  if (form.materialType === 'LINK' && !isHttpUrl(form.linkUrl)) return '外链须为 http(s) 地址'
  if (form.materialType !== 'LINK' && !form.fileKey.trim()) return 'fileKey 必填'
  return ''
}

async function submit(publish: boolean) {
  formError.value = formInvalid()
  if (formError.value) return
  const body = materialPayload(publish)
  let res
  try {
    res = await http.post('/train/material', body)
  } catch (err) {
    formError.value = errorMessage(err)
    return
  }
  if (res.data.code !== 0) {
    formError.value = res.data.msg || '保存失败'
    return
  }
  showForm.value = false
  await loadCates()
  await loadList()
  await loadWeekly()
}

async function submitUpdate() {
  formError.value = !editingId.value ? '标题与分类必填' : formInvalid()
  if (formError.value) return
  const body = materialPayload(true)
  let res
  try {
    res = await http.put(`/train/material/${editingId.value}`, body)
  } catch (err) {
    formError.value = errorMessage(err)
    return
  }
  if (res.data.code !== 0) {
    formError.value = res.data.msg || '保存失败'
    return
  }
  showForm.value = false
  editingId.value = 0
  await loadCates()
  await loadList()
  await loadWeekly()
}

async function offline(row: Row) {
  if (!confirm(`下架「${row.title}」？`)) return
  const res = await http.delete(`/train/material/${row.id}`)
  if (res.data.code === 0) await loadList()
}

onMounted(async () => {
  const rawTitle = route.query.title
  const title = typeof rawTitle === 'string' ? rawTitle : ''
  if (title) filters.title = title
  await loadCates()
  await loadList()
  await loadWeekly()
  const rawId = route.query.materialId
  const materialId = Number(typeof rawId === 'string' ? rawId : '')
  if (!materialId) return
  const hit = rows.value.find((row) => row.id === materialId)
  if (hit) openDetail(hit)
})
</script>

<style scoped>
.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.tree {
  list-style: none;
  padding-left: 0;
  font-size: 13px;
}
.tree ul {
  padding-left: 16px;
}
.linkish {
  background: none;
  border: none;
  color: var(--blue);
  cursor: pointer;
  padding: 0;
  font-size: 13px;
}
.linkish.on {
  font-weight: 650;
  text-decoration: underline;
}
.filter-note {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: -6px 0 12px;
  font-size: 12px;
  color: var(--text2);
}
.pos-tag {
  margin-right: 4px;
  background: rgba(0, 113, 227, 0.1);
  color: var(--blue);
}
.detail-card {
  width: min(720px, 92vw);
  padding: 20px;
  max-height: 86vh;
  overflow: auto;
}
.fld {
  display: block;
  font-size: 12px;
  color: var(--text2);
  margin: 8px 0 4px;
}
.fld-in {
  width: 100%;
  box-sizing: border-box;
}
.weekly-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  margin-bottom: 12px;
}
.weekly-card.warn {
  border: 1px solid #e6a700;
}
.weekly-label {
  font-size: 12px;
  color: var(--text2);
}
.weekly-num {
  font-size: 22px;
  font-weight: 650;
}
.g2 {
  display: grid;
  grid-template-columns: 240px 1fr;
  gap: 12px;
}
</style>
