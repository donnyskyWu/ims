<template>
  <div class="page page-bi0-query">
    <div class="pg-h">
      <div>
        <h1>自定义查询</h1>
        <div class="sub">FR-M6-005 · 只读消费 COLLECT 元数据 · /ims/bi/query</div>
      </div>
      <div class="acts">
        <button class="btn btn-sec btn-sm" type="button" @click="goMetadata">元数据维护</button>
      </div>
    </div>
    <div class="tabs">
      <div class="tab" :class="{ on: tab === 'builder' }" @click="tab = 'builder'">自定义查询</div>
      <div class="tab" :class="{ on: tab === 'mine' }" @click="switchMine">我的查询</div>
    </div>

    <template v-if="tab === 'builder'">
      <div class="card bi0-config-card">
        <div class="bi0-config-hd">
          <div class="collapse-h"><span class="caret">▼</span><h3>查询配置</h3></div>
          <div class="rowline">
            <button class="btn btn-pri btn-sm" type="button" :disabled="running" @click="runAdhoc">执行查询</button>
            <button class="btn btn-sec btn-sm" type="button" @click="saveDraft">保存为我的查询</button>
          </div>
        </div>
        <div class="bi0-config-body">
          <div class="bi0-qb-root qb-layout">
            <div class="qb-form">
              <div class="qb-row">
                <label>数据源</label>
                <select v-model="builder.entityCode" style="width: 280px" @change="loadFields">
                  <option value="">请选择已映射实体</option>
                  <option v-for="e in entities" :key="e.entityCode" :value="e.entityCode">
                    {{ e.entityName }}（{{ e.entityCode }}）
                  </option>
                </select>
              </div>
              <div v-if="fieldHint" class="hint">{{ fieldHint }}</div>
              <div class="qb-row">
                <label>展示字段</label>
                <div class="qb-chips">
                  <label v-for="f in fields" :key="f.fieldCode" class="chip" style="cursor: pointer">
                    <input v-model="builder.selectFields" type="checkbox" :value="f.fieldCode" />
                    {{ f.displayName }} ({{ f.fieldCode }})
                  </label>
                </div>
              </div>
              <div class="qb-row">
                <label>行数上限</label>
                <input v-model.number="builder.limit" type="number" min="1" max="1000" style="width: 100px" />
              </div>
              <div class="qb-cond-hd"><b>SQL 预览</b></div>
              <textarea class="code-edit" readonly rows="4" :value="previewSql" />
            </div>
            <div class="qb-side">
              <div class="qb-side-hd">可选字段（只读 · entity/fields）</div>
              <div v-for="f in fields" :key="'s' + f.fieldCode" class="fi mono">{{ f.displayName }}</div>
              <p v-if="!fields.length" class="hint">先选数据源；未映射请去元数据维护</p>
            </div>
          </div>
        </div>
      </div>
      <div v-if="result" class="card bi0-result-card">
        <div class="bi0-result-hd"><div class="collapse-h"><b>查询结果</b> · 共 {{ result.total }} 行</div></div>
        <div class="tbl-wrap">
          <table>
            <thead>
              <tr>
                <th v-for="c in result.columns" :key="c">{{ c }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, idx) in result.rows" :key="idx">
                <td v-for="c in result.columns" :key="c">{{ row[c] }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>

    <template v-else>
      <div class="card bi0-mine-card">
        <div class="bi0-mine-hd"><h3>已保存查询</h3></div>
        <div class="bi0-mine-body">
          <div class="qbar">
            <input v-model="mineFilter.queryName" placeholder="名称" />
            <select v-model="mineFilter.status">
              <option value="">全部状态</option>
              <option value="DRAFT">DRAFT</option>
              <option value="PUBLISHED">PUBLISHED</option>
            </select>
            <button class="btn btn-sec btn-sm" type="button" @click="loadMine">查询</button>
          </div>
          <div class="tbl-wrap">
            <table>
              <thead>
                <tr>
                  <th>查询名称</th>
                  <th>实体</th>
                  <th>创建人</th>
                  <th>状态</th>
                  <th>更新时间</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="!mineRows.length">
                  <td colspan="6"><div class="empty"><div class="et">暂无保存的查询</div></div></td>
                </tr>
                <tr v-for="row in mineRows" :key="row.id">
                  <td>{{ row.queryName }}</td>
                  <td class="mono">{{ row.entityCode }}</td>
                  <td>{{ row.creatorName }}</td>
                  <td>{{ row.status }}</td>
                  <td>{{ row.updatedAt }}</td>
                  <td>
                    <button class="btn-txt btn" type="button" @click="runSaved(row.id)">执行</button>
                    <button
                      v-if="row.status !== 'PUBLISHED'"
                      class="btn-txt btn"
                      type="button"
                      @click="publishRow(row.id)"
                    >
                      发布
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </template>
    <p v-if="toast" class="hint" style="margin-top: 10px">{{ toast }}</p>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { http } from '../../api/http'

type FieldVo = { fieldCode: string; displayName: string; columnName: string }
type EntityOpt = { entityCode: string; entityName: string }
type QueryRow = {
  id: string
  queryName: string
  entityCode: string
  status: string
  creatorName: string
  updatedAt: string
}

const router = useRouter()
const tab = ref<'builder' | 'mine'>('builder')
const entities = ref<EntityOpt[]>([])
const fields = ref<FieldVo[]>([])
const fieldHint = ref('')
const toast = ref('')
const running = ref(false)
const result = ref<{ columns: string[]; rows: Record<string, unknown>[]; total: number; sql?: string } | null>(null)
const previewSql = ref('SELECT … FROM …（执行后展示实际 SQL）')

const builder = reactive({
  entityCode: '',
  selectFields: [] as string[],
  limit: 100,
})

const mineFilter = reactive({ queryName: '', status: '' })
const mineRows = ref<QueryRow[]>([])

const payloadConfig = computed(() => ({
  selectFields: builder.selectFields.length ? builder.selectFields : fields.value.map((f) => f.fieldCode),
  conditions: [] as unknown[],
  limit: builder.limit || 100,
}))

async function loadEntities() {
  const res = await http.get('/collect/metadata/list', { params: { pageNo: 1, pageSize: 100 } })
  if (res.code !== 0) return
  entities.value = res.data.list.map((r: { entityCode: string; entityName: string }) => ({
    entityCode: r.entityCode,
    entityName: r.entityName,
  }))
}

async function loadFields() {
  fields.value = []
  fieldHint.value = ''
  if (!builder.entityCode) return
  const res = await http.get(`/collect/metadata/entity/${builder.entityCode}/fields`)
  if (res.code === 1261) {
    fieldHint.value = '实体未映射（1261）· 请点击右上角「元数据维护」完成 COLLECT P4m 映射'
    return
  }
  if (res.code !== 0) {
    fieldHint.value = res.msg || '加载字段失败'
    return
  }
  fields.value = res.data.fields
  builder.selectFields = fields.value.slice(0, 2).map((f) => f.fieldCode)
}

async function ensureSaved(name: string) {
  const res = await http.post('/bi/query', {
    queryName: name,
    entityCode: builder.entityCode,
    status: 'DRAFT',
    config: payloadConfig.value,
  })
  if (res.code === 1261) {
    toast.value = '实体未映射（1261）'
    return null
  }
  if (res.code !== 0) {
    toast.value = res.msg || '保存失败'
    return null
  }
  return res.data.id as string
}

async function runAdhoc() {
  if (!builder.entityCode) {
    toast.value = '请选择数据源'
    return
  }
  running.value = true
  toast.value = ''
  try {
    const id = await ensureSaved(`临时查询 ${new Date().toLocaleTimeString()}`)
    if (!id) return
    const run = await http.post(`/bi/query/${id}/run`, {})
    if (run.code !== 0) {
      toast.value = run.msg || '执行失败'
      return
    }
    result.value = run.data
    previewSql.value = run.data.sql || previewSql.value
  } finally {
    running.value = false
  }
}

async function saveDraft() {
  const name = window.prompt('查询名称', '我的查询')
  if (!name?.trim()) return
  const id = await ensureSaved(name.trim())
  if (id) toast.value = '已保存'
}

async function loadMine() {
  const res = await http.get('/bi/query/page', {
    params: { pageNo: 1, pageSize: 50, queryName: mineFilter.queryName, status: mineFilter.status },
  })
  if (res.code === 0) mineRows.value = res.data.list
}

function switchMine() {
  tab.value = 'mine'
  loadMine()
}

async function runSaved(id: string) {
  const run = await http.post(`/bi/query/${id}/run`, {})
  if (run.code !== 0) {
    toast.value = run.msg || '执行失败'
    return
  }
  tab.value = 'builder'
  result.value = run.data
  previewSql.value = run.data.sql || previewSql.value
  toast.value = '已加载结果'
}

async function publishRow(id: string) {
  const res = await http.put(`/bi/query/${id}/publish`, {})
  if (res.code === 0) {
    toast.value = '已发布'
    loadMine()
  } else toast.value = res.msg || '发布失败'
}

function goMetadata() {
  router.push('/ims/collect/metadata')
}

onMounted(() => {
  loadEntities()
})
</script>
