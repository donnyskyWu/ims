export function showToast(message: string, kind: 'success' | 'warn' | 'error' = 'success') {
  let host = document.querySelector('.toasts')
  if (!host) {
    host = document.createElement('div')
    host.className = 'toasts'
    document.body.appendChild(host)
  }
  const el = document.createElement('div')
  el.className = `toast t-${kind}`
  el.dataset.testid = 'app-toast'
  el.textContent = message
  host.appendChild(el)
  window.setTimeout(() => {
    el.classList.add('out')
    window.setTimeout(() => el.remove(), 280)
  }, 2400)
}
