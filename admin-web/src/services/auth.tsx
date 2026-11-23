import { createContext, ReactNode, useCallback, useContext, useEffect, useState } from 'react'
import type { Me, PortalKey } from '../types'
import { api, getActivePortal, refreshSession, setPortal, tokens } from './api'

interface AuthState {
  portal: PortalKey
  me: Me | null
  loading: boolean
  login: (identifier: string, password: string, explicitPortal?: PortalKey) => Promise<PortalKey>
  logout: () => Promise<void>
  changePassword: (current: string, next: string) => Promise<void>
  can: (...perms: string[]) => boolean
  /** Absolute path inside the current portal: path('entries/1') -> '/manage/entries/1'. */
  path: (p?: string) => string
}

const Ctx = createContext<AuthState>(null as unknown as AuthState)
export const useAuth = () => useContext(Ctx)

function detectPortal(initial?: PortalKey): PortalKey {
  if (initial) return initial
  const fromUrl = window.location.pathname.split('/')[1]
  if (['manage', 'callcentre', 'admin'].includes(fromUrl)) return fromUrl as PortalKey
  const active = getActivePortal()
  if (active && ['manage', 'callcentre', 'admin'].includes(active)) return active as PortalKey
  return 'manage'
}

export function AuthProvider({ portal: initialPortal, children }: { portal?: PortalKey; children: ReactNode }) {
  const [curPortal, setCurPortal] = useState<PortalKey>(() => detectPortal(initialPortal))
  const [me, setMe] = useState<Me | null>(null)
  const [loading, setLoading] = useState(true)

  const loadMe = useCallback(async () => {
    const { data } = await api.get<Me>('/auth/me')
    setMe(data)
    if (data.portal && ['manage', 'callcentre', 'admin'].includes(data.portal)) {
      setCurPortal(data.portal as PortalKey)
      setPortal(data.portal)
    }
  }, [])

  useEffect(() => {
    const p = initialPortal ?? detectPortal()
    setCurPortal(p)
    setPortal(p)
    let alive = true
    ;(async () => {
      try {
        if (tokens.refresh) {
          await refreshSession()
          if (alive) await loadMe()
        }
      } catch {
        tokens.clear()
        if (alive) setMe(null)
      } finally {
        if (alive) setLoading(false)
      }
    })()
    const onLogout = () => {
      setMe(null)
      setLoading(false)
    }
    window.addEventListener('fs:logout', onLogout)
    return () => {
      alive = false
      window.removeEventListener('fs:logout', onLogout)
    }
  }, [initialPortal, loadMe])

  const login = async (identifier: string, password: string, explicitPortal?: PortalKey): Promise<PortalKey> => {
    setLoading(true)
    try {
      const payload: { identifier: string; password: string; portal?: string } = { identifier, password }
      if (explicitPortal) payload.portal = explicitPortal
      const { data } = await api.post('/auth/login', payload)
      const target = (data.portal ?? curPortal) as PortalKey
      setCurPortal(target)
      setPortal(target)
      tokens.set(data.access_token, data.refresh_token)
      await loadMe()
      return target
    } finally {
      setLoading(false)
    }
  }

  const logout = async () => {
    const refresh = tokens.refresh
    try {
      if (refresh) await api.post('/auth/logout', { refresh_token: refresh })
    } catch {
      /* best effort */
    }
    tokens.clear()
    setMe(null)
  }

  const changePassword = async (current: string, next: string) => {
    const { data } = await api.post('/auth/change-password', { current_password: current, new_password: next })
    tokens.set(data.access_token, data.refresh_token)
    await loadMe()
  }

  const can = (...perms: string[]) => !!me && perms.some((p) => me.permissions.includes(p))
  const path = (p = '') => `/${curPortal}${p ? `/${p}` : ''}`

  return (
    <Ctx.Provider value={{ portal: curPortal, me, loading, login, logout, changePassword, can, path }}>
      {children}
    </Ctx.Provider>
  )
}
