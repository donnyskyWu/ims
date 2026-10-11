<template>
  <div v-if="!modelValue.length" class="empty">
    <div class="et">请先选择物理表以加载列</div>
  </div>
  <div v-else class="tbl-wrap field-map-wrap">
    <table class="field-map-table">
      <colgroup>
        <col v-if="showInclude" class="col-include" />
        <col class="col-column" />
        <col class="col-code" />
        <col class="col-display" />
        <col class="col-dtype" />
        <col class="col-query" />
        <col class="col-dict" />
      </colgroup>
      <thead>
        <tr>
          <th v-if="showInclude">启用</th>
          <th>物理列</th>
          <th>fieldCode</th>
          <th>显示名</th>
          <th>数据类型</th>
          <th>查询条件</th>
          <th>字典类型</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(f, idx) in modelValue" :key="`${f.columnName}-${idx}`">
          <td v-if="showInclude">
            <input
              type="checkbox"
              :checked="f.included"
              @change="patch(idx, 'included', ($event.target as HTMLInputElement).checked)"
            />
          </td>
          <td>
            <span v-if="lockColumn && f.columnName" class="mono">{{ f.columnName }}</span>
            <input
              v-else
              :value="f.columnName"
              placeholder="列名"
              class="mono"
              @input="patch(idx, 'columnName', ($event.target as HTMLInputElement).value)"
            />
          </td>
          <td>
            <input
              :value="f.fieldCode"
              placeholder="fieldCode"
              class="mono"
              @input="patch(idx, 'fieldCode', ($event.target as HTMLInputElement).value)"
            />
          </td>
          <td>
            <input
              :value="f.displayName"
              placeholder="显示名"
              @input="patch(idx, 'displayName', ($event.target as HTMLInputElement).value)"
            />
          </td>
          <td>
            <select :value="f.dataType" @change="patch(idx, 'dataType', ($event.target as HTMLSelectElement).value)">
              <option v-for="t in DATA_TYPES" :key="t.value" :value="t.value">{{ t.label }}</option>
            </select>
          </td>
          <td>
            <select
              :value="f.queryConditionType"
              @change="patch(idx, 'queryConditionType', ($event.target as HTMLSelectElement).value)"
            >
              <option v-for="t in QUERY_TYPES" :key="t.value" :value="t.value">{{ t.label }}</option>
            </select>
          </td>
          <td>
            <input
              :value="f.dictType"
              placeholder="dict_xxx"
              class="mono"
              @input="patch(idx, 'dictType', ($event.target as HTMLInputElement).value)"
            />
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
import type { FieldRow } from './types'

const DATA_TYPES = [
  { value: 'STRING', label: '字符串 STRING' },
  { value: 'NUMBER', label: '数值 NUMBER' },
  { value: 'DATETIME', label: '日期时间 DATETIME' },
  { value: 'BOOLEAN', label: '布尔 BOOLEAN' },
]
const QUERY_TYPES = [
  { value: 'EQ', label: '等于 EQ' },
  { value: 'LIKE', label: '模糊 LIKE' },
  { value: 'RANGE', label: '区间 RANGE' },
  { value: 'IN', label: '包含 IN' },
]

const props = defineProps<{
  modelValue: FieldRow[]
  showInclude?: boolean
  lockColumn?: boolean
}>()

const emit = defineEmits<{ 'update:modelValue': [FieldRow[]] }>()

function patch(idx: number, key: keyof FieldRow, val: string | boolean) {
  const next = props.modelValue.map((row, i) => (i === idx ? { ...row, [key]: val } : row))
  emit('update:modelValue', next)
}
</script>

<style scoped>
.field-map-wrap {
  max-height: 420px;
  overflow: auto;
  border: 1px solid var(--line, #e8e8e8);
  border-radius: var(--r-s, 6px);
}
.field-map-table {
  width: 100%;
  table-layout: fixed;
  font-size: 12.5px;
}
.field-map-table th,
.field-map-table td {
  padding: 8px 6px;
  vertical-align: middle;
}
.col-include {
  width: 44px;
}
.col-column {
  width: 120px;
}
.col-code {
  width: 120px;
}
.col-display {
  width: 100px;
}
.col-dtype {
  width: 148px;
  min-width: 148px;
}
.col-query {
  width: 128px;
  min-width: 128px;
}
.col-dict {
  width: 96px;
}
.field-map-table input,
.field-map-table select {
  width: 100%;
  min-width: 0;
  height: 32px;
  font-size: 12.5px;
  box-sizing: border-box;
}
</style>
