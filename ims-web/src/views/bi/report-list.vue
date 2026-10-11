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
        <button class="btn btn-sec btn-sm" type="button" data-testid="bi-import" @click="openImport">导入模板</button>
        <button class="btn btn-pri btn-sm" type="button" @click="openCreate">新建报表</button>
        <router-link class="btn btn-sec btn-sm" to="/ims/bi/report/subscribe">订阅与分享</router-link>
        <router-link class="btn btn-sec btn-sm" to="/ims/bi/report/preview">预览与下钻</router-link>
        <router-link class="btn btn-sec btn-sm" to="/ims/bi/report">报表中心</router-link>
      </div>
    </div>

    <div style="display: grid; grid-template-columns: 220px 1fr; gap: 12px; align-items: start">
      <div class="card" style="padding: 12px">
        <div class="rowline" style="justify-content: space-between">
          <b>分类</b>
          <button class="btn btn-sec btn-sm" type="button" data-testid="bi-cat-manage" @click="openCats">分类管理</button>
        </div>
        <div
          class="csub"
          data-testid="bi-cat-node"
          data-name="全部"
          style="margin-top: 10px; cursor: pointer"
          :style="{ fontWeight: filters.category ? 400 : 700 }"
          @click="selectCat('')"
        >
          全部
        </div>
        <template v-for="node in categories" :key="node.id">
          <div
            data-testid="bi-cat-node"
            :data-name="node.name"
            style="margin-top: 8px; cursor: pointer"
            :style="{ fontWeight: filters.category === node.name ? 700 : 400 }"
            @click="selectCat(node.name)"
          >
            {{ node.name }}
          </div>
          <div
            v-for="child in node.children"
            :key="child.id"
            data-testid="bi-cat-node"
            :data-name="child.name"
            class="csub"
            style="margin: 4px 0 0 14px; cursor: pointer"
            :style="{ fontWeight: filters.category === child.name ? 700 : 400 }"
            @click="selectCat(child.name)"
          >
            {{ child.name }}
          </div>
        </template>
        <p class="csub" data-testid="bi-cat-hint" style="margin-top: 12px">当前分类：{{ filters.category || '全部' }} · {{ total }}</p>
      </div>

      <div>
        <div class="qbar">
          <input v-model="filters.keyword" data-testid="bi-report-keyword" placeholder="名称/编号" style="width: 140px" />
          <select v-model="filters.reportType" data-testid="bi-filter-type" style="width: 110px">
            <option value="">全部类型</option>
            <option value="REPORT">报表</option>
            <option value="DASHBOARD">大屏</option>
          </select>
          <select v-model="filters.shareScope" data-testid="bi-filter-scope" style="width: 120px">
            <option value="">全部可见范围</option>
            <option value="PRIVATE">私有</option>
            <option value="SPECIFIED">指定人</option>
            <option value="ALL">公开</option>
          </select>
          <select v-model="filters.status" data-testid="bi-filter-status" style="width: 110px">
            <option value="">全部状态</option>
            <option value="DRAFT">草稿</option>
            <option value="PUBLISHED">已发布</option>
          </select>
          <span class="sp"></span>
          <button class="btn btn-pri btn-sm" type="button" data-testid="bi-report-search" @click="loadList">查询</button>
          <button class="btn btn-sec btn-sm" type="button" @click="viewMode = viewMode === 'card' ? 'table' : 'card'">
            {{ viewMode === 'card' ? '列表' : '卡片' }}
          </button>
        </div>

        <div v-if="viewMode === 'card'" style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-top: 12px">
          <div v-for="row in rows" :key="row.id" class="card hov">
            <div class="rowline" style="justify-content: space-between">
              <b>{{ row.reportName }}</b>
              <span class="tag tag-info">{{ row.reportType === 'DASHBOARD' ? '大屏' : '报表' }}</span>
            </div>
            <div class="csub" style="margin-top: 6px">{{ row.category }} / {{ row.subCategory || '—' }}</div>
            <div class="csub mono" style="margin-top: 4px">{{ row.reportNo }} · {{ row.status }}</div>
            <button class="btn btn-sec btn-sm" type="button" style="margin-top: 10px" @click="openDesigner(row.id)">编辑设计</button>
          </div>
          <div v-if="!loading && !rows.length" class="card" style="grid-column: 1 / -1">
            <div class="empty" data-testid="bi-report-list-empty"><div class="et">{{ emptyText }}</div></div>
          </div>
        </div>

        <div v-else class="tbl-block" style="margin-top: 12px">
          <div class="tbl-wrap">
            <table>
              <thead>
                <tr>
                  <th>编号</th>
                  <th>名称</th>
                  <th>类型</th>
                  <th>分类</th>
                  <th>状态</th>
                  <th>更新</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="loading"><td colspan="7"><div class="empty"><div class="et">加载中</div></div></td></tr>
                <tr v-else-if="!rows.length"><td colspan="7"><div class="empty" data-testid="bi-report-list-empty"><div class="et">{{ emptyText }}</div></div></td></tr>
                <tr v-for="row in rows" v-else :key="row.id">
                  <td class="mono">{{ row.reportNo }}</td>
                  <td>{{ row.reportName }}</td>
                  <td>{{ row.reportType === 'DASHBOARD' ? '大屏' : '报表' }}</td>
                  <td>{{ row.category }}</td>
                  <td>{{ row.status }}</td>
                  <td class="csub">{{ row.updatedAt }}</td>
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
        <label class="fld">报表类型<i class="req">*</i></label>
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
        <p v-if="fieldErrors.reportType" class="hint" data-testid="bi-new-type-error" style="color: var(--red)">{{ fieldErrors.reportType }}</p>
        <label class="fld">报表名称<i class="req">*</i></label>
        <input v-model="form.reportName" class="fld-in" data-testid="bi-new-name" />
        <p v-if="fieldErrors.reportName" class="hint" data-testid="bi-new-name-error" style="color: var(--red)">{{ fieldErrors.reportName }}</p>
        <label class="fld">分类</label>
        <select v-model="form.category" class="fld-in" data-testid="bi-new-category">
          <option v-for="name in flatNames" :key="name" :value="name">{{ name }}</option>
        </select>
        <label class="fld">可见范围</label>
        <select v-model="form.shareScope" class="fld-in" data-testid="bi-new-scope">
          <option value="PRIVATE">私有</option>
          <option value="SPECIFIED">指定人</option>
          <option value="ALL">公开</option>
        </select>
        <label class="fld">指标口径说明</label>
        <textarea v-model="form.metricNote" class="fld-in" data-testid="bi-new-note" rows="3" />
        <p v-if="formError" class="hint" style="color: var(--red)">{{ formError }}</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="showForm = false">取消</button>
          <button class="btn btn-pri btn-sm" type="button" data-testid="bi-new-submit" @click="submitCreate">创建并进入设计器</button>
        </div>
      </div>
    </div>

    <div v-if="showCats" class="modal-mask" data-testid="bi-cat-dialog" @click.self="showCats = false">
      <div class="card" style="width: 560px; padding: 20px">
        <h3 style="margin: 0 0 12px">分类管理</h3>
        <label class="fld">分类名称</label>
        <input v-model="catForm.name" class="fld-in" data-testid="bi-cat-name" placeholder="请填写分类名称" />
        <label class="fld">上级</label>
        <select v-model.number="catForm.parentId" class="fld-in" data-testid="bi-cat-parent">
          <option :value="0">顶级</option>
          <option v-for="node in categories" :key="node.id" :value="node.id">{{ node.name }}</option>
        </select>
        <p v-if="catError" class="hint" data-testid="bi-cat-error" style="color: var(--red)">{{ catError }}</p>
        <p v-if="catMsg" class="hint" data-testid="bi-cat-msg">{{ catMsg }}</p>
        <div class="acts" style="margin: 8px 0 12px">
          <button class="btn btn-pri btn-sm" type="button" data-testid="bi-cat-add" @click="addCategory">＋ 新增分类</button>
        </div>
        <table>
          <tbody>
            <tr v-for="node in flatNodes" :key="node.id">
              <td>{{ node.level === 2 ? '└ ' : '' }}{{ node.name }}</td>
              <td class="csub">{{ node.level === 1 ? '顶级' : '二级' }}</td>
              <td>
                <button
                  v-if="node.name !== '未分类'"
                  class="btn btn-sec btn-sm"
                  type="button"
                  data-testid="bi-cat-delete"
                  @click="removeCategory(node.id)"
                >
                  删除
                </button>
              </td>
            </tr>
          </tbody>
        </table>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="showCats = false">关闭</button>
        </div>
      </div>
    </div>

    <div v-if="showImport" class="modal-mask" data-testid="bi-import-dialog" @click.self="showImport = false">
      <div class="card" style="width: 560px; padding: 20px">
        <h3 style="margin: 0 0 12px">导入模板</h3>
        <input data-testid="bi-import-file" type="file" accept=".json,application/json" @change="onImportFile" />
        <p v-if="importError" class="hint" data-testid="bi-import-error" style="color: var(--red)">{{ importError }}</p>
        <p v-if="importPreview" class="csub" data-testid="bi-import-summary">
          文件格式正确 · 组件数量 {{ importPreview.compCount }} · 数据源引用 {{ importPreview.dsCount }}
        </p>
        <p v-for="(warn, idx) in importWarnings" :key="idx" class="hint">{{ warn }}</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="showImport = false">取消</button>
          <button class="btn btn-pri btn-sm" type="button" data-testid="bi-import-submit" @click="submitImport">导入并进入设计器</button>
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
  shareScope?: string
  updatedAt: string
}

