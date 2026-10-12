<script setup lang="ts">
import { computed, ref } from "vue";
import TraceGraph from "@/components/TraceGraph.vue";
import UserSelect from "@/components/UserSelect.vue";
import DeptTreeSelect from "@/components/DeptTreeSelect.vue";
import { layout, type FlowNode } from "./designer";

const nodes = defineModel<FlowNode[]>({ required: true });
const selected = ref<number | null>(nodes.value[0]?.nodeOrder ?? null);
const current = computed(() => nodes.value.find((item) => item.nodeOrder === selected.value) || null);
const graph = computed(() => layout(nodes.value));
const palette = [
  { nodeType: "APPROVE", nodeName: "审批" },
  { nodeType: "TASK", nodeName: "任务" },
  { nodeType: "CC", nodeName: "抄送" },
  { nodeType: "TIMER", nodeName: "计时" },
];

function pick(id: string) {
  selected.value = Number(id);
}

function add(kind: string, name: string) {
  const order = Math.max(0, ...nodes.value.map((item) => item.nodeOrder)) + 1;
  const end = nodes.value.find((item) => item.nodeType === "END");
  const node: FlowNode = {
    nodeOrder: order,
    nodeKey: `n${order}`,
    nodeName: name,
    nodeType: kind,
    nextOrders: end ? [end.nodeOrder] : [],
  };
  if (kind === "APPROVE" || kind === "TASK") node.assigneeRule = { assignType: "LEADER" };
  if (kind === "CC") node.assigneeRule = { assignType: "USER", targetUserIds: [] };
  if (kind !== "TIMER") node.slaHours = kind === "APPROVE" ? 24 : null;
  const before = nodes.value.filter((item) => item.nodeType !== "END");
  const tail = nodes.value.filter((item) => item.nodeType === "END");
  const previous = before[before.length - 1];
  if (previous && previous.nodeType !== "START") previous.nextOrders = [order];
  if (previous?.nodeType === "START" && (previous.nextOrders || []).every((item) => tail.some((endNode) => endNode.nodeOrder === item))) {
    previous.nextOrders = [order];
  }
  nodes.value = [...before, node, ...tail];
  selected.value = order;
}

function rule() {
  const node = current.value;
  if (!node) return;
  node.assigneeRule = node.assigneeRule || { assignType: "LEADER" };
}

function setUsers(value: string | string[] | null) {
  const node = current.value;
  if (!node) return;
  rule();
  node.assigneeRule!.targetUserIds = Array.isArray(value) ? value : value ? [value] : [];
}

function setDept(value: string | string[] | null) {
  const node = current.value;
  if (!node) return;
  rule();
  node.assigneeRule!.targetDeptId = Array.isArray(value) ? value[0] || "" : value || "";
}

function addField() {
  const node = current.value;
  if (!node) return;
  node.formFields = [...(node.formFields || []), { fieldKey: "", fieldLabel: "", fieldType: "text", required: false }];
}

function addCondition() {
  const node = current.value;
  if (!node) return;
  node.conditionExpr = [...(node.conditionExpr || []), { expression: "", nextNodeOrder: 0 }];
}
</script>

<template>
  <div class="designer">
    <aside class="palette">
      <p>节点</p>
      <button v-for="item in palette" :key="item.nodeType" class="btn btn-sec btn-sm" type="button" @click="add(item.nodeType, item.nodeName)">
        {{ item.nodeName }}
      </button>
    </aside>
    <TraceGraph :nodes="graph.graphNodes" :edges="graph.edges" @node-click="pick" />
    <aside v-if="current" class="props">
      <label>名称<input v-model="current.nodeName" maxlength="64" /></label>
      <label>类型
        <select v-model="current.nodeType">
          <option value="START">开始</option>
          <option value="APPROVE">审批</option>
          <option value="TASK">任务</option>
          <option value="CC">抄送</option>
          <option value="TIMER">计时</option>
          <option value="END">结束</option>
        </select>
      </label>
      <label v-if="current.nodeType === 'APPROVE' || current.nodeType === 'TASK' || current.nodeType === 'CC'">处理人
        <select v-model="current.assigneeRule!.assignType" @focus="rule">
          <option value="USER">指定人</option>
          <option value="LEADER">发起人直属上级</option>
          <option value="PERM">持有权限码</option>
          <option value="DEPT_LEADER">指定部门负责人</option>
        </select>
      </label>
      <UserSelect v-if="current.assigneeRule?.assignType === 'USER'" :model-value="current.assigneeRule.targetUserIds || []" multiple @update:model-value="setUsers" />
      <label v-if="current.assigneeRule?.assignType === 'PERM'">权限码<input v-model="current.assigneeRule.permCode" /></label>
      <DeptTreeSelect v-if="current.assigneeRule?.assignType === 'DEPT_LEADER'" :model-value="current.assigneeRule.targetDeptId || null" @update:model-value="setDept" />
      <label v-if="current.nodeType !== 'END' && current.nodeType !== 'START'">时限（小时）<input v-model.number="current.slaHours" type="number" min="1" /></label>
      <label>并行组<input v-model="current.parallelGroup" placeholder="同组为会签" /></label>
      <div v-if="current.nodeType === 'START'">
        <p>表单字段</p>
        <div v-for="(field, index) in current.formFields || []" :key="index" class="row">
          <input v-model="field.fieldKey" placeholder="字段" />
          <input v-model="field.fieldLabel" placeholder="名称" />
          <label><input v-model="field.required" type="checkbox" />必填</label>
        </div>
        <button class="btn btn-txt" type="button" @click="addField">添加字段</button>
      </div>
      <div>
        <p>条件</p>
        <div v-for="(cond, index) in current.conditionExpr || []" :key="index" class="row">
          <input v-model="cond.expression" placeholder="form.title == '加急'" />
          <input v-model.number="cond.nextNodeOrder" type="number" placeholder="下一节点" />
        </div>
        <button class="btn btn-txt" type="button" @click="addCondition">添加条件</button>
      </div>
    </aside>
  </div>
</template>

<style scoped>
.designer { display: grid; grid-template-columns: 120px 1fr 240px; gap: 12px; align-items: start; }
.palette, .props { display: flex; flex-direction: column; gap: 8px; }
.props label { display: flex; flex-direction: column; gap: 4px; font-size: 12px; }
.row { display: flex; gap: 4px; margin-bottom: 4px; }
input, select { border: 1px solid var(--line2); border-radius: 6px; padding: 4px 6px; }
</style>
