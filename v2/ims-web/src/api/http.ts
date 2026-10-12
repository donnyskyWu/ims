import axios, { type AxiosError, type AxiosInstance, type AxiosRequestConfig, type InternalAxiosRequestConfig } from "axios";
import errorCodes from "./error-codes.json";
import { decidePolicy, networkMessage, type ErrorCodeEntry, type FieldError } from "./error-policy";
import { toast } from "@/utils/toast";

export const API_BASE = "/admin-api/ims";

export class BizError extends Error {
  code: number;
  msg: string;
  data: unknown;
  traceId: string;
  httpStatus: number;

  constructor(code: number, msg: string, data: unknown, traceId = "", httpStatus = 200) {
    super(msg);
    this.name = "BizError";
    this.code = code;
    this.msg = msg;
    this.data = data;
    this.traceId = traceId;
    this.httpStatus = httpStatus;
  }
}

export interface RequestOptions {
  method?: string;
  url: string;
  params?: Record<string, unknown>;
  data?: unknown;
  silent?: boolean;
  inDrawer?: boolean;
  timeout?: number;
  clientToken?: string;
  idempotent?: boolean;
  responseType?: "json" | "blob";
  headers?: Record<string, string>;
}

type FieldHandler = (errors: FieldError[]) => void;
type DrawerHandler = () => void;

const fieldHandlers: FieldHandler[] = [];
const drawerHandlers: DrawerHandler[] = [];
const tokenJar = new Map<string, string>();

export function pushFieldHandler(handler: FieldHandler): () => void {
  fieldHandlers.push(handler);
  return () => {
    const index = fieldHandlers.indexOf(handler);
    if (index >= 0) fieldHandlers.splice(index, 1);
  };
}

export function pushDrawerHandler(handler: DrawerHandler): () => void {
  drawerHandlers.push(handler);
  return () => {
    const index = drawerHandlers.indexOf(handler);
    if (index >= 0) drawerHandlers.splice(index, 1);
  };
}

export function clientToken(key: string): string {
  let token = tokenJar.get(key);
  if (!token) {
    token = crypto.randomUUID();
    tokenJar.set(key, token);
  }
  return token;
}

export function clearClientToken(key: string): void {
  tokenJar.delete(key);
}

let authHeader: () => string | null = () => null;
let refreshAuth: () => Promise<boolean> = async () => false;
let onKick: (message: string) => void = () => undefined;
let onExpired: (message: string) => void = () => undefined;

export function bindSession(hooks: {
  authHeader: () => string | null;
  refresh: () => Promise<boolean>;
  onKick: (message: string) => void;
  onExpired: (message: string) => void;
}): void {
  authHeader = hooks.authHeader;
  refreshAuth = hooks.refresh;
  onKick = hooks.onKick;
  onExpired = hooks.onExpired;
}

const table = errorCodes as ErrorCodeEntry[];
let refreshing: Promise<boolean> | null = null;

function traceId(): string {
  return crypto.randomUUID();
}

function applyDecision(decision: ReturnType<typeof decidePolicy>): void {
  if (decision.fieldErrors?.length) {
    const handler = fieldHandlers[fieldHandlers.length - 1];
    handler?.(decision.fieldErrors);
  }
  if (decision.closeDrawer) drawerHandlers[drawerHandlers.length - 1]?.();
  if (decision.toast) toast.error(decision.toast);
  if (decision.relogin === "kick") onKick(decision.toast || "您的账号已在其他设备登录，本设备已下线");
  if (decision.relogin === "expired") onExpired(decision.toast || "登录已失效，请重新登录");
}

interface RetryConfig extends InternalAxiosRequestConfig {
  _retried?: boolean;
  _silent?: boolean;
  _inDrawer?: boolean;
}

function envelopeOf(payload: unknown): { code: number; msg: string; data: unknown } | null {
  if (!payload || typeof payload !== "object") return null;
  if (!("code" in payload)) return null;
  const body = payload as { code: number; msg?: string; data?: unknown };
  return { code: Number(body.code), msg: String(body.msg || ""), data: body.data };
}

