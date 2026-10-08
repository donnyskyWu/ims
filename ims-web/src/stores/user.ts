import { defineStore } from 'pinia'
import { http } from '../api/http'

type Profile = { userId: string; nickname?: string; username?: string }

function readProfile(): Profile | null {
  try {
    const raw = localStorage.getItem('ims_profile')
    return raw ? (JSON.parse(raw) as Profile) : null
  } catch {
    return null
  }
}

export const useUserStore = defineStore('user', {
  state: () => ({
    accessToken: localStorage.getItem('ims_access') || '',
    refreshToken: localStorage.getItem('ims_refresh') || '',
    profile: readProfile(),
    permCodes: [] as string[],
  }),
  actions: {
    // 无明确权限码即不放行。前端只做展示，安全由后端 fail-closed 保证。
    hasPerm(code: string) {
      return this.permCodes.includes(code)
    },
    async login(username: string, password: string) {
      const cb = await http.post('/auth/login', { username, password })
      const data = cb.data.data
      this.accessToken = data.accessToken
      this.refreshToken = data.refreshToken
      this.profile = data.profile
      localStorage.setItem('ims_access', this.accessToken)
      localStorage.setItem('ims_refresh', this.refreshToken)
      localStorage.setItem('ims_profile', JSON.stringify(this.profile))
    },
    async ensureProfile() {
      if (!this.refreshToken) return
      const res = await http.post('/auth/sso/refresh', { refreshToken: this.refreshToken })
      this.accessToken = res.data.data.accessToken
      this.profile = res.data.data.userProfile
      localStorage.setItem('ims_access', this.accessToken)
      if (this.profile) localStorage.setItem('ims_profile', JSON.stringify(this.profile))
    },
    async logout() {
      try {
        await http.post('/auth/sso/logout', { refreshToken: this.refreshToken })
      } finally {
        this.accessToken = ''
        this.refreshToken = ''
        this.profile = null
        this.permCodes = []
        localStorage.removeItem('ims_access')
        localStorage.removeItem('ims_refresh')
        localStorage.removeItem('ims_profile')
      }
    },
  },
})
