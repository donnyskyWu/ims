<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>用户管理</h1>
        <div class="sub">SYS-001 · 手机号由接口脱敏 · GET /system/user/page</div>
      </div>
      <div class="acts">
        <button class="btn btn-pri" type="button" @click="open = true">新建用户</button>
      </div>
    </div>
    <form class="qbar" @submit.prevent="search">
      <input v-model="keyword" placeholder="用户名 / 手机" style="width: 160px" />
      <select v-model="status" style="width: 108px">
        <option value="">全部状态</option>
        <option value="ENABLED">启用</option>
        <option value="DISABLED">停用</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">查询</button>
      <button class="btn btn-sec btn-sm" type="button" @click="reset">重置</button>
    </form>
    <div class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>用户 ID</th>
              <th>用户名</th>
              <th>姓名</th>
              <th>手机</th>
              <th>钉钉</th>
              <th>状态</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="6" style="white-space: normal"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!rows.length">
              <td colspan="6" style="white-space: normal">
                <div class="empty">
                  <div class="et">{{ error || '没有用户' }}</div>
                  <div class="es">列表只展示接口返回的字段</div>
                </div>
              </td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.id">
              <td class="mono num">{{ row.id }}</td>
              <td>{{ row.username || '—' }}</td>
              <td style="font-weight: 500">{{ row.nickname || '—' }}</td>
              <td class="masked">{{ row.mobile || '—' }}</td>
              <td>
                <span class="tag" :style="row.dingtalkUserId ? okStyle : offStyle">
                  <span class="dot"></span>{{ row.dingtalkUserId ? '已绑定' : '未绑定' }}
                </span>
              </td>
              <td>
                <span class="tag" :style="row.status === 'ENABLED' ? okStyle : offStyle">
                  <span class="dot"></span>{{ statusText(row.status) }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="pager">
        <span class="pg-total">共 {{ total }} 条</span>
        <select class="pg-size" :value="pageSize" @change="changeSize">
          <option :value="10">10</option>
          <option :value="20">20</option>
          <option :value="50">50</option>
        </select>
        <span>条/页</span>
        <span class="pg-sp"></span>
        <span class="pg-n" :class="{ dis: pageNo <= 1 }" @click="goto(pageNo - 1)">‹</span>
        <span v-for="n in pageList" :key="n" class="pg-n" :class="{ on: n === pageNo }" @click="goto(n)">{{ n }}</span>
        <span class="pg-n" :class="{ dis: pageNo >= pageCount }" @click="goto(pageNo + 1)">›</span>
      </div>
    </div>
    <ProtoDrawer :open="open" title="新建用户" width="480px" @close="open = false">
      <div class="formrow one"><div class="fld"><label>用户名<i class="req">*</i></label><input v-model="form.username" /></div></div>
      <div class="formrow one"><div class="fld"><label>昵称</label><input v-model="form.nickname" /></div></div>
      <div class="formrow one"><div class="fld"><label>手机</label><input v-model="form.mobile" /></div></div>
      <div class="formrow one"><div class="fld"><label>密码<i class="req">*</i></label><input v-model="form.password" type="password" /></div></div>
      <div v-if="formError" class="hint bad">{{ formError }}</div>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="open = false">取消</button>
        <button class="btn btn-pri" type="button" :disabled="saving" @click="create">{{ saving ? '保存中…' : '保存' }}</button>
      </template>
    </ProtoDrawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import ProtoDrawer from '../../components/ProtoDrawer.vue'
import { http, errorMessage } from '../../api/http'
import { asList, asTotal } from '../../api/read'

type UserRow = {
  id: string
  username: string
  nickname: string
  mobile: string
  status: string
  dingtalkUserId?: string
}

const okStyle = 'background:rgba(52,199,89,.12);color:#1e8e3e'
const offStyle = 'background:rgba(142,142,147,.12);color:#6d6d72'
const rows = ref<UserRow[]>([])
const total = ref(0)
const pageNo = ref(1)
const pageSize = ref(10)
const keyword = ref('')
const status = ref('')
const loading = ref(false)
const error = ref('')
const open = ref(false)
const saving = ref(false)
const formError = ref('')
const form = reactive({ username: '', nickname: '', mobile: '', password: '' })
const pageCount = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))
const pageList = computed(() => {
  const end = Math.min(pageCount.value, Math.max(pageNo.value + 2, 5))
  const start = Math.max(1, end - 4)
  const list: number[] = []
  for (let i = start; i <= Math.min(pageCount.value, start + 4); i += 1) list.push(i)
  return list
})

function statusText(value: string) {
  if (value === 'ENABLED') return '启用'
  if (value === 'DISABLED') return '停用'
  return value || '—'
}

function queryParams() {
  const params: Record<string, string | number> = { pageNo: pageNo.value, pageSize: pageSize.value }
  const text = keyword.value.trim()
  if (text) {
    if (/^\d+$/.test(text)) params.mobile = text
    else params.username = text
  }
  if (status.value) params.status = status.value
  return params
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await http.get('/system/user/page', { params: queryParams() })
    const data = res.data?.data
    rows.value = asList(data) as unknown as UserRow[]
    total.value = asTotal(data, rows.value.length)
  } catch (e: unknown) {
    rows.value = []
    total.value = 0
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}
function search() {
  pageNo.value = 1
  load()
}
function reset() {
  keyword.value = ''
  status.value = ''
  search()
}
function goto(page: number) {
  if (page < 1 || page > pageCount.value || page === pageNo.value) return
  pageNo.value = page
  load()
}
function changeSize(event: Event) {
  pageSize.value = Number((event.target as HTMLSelectElement).value)
  pageNo.value = 1
  load()
}
async function create() {
  formError.value = ''
  if (!form.username.trim() || !form.password) {
    formError.value = '用户名和密码必填'
    return
  }
  saving.value = true
  try {
    await http.post('/system/user', form)
    open.value = false
    form.username = ''
    form.nickname = ''
    form.mobile = ''
    form.password = ''
    load()
  } catch (e: unknown) {
    formError.value = errorMessage(e)
  } finally {
    saving.value = false
  }
}
onMounted(load)
</script>
