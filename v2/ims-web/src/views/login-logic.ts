export const SSO_ERROR_CODES = [1002, 1006, 1008, 1216, 1217, 5003] as const;

export interface MenuLike {
  path: string | null;
  children?: MenuLike[];
}

export function ssoErrorText(code: string | null, messages: Record<number, string>): string {
  const value = Number(code || "");
  if (!SSO_ERROR_CODES.includes(value as (typeof SSO_ERROR_CODES)[number])) return "";
  return messages[value] || "登录失败";
}

export function preferredTab(stored: string | null, dingtalkEnabled: boolean): "ding" | "account" {
  if (!dingtalkEnabled) return "account";
  return stored === "account" ? "account" : "ding";
}

export function inDingTalk(ua: string): boolean {
  return /DingTalk/i.test(ua);
}

export function landingPath(menus: MenuLike[], redirect: string): string {
  const safe = redirect.startsWith("/") && !redirect.startsWith("//") ? redirect.split("?")[0] : "";
  if (safe && hasPath(menus, safe)) return safe;
  if (hasPath(menus, "/ims/workbench")) return "/ims/workbench";
  return firstLeaf(menus) || "/";
}

export function hasPath(menus: MenuLike[], path: string): boolean {
  for (const node of menus) {
    if (node.path === path) return true;
    if (node.children && hasPath(node.children, path)) return true;
  }
  return false;
}

function firstLeaf(menus: MenuLike[]): string {
  for (const node of menus) {
    if (node.path && node.path !== "/ims/auth") return node.path;
    const nested = firstLeaf(node.children || []);
    if (nested) return nested;
  }
  return "";
}
