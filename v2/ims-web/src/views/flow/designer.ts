export interface FlowNode {
  nodeOrder: number;
  nodeKey: string;
  nodeName: string;
  nodeType: string;
  assigneeRule?: { assignType?: string; targetUserIds?: string[]; permCode?: string; targetDeptId?: string };
  slaHours?: number | null;
  formFields?: { fieldKey: string; fieldLabel: string; fieldType: string; required?: boolean }[];
  conditionExpr?: { expression: string; nextNodeOrder: number }[];
  parallelGroup?: string;
  nextOrders?: number[];
}

export function blankFlow(): FlowNode[] {
  return [
    {
      nodeOrder: 1,
      nodeKey: "start",
      nodeName: "发起",
      nodeType: "START",
      formFields: [{ fieldKey: "title", fieldLabel: "标题", fieldType: "text", required: true }],
      nextOrders: [2],
    },
    {
      nodeOrder: 2,
      nodeKey: "approve",
      nodeName: "审批",
      nodeType: "APPROVE",
      assigneeRule: { assignType: "LEADER" },
      slaHours: 24,
      nextOrders: [3],
    },
    { nodeOrder: 3, nodeKey: "end", nodeName: "结束", nodeType: "END" },
  ];
}

export function layout(nodes: FlowNode[]) {
  const sorted = [...nodes].sort((a, b) => a.nodeOrder - b.nodeOrder);
  const graphNodes = sorted.map((node, index) => ({
    id: String(node.nodeOrder),
    label: node.nodeName || node.nodeKey,
    x: 80 + (index % 4) * 160,
    y: 70 + Math.floor(index / 4) * 90,
  }));
  const edges: { from: string; to: string }[] = [];
  for (const node of sorted) {
    const targets = new Set<number>();
    for (const order of node.nextOrders || []) targets.add(Number(order));
    for (const cond of node.conditionExpr || []) targets.add(Number(cond.nextNodeOrder));
    if (!targets.size) {
      const next = sorted.find((item) => item.nodeOrder > node.nodeOrder);
      if (next) targets.add(next.nodeOrder);
    }
    for (const order of targets) edges.push({ from: String(node.nodeOrder), to: String(order) });
  }
  return { graphNodes, edges };
}
