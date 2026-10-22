import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { tokens } from '../src/services/api'
import { calls, FakeEventSource, handlers, installApiMock, renderApp } from './helpers' // helpers first: installs the api mock
import { accuracyClass, markerStyle, popupLines } from '../src/features/map/markers'
import { loadGoogleMaps, onMapsAuthFailure } from '../src/features/map/googleMaps'
import { canReject } from '../src/features/submissions/ReviewPanel'
import { displayValue } from '../src/features/submissions/SubmissionDetail'
import { moved } from '../src/features/settings/Settings'

type Rec = Record<string, any>
let state: Rec

const TYPES = () => ({
  items: [
    { id: 't1', label: 'Customer', active: true, sort_order: 0, times_used: 3 },
    { id: 't2', label: 'Dealer', active: true, sort_order: 1, times_used: 1 },
    { id: 't3', label: 'Supplier', active: false, sort_order: 2, times_used: 0 },
  ],
  settings: { required: true, allow_other: false },
})
const REASONS = [
  { id: 'r1', code: 'unclear_photo', label: 'Unclear photo', default_message: 'Upload a clearer photo of the relevant evidence.', requires_comment: false, active: true, sort_order: 0 },
  { id: 'r2', code: 'other', label: 'Other', default_message: null, requires_comment: true, active: true, sort_order: 1 },
]

beforeEach(() => {
  tokens.set('tok', 'ref')
  calls.length = 0
  FakeEventSource.instances = []
  vi.stubGlobal('EventSource', FakeEventSource)
  state = { types: TYPES() }
  installApiMock()
  const get = handlers.get
  handlers.get = (url, cfg) => {
    if (url === '/person-types') return { data: state.types }
    if (url === '/review-reasons') return { data: { items: REASONS } }
    return get(url, cfg)
  }
})
afterEach(() => vi.unstubAllGlobals())

// ------------------------------------------------------------------ Settings
test('settings: managed person types can be added, renamed, deactivated, reordered and configured', async () => {
  handlers.post = (url, body) => {
    if (url === '/person-types') { state.types = { ...state.types, items: [...state.types.items, { id: 't9', label: body.label, active: true, sort_order: 3, times_used: 0 }] }; return { data: state.types } }
    throw new Error(url)
  }
  handlers.patch = (url, body) => {
    if (url === '/person-types/settings') { state.types = { ...state.types, settings: { ...state.types.settings, ...body } }; return { data: state.types } }
    const id = url.split('/').pop()
    state.types = { ...state.types, items: state.types.items.map((t: Rec) => (t.id === id ? { ...t, ...(body.label ? { label: body.label } : {}), ...(body.active !== undefined ? { active: body.active } : {}) } : t)) }
    return { data: state.types }
  }
  handlers.put = (_url, body) => {
    const by = Object.fromEntries(state.types.items.map((t: Rec) => [t.id, t]))
    state.types = { ...state.types, items: body.ids.map((i: string) => by[i]) }
    return { data: state.types }
  }
  renderApp('/settings')
  const list = await screen.findByRole('list', { name: 'Person types' })
  expect(within(list).getAllByRole('listitem').map((li) => li.textContent)).toEqual([
    expect.stringContaining('Customer'), expect.stringContaining('Dealer'), expect.stringContaining('Supplier')])
  expect(within(list).getByText('Supplier').closest('li')).toHaveTextContent('inactive') // inactive options are shown but flagged
  const user = userEvent.setup()

  await user.type(screen.getByLabelText('Add a new type'), 'Government Official')
  await user.click(screen.getByRole('button', { name: 'Add type' }))
  expect(await within(list).findByText('Government Official')).toBeInTheDocument()
  expect(calls.find((c) => c.method === 'post' && c.url === '/person-types')).toBeTruthy()

  const dealer = within(list).getByText('Dealer').closest('li')!
  await user.click(within(dealer).getByRole('button', { name: 'Rename' }))
  const input = within(dealer).getByLabelText('New name')
  await user.clear(input)
  await user.type(input, 'Retail Dealer')
  await user.click(within(dealer).getByRole('button', { name: 'Save' }))
  expect(await within(list).findByText('Retail Dealer')).toBeInTheDocument()

  await user.click(within(within(list).getByText('Customer').closest('li')!).getByRole('button', { name: 'Deactivate' }))
  await waitFor(() => expect(calls.some((c) => c.method === 'patch' && c.url === '/person-types/t1' && c.cfg.active === false)).toBe(true))

  await user.click(within(within(list).getByText('Customer').closest('li')!).getByRole('button', { name: 'Move down' }))
  await waitFor(() => expect(calls.find((c) => c.method === 'put')!.cfg.ids.slice(0, 2)).toEqual(['t2', 't1']))

  await user.click(screen.getByLabelText('Allow "Other" with a custom value'))
  await waitFor(() => expect(calls.some((c) => c.url === '/person-types/settings' && c.cfg.allow_other === true)).toBe(true))
})

