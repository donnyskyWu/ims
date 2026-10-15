export const REQUIRED_HINT = '必填项，请填写'

export function requiredError(value: unknown): string {
  if (value === null || value === undefined) return REQUIRED_HINT
  if (typeof value === 'number') {
    return Number.isFinite(value) ? '' : REQUIRED_HINT
  }
  const text = String(value).trim()
  if (!text || text === 'NaN') return REQUIRED_HINT
  return ''
}

/** 选择器主键：0、空、NaN 都视为未填。 */
export function requiredId(value: unknown): string {
  if (value === null || value === undefined || value === '') return REQUIRED_HINT
  const n = typeof value === 'number' ? value : Number(value)
  if (!Number.isFinite(n) || n <= 0) return REQUIRED_HINT
  return ''
}
