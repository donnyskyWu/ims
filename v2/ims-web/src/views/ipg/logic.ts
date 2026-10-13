export interface GroupNode {
  id: string;
  groupName: string;
  groupType?: string;
  parentId?: string | null;
  parentName?: string;
  leaderUserId?: string | null;
  leaderName?: string;
  level?: string;
  status?: string;
  sortOrder?: number;
  remark?: string;
  createTime?: string;
  updateTime?: string;
  memberCount?: number;
  accountCount?: number;
  authorCount?: number;
  readonly?: boolean;
  children?: GroupNode[];
}

export interface FlatGroup extends GroupNode {
  depth: number;
  hit: boolean;
}

function matches(node: GroupNode, keyword: string): boolean {
  if (!keyword) return true;
  const name = (node.groupName || "").toLowerCase();
  if (name.includes(keyword)) return true;
  return (node.children || []).some((child) => matches(child, keyword));
}

/** 组名模糊搜索。命中小组时保留父大组，并只高亮名称命中的节点。 */
export function flattenGroups(nodes: GroupNode[], keyword = ""): FlatGroup[] {
  const key = keyword.trim().toLowerCase();
  const rows: FlatGroup[] = [];
  const walk = (list: GroupNode[], depth: number) => {
    for (const node of list) {
      if (!matches(node, key)) continue;
      const hit = !!key && (node.groupName || "").toLowerCase().includes(key);
      rows.push({ ...node, depth, hit, children: undefined });
      walk(node.children || [], depth + 1);
    }
  };
  walk(nodes, 0);
  return rows;
}

export function nodeText(node: GroupNode): string {
  const level = node.level ? ` [${node.level}级]` : "";
  const members = node.memberCount ?? 0;
  const accounts = node.accountCount ?? 0;
  const authors = node.authorCount ?? 0;
  return `${node.groupName} (${members}/${accounts}/${authors})${level}`;
}
