import axios from 'axios'
import { apiErrorBody, isSessionInvalid } from '../auth/sessionPolicy'
import { sessionExpiry } from '../auth/session'

export function isSessionInvalidError(error: unknown): boolean {
  if (axios.isAxiosError(error)) {
    return isSessionInvalid(error.response?.status, apiErrorBody(error.response?.data))
  }
  return isSessionInvalid(undefined, apiErrorBody(error))
}

const SESSION_CHECKED = Symbol.for('ims.sessionChecked')

function requestGenOf(config: unknown): number | undefined {
  if (!config || typeof config !== 'object' || !('sessionGen' in config)) return undefined
  const value = (config as { sessionGen?: unknown }).sessionGen
  return typeof value === 'number' ? value : undefined
}

function markSessionChecked(target: unknown) {
  if (target && typeof target === 'object') {
    Object.defineProperty(target, SESSION_CHECKED, { value: true })
  }
}

function notifySessionExpiry(status: number | undefined, data: unknown, requestGen?: number) {
  sessionExpiry.expireFrom(status, apiErrorBody(data), requestGen)
}

export function errorMessage(error: unknown): string {
  if (!(error && typeof error === 'object' && SESSION_CHECKED in error)) {
    if (axios.isAxiosError(error)) {
      notifySessionExpiry(error.response?.status, error.response?.data, requestGenOf(error.config))
    } else {
      notifySessionExpiry(undefined, error)
    }
  }
  if (axios.isAxiosError(error)) {
    const status = error.response?.status
    const data = error.response?.data as { msg?: string } | undefined
    if (status === 404) return '接口尚未提供'
    if (data?.msg) return data.msg
    if (status) return `请求失败（${status}）`
    return '网络异常'
  }
  if (error && typeof error === 'object' && 'msg' in error) {
    const msg = (error as { msg?: string }).msg
    if (msg) return msg
  }
  return '加载失败'
}

export const http = axios.create({ baseURL: '/admin-api/ims', timeout: 15000 })

http.interceptors.request.use((config) => {
  ;(config as { sessionGen?: number }).sessionGen = sessionExpiry.generation()
  const token = localStorage.getItem('ims_access')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

http.interceptors.response.use(
  (res) => {
    const body = res.data
    if (body && typeof body.code === 'number' && body.code !== 0) {
      notifySessionExpiry(res.status, body, requestGenOf(res.config))
      markSessionChecked(body)
      return Promise.reject(body)
    }
    return res
  },
  (error) => {
    if (axios.isAxiosError(error)) {
      notifySessionExpiry(error.response?.status, error.response?.data, requestGenOf(error.config))
      markSessionChecked(error)
    }
    return Promise.reject(error)
  },
)
