import { createContext, ReactNode, useCallback, useContext, useEffect, useState } from 'react'
import { api, refreshSession, tokens } from './api'
import type { Me } from '../types'

interface AuthState {
  me: Me | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
}
const Ctx = createContext<AuthState>(null as unknown as AuthState)
export const useAuth = () => useContext(Ctx)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<Me | null>(null)
  const [loading, setLoading] = useState(true)

  const loadMe = useCallback(async () => {
    const { data } = await api.get<Me>('/auth/me')
    if (data.role !== 'admin') {
      tokens.clear()
      throw new Error('This portal is for administrators only.')
    }
    setMe(data)
  }, [])

  useEffect(() => {
    (async () => {
      try {
        if (tokens.refresh) { await refreshSession(); await loadMe() }
      } catch { tokens.clear() } finally { setLoading(false) }
    })()
    const onLogout = () => setMe(null)
    window.addEventListener('fs:logout', onLogout)
    return () => window.removeEventListener('fs:logout', onLogout)
  }, [loadMe])

  const login = async (email: string, password: string) => {
    const { data } = await api.post('/auth/login', { email, password })
    tokens.set(data.access_token, data.refresh_token)
    await loadMe() // throws (and clears tokens) for non-admin accounts
  }
  const logout = async () => {
    const refresh = tokens.refresh
    try { if (refresh) await api.post('/auth/logout', { refresh_token: refresh }) } catch { /* best effort */ }
    tokens.clear()
    setMe(null)
  }
  return <Ctx.Provider value={{ me, loading, login, logout }}>{children}</Ctx.Provider>
}