type CatNode = { id: number; name: string; system?: boolean; children: CatNode[] }

const rows = ref<Row[]>([])
const categories = ref<CatNode[]>([])
const total = ref(0)
const loading = ref(false)
const viewMode = ref<'card' | 'table'>('card')
const showForm = ref(false)
const formError = ref('')
const fieldErrors = reactive({ reportName: '', reportType: '' })
const filters = reactive({ keyword: '', reportType: '', category: '', shareScope: '', status: '' })
const listFiltered = ref(false)
const emptyText = computed(() => (listFiltered.value ? '当前筛选下暂无报表' : '暂无报表，点击新建'))
const form = reactive({ reportName: '', reportType: 'REPORT', category: '未分类', shareScope: 'PRIVATE', metricNote: '' })
const showCats = ref(false)
const catError = ref('')
const catMsg = ref('')
const catForm = reactive({ name: '', parentId: 0 })
const showImport = ref(false)
const importError = ref('')
const importTemplate = ref<Record<string, unknown> | null>(null)
const importPreview = ref<{ compCount: number; dsCount: number } | null>(null)
const importWarnings = ref<string[]>([])

const flatNames = computed(() => {
  const names: string[] = []
  for (const node of categories.value) {
    names.push(node.name)
    for (const child of node.children || []) names.push(child.name)
  }
  return names
})

