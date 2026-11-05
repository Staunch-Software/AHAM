import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios'

let accessToken: string | null = null
let portal = 'admin'
const refreshKey = () => `sankalp_refresh_${portal}`

/** Each portal keeps its own session (refresh token), so a browser can be signed in to two portals in two tabs. */
export function setPortal(p: string) {
  if (p !== portal) accessToken = null
  portal = p
}

// Access token lives in memory only; the refresh token is kept in localStorage so a reload keeps the session.
export const tokens = {
  get access() { return accessToken },
  get refresh() { try { return localStorage.getItem(refreshKey()) } catch { return null } },
  set(access: string, refresh: string) {
    accessToken = access
    try { localStorage.setItem(refreshKey(), refresh) } catch { /* storage unavailable */ }
  },
  clear() {
    accessToken = null
    try { localStorage.removeItem(refreshKey()) } catch { /* ignore */ }
  },
}

export const API_BASE = `${import.meta.env.VITE_API_URL ?? ''}/api/v1`
export const api = axios.create({ baseURL: API_BASE })

api.interceptors.request.use((cfg) => {
  if (tokens.access) cfg.headers.Authorization = `Bearer ${tokens.access}`
  return cfg
})

let refreshing: Promise<void> | null = null
export function refreshSession(): Promise<void> {
  if (!refreshing) {
    refreshing = (async () => {
      const refresh = tokens.refresh
      if (!refresh) throw new Error('no refresh token')
      const { data } = await axios.post(`${API_BASE}/auth/refresh`, { refresh_token: refresh })
      tokens.set(data.access_token, data.refresh_token)
    })().finally(() => { refreshing = null })
  }
  return refreshing
}

api.interceptors.response.use(undefined, async (err: AxiosError) => {
  const cfg = err.config as (InternalAxiosRequestConfig & { _retried?: boolean }) | undefined
  if (err.response?.status === 401 && cfg && !cfg._retried && !cfg.url?.startsWith('/auth/login')) {
    cfg._retried = true
    try {
      await refreshSession()
      return api(cfg)
    } catch {
      tokens.clear()
      window.dispatchEvent(new Event('fs:logout'))
    }
  }
  return Promise.reject(err)
})

export function errorMessage(e: unknown): string {
  const d = (e as AxiosError<any>)?.response?.data?.detail
  if (typeof d === 'string') return d
  if (d?.message) return d.message
  if (d?.errors?.[0]?.message) return d.errors.map((x: any) => x.message).join('; ')
  if (Array.isArray(d) && d[0]?.msg) return d.map((x: any) => String(x.msg).replace(/^Value error, /, '')).join('; ')
  if (Array.isArray(d) && d[0]?.message) return d.map((x: any) => x.message).join('; ')
  return (e as Error)?.message ?? 'Something went wrong'
}

/** Saves a file returned by an authenticated GET (CSV exports, templates). */
export async function download(url: string, params: Record<string, unknown>, filename: string) {
  const res = await api.get(url, { params, responseType: 'blob' })
  const href = URL.createObjectURL(res.data as Blob)
  const a = document.createElement('a')
  a.href = href
  a.download = filename
  a.click()
  setTimeout(() => URL.revokeObjectURL(href), 1000)
}
