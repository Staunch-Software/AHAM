import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { act } from 'react'
import { adminMe, calls, FakeEventSource, handlers, installApiMock, renderApp } from './helpers' // must precede api import (installs the api mock)
import { tokens } from '../src/services/api'

const dash = { total_agents: 3, active_branches: 2, submissions_today: 5, pending_review: 1, needs_correction: 2, recent: [], trend: [] }

beforeEach(() => {
  tokens.set('tok', 'ref')
  calls.length = 0
  FakeEventSource.instances = []
  vi.stubGlobal('EventSource', FakeEventSource)
  installApiMock()
  const base = handlers.get
  handlers.get = (url, cfg) => (url === '/dashboard' ? { data: dash } : base(url, cfg))
})
afterEach(() => vi.unstubAllGlobals())

test('no form-builder or form-management UI or routes exist', async () => {
  renderApp('/')
  await screen.findByText('Dashboard', { selector: 'h1' })
  const nav = screen.getByRole('navigation', { name: 'Main' })
  const labels = within(nav).getAllByRole('link').map((a) => a.textContent)
  expect(labels).toEqual(['Dashboard', 'Submissions', 'Performance', 'Field map', 'Organization', 'Employees', 'Reports', 'Settings', 'Audit log'])
  expect(screen.queryByText(/form builder|add field|schema|publish form/i)).toBeNull()
  for (const p of ['/forms', '/form-builder', '/forms/new', '/schemas']) {
    const { unmount } = renderApp(p)
    expect(await screen.findByText('Page not found.')).toBeInTheDocument()
    unmount()
  }
})

test('dashboard shows real counts and hides empty trend', async () => {
  renderApp('/')
  expect(await screen.findByTestId('stat-Reports today')).toHaveTextContent('5')
  expect(screen.getByTestId('stat-Needs correction')).toHaveTextContent('2')
  expect(screen.queryByRole('img', { name: /per day/i })).toBeNull()
  expect(screen.getByText('No submissions yet.')).toBeInTheDocument()
})

