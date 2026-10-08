<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>穿透查询</h1>
        <div class="sub">DC-001 · /ims/dc/trace · GET/POST /dc/trace/* · 12 DC</div>
      </div>
    </div>
    <div v-if="dataAsOf" class="hint" style="margin-bottom: 10px" data-testid="dc-trace-meta">
      数据截至 <b>{{ dataAsOf }}</b> · queryCostMs {{ queryCostMs }} ms
    </div>
    <form class="qbar" @submit.prevent="searchEntry">
      <select v-model="entryType" style="width: 120px">
        <option value="ACCOUNT">账号</option>
        <option value="SESSION">场次</option>
        <option value="PERSON">实名人</option>
      </select>
      <input
        v-model="keyword"
        placeholder="关键词"
        style="width: 160px"
        data-testid="dc-trace-keyword"
      />
      <button class="btn btn-sec btn-sm" type="button" data-testid="dc-trace-search-entry" @click="searchEntry">
        搜入口
      </button>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit" data-testid="dc-trace-submit">穿透查询</button>
    </form>
    <div v-if="entries.length" class="hint" style="margin: 8px 0">
      入口：
      <button
        v-for="e in entries"
        :key="e.entryId"
        type="button"
        class="btn btn-sec btn-sm"
        style="margin-right: 6px"
        @click="pickEntry(e)"
      >
        {{ e.entryLabel }}
      </button>
    </div>
    <div v-if="error" class="hint" style="color: var(--red)">{{ error }}</div>
    <div class="g2" style="margin-top: 12px">
      <div class="card" style="padding: 12px; min-height: 200px" data-testid="dc-trace-graph">
        <b style="font-size: 13px">关系图</b>
        <ul style="margin: 10px 0 0; padding-left: 18px; font-size: 12px">
          <li v-for="n in nodes" :key="n.nodeId">{{ n.nodeType }} · {{ n.nodeLabel }}</li>
        </ul>
        <p v-if="!nodes.length" class="csub">选择入口后查询</p>
      </div>
      <div class="tbl-block" data-testid="dc-trace-detail-table">
        <div class="tbl-wrap">
          <table>
            <thead>
              <tr>
                <th>场次</th>
                <th>平台</th>
                <th>账号</th>
                <th>实名人</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="d in details" :key="d.sessionCode">
                <td class="mono">{{ d.sessionCode }}</td>
                <td>{{ d.platform }}</td>
                <td>{{ d.accountNo }}</td>
                <td>{{ d.realnameName }}</td>
              </tr>
              <tr v-if="!details.length">
                <td colspan="4"><div class="empty"><div class="et">暂无明细</div></div></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { http } from '../../api/http'

type Entry = { entryType: string; entryId: string; entryLabel: string }
type Node = { nodeType: string; nodeId: string; nodeLabel: string }
type Detail = { sessionCode: string; platform: string; accountNo: string; realnameName: string }

const keyword = ref('')
const entryType = ref('ACCOUNT')
const selectedEntry = ref<Entry | null>(null)
const entries = ref<Entry[]>([])
const nodes = ref<Node[]>([])
const details = ref<Detail[]>([])
const dataAsOf = ref('')
const queryCostMs = ref(0)
const error = ref('')

async function searchEntry() {
  error.value = ''
  try {
    const res = await http.get('/dc/trace/entry', {
      params: { keyword: keyword.value, entryType: entryType.value, limit: 8 },
    })
    if (res.data.code !== 0) {
      error.value = res.data.msg || '搜索失败'
      return
    }
    entries.value = res.data.data || []
    if (entries.value.length === 1) pickEntry(entries.value[0])
  } catch {
    error.value = '网络错误'
  }
}

function pickEntry(e: Entry) {
  selectedEntry.value = e
  runQuery()
}

async function runQuery() {
  if (!selectedEntry.value) {
    error.value = '请先选择穿透入口'
    return
  }
  error.value = ''
  try {
    const res = await http.post('/dc/trace/query', {
      entryType: selectedEntry.value.entryType,
      entryId: selectedEntry.value.entryId,
      mode: 'DETAIL',
      pageNo: 1,
      pageSize: 10,
    })
    if (res.data.code !== 0) {
      error.value = res.data.msg || '查询失败'
      return
    }
    const data = res.data.data
    nodes.value = data.nodes || []
    dataAsOf.value = data.dataAsOf || ''
    queryCostMs.value = data.queryCostMs || 0
    details.value = data.detailList?.list || []
  } catch {
    error.value = '网络错误'
  }
}
</script>
