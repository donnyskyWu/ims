<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>升级中心</h1>
        <div class="sub">ALERT-003 · 一级 30 分钟 / 二级 60 分钟 · L3 从二级起跳 · 钉钉不外发</div>
      </div>
      <div class="acts">
        <router-link class="btn btn-sec btn-sm" to="/ims/alert/live">实时预警</router-link>
        <router-link class="btn btn-sec btn-sm" to="/ims/alert/rule">预警规则</router-link>
      </div>
    </div>

    <div class="card" style="margin-bottom: 12px">
      <h3 style="margin: 0 0 12px">升级链路配置</h3>
      <form class="qbar" @submit.prevent="saveConfig">
        <label>
          一级（分钟）
          <input
            v-model.number="form.level1TimeoutMinutes"
            data-testid="alert-escalate-l1"
            type="number"
            min="0"
            max="10080"
            style="width: 88px"
          />
        </label>
        <label>
          二级（分钟）
          <input
            v-model.number="form.level2TimeoutMinutes"
            data-testid="alert-escalate-l2"
            type="number"
            min="0"
            max="10080"
            style="width: 88px"
          />
        </label>
        <label>
          严重级起跳
          <select v-model.number="form.severeStartLevel" data-testid="alert-escalate-severe" style="width: 120px">
            <option :value="2">二级</option>
            <option :value="3">三级</option>
          </select>
        </label>
        <span class="sp"></span>
        <button class="btn btn-pri btn-sm" type="submit" data-testid="alert-escalate-save">保存</button>
      </form>
      <p class="hint">一级责任人 → 二级部门负责人 → 三级运营总监与系统管理员。到点写入站内通知，钉钉不外发。</p>
      <p v-if="savedHint" class="hint" data-testid="alert-escalate-saved">{{ savedHint }}</p>
      <p v-if="formError" class="hint" style="color: var(--red)" data-testid="alert-escalate-form-error">{{ formError }}</p>
    </div>

    <form class="qbar" @submit.prevent="loadList">
      <select v-model="levelFilter" data-testid="alert-escalate-level" style="width: 140px">
        <option value="">全部级别</option>
        <option value="1">一级</option>
        <option value="2">二级</option>
        <option value="3">三级</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">刷新</button>
    </form>

    <p v-if="error" class="hint" style="color: var(--red)">{{ error }}</p>

    <div class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>预警编号</th>
              <th>规则</th>
              <th>级别</th>
              <th>当前升级级别</th>
              <th>下一级升级于</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="6"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!rows.length">
              <td colspan="6"><div class="empty"><div class="et">暂无待升级预警</div></div></td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.alertNo" :data-testid="`alert-escalate-row-${row.alertNo}`">
              <td class="mono">{{ row.alertNo }}</td>
              <td>{{ row.ruleName }}</td>
              <td>{{ row.level }}</td>
              <td data-testid="alert-escalate-current">{{ levelName(row.currentLevel) }}</td>
              <td class="mono">{{ nextText(row.nextEscalateAt) }}</td>
              <td>
                <button class="btn btn-txt btn-sm" type="button" data-testid="alert-escalate-timeline" @click="openTimeline(row.alertNo)">
                  时间轴
                </button>
                <button
                  class="btn btn-sec btn-sm"
                  type="button"
                  data-testid="alert-escalate-confirm"
                  @click="confirmStop(row.alertNo)"
                >
                  确认
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    <p v-if="toast" class="hint" data-testid="alert-escalate-toast">{{ toast }}</p>

    <ProtoDrawer :open="timelineOpen" title="升级时间轴" width="640px" @close="timelineOpen = false">
      <p v-if="timeline" class="hint" data-testid="alert-escalate-timeline-status">
        {{ timeline.alertNo }} · {{ timeline.alertLevel }} · {{ timeline.responseStatus }}
        <span v-if="timeline.responseStatus !== 'OPEN'"> · 已响应，升级链停止</span>
      </p>
      <div v-if="timeline && !timeline.timeline.length" class="empty"><div class="et">尚未进入下一级</div></div>
      <ul v-else-if="timeline" style="list-style: none; padding: 0; margin: 0">
        <li
          v-for="node in timeline.timeline"
          :key="node.escalationLevel"
          class="card"
          style="margin-bottom: 8px"
          data-testid="alert-escalate-node"
        >
          <strong>{{ levelName(node.escalationLevel) }}</strong>
          · 距产生 {{ node.elapsedMinutes }} 分钟
          <div class="hint">
            {{ receiverText(node.escalatedTo) }}
          </div>
          <div class="hint">站内已记录，钉钉不外发</div>
        </li>
      </ul>
    </ProtoDrawer>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import ProtoDrawer from '../../components/ProtoDrawer.vue'
