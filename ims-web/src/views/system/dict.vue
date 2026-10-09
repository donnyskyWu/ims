<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>字典管理</h1>
        <div class="sub">SYS-004 · 左类型右数据 · 停用值不可删</div>
      </div>
    </div>
    <p v-if="error" class="hint bad">{{ error }}</p>
    <div class="g2r">
      <div class="tbl-block">
        <form class="qbar" style="margin: 10px 12px" @submit.prevent>
          <input v-model="typeQuery" data-testid="dict-type-filter" placeholder="类型 / 名称" style="width: 180px" />
        </form>
        <div class="tbl-wrap">
          <table>
            <thead>
              <tr><th>类型</th><th>名称</th><th>数量</th></tr>
            </thead>
            <tbody>
              <tr v-if="!typesReady">
                <td colspan="3"><div class="empty"><div class="et">加载中</div></div></td>
              </tr>
              <tr v-else-if="!visibleTypes.length">
                <td colspan="3" style="white-space: normal">
                  <div class="empty" data-testid="dict-type-empty">
                    <div class="et">{{ error || (typeQuery.trim() ? '没有匹配的字典类型' : '没有字典类型') }}</div>
                    <div v-if="typeQuery.trim()" class="es">换一个类型编码或名称再筛。</div>
                  </div>
                </td>
              </tr>
              <tr
                v-for="row in visibleTypes"
                v-else
                :key="String(row.dictType)"
                data-testid="dict-type-row"
                :style="row.dictType === current ? 'background:#f0f6ff' : ''"
                @click="pick(String(row.dictType))"
              >
                <td class="mono">{{ row.dictType }}</td>
                <td>{{ row.typeName }}</td>
                <td class="num">{{ row.valueCount }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <div class="tbl-block">
        <div class="cattabs" data-testid="dict-status-tabs" style="margin: 10px 12px 0">
          <button class="cattab" :class="{ on: valueStatus === '' }" type="button" data-testid="dict-status-all" @click="valueStatus = ''">全部</button>
          <button class="cattab" :class="{ on: valueStatus === 'ENABLED' }" type="button" data-testid="dict-status-enabled" @click="valueStatus = 'ENABLED'">启用</button>
          <button class="cattab" :class="{ on: valueStatus === 'DISABLED' }" type="button" data-testid="dict-status-disabled" @click="valueStatus = 'DISABLED'">停用</button>
        </div>
        <div class="tbl-wrap">
          <table>
            <thead>
              <tr><th>标签</th><th>值</th><th>排序</th><th>状态</th><th></th></tr>
            </thead>
            <tbody>
              <tr v-if="!ready">
                <td colspan="5"><div class="empty"><div class="et">加载中</div></div></td>
              </tr>
              <tr v-else-if="!currentVisible">
                <td colspan="5" style="white-space: normal">
                  <div class="empty" data-testid="dict-value-empty">
                    <div class="et">先从左侧选择字典类型</div>
                  </div>
                </td>
              </tr>
              <tr v-else-if="!visibleRows.length">
                <td colspan="5" style="white-space: normal">
                  <div class="empty" data-testid="dict-value-empty">
                    <div class="et">{{ error || (valueStatus ? '没有该状态的字典项' : '没有字典项') }}</div>
                    <div v-if="valueStatus === 'DISABLED'" class="es">停用值保留在类型里，不能删除。</div>
                  </div>
                </td>
              </tr>
              <tr v-for="row in visibleRows" v-else :key="String(row.id)" data-testid="dict-value-row">
                <td>{{ row.dictLabel }}</td>
                <td class="mono">{{ row.dictValue }}</td>
                <td class="num">{{ row.sort }}</td>
                <td>{{ row.status === 'DISABLED' ? '停用' : '启用' }}</td>
                <td>
                  <button v-if="row.status === 'ENABLED'" class="btn btn-txt" type="button" data-testid="dict-delete" @click="remove(row)">删除</button>
                  <span v-else class="sub" data-testid="dict-disabled-lock">停用不可删</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { errorMessage, http } from '../../api/http'
import { asList, readData } from '../../api/read'

const types = ref<Record<string, unknown>[]>([])
const rows = ref<Record<string, unknown>[]>([])
const current = ref('dict_platform_type')
const ready = ref(false)
const typesReady = ref(false)
const error = ref('')
const typeQuery = ref('')
const valueStatus = ref('')

const visibleTypes = computed(() => {
  const query = typeQuery.value.trim().toLowerCase()
  if (!query) return types.value
  return types.value.filter((row) => {
    const code = String(row.dictType || '').toLowerCase()
    const name = String(row.typeName || '').toLowerCase()
    return code.includes(query) || name.includes(query)
  })
})

const currentVisible = computed(() => visibleTypes.value.some((row) => row.dictType === current.value))

const visibleRows = computed(() => {
  if (!valueStatus.value) return rows.value
  return rows.value.filter((row) => row.status === valueStatus.value)
})

async function loadTypes() {
  const res = await readData('/system/dict-type/list')
  typesReady.value = true
  error.value = res.error
  types.value = asList(res.data)
}

async function loadData() {
  ready.value = false
  const res = await readData('/system/dict-data/list', { dictType: current.value })
  ready.value = true
  error.value = res.error
  rows.value = asList(res.data)
}

async function pick(dictType: string) {
  current.value = dictType
  await loadData()
}

async function remove(row: Record<string, unknown>) {
  error.value = ''
  if (row.status !== 'ENABLED') {
    error.value = '停用值不可删'
    return
  }
  try {
    await http.delete(`/system/dict-data/${row.id}`)
    await loadTypes()
    await loadData()
  } catch (e: unknown) {
    error.value = errorMessage(e)
  }
}

onMounted(async () => {
  await loadTypes()
  await loadData()
})
</script>
