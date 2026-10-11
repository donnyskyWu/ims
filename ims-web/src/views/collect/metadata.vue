<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>元数据维护</h1>
        <div class="sub">UX-M8 §4 · COLLECT P4m · BI0 只读消费 entity/{code}/fields</div>
      </div>
      <div class="acts">
        <button class="btn btn-pri btn-sm" type="button" data-testid="metadata-create-btn" @click="openCreate">
          新建实体
        </button>
      </div>
    </div>
    <p class="hint" style="margin-bottom: 10px">
      自定义查询须先在此映射 IMS 库物理表与字段。
      <button class="btn btn-txt btn-sm" type="button" @click="goBiQuery">前往自定义查询 →</button>
    </p>
    <div class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>实体编码</th>
              <th>实体名称</th>
              <th>物理表</th>
              <th>字段数</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="6"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!rows.length">
              <td colspan="6"><div class="empty"><div class="et">{{ error || '暂无元数据实体' }}</div></div></td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.id" data-testid="metadata-entity-row">
              <td class="mono">{{ row.entityCode }}</td>
              <td>{{ row.entityName }}</td>
              <td class="mono">{{ row.tableName }}</td>
              <td class="num">{{ row.fieldCount }}</td>
              <td>{{ statusLabel(row.status) }}</td>
              <td>
                <button class="btn-txt btn" type="button" @click="openEdit(row)">编辑</button>
                <button class="btn-txt btn" type="button" @click="openFields(row)">字段配置</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <ProtoDrawer :open="createOpen" title="新建实体" width="920px" @close="createOpen = false">
      <div class="metadata-drawer-body">
        <div class="metadata-form-grid">
          <label class="fld wide">
            <span>未映射物理表 <em class="req">*</em></span>
            <select v-model="createForm.tableName" data-testid="metadata-create-table" @change="onCreateTablePick">
              <option value="">请选择 IMS 库表</option>
              <option v-for="t in unmapped" :key="t.tableName" :value="t.tableName">
                {{ tableOptionLabel(t) }}
              </option>
            </select>
          </label>
          <label class="fld">
            <span>实体编码 <em class="req">*</em></span>
            <input v-model="createForm.entityCode" class="mono" placeholder="如 SYS_USER" />
          </label>
          <label class="fld">
            <span>实体名称 <em class="req">*</em></span>
            <input v-model="createForm.entityName" placeholder="中文名称" />
          </label>
          <label class="fld">
            <span>状态</span>
            <select v-model="createForm.status">
              <option value="ENABLED">启用</option>
              <option value="DISABLED">停用</option>
            </select>
          </label>
        </div>
        <template v-if="createForm.tableName">
          <div class="dsec field-map-sec">
            <div class="field-map-sec-h">
              <div>
                <b>字段映射</b>
                <p class="hint field-map-hint">选表后自动加载列；勾选参与 BI 查询的字段</p>
              </div>
              <button
                class="btn btn-sec btn-sm"
                type="button"
                :disabled="columnsLoading"
                @click="reloadCreateColumns"
              >
                {{ columnsLoading ? '加载中…' : '重新加载列' }}
              </button>
            </div>
            <FieldMappingTable v-model="createFieldRows" show-include :lock-column="true" />
          </div>
        </template>
        <p v-if="formMsg" class="hint bad">{{ formMsg }}</p>
      </div>
      <template #footer>
        <button class="btn btn-sec" type="button" @click="createOpen = false">取消</button>
        <button class="btn btn-pri" type="button" data-testid="metadata-create-submit" :disabled="saving" @click="createEntity">
          创建
        </button>
      </template>
    </ProtoDrawer>

    <ProtoDrawer :open="editOpen" title="编辑实体" width="480px" @close="editOpen = false">
      <div class="metadata-drawer-body">
        <p class="hint mono">{{ editForm.entityCode }} · {{ editForm.tableName }}</p>
        <div class="metadata-form-grid metadata-form-grid--single">
          <label class="fld wide">
            <span>实体名称</span>
            <input v-model="editForm.entityName" />
          </label>
          <label class="fld wide">
            <span>状态</span>
            <select v-model="editForm.status">
              <option value="ENABLED">启用</option>
              <option value="DISABLED">停用</option>
            </select>
          </label>
        </div>
        <p v-if="formMsg" class="hint bad">{{ formMsg }}</p>
      </div>
      <template #footer>
        <button class="btn btn-sec" type="button" @click="editOpen = false">取消</button>
        <button class="btn btn-pri" type="button" :disabled="saving" @click="saveEdit">保存</button>
      </template>
    </ProtoDrawer>

    <ProtoDrawer
      :open="fieldOpen"
      :title="`字段配置 · ${activeEntity?.entityCode || ''}`"
      width="920px"
      @close="fieldOpen = false"
    >
      <div class="metadata-drawer-body">
        <p class="hint" style="margin-bottom: 8px">
          物理表 <span class="mono">{{ activeEntity?.tableName }}</span>
          · 查询条件类型对齐字典 dict_metadata_query_condition_type
        </p>
        <div class="field-map-sec-h" style="margin-bottom: 10px">
          <button class="btn btn-sec btn-sm" type="button" :disabled="columnsLoading" @click="reloadFieldColumns">
            {{ columnsLoading ? '加载中…' : '从物理表加载列' }}
          </button>
          <button class="btn btn-sec btn-sm" type="button" @click="addFieldRow">+ 手工添加</button>
        </div>
        <FieldMappingTable v-model="fieldRows" :lock-column="false" />
        <p v-if="formMsg" class="hint bad">{{ formMsg }}</p>
      </div>
      <template #footer>
        <button class="btn btn-sec" type="button" @click="fieldOpen = false">关闭</button>
        <button class="btn btn-pri" type="button" :disabled="saving" @click="saveFields">保存字段</button>
      </template>
    </ProtoDrawer>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { errorMessage, http } from '../../api/http'
