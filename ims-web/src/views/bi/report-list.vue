<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>报表管理</h1>
        <div class="sub">
          报表/大屏统一目录 · /ims/bi/report/list · BI-001 首片 · 列表按 BR-212 行级过滤（创建者 ∩ 查看者）
        </div>
      </div>
      <div class="acts">
        <button class="btn btn-sec btn-sm" type="button" data-testid="bi-import-open" @click="openImport">导入模板</button>
        <button class="btn btn-pri btn-sm" type="button" @click="openCreate">新建报表</button>
        <router-link class="btn btn-sec btn-sm" to="/ims/bi/report/subscribe">订阅与分享</router-link>
        <router-link class="btn btn-sec btn-sm" to="/ims/bi/report/preview">预览与下钻</router-link>
        <router-link class="btn btn-sec btn-sm" to="/ims/bi/report">报表中心</router-link>
      </div>
    </div>

    <div class="qbar">
      <input v-model="filters.keyword" data-testid="bi-report-keyword" placeholder="名称/编号" style="width: 140px" />
      <select v-model="filters.reportType" data-testid="bi-filter-type" style="width: 110px">
        <option value="">全部类型</option>
        <option value="REPORT">报表</option>
        <option value="DASHBOARD">大屏</option>
      </select>
      <select v-model="filters.shareScope" data-testid="bi-filter-scope" style="width: 120px">
        <option value="">可见范围</option>
        <option value="PRIVATE">私有</option>
        <option value="SPECIFIED">指定人</option>
        <option value="ALL">公开</option>
      </select>
      <select v-model="filters.status" data-testid="bi-filter-status" style="width: 120px">
        <option value="">状态</option>
        <option value="DRAFT">草稿</option>
        <option value="PUBLISHED">已发布</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="button" data-testid="bi-report-search" @click="loadList">查询</button>
      <button class="btn btn-sec btn-sm" type="button" @click="viewMode = viewMode === 'card' ? 'table' : 'card'">
        {{ viewMode === 'card' ? '列表' : '卡片' }}
      </button>
    </div>

    <div style="display: flex; gap: 12px; margin-top: 12px; align-items: flex-start">
      <aside class="card" data-testid="bi-cat-tree" style="width: 230px; padding: 12px; flex: none">
        <div class="rowline" style="justify-content: space-between; margin-bottom: 8px">
          <b style="font-size: 13px">分类</b>
          <button class="btn btn-sec btn-sm" type="button" data-testid="bi-cat-manage" @click="openCatManage">分类管理</button>
        </div>
        <button class="btn btn-sm" type="button" data-testid="bi-cat-all" :class="!filters.category && !filters.subCategory ? 'btn-pri' : 'btn-sec'" style="width: 100%; margin-top: 4px" @click="pickCat('', '')">
          全部
        </button>
        <div v-for="cat in categories" :key="cat.id || cat.name">
          <button
            class="btn btn-sm"
            type="button"
            :data-testid="`bi-cat-${cat.name}`"
            :class="filters.category === cat.name && !filters.subCategory ? 'btn-pri' : 'btn-sec'"
            style="width: 100%; margin-top: 4px; text-align: left"
            @click="pickCat(cat.name, '')"
          >
            {{ cat.name }}
          </button>
          <button
            v-for="child in childNodes(cat)"
            :key="child.id"
            class="btn btn-sm"
            type="button"
            :data-testid="`bi-cat-${child.name}`"
            :class="filters.subCategory === child.name ? 'btn-pri' : 'btn-sec'"
            style="width: calc(100% - 16px); margin: 4px 0 0 16px; text-align: left"
            @click="pickCat(cat.name, child.name)"
          >
            {{ child.name }}
          </button>
        </div>
      </aside>

      <div style="flex: 1; min-width: 0">
        <div class="hint" data-testid="bi-cat-hint" style="margin-bottom: 8px">当前分类：{{ activeCatLabel }} · {{ total }} 条</div>

        <div v-if="viewMode === 'card'" style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px">
          <div v-for="row in rows" :key="row.id" class="card hov">
            <div class="rowline" style="justify-content: space-between">
              <b>{{ row.reportName }}</b>
              <span class="tag tag-info">{{ row.reportType === 'DASHBOARD' ? '大屏' : '报表' }}</span>
            </div>
            <div class="csub" style="margin-top: 6px">{{ row.category }} / {{ row.subCategory || '—' }}</div>
            <div class="csub mono" style="margin-top: 4px">{{ row.reportNo }} · {{ statusLabel(row.status) }} · v{{ row.version || 1 }}</div>
            <div class="csub" style="margin-top: 4px">{{ formatBj(row.updatedAt) }}</div>
            <button class="btn btn-sec btn-sm" type="button" style="margin-top: 10px" @click="openDesigner(row.id)">编辑设计</button>
          </div>
          <div v-if="!loading && !rows.length" class="card" style="grid-column: 1 / -1">
            <div class="empty" data-testid="bi-report-list-empty"><div class="et">{{ emptyText }}</div></div>
          </div>
        </div>

        <div v-else class="tbl-block">
          <div class="tbl-wrap">
            <table>
              <thead>
                <tr>
                  <th>编号</th>
                  <th>名称</th>
                  <th>类型</th>
                  <th>分类</th>
                  <th>状态</th>
                  <th>版本</th>
                  <th>更新</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="loading"><td colspan="8"><div class="empty"><div class="et">加载中</div></div></td></tr>
                <tr v-else-if="!rows.length"><td colspan="8"><div class="empty" data-testid="bi-report-list-empty"><div class="et">{{ emptyText }}</div></div></td></tr>
                <tr v-for="row in rows" v-else :key="row.id">
                  <td class="mono">{{ row.reportNo }}</td>
                  <td>{{ row.reportName }}</td>
                  <td>{{ row.reportType === 'DASHBOARD' ? '大屏' : '报表' }}</td>
                  <td>{{ row.category }}</td>
                  <td>{{ statusLabel(row.status) }}</td>
                  <td>v{{ row.version || 1 }}</td>
                  <td class="csub">{{ formatBj(row.updatedAt) }}</td>
                  <td><button class="btn btn-sec btn-sm" type="button" @click="openDesigner(row.id)">编辑</button></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <div v-if="showForm" class="modal-mask" @click.self="showForm = false">
      <div class="card" style="width: 420px; padding: 20px">
        <h3 style="margin: 0 0 12px">新建报表</h3>
        <label class="fld">报表类型<span style="color: var(--red)">*</span></label>
        <div class="rowline" style="gap: 8px; margin-bottom: 10px">
          <button
            type="button"
            class="btn btn-sm"
            :class="form.reportType === 'REPORT' ? 'btn-pri' : 'btn-sec'"
            @click="form.reportType = 'REPORT'"
          >
            报表
          </button>
          <button
            type="button"
            class="btn btn-sm"
            :class="form.reportType === 'DASHBOARD' ? 'btn-pri' : 'btn-sec'"
            @click="form.reportType = 'DASHBOARD'"
          >
            大屏
          </button>
        </div>
        <p v-if="typeError" class="hint bad">{{ typeError }}</p>
        <label class="fld">报表名称<span style="color: var(--red)">*</span></label>
        <input v-model="form.reportName" class="fld-in" data-testid="bi-new-name" />
        <p v-if="nameError" class="hint bad" data-testid="bi-new-name-error">{{ nameError }}</p>
        <label class="fld">分类</label>
        <select v-model="form.categoryKey" class="fld-in" data-testid="bi-new-category">
          <option v-for="opt in categoryOptions" :key="opt.key" :value="opt.key">{{ opt.label }}</option>
        </select>
        <label class="fld">可见范围</label>
        <select v-model="form.shareScope" class="fld-in" data-testid="bi-new-scope">
          <option value="PRIVATE">私有</option>
          <option value="SPECIFIED">指定人·角色</option>
          <option value="ALL">公开</option>
        </select>
        <label class="fld">指标口径说明</label>
        <textarea v-model="form.metricNote" class="fld-in" rows="3" data-testid="bi-new-note" placeholder="引用已登记指标口径，不自造口径"></textarea>
        <p v-if="formError" class="hint bad">{{ formError }}</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="showForm = false">取消</button>
          <button class="btn btn-pri btn-sm" type="button" data-testid="bi-new-submit" @click="submitCreate">创建并进入设计器</button>
        </div>
      </div>
    </div>

    <div v-if="showCat" class="modal-mask" @click.self="showCat = false">
      <div class="card" style="width: 520px; padding: 20px" data-testid="bi-cat-dialog">
        <h3 style="margin: 0 0 8px">分类管理</h3>
        <p class="hint">报表分类支持两级（如 运营 / 日报）。删除分类后，其下报表移入「未分类」。</p>
        <table style="width: 100%; margin-top: 8px">
          <thead>
            <tr><th style="text-align: left">名称</th><th style="text-align: left">层级</th><th></th></tr>
          </thead>
          <tbody>
            <template v-for="cat in categories" :key="cat.id">
              <tr>
                <td>{{ cat.name }}</td>
                <td>顶级</td>
                <td><button v-if="!cat.protected" class="btn btn-sec btn-sm" type="button" @click="deleteCat(cat.id, cat.name)">删除</button></td>
              </tr>
              <tr v-for="child in childNodes(cat)" :key="child.id">
                <td style="padding-left: 16px">{{ child.name }}</td>
                <td>{{ cat.name }}</td>
                <td><button class="btn btn-sec btn-sm" type="button" @click="deleteCat(child.id, child.name)">删除</button></td>
              </tr>
            </template>
          </tbody>
        </table>
        <label class="fld">名称</label>
        <input v-model="catForm.name" class="fld-in" data-testid="bi-cat-name" placeholder="分类名称" />
        <p v-if="catNameError" class="hint bad" data-testid="bi-cat-name-error">{{ catNameError }}</p>
        <label class="fld">上级</label>
        <select v-model="catForm.parentId" class="fld-in" data-testid="bi-cat-parent">
          <option :value="0">顶级</option>
          <option v-for="cat in categories" :key="cat.id" :value="cat.id">{{ cat.name }}</option>
        </select>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="showCat = false">关闭</button>
          <button class="btn btn-pri btn-sm" type="button" data-testid="bi-cat-add" @click="addCategory">＋ 新增分类</button>
        </div>
      </div>
    </div>

    <div v-if="showImport" class="modal-mask" @click.self="showImport = false">
      <div class="card" style="width: 480px; padding: 20px" data-testid="bi-import-dialog">
        <h3 style="margin: 0 0 12px">导入模板</h3>
        <input data-testid="bi-import-file" type="file" accept=".json,application/json" @change="onImportFile" />
        <p v-if="importError" class="hint bad" data-testid="bi-import-error">{{ importError }}</p>
        <div v-if="importPreview" class="hint" data-testid="bi-import-summary" style="margin-top: 8px">
          <div>文件格式正确</div>
          <div>组件数量 {{ importPreview.componentCount }}</div>
          <div>数据源引用 {{ importPreview.datasetRefs.join('、') || '无' }}</div>
          <div v-for="warn in importPreview.warnings" :key="warn.key">{{ warn.message }}</div>
        </div>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="showImport = false">取消</button>
          <button class="btn btn-pri btn-sm" type="button" data-testid="bi-import-go" :disabled="!importPreview" @click="enterImported">
            导入并进入设计器
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { http } from '../../api/http'

