/** 采集健康空态：未返回、未绑定、未探活都要有可见文案。 */
export function healthText(label?: string | null): string {
  const text = (label || '').trim()
  return text || '未探活'
}

export function healthIsEmpty(label?: string | null): boolean {
  const text = healthText(label)
  return text === '未探活' || text === '未绑定'
}
