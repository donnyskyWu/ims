import { request } from "@/api/http";

export type Row = Record<string, unknown>;

export interface PageData<T> {
  list: T[];
  total: number;
}

function clean(params: Record<string, unknown>): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(params)) {
    if (value === "" || value === null || value === undefined) continue;
    out[key] = value;
  }
  return out;
}

export function page<T = Row>(url: string, params: Record<string, unknown> = {}) {
  return request<PageData<T>>({ url, params: clean(params) });
}

export const flowApi = {
  templates: (params: Record<string, unknown>) => page("/flow/template/list", params),
  createTemplate: (data: Row) => request<Row>({ method: "POST", url: "/flow/template", data, inDrawer: true }),
  updateTemplate: (id: string, data: Row) => request<Row>({ method: "PUT", url: `/flow/template/${id}`, data, inDrawer: true }),
  publishTemplate: (id: string) => request<Row>({ method: "POST", url: `/flow/template/${id}/publish`, silent: true }),
  disableTemplate: (id: string) => request<Row>({ method: "POST", url: `/flow/template/${id}/disable`, silent: true }),
  deleteTemplate: (id: string) => request<Row>({ method: "DELETE", url: `/flow/template/${id}`, silent: true }),
  reviseTemplate: (id: string) => request<Row>({ method: "POST", url: `/flow/template/${id}/revise`, silent: true }),
  previewTemplate: (id: string) => request<Row>({ url: `/flow/template/${id}/preview` }),
  startInstance: (data: Row) => request<Row>({ method: "POST", url: "/flow/instance", data, inDrawer: true }),
  myTodo: (params: Record<string, unknown>) => page("/flow/task/my-todo", params),
  myInitiated: (params: Record<string, unknown>) => page("/flow/task/my-initiated", params),
  myHandled: (params: Record<string, unknown>) => page("/flow/task/my-handled", params),
  badge: () => request<{ count: number }>({ url: "/flow/task/badge", silent: true }),
  handle: (id: string, data: Row) => request<Row>({ method: "PUT", url: `/flow/task/${id}/handle`, data, inDrawer: true }),
  transfer: (id: string, data: Row) => request<Row>({ method: "PUT", url: `/flow/task/${id}/transfer`, data, inDrawer: true }),
  board: (params: Record<string, unknown>) => request<Row>({ url: "/flow/instance/board", params: clean(params) }),
  detail: (instanceNo: string) => request<Row>({ url: `/flow/instance/${instanceNo}` }),
  revoke: (instanceNo: string) => request<Row>({ method: "PUT", url: `/flow/instance/${instanceNo}/revoke`, silent: true }),
  versions: (templateId: string) => request<Row[]>({ url: "/flow/version/list", params: { templateId } }),
  diff: (params: Record<string, unknown>) => request<Row>({ url: "/flow/version/diff", params }),
  snapshot: (templateId: string, version: number) => request<Row>({ url: "/flow/version/snapshot", params: { templateId, version } }),
  rollback: (templateId: string, data: Row) => request<Row>({ method: "POST", url: `/flow/version/${templateId}/rollback`, data, inDrawer: true }),
  timeouts: (params: Record<string, unknown>) => page("/flow/timeout/list", params),
  timeoutRate: (statMonth?: string) => request<Row>({ url: "/flow/timeout/rate", params: clean({ statMonth }) }),
  timeoutDistribution: (dimension: string, statMonth?: string) =>
    request<Row[]>({ url: "/flow/timeout/distribution", params: clean({ dimension, statMonth }) }),
  urge: (id: string, urgeMessage: string) => request<Row>({ method: "PUT", url: `/flow/timeout/${id}/urge`, data: { urgeMessage }, silent: true }),
};
