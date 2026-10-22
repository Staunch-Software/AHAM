import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'
import App, { makeQueryClient } from '../src/app/App'

export type Handler = (url: string, cfg?: any) => any
export const handlers: { get: Handler; post: Handler; patch: Handler; put: Handler } = {
  get: () => { throw new Error('unhandled GET') },
  post: () => { throw new Error('unhandled POST') },
  patch: () => { throw new Error('unhandled PATCH') },
  put: () => { throw new Error('unhandled PUT') },
}
export const calls: { method: string; url: string; cfg?: any }[] = []

export class FakeEventSource {
  static instances: FakeEventSource[] = []
  listeners: Record<string, (() => void)[]> = {}
  onopen: (() => void) | null = null
  onerror: (() => void) | null = null
  closed = false
  constructor(public url: string) { FakeEventSource.instances.push(this) }
  addEventListener(t: string, fn: () => void) { (this.listeners[t] ??= []).push(fn) }
  emit(t: string) { (this.listeners[t] ?? []).forEach((f) => f()) }
  close() { this.closed = true }
}

export const adminMe = { id: 'u1', company_id: 'c1', full_name: 'Ada Admin', email: 'a@x.io', role: 'admin', branch_ids: [] }

export function installApiMock(me: any = adminMe) {
  handlers.get = (url) => {
    if (url === '/auth/me') return { data: me }
    throw new Error(`unhandled GET ${url}`)
  }
  handlers.post = (url) => {
    if (url === '/events/ticket') return { data: { ticket: 'tkt', expires_in: 60 } }
    throw new Error(`unhandled POST ${url}`)
  }
}

export function renderApp(path = '/') {
  const client = makeQueryClient()
  const utils = render(<MemoryRouter initialEntries={[path]}><App client={client} /></MemoryRouter>)
  return { client, ...utils }
}

vi.mock('../src/services/api', () => {
  const wrap = (m: 'get' | 'post' | 'patch' | 'put') => async (url: string, cfg?: any) => {
    calls.push({ method: m, url, cfg })
    return handlers[m](url, cfg)
  }
  const store = { access: 'tok' as string | null, refresh: 'ref' as string | null }
  return {
    api: { get: wrap('get'), post: wrap('post'), patch: wrap('patch'), put: wrap('put') },
    API_BASE: '/api/v1',
    tokens: {
      get access() { return store.access },
      get refresh() { return store.refresh },
      set: (a: string, r: string) => { store.access = a; store.refresh = r },
      clear: () => { store.access = null; store.refresh = null },
    },
    refreshSession: async () => {},
    errorMessage: (e: any) => e?.response?.data?.detail ?? e?.message ?? 'error',
  }
})