const router = useRouter()

type Row = {
  id: number
  reportNo: string
  reportName: string
  reportType: string
  category: string
  subCategory: string
  status: string
  version?: number
  updatedAt: string
}

type CatChild = { id: number; name: string }
type Cat = { id: number; code: string; name: string; protected?: boolean; children: Array<CatChild | string> }

type ImportPreview = {
  reportId: number
  componentCount: number
  datasetRefs: string[]
  warnings: Array<{ key: string; message: string }>
}

const rows = ref<Row[]>([])
const categories = ref<Cat[]>([])
const loading = ref(false)
const total = ref(0)
const viewMode = ref<'card' | 'table'>('card')
const showForm = ref(false)
const showCat = ref(false)
const showImport = ref(false)
const formError = ref('')
const nameError = ref('')
const typeError = ref('')
const catNameError = ref('')
const importError = ref('')
const importPreview = ref<ImportPreview | null>(null)
const filters = reactive({ keyword: '', reportType: '', category: '', subCategory: '', shareScope: '', status: '' })
const listFiltered = ref(false)
const emptyText = computed(() => (listFiltered.value ? '当前筛选下暂无报表' : '暂无报表，点击新建'))
const form = reactive({
  reportName: '',
  reportType: 'REPORT',
  categoryKey: '内容',
  shareScope: 'PRIVATE',
  metricNote: '',
})
const categoryOptions = computed(() => {
  const options: Array<{ key: string; label: string; category: string; sub: string }> = []
  for (const cat of categories.value) {
    options.push({ key: cat.name, label: cat.name, category: cat.name, sub: '' })
    for (const child of childNodes(cat)) {
      options.push({
        key: `${cat.name}/${child.name}`,
        label: `${cat.name} / ${child.name}`,
        category: cat.name,
        sub: child.name,
      })
    }
  }
  return options
})
const catForm = reactive({ name: '', parentId: 0 })
const activeCatLabel = computed(() => filters.subCategory || filters.category || '全部')

