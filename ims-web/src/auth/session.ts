import { ElMessage } from 'element-plus'
import { createExpiryGate, SESSION_EXPIRED_TOAST } from './sessionPolicy'

let extraClear: (() => void) | null = null

export function bindSessionCleaner(clear: () => void) {
  extraClear = clear
}

function clearBrowserSession() {
  localStorage.removeItem('ims_access')
  localStorage.removeItem('ims_refresh')
  localStorage.removeItem('ims_profile')
  extraClear?.()
}

export const sessionExpiry = createExpiryGate({
  onLoginPage: () => window.location.pathname === '/login',
  currentFullPath: () => `${window.location.pathname}${window.location.search}`,
  clearSession: clearBrowserSession,
  toast(message) {
    ElMessage.warning({ message, grouping: true })
  },
  redirectToLogin(redirect) {
    void import('../router').then(({ default: router }) => {
      if (router.currentRoute.value.path === '/login') return
      void router.replace({
        path: '/login',
        query: redirect ? { redirect } : {},
      })
    })
  },
})

export function resetSessionExpiry() {
  sessionExpiry.reset()
}

export { SESSION_EXPIRED_TOAST }
