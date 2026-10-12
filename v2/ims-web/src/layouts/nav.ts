import type { MenuNode } from "@/stores/auth";

/** 侧栏只渲染有权限的目录和菜单。按钮不进导航；没有下级的空目录不显示。 */
export function visibleNav(nodes: MenuNode[], permCodes: string[]): MenuNode[] {
  const owned = new Set(permCodes);
  const walk = (list: MenuNode[]): MenuNode[] => {
    const out: MenuNode[] = [];
    for (const node of list) {
      if (node.type === "BUTTON") continue;
      if (node.permCode && !owned.has(node.permCode)) continue;
      const children = walk(node.children || []);
      if (node.type === "DIR" && children.length === 0) continue;
      out.push({ ...node, children });
    }
    return out;
  };
  return walk(nodes);
}
