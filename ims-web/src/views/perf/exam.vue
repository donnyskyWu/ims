<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>在线考试</h1>
        <div class="sub">PERF-003 · IMS 自建考试域 · 05 PERF</div>
      </div>
      <div class="acts">
        <button class="btn btn-pri btn-sm" type="button" disabled>创建试卷</button>
      </div>
    </div>
    <div class="cattabs">
      <button type="button" class="cattab on">题库管理</button>
      <button type="button" class="cattab" disabled>试卷管理</button>
      <button type="button" class="cattab" disabled>成绩管理</button>
    </div>
    <form class="qbar" @submit.prevent="loadList">
      <input v-model="filters.questionNo" placeholder="题目编号" style="width: 110px" />
      <input v-model="filters.stemKeyword" placeholder="题干关键词" style="width: 150px" />
      <select v-model="filters.knowledgeDomain" style="width: 110px">
        <option value="">全部知识域</option>
        <option value="LIVE_RULE">直播规范</option>
        <option value="CONTENT_SKILL">内容技能</option>
        <option value="LIVE_SKILL">直播技能</option>
        <option value="DATA_SKILL">数据技能</option>
        <option value="COMPLIANCE">制度合规</option>
      </select>
      <select v-model="filters.questionType" style="width: 90px">
        <option value="">全部题型</option>
        <option value="SINGLE">单选</option>
        <option value="MULTIPLE">多选</option>
        <option value="JUDGE">判断</option>
        <option value="ESSAY">简答</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">查询</button>
      <button class="btn btn-sec btn-sm" type="button" @click="resetFilters">重置</button>
    </form>
    <div class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>题目编号</th>
              <th>题干</th>
              <th>知识域</th>
              <th>题型</th>
              <th>分值</th>
              <th>被引用</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="7"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!rows.length">
              <td colspan="7"><div class="empty"><div class="et">{{ error || '暂无题目' }}</div></div></td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.id">
              <td class="mono num" style="color: var(--blue)">{{ row.questionNo }}</td>
              <td style="font-weight: 500; max-width: 340px">{{ row.stem }}</td>
              <td>
                <span class="tag" style="background: rgba(142, 142, 147, 0.12); color: #6d6d72">
                  <span class="dot"></span>{{ row.knowledgeDomainLabel }}
                </span>
              </td>
              <td>
                <span class="tag" :style="typeStyle(row.questionType)">
                  <span class="dot"></span>{{ row.questionTypeLabel }}
                </span>
              </td>
              <td class="num">{{ row.score }} 分</td>
              <td class="num">{{ row.refCount }} 卷</td>
              <td><span class="btn btn-sec btn-sm" style="pointer-events: none; opacity: 0.5">编辑</span></td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="total > 0" class="pager">
        <span class="pg-total">共 {{ total }} 条</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { http } from '../../api/http'

type Row = {
  id: string
  questionNo: string
  stem: string
  knowledgeDomainLabel: string
  questionType: string
  questionTypeLabel: string
  score: number
  refCount: number
}

const rows = ref<Row[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const filters = reactive({
  questionNo: '',
  stemKeyword: '',
  knowledgeDomain: '',
  questionType: '',
})

function typeStyle(qtype: string) {
  const map: Record<string, string> = {
    SINGLE: 'background:rgba(0,113,227,.12);color:#0071e3',
    MULTIPLE: 'background:rgba(175,82,218,.12);color:#8944ab',
    JUDGE: 'background:rgba(90,200,250,.12);color:#0e7fb8',
    ESSAY: 'background:rgba(255,149,0,.12);color:#c46a00',
  }
  return map[qtype] || map.SINGLE
}

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const params: Record<string, string | number> = { pageNo: 1, pageSize: 20 }
    if (filters.questionNo) params.questionNo = filters.questionNo
    if (filters.stemKeyword) params.stemKeyword = filters.stemKeyword
    if (filters.knowledgeDomain) params.knowledgeDomain = filters.knowledgeDomain
    if (filters.questionType) params.questionType = filters.questionType
    const res = await http.get('/perf/exam/questions', { params })
    if (res.data.code !== 0) {
      error.value = res.data.msg || '加载失败'
      rows.value = []
      total.value = 0
      return
    }
    rows.value = res.data.data.list || []
    total.value = res.data.data.total || 0
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : '网络错误'
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  filters.questionNo = ''
  filters.stemKeyword = ''
  filters.knowledgeDomain = ''
  filters.questionType = ''
  loadList()
}

onMounted(loadList)
</script>
