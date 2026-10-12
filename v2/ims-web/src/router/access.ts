import type { RouteLocationNormalized } from "vue-router";
import type { MenuNode } from "@/stores/auth";

export function collectMenuPerms(nodes: MenuNode[]): Set<string> {
  const found = new Set<string>();
  const walk = (list: MenuNode[]) => {
    for (const node of list) {
      if (node.permCode) found.add(node.permCode);
      walk(node.children || []);
    }
  };
  walk(nodes);
  return found;
}

export function routeAllowed(
  to: RouteLocationNormalized,
  menus: MenuNode[],
  permCodes: string[],
): boolean {
  if (to.meta.public || to.meta.menuless) return true;
  const need = typeof to.meta.perm === "string" ? to.meta.perm : "";
  const any = Array.isArray(to.meta.anyPerm) ? (to.meta.anyPerm as string[]) : [];
  if (!need && any.length === 0) return true;
  const owned = collectMenuPerms(menus);
  for (const code of permCodes) owned.add(code);
  if (need) return owned.has(need);
  return any.some((code) => owned.has(code));
}

export function pathForPerm(perm: string | null, routes: { perm?: string; path: string }[]): string {
  if (!perm) return "";
  return routes.find((item) => item.perm === perm)?.path || "";
}
