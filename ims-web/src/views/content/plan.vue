<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>计划管理</h1>
        <div class="sub">计划向导 / 计划列表（CONTENT-102 · P-M2-011）</div>
      </div>
      <div class="acts">
        <button class="btn btn-pri" type="button" @click="openCreate">新增计划</button>
      </div>
    </div>
    <p class="hint" style="margin-bottom: 10px">
      创建为草稿（DRAFT）；草稿可「启动」→ IN_PROGRESS；执行中可申请终止 → TERMINATE_PENDING，审批通过后 TERMINATED 并终止关联任务。
    </p>
    <div class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>计划名</th>
              <th>SOP</th>
              <th>IP 组</th>
              <th>周期</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="6"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!rows.length">
              <td colspan="6"><div class="empty"><div class="et">{{ error || '暂无计划' }}</div></div></td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.id">
              <td><b>{{ row.planName }}</b></td>
              <td>{{ row.sopName || row.sopId }}</td>
              <td>{{ row.ipGroupName || '—' }}</td>
              <td class="num">{{ row.startDate }} ~ {{ row.endDate }}</td>
              <td>
                {{ row.status }}
                <div
                  v-if="row.status === 'TERMINATE_PENDING' || row.status === 'TERMINATED'"
                  class="hint"
                  data-testid="plan-terminate-reason"
                >
                  {{ terminateLabel(row) }}
                </div>
              </td>
              <td class="acts-inline">
                <button
                  v-if="row.status === 'DRAFT'"
                  class="btn btn-pri btn-sm"
                  type="button"
                  :disabled="actingId === row.id"
                  @click="startPlan(row)"
                >
                  启动
                </button>
                <button
                  v-if="row.status === 'IN_PROGRESS'"
                  class="btn btn-sec btn-sm"
                  type="button"
                  :disabled="actingId === row.id"
                  @click="requestTerminate(row)"
                >
                  申请终止
                </button>
                <template v-if="row.status === 'TERMINATE_PENDING'">
                  <button
                    class="btn btn-pri btn-sm"
                    type="button"
                    :disabled="actingId === row.id"
                    @click="approveTerminate(row)"
                  >
                    批准终止
                  </button>
                  <button
                    class="btn btn-sec btn-sm"
                    type="button"
                    :disabled="actingId === row.id"
                    @click="rejectTerminate(row)"
                  >
                    驳回终止
                  </button>
                </template>
                <span
                  v-if="!['DRAFT', 'IN_PROGRESS', 'TERMINATE_PENDING'].includes(row.status)"
                  class="hint"
                >—</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="pager"><span class="pg-total">共 {{ total }} 条</span></div>
    </div>

    <ProtoDrawer :open="createOpen" title="新增计划（草稿）" width="600px" @close="createOpen = false">
      <div class="formrow one">
        <div class="fld">
          <label>计划名称 *</label>
          <input v-model="form.planName" />
        </div>
        <div class="fld">
          <label>SOP 模板</label>
          <select v-model="sopPick" @change="onSopPick">
            <option value="">— 选择已启用模板 —</option>
            <option v-for="sop in sopOptions" :key="sop.id" :value="String(sop.id)">
              {{ sop.sopName }} · v{{ sop.version }}（{{ sop.sopCode }}）
            </option>
          </select>
        </div>
        <div class="fld">
          <label>SOP 模板 id *</label>
          <input v-model.number="form.sopId" type="number" />
          <p class="hint">须为启用版本。下拉与 id 同步，保存即草稿。</p>
        </div>
        <div class="fld">
          <label>IP 组</label>
          <select @change="onIpPick">
            <option value="">— 选择 IP 组，或手工填写 —</option>
            <option v-for="g in ipOptions" :key="g.id" :value="String(g.id)">{{ g.name }}（{{ g.id }}）</option>
          </select>
        </div>
        <div class="fld">
          <label>IP 组 id *</label>
          <input v-model="form.ipGroupIds" placeholder="例如 1 或 1,2" />
        </div>
        <div class="fld">
          <label>开始日期 *</label>
          <input v-model="form.startDate" type="date" />
        </div>
        <div class="fld">
          <label>结束日期 *</label>
          <input v-model="form.endDate" type="date" />
        </div>
        <p v-if="sopLoaded && !sopOptions.length" class="hint" data-testid="plan-sop-empty">
          没有已启用的 SOP 模板。先到 SOP 管理保存模板。
        </p>
        <p v-if="dateError" class="hint bad" data-testid="plan-date-error">{{ dateError }}</p>
      </div>
      <template #footer>
        <button class="btn btn-sec" type="button" @click="createOpen = false">取消</button>
        <button class="btn btn-pri" type="button" :disabled="saving" @click="savePlan">保存草稿</button>
      </template>
    </ProtoDrawer>

    <ProtoDrawer :open="terminateOpen" title="申请终止" width="480px" @close="terminateOpen = false">
      <p>计划「{{ terminateTarget?.planName }}」进入终止待审。原因可留空。</p>
      <div class="fld">
        <label>终止原因</label>
        <textarea v-model="terminateReason" data-testid="plan-terminate-reason-input" rows="3" placeholder="可留空" />
      </div>
      <p class="hint">留空时列表显示「未填写终止原因」。</p>
      <template #footer>
        <button class="btn btn-sec" type="button" @click="terminateOpen = false">取消</button>
        <button class="btn btn-pri" type="button" data-testid="plan-terminate-submit" :disabled="actingId != null" @click="submitTerminate">
          提交申请
        </button>
      </template>
    </ProtoDrawer>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { http, errorMessage } from '../../api/http'
import ProtoDrawer from '../../components/ProtoDrawer.vue'