test('settings: a duplicate-name error from the server is shown, not swallowed', async () => {
  handlers.post = () => { const e: any = new Error('x'); e.response = { data: { detail: 'An active option with this name already exists' } }; throw e }
  renderApp('/settings')
  const user = userEvent.setup()
  await user.type(await screen.findByLabelText('Add a new type'), 'dealer')
  await user.click(screen.getByRole('button', { name: 'Add type' }))
  expect((await screen.findAllByRole('alert'))[0]).toHaveTextContent('already exists')
})

test('settings: reorder helper moves within bounds only', () => {
  expect(moved(['a', 'b', 'c'], 1, -1)).toEqual(['b', 'a', 'c'])
  expect(moved(['a', 'b', 'c'], 0, -1)).toBeNull()
  expect(moved(['a', 'b', 'c'], 2, 1)).toBeNull()
})

// ------------------------------------------------------------------ Review panel
const detail = (over: Rec = {}) => ({
  id: 's2', agent_name: 'Ravi', employee_code: 'E1', branch_id: 'b1', branch_name: 'HQ', form_title: 'Field Meeting Report', form_version: 4,
  submitted_at_device: '2026-10-10T04:45:00Z', received_at_server: '2026-10-10T07:00:05Z', accepted_at_server: '2026-10-10T07:00:06Z',
  status: 'accepted', review_status: 'pending', photo_count: 0, has_location: false, client_submission_id: 'c1', device_tz_offset_min: 330,
  reference: 'FS-2026-0042', revision: 2, is_latest: true, root_id: 's1', person_types: ['Dealer'],
  review_reason_code: null, review_comment: null, review_flags: [], reviewed_at: null,
  option_labels: { 'meeting_details[0].contact_category': 'Dealer' },
  revisions: [
    { id: 's1', revision: 1, accepted_at_server: '2026-10-09T07:00:06Z', review_status: 'rejected', is_latest: false },
    { id: 's2', revision: 2, accepted_at_server: '2026-10-10T07:00:06Z', review_status: 'pending', is_latest: true }],
  reviews: [{ id: 'v1', submission_id: 's1', revision: 1, decision: 'rejected', reason_code: 'unclear_photo', reason_label: 'Unclear photo', comment: 'Blurry', flags: [], reviewer: 'Ada Admin', created_at: '2026-10-09T09:00:00Z' }],
  submission_location: { latitude: null, longitude: null, accuracy_m: null, fix_at_device: null, status: 'timeout', place_name: null, place_status: 'done' },
  answers: { meeting_details: [{ contact_category: 'T', contact_name: 'Kumar' }, { contact_category: 'other:Govt officer', contact_name: 'Devi' }] },
  schema: { title: 'FMR', sections: [{ id: 'meeting_details', title: 'Meeting Details', repeatable: true, fields: [
    { key: 'contact_category', label: 'Type of person', type: 'dropdown' }, { key: 'contact_name', label: 'Name', type: 'text' }] }] },
  photos: [], events: [], ...over,
})

function openDetail(d: Rec) {
  const get = handlers.get
  handlers.get = (url, cfg) => (url === '/submissions/s2' ? { data: d } : get(url, cfg))
  return renderApp('/submissions/s2')
}

