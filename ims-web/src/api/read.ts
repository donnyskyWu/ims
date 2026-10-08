import { errorMessage, http } from './http'

export async function readData(url: string, params?: Record<string, unknown>) {
  try {
    const res = await http.get(url, { params })
    return { data: res.data?.data as unknown, error: '' }
  } catch (error) {
    return { data: null, error: errorMessage(error) }
  }
}

export function asList(data: unknown): Record<string, unknown>[] {
  if (Array.isArray(data)) return data as Record<string, unknown>[]
  if (data && typeof data === 'object' && Array.isArray((data as { list?: unknown }).list)) {
    return (data as { list: Record<string, unknown>[] }).list
  }
  return []
}

export function asTotal(data: unknown, fallback: number) {
  if (data && typeof data === 'object' && typeof (data as { total?: unknown }).total === 'number') {
    return (data as { total: number }).total
  }
  return fallback
}

export function cell(row: Record<string, unknown>, keys: string[]) {
  for (const key of keys) {
    const value = row[key]
    if (value !== undefined && value !== null && value !== '') return String(value)
  }
  return '—'
}
