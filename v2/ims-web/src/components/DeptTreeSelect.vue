<script setup lang="ts">
import { computed, onMounted } from "vue";
import { useDeptStore } from "@/stores/dept";
import { findDept, type DeptNode } from "./dept/tree-logic";

const props = withDefaults(
  defineProps<{
    multiple?: boolean;
    onlyEnabled?: boolean;
    checkStrictly?: boolean;
    disabledIds?: string[];
    disableLocal?: boolean;
    placeholder?: string;
  }>(),
  { multiple: false, onlyEnabled: true, checkStrictly: true, placeholder: "请选择部门" },
);
const model = defineModel<string | string[] | null>({ default: null });
const dept = useDeptStore();

onMounted(() => {
  void dept.load();
});

const data = computed(() => decorate(dept.tree));

function decorate(nodes: DeptNode[]): DeptNode[] {
  return nodes
    .filter((node) => (props.onlyEnabled ? node.status !== "DISABLED" : true))
    .filter((node) => node.source !== "SYSTEM")
    .map((node) => ({ ...node, children: decorate(node.children) }));
}

function disabled(id: string): boolean {
  if (props.disabledIds?.includes(id)) return true;
  const node = findDept(dept.tree, id);
  if (!node) return false;
  if (props.onlyEnabled && node.status !== "ENABLED") return true;
  if (node.source === "SYSTEM") return true;
  if (props.disableLocal && node.source === "LOCAL") return true;
  return false;
}
</script>

<template>
  <el-tree-select
    :model-value="model"
    :data="data"
    :multiple="multiple"
    :check-strictly="checkStrictly"
    node-key="id"
    :props="{ label: 'name', children: 'children', disabled: (row: DeptNode) => disabled(row.id) }"
    filterable
    clearable
    :placeholder="placeholder"
    :render-after-expand="false"
    @update:model-value="model = $event"
  />
</template>