test('review: reason and (when required) comment are mandatory; default message pre-fills; flags and decision are sent', async () => {
  handlers.post = (url) => { if (url === '/submissions/s2/reviews') return { data: {} }; throw new Error(url) }
  openDetail(detail())
  await screen.findByRole('heading', { level: 1, name: /FS-2026-0042/ })
  const user = userEvent.setup()
  await screen.findByRole('option', { name: 'Unclear photo' }) // reasons have loaded
  const send = screen.getByRole('button', { name: 'Send back for correction' })
  expect(send).toBeDisabled() // no reason yet
  await user.selectOptions(screen.getByLabelText('Reason for sending back'), 'unclear_photo')
  expect(screen.getByLabelText(/Message to the agent/)).toHaveValue('Upload a clearer photo of the relevant evidence.')
  expect(send).toBeEnabled()
  await user.selectOptions(screen.getByLabelText('Reason for sending back'), 'other')
  expect(screen.getByLabelText(/Message to the agent \(required\)/)).toHaveValue('') // "Other" has no default and needs text
  expect(send).toBeDisabled()

  // flag the second meeting
  const meeting2 = screen.getByRole('region', { name: 'Meeting 2' })
  await user.click(within(meeting2).getByRole('button', { name: 'Flag' }))
  await user.type(within(meeting2).getByLabelText('Flag note'), 'Which dealer?')
  await user.click(within(meeting2).getByRole('button', { name: 'Add' }))
  expect(within(meeting2).getByTestId('flag-set')).toHaveTextContent('Which dealer?')
  expect(screen.getByText('Flagged items (1)')).toBeInTheDocument()

  await user.type(screen.getByLabelText(/Message to the agent/), 'Please say which dealer you met.')
  await user.click(send)
  await waitFor(() => expect(calls.find((c) => c.method === 'post' && c.url === '/submissions/s2/reviews')).toBeTruthy())
  expect(calls.find((c) => c.url === '/submissions/s2/reviews')!.cfg).toEqual({
    decision: 'rejected', reason_code: 'other', comment: 'Please say which dealer you met.', flags: [{ path: 'meeting_details[1]', note: 'Which dealer?' }] })
})

test('review: approving sends no reason or flags', async () => {
  handlers.post = () => ({ data: {} })
  openDetail(detail())
  await userEvent.setup().click(await screen.findByRole('button', { name: 'Approve' }))
  await waitFor(() => expect(calls.find((c) => c.url === '/submissions/s2/reviews')!.cfg).toEqual({ decision: 'approved', reason_code: undefined, comment: undefined, flags: [] }))
})

test('review: an approved report is final until reopened with a written reason', async () => {
  handlers.post = () => ({ data: {} })
  openDetail(detail({ review_status: 'approved' }))
  const user = userEvent.setup()
  await screen.findByText(/This version is final/)
  expect(screen.queryByRole('button', { name: 'Approve' })).toBeNull()
  await user.click(screen.getByRole('button', { name: 'Reopen for review…' }))
  const dlg = screen.getByRole('dialog')
  expect(within(dlg).getByRole('button', { name: 'Reopen' })).toBeDisabled()
  await user.type(within(dlg).getByLabelText('Reason for reopening'), 'Client asked for a recheck')
  await user.click(within(dlg).getByRole('button', { name: 'Reopen' }))
  await waitFor(() => expect(calls.find((c) => c.url === '/submissions/s2/reopen')!.cfg).toEqual({ comment: 'Client asked for a recheck' }))
})

test('review: an earlier version is read-only and points to the current one; history shows every decision', async () => {
  openDetail(detail({ is_latest: false, revision: 1, review_status: 'rejected' }))
  await screen.findByText(/earlier version/)
  expect(screen.getByRole('link', { name: 'revision 2' })).toHaveAttribute('href', '/submissions/s2')
  expect(screen.queryByRole('button', { name: 'Approve' })).toBeNull()
  const hist = screen.getByText('Review history').closest('section')!
  expect(within(hist).getByText('Unclear photo')).toBeInTheDocument()
  expect(within(hist).getByText('Ada Admin')).toBeInTheDocument()
  expect(within(screen.getByRole('navigation', { name: 'Versions' })).getAllByText(/Revision/)).toHaveLength(2)
})