export const http: AxiosInstance = axios.create({
  baseURL: API_BASE,
  timeout: 30_000,
});

http.interceptors.request.use((config) => {
  const next = config as RetryConfig;
  next.headers = next.headers || {};
  const authorization = authHeader();
  if (authorization) next.headers.Authorization = authorization;
  if (!next.headers["X-Trace-Id"]) next.headers["X-Trace-Id"] = traceId();
  return next;
});

async function singleRefresh(): Promise<boolean> {
  if (!refreshing) {
    refreshing = refreshAuth().finally(() => {
      refreshing = null;
    });
  }
  return refreshing;
}

http.interceptors.response.use(
  (response) => {
    if (response.config.responseType === "blob") return response;
    const body = envelopeOf(response.data);
    if (!body) return response;
    const trace = String(response.headers["x-trace-id"] || response.config.headers["X-Trace-Id"] || "");
    if (body.code === 0) {
      response.data = body.data;
      return response;
    }
    const cfg = response.config as RetryConfig;
    const decision = decidePolicy(
      { code: body.code, msg: body.msg, data: body.data, traceId: trace },
      table,
      { silent: cfg._silent, hasForm: fieldHandlers.length > 0, inDrawer: cfg._inDrawer ?? drawerHandlers.length > 0 },
    );
    applyDecision(decision);
    return Promise.reject(new BizError(body.code, body.msg, body.data, trace, response.status));
  },
  async (error: AxiosError) => {
    const cfg = (error.config || {}) as RetryConfig;
    const status = error.response?.status;
    const body = envelopeOf(error.response?.data);
    const trace = String(error.response?.headers?.["x-trace-id"] || cfg.headers?.["X-Trace-Id"] || "");
    if (status === 401 || body?.code === 1002 || body?.code === 1003) {
      const code = body?.code;
      if (code === 1003) {
        const message = body?.msg || "您的账号已在其他设备登录，本设备已下线";
        if (!cfg._silent) toast.error(message);
        onKick(message);
        return Promise.reject(new BizError(1003, message, body?.data, trace, 401));
      }
      const refreshingCall = String(cfg.url || "").includes("refresh-token");
      if (!refreshingCall && !cfg._retried) {
        cfg._retried = true;
        const ok = await singleRefresh();
        if (ok) return http(cfg);
      }
      const message = "登录已失效，请重新登录";
      if (!cfg._silent) toast.error(message);
      onExpired(message);
      return Promise.reject(new BizError(code || 1002, message, body?.data, trace, 401));
    }
    if (body && body.code !== 0) {
      const decision = decidePolicy(
        { code: body.code, msg: body.msg, data: body.data, traceId: trace },
        table,
        { silent: cfg._silent, hasForm: fieldHandlers.length > 0, inDrawer: cfg._inDrawer ?? drawerHandlers.length > 0 },
      );
      applyDecision(decision);
      return Promise.reject(new BizError(body.code, body.msg, body.data, trace, status || 200));
    }
    if (!cfg._silent) toast.error(networkMessage());
    return Promise.reject(new BizError(0, networkMessage(), null, trace, status || 0));
  },
);

export async function request<T>(options: RequestOptions): Promise<T> {
  const timeout = options.timeout ?? (options.responseType === "blob" ? 300_000 : 30_000);
  const headers: Record<string, string> = { ...(options.headers || {}) };
  if (options.clientToken) headers["X-Client-Token"] = options.clientToken;
  const config: AxiosRequestConfig = {
    method: options.method || "GET",
    url: options.url,
    params: options.params,
    data: options.data,
    timeout,
    headers,
    responseType: options.responseType,
  };
  (config as RetryConfig)._silent = options.silent;
  (config as RetryConfig)._inDrawer = options.inDrawer;
  const response = await http.request<T>(config);
  return response.data;
}

export function resetHttpForTests(): void {
  fieldHandlers.splice(0, fieldHandlers.length);
  drawerHandlers.splice(0, drawerHandlers.length);
  tokenJar.clear();
  refreshing = null;
}
