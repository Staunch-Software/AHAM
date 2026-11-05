import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'
import App, { makeQueryClient } from '../src/app/App'
import { tokens } from '../src/services/api'

export type Handler = (url: string, cfg?: any) => any
type Method = 'get' | 'post' | 'patch' | 'put' | 'delete'
export const handlers: Record<Method, Handler> = {
  get: () => { throw new Error('unhandled GET') },
  post: () => { throw new Error('unhandled POST') },
  patch: () => { throw new Error('unhandled PATCH') },
  put: () => { throw new Error('unhandled PUT') },
  delete: () => { throw new Error('unhandled DELETE') },
}
export const calls: { method: string; url: string; body?: any; cfg?: any }[] = []

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

const PERMS: Record<string, string[]> = {
  branch_manager: ['entries.read', 'dashboard.read', 'compliance.read', 'map.read', 'team.read', 'branch.answer', 'correct.number', 'correct.so'],
  product_manager: ['entries.read', 'dashboard.read', 'compliance.read', 'map.read', 'team.read', 'compliance.export'],
  caller: ['entries.read', 'calls.work'],
  master_owner: ['entries.read', 'dashboard.read', 'compliance.read', 'map.read', 'calls.work', 'calls.manage', 'login_register.upload'],
  mis: ['login_register.upload'],
  sankalp_monitor: ['entries.read', 'dashboard.read', 'compliance.read', 'map.read', 'team.read', 'compliance.export', 'correct.so',
    'category.review', 'reference.import', 'takeoff.export', 'audit.read'],
  admin: ['entries.read', 'dashboard.read', 'compliance.read', 'map.read', 'team.read', 'compliance.export', 'users.manage', 'org.manage',
    'settings.manage', 'cp_subtypes.manage', 'reference.import', 'takeoff.export', 'audit.read', 'login_register.upload'],
}
const PORTAL: Record<string, string> = { branch_manager: 'manage', product_manager: 'manage', caller: 'callcentre', master_owner: 'callcentre', mis: 'admin', sankalp_monitor: 'admin', admin: 'admin' }

export function meFor(role: string, over: Record<string, unknown> = {}) {
  return {
    id: `u-${role}`, company_id: 'c1', employee_code: 'AHFL90011', full_name: `Test ${role}`, email: null, role,
    role_label: role.replace('_', ' '), portal: PORTAL[role], permissions: PERMS[role], designation: null,
    branch_id: role === 'branch_manager' ? 'b1' : null, cluster_id: null, region_id: null,
    branch_name: role === 'branch_manager' ? 'Vijayawada' : null, cluster_name: null, region_name: null,
    company_name: 'AHAM', must_change_password: false, ...over,
  }
}

export const META = {
  categories: [{ key: 'lead', label: 'Lead', call_group: 'lead' }, { key: 'contact_point', label: 'Contact Point', call_group: 'dsa_cp' }],
  slots: ['09-10', '10-11', '11-12', '12-01', '01-02', '02-03', '03-04', '04-05', '05-06', '06-07'],
  outcomes: ['Connected', 'RNR', 'Busy', 'Switched off', 'Not reachable', 'Invalid number', 'Wrong person', 'Callback requested', 'Refused to talk'],
  unanswered: ['Busy', 'Not reachable', 'RNR', 'Switched off'],
  questions: {
    name_check: ['Same person', 'Same person, different spelling', 'Different person – same family', 'Different person'],
    visit: ['Yes', "Don't recall", 'No'], relationship: ['No', 'Yes – the same officer', 'Yes – another employee'],
    loan_need: ['Home purchase', 'Self-construction', 'LAP', 'Not looking for a loan'], timeline: ['Within 15 days'], income: ['Salaried'],
    documents: ['Yes', 'Partly', 'No', 'File already logged with Aham'], next_step: ['SO / branch visit', 'Call centre to continue', 'Not now'],
    purpose: ['Discuss eligibility'], own_contribution: ['Fully'], dsa_rag: ['Green', 'NA', 'Amber', 'Red'],
  },
  branch_codes: [
    { code: '1', meaning: 'Logged in', date_label: null }, { code: '3', meaning: 'RNR: customer not answering the branch', date_label: null },
    { code: 'R2', meaning: 'Rejected: eligibility or income', date_label: null }, { code: 'A1', meaning: 'Documents pending: KYC', date_label: 'Login date' },
  ],
  statuses: ['In retry', 'Validated'], lead_outcomes: ['Logged in'], rags: ['PENDING', 'NA', 'RED', 'AMBER', 'RNR', 'GREEN'],
  tracker: { owners: ['branch', 'call_centre', 'done'], outcomes: ['Reopen for calling'] },
  limits: {
    repeat_window_days: 30, max_unanswered_lead: 9, tries_per_day_lead: 2, tries_per_day_dsa: 1, max_slots_per_day: 3,
    first_attempt_target_days: 1, action_window_days: 14, correct_number_window_days: 15, amber_correction_window_days: 15,
    branch_date_threshold_days: 14, daily_entry_target: 10, daily_lead_target: 5, green_channel_construction_limit: 800000,
    green_channel_purchase_limit: 1500000,
  },
}

/** Signed-in as `role` (null = signed out). Extra GET routes can be added per test. */
export function installApiMock(role: string | null, extra: Record<string, any> = {}) {
  calls.length = 0
  tokens.set('tok', 'ref')  // every test starts with a stored session (signed out = /auth/me refuses it)
  const me = role ? meFor(role) : null
  handlers.get = (url, cfg) => {
    if (url === '/auth/me') { if (!me) throw Object.assign(new Error('401'), { response: { status: 401 } }); return { data: me } }
    if (url === '/sankalp/meta') return { data: META }
    if (url in extra) return { data: typeof extra[url] === 'function' ? extra[url](cfg) : extra[url] }
    if (['/branches', '/regions', '/clusters'].includes(url)) return { data: [] }
    if (url === '/roles') return { data: { portals: {}, roles: [] } }
    if (url === '/employees') return { data: { items: [], total: 0, page: 1, page_size: 25 } }
    throw new Error(`unhandled GET ${url}`)
  }
  handlers.post = (url) => {
    if (url === '/events/ticket') return { data: { ticket: 'tkt', expires_in: 60 } }
    throw new Error(`unhandled POST ${url}`)
  }
  return me
}

export function renderApp(path = '/') {
  const client = makeQueryClient()
  const utils = render(<MemoryRouter initialEntries={[path]}><App client={client} /></MemoryRouter>)
  return { client, ...utils }
}

vi.mock('../src/services/api', () => {
  const wrap = (m: Method) => async (url: string, a?: any, b?: any) => {
    const withBody = m === 'post' || m === 'put' || m === 'patch'
    calls.push({ method: m, url, body: withBody ? a : undefined, cfg: withBody ? b : a })
    return handlers[m](url, withBody ? a : a)
  }
  const store = { access: 'tok' as string | null, refresh: 'ref' as string | null }
  return {
    api: { get: wrap('get'), post: wrap('post'), patch: wrap('patch'), put: wrap('put'), delete: wrap('delete') },
    API_BASE: '/api/v1',
    setPortal: () => {},
    tokens: {
      get access() { return store.access },
      get refresh() { return store.refresh },
      set: (a: string, r: string) => { store.access = a; store.refresh = r },
      clear: () => { store.access = null; store.refresh = null },
    },
    refreshSession: async () => {},
    download: async () => {},
    errorMessage: (e: any) => e?.response?.data?.detail?.message ?? e?.response?.data?.detail ?? e?.message ?? 'error',
  }
})