test('review: flags saved with a rejection are shown on the sent-back report', async () => {
  openDetail(detail({ review_status: 'rejected', review_comment: 'Fix it', review_flags: [{ path: 'meeting_details[0]', note: 'Photo is blurry' }] }))
  await screen.findByTestId('sent-back')
  expect(screen.getByTestId('sent-back')).toHaveTextContent('Fix it')
  const m1 = screen.getByRole('region', { name: 'Meeting 1' })
  expect(within(m1).getByText(/Photo is blurry/)).toBeInTheDocument()
})

test('review helpers: canReject and answer display', () => {
  expect(canReject(undefined, 'x')).toBe(false)
  expect(canReject(REASONS[0], '')).toBe(true)
  expect(canReject(REASONS[1], '  ')).toBe(false)
  expect(canReject(REASONS[1], 'why')).toBe(true)
  const f = { key: 'contact_category', label: 'Type', type: 'dropdown' }
  expect(displayValue(f, 'uuid-1', 'm[0].contact_category', { 'm[0].contact_category': 'Dealer' })).toBe('Dealer')
  expect(displayValue(f, 'other:Govt', 'm[0].contact_category', { 'm[0].contact_category': 'Govt' })).toBe('Govt (other)')
  expect(displayValue(f, 'plain', 'x', {})).toBe('plain')
  expect(displayValue(f, '', 'x', {})).toBe('—')
})

// ------------------------------------------------------------------ Analytics
const metrics = (o: Rec = {}) => ({
  reports: 0, active_agents: 0, pending: 0, approved: 0, needs_correction: 0, target: null, achievement: null,
  reviewed_decisions: 0, rejection_rate: null, previous_reports: 0, trend_pct: null, ...o })
const overview = (key = 'month', applies = true) => ({
  period: { key, from: '2026-10-01', to: '2026-10-31', timezone: 'Asia/Kolkata', targets_apply: applies },
  totals: { reports: 9, pending: 4, approved: 3, needs_correction: 2, assigned_agents: 6, active_agents: 4, reviewed_decisions: 5, rejection_rate: 40, previous_reports: 6, trend_pct: 50 },
  branches: [
    { branch_id: 'b1', name: 'Chennai', code: 'CHN', assigned_agents: 4,
      ...metrics({ reports: 7, active_agents: 3, pending: 3, approved: 3, needs_correction: 1, target: applies ? 10 : null, achievement: applies ? 70 : null, reviewed_decisions: 5, rejection_rate: 40, previous_reports: 4, trend_pct: 75 }) },
    { branch_id: 'b2', name: 'Trichy', code: 'TRY', assigned_agents: 2, ...metrics({ reports: 2, active_agents: 1, previous_reports: 0, trend_pct: null }) },
  ],
  person_types: [{ label: 'Dealer', meetings: 5 }, { label: 'Customer', meetings: 2 }],
})

test('analytics: totals, branch table with targets, honest empty values and drill-down links', async () => {
  const get = handlers.get
  handlers.get = (url, cfg) => (url === '/analytics/overview' ? { data: overview(cfg.params.period) } : get(url, cfg))
  renderApp('/analytics')
  expect(await screen.findByText('Reports submitted')).toBeInTheDocument()
  expect(calls.find((c) => c.url === '/analytics/overview')!.cfg.params).toEqual({ period: 'month' })
  const table = screen.getByRole('table')
  const chennai = within(table).getByText('Chennai').closest('tr')!
  expect(within(chennai).getByText('70%')).toBeInTheDocument()
  expect(within(chennai).getByRole('progressbar')).toHaveAttribute('aria-valuenow', '70')
  expect(within(chennai).getByText('▲ 75%')).toBeInTheDocument()
  expect(within(chennai).getByText('40%')).toBeInTheDocument() // rejection rate
  const trichy = within(table).getByText('Trichy').closest('tr')!
  expect(within(trichy).getByText('No target')).toBeInTheDocument()
  expect(within(trichy).getAllByText('—').length).toBeGreaterThanOrEqual(2) // no rejection rate / trend: not "0%"
  const reportsLink = within(chennai).getByRole('link', { name: '7' })
  expect(reportsLink.getAttribute('href')).toContain('/submissions?date_from=2026-10-01&date_to=2026-10-31&branch_id=b1')
  expect(screen.getByRole('list', { name: 'Meetings by type of person' })).toHaveTextContent('Dealer')
  expect(within(chennai).getByRole('link', { name: 'Chennai' }).getAttribute('href')).toContain('/analytics/branches/b1')
})

