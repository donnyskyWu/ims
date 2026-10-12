import type { App, Directive, DirectiveBinding } from "vue";
import { useAuthStore } from "@/stores/auth";
import { hasAllPerm, hasAnyPerm, isPermCode, type PermAction } from "@/utils/perm";

type PermEl = HTMLElement & { _permAnchor?: Comment };

function read(binding: DirectiveBinding): { codes: string[]; all: boolean; action?: PermAction } {
  const raw = binding.value;
  const codes = Array.isArray(raw) ? raw.map(String) : [String(raw || "")];
  let action: PermAction | undefined;
  if (binding.modifiers.w) action = "w";
  if (binding.modifiers.d) action = "d";
  return { codes, all: Boolean(binding.modifiers.all), action };
}

function allowed(binding: DirectiveBinding): boolean {
  const { codes, all, action } = read(binding);
  for (const code of codes) {
    if (!isPermCode(code) && import.meta.env.DEV) console.error("权限码格式不正确");
  }
  const auth = useAuthStore();
  const state = { permCodes: auth.permCodes, permDetails: auth.permDetails };
  return all ? hasAllPerm(state, codes, action) : hasAnyPerm(state, codes, action);
}

function hide(el: PermEl) {
  if (!el.parentNode || el._permAnchor) return;
  const anchor = document.createComment("");
  el._permAnchor = anchor;
  el.parentNode.replaceChild(anchor, el);
}

function show(el: PermEl) {
  const anchor = el._permAnchor;
  if (!anchor?.parentNode) return;
  anchor.parentNode.replaceChild(el, anchor);
  el._permAnchor = undefined;
}

export const permDirective: Directive = {
  mounted(el: PermEl, binding) {
    if (!allowed(binding)) hide(el);
  },
  updated(el: PermEl, binding) {
    if (allowed(binding)) show(el);
    else hide(el);
  },
};

export function setupPerm(app: App): void {
  app.directive("perm", permDirective);
}