function statusLabel(status: string) {
  if (status === 'PUBLISHED') return '已发布'
  if (status === 'DRAFT') return '草稿'
  return status || '—'
}

function formatBj(raw: string) {
  if (!raw) return '—'
  const date = new Date(raw)
  if (Number.isNaN(date.getTime())) return raw.replace('T', ' ').slice(0, 16)
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  }).formatToParts(date)
  const pick = (type: string) => parts.find((part) => part.type === type)?.value || ''
  return `${pick('year')}-${pick('month')}-${pick('day')} ${pick('hour')}:${pick('minute')}`
}

function childNodes(cat: Cat): CatChild[] {
  return (cat.children || []).map((child, index) =>
    typeof child === 'string' ? { id: index, name: child } : { id: child.id, name: child.name },
  )
}

async function loadCategories() {
  const res = await http.get('/bi/report/categories')
  if (res.data.code === 0) categories.value = res.data.data.categories || []
}

async function loadList() {
  loading.value = true
  try {
    const res = await http.get('/bi/report/list', {
      params: {
        keyword: filters.keyword || undefined,
        reportType: filters.reportType || undefined,
        category: filters.subCategory ? undefined : filters.category || undefined,
        subCategory: filters.subCategory || undefined,
        shareScope: filters.shareScope || undefined,
        status: filters.status || undefined,
        pageNo: 1,
        pageSize: 50,
      },
    })
    if (res.data.code === 0) {
      rows.value = res.data.data.list || []
      total.value = res.data.data.total ?? rows.value.length
      listFiltered.value = Boolean(
        filters.keyword.trim() || filters.reportType || filters.category || filters.subCategory || filters.shareScope || filters.status,
      )
    }
  } finally {
    loading.value = false
  }
}

