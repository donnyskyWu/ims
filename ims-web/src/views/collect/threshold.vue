<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>阈值规则</h1>
        <div class="sub">UX-M8 §5 · ALERT/MON 只读消费 · 16 COLLECT</div>
      </div>
      <div class="acts">
        <button class="btn btn-pri btn-sm" type="button" data-testid="threshold-create" @click="openCreate">新增规则</button>
      </div>
    </div>
    <div class="tabs" style="margin-bottom: 12px">
      <button
        v-for="c in categories"
        :key="c.value"
        type="button"
        class="btn btn-sm"
        :class="activeCategory === c.value ? 'btn-pri' : 'btn-sec'"
        :data-testid="'threshold-tab-' + c.value"
        @click="switchCategory(c.value)"
      >
        {{ c.label }}
      </button>
    </div>
    <p class="hint" style="margin-bottom: 8px">账号覆盖优先级高于全局阈值。负数和文本不能保存。</p>
    <div class="tbl-block">
      <div class="tbl-wrap">
        <table data-testid="threshold-table">
          <thead>
            <tr>
              <th>名称</th>
              <th>平台</th>
              <th>摘要</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!rows.length && !loading">
              <td colspan="5"><div class="empty"><div class="et">{{ error || '暂无阈值规则' }}</div></div></td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.id">
              <td>{{ row.ruleName || row.metricName || '—' }}</td>
              <td>{{ platformLabel(String(row.platformType || '')) || '全部' }}</td>
              <td style="font-size: 12px">{{ summaryOf(row) }}</td>
              <td>{{ row.status }}</td>
              <td>
                <button class="btn-txt btn" type="button" @click="remove(row)">删除</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    <ProtoDrawer :open="drawerOpen" :title="'新增 · ' + categoryLabel" width="480px" @close="drawerOpen = false">
      <form class="drawer-form" data-testid="threshold-form" @submit.prevent="save">
        <FormField label="名称" :required="activeCategory === 'ALERT'" :error="errors.ruleName">
          <input v-model="form.ruleName" data-testid="threshold-name" />
        </FormField>
        <FormField label="平台">
          <select v-model="form.platformType" data-testid="threshold-platform">
            <option value="">全部</option>
            <option v-for="p in platforms" :key="p.value" :value="p.value">{{ p.label }}</option>
          </select>
        </FormField>
        <template v-if="activeCategory === 'ALERT'">
          <FormField label="指标" required :error="errors.metricName">
            <input v-model="form.metricName" data-testid="threshold-metric" />
          </FormField>
          <FormField label="比较符">
            <select v-model="form.compareOperator" data-testid="threshold-op">
              <option value="GT">大于</option>
              <option value="GTE">大于等于</option>
              <option value="LT">小于</option>
              <option value="LTE">小于等于</option>
              <option value="EQ">等于</option>
            </select>
          </FormField>
          <FormField label="阈值" required :error="errors.thresholdValue">
            <input v-model="form.thresholdValue" data-testid="threshold-value" />
          </FormField>
          <FormField label="通知渠道">
            <input v-model="form.notifyMethods" data-testid="threshold-notify" placeholder="站内 / 钉钉" />
          </FormField>
        </template>
        <template v-else-if="activeCategory === 'FANS'">
          <FormField label="低粉" required :error="errors.lowFans">
            <input v-model="form.lowFans" data-testid="threshold-low-fans" />
          </FormField>
          <FormField label="高粉" required :error="errors.highFans">
            <input v-model="form.highFans" data-testid="threshold-high-fans" />
          </FormField>
        </template>
        <template v-else-if="activeCategory === 'WORK'">
          <FormField label="爆款线" required :error="errors.hotValue">
            <input v-model="form.hotValue" data-testid="threshold-hot" />
          </FormField>
          <FormField label="低分线" required :error="errors.lowValue">
            <input v-model="form.lowValue" data-testid="threshold-low" />
          </FormField>
        </template>
        <template v-else>
          <FormField label="账号" required :error="errors.overrideAccountId">
            <select v-model="form.overrideAccountId" data-testid="threshold-account">
              <option value="">请选择账号</option>
              <option v-for="item in accounts" :key="item.id" :value="item.id">
                {{ item.nickname }}（{{ item.accountNo }}）
              </option>
            </select>
          </FormField>
          <FormField label="覆盖值" required :error="errors.overrideValue">
            <input v-model="form.overrideValue" data-testid="threshold-override" />
          </FormField>
          <p class="hint">账号覆盖优先于同平台全局阈值。</p>
        </template>
        <p v-if="formMsg" class="hint" data-testid="threshold-form-msg">{{ formMsg }}</p>
        <div class="drawer-actions">
          <button class="btn btn-sec" type="button" @click="drawerOpen = false">取消</button>
          <button class="btn btn-pri" type="submit" data-testid="threshold-save">保存</button>
        </div>
      </form>
    </ProtoDrawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { http, errorMessage } from '../../api/http'
import FormField from '../../components/form/FormField.vue'
import { REQUIRED_HINT } from '../../components/form/required'
import { showToast } from '../../components/form/toast'
import ProtoDrawer from '../../components/ProtoDrawer.vue'

