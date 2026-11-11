// The web side of the feature-review fixes (docs/feature-review.md), numbered as in the review.
import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, test, vi } from 'vitest'
import { isSunday, parseWhole, rupeesInWords } from '../src/services/format'
import { FakeEventSource, handlers, installApiMock, renderApp } from './helpers'

beforeEach(() => {
  FakeEventSource.instances = []
  vi.stubGlobal('EventSource', FakeEventSource)
})

const base = {
  id: 'e1', entry_code: 'AHFL90001-20261020-100000', emp_code: 'AHFL90001', so_user_id: 's1', so_name: 'Ravi Kumar', so_employee_code: 'AHFL90001',
  branch_id: 'b1', branch_name: 'Vijayawada', region_name: 'AP & TG', category: 'lead', category_label: 'Lead', cp_subtype_label: null, call_group: 'lead',
  person_name: 'Suresh', phone: '9876543210', submitted_at_device: '2026-10-20T04:30:00Z', received_at_server: '2026-10-20T04:31:00Z',
  entry_date: '2026-10-20', count_date: '2026-10-20', device_time_suspect: false, selection_status: 'Allocate', status: null, rag: 'PENDING',
  rag_overridden: false, priority: false, so_action: null, so_action_date: null, so_action_until: null, cc_action: null, cc_action_date: null,
  lead_outcome: null, tcs_id: null, customer_validated: false, sankalp_success: false, photo_count: 0, has_location: true, place_name: null,
  description: 'Wants a loan', keka_photo_time: null, phone_raw: '9876543210', device_tz_offset_min: 330, spoke: null,
  location: { latitude: 16.5, longitude: 80.6, accuracy_m: 10, fix_at_device: null, status: 'obtained', place_name: null, place_status: 'done' },
  original_so_user_id: 's1', call_cycle: 1, unanswered_count: 0, callback_date: null, validated_on: null, first_validation: false, login_date: null,
  login_source: null, category_review: null, photos: [], history: [], first_caller: null, on_list_of: [], attempts: [], lead_card: null,
  branch_answers: [], tracker: null, same_number: [],
}
const entry = (over: Record<string, unknown> = {}) => ({ ...base, ...over })

test('16.1 / 14.1 helpers: amounts are whole numbers or refused; Sundays are spotted', () => {
  expect(parseWhole('45,00,000')).toBe(4500000)
  expect(parseWhole(' 4000000 ')).toBe(4000000)
  expect(parseWhole('')).toBeNull()
  for (const bad of ['40L', '7 lacks', '35.5 lakh', '₹40,000']) expect(parseWhole(bad)).toBe('bad')
  expect(rupeesInWords(4000000)).toBe('40 lakh')
  expect(rupeesInWords(12500000)).toBe('1.25 crore')
  expect(isSunday('2026-10-25')).toBe(true)
  expect(isSunday('2026-10-26')).toBe(false)
})

