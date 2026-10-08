<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>报表中心</h1>
        <div class="sub">M6 八张标准报表 · 统一筛选条 · /ims/bi/report</div>
      </div>
    </div>

    <div class="qbar">
      <span class="csub">平台</span>
      <select v-model="platform" style="width: 110px">
        <option value="">全部平台</option>
        <option value="DOUYIN">抖音</option>
        <option value="WECHAT_CHANNELS">视频号</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="button" @click="reloadPreview">刷新预览</button>
    </div>

    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-top: 14px">
      <div
        v-for="item in reports"
        :key="item.code"
        class="card hov"
        style="cursor: pointer"
        :style="{ outline: selected?.code === item.code ? '2px solid var(--blue)' : '' }"
        @click="selectReport(item)"
      >
        <b>{{ item.title }}</b>
        <div class="csub" style="margin-top: 8px">{{ item.desc }}</div>
        <div class="rowline" style="margin-top: 10px; gap: 6px; flex-wrap: wrap">
          <span v-for="tag in item.tags" :key="tag" class="tag tag-info">{{ tag }}</span>
        </div>
      </div>
    </div>

    <div v-if="preview" class="card" style="margin-top: 16px">
      <div class="bi0-result-hd"><b>{{ preview.title }}</b> · {{ preview.total }} 行 · {{ preview.dataAsOf }}</div>
      <div class="tbl-wrap" style="margin-top: 8px">
        <table>
          <thead>
            <tr>
              <th v-for="c in preview.columns" :key="c">{{ c }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, idx) in preview.rows" :key="idx">
              <td v-for="c in preview.columns" :key="c">{{ row[c] }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { http } from '../../api/http'

type ReportCard = { code: string; title: string; desc: string; tags: string[] }

const reports = ref<ReportCard[]>([])
const selected = ref<ReportCard | null>(null)
const preview = ref<{ title: string; columns: string[]; rows: Record<string, unknown>[]; total: number; dataAsOf: string } | null>(null)
const platform = ref('')

async function loadCatalog() {
  const res = await http.get('/bi/report/catalog')
  if (res.data.code === 0) {
    reports.value = res.data.data.reports || []
    if (reports.value.length && !selected.value) {
      selected.value = reports.value[0]
      await reloadPreview()
    }
  }
}

async function selectReport(item: ReportCard) {
  selected.value = item
  await reloadPreview()
}

async function reloadPreview() {
  if (!selected.value) return
  const res = await http.get(`/bi/report/${selected.value.code}`, { params: { platform: platform.value || undefined } })
  if (res.data.code === 0) preview.value = res.data.data
}

onMounted(loadCatalog)
</script>
