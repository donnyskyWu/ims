type Listener = () => void

const listeners = new Set<Listener>()

/** 顶栏角标与工作台消息区共用：已读/全部已读后互相刷新。 */
export function onInboxChanged(fn: Listener) {
  listeners.add(fn)
  return () => listeners.delete(fn)
}

export function notifyInboxChanged() {
  for (const fn of listeners) fn()
}