test('analytics: a target can be set; targets are not offered for the "today" view', async () => {
  const get = handlers.get
  handlers.get = (url, cfg) => (url === '/analytics/overview' ? { data: overview(cfg.params.period, cfg.params.period !== 'today') } : get(url, cfg))
  handlers.put = () => ({ data: {} })
  renderApp('/analytics')
  const user = userEvent.setup()
  const row = (await screen.findByText('Trichy')).closest('tr')!
  await user.click(within(row).getByRole('button', { name: 'Set' }))
  await user.type(within(row).getByLabelText('Monthly target'), '15')
  await user.click(within(row).getByRole('button', { name: 'Save' }))
  await waitFor(() => expect(calls.find((c) => c.method === 'put')!.cfg).toEqual({ scope: 'branch', id: 'b2', period: 'monthly', target: 15 }))
  await user.click(screen.getByRole('button', { name: 'Today' }))
  await waitFor(() => expect(screen.getAllByText('n/a').length).toBeGreaterThan(0))
  expect(screen.queryByRole('button', { name: 'Set' })).toBeNull()
})

test('analytics: custom period waits for both dates', async () => {
  const get = handlers.get
  handlers.get = (url, cfg) => (url === '/analytics/overview' ? { data: overview('custom', false) } : get(url, cfg))
  renderApp('/analytics?period=custom')
  expect(await screen.findByText('Choose a start and end date.')).toBeInTheDocument()
  expect(calls.some((c) => c.url === '/analytics/overview')).toBe(false)
  fireEvent.change(screen.getByLabelText('From'), { target: { value: '2026-10-01' } })
  fireEvent.change(screen.getByLabelText('To'), { target: { value: '2026-10-09' } })
  await screen.findByText('Reports submitted')
  expect(calls.find((c) => c.url === '/analytics/overview')!.cfg.params).toEqual({ period: 'custom', date_from: '2026-10-01', date_to: '2026-10-09' })
})

test('analytics: agent drill-down lists agents and warns that unsynced reports are not counted', async () => {
  const get = handlers.get
  handlers.get = (url, cfg) => (url === '/analytics/branches/b1/agents' ? { data: {
    period: overview().period, branch: { id: 'b1', name: 'Chennai' }, note: "A low count can also mean reports are still waiting to sync on the agent's phone.",
    agents: [{ agent_id: 'a1', name: 'Agent C', employee_code: 'E3', status: 'active', last_report_at: null, ...metrics({ reports: 12, target: 25, achievement: 48 }) }] } } : get(url, cfg))
  renderApp('/analytics/branches/b1?period=month')
  const row = (await screen.findByText('Agent C')).closest('tr')!
  expect(within(row).getByText('48%')).toBeInTheDocument()
  expect(within(row).getByText('Never')).toBeInTheDocument()
  expect(screen.getByTestId('sync-note')).toHaveTextContent('waiting to sync')
  expect(within(row).getByRole('link', { name: '12' }).getAttribute('href')).toContain('agent_id=a1')
})

// ------------------------------------------------------------------ Map
const mapData = () => ({
  reports: [
    { id: 'm1', reference: 'FS-2026-0001', revision: 1, agent_name: 'Ravi', employee_code: 'E1', branch_id: 'b1', branch_name: 'Chennai', form_title: 'FMR',
      review_status: 'pending', latitude: 13.08, longitude: 80.27, accuracy_m: 120, location_status: 'obtained', place_name: 'Anna Salai, Chennai', place_status: 'done',
      submitted_at_device: '2026-10-10T04:45:00Z', accepted_at_server: '2026-10-10T04:46:00Z', meeting_dates: ['2026-10-10'], person_types: ['Dealer'] },
    { id: 'm2', reference: 'FS-2026-0002', revision: 1, agent_name: 'Devi', employee_code: 'E2', branch_id: 'b1', branch_name: 'Chennai', form_title: 'FMR',
      review_status: 'approved', latitude: 13.1, longitude: 80.3, accuracy_m: 8, location_status: 'obtained', place_name: null, place_status: 'pending',
      submitted_at_device: '2026-10-10T05:45:00Z', accepted_at_server: '2026-10-10T05:46:00Z', meeting_dates: [], person_types: [] }],
  photos: [], branches: [{ id: 'b1', name: 'Chennai', code: 'CHN', status: 'active', latitude: 13.0, longitude: 80.2 }],
  counts: { reports: 5, with_gps: 2, without_gps: 3, shown: 2, truncated: false }, note: 'n',
})

