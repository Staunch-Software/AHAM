import { createContext, ReactNode, useCallback, useContext, useEffect, useState } from 'react'
import type { Me, PortalKey } from '../types'
import { api, refreshSession, setPortal, tokens } from './api'

interface AuthState {
  portal: PortalKey
  me: Me | null
  loading: boolean
  login: (identifier: string, password: string) => Promise<void>
  logout: () => Promise<void>
  changePassword: (current: string, next: string) => Promise<void>
  can: (...perms: string[]) => boolean
  /** Absolute path inside the current portal: path('entries/1') -> '/manage/entries/1'. */
  path: (p?: string) => string
}
const Ctx = createContext<AuthState>(null as unknown as AuthState)
export const useAuth = () => useContext(Ctx)

/** The sign-in for one portal. The server refuses accounts of another portal ("wrong_portal"). */
export function AuthProvider({ portal, children }: { portal: PortalKey; children: ReactNode }) {
  setPortal(portal)
  const [me, setMe] = useState<Me | null>(null)
  const [loading, setLoading] = useState(true)

  const loadMe = useCallback(async () => {
    const { data } = await api.get<Me>('/auth/me')
    setMe(data)
  }, [])

  useEffect(() => {
    setPortal(portal)
    let alive = true
    ;(async () => {
      try {
        if (tokens.refresh) { await refreshSession(); await loadMe() }
      } catch { tokens.clear() } finally { if (alive) setLoading(false) }
    })()
    const onLogout = () => setMe(null)
    window.addEventListener('fs:logout', onLogout)
    return () => { alive = false; window.removeEventListener('fs:logout', onLogout) }
  }, [portal, loadMe])

  const login = async (identifier: string, password: string) => {
    const { data } = await api.post('/auth/login', { identifier, password, portal })
    tokens.set(data.access_token, data.refresh_token)
    await loadMe()
  }
  const logout = async () => {
    const refresh = tokens.refresh
    try { if (refresh) await api.post('/auth/logout', { refresh_token: refresh }) } catch { /* best effort */ }
    tokens.clear()
    setMe(null)
  }
  const changePassword = async (current: string, next: string) => {
    const { data } = await api.post('/auth/change-password', { current_password: current, new_password: next })
    tokens.set(data.access_token, data.refresh_token)
    await loadMe()
  }
  const can = (...perms: string[]) => !!me && perms.some((p) => me.permissions.includes(p))
  const path = (p = '') => `/${portal}${p ? `/${p}` : ''}`
  return <Ctx.Provider value={{ portal, me, loading, login, logout, changePassword, can, path }}>{children}</Ctx.Provider>
}