import ProtoDrawer from '../../components/ProtoDrawer.vue'
import FieldMappingTable from './metadata/FieldMappingTable.vue'
import type { FieldRow, TableColumn } from './metadata/types'

type EntityRow = {
  id: string
  entityCode: string
  entityName: string
  tableName: string
  fieldCount: number
  status: string
}

const SKIP_COLUMNS = new Set(['id', 'tenant_id', 'deleted'])

const router = useRouter()
const rows = ref<EntityRow[]>([])
const unmapped = ref<
  { tableName: string; tableComment: string; suggestedEntityCode: string; suggestedEntityName: string }[]
>([])
const loading = ref(false)
const saving = ref(false)
const columnsLoading = ref(false)
const error = ref('')
const formMsg = ref('')
const createOpen = ref(false)
const editOpen = ref(false)
const fieldOpen = ref(false)
const activeEntity = ref<EntityRow | null>(null)
const fieldRows = ref<FieldRow[]>([])
const createFieldRows = ref<FieldRow[]>([])
const createForm = reactive({ entityCode: '', entityName: '', tableName: '', status: 'ENABLED' })
const editForm = reactive({ id: '', entityCode: '', entityName: '', tableName: '', status: 'ENABLED' })

function statusLabel(status: string) {
  return status === 'DISABLED' ? '停用' : '启用'
}

function tableOptionLabel(t: { tableName: string; tableComment: string }) {
  const comment = (t.tableComment || '').trim()
  return comment ? `${t.tableName}（${comment}）` : t.tableName
}

function inferDataType(sqlType: string): string {
  const t = sqlType.toUpperCase()
  if (t.includes('INT') || t.includes('DECIMAL') || t.includes('FLOAT') || t.includes('NUMERIC')) return 'NUMBER'
  if (t.includes('DATE') || t.includes('TIME')) return 'DATETIME'
  if (t.includes('BOOL') || t.includes('TINYINT(1)')) return 'BOOLEAN'
  return 'STRING'
}

function inferQueryType(col: TableColumn): string {
  const name = col.columnName.toLowerCase()
  if (name.endsWith('_at') || name.includes('date')) return 'RANGE'
  if (name.includes('name') || name.includes('title') || name.includes('no')) return 'LIKE'
  return 'EQ'
}

function columnsToFieldRows(cols: TableColumn[], existing: FieldRow[] = []): FieldRow[] {
  const byCol = new Map(existing.map((f) => [f.columnName, f]))
  return cols.map((col) => {
    const prev = byCol.get(col.columnName)
    if (prev) {
      return { ...prev, dataType: prev.dataType || inferDataType(col.dataType) }
    }
    const code = col.columnName
    return {
      included: !SKIP_COLUMNS.has(code),
      fieldCode: code,
      columnName: code,
      displayName: code,
      dataType: inferDataType(col.dataType),
      queryConditionType: inferQueryType(col),
      dictType: '',
    }
  })
}

async function fetchTableColumns(tableName: string): Promise<TableColumn[]> {
  const res = await http.get('/collect/metadata/table-columns', { params: { tableName } })
  return res.data.data.list || []
}

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const res = await http.get('/collect/metadata/list', { params: { pageNo: 1, pageSize: 100 } })
    rows.value = res.data.data.list || []
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}

async function loadUnmapped() {
  const res = await http.get('/collect/metadata/unmapped-tables')
  unmapped.value = res.data.data.list || []
}

function goBiQuery() {
  router.push('/ims/bi/query')
}

function openCreate() {
  formMsg.value = ''
  createForm.entityCode = ''
  createForm.entityName = ''
  createForm.tableName = ''
  createForm.status = 'ENABLED'
  createFieldRows.value = []
  loadUnmapped()
  createOpen.value = true
}

