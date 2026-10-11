<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>填写日报</h1>
        <div class="sub">MEET-001 · 草稿自动保存 · 正式提交</div>
      </div>
      <div class="acts">
        <button class="btn btn-sec btn-sm" type="button" @click="goBack">返回我的日报</button>
      </div>
    </div>
    <p class="hint">日报日期 {{ reportDate }} · 截止 {{ deadlineTime }}</p>
    <div class="card" style="padding: 16px; max-width: 720px">
      <label class="fld">
        <span>日报类型</span>
        <select v-model="form.reportType" data-testid="daily-type">
          <option value="">请选择</option>
          <option v-for="item in reportTypes" :key="item.value" :value="item.value">{{ item.label }}</option>
        </select>
      </label>
      <label class="fld">
        <span>今日完成 *</span>
        <textarea v-model="form.contentDone" rows="4" data-testid="daily-done" />
        <p v-if="fieldErrors.contentDone" class="err">{{ fieldErrors.contentDone }}</p>
      </label>
      <label class="fld">
        <span>明日计划</span>
        <textarea v-model="form.contentPlan" rows="3" data-testid="daily-plan" />
      </label>
      <label class="fld">
        <span>问题与风险</span>
        <textarea v-model="form.contentIssue" rows="3" data-testid="daily-issue" />
      </label>
      <label v-if="weekSummaryEnabled" class="fld">
        <span>周小结 *</span>
        <textarea v-model="form.weekSummary" rows="3" data-testid="daily-week" />
        <p v-if="fieldErrors.weekSummary" class="err">{{ fieldErrors.weekSummary }}</p>
      </label>
      <div v-if="locked" class="hint" style="margin: 12px 0">正文已提交，仅可追加补充说明。</div>
      <label v-if="locked" class="fld">
        <span>补充说明</span>
        <textarea v-model="form.supplement" rows="3" data-testid="daily-supplement" />
      </label>
      <div class="acts" style="margin-top: 16px">
        <button v-if="!locked" class="btn btn-sec btn-sm" type="button" :disabled="saving" @click="save(true)">存草稿</button>
        <button class="btn btn-pri btn-sm" type="button" data-testid="daily-submit" :disabled="saving" @click="save(false)">
          {{ locked ? '保存补充说明' : '保存并提交' }}
        </button>
      </div>
      <p v-if="msg" class="hint" data-testid="daily-msg" style="margin-top: 8px">{{ msg }}</p>
    </div>
    <div v-if="toast" class="toasts">
      <div class="toast t-success">{{ toast }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { errorMessage, http } from '../../api/http'

const router = useRouter()
const reportDate = ref('')
const deadlineTime = ref('22:00')
const weekSummaryEnabled = ref(false)
const locked = ref(false)
const saving = ref(false)
const msg = ref('')
const toast = ref('')
const reportId = ref<number | null>(null)
const reportTypes = ref<{ value: string; label: string }[]>([
  { value: 'LIVE', label: '直播' },
  { value: 'SHORT_VIDEO', label: '短视频' },
  { value: 'OPS', label: '运营' },
  { value: 'ADMIN', label: '行政' },
])
const form = reactive({
  reportType: '',
  contentDone: '',
  contentPlan: '',
  contentIssue: '',
  weekSummary: '',
  supplement: '',
})
const fieldErrors = reactive({ contentDone: '', weekSummary: '' })

function todayStr() {
  const d = new Date()
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

function goBack() {
  router.push('/ims/meet/daily')
}

function applyRow(row: Record<string, unknown>) {
  reportId.value = Number(row.id)
  form.reportType = String(row.reportType || '')
  form.contentDone = String(row.contentDone || '')
  form.contentPlan = String(row.contentPlan || '')
  form.contentIssue = String(row.contentIssue || '')
  form.weekSummary = String(row.weekSummary || '')
  form.supplement = String(row.supplement || '')
  locked.value = row.submitStatus === 'SUBMITTED' || row.submitStatus === 'READ'
}

async function loadTemplateAndToday() {
  reportDate.value = todayStr()
  const tpl = await http.get('/meet/daily/template')
  if (tpl.data.code === 0) {
    deadlineTime.value = tpl.data.data.deadlineTime || '22:00'
    weekSummaryEnabled.value = !!tpl.data.data.weekSummaryEnabled
    if (Array.isArray(tpl.data.data.reportTypes) && tpl.data.data.reportTypes.length) {
      reportTypes.value = tpl.data.data.reportTypes
    }
  }
  const cur = await http.get(`/meet/daily/${reportDate.value}`)
  if (cur.data.code === 0 && cur.data.data) {
    applyRow(cur.data.data)
  }
}

function validate(asDraft: boolean) {
  fieldErrors.contentDone = ''
  fieldErrors.weekSummary = ''
  if (asDraft || locked.value) return true
  let ok = true
  if (!form.contentDone.trim()) {
    fieldErrors.contentDone = '必填项，请填写'
    ok = false
  }
  if (weekSummaryEnabled.value && !form.weekSummary.trim()) {
    fieldErrors.weekSummary = '必填项，请填写'
    ok = false
  }
  return ok
}

async function save(asDraft: boolean) {
  msg.value = ''
  toast.value = ''
  if (!validate(asDraft)) {
    msg.value = '必填项，请填写'
    return
  }
  const wasLocked = locked.value
  saving.value = true
  try {
    const payload = {
      reportDate: reportDate.value,
      reportType: form.reportType,
      contentDone: form.contentDone,
      contentPlan: form.contentPlan,
      contentIssue: form.contentIssue,
      weekSummary: form.weekSummary,
      supplement: wasLocked ? form.supplement : undefined,
      asDraft,
    }
    const res = wasLocked && reportId.value
      ? await http.put(`/meet/daily/${reportId.value}`, payload)
      : await http.post('/meet/daily/submit', payload)
    applyRow(res.data.data)
    if (asDraft) {
      msg.value = '草稿已保存'
      toast.value = '草稿已保存'
    } else if (wasLocked) {
      msg.value = '补充说明已保存'
      toast.value = '补充说明已保存'
    } else {
      const onTime = res.data.data.isOnTime ? '按时' : '迟交'
      msg.value = `已提交 · ${onTime} · 审阅待审阅`
      toast.value = '已提交'
    }
  } catch (e: unknown) {
    msg.value = errorMessage(e)
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
.fld textarea,
.fld select {
  width: 100%;
  box-sizing: border-box;
  padding: 8px;
  border: 1px solid var(--border, #ddd);
  border-radius: 8px;
  font: inherit;
  background: #fff;
}
.err {
  color: var(--red, #d70015);
  font-size: 12px;
  margin: 4px 0 0;
}
</style>