const flatNodes = computed(() => {
  const list: { id: number; name: string; level: number }[] = []
  for (const node of categories.value) {
    list.push({ id: node.id, name: node.name, level: 1 })
    for (const child of node.children || []) list.push({ id: child.id, name: child.name, level: 2 })
  }
  return list
})

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
        category: filters.category || undefined,
        shareScope: filters.shareScope || undefined,
        status: filters.status || undefined,
        pageNo: 1,
        pageSize: 50,
      },
    })
    if (res.data.code === 0) {
      rows.value = res.data.data.list || []
      total.value = Number(res.data.data.total ?? rows.value.length)
      listFiltered.value = Boolean(
        filters.keyword.trim() || filters.reportType || filters.category || filters.shareScope || filters.status,
      )
    }
  } finally {
    loading.value = false
  }
}

function selectCat(name: string) {
  filters.category = name
}

function openCreate() {
  form.reportName = ''
  form.reportType = 'REPORT'
  form.category = flatNames.value.includes('未分类') ? '未分类' : flatNames.value[0] || '未分类'
  form.shareScope = 'PRIVATE'
  form.metricNote = ''
  formError.value = ''
  fieldErrors.reportName = ''
  fieldErrors.reportType = ''
  showForm.value = true
}

async function submitCreate() {
  formError.value = ''
  fieldErrors.reportName = form.reportName.trim() ? '' : '必填项，请填写'
  fieldErrors.reportType = form.reportType ? '' : '必填项，请填写'
  if (fieldErrors.reportName || fieldErrors.reportType) return
  let res
  try {
    res = await http.post('/bi/report', {
      reportName: form.reportName.trim(),
      reportType: form.reportType,
      category: form.category,
      shareScope: form.shareScope,
      metricNote: form.metricNote.trim(),
    })
  } catch (err) {
    const body = err as { msg?: string }
    formError.value = body.msg || '保存失败'
    return
  }
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

function openCats() {
  catForm.name = ''
  catForm.parentId = 0
  catError.value = ''
  catMsg.value = ''
  showCats.value = true
}

async function addCategory() {
  catError.value = ''
  catMsg.value = ''
  if (!catForm.name.trim()) {
    catError.value = '请填写分类名称'
    return
  }
  try {
    await http.post('/bi/report/category', {
      action: 'add',
      name: catForm.name.trim(),
      parentId: catForm.parentId || 0,
    })
    catForm.name = ''
    catMsg.value = '分类已新增'
    await loadCategories()
  } catch (err) {
    const body = err as { msg?: string }
    catError.value = body.msg || '新增失败'
  }
}

async function removeCategory(id: number) {
  catError.value = ''
  try {
    const res = await http.post('/bi/report/category', { action: 'delete', categoryId: id })
    catMsg.value = res.data.data?.message || '其下报表已移入「未分类」'
    await loadCategories()
    await loadList()
  } catch (err) {
    const body = err as { msg?: string }
    catError.value = body.msg || '删除失败'
  }
}

function openImport() {
  importError.value = ''
  importTemplate.value = null
  importPreview.value = null
  importWarnings.value = []
  showImport.value = true
}

async function onImportFile(event: Event) {
  importError.value = ''
  importPreview.value = null
  importWarnings.value = []
  importTemplate.value = null
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  if (!file.name.toLowerCase().endsWith('.json')) {
    importError.value = '文件格式不正确'
    return
  }
  let parsed: unknown
  try {
    parsed = JSON.parse(await file.text())
  } catch {
    importError.value = '文件格式不正确'
    return
  }
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    importError.value = '文件格式不正确'
    return
  }
  const template = parsed as Record<string, unknown>
  const comps = (template.comps || template.components || []) as unknown[]
  const datasets = new Set(
    (Array.isArray(comps) ? comps : [])
      .map((item) => (item && typeof item === 'object' ? String((item as { dataset?: string }).dataset || '') : ''))
      .filter(Boolean),
  )
  importTemplate.value = template
  importPreview.value = { compCount: Array.isArray(comps) ? comps.length : 0, dsCount: datasets.size }
}

async function submitImport() {
  importError.value = ''
  if (!importTemplate.value) {
    importError.value = '文件格式不正确'
    return
  }
  try {
    const res = await http.post('/bi/report/import', { template: importTemplate.value })
    importWarnings.value = (res.data.data.warnings || []).map((item: { message?: string }) => item.message || '')
    const rid = res.data.data.reportId || res.data.data.id
    showImport.value = false
    if (rid) {
      await router.push({ path: '/ims/bi/report/designer', query: { reportId: String(rid) } })
    }
  } catch (err) {
    const body = err as { msg?: string }
    importError.value = body.msg || '文件格式不正确'
  }
}

watch(
  () => [filters.reportType, filters.shareScope, filters.status, filters.category],
  () => {
    void loadList()
  },
)

onMounted(async () => {
  await loadCategories()
  await loadList()
})
</script>