test('non-admin accounts cannot use the portal', async () => {
  tokens.clear() // signed-out start: avoids a stray in-flight session restore leaking into later tests
  installApiMock({ ...adminMe, role: 'agent' })
  const post = handlers.post
  handlers.post = (url, cfg) => (url === '/auth/login' ? { data: { access_token: 'a', refresh_token: 'r' } } : post(url, cfg))
  renderApp('/login')
  const user = userEvent.setup()
  await user.type(await screen.findByLabelText('Email'), 'agent@x.io')
  await user.type(screen.getByLabelText('Password'), 'password123')
  await user.click(screen.getByRole('button', { name: 'Sign in' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('administrators only')
})

test('login validates input client-side', async () => {
  tokens.clear()
  installApiMock({ ...adminMe, role: 'agent' })
  renderApp('/login')
  await userEvent.setup().click(await screen.findByRole('button', { name: 'Sign in' }))
  expect(await screen.findByText('Enter a valid email')).toBeInTheDocument()
})

test('live updates: event triggers authoritative refetch; reconnect gets a fresh ticket and refetches', async () => {
  vi.useFakeTimers({ shouldAdvanceTime: true })
  renderApp('/')
  await screen.findByTestId('stat-Reports today')
  await waitFor(() => expect(FakeEventSource.instances.length).toBe(1))
  const es = FakeEventSource.instances[0]
  expect(es.url).toContain('/events/submissions?ticket=tkt')
  act(() => es.onopen?.())
  expect(screen.getByTestId('live-status')).toHaveTextContent('Live')

  const dashCalls = () => calls.filter((c) => c.url === '/dashboard').length
  const before = dashCalls()
  act(() => es.emit('submission.accepted'))
  await waitFor(() => expect(dashCalls()).toBe(before + 1)) // refetched from REST; payload not trusted

  const tickets = () => calls.filter((c) => c.url === '/events/ticket').length
  const t0 = tickets()
  act(() => es.onerror?.())
  expect(es.closed).toBe(true)
  expect(screen.getByTestId('live-status')).toHaveTextContent('Reconnecting')
  await act(async () => { await vi.advanceTimersByTimeAsync(1500) })
  await waitFor(() => expect(FakeEventSource.instances.length).toBe(2))
  expect(tickets()).toBe(t0 + 1)
  const mid = dashCalls()
  act(() => FakeEventSource.instances[1].onopen?.())
  await waitFor(() => expect(dashCalls()).toBe(mid + 1)) // catch-up refetch after reconnect
  vi.useRealTimers()
})

test('submission list sends server-side filters and pagination', async () => {
  const row = {
    id: 'abcdef12-0000', agent_name: 'Ravi', employee_code: 'E1', branch_id: 'b1', branch_name: 'HQ', form_title: 'Field Meeting Report',
    reference: 'FS-2026-0042', revision: 2, is_latest: true, root_id: 'r', person_types: ['Dealer'],
    review_reason_code: null, review_comment: null, review_flags: [], reviewed_at: null,
    form_version: 1, submitted_at_device: '2026-10-10T04:45:00Z', received_at_server: '2026-10-10T06:00:00Z',
    accepted_at_server: '2026-10-10T06:00:01Z', status: 'accepted', review_status: 'pending', photo_count: 1, has_location: true,
  }
  const base = handlers.get
  handlers.get = (url, cfg) => {
    if (url === '/submissions') return { data: { items: [row], total: 60, page: cfg.params.page, page_size: 25 } }
    if (url === '/branches') return { data: [{ id: 'b1', name: 'HQ', code: 'HQ', status: 'active' }] }
    if (url === '/employees') return { data: { items: [], total: 0, page: 1, page_size: 100 } }
    if (url === '/person-types') return { data: { items: [{ id: 't1', label: 'Dealer', active: true, sort_order: 0, times_used: 1 }], settings: { required: true, allow_other: false } } }
    return base(url, cfg)
  }
  renderApp('/submissions?review_status=pending&page=2')
  await screen.findByText('FS-2026-0042')
  expect(screen.getByText('Revision 2')).toBeInTheDocument()
  expect(within(screen.getByRole('table')).getByText('Dealer')).toBeInTheDocument()
  const last = () => calls.filter((c) => c.url === '/submissions').at(-1)!.cfg.params
  expect(last()).toMatchObject({ review_status: 'pending', page: 2, page_size: 25 })
  expect(screen.getByText('Page 2 of 3')).toBeInTheDocument()
  fireEvent.change(screen.getByLabelText('Location'), { target: { value: 'true' } })
  await waitFor(() => expect(last()).toMatchObject({ has_location: 'true', review_status: 'pending' }))
  expect(last().page).toBe(1) // changing a filter resets paging
})

test('submission detail keeps photo and submission metadata separate', async () => {
  const photo = {
    photo_id: 'p1', group_key: 'meeting_details:0', field_key: 'meeting_photo', original_filename: null, mime_type: 'image/jpeg',
    size_bytes: 100, sha256: 'ab'.repeat(32), photo_captured_at_device: '2026-10-10T04:30:00Z', exif_captured_at: null,
    photo_capture_latitude: 14.4426, photo_capture_longitude: 79.9865, photo_capture_accuracy_m: 8,
    photo_location_fix_at_device: '2026-10-10T04:30:01Z', photo_location_status: 'obtained', location_source: 'gps',
    photo_place_name: 'Gandhi Road, Nellore, Andhra Pradesh', photo_place_status: 'done',
    upload_completed_at_server: '2026-10-10T07:00:00Z', url: '/u', thumb_url: '/t',
  }
  const detail = {
    id: 's1', agent_name: 'Ravi', employee_code: 'E1', branch_name: 'HQ', form_title: 'Field Meeting Report', form_version: 1,
    submitted_at_device: '2026-10-10T04:45:00Z', received_at_server: '2026-10-10T07:00:05Z', accepted_at_server: '2026-10-10T07:00:06Z',
    status: 'accepted', review_status: 'pending', photo_count: 1, has_location: false, client_submission_id: 'c1', device_tz_offset_min: 330,
    reference: 'FS-2026-0001', revision: 1, is_latest: true, root_id: 's1', person_types: [], review_reason_code: null, review_comment: null, review_flags: [], reviewed_at: null,
    option_labels: {}, revisions: [{ id: 's1', revision: 1, accepted_at_server: '2026-10-10T07:00:06Z', review_status: 'pending', is_latest: true }], reviews: [],
    submission_location: { latitude: null, longitude: null, accuracy_m: null, fix_at_device: null, status: 'timeout', place_name: null, place_status: 'pending' },
    answers: { meeting_details: [{ contact_name: 'Kumar', meeting_photo: 'p1' }] },
    schema: {
      title: 'FMR',
      sections: [{ id: 'meeting_details', title: 'Meeting Details', repeatable: true, fields: [
        { key: 'contact_name', label: 'Name', type: 'text' }, { key: 'meeting_photo', label: 'Meeting Photo', type: 'photo' }] }],
    },
    photos: [photo], events: [{ type: 'accepted', detail: null, at: '2026-10-10T07:00:06Z' }],
  }
  const base = handlers.get
  handlers.get = (url, cfg) => (url === '/submissions/s1' ? { data: detail } : url === '/review-reasons' ? { data: { items: [] } } : base(url, cfg))
  renderApp('/submissions/s1')
  const card = await screen.findByTestId('photo-card')
  expect(within(card).getByText(/2026-10-10 10:00:00 \(UTC\+05:30\)/)).toBeInTheDocument() // photo time at capture
  expect(within(card).getByText(/14\.442600, 79\.986500/)).toBeInTheDocument()
  expect(within(card).getByTestId('place-name')).toHaveTextContent('Gandhi Road, Nellore, Andhra Pradesh') // place name next to coordinates
  expect(within(card).getByRole('link', { name: 'Open in Google Maps' })).toBeInTheDocument()
  const sub = screen.getByText('Submission event (when Submit was pressed)').closest('section')!
  expect(within(sub).getByText(/2026-10-10 10:15:00 \(UTC\+05:30\)/)).toBeInTheDocument() // separate submit time
  expect(within(sub).getByText(/Unavailable \(timeout\)/)).toBeInTheDocument() // no fabricated coordinates
  expect(within(sub).queryByRole('link', { name: 'Open in Google Maps' })).toBeNull()
  expect(screen.getByText('Kumar')).toBeInTheDocument()
})
