<script setup lang="ts">
import { computed } from "vue";
import EmptyState from "./EmptyState.vue";
import StatusTag from "./StatusTag.vue";
import MoneyText from "./MoneyText.vue";
import PercentText from "./PercentText.vue";
import MaskedText from "./MaskedText.vue";
import Perm from "./Perm.vue";
import { fmtTime, emptyText as textOf } from "@/utils/format";

export interface ColumnAction {
  label: string;
  perm?: string;
  danger?: boolean;
  disabled?: (row: Record<string, unknown>) => boolean;
  hint?: (row: Record<string, unknown>) => string;
  onClick: (row: Record<string, unknown>) => void;
}

export interface TableColumn {
  key: string;
  label: string;
  width?: number | string;
  type?: "text" | "mono" | "number" | "money" | "percent" | "status" | "time" | "masked" | "actions";
  dictType?: string;
  sortable?: boolean;
  fixed?: "left" | "right";
  actions?: ColumnAction[];
}

const props = withDefaults(
  defineProps<{
    columns: TableColumn[];
    data: Record<string, unknown>[];
    loading?: boolean;
    selectable?: boolean;
    rowKey?: string;
    emptyType?: "empty" | "noPermission" | "error";
    emptyText?: string;
  }>(),
  { rowKey: "id", loading: false, emptyType: "empty" },
);
const emit = defineEmits<{
  "sort-change": [payload: { sortField: string; sortOrder: string }];
  "selection-change": [rows: Record<string, unknown>[]];
  retry: [];
}>();

const alignOf = (column: TableColumn) => (["number", "money", "percent"].includes(column.type || "") ? "right" : "left");
const scalar = (value: unknown) => value as string | number | null;

function onSort(payload: { prop: string; order: "ascending" | "descending" | null }) {
  if (!payload.order) {
    emit("sort-change", { sortField: "", sortOrder: "" });
    return;
  }
  emit("sort-change", { sortField: payload.prop, sortOrder: payload.order === "ascending" ? "asc" : "desc" });
}

const visibleActions = (column: TableColumn) => (column.actions || []).slice(0, 3);
const moreActions = (column: TableColumn) => (column.actions || []).slice(3);
const showEmpty = computed(() => !props.loading && props.data.length === 0);
</script>

<template>
  <div class="wrap">
    <el-table
      v-loading="loading"
      :data="data"
      :row-key="rowKey"
      @selection-change="emit('selection-change', $event)"
      @sort-change="onSort"
    >
      <el-table-column v-if="selectable" type="selection" width="42" />
      <el-table-column
        v-for="column in columns"
        :key="column.key"
        :prop="column.key"
        :label="column.label"
        :width="column.width"
        :sortable="column.sortable ? 'custom' : false"
        :fixed="column.fixed"
        :align="alignOf(column)"
      >
        <template #default="{ row }">
          <slot :name="`cell-${column.key}`" :row="row">
            <span v-if="column.type === 'mono'" class="mono">{{ textOf(row[column.key]) }}</span>
            <span v-else-if="column.type === 'number'" class="num">{{ textOf(row[column.key]) }}</span>
            <MoneyText v-else-if="column.type === 'money'" :value="scalar(row[column.key])" />
            <PercentText v-else-if="column.type === 'percent'" :value="scalar(row[column.key])" />
            <StatusTag v-else-if="column.type === 'status'" :dict-type="column.dictType || ''" :value="row[column.key] as string" />
            <span v-else-if="column.type === 'time'">{{ fmtTime(row[column.key] as string) }}</span>
            <MaskedText v-else-if="column.type === 'masked'" :value="row[column.key] as string" />
            <span v-else-if="column.type === 'actions'" class="acts">
              <template v-for="action in visibleActions(column)" :key="action.label">
                <Perm v-if="action.perm" :code="action.perm">
                  <button :class="action.danger ? 'btn btn-danger-txt' : 'btn btn-txt'" type="button" :disabled="action.disabled?.(row)" :title="action.hint?.(row) || ''" @click="action.onClick(row)">{{ action.label }}</button>
                </Perm>
                <button v-else :class="action.danger ? 'btn btn-danger-txt' : 'btn btn-txt'" type="button" :disabled="action.disabled?.(row)" :title="action.hint?.(row) || ''" @click="action.onClick(row)">{{ action.label }}</button>
              </template>
              <el-dropdown v-if="moreActions(column).length">
                <button class="btn btn-txt" type="button">更多</button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item v-for="action in moreActions(column)" :key="action.label" @click="action.onClick(row)">
                      {{ action.label }}
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
              <slot name="actions" :row="row" />
            </span>
            <span v-else>{{ textOf(row[column.key]) }}</span>
          </slot>
        </template>
      </el-table-column>
      <template #empty>
        <EmptyState :type="emptyType" :desc="emptyText" @retry="emit('retry')" />
      </template>
    </el-table>
    <EmptyState v-if="showEmpty" :type="emptyType" :desc="emptyText" @retry="emit('retry')" />
  </div>
</template>

<style scoped>
.wrap { background: var(--card); border-radius: var(--r); box-shadow: var(--sh); }
.acts { display: inline-flex; align-items: center; }
</style>
