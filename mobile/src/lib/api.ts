import { fetch } from 'expo/fetch'
import * as SecureStore from 'expo-secure-store'
import { BUILT_IN_SERVER, REQUEST_TIMEOUT_MS, SERVER_EDITABLE } from './config'
import { kvDelete, kvGet, kvSet } from './db'
import { normalizeServer } from './server'

const REFRESH_KEY = 'sankalp.refresh'
let accessToken: string | null = null
const authLost = new Set<() => void>()

/** Network failure, timeout, 5xx, 429: try again later. */
export class NetworkError extends Error {}
/** The session is gone (refresh token rejected): the user must sign in again. Nothing local is lost. */
export class AuthError extends Error {}
export class ApiError extends Error {
  constructor(public status: number, public detail: any, message?: string) {
    super(message ?? describe(detail) ?? `Request failed (${status})`)
  }
  get code(): string | undefined { return this.detail?.code }
  get retryable() { return this.status >= 500 || this.status === 429 || this.status === 408 }
}

function describe(d: any): string | undefined {
  if (typeof d === 'string') return d
  if (d?.message) return d.message
  if (d?.errors?.length) return d.errors.map((e: any) => e.message).join('; ')
  if (Array.isArray(d) && d[0]?.msg) return d.map((e: any) => String(e.msg).replace(/^Value error, /, '')).join('; ')
  return undefined
}

export const onAuthLost = (fn: () => void) => { authLost.add(fn); return () => { authLost.delete(fn) } }

export const tokens = {
  getRefresh: () => SecureStore.getItemAsync(REFRESH_KEY),
  async set(access: string, refresh: string) { accessToken = access; await SecureStore.setItemAsync(REFRESH_KEY, refresh) },
  async clear() { accessToken = null; await SecureStore.deleteItemAsync(REFRESH_KEY) },
  get access() { return accessToken },
}

type Init = { method: string; headers: Record<string, string>; body?: string | Uint8Array<ArrayBuffer> }

// The phone's own clock reading the last time the server answered. It only moves forward, so a clock set back by
// hand (to put a meeting on an earlier day) shows up: such an entry's Submit time is before it (5.1, "check the time").
const CONTACT_KEY = 'last_server_contact'
let lastContactMs: number | null = null
const loadContact = async () => { lastContactMs ??= (await kvGet<number>(CONTACT_KEY).catch(() => null)) ?? 0; return lastContactMs }

async function noteContact() {
  const known = await loadContact()
  const now = Date.now()
  if (now > known + 60_000) {
    lastContactMs = now
    kvSet(CONTACT_KEY, now).catch(() => {})
  }
}

/** ISO time (phone clock) of the last server answer, sent with each new entry; null before the first contact. */
export async function lastServerContact(): Promise<string | null> {
  const ms = await loadContact()
  return ms ? new Date(ms).toISOString() : null
}

// The server this phone talks to: the address typed on the sign-in or Me screen, else the one built into the app.
const SERVER_KEY = 'server_url'
let server: string | null = null

export async function serverUrl(): Promise<string> {
  return (server ??= (SERVER_EDITABLE ? await kvGet<string>(SERVER_KEY).catch(() => null) : null) || BUILT_IN_SERVER)
}

/** Checks that the server answers at the typed address, then uses it from now on. Blank = the built-in address. */
export async function setServer(input: string): Promise<string> {
  const url = input.trim() ? normalizeServer(input) : BUILT_IN_SERVER
  if (!url) throw new ApiError(0, null, 'Type the PC’s address, for example 192.168.1.20')
  let ok = false
  try { ok = (await rawFetch(`${url}/health`, { method: 'GET', headers: { Accept: 'application/json' } }, 6000)).ok } catch { ok = false }
  if (!ok) throw new NetworkError(`No answer from ${url}. Is the phone on the same Wi-Fi as the PC, and is the server running?`)
  if (url === BUILT_IN_SERVER) await kvDelete(SERVER_KEY); else await kvSet(SERVER_KEY, url)
  server = url
  return url
}

async function rawFetch(url: string, init: Init, timeoutMs: number) {
  const ctl = new AbortController()
  const timer = setTimeout(() => ctl.abort(), timeoutMs)
  try {
    const res = await fetch(url, { ...init, signal: ctl.signal })
    noteContact().catch(() => {})
    return res
  } catch (e) {
    throw new NetworkError((e as Error)?.name === 'AbortError' ? 'The server did not answer in time' : 'No connection to the server')
  } finally {
    clearTimeout(timer)
  }
}

let refreshing: Promise<void> | null = null
/** Trades the stored refresh token for a new pair (single-use rotation on the server). */
export function refreshSession(): Promise<void> {
  refreshing ??= (async () => {
    const refresh = await tokens.getRefresh()
    if (!refresh) throw new AuthError('Not signed in')
    const res = await rawFetch(`${await serverUrl()}/api/v1/auth/refresh`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ refresh_token: refresh }),
    }, REQUEST_TIMEOUT_MS)
    if (res.status === 401) {
      await tokens.clear()
      authLost.forEach((f) => f())
      throw new AuthError('Your session has ended. Sign in again.')
    }
    if (!res.ok) throw new NetworkError(`Server error (${res.status})`)
    const data = await res.json()
    await tokens.set(data.access_token, data.refresh_token)
  })().finally(() => { refreshing = null })
  return refreshing
}

interface Opts { body?: unknown; rawBody?: string | Uint8Array<ArrayBuffer>; headers?: Record<string, string>; timeoutMs?: number; auth?: boolean }

/** JSON API call with bearer auth; a 401 refreshes the session once and retries. */
export async function api<T = any>(method: string, path: string, opts: Opts = {}): Promise<T> {
  const auth = opts.auth ?? true
  const base = `${await serverUrl()}/api/v1`
  const go = async () => {
    const headers: Record<string, string> = { Accept: 'application/json', ...opts.headers }
    if (opts.body !== undefined) headers['Content-Type'] = 'application/json'
    if (auth && tokens.access) headers.Authorization = `Bearer ${tokens.access}`
    return rawFetch(`${base}${path}`, {
      method, headers, body: opts.rawBody ?? (opts.body !== undefined ? JSON.stringify(opts.body) : undefined),
    }, opts.timeoutMs ?? REQUEST_TIMEOUT_MS)
  }
  if (auth && !tokens.access) await refreshSession()
  let res = await go()
  if (res.status === 401 && auth) {
    await refreshSession()
    res = await go()
  }
  const text = await res.text()
  const data = text ? safeJson(text) : null
  if (!res.ok) {
    if (res.status >= 500 || res.status === 429) throw new NetworkError(`Server busy (${res.status})`)
    throw new ApiError(res.status, data?.detail ?? data)
  }
  return data as T
}

const safeJson = (t: string) => { try { return JSON.parse(t) } catch { return t } }
