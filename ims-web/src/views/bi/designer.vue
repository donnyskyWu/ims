<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>报表设计器</h1>
        <div class="sub">
          {{ report?.reportName || '加载中…' }} · 隐藏路由 /ims/bi/report/designer · BI-001 P0
        </div>
      </div>
      <div class="acts">
        <router-link class="btn btn-sec btn-sm" to="/ims/bi/report/list">返回报表管理</router-link>
        <button class="btn btn-sec btn-sm" type="button" @click="runPreview">运行预览</button>
        <button class="btn btn-pri btn-sm" type="button" :disabled="saving" @click="saveLayout">保存</button>
        <button class="btn btn-pri btn-sm" type="button" @click="publish">保存并发布</button>
      </div>
    </div>

    <div v-if="loadError" class="card"><div class="empty"><div class="et">{{ loadError }}</div></div></div>

    <div v-else class="bidsn" style="display: grid; grid-template-columns: 198px 1fr 272px; gap: 12px; min-height: 520px">
      <div class="card" style="padding: 12px">
        <b style="font-size: 13px">数据集</b>
        <div v-for="ds in datasets" :key="ds.code" class="csub" style="margin-top: 8px; cursor: pointer" @click="activeDataset = ds.code">
          {{ ds.name }}
        </div>
        <b style="font-size: 13px; display: block; margin-top: 16px">组件库</b>
        <button
          v-for="c in compLib"
          :key="c.type"
          class="btn btn-sec btn-sm"
          type="button"
          style="display: block; width: 100%; margin-top: 8px"
          @click="addComp(c)"
        >
          + {{ c.name }}
        </button>
      </div>

      <div class="card" style="padding: 12px; position: relative; background: repeating-linear-gradient(0deg, #f5f7fa, #f5f7fa 39px, #e8ecf0 40px)">
        <div class="rowline" style="justify-content: space-between; margin-bottom: 8px">
          <span class="csub">画布 · FREE · {{ comps.length }} 组件</span>
          <span v-if="previewMsg" class="tag tag-info">{{ previewMsg }}</span>
        </div>
        <div
          v-for="comp in comps"
          :key="comp.id"
          class="card hov"
          :style="{
            position: 'absolute',
            left: comp.x + 'px',
            top: comp.y + 'px',
            width: comp.w + 'px',
            minHeight: comp.h + 'px',
            padding: '8px',
            outline: selectedId === comp.id ? '2px solid var(--blue)' : '',
            cursor: 'pointer',
          }"
          @click="selectedId = comp.id"
        >
          <b>{{ comp.title }}</b>
          <div class="csub">{{ comp.type }} · {{ comp.dataset || activeDataset }}</div>
        </div>
        <div v-if="!comps.length" class="empty" style="margin-top: 120px"><div class="et">从左侧拖入组件（点击添加）</div></div>
      </div>

      <div class="card" style="padding: 12px">
        <b style="font-size: 13px">属性</b>
        <template v-if="selected">
          <label class="fld">标题</label>
          <input v-model="selected.title" class="fld-in" />
          <label class="fld">X / Y</label>
          <div class="rowline" style="gap: 8px">
            <input v-model.number="selected.x" type="number" class="fld-in" style="width: 48%" />
            <input v-model.number="selected.y" type="number" class="fld-in" style="width: 48%" />
          </div>
          <label class="fld">宽 / 高</label>
          <div class="rowline" style="gap: 8px">
            <input v-model.number="selected.w" type="number" class="fld-in" style="width: 48%" />
            <input v-model.number="selected.h" type="number" class="fld-in" style="width: 48%" />
          </div>
          <button class="btn btn-sec btn-sm" type="button" style="margin-top: 12px" @click="removeSelected">删除组件</button>
        </template>
        <div v-else class="csub" style="margin-top: 12px">选中画布组件以编辑</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { http } from '../../api/http'

type Comp = {
  id: string
  type: string
  title: string
  x: number
  y: number
  w: number
  h: number
  dataset?: string
}

type ReportVo = {
  id: number
  reportName: string
  status: string
  comps: Comp[]
  layoutMode: string
}

const route = useRoute()
const reportId = computed(() => Number(route.query.reportId || 0))
const report = ref<ReportVo | null>(null)
const comps = ref<Comp[]>([])
const datasets = ref<{ code: string; name: string }[]>([])
const compLib = ref<{ type: string; name: string; defaultSize: { w: number; h: number } }[]>([])
const activeDataset = ref('METRIC_LIB')
const selectedId = ref('')
const saving = ref(false)
const loadError = ref('')
const previewMsg = ref('')

const selected = computed(() => comps.value.find((c) => c.id === selectedId.value) || null)

function uid() {
  return `c${Date.now().toString(36)}${Math.random().toString(36).slice(2, 5)}`
}

function addComp(meta: { type: string; name: string; defaultSize: { w: number; h: number } }) {
  const id = uid()
  comps.value.push({
    id,
    type: meta.type,
    title: meta.name,
    x: 40 + comps.value.length * 24,
    y: 40 + comps.value.length * 16,
    w: meta.defaultSize.w,
    h: meta.defaultSize.h,
    dataset: activeDataset.value,
  })
  selectedId.value = id
}

function removeSelected() {
  if (!selectedId.value) return
  comps.value = comps.value.filter((c) => c.id !== selectedId.value)
  selectedId.value = ''
}

async function loadMeta() {
  const ds = await http.get('/bi/report/datasets')
  if (ds.data.code === 0) {
    datasets.value = ds.data.data.datasets || []
    compLib.value = ds.data.data.compLib || []
  }
}

async function loadReport() {
  loadError.value = ''
  if (!reportId.value) {
    loadError.value = '缺少 reportId 参数'
    return
  }
  const res = await http.get(`/bi/report/${reportId.value}`)
  if (res.data.code !== 0) {
    loadError.value = res.data.msg || '加载失败'
    return
  }
  report.value = res.data.data
  comps.value = (res.data.data.comps || []) as Comp[]
  if (comps.value.length) selectedId.value = comps.value[0].id
}

async function saveLayout() {
  if (!reportId.value) return
  saving.value = true
  try {
    const res = await http.put(`/bi/report/${reportId.value}`, {
      reportName: report.value?.reportName,
      layoutJson: { layoutMode: 'FREE', comps: comps.value },
    })
    if (res.data.code !== 0) {
      previewMsg.value = res.data.msg || '保存失败'
      return
    }
    report.value = res.data.data
    previewMsg.value = '已保存'
  } finally {
    saving.value = false
  }
}

async function publish() {
  await saveLayout()
  const res = await http.post(`/bi/report/${reportId.value}/publish`)
  if (res.data.code === 0) {
    previewMsg.value = `已发布 · ${res.data.data.status}`
    report.value = { ...report.value!, status: res.data.data.status }
  }
}

async function runPreview() {
  const res = await http.post('/bi/report/query', {
    reportId: reportId.value,
    compId: selectedId.value || 'preview',
    components: comps.value,
  })
  if (res.data.code === 0) {
    previewMsg.value = `预览 ${res.data.data.total} 行 · ${res.data.data.status}`
  }
}

onMounted(async () => {
  await loadMeta()
  await loadReport()
})
</script>