import { errorMessage, http } from '../../api/http'

type Person = { userId: number; userName: string; roleLabel: string }
type Row = {
  alertNo: string
  ruleName: string
  level: string
  currentLevel: number
  nextEscalateAt: string
}
type Node = {
  escalationLevel: number
  escalatedTo: Person[]
  elapsedMinutes: number
}
type Timeline = {
  alertNo: string
  alertLevel: string
  responseStatus: string
  timeline: Node[]
}

const form = reactive({
  level1TimeoutMinutes: 30,
  level2TimeoutMinutes: 60,
  severeStartLevel: 2,
})
const savedHint = ref('')
const formError = ref('')
const error = ref('')
const toast = ref('')
const loading = ref(false)
const rows = ref<Row[]>([])
const levelFilter = ref('')
const timelineOpen = ref(false)
const timeline = ref<Timeline | null>(null)

function levelName(level: number) {
  return ({ 1: '一级', 2: '二级', 3: '三级' } as Record<number, string>)[level] || String(level)
}

function nextText(value: string) {
  if (!value) return '终级等待响应'
  return value.slice(0, 16).replace('T', ' ')
}

function receiverText(people: Person[]) {
  if (!people.length) return '暂无接收人'
  return people.map((item) => `${item.userName}（${item.roleLabel}）`).join('、')
}

async function saveConfig() {
  savedHint.value = ''
  formError.value = ''
  try {
    await http.put('/alert/escalate/config', {
      level1TimeoutMinutes: form.level1TimeoutMinutes,
      level2TimeoutMinutes: form.level2TimeoutMinutes,
      severeStartLevel: form.severeStartLevel,
      level1Receivers: { dynamicTarget: 'RESPONSIBLE_PERSON' },
      level2Receivers: { dynamicTarget: 'DEPT_LEADER', extraUserIds: [] },
      level3Receivers: { roleCodes: ['R4', 'R1'] },
    })
    savedHint.value = `升级链路已更新：一级 ${form.level1TimeoutMinutes} 分钟，二级 ${form.level2TimeoutMinutes} 分钟`
    await loadList()
  } catch (err) {
    formError.value = errorMessage(err)
  }
}

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const params: Record<string, unknown> = { pageNo: 1, pageSize: 50 }
    if (levelFilter.value) params.currentLevel = Number(levelFilter.value)
    const res = await http.get('/alert/escalate/pending', { params })
    rows.value = res.data.data?.list || []
  } catch (err) {
    error.value = errorMessage(err)
    rows.value = []
  } finally {
    loading.value = false
  }
}

async function openTimeline(alertNo: string) {
  toast.value = ''
  try {
    const res = await http.get(`/alert/escalate/timeline/${alertNo}`)
    timeline.value = res.data.data
    timelineOpen.value = true
  } catch (err) {
    toast.value = errorMessage(err)
  }
}

async function confirmStop(alertNo: string) {
  toast.value = ''
  try {
    const res = await http.put(`/alert/check/${alertNo}/respond`, { response: 'CONFIRM', handleRemark: '升级中心确认' })
    const stopped = res.data.data?.escalationStopped
    toast.value = stopped
      ? `响应成功，后续升级已停止（${alertNo}）`
      : `已确认（${alertNo}）`
    await loadList()
  } catch (err) {
    toast.value = errorMessage(err)
  }
}

onMounted(loadList)
</script>