test('map: without a Google browser key it explains the setup and still lists every recorded location', async () => {
  const get = handlers.get
  handlers.get = (url, cfg) => (url === '/map/markers' ? { data: mapData() } : get(url, cfg))
  renderApp('/map')
  expect(await screen.findByTestId('map-key-missing')).toHaveTextContent('VITE_GOOGLE_MAPS_API_KEY')
  expect(screen.queryByTestId('google-map')).toBeNull()
  expect(screen.getByTestId('map-summary')).toHaveTextContent('Showing 2 of 2 reports')
  expect(screen.getByTestId('map-summary')).toHaveTextContent('3 without GPS are not on the map')
  expect(screen.getByTestId('map-summary')).toHaveTextContent('does not track agents continuously')
  const row = screen.getByText('FS-2026-0001').closest('tr')!
  expect(within(row).getByText('Anna Salai, Chennai')).toBeInTheDocument()
  expect(within(row).getByText(/poor accuracy/)).toBeInTheDocument() // 120 m is flagged
  const row2 = screen.getByText('FS-2026-0002').closest('tr')!
  expect(within(row2).getByText(/precise/)).toBeInTheDocument()
  expect(within(row2).getByText('Looking up…')).toBeInTheDocument()
  expect(within(row).getByRole('link', { name: '13.08000, 80.27000' }).getAttribute('href')).toBe('https://www.google.com/maps?q=13.08,80.27')
  // filters are sent to the server (and photo/branch switches)
  expect(calls.find((c) => c.url === '/map/markers')!.cfg.params).toMatchObject({ include_photos: false, include_branches: true })
  fireEvent.click(screen.getByLabelText('Photo locations'))
  await waitFor(() => expect(calls.filter((c) => c.url === '/map/markers').at(-1)!.cfg.params.include_photos).toBe(true))
})

test('map marker styling: imprecise locations are visibly different; pop-up is plain text', () => {
  expect([accuracyClass(5), accuracyClass(60), accuracyClass(300), accuracyClass(null)]).toEqual(['good', 'fair', 'poor', 'unknown'])
  const precise = markerStyle('approved', 8), poor = markerStyle('approved', 400), unknown = markerStyle('pending', null)
  expect(precise.fillOpacity).toBeGreaterThan(0.5)
  expect(poor.fillOpacity).toBeLessThan(0.3) // hollow
  expect(unknown.fillOpacity).toBeLessThan(0.3)
  expect(precise.color).not.toBe(markerStyle('rejected', 8).color) // status colours differ
  const r = mapData().reports[0] as any
  const lines = popupLines({ ...r, agent_name: '<img src=x onerror=alert(1)>' })
  expect(lines.join('\n')).toContain('Agent: <img src=x onerror=alert(1)> (E1)') // returned as text; the map sets textContent
  expect(lines).toContain('Status: pending')
  expect(popupLines({ ...r, review_status: 'rejected' })).toContain('Status: needs correction')
  expect(lines.some((l) => l.includes('poor accuracy'))).toBe(true)
})

test('google maps loader injects one script with the key and reports key rejection', async () => {
  const p = loadGoogleMaps('KEY123')
  const script = document.head.querySelector('script[src*="maps.googleapis.com"]') as HTMLScriptElement
  expect(script.src).toContain('key=KEY123')
  expect(script.src).toContain('callback=__fieldsyncMapsReady')
  expect(loadGoogleMaps('KEY123')).toBe(p) // loaded once
  ;(window as any).google = { maps: { Map: class {} } }
  ;(window as any).__fieldsyncMapsReady()
  await expect(p).resolves.toBeTruthy()
  const seen: string[] = []
  const off = onMapsAuthFailure((m) => seen.push(m))
  ;(window as any).gm_authFailure()
  off()
  expect(seen[0]).toContain('Google rejected the map key')
})
