<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>利润反查</h1>
        <div class="sub">DC-002 · /ims/fin/profit-trace · GET /dc/profit-trace/* · 11 FIN</div>
      </div>
    </div>

    <div v-if="dataAsOf" class="hint" style="margin-bottom: 10px">
      DC-002 · perm <code>ims:fin:profit-trace:query</code> · 数据截至 {{ dataAsOf }}
    </div>

    <div class="tabs" style="margin-bottom: 8px">
      <button type="button" class="tab on">利润列表</button>
      <button type="button" class="tab" disabled title="下一片">聚合下钻</button>
      <button type="button" class="tab" disabled title="下一片">异常清单</button>
    </div>

    <form class="qbar" @submit.prevent="loadList">
      <input v-model="query.sessionCode" placeholder="场次 ID" style="width: 180px" />
      <input v-model="query.platform" placeholder="平台" style="width: 100px" />
      <select v-model="query.calcStatus" style="width: 120px">
        <option value="">全部状态</option>
        <option value="CALCULATED">已计算</option>
        <option value="RECALCULATED">已重算</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="button" @click="loadList">查询</button>
    </form>

    <div v-if="error" class="hint" style="color: var(--red); margin: 8px 0">{{ error }}</div>

    <div class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>场次 ID</th>
              <th>标题</th>
              <th>净利润</th>
              <th>毛利</th>
              <th>版本</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="6"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!rows.length">
              <td colspan="6"><div class="empty"><div class="et">暂无已核算利润（需先核准成本）</div></div></td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.sessionCode">
              <td class="mono">{{ row.sessionCode }}</td>
              <td>{{ row.sessionTitle }}</td>
              <td class="num">¥{{ fmt(row.netProfit) }}</td>
              <td class="num">¥{{ fmt(row.grossProfit) }}</td>
              <td>V{{ row.calcVersion }}</td>
              <td>
                <button class="btn btn-sec btn-sm" type="button" @click="openTrace(row.sessionCode)">反查</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="drawerOpen && chain" class="drawer-mask" @click.self="drawerOpen = false">
      <div class="drawer" style="width: 680px">
        <div class="drawer-h">
          <b>反查链路 · {{ chain.sessionCode }}</b>
          <span class="hint">{{ queryCostMs }} ms</span>
          <button type="button" class="btn btn-sec btn-sm" @click="drawerOpen = false">关闭</button>
        </div>
        <p class="hint">BR-209：利润 → 场次 → 账号/资产/责任人/实名人 → 成本明细</p>
        <div class="g2" style="margin-bottom: 12px">
          <div class="card stat"><span class="l">净利润</span><div class="n">¥{{ fmt(chain.chain?.profit?.netProfit) }}</div></div>
          <div class="card stat"><span class="l">场次</span><div class="n" style="font-size: 14px">{{ chain.chain?.session?.sessionTitle }}</div></div>
        </div>
        <ul class="hint" style="line-height: 1.8; margin-bottom: 12px">
          <li>账号：{{ chain.chain?.account?.accountNo || '—' }}</li>
          <li>责任人：{{ chain.chain?.responsibleUser?.userName || '—' }}</li>
          <li>实名人：{{ chain.chain?.realnamePersons?.[0]?.userName || '—' }}</li>
          <li>资产：{{ (chain.chain?.assets || []).map((a: { assetCode: string }) => a.assetCode).join(', ') || '—' }}</li>
        </ul>
        <h3 style="font-size: 14px; margin-bottom: 6px">成本明细</h3>
        <table>
          <thead><tr><th>项目</th><th>金额</th></tr></thead>
          <tbody>
            <tr v-for="item in chain.chain?.costDetail || []" :key="item.costItem">
              <td>{{ item.costItemLabel || item.costItem }}</td>
              <td class="num">{{ item.amount == null ? '—' : '¥' + fmt(item.amount) }}</td>
            </tr>
          </tbody>
        </table>
        <h3 style="font-size: 14px; margin: 12px 0 6px">分成明细</h3>
        <table>
          <thead><tr><th>对象</th><th>分成</th></tr></thead>
          <tbody>
            <tr v-for="(s, i) in chain.chain?.shareDetail || []" :key="i">
              <td>{{ s.targetRefName || s.shareTarget }}</td>
              <td class="num">{{ s.shareAmount == null ? '—' : '¥' + fmt(s.shareAmount) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { http } from '../../api/http'

const loading = ref(false)
const error = ref('')
const rows = ref<Record<string, unknown>[]>([])
const dataAsOf = ref('')
const drawerOpen = ref(false)
const chain = ref<Record<string, unknown> | null>(null)
const queryCostMs = ref(0)
const query = reactive({ sessionCode: '', platform: '', calcStatus: '' })

function fmt(n: unknown) {
  return Number(n || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const res = await http.get('/dc/profit-trace/list', {
      params: {
        pageNo: 1,
        pageSize: 50,
        sessionCode: query.sessionCode || undefined,
        platform: query.platform || undefined,
        calcStatus: query.calcStatus || undefined,
      },
    })
    if (res.data?.code !== 0) {
      error.value = res.data?.msg || '加载失败'
      rows.value = []
      return
    }
    rows.value = res.data.data?.list || []
    dataAsOf.value = res.data.data?.dataAsOf || ''
  } finally {
    loading.value = false
  }
}

async function openTrace(sessionCode: string) {
  const res = await http.get(`/dc/profit-trace/${sessionCode}`)
  if (res.data?.code !== 0) {
    error.value = res.data?.msg || '反查失败'
    return
  }
  chain.value = res.data.data
  queryCostMs.value = res.data.data?.queryCostMs || 0
  drawerOpen.value = true
}

onMounted(loadList)
</script>