function pickCat(category: string, subCategory: string) {
  filters.category = category
  filters.subCategory = subCategory
  void loadList()
}

function openCreate() {
  form.reportName = ''
  form.reportType = 'REPORT'
  form.categoryKey = categoryOptions.value[0]?.key || '内容'
  form.shareScope = 'PRIVATE'
  form.metricNote = ''
  formError.value = ''
  nameError.value = ''
  typeError.value = ''
  showForm.value = true
}

async function submitCreate() {
  formError.value = ''
  nameError.value = ''
  typeError.value = ''
  let invalid = false
  if (!form.reportType) {
    typeError.value = '必填项，请填写'
    invalid = true
  }
  if (!form.reportName.trim()) {
    nameError.value = '必填项，请填写'
    invalid = true
  }
  if (invalid) return
  const picked = categoryOptions.value.find((opt) => opt.key === form.categoryKey) || categoryOptions.value[0]
  const res = await http.post('/bi/report', {
    reportName: form.reportName.trim(),
    reportType: form.reportType,
    category: picked?.category || '未分类',
    subCategory: picked?.sub || '',
    shareScope: form.shareScope,
    metricNote: form.metricNote.trim(),
  })
  if (res.data.code !== 0) {
    formError.value = res.data.msg || '保存失败'
    return
  }
  showForm.value = false
  const rid = res.data.data?.id
  if (rid) {
    await router.push({ path: '/ims/bi/report/designer', query: { reportId: String(rid) } })
    return
  }
  await loadList()
}

function openDesigner(id: number) {
  router.push({ path: '/ims/bi/report/designer', query: { reportId: String(id) } })
}

function openCatManage() {
  catForm.name = ''
  catForm.parentId = 0
  catNameError.value = ''
  showCat.value = true
}

async function addCategory() {
  catNameError.value = ''
  if (!catForm.name.trim()) {
    catNameError.value = '必填项，请填写'
    return
  }
  const res = await http.post('/bi/report/category', {
    action: 'add',
    name: catForm.name.trim(),
    parentId: catForm.parentId || 0,
  })
  if (res.data.code !== 0) {
    catNameError.value = res.data.msg || '新增失败'
    return
  }
  categories.value = res.data.data.categories || []
  catForm.name = ''
}

async function deleteCat(id: number, name: string) {
  if (!window.confirm(`删除分类「${name}」？其下报表将移入「未分类」。`)) return
  const res = await http.post('/bi/report/category', { action: 'delete', id })
  if (res.data.code !== 0) {
    catNameError.value = res.data.msg || '删除失败'
    return
  }
  categories.value = res.data.data.categories || []
  if (filters.category === name || filters.subCategory === name) {
    filters.category = '未分类'
    filters.subCategory = ''
  }
  await loadList()
}

function openImport() {
  importError.value = ''
  importPreview.value = null
  showImport.value = true
}

async function onImportFile(event: Event) {
  importError.value = ''
  importPreview.value = null
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  const text = await file.text()
  let template: unknown
  try {
    template = JSON.parse(text)
  } catch {
    importError.value = '文件格式不正确'
    return
  }
  if (!template || typeof template !== 'object' || Array.isArray(template)) {
    importError.value = '文件格式不正确'
    return
  }
  const res = await http.post('/bi/report/import', { template })
  if (res.data.code !== 0) {
    importError.value = res.data.msg || '文件格式不正确'
    return
  }
  importPreview.value = res.data.data
}

async function enterImported() {
  const rid = importPreview.value?.reportId
  if (!rid) return
  showImport.value = false
  await router.push({ path: '/ims/bi/report/designer', query: { reportId: String(rid) } })
}

watch(
  () => [filters.reportType, filters.shareScope, filters.status],
  () => {
    void loadList()
  },
)

onMounted(async () => {
  await loadCategories()
  await loadList()
})
</script>