const categories = [
  { value: 'ALERT', label: '预警阈值' },
  { value: 'FANS', label: '粉丝阈值' },
  { value: 'WORK', label: '作品阈值' },
  { value: 'OVERRIDE', label: '账号覆盖' },
]
const platforms = [
  { value: 'DOUYIN', label: '抖音' },
  { value: 'KUAISHOU', label: '快手' },
  { value: 'WECHAT_CHANNELS', label: '视频号' },
]
const PLATFORM_LABEL: Record<string, string> = {
  DOUYIN: '抖音',
  KUAISHOU: '快手',
  WECHAT_CHANNELS: '视频号',
  XIAOHONGSHU: '小红书',
}
const activeCategory = ref('ALERT')
const rows = ref<Record<string, any>[]>([])
const loading = ref(false)
const error = ref('')
const drawerOpen = ref(false)
const formMsg = ref('')
const accounts = ref<{ id: string; nickname: string; accountNo: string }[]>([])
const form = reactive({
  ruleName: '',
  platformType: 'DOUYIN',
  metricName: '',
  compareOperator: 'GT',
  thresholdValue: '',
  notifyMethods: '',
  lowFans: '1000',
  highFans: '100000',
  hotValue: '1000000',
  lowValue: '20',
  overrideAccountId: '',
  overrideValue: '',
})
const errors = reactive<Record<string, string>>({})

const categoryLabel = computed(() => categories.find((c) => c.value === activeCategory.value)?.label || activeCategory.value)

function platformLabel(code: string) {
  return PLATFORM_LABEL[code] || code
}

function badNumber(raw: string) {
  const text = raw.trim()
  if (!text) return REQUIRED_HINT
  if (!/^-?\d+(\.\d+)?$/.test(text) && !/^\d+(\.\d+)?w$/i.test(text)) return '阈值须为数字（1001）'
  const n = text.toLowerCase().endsWith('w') ? Number(text.slice(0, -1)) * 10000 : Number(text)
  if (n < 0) return '阈值不能为负数（1001）'
  return ''
}

function summaryOf(row: Record<string, unknown>) {
  if (activeCategory.value === 'ALERT') {
    return `${row.metricName || ''} ${row.compareOperator || ''} ${row.thresholdValue || ''}`.trim()
  }
  if (activeCategory.value === 'FANS') return `低${row.lowFans} / 高${row.highFans}`
  if (activeCategory.value === 'WORK') return `爆${row.hotValue} / 低${row.lowValue}`
  return `账号 ${row.overrideAccountId || '—'} · ${row.overrideValue || '—'}`
}

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const res = await http.get('/collect/threshold/list', {
      params: { thresholdCategory: activeCategory.value },
    })
    rows.value = res.data.data.list || []
  } catch (e) {
    error.value = errorMessage(e)
    rows.value = []
  } finally {
    loading.value = false
  }
}

async function loadAccounts() {
  const merged: { id: string; nickname: string; accountNo: string }[] = []
  for (const platform of platforms) {
    try {
      const res = await http.get('/corp/account/page', {
        params: { platformType: platform.value, pageNo: 1, pageSize: 50 },
      })
      const list = res.data?.data?.list || []
      for (const item of list) {
        merged.push({
          id: String(item.id),
          nickname: item.nickname || item.accountName || item.accountNo,
          accountNo: item.accountNo || item.id,
        })
      }
    } catch {
      /* 某个平台没有账号时覆盖下拉仍可用其他平台 */
    }
  }
  accounts.value = merged
}

function switchCategory(cat: string) {
  activeCategory.value = cat
  loadList()
}

function clearErrors() {
  for (const key of Object.keys(errors)) delete errors[key]
  formMsg.value = ''
}

function openCreate() {
  clearErrors()
  form.ruleName = ''
  form.metricName = ''
  form.thresholdValue = ''
  form.notifyMethods = ''
  form.overrideAccountId = ''
  form.overrideValue = ''
  drawerOpen.value = true
  if (activeCategory.value === 'OVERRIDE' && !accounts.value.length) loadAccounts()
}

function validate(): boolean {
  clearErrors()
  if (activeCategory.value === 'ALERT') {
    if (!form.ruleName.trim() && !form.metricName.trim()) errors.ruleName = REQUIRED_HINT
    if (!form.metricName.trim()) errors.metricName = REQUIRED_HINT
    errors.thresholdValue = badNumber(form.thresholdValue)
  } else if (activeCategory.value === 'FANS') {
    errors.lowFans = badNumber(form.lowFans)
    errors.highFans = badNumber(form.highFans)
  } else if (activeCategory.value === 'WORK') {
    errors.hotValue = badNumber(form.hotValue)
    errors.lowValue = badNumber(form.lowValue)
  } else {
    if (!form.overrideAccountId) errors.overrideAccountId = REQUIRED_HINT
    errors.overrideValue = badNumber(form.overrideValue)
  }
  return !Object.values(errors).some(Boolean)
}

async function save() {
  if (!validate()) return
  const body: Record<string, unknown> = {
    thresholdCategory: activeCategory.value,
    platformType: form.platformType,
    ruleName: form.ruleName.trim(),
    status: 'ENABLED',
  }
  if (activeCategory.value === 'ALERT') {
    body.metricName = form.metricName.trim()
    body.compareOperator = form.compareOperator
    body.thresholdValue = form.thresholdValue.trim()
    body.notifyMethods = form.notifyMethods.trim()
    body.thresholdType = 'NUMBER'
  } else if (activeCategory.value === 'FANS') {
    body.lowFans = Number(form.lowFans)
    body.highFans = Number(form.highFans)
  } else if (activeCategory.value === 'WORK') {
    body.hotValue = form.hotValue.trim()
    body.lowValue = form.lowValue.trim()
  } else {
    body.overrideAccountId = form.overrideAccountId
    body.overrideValue = form.overrideValue.trim()
  }
  try {
    await http.post('/collect/threshold', body)
    drawerOpen.value = false
    showToast('采集配置已保存')
    await loadList()
  } catch (e) {
    formMsg.value = errorMessage(e)
  }
}

async function remove(row: Record<string, unknown>) {
  await http.delete(`/collect/threshold/${row.id}`)
  await loadList()
}

onMounted(() => {
  loadList()
  loadAccounts()
})
</script>

<style scoped>
.drawer-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 16px;
}
</style>
