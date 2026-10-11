/** 角色来源与状态的展示文案。接口值仍是 MANUAL / DINGTALK_AUTO / PENDING_CONFIG。 */

export function roleSourceLabel(source: unknown): string {
  if (source === 'MANUAL') return '手工'
  if (source === 'DINGTALK_AUTO') return '钉钉自动'
  return ''
}

export function roleChoiceLabel(role: { roleName?: unknown; source?: unknown; status?: unknown }): string {
  const name = String(role.roleName || '')
  const marks: string[] = []
  const source = roleSourceLabel(role.source)
  if (source) marks.push(source)
  if (role.status === 'PENDING_CONFIG') marks.push('待配置')
  return marks.length ? `${name}（${marks.join(' / ')}）` : name
}
