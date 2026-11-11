import * as Network from 'expo-network'
import { createContext, type ReactNode, useCallback, useContext, useEffect, useState } from 'react'
import { api, ApiError, AuthError, NetworkError, onAuthLost, refreshSession, tokens } from './api'
import { kvDelete, kvGet, kvSet } from './db'

export interface Me {
  id: string
  employee_code: string
  full_name: string
  role: string
  role_label: string
  portal: string
  designation: string | null
  branch_name: string | null
  cluster_name: string | null
  region_name: string | null
  company_name: string | null
  spoke: string | null
  must_change_password: boolean
}

type Status = 'loading' | 'signedOut' | 'signedIn'
interface Session {
  status: Status
  me: Me | null
  /** True while the server could not be reached to confirm the session (the app still works offline). */
  offline: boolean
  login: (identifier: string, password: string) => Promise<void>
  logout: () => Promise<void>
  changePassword: (current: string, next: string) => Promise<void>
  reload: () => Promise<void>
}

const Ctx = createContext<Session>(null as unknown as Session)
export const useSession = () => useContext(Ctx)

const PORTAL_NAMES: Record<string, string> = { manage: 'Management portal', callcentre: 'Call-centre portal', admin: 'HR & Admin portal' }

/** Error text for the sign-in screen. */
export function loginMessage(e: unknown): string {
  if (e instanceof NetworkError) return 'Cannot reach the server. Check the internet connection and try again.'
  if (e instanceof ApiError && e.code === 'wrong_portal') {
    return `This app is for Sales Officers. Sign in on the ${PORTAL_NAMES[e.detail.portal] ?? 'web portal'} instead.`
  }
  if (e instanceof ApiError && e.status === 401) return 'Wrong Emp ID or password.'
  if (e instanceof ApiError && e.status === 429) return 'Too many attempts. Wait a few minutes and try again.'
  return (e as Error)?.message ?? 'Sign-in failed'
}

export function SessionProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<{ status: Status; me: Me | null; offline: boolean }>({ status: 'loading', me: null, offline: false })

  const fetchMe = useCallback(async () => {
    const me = await api<Me>('GET', '/auth/me')
    await kvSet('me', me)
    setState({ status: 'signedIn', me, offline: false })
    return me
  }, [])

  useEffect(() => {
    let alive = true
    ;(async () => {
      const cached = await kvGet<Me>('me')
      const refresh = await tokens.getRefresh()
      if (!refresh || !cached) { if (alive) setState({ status: 'signedOut', me: null, offline: false }); return }
      // Signed in before: open straight away (offline works), then confirm with the server.
      if (alive) setState({ status: 'signedIn', me: cached, offline: true })
      try {
        await refreshSession()
        if (alive) await fetchMe()
      } catch (e) {
        if (e instanceof AuthError && alive) setState({ status: 'signedOut', me: null, offline: false })
      }
    })()
    const off = onAuthLost(() => setState({ status: 'signedOut', me: null, offline: false }))
    return () => { alive = false; off() }
  }, [fetchMe])

  // Opened offline: confirm the session (and fresh profile) as soon as the server answers again. The network event
  // covers the phone getting signal back; the timer covers a server that was down while the phone had signal.
  useEffect(() => {
    if (!state.offline) return
    const retry = () => fetchMe().catch((e) => {
      if (e instanceof AuthError) setState({ status: 'signedOut', me: null, offline: false })
    })
    const sub = Network.addNetworkStateListener((n) => { if (n.isConnected && n.isInternetReachable !== false) retry() })
    const timer = setInterval(retry, 30_000)
    return () => { sub.remove(); clearInterval(timer) }
  }, [state.offline, fetchMe])

  const login = async (identifier: string, password: string) => {
    const data = await api<{ access_token: string; refresh_token: string }>('POST', '/auth/login', {
      auth: false, body: { identifier: identifier.trim(), password, portal: 'mobile' },
    })
    await tokens.set(data.access_token, data.refresh_token)
    await fetchMe()
  }
  const logout = async () => {
    const refresh = await tokens.getRefresh()
    try { if (refresh) await api('POST', '/auth/logout', { auth: false, body: { refresh_token: refresh } }) } catch { /* offline: fine */ }
    await tokens.clear()
    await kvDelete('me')  // the entries stay on the phone, tied to their owner
    setState({ status: 'signedOut', me: null, offline: false })
  }
  const changePassword = async (current: string, next: string) => {
    const data = await api<{ access_token: string; refresh_token: string }>('POST', '/auth/change-password', {
      body: { current_password: current, new_password: next },
    })
    await tokens.set(data.access_token, data.refresh_token)
    await fetchMe()
  }
  const reload = async () => { try { await fetchMe() } catch { /* keep the cached profile */ } }

  return <Ctx.Provider value={{ ...state, login, logout, changePassword, reload }}>{children}</Ctx.Provider>
}
