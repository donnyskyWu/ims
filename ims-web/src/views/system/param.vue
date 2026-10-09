<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>系统参数</h1>
        <div class="sub">SYS-005 · key 不改名 · 未知 key 返回 1213</div>
      </div>
    </div>
    <p v-if="error" class="hint bad">{{ error }}</p>
    <form class="qbar" style="margin-bottom: 10px" @submit.prevent>
      <input v-model="keyword" data-testid="param-keyword" placeholder="key / 说明" style="width: 220px" />
      <button class="btn btn-sec btn-sm" type="button" data-testid="param-reset" @click="keyword = ''">重置</button>
    </form>
    <div class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>key（不改名）</th>
              <th>说明</th>
              <th>当前值</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!ready">
              <td colspan="4"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!visible.length">
              <td colspan="4" style="white-space: normal">
                <div class="empty" data-testid="param-empty">
                  <div class="et">{{ error || (keyword.trim() ? '没有匹配的参数' : '没有参数') }}</div>
                  <div v-if="keyword.trim()" class="es">按 key 或说明再筛，未知 key 不能新建。</div>
                </div>
              </td>
            </tr>
            <tr v-for="row in visible" v-else :key="String(row.paramKey)" data-testid="param-row">
              <td class="mono">{{ row.paramKey }}</td>
              <td>{{ row.remark }}</td>
              <td class="mono">{{ displayValue(row) }}</td>
              <td><button class="btn btn-txt" type="button" @click="open(row)">修改</button></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    <ProtoDrawer :open="drawer" title="修改参数" @close="drawer = false">
      <div class="fld" style="margin-bottom: 12px">
        <label>key</label>
        <input :value="editingKey" readonly />
      </div>
      <div class="fld">
        <label>当前值</label>
        <input
          v-model="editingValue"
          :type="editingSecret ? 'password' : 'text'"
          :placeholder="editingSecret ? '留空表示不修改已保存的密钥' : ''"
          autocomplete="off"
        />
      </div>
      <p v-if="saveError" class="hint bad">{{ saveError }}</p>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="drawer = false">取消</button>
        <button class="btn btn-pri" type="button" @click="save">保存</button>
      </template>
    </ProtoDrawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import ProtoDrawer from '../../components/ProtoDrawer.vue'
import { errorMessage, http } from '../../api/http'
import { asList, readData } from '../../api/read'

const rows = ref<Record<string, unknown>[]>([])
const ready = ref(false)
const error = ref('')
const drawer = ref(false)
const saveError = ref('')
const editingKey = ref('')
const editingValue = ref('')
const editingSecret = ref(false)
const keyword = ref('')

const visible = computed(() => {
  const query = keyword.value.trim().toLowerCase()
  if (!query) return rows.value
  return rows.value.filter((row) => {
    const key = String(row.paramKey || '').toLowerCase()
    const remark = String(row.remark || '').toLowerCase()
    return key.includes(query) || remark.includes(query)
  })
})

function displayValue(row: Record<string, unknown>) {
  const v = String(row.paramValue ?? '')
  if (row.secret && v) return v
  return v || '—'
}

async function load() {
  const res = await readData('/system/param')
  ready.value = true
  error.value = res.error
  rows.value = asList(res.data)
}

function open(row: Record<string, unknown>) {
  editingKey.value = String(row.paramKey || '')
  editingSecret.value = !!row.secret
  editingValue.value = editingSecret.value ? '' : String(row.paramValue ?? '')
  saveError.value = ''
  drawer.value = true
}

async function save() {
  saveError.value = ''
  const raw = editingValue.value
  const paramValue = raw === 'true' ? true : raw === 'false' ? false : raw
  try {
    await http.put('/system/param', { paramKey: editingKey.value, paramValue })
    drawer.value = false
    await load()
  } catch (e: unknown) {
    saveError.value = errorMessage(e)
  }
}

onMounted(load)
</script>
