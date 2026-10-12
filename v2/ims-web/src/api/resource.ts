import { BizError, request } from "@/api/http";

export interface PageData<T> {
  list: T[];
  total: number;
}

export async function resourcePage<T>(url: string, params: Record<string, unknown>): Promise<PageData<T>> {
  const data = await request<PageData<T>>({ url, params, silent: true });
  return { list: data.list || [], total: Number(data.total || 0) };
}

export function resourceGet<T>(url: string, params?: Record<string, unknown>): Promise<T> {
  return request<T>({ url, params, silent: true, inDrawer: true });
}

export function resourceSend<T>(method: string, url: string, data?: unknown): Promise<T> {
  return request<T>({ method, url, data, silent: true, inDrawer: true });
}

export async function selectorPage(url: string, keyword: string, pageNo: number) {
  try {
    return await request<PageData<Record<string, unknown>>>({
      url,
      params: { keyword, pageNo, pageSize: 20 },
      silent: true,
    });
  } catch (caught) {
    if ((caught as BizError).code === 1221) return { list: [], total: 0 };
    throw caught;
  }
}

export async function selectorByIds(url: string, ids: string[]) {
  if (!ids.length) return [];
  try {
    const data = await request<PageData<Record<string, unknown>>>({
      url,
      params: { ids: ids.join(","), pageSize: 50 },
      silent: true,
    });
    return data.list || [];
  } catch (caught) {
    if ((caught as BizError).code === 1221) return [];
    throw caught;
  }
}
