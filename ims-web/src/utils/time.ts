/** 页面时间统一按 Asia/Shanghai，格式 yyyy-MM-dd HH:mm。 */

const SHANGHAI = 'Asia/Shanghai'

function shanghaiParts(date: Date) {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: SHANGHAI,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  }).formatToParts(date)
  const pick = (type: string) => parts.find((item) => item.type === type)?.value || ''
  return { year: pick('year'), month: pick('month'), day: pick('day'), hour: pick('hour'), minute: pick('minute') }
}

/** 带偏移的瞬时换算到北京；没有时区的墙钟按北京时间原样显示。 */
export function formatDateTime(value?: string | null): string {
  const text = String(value || '').trim()
  if (!text) return ''
  if (/^\d{4}-\d{2}-\d{2}$/.test(text)) return text
  const matched = text.match(/^(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2})/)
  if (!matched) return text
  const hasZone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(text)
  if (!hasZone) return `${matched[1]} ${matched[2]}`
  const normalized = text.includes('T') ? text : text.replace(' ', 'T')
  const date = new Date(normalized)
  if (Number.isNaN(date.getTime())) return `${matched[1]} ${matched[2]}`
  const parts = shanghaiParts(date)
  return `${parts.year}-${parts.month}-${parts.day} ${parts.hour}:${parts.minute}`
}

export function shanghaiToday(now = new Date()): string {
  const parts = shanghaiParts(now)
  return `${parts.year}-${parts.month}-${parts.day}`
}

export function shanghaiDateTimeLocal(now = new Date()): string {
  const parts = shanghaiParts(now)
  return `${parts.year}-${parts.month}-${parts.day}T${parts.hour}:${parts.minute}`
}

export function addShanghaiDays(iso: string, days: number): string {
  const [year, month, day] = iso.split('-').map(Number)
  const utc = new Date(Date.UTC(year, month - 1, day))
  utc.setUTCDate(utc.getUTCDate() + days)
  const y = utc.getUTCFullYear()
  const m = String(utc.getUTCMonth() + 1).padStart(2, '0')
  const d = String(utc.getUTCDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

/** datetime-local 按北京时间提交，不跟浏览器时区走。 */
export function datetimeLocalToOffset(value: string): string {
  const text = value.trim()
  if (!text) return ''
  if (/(?:Z|[+-]\d{2}:?\d{2})$/i.test(text)) return text
  if (text.length === 16) return `${text}:00+08:00`
  return `${text}+08:00`
}

export function shiftShanghaiMinutes(local: string, minutes: number): string {
  const ms = Date.parse(datetimeLocalToOffset(local))
  if (!Number.isFinite(ms)) return local
  return shanghaiDateTimeLocal(new Date(ms + minutes * 60 * 1000))
}
