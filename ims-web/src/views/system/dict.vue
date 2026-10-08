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
        <div class="tbl-wrap">
          <table>
            <thead>
              <tr><th>类型</th><th>名称</th><th>数量</th></tr>
            </thead>
            <tbody>
              <tr v-for="row in types" :key="String(row.dictType)" :class="{ active: row.dictType === current }" @click="pick(String(row.dictType))">
                <td class="mono">{{ row.dictType }}</td>
                <td>{{ row.typeName }}</td>
                <td class="num">{{ row.valueCount }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <div class="tbl-block">
        <div class="tbl-wrap">
          <table>
            <thead>
              <tr><th>标签</th><th>值</th><th>排序</th><th>状态</th><th></th></tr>
            </thead>
            <tbody>
              <tr v-if="!ready">
                <td colspan="5"><div class="empty"><div class="et">加载中</div></div></td>
              </tr>
              <tr v-else-if="!rows.length">
                <td colspan="5"><div class="empty"><div class="et">没有字典项</div></div></td>
              </tr>
              <tr v-for="row in rows" v-else :key="String(row.id)">
                <td>{{ row.dictLabel }}</td>
                <td class="mono">{{ row.dictValue }}</td>
                <td class="num">{{ row.sort }}</td>
                <td>{{ row.status === 'DISABLED' ? '停用' : '启用' }}</td>
                <td><button class="btn btn-txt" type="button" @click="remove(row)">删除</button></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { errorMessage, http } from '../../api/http'
import { asList, readData } from '../../api/read'

const types = ref<Record<string, unknown>[]>([])
const rows = ref<Record<string, unknown>[]>([])
const current = ref('dict_platform_type')
const ready = ref(false)
const error = ref('')

async function loadTypes() {
  const res = await readData('/system/dict-type/list')
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
