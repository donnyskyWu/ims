export type InboxRef = {
  refType?: string
  refId?: number
}

/** 与顶栏消息抽屉相同的来源跳转。没有 ref 或未识别的类型不跳。 */
export function messageSourcePath(row: InboxRef): string {
  const ref = row.refType || ''
  const id = Number(row.refId || 0)
  if (!ref || !id) return ''
  if (ref === 'cert_remind' || ref === 'cert_expire') return '/ims/corp/resource/certificate'
  if (ref === 'acct_recharge_verify' || ref === 'acct_transfer') return '/ims/corp/account/douyin'
  if (ref === 'live_report_overdue' || ref === 'live_session' || ref === 'live_alarm') return '/ims/live/sessions'
  return ''
}
