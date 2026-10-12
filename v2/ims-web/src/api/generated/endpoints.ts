import { operations } from "./client";
import { API_BASE, clientToken, request, type RequestOptions } from "../http";

const PREFIX = "/admin-api/ims";

const IDEMPOTENT = new Set(["order_echo_admin_api_ims_demo_order_echo_post"]);

function relative(path: string): string {
  return path.startsWith(PREFIX) ? path.slice(PREFIX.length) : path;
}

const byId = new Map(operations.map((item) => [item.operationId, item]));

export interface CallOptions extends Omit<RequestOptions, "url" | "method" | "data" | "params"> {
  query?: Record<string, unknown>;
  body?: unknown;
  pathParams?: Record<string, string>;
  tokenKey?: string;
}

export function call<T>(operationId: string, options: CallOptions = {}): Promise<T> {
  const found = byId.get(operationId);
  if (!found) return Promise.reject(new Error("未知接口"));
  let path = relative(found.path);
  if (options.pathParams) {
    for (const [key, value] of Object.entries(options.pathParams)) {
      path = path.replace(`{${key}}`, encodeURIComponent(value));
    }
  }
  let token = options.clientToken;
  if (!token && options.tokenKey && (options.idempotent || IDEMPOTENT.has(operationId))) {
    token = clientToken(options.tokenKey);
  }
  return request<T>({
    method: found.method,
    url: path,
    params: options.query,
    data: options.body,
    silent: options.silent,
    inDrawer: options.inDrawer,
    timeout: options.timeout,
    clientToken: token,
    idempotent: options.idempotent || IDEMPOTENT.has(operationId),
    responseType: options.responseType,
    headers: options.headers,
  });
}

/** B0a 功能点约定的字典简表。合并后的接口清单未收录该路径，前端仍按约定调用。 */
export function dictSimpleList<T>(dictType: string, status?: string): Promise<T> {
  return request<T>({
    method: "GET",
    url: "/system/dict-data/simple-list",
    params: { dictType, status },
  });
}

export function dingtalkLoginUrl(redirect: string): string {
  const found = byId.get("sso_redirect_admin_api_ims_auth_sso_dingtalk_redirect_get");
  const path = found ? relative(found.path) : "/auth/sso/dingtalk/redirect";
  return `${API_BASE}${path}?redirect=${encodeURIComponent(redirect)}`;
}

export function uploadFile<T>(scene: string, file: File, tokenKey?: string): Promise<T> {
  const data = new FormData();
  data.append("scene", scene);
  data.append("file", file);
  return call<T>("file_upload_admin_api_ims_file_upload_post", {
    body: data,
    timeout: 300_000,
    headers: { "Content-Type": "multipart/form-data" },
    tokenKey,
    idempotent: Boolean(tokenKey),
  });
}