const rows = ref<any[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const createOpen = ref(false)
const saving = ref(false)
const actingId = ref<number | null>(null)
const form = ref({
  planName: '',
  sopId: 0,
  ipGroupIds: '',
  startDate: '',
  endDate: '',
})
const sopPick = ref('')
const sopLoaded = ref(false)
const dateError = ref('')
const sopOptions = ref<{ id: number; sopName: string; sopCode: string; version: number }[]>([])
const ipOptions = ref<{ id: number; name: string }[]>([])
const terminateOpen = ref(false)
const terminateReason = ref('')
const terminateTarget = ref<{ id: number; planName: string } | null>(null)

function flattenGroups(nodes: { id: number; groupName: string; status: number; children?: unknown[] }[], out: { id: number; name: string }[] = []) {
  for (const node of nodes || []) {
    if (node.status === 1) out.push({ id: node.id, name: node.groupName })
    flattenGroups((node.children || []) as { id: number; groupName: string; status: number; children?: unknown[] }[], out)
  }
  return out
}

function terminateLabel(row: { terminateReason?: string }) {
  const reason = String(row.terminateReason || '').trim()
  return reason || '未填写终止原因'
}

async function loadCreateOptions() {
  sopLoaded.value = false
  try {
    const { data } = await http.get('/content/sop/list', { params: { pageNo: 1, pageSize: 100, status: 'ENABLED' } })
    sopOptions.value = data.data.list || []
  } catch {
    sopOptions.value = []
  } finally {
    sopLoaded.value = true
  }
  try {
    const { data } = await http.get('/ip-group/tree')
    ipOptions.value = flattenGroups(data.data || [])
  } catch {
    ipOptions.value = []
  }
}

function onSopPick() {
  const id = parseInt(sopPick.value, 10)
  if (!Number.isNaN(id) && id > 0) form.value.sopId = id
}

function onIpPick(ev: Event) {
  const id = (ev.target as HTMLSelectElement).value
  if (id) form.value.ipGroupIds = id
}

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await http.get('/content/plan', { params: { pageNo: 1, pageSize: 50 } })
    rows.value = data.data.list
    total.value = data.data.total
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}

function openCreate() {
  form.value = { planName: '', sopId: 0, ipGroupIds: '', startDate: '', endDate: '' }
  sopPick.value = ''
  dateError.value = ''
  sopLoaded.value = false
  createOpen.value = true
  void loadCreateOptions()
}

function parseIpIds(raw: string): number[] {
  return raw
    .split(/[,，\s]+/)
    .map((s) => parseInt(s.trim(), 10))
    .filter((n) => !Number.isNaN(n) && n > 0)
}

async function savePlan() {
  dateError.value = ''
  if (form.value.startDate && form.value.endDate && form.value.endDate < form.value.startDate) {
    dateError.value = '结束日期不能早于开始日期'
    return
  }
  const ipGroupIds = parseIpIds(form.value.ipGroupIds)
  if (!form.value.planName || !form.value.sopId || !ipGroupIds.length || !form.value.startDate || !form.value.endDate) {
    alert('请填写必填项')
    return
  }
  saving.value = true
  try {
    await http.post('/content/plan', {
      planName: form.value.planName,
      sopId: form.value.sopId,
      ipGroupIds,
      startDate: form.value.startDate,
      endDate: form.value.endDate,
    })
    createOpen.value = false
    await loadList()
  } catch (e) {
    alert(errorMessage(e))
  } finally {
    saving.value = false
  }
}

async function startPlan(row: { id: number; planName: string }) {
  if (!confirm(`启动计划「${row.planName}」？将按 SOP 节点生成任务。`)) return
  actingId.value = row.id
  try {
    const { data } = await http.post(`/content/plan/${row.id}/start`)
    const n = data.data?.tasksGenerated ?? 0
    alert(n ? `已启动，生成 ${n} 条任务` : '已启动')
    await loadList()
  } catch (e) {
    alert(errorMessage(e))
  } finally {
    actingId.value = null
  }
}

function requestTerminate(row: { id: number; planName: string }) {
  terminateTarget.value = { id: row.id, planName: row.planName }
  terminateReason.value = ''
  terminateOpen.value = true
}

async function submitTerminate() {
  const target = terminateTarget.value
  if (!target) return
  actingId.value = target.id
  try {
    await http.post(`/content/plan/${target.id}/terminate`, { reason: terminateReason.value.trim() })
    terminateOpen.value = false
    alert('已提交终止申请')
    await loadList()
  } catch (e) {
    alert(errorMessage(e))
  } finally {
    actingId.value = null
  }
}

async function approveTerminate(row: { id: number; planName: string }) {
  if (!confirm(`批准终止计划「${row.planName}」？关联未完成任务将标记 TERMINATED。`)) return
  actingId.value = row.id
  try {
    const { data } = await http.post(`/content/plan/${row.id}/terminate/approve`)
    const n = data.data?.tasksTerminated ?? 0
    alert(n ? `已终止，${n} 条任务已终止` : '计划已终止')
    await loadList()
  } catch (e) {
    alert(errorMessage(e))
  } finally {
    actingId.value = null
  }
}

async function rejectTerminate(row: { id: number; planName: string }) {
  if (!confirm(`驳回终止申请，计划「${row.planName}」恢复执行？`)) return
  actingId.value = row.id
  try {
    await http.post(`/content/plan/${row.id}/terminate/reject`)
    alert('已驳回，计划恢复 IN_PROGRESS')
    await loadList()
  } catch (e) {
    alert(errorMessage(e))
  } finally {
    actingId.value = null
  }
}

loadList()
</script>
