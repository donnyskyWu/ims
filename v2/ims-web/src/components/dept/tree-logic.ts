export interface DeptNode {
  id: string;
  parentId: string;
  name: string;
  source: string;
  status: string;
  localOrphan: number;
  memberCount: number;
  directMemberCount: number;
  leaderUserId: string;
  children: DeptNode[];
}

export function textId(value: unknown): string {
  if (value === null || value === undefined || value === "") return "";
  return String(value);
}

export function normalizeDept(raw: unknown): DeptNode {
  const row = raw as Record<string, unknown>;
  const children = Array.isArray(row.children) ? row.children.map((item) => normalizeDept(item)) : [];
  return {
    id: textId(row.id),
    parentId: textId(row.parentId),
    name: String(row.name || ""),
    source: String(row.source || ""),
    status: String(row.status || "ENABLED"),
    localOrphan: Number(row.localOrphan || 0),
    memberCount: Number(row.memberCount || 0),
    directMemberCount: Number(row.directMemberCount || 0),
    leaderUserId: textId(row.leaderUserId),
    children,
  };
}

export function flattenDept(nodes: DeptNode[], acc: DeptNode[] = []): DeptNode[] {
  for (const node of nodes) {
    acc.push(node);
    flattenDept(node.children, acc);
  }
  return acc;
}

export function findDept(nodes: DeptNode[], id: string | null): DeptNode | null {
  if (!id) return null;
  for (const node of nodes) {
    if (node.id === id) return node;
    const child = findDept(node.children, id);
    if (child) return child;
  }
  return null;
}

export function deptPath(nodes: DeptNode[], id: string | null): DeptNode[] {
  if (!id) return [];
  const walk = (list: DeptNode[], trail: DeptNode[]): DeptNode[] | null => {
    for (const node of list) {
      const next = [...trail, node];
      if (node.id === id) return next;
      const found = walk(node.children, next);
      if (found) return found;
    }
    return null;
  };
  return walk(nodes, []) || [];
}

export function descendantIds(node: DeptNode | null): Set<string> {
  const ids = new Set<string>();
  if (!node) return ids;
  const walk = (current: DeptNode) => {
    ids.add(current.id);
    current.children.forEach(walk);
  };
  walk(node);
  return ids;
}

export function filterDeptTree(nodes: DeptNode[], keyword: string): DeptNode[] {
  const text = keyword.trim();
  if (!text) return nodes;
  const visit = (node: DeptNode): DeptNode | null => {
    const children = node.children.map(visit).filter((item): item is DeptNode => item !== null);
    if (node.name.includes(text) || children.length) return { ...node, children };
    return null;
  };
  return nodes.map(visit).filter((item): item is DeptNode => item !== null);
}

export function defaultExpanded(nodes: DeptNode[]): string[] {
  return nodes.map((node) => node.id);
}

export function ancestorIds(nodes: DeptNode[], id: string | null): string[] {
  return deptPath(nodes, id)
    .slice(0, -1)
    .map((node) => node.id);
}

export interface DropCheck {
  ok: boolean;
  reason?: string;
}

export function canMoveDept(nodes: DeptNode[], sourceId: string, targetId: string): DropCheck {
  const source = findDept(nodes, sourceId);
  const target = findDept(nodes, targetId);
  if (!source || !target) return { ok: false, reason: "部门不存在" };
  if (source.id === target.id || descendantIds(source).has(target.id)) {
    return { ok: false, reason: "部门不能移动到自身或下级部门之下" };
  }
  if (target.source === "SYSTEM") return { ok: false, reason: "不能移动到待分配部门" };
  if (source.source === "DINGTALK" && target.source === "LOCAL") {
    return { ok: false, reason: "钉钉部门不能移到本地部门下" };
  }
  return { ok: true };
}

export function fallbackSelection(nodes: DeptNode[], selectedId: string | null, showDisabled: boolean): string | null {
  if (!selectedId) return null;
  const path = deptPath(nodes, selectedId);
  const current = path[path.length - 1];
  const hidden = current && current.status === "DISABLED" && !showDisabled;
  if (current && !hidden) return selectedId;
  const ancestors = path.slice(0, -1).reverse();
  for (const node of ancestors) {
    if (node.status === "DISABLED" && !showDisabled) continue;
    return node.id;
  }
  return null;
}

export function isPendingDept(node: DeptNode | null): boolean {
  return Boolean(node && node.source === "SYSTEM");
}
