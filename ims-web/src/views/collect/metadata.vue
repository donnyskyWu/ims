<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>元数据维护</h1>
        <div class="sub">UX-M8 §4 · BI0 只读消费 entity/{code}/fields · 16 COLLECT</div>
      </div>
      <div class="acts">
        <button class="btn btn-pri btn-sm" type="button" @click="openCreate">新建实体</button>
      </div>
    </div>
    <p class="hint" style="margin-bottom: 10px">自定义查询须先在此映射实体与字段；页内不含 BI0 QueryBuilder。</p>
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
            <tr v-if="!rows.length && !loading">
              <td colspan="6"><div class="empty"><div class="et">{{ error || '暂无元数据实体' }}</div></div></td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.id">
              <td class="mono">{{ row.entityCode }}</td>
              <td>{{ row.entityName }}</td>
              <td class="mono">{{ row.tableName }}</td>
              <td class="num">{{ row.fieldCount }}</td>
              <td>{{ row.status }}</td>
              <td>
                <button class="btn-txt btn" type="button" @click="openFields(row)">字段配置</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    <div v-if="createOpen" class="drawer-mask" @click.self="createOpen = false">
      <div class="drawer">
        <h3>新建实体</h3>
        <div class="formrow">
          <label>未映射表</label>
          <select v-model="createForm.tableName" @change="onTablePick">
            <option value="">请选择</option>
            <option v-for="t in unmapped" :key="t.tableName" :value="t.tableName">
              {{ t.tableName }} ({{ t.tableComment }})
            </option>
          </select>
        </div>
        <div class="formrow">
          <label>实体编码</label>
          <input v-model="createForm.entityCode" class="mono" />
        </div>
        <div class="formrow">
          <label>实体名称</label>
          <input v-model="createForm.entityName" />
        </div>
        <p v-if="formMsg" class="hint">{{ formMsg }}</p>
        <div class="drawer-acts">
          <button class="btn btn-sec btn-sm" type="button" @click="createOpen = false">取消</button>
          <button class="btn btn-pri btn-sm" type="button" @click="createEntity">创建</button>
        </div>
      </div>
    </div>
    <div v-if="fieldOpen" class="drawer-mask" @click.self="fieldOpen = false">
      <div class="drawer wide">
        <h3>字段配置 · {{ activeEntity?.entityCode }}</h3>
        <div v-for="(f, idx) in fieldRows" :key="idx" class="formrow one">
          <input v-model="f.columnName" placeholder="列名" class="mono" style="width: 120px" />
          <input v-model="f.fieldCode" placeholder="fieldCode" class="mono" style="width: 120px" />
          <input v-model="f.displayName" placeholder="显示名" style="width: 100px" />
          <select v-model="f.queryConditionType" style="width: 90px">
            <option value="EQ">EQ</option>
            <option value="LIKE">LIKE</option>
            <option value="RANGE">RANGE</option>
          </select>
        </div>
        <button class="btn btn-sec btn-sm" type="button" @click="addFieldRow">+ 字段</button>
        <div class="drawer-acts">
          <button class="btn btn-sec btn-sm" type="button" @click="fieldOpen = false">关闭</button>
          <button class="btn btn-pri btn-sm" type="button" @click="saveFields">保存字段</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { http } from '../../api/http'

type EntityRow = {
  id: string
  entityCode: string
  entityName: string
  tableName: string
  fieldCount: number
  status: string
}

const rows = ref<EntityRow[]>([])
const unmapped = ref<{ tableName: string; tableComment: string; suggestedEntityCode: string; suggestedEntityName: string }[]>([])
const loading = ref(false)
const error = ref('')
const createOpen = ref(false)
const fieldOpen = ref(false)
const formMsg = ref('')
const activeEntity = ref<EntityRow | null>(null)
const fieldRows = ref<{ fieldCode: string; columnName: string; displayName: string; queryConditionType: string }[]>([])
const createForm = reactive({ entityCode: '', entityName: '', tableName: '', status: 'ENABLED' })

async function loadList() {
  loading.value = true
  try {
    const res = await http.get('/collect/metadata/list', { params: { pageNo: 1, pageSize: 50 } })
    rows.value = res.data.data.list || []
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

async function loadUnmapped() {
  const res = await http.get('/collect/metadata/unmapped-tables')
  unmapped.value = res.data.data.list || []
}

function openCreate() {
  formMsg.value = ''
  createForm.entityCode = ''
  createForm.entityName = ''
  createForm.tableName = ''
  loadUnmapped()
  createOpen.value = true
}

function onTablePick() {
  const t = unmapped.value.find((x) => x.tableName === createForm.tableName)
  if (t) {
    createForm.entityCode = t.suggestedEntityCode
    createForm.entityName = t.suggestedEntityName
  }
}

async function createEntity() {
  formMsg.value = ''
  try {
    await http.post('/collect/metadata/create', createForm)
    createOpen.value = false
    await loadList()
  } catch (e) {
    formMsg.value = e instanceof Error ? e.message : '创建失败'
  }
}

async function openFields(row: EntityRow) {
  activeEntity.value = row
  const detail = await http.get(`/collect/metadata/${row.id}`)
  const fields = detail.data.data.fields || []
  fieldRows.value = fields.length
    ? fields.map((f: Record<string, string>) => ({
        fieldCode: f.fieldCode,
        columnName: f.columnName,
        displayName: f.displayName,
        queryConditionType: f.queryConditionType || 'EQ',
      }))
    : [{ fieldCode: '', columnName: '', displayName: '', queryConditionType: 'EQ' }]
  fieldOpen.value = true
}

function addFieldRow() {
  fieldRows.value.push({ fieldCode: '', columnName: '', displayName: '', queryConditionType: 'EQ' })
}

async function saveFields() {
  if (!activeEntity.value) return
  await http.put(`/collect/metadata/${activeEntity.value.id}/fields`, {
    fields: fieldRows.value.map((f, i) => ({
      ...f,
      dataType: 'STRING',
      sortOrder: i,
    })),
  })
  fieldOpen.value = false
  await loadList()
}

onMounted(loadList)
</script>

<style scoped>
.drawer.wide {
  max-width: 640px;
}
</style>
