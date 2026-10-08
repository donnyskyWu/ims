<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>填写日报</h1>
        <div class="sub">MEET-001 P1 · 草稿自动保存 · 正式提交</div>
      </div>
      <div class="acts">
        <button class="btn btn-sec btn-sm" type="button" @click="goBack">返回我的日报</button>
      </div>
    </div>
    <p class="hint">日报日期 {{ reportDate }} · 截止 {{ deadlineTime }}</p>
    <div class="card" style="padding: 16px; max-width: 720px">
      <label class="fld"><span>今日完成 *</span><textarea v-model="form.contentDone" rows="4" /></label>
      <label class="fld"><span>明日计划 *</span><textarea v-model="form.contentPlan" rows="3" /></label>
      <label class="fld"><span>问题与风险 *</span><textarea v-model="form.contentIssue" rows="3" /></label>
      <label v-if="weekSummaryEnabled" class="fld"><span>周小结 *</span><textarea v-model="form.weekSummary" rows="3" /></label>
      <div v-if="locked" class="hint" style="margin: 12px 0">正文已提交，仅可追加补充说明。</div>
      <label v-if="locked" class="fld"><span>补充说明</span><textarea v-model="form.supplement" rows="3" /></label>
      <div class="acts" style="margin-top: 16px">
        <button v-if="!locked" class="btn btn-sec btn-sm" type="button" :disabled="saving" @click="save(true)">存草稿</button>
        <button class="btn btn-pri btn-sm" type="button" :disabled="saving" @click="save(false)">
          {{ locked ? '保存补充说明' : '提交日报' }}
        </button>
      </div>
      <p v-if="msg" class="hint" style="margin-top: 8px">{{ msg }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { http } from '../../api/http'

const router = useRouter()
const reportDate = ref('')
const deadlineTime = ref('22:00')
const weekSummaryEnabled = ref(false)
const locked = ref(false)
const saving = ref(false)
const msg = ref('')
const reportId = ref<number | null>(null)
const form = reactive({
  contentDone: '',
  contentPlan: '',
  contentIssue: '',
  weekSummary: '',
  supplement: '',
})

function todayStr() {
  const d = new Date()
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

function goBack() {
  router.push('/ims/meet/daily')
}

async function loadTemplateAndToday() {
  reportDate.value = todayStr()
  const tpl = await http.get('/meet/daily/template')
  if (tpl.data.code === 0) {
    deadlineTime.value = tpl.data.data.deadlineTime || '22:00'
    weekSummaryEnabled.value = !!tpl.data.data.weekSummaryEnabled
  }
  const cur = await http.get(`/meet/daily/${reportDate.value}`)
  if (cur.data.code === 0 && cur.data.data) {
    const row = cur.data.data
    reportId.value = row.id
    form.contentDone = row.contentDone || ''
    form.contentPlan = row.contentPlan || ''
    form.contentIssue = row.contentIssue || ''
    form.weekSummary = row.weekSummary || ''
    form.supplement = row.supplement || ''
    locked.value = row.submitStatus === 'SUBMITTED' || row.submitStatus === 'READ'
  }
}

async function save(asDraft: boolean) {
  saving.value = true
  msg.value = ''
  try {
    const payload = {
      reportDate: reportDate.value,
      contentDone: form.contentDone,
      contentPlan: form.contentPlan,
      contentIssue: form.contentIssue,
      weekSummary: form.weekSummary,
      supplement: form.supplement || undefined,
      asDraft,
    }
    let res
    if (locked.value && reportId.value) {
      res = await http.put(`/meet/daily/${reportId.value}`, payload)
    } else {
      res = await http.post('/meet/daily/submit', payload)
    }
    if (res.data.code !== 0) {
      msg.value = res.data.msg || '保存失败'
      return
    }
    reportId.value = res.data.data.id
    locked.value = res.data.data.submitStatus === 'SUBMITTED' || res.data.data.submitStatus === 'READ'
    msg.value = asDraft ? '草稿已保存' : locked.value ? '已提交' : '已保存'
  } catch (e: unknown) {
    msg.value = e instanceof Error ? e.message : '网络错误'
  } finally {
    saving.value = false
  }
}

onMounted(loadTemplateAndToday)
</script>

<style scoped>
.fld {
  display: block;
  margin-bottom: 12px;
}
.fld span {
  display: block;
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 4px;
}
.fld textarea {
  width: 100%;
  box-sizing: border-box;
  padding: 8px;
  border: 1px solid var(--border, #ddd);
  border-radius: 8px;
  font: inherit;
}
</style>