test('16.1 the lead card refuses "40L" instead of saving ₹40, and reads the amount back', async () => {
  const attempts = [{ id: 'a1', call_date: '2026-10-21', slot: '10-11', outcome: 'Connected', cycle: 1, next_date: null, answers: { loan_need: 'Home purchase' }, row_status: 'Validated', caller: 'Divya', at: '' }]
  installApiMock('caller', { '/entries/e1': entry({ attempts, status: 'Validated' }) })
  renderApp('/callcentre/calls/e1')
  const loan = await screen.findByLabelText(/Loan requirement/)
  await userEvent.type(loan, '40L')
  expect(screen.getByText('Digits only, e.g. 4500000')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Save lead card' })).toBeDisabled()
  await userEvent.clear(loan)
  await userEvent.type(loan, '4000000')
  expect(screen.getByText('₹40,00,000 (40 lakh)')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Save lead card' })).toBeEnabled()
  // the other limits of 7.4 are said at the field, not after Save
  const cibil = screen.getByLabelText(/CIBIL score/)
  await userEvent.type(cibil, '950')
  expect(screen.getByText('Between 300 and 900; blank if the customer does not know')).toBeInTheDocument()
  await userEvent.type(screen.getByLabelText(/Property pincode/), '52001')
  expect(screen.getByText('6 digits')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Save lead card' })).toBeDisabled()
  await userEvent.clear(cibil)
  await userEvent.type(screen.getByLabelText(/Property pincode/), '0')
  expect(screen.getByRole('button', { name: 'Save lead card' })).toBeEnabled()
})

test('14.1 a Sunday callback date is refused at once', async () => {
  installApiMock('caller', { '/entries/e1': entry() })
  renderApp('/callcentre/calls/e1')
  await userEvent.click(await screen.findByRole('button', { name: 'Callback requested' }))
  await userEvent.type(screen.getByLabelText(/^Call back on \(working day\)/), '2026-10-25')
  expect(screen.getByText('A Sunday is not a working day: pick another date')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Save try' })).toBeDisabled()
})

test('15.1 a converted DSA/CP contact is called with the Lead questions straight away', async () => {
  installApiMock('caller', { '/entries/e1': entry({ call_group: 'dsa_cp', category: 'dsa_connector', category_label: 'DSA/Connector', converted: true }) })
  renderApp('/callcentre/calls/e1')
  expect(await screen.findByText(/Converted from DSA\/CP: called as a lead, 2 tries a day, up to 9 unanswered/)).toBeInTheDocument()
  await userEvent.click(screen.getByRole('button', { name: 'Connected' }))
  expect(screen.getByRole('group', { name: 'Loan need' })).toBeInTheDocument()
  await userEvent.click(within(screen.getByRole('group', { name: 'Loan need' })).getByRole('button', { name: 'Home purchase' }))
  expect(screen.getByTestId('status-preview')).toHaveTextContent('Validated – converted from DSA/CP')
})

test('12.2 / 12.3 the caller sees why an entry is PRIORITY and that its first try is overdue', async () => {
  const row = { ...entry({ priority: true, priority_reason: 'Branch: customer not answering' }), allocation_id: 'al1', kind: 'priority', run_date: '2026-10-21', caller_id: 'c1', caller: 'Divya', tries_today: 0, unanswered_count: 0, first_try_overdue: true }
  installApiMock('caller', { '/calls/my-list': { today: '2026-10-21', items: [row] } })
  renderApp('/callcentre/calls')
  expect(await screen.findByTestId('priority-reason')).toHaveTextContent('Branch: customer not answering')
  expect(screen.getByText('First try overdue')).toBeInTheDocument()
})

test('24.1 / 27.1 open actions come in pages, and expired ones have their own view', async () => {
  const open = entry({ so_action: 'Visit customer', so_action_date: '2026-10-24' })
  const gone = entry({ id: 'e2', entry_code: 'AHFL90001-20261020-110000', expired_action: 'Correct customer number', expired_on: '2026-11-04' })
  installApiMock('branch_manager', {
    '/branch/actions': (cfg: { params: { expired?: boolean } }) => ({ items: cfg.params.expired ? [gone] : [open], total: 1, page: 1, page_size: 100 }),
  })
  renderApp('/manage/actions')
  expect(await screen.findByText('Visit customer')).toBeInTheDocument()
  await userEvent.click(screen.getByRole('button', { name: 'Expired unworked' }))
  expect(await screen.findByText('Expired: Correct customer number · 2026-11-04')).toBeInTheDocument()
  expect(screen.getByText('1 total')).toBeInTheDocument()
})

test('1.2 the audit log shows a setting change with its old and new value', async () => {
  installApiMock('admin', {
    '/audit-logs': { items: [{ id: 'l1', actor: 'Admin', action: 'settings.update', entity_type: 'company', entity_id: 'c1', created_at: '2026-11-01T06:00:00Z', details: { daily_entry_target: { old: 10, new: 12 } } }], total: 1, page: 1, page_size: 25 },
  })
  renderApp('/admin/audit')
  expect(await screen.findByText('daily entry target: 10 → 12')).toBeInTheDocument()
})

test('3.3 Organization shows who heads what and warns when a branch has nobody to answer its leads', async () => {
  installApiMock('admin', {
    '/regions': [{ id: 'r1', name: 'RoTN U', code: 'ROTNU', status: 'active' }, { id: 'r2', name: 'AP & TG', code: 'APTG', status: 'active' }],
    '/branches': [
      { id: 'b1', name: 'Madurai', code: 'MDU', region_id: 'r1', cluster_id: null, status: 'active', address: null, latitude: null, longitude: null },
      { id: 'b2', name: 'Guntur', code: 'GNT', region_id: 'r2', cluster_id: null, status: 'active', address: null, latitude: null, longitude: null },
    ],
    '/org/managers': { branches: { b2: ['Suresh'] }, clusters: {}, regions: { r2: ['Rani'] } },
  })
  renderApp('/admin/organization')
  expect(await screen.findByText(/Nobody answers the leads of 1 branch/)).toBeInTheDocument()
  expect(screen.getByText("No BM, no RBH")).toBeInTheDocument()
  expect(screen.getByText('Suresh')).toBeInTheDocument()
  expect(screen.getByText('No RBH')).toBeInTheDocument()
})

test('3.1 HR & Admin has the employee roster for the monitor', async () => {
  installApiMock('sankalp_monitor', { '/dashboard': { period: { from: '2026-10-21', to: '2026-10-21' }, totals: {}, rag: {}, by_category: {}, by_status: {}, trend: [], branches: [] } })
  renderApp('/admin/team')
  expect(await screen.findByRole('heading', { name: 'Employee roster' })).toBeInTheDocument()
  expect(within(screen.getByRole('navigation', { name: 'Main' })).getByRole('link', { name: 'Employee roster' })).toHaveAttribute('href', '/admin/team')
})

test('dashboard offers last week (on a Monday, this week is still empty)', async () => {
  const seen: string[] = []
  const dash = { period: { from: '2026-10-26', to: '2026-11-01' }, totals: {}, rag: {}, by_category: {}, by_status: {}, trend: [], branches: [], conversion: { since: '2026-09-22', regions: [], total: { validated: 0, logged_in: 0, rejected: 0, open: 0 } } }
  installApiMock('admin', { '/dashboard': (cfg: { params: { period: string } }) => { seen.push(cfg.params.period); return dash } })
  renderApp('/admin/dashboard')
  await userEvent.click(await screen.findByRole('button', { name: 'Last week' }))
  await waitFor(() => expect(seen).toContain('last_week'))
})

test('each entry shows one current status, not its earlier ones', async () => {
  // the server works out the one status (here the login outcome wins over the last call's "In retry")
  const row = entry({ status: 'In retry', selection_status: 'Allocate', lead_outcome: 'Logged in', current_status: 'Logged in', rag: 'NA' })
  installApiMock('sankalp_monitor', { '/entries': { items: [row], total: 1, page: 1, page_size: 25 } })
  renderApp('/admin/entries')
  const table = await screen.findByRole('table')
  expect(await within(table).findByText('Logged in')).toBeInTheDocument()
  expect(within(table).queryByText('In retry')).not.toBeInTheDocument()
  expect(within(table).queryByText('Allocate')).not.toBeInTheDocument()
  expect(within(table).getByText('Mobile: 9876543210')).toBeInTheDocument()  // a number always says what it is
})

test('a second run the same day says nothing new was found, and the day keeps showing what its run did', async () => {
  const today = new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10)
  const first = { id: 'r1', run_date: today, started_at: `${today}T07:41:52Z`, started_by: 'Geetha M',
    counts: { selection: { Allocate: 48 }, allocated: { fresh: 48, retry: 26, followup: 2, priority: 4 }, unreturned: 0 } }
  const empty = { id: 'r2', run_date: today, started_at: `${today}T07:47:00Z`, started_by: 'Geetha M', counts: { selection: {}, allocated: {}, unreturned: 0 } }
  installApiMock('master_owner', {
    '/calls/caller-days': { day: today, items: [] },
    '/calls/allocations': { callers: [], unassigned: 0, first_try_overdue: 0, items: [] },
    '/calls/runs': [empty, first],
  })
  const post = handlers.post
  handlers.post = (url) => (url === '/calls/runs' ? { data: { run_date: today, ...empty.counts } } : post(url))
  renderApp('/callcentre/run')
  expect(await screen.findByText(/Run at .* by Geetha M/)).toBeInTheDocument()
  expect(screen.getByText('Selected for calling')).toBeInTheDocument()
  expect(screen.getAllByText('48 new, 26 retries, 2 follow-ups, 4 PRIORITY').length).toBeGreaterThan(0)
  await userEvent.click(screen.getByRole('button', { name: `Run again for ${today}` }))
  expect(await screen.findByRole('status')).toHaveTextContent('Nothing new to select')
  expect(screen.getAllByRole('row').filter((r) => r.textContent?.includes('Geetha M'))).toHaveLength(1)  // the empty run is not listed
})

test('saving a new caller for a branch after the run says how many new entries went to them', async () => {
  const today = new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10)
  const days = { day: today, items: [{ branch_id: 'b2', branch: 'Nellore', region: 'AP & TG', caller_id: 'c2' }] }
  installApiMock('master_owner', {
    '/calls/caller-days': days, '/calls/runs': [],
    '/calls/allocations': { callers: [], unassigned: 0, first_try_overdue: 0, items: [] },
  })
  handlers.put = (url) => (url === '/calls/caller-days' ? { data: { ...days, moved: 13 } } : (() => { throw new Error(`unhandled PUT ${url}`) })())
  renderApp('/callcentre/run')
  await screen.findByText('Nellore')
  await userEvent.click(screen.getByRole('button', { name: 'Save' }))
  expect(await screen.findByRole('status')).toHaveTextContent('13 new entries not yet called went to the caller now set for their branch')
})
