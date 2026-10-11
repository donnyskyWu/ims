import { defineStore } from 'pinia'
import { http, isSessionInvalidError } from '../api/http'
import { resetSessionExpiry } from '../auth/session'

type Profile = { userId: string; nickname?: string; username?: string }

const PUBLIC_MENU_IDS = new Set(['workbench', 'workbenchTodos', 'workbenchMsgs'])

function readProfile(): Profile | null {
  try {
    const raw = localStorage.getItem('ims_profile')
    return raw ? (JSON.parse(raw) as Profile) : null
  } catch {
    return null
  }
}

function pathname(route: string) {
  return route.split('?')[0]
}

export const useUserStore = defineStore('user', {
  state: () => ({
    accessToken: localStorage.getItem('ims_access') || '',
    refreshToken: localStorage.getItem('ims_refresh') || '',
    profile: readProfile(),
    permCodes: [] as string[],
    permLevels: {} as Record<string, string>,
    routes: [] as string[],
    admin: false,
    fullCatalog: false,
    accessReady: false,
    accessGen: 0,
  }),
  actions: {
    // 无明确权限码即不放行。前端只做展示，安全由后端 fail-closed 保证。
    hasPerm(code: string) {
      if (this.admin || this.fullCatalog) return true
      return this.permCodes.includes(code)
    },
    canWrite(code: string) {
      if (this.admin || this.fullCatalog) return true
      return (this.permLevels[code] || '').includes('W')
    },
    canOpen(path: string) {
      if (this.admin || this.fullCatalog) return true
      const target = pathname(path)
      if (target === '/ims/workbench' || target.startsWith('/ims/workbench/')) return true
      return this.routes.some((route) => {
        const base = pathname(route)
        return target === base || target.startsWith(`${base}/`)
      })
    },
    canSeeMenu(id: string, path: string) {
      if (this.admin || this.fullCatalog) return true
      if (PUBLIC_MENU_IDS.has(id)) return true
      // 侧栏按菜单路由精确匹配。不能用前缀，否则「报表中心」会把「预览与下钻」等下级菜单一并放出来。
      const target = pathname(path)
      return this.routes.some((route) => pathname(route) === target)
    },
    async login(username: string, password: string) {
      const cb = await http.post('/auth/login', { username, password })
      const data = cb.data.data
      this.accessToken = data.accessToken
      this.refreshToken = data.refreshToken
      this.profile = data.profile
      this.accessReady = false
      this.accessGen += 1
      localStorage.setItem('ims_access', this.accessToken)
      localStorage.setItem('ims_refresh', this.refreshToken)
      localStorage.setItem('ims_profile', JSON.stringify(this.profile))
      resetSessionExpiry()
      await this.loadAccess()
    },
    async loadAccess() {
      if (!this.accessToken || this.accessReady) return
      const gen = this.accessGen
      try {
        const res = await http.get('/auth/access')
        if (gen !== this.accessGen) return
        const data = res.data?.data || {}
        this.admin = Boolean(data.admin)
        this.fullCatalog = Boolean(data.fullCatalog)
        this.permCodes = Array.isArray(data.permCodes) ? data.permCodes : []
        this.permLevels = data.permLevels && typeof data.permLevels === 'object' ? data.permLevels : {}
        this.routes = Array.isArray(data.routes) ? data.routes : []
      } catch (error) {
        if (gen !== this.accessGen) return
        if (isSessionInvalidError(error)) {
          this.clearLocalSession()
          return
        }
        this.admin = false
        this.fullCatalog = false
        this.permCodes = []
        this.permLevels = {}
        this.routes = []
      } finally {
        if (gen === this.accessGen) this.accessReady = true
      }
    },
    async ensureProfile() {
      if (!this.refreshToken) return
      const res = await http.post('/auth/sso/refresh', { refreshToken: this.refreshToken })
      this.accessToken = res.data.data.accessToken
      this.profile = res.data.data.userProfile
      localStorage.setItem('ims_access', this.accessToken)
      if (this.profile) localStorage.setItem('ims_profile', JSON.stringify(this.profile))
      this.accessReady = false
      this.accessGen += 1
      resetSessionExpiry()
      await this.loadAccess()
    },
    clearLocalSession() {
      this.accessToken = ''
      this.refreshToken = ''
      this.profile = null
      this.permCodes = []
      this.permLevels = {}
      this.routes = []
      this.admin = false
      this.fullCatalog = false
      this.accessReady = false
      this.accessGen += 1
      localStorage.removeItem('ims_access')
      localStorage.removeItem('ims_refresh')
      localStorage.removeItem('ims_profile')
    },
    async logout() {
      try {
        await http.post('/auth/sso/logout', { refreshToken: this.refreshToken })
      } finally {
        this.clearLocalSession()
      }
    },
  },
})
