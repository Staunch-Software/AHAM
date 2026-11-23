import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, test, vi } from 'vitest'
import { calls, FakeEventSource, handlers, installApiMock, meFor, renderApp } from './helpers'

beforeEach(() => {
  FakeEventSource.instances = []
  vi.stubGlobal('EventSource', FakeEventSource)
})

const DASH = {
  period: { from: '2026-10-21', to: '2026-10-21' },
  totals: { entries: 12, lead_prospect: 7, dsa_cp: 3, validated: 4, logged_in: 1, sankalp_success: 1, awaiting_call: 2, open_so_actions: 3, active_sos: 2 },
  rag: { GREEN: 4, AMBER: 2 }, by_category: { Lead: 5 }, by_status: { Validated: 4 }, trend: [{ day: '2026-10-21', entries: 12 }], branches: [],
  conversion: {
    since: '2026-09-22',
    regions: [{ region: 'Karnataka', validated: 4, logged_in: 1, rejected: 1, open: 2 }, { region: 'Chennai 1', validated: 6, logged_in: 3, rejected: 0, open: 3 }],
    total: { validated: 10, logged_in: 4, rejected: 1, open: 5 },
  },
}

test('the root path renders the unified sign-in page without exposing internal workflows', async () => {
  installApiMock(null)
  renderApp('/')
  expect(screen.getByRole('heading', { name: /sign in/i })).toBeInTheDocument()
  expect(screen.queryByTestId('portal-manage')).not.toBeInTheDocument()
  expect(screen.queryByText(/SO meets a customer/i)).not.toBeInTheDocument()
})

test('sign-in sends credentials and routes to the user portal without choosing', async () => {
  installApiMock(null)
  handlers.post = (url) => {
    if (url === '/auth/login') return { data: { access_token: 'new-tok', refresh_token: 'new-ref', portal: 'manage', role: 'branch_manager' } }
    throw new Error(url)
  }
  renderApp('/login')
  await userEvent.type(await screen.findByLabelText('Emp ID or email'), 'AHFL90061')
  await userEvent.type(screen.getByLabelText('Password'), 'secret')
  await userEvent.click(screen.getByRole('button', { name: 'Sign in' }))
  expect(calls.find((c) => c.url === '/auth/login')?.body).toEqual({ identifier: 'AHFL90061', password: 'secret' })
})

test('mobile-only account shows configured for mobile app message', async () => {
  installApiMock(null)
  handlers.post = (url) => {
    if (url === '/auth/login') throw Object.assign(new Error('403'), { response: { status: 403, data: { detail: { code: 'mobile_only', portal: 'mobile', message: 'This account is configured for the AHAM Sankalp mobile app.' } } } })
    throw new Error(url)
  }
  renderApp('/login')
  await userEvent.type(await screen.findByLabelText('Emp ID or email'), 'AHFL90061')
  await userEvent.type(screen.getByLabelText('Password'), 'secret')
  await userEvent.click(screen.getByRole('button', { name: 'Sign in' }))
  const alert = await screen.findByRole('alert')
  expect(alert).toHaveTextContent('This account is configured for the AHAM Sankalp mobile app.')
})

test('a temporary password must be replaced before the portal opens', async () => {
  installApiMock('branch_manager')
  const me = meFor('branch_manager', { must_change_password: true })
  const base = handlers.get
  handlers.get = (url, cfg) => (url === '/auth/me' ? { data: { ...me } } : base(url, cfg))
  handlers.post = (url) => {
    if (url === '/auth/change-password') { me.must_change_password = false; return { data: { access_token: 'a', refresh_token: 'r' } } }
    if (url === '/events/ticket') return { data: { ticket: 't' } }
    throw new Error(url)
  }
  handlers.get = ((orig) => (url: string, cfg?: any) => (url === '/dashboard' ? { data: DASH } : orig(url, cfg)))(handlers.get)
  renderApp('/manage')
  expect(await screen.findByText('Choose your own password')).toBeInTheDocument()
  await userEvent.type(screen.getByLabelText('Temporary password'), 'Temp1234')
  await userEvent.type(screen.getByLabelText('New password'), 'mine-1234')
  await userEvent.type(screen.getByLabelText('New password again'), 'mine-1234')
  await userEvent.click(screen.getByRole('button', { name: 'Save and continue' }))
  expect(await screen.findByTestId('kpi-entries')).toHaveTextContent('12')
  expect(calls.find((c) => c.url === '/auth/change-password')?.body).toEqual({ current_password: 'Temp1234', new_password: 'mine-1234' })
})

