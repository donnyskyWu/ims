import { request } from "./http";

export interface PageData<T> {
  list: T[];
  total: number;
}

export type Row = Record<string, unknown>;

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

export const systemApi = {
  userPage: (params: Record<string, unknown>) => page("/system/user/page", params),
  userGet: (id: string) => request<Row>({ url: `/system/user/${id}` }),
  userSave: (data: Row, editing: boolean) => request<Row>({ method: editing ? "PUT" : "POST", url: "/system/user", data, inDrawer: true }),
  userDelete: (id: string) => request<Row>({ method: "DELETE", url: "/system/user/delete", params: { id }, silent: true }),
  userAction: (id: string, action: string) => request<Row>({ method: action === "reset-password" ? "POST" : "PUT", url: `/system/user/${id}/${action}`, silent: true }),
  userExport: (params: Record<string, unknown>) => request<Row>({ method: "POST", url: "/system/user/export", data: clean(params) }),
  rolePage: (params: Record<string, unknown>) => page("/system/role/page", params),
  roleSave: (data: Row, editing: boolean) => request<Row>({ method: editing ? "PUT" : "POST", url: "/system/role", data, inDrawer: true }),
  roleMenus: (id: string, menuIds: string[]) => request<Row>({ method: "PUT", url: `/system/role/${id}/menus`, data: { menuIds }, silent: true }),
  rolePerms: (id: string, details: Row[]) => request<Row>({ method: "PUT", url: `/system/role/${id}/perm-detail`, data: { details }, silent: true }),
  roleScope: (id: string, dataScope: string) => request<Row>({ method: "PUT", url: `/system/role/${id}/data-scope`, data: { dataScope }, silent: true }),
  roleMembers: (id: string) => request<Row[]>({ url: `/system/role/${id}/members` }),
  roleMemberAdd: (id: string, userId: string) => request<Row>({ method: "POST", url: `/system/role/${id}/members`, data: { userId }, silent: true }),
  roleMemberRemove: (id: string, userId: string) => request<Row>({ method: "DELETE", url: `/system/role/${id}/members/${userId}`, silent: true }),
  roleStatus: (id: string, status: string) => request<Row>({ method: "PUT", url: `/system/role/${id}/status`, data: { status }, silent: true }),
  roleDelete: (id: string, confirmName: string) => request<Row>({ method: "DELETE", url: `/system/role/${id}`, data: { confirmName }, silent: true }),
  rolePreview: (id: string, userId: string) => request<Row>({ method: "POST", url: `/system/role/${id}/preview`, data: { userId }, silent: true }),
  roleFromPosition: (positionCode: string) => request<Row>({ method: "POST", url: "/system/role/from-position", data: { positionCode }, silent: true }),
  menuTree: () => request<Row[]>({ url: "/system/menu/tree" }),
  menuSave: (data: Row, editing: boolean) => request<Row>({ method: editing ? "PUT" : "POST", url: "/system/menu", data, inDrawer: true }),
  menuDelete: (id: string) => request<Row>({ method: "DELETE", url: `/system/menu/${id}`, silent: true }),
  menuVisible: (id: string, visible: boolean) => request<Row>({ method: "PUT", url: `/system/menu/${id}/visible`, data: { visible }, silent: true }),
  dictTypes: () => request<Row[]>({ url: "/system/dict-type/list" }),
  dictTypeCreate: (data: Row) => request<Row>({ method: "POST", url: "/system/dict/type/create", data, inDrawer: true }),
  dictTypeUpdate: (data: Row) => request<Row>({ method: "PUT", url: "/system/dict-type", data, inDrawer: true }),
  dictTypeDelete: (id: string) => request<Row>({ method: "DELETE", url: `/system/dict-type/${id}`, silent: true }),
  dictValues: (dictType: string) => request<Row[]>({ url: "/system/dict-data/list", params: { dictType } }),
  dictValueSave: (data: Row, editing: boolean) => request<Row>({ method: editing ? "PUT" : "POST", url: "/system/dict-data", data, inDrawer: true }),
  dictValueDelete: (id: string) => request<Row>({ method: "DELETE", url: `/system/dict-data/${id}`, silent: true }),
  params: () => request<Row[]>({ url: "/system/param/list" }),
  paramSave: (paramKey: string, value: string) => request<Row>({ method: "PUT", url: "/system/param", data: { paramKey, value }, silent: true }),
  paramHistory: (paramKey: string) => request<Row[]>({ url: "/system/param/history", params: { paramKey } }),
  operatePage: (params: Record<string, unknown>) => page("/system/operate-log/page", params),
  operateDetail: (id: string) => request<Row>({ url: `/system/operate-log/${id}` }),
  loginPage: (params: Record<string, unknown>) => page("/system/login-log/page", params),
  operateExport: (params: Record<string, unknown>) => request<Row>({ method: "POST", url: "/system/operate-log/export", data: clean(params) }),
  loginExport: (params: Record<string, unknown>) => request<Row>({ method: "POST", url: "/system/login-log/export", data: clean(params) }),
  notifyPage: (params: Record<string, unknown>) => page("/system/notify/page", params),
  notifyResend: (id: string) => request<Row>({ method: "POST", url: `/system/notify/${id}/resend`, silent: true }),
  tenantPage: (params: Record<string, unknown>) => page("/system/tenant/page", params),
  tenantSave: (data: Row, id?: string) => request<Row>({ method: id ? "PUT" : "POST", url: id ? `/system/tenant/${id}` : "/system/tenant", data, inDrawer: true }),
  tenantPackage: (id: string, packageId: string) => request<Row>({ method: "PUT", url: `/system/tenant/${id}/package`, data: { packageId }, silent: true }),
  packagePage: (params: Record<string, unknown>) => page("/system/tenant-package/page", params),
  packageSave: (data: Row, id?: string) => request<Row>({ method: id ? "PUT" : "POST", url: id ? `/system/tenant-package/${id}` : "/system/tenant-package", data, inDrawer: true }),
  packageMenus: (id: string, menuIds: string[]) => request<Row>({ method: "PUT", url: `/system/tenant-package/${id}/menus`, data: { menuIds }, silent: true }),
  packageDelete: (id: string, confirmName: string) => request<Row>({ method: "DELETE", url: `/system/tenant-package/${id}`, data: { confirmName }, silent: true }),
  me: () => request<Row>({ url: "/auth/me" }),
  sessions: () => request<Row[]>({ url: "/auth/sessions/my" }),
  dropSession: (sid: string) => request<Row>({ method: "DELETE", url: `/auth/sessions/${sid}`, silent: true }),
};
