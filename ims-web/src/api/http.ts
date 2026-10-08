import axios from 'axios'

export function errorMessage(error: unknown): string {
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
  const token = localStorage.getItem('ims_access')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

http.interceptors.response.use((res) => {
  const body = res.data
  if (body && typeof body.code === 'number' && body.code !== 0) {
    return Promise.reject(body)
  }
  return res
})
