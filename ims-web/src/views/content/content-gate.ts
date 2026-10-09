/** ADR-079：内容须到待发布及之后，任务才可完成。与后端 APPROVED_CONTENT_STATUSES 一致。 */
export const APPROVED_CONTENT_STATUSES = new Set([
  'PENDING_PUBLISH',
  'PUBLISHED_DRAFT',
  'FORMALLY_PUBLISHED',
  'PUBLISHED',
  'UNPUBLISHED',
])

export const COMPLETE_GATE_HINT = '内容须审核通过后方可完成任务'

export function contentPassesGate(status: string | undefined | null): boolean {
  return !!status && APPROVED_CONTENT_STATUSES.has(status)
}
