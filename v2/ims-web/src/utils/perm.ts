export type PermAction = "r" | "w" | "d";

export interface PermDetail {
  r?: boolean | number;
  w?: boolean | number;
  d?: boolean | number;
}

export interface PermState {
  permCodes: string[];
  permDetails: Record<string, PermDetail>;
}

const PERM_RE = /^ims:[a-z0-9-]+:[a-z0-9-]+:[a-z0-9-]+$/;

export function isPermCode(value: string): boolean {
  return PERM_RE.test(value);
}

function flag(value: boolean | number | undefined): boolean {
  return value === true || value === 1;
}

export function hasPerm(state: PermState, code: string, action?: PermAction): boolean {
  if (!state.permCodes.includes(code)) return false;
  if (!action) return true;
  const detail = state.permDetails[code];
  if (!detail) return true;
  if (action === "r") return flag(detail.r) || flag(detail.w) || flag(detail.d);
  if (action === "w") return flag(detail.w);
  return flag(detail.d);
}

export function hasAnyPerm(state: PermState, codes: string[], action?: PermAction): boolean {
  return codes.some((code) => hasPerm(state, code, action));
}

export function hasAllPerm(state: PermState, codes: string[], action?: PermAction): boolean {
  return codes.length > 0 && codes.every((code) => hasPerm(state, code, action));
}
