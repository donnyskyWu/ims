/** 复用绩效结果导出：服务端 CSV + X-Export-Rows。 */

export async function downloadAdminCsv(
  path: string,
  params: Record<string, string | number | null | undefined>,
  filename: string,
): Promise<{ ok: boolean; count: number; message: string }> {
  const query = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value === '' || value == null) continue
    query.set(key, String(value))
  }
  const suffix = query.toString()
  const token = localStorage.getItem('ims_access')
  const res = await fetch(`/admin-api/ims${path}${suffix ? `?${suffix}` : ''}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!res.ok) return { ok: false, count: 0, message: `导出失败（${res.status}）` }
  const contentType = res.headers.get('content-type') || ''
  if (contentType.includes('application/json')) {
    const body = (await res.json()) as { msg?: string }
    return { ok: false, count: 0, message: body.msg || '导出失败' }
  }
  const count = Number(res.headers.get('X-Export-Rows') || '0')
  const blob = await res.blob()
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = filename
  link.click()
  URL.revokeObjectURL(link.href)
  return { ok: true, count, message: count === 0 ? '当前筛选没有数据，已导出空表' : `已导出 ${count} 条` }
}

export function downloadRowsCsv(filename: string, header: string[], rows: Array<Array<string | number>>) {
  const lines = [header, ...rows].map((cells) => cells.map((cell) => `"${String(cell).replaceAll('"', '""')}"`).join(','))
  const blob = new Blob(['\ufeff' + lines.join('\n')], { type: 'text/csv;charset=utf-8' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = filename
  link.click()
  URL.revokeObjectURL(link.href)
  return rows.length
}
