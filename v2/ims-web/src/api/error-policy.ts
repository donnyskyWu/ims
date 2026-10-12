export interface FieldError {
  field: string;
  message: string;
}

export interface BizBody {
  code: number;
  msg: string;
  data?: unknown;
  traceId?: string;
}

export interface PolicyOptions {
  silent?: boolean;
  hasForm?: boolean;
  inDrawer?: boolean;
}

export interface PolicyDecision {
  toast?: string;
  fieldErrors?: FieldError[];
  closeDrawer?: boolean;
  relogin?: "kick" | "expired";
}

export interface ErrorCodeEntry {
  code: number;
  msg: string;
  strategy: string;
}

function fieldErrorsOf(data: unknown): FieldError[] {
  if (!data || typeof data !== "object") return [];
  const raw = (data as { fieldErrors?: unknown }).fieldErrors;
  if (!Array.isArray(raw)) return [];
  return raw
    .map((item) => {
      if (!item || typeof item !== "object") return null;
      const field = String((item as { field?: string }).field || "");
      const message = String((item as { message?: string }).message || "");
      if (!field) return null;
      return { field, message };
    })
    .filter((item): item is FieldError => item !== null);
}

export function strategyOf(table: ErrorCodeEntry[], code: number): string {
  return table.find((item) => item.code === code)?.strategy || (code >= 5000 && code < 6000 ? "toast" : "toast");
}

export function decidePolicy(body: BizBody, table: ErrorCodeEntry[], options: PolicyOptions = {}): PolicyDecision {
  if (options.silent) return {};
  const strategy = strategyOf(table, body.code);
  if (body.code === 1003 || (strategy === "relogin" && body.code === 1003)) {
    return { relogin: "kick", toast: body.msg || "您的账号已在其他设备登录，本设备已下线" };
  }
  if (body.code === 1002 || strategy === "relogin") {
    return { relogin: "expired", toast: "登录已失效，请重新登录" };
  }
  if (strategy === "fieldError" || body.code === 1001) {
    const fieldErrors = fieldErrorsOf(body.data);
    if (options.hasForm && fieldErrors.length) return { fieldErrors };
    return { toast: body.msg };
  }
  if (strategy === "noPermission" || body.code === 1008) {
    return { toast: "暂无权限" };
  }
  const decision: PolicyDecision = {};
  if (body.code >= 5000 && body.code < 6000) {
    const trace = (body.traceId || "").replace(/-/g, "").slice(0, 8);
    decision.toast = trace ? `${body.msg} 问题编号：${trace}` : body.msg;
  } else {
    decision.toast = body.msg;
  }
  if (body.code === 1504 && options.inDrawer) decision.closeDrawer = true;
  return decision;
}

export function networkMessage(): string {
  return "网络异常，请检查网络后重试";
}