async function onCreateTablePick() {
  const t = unmapped.value.find((x) => x.tableName === createForm.tableName)
  if (t) {
    createForm.entityCode = t.suggestedEntityCode
    createForm.entityName = t.suggestedEntityName
  }
  await reloadCreateColumns()
}

async function reloadCreateColumns() {
  if (!createForm.tableName) return
  columnsLoading.value = true
  try {
    const cols = await fetchTableColumns(createForm.tableName)
    createFieldRows.value = columnsToFieldRows(cols, createFieldRows.value)
  } catch (e) {
    formMsg.value = errorMessage(e)
  } finally {
    columnsLoading.value = false
  }
}

function fieldPayload(list: FieldRow[]) {
  return list
    .filter((f) => f.fieldCode.trim() && f.columnName.trim())
    .map((f, i) => ({
      fieldCode: f.fieldCode.trim(),
      columnName: f.columnName.trim(),
      displayName: f.displayName.trim() || f.fieldCode.trim(),
      dataType: f.dataType || 'STRING',
      queryConditionType: f.queryConditionType || 'EQ',
      dictType: f.dictType.trim(),
      sortOrder: i,
    }))
}

async function createEntity() {
  formMsg.value = ''
  if (!createForm.tableName.trim() || !createForm.entityCode.trim() || !createForm.entityName.trim()) {
    formMsg.value = '必填项，请填写'
    return
  }
  saving.value = true
  try {
    const res = await http.post('/collect/metadata/create', createForm)
    const entityId = res.data.data.id as string
    const mapped = createFieldRows.value.filter((f) => f.included)
    const fields = fieldPayload(mapped.length ? mapped : createFieldRows.value)
    if (fields.length) {
      await http.put(`/collect/metadata/${entityId}/fields`, { fields })
    }
    createOpen.value = false
    await loadList()
  } catch (e) {
    formMsg.value = errorMessage(e)
  } finally {
    saving.value = false
  }
}

function openEdit(row: EntityRow) {
  formMsg.value = ''
  editForm.id = row.id
  editForm.entityCode = row.entityCode
  editForm.entityName = row.entityName
  editForm.tableName = row.tableName
  editForm.status = row.status
  editOpen.value = true
}

async function saveEdit() {
  formMsg.value = ''
  saving.value = true
  try {
    await http.put(`/collect/metadata/${editForm.id}`, {
      entityName: editForm.entityName,
      status: editForm.status,
    })
    editOpen.value = false
    await loadList()
  } catch (e) {
    formMsg.value = errorMessage(e)
  } finally {
    saving.value = false
  }
}

async function openFields(row: EntityRow) {
  formMsg.value = ''
  activeEntity.value = row
  const detail = await http.get(`/collect/metadata/${row.id}`)
  const fields = detail.data.data.fields || []
  fieldRows.value = fields.length
    ? fields.map((f: Record<string, string>) => ({
        included: true,
        fieldCode: f.fieldCode,
        columnName: f.columnName,
        displayName: f.displayName,
        dataType: f.dataType || 'STRING',
        queryConditionType: f.queryConditionType || 'EQ',
        dictType: f.dictType || '',
      }))
    : []
  fieldOpen.value = true
  if (!fieldRows.value.length) {
    await reloadFieldColumns()
  }
}

async function reloadFieldColumns() {
  if (!activeEntity.value?.tableName) return
  columnsLoading.value = true
  try {
    const cols = await fetchTableColumns(activeEntity.value.tableName)
    fieldRows.value = columnsToFieldRows(cols, fieldRows.value)
  } catch (e) {
    formMsg.value = errorMessage(e)
  } finally {
    columnsLoading.value = false
  }
}

function addFieldRow() {
  fieldRows.value.push({
    included: true,
    fieldCode: '',
    columnName: '',
    displayName: '',
    dataType: 'STRING',
    queryConditionType: 'EQ',
    dictType: '',
  })
}

async function saveFields() {
  if (!activeEntity.value) return
  formMsg.value = ''
  saving.value = true
  try {
    const fields = fieldPayload(fieldRows.value)
    if (!fields.length) {
      formMsg.value = '请至少配置一个有效字段'
      return
    }
    await http.put(`/collect/metadata/${activeEntity.value.id}/fields`, { fields })
    fieldOpen.value = false
    await loadList()
  } catch (e) {
    formMsg.value = errorMessage(e)
  } finally {
    saving.value = false
  }
}

onMounted(loadList)
</script>

<style scoped>
.metadata-drawer-body {
  padding-bottom: 4px;
}
.metadata-form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px 16px;
  margin-bottom: 4px;
}
.metadata-form-grid--single {
  grid-template-columns: 1fr;
}
.metadata-form-grid .fld.wide {
  grid-column: 1 / -1;
}
.field-map-sec {
  margin-top: 4px;
}
.field-map-sec-h {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
}
.field-map-hint {
  margin: 4px 0 0;
  font-size: 12px;
}
.hint.bad {
  color: var(--danger, #c0392b);
  margin-top: 10px;
}
</style>
