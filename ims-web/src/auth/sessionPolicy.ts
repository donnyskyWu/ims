export const SESSION_EXPIRED_TOAST = '登录已过期，请重新登录'

export type ApiErrorBody = { code?: number; msg?: string }

/** 登录态失效。业务码 1002 还会表示下载链接过期、重名等，那些不在这里。 */
export function isSessionInvalid(status: number | undefined, body: ApiErrorBody | null | undefined): boolean {
  const msg = body?.msg ?? ''
  if (msg === '会话无效' || msg === '未登录') return true
  if (body?.code === 401) return true
  return status === 401 && msg === ''
}

export function apiErrorBody(data: unknown): ApiErrorBody | undefined {
  if (!data || typeof data !== 'object') return undefined
  const rec = data as { code?: unknown; msg?: unknown }
  return {
    code: typeof rec.code === 'number' ? rec.code : undefined,
    msg: typeof rec.msg === 'string' ? rec.msg : undefined,
  }
}

/** 只接受站内路径，避免把登录回跳做成开放重定向。 */
export function safeInternalRedirect(value: unknown): string {
  const raw = Array.isArray(value) ? value[0] : value
  if (typeof raw !== 'string' || !raw.startsWith('/') || raw.startsWith('//')) return ''
  if (raw.includes('\\') || raw.includes('://')) return ''
  const path = raw.split('?')[0].split('#')[0]
  if (path === '/login' || path.startsWith('/login/')) return ''
  return raw
}

export type SessionSink = {
  onLoginPage: () => boolean
  currentFullPath: () => string
  clearSession: () => void
  toast: (message: string) => void
  redirectToLogin: (redirect: string) => void
}

export function createExpiryGate(sink: SessionSink) {
  let locked = false
  let generation = 0
  return {
    generation() {
      return generation
    },
    reset() {
      locked = false
      generation += 1
    },
    expireFrom(status: number | undefined, body: ApiErrorBody | null | undefined, requestGen?: number): boolean {
      if (!isSessionInvalid(status, body)) return false
      // 登录成功后，过期请求的响应不能清掉新 token。
      if (requestGen !== undefined && requestGen !== generation) return false
      // 已经在登录页时不再清掉刚写入的新 token，也不重复提示。
      if (sink.onLoginPage()) return true
      if (locked) return true
      locked = true
      sink.clearSession()
      sink.toast(SESSION_EXPIRED_TOAST)
      sink.redirectToLogin(safeInternalRedirect(sink.currentFullPath()))
      return true
    },
  }
}