test('the menu shows only what the role may do', async () => {
  installApiMock('branch_manager', { '/dashboard': DASH })
  const { unmount } = renderApp('/manage')
  const nav = await screen.findByRole('navigation', { name: 'Main' })
  expect(within(nav).getByText('Leads to answer')).toBeInTheDocument()
  expect(within(nav).getByText('Team')).toBeInTheDocument()
  expect(await screen.findByTestId('kpi-entries')).toHaveTextContent('12')
  // lead conversion by region, as the Takeoff master: 1 of 4 validated leads logged in
  expect(screen.getByRole('row', { name: /Karnataka 4 1 1 2 25.0%/ })).toBeInTheDocument()
  expect(screen.getByRole('row', { name: /Total 10 4 1 5 40.0%/ })).toBeInTheDocument()  // every entry since Takeoff start
  expect(screen.getByText(/entries made from 2026-09-22 to today/)).toBeInTheDocument()
  unmount()

  installApiMock('product_manager', { '/dashboard': DASH })
  const pm = renderApp('/manage')
  const nav2 = await screen.findByRole('navigation', { name: 'Main' })
  expect(within(nav2).queryByText('Leads to answer')).toBeNull()  // only BMs and RBHs answer leads
  pm.unmount()

  installApiMock('mis')
  renderApp('/admin')
  const nav3 = await screen.findByRole('navigation', { name: 'Main' })
  expect(within(nav3).getAllByRole('link').map((a) => a.textContent)).toEqual(['Uploads'])
  expect(await screen.findByText('Login register (MIS)')).toBeInTheDocument()
  expect(screen.queryByText('Employee roster (FOS Spoke)')).toBeNull()
})

test('menu links point inside the portal from any page, not below the current one', async () => {
  installApiMock('branch_manager', { '/dashboard': DASH })
  const { unmount } = renderApp('/manage/dashboard')
  const nav = await screen.findByRole('navigation', { name: 'Main' })
  expect(within(nav).getByRole('link', { name: 'Team' })).toHaveAttribute('href', '/manage/team')
  expect(within(nav).getByRole('link', { name: 'Dashboard' })).toHaveAttribute('href', '/manage/dashboard')
  unmount()

  installApiMock('mis')
  renderApp('/admin')  // the portal home redirects to the first page; its link must not grow to /admin/uploads/uploads
  expect(await screen.findByText('Login register (MIS)')).toBeInTheDocument()
  const nav2 = screen.getByRole('navigation', { name: 'Main' })
  expect(within(nav2).getByRole('link', { name: 'Uploads' })).toHaveAttribute('href', '/admin/uploads')
})

test('a page outside the role is refused, and a session of another portal is not reused', async () => {
  installApiMock('caller', { '/calls/my-list': { today: '2026-10-21', items: [] } })
  const { unmount } = renderApp('/callcentre/run')
  expect(await screen.findByText('Your role cannot open this page.')).toBeInTheDocument()
  unmount()
  installApiMock('caller', { '/calls/my-list': { today: '2026-10-21', items: [] } })
  renderApp('/admin')  // a caller's session opened at another portal automatically routes to their own portal
  expect(await screen.findByRole('heading', { name: 'My calls' })).toBeInTheDocument()
})

test('live updates subscribe to the entry stream and refetch on a new entry', async () => {
  let n = 0
  installApiMock('branch_manager', { '/dashboard': () => { n += 1; return DASH } })
  renderApp('/manage/dashboard')
  await screen.findByTestId('kpi-entries')
  await waitFor(() => expect(FakeEventSource.instances.length).toBe(1))
  const es = FakeEventSource.instances[0]!
  expect(es.url).toBe('/api/v1/events/stream?ticket=tkt')
  const before = n
  es.emit('entry.created')
  await waitFor(() => expect(n).toBeGreaterThan(before))
})

test('dashboard KPI cards link to entries filtered by period and metric', async () => {
  installApiMock('branch_manager', {
    '/dashboard': DASH,
    '/entries': { items: [], total: 0, page: 1, page_size: 25 },
  })
  renderApp('/manage/dashboard')
  const entriesKpi = await screen.findByTestId('kpi-entries')
  const entriesLink = entriesKpi.closest('a')!
  expect(entriesLink).toHaveAttribute('href', '/manage/entries?date_from=2026-10-21&date_to=2026-10-21&date_field=count')

  const validatedKpi = screen.getByTestId('kpi-validated')
  const validatedLink = validatedKpi.closest('a')!
  expect(validatedLink).toHaveAttribute('href', '/manage/entries?date_from=2026-10-21&date_to=2026-10-21&date_field=count&customer_validated=true')

  // Clicking the KPI card navigates to Entries page and shows the active dashboard filter banner
  await userEvent.click(validatedLink)
  expect(await screen.findByText('Filtered from Dashboard:')).toBeInTheDocument()
  expect(screen.getByText('Customers validated')).toBeInTheDocument()
  expect(screen.getByText(/Count date: 2026-10-21 to 2026-10-21/)).toBeInTheDocument()

  // Clicking "Clear dashboard filter" resets the filter banner
  await userEvent.click(screen.getByRole('button', { name: /Clear dashboard filter/i }))
  expect(screen.queryByText('Filtered from Dashboard:')).not.toBeInTheDocument()
})
