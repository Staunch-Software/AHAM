// Weighted average IRR pages (docs/irr-module.md): the report and the register upload's error table.
import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, test, vi } from 'vitest'
import { calls, FakeEventSource, handlers, installApiMock, meFor, renderApp } from './helpers'

beforeEach(() => {
  FakeEventSource.instances = []
  vi.stubGlobal('EventSource', FakeEventSource)
})

/** Signed in as `role` with the IRR permissions the server gives it. */
function signIn(role: string, irrPerms: string[], extra: Record<string, unknown> = {}) {
  installApiMock(role, extra)
  const me = meFor(role)
  const base = handlers.get
  handlers.get = (url, cfg) => (url === '/auth/me' ? { data: { ...me, permissions: [...me.permissions, ...irrPerms] } } : base(url, cfg))
}

const cell = (accounts: number, irr: number | null) => ({ accounts, irr, amount: 0, records: accounts })
const REPORT = {
  as_of: '2026-11-05', product: 'HL', level: 'branch', decimals: 2, band: null, warnings: [],
  periods: { TD: { from: '2026-11-05', to: '2026-11-05' }, MTD: { from: '2026-11-01', to: '2026-11-05' }, YTD: { from: '2026-04-01', to: '2026-11-05' } },
  rows: [
    { branch_id: 'b1', region_id: 'r1', code: 'B1', label: 'Vijayawada', region: 'AP & TG', flags: [], periods: { TD: cell(2, 9.12), MTD: cell(2, 9.12), YTD: cell(2, 9.09) } },
    { branch_id: 'b2', region_id: 'r1', code: 'B2', label: 'Guntur', region: 'AP & TG', flags: [], periods: { TD: cell(0, null), MTD: cell(0, null), YTD: cell(0, null) } },
  ],
  total: { label: 'Company total', flags: [], periods: { TD: cell(2, 9.12), MTD: cell(3, 9.24), YTD: cell(3, 9.19) } },
  open_exceptions: { TD: 1, MTD: 1, YTD: 1 },
}
const DETAIL = {
  as_of: '2026-11-05', period: 'MTD', from: '2026-11-01', to: '2026-11-05', decimals: 2, total: 2, page: 1, page_size: 25,
  items: [{ id: 'd1', loan_account: 'HLA', disbursement_ref: '1', disbursement_date: '2026-11-05', branch: 'Vijayawada', branch_code: 'B1', region: 'AP & TG', product: 'Home Loan', product_class: 'HL', amount: 3000000, tenure_months: 240, roi: 9, weight: 720000000, weighted_roi: 6480000000 }],
  totals: { records: 2, accounts: 2, amount: 3500000, weight: 750000000, weighted_roi: 6840000000, irr: 9.12 },
}

test('the IRR report shows accounts and IRR per period, a dash when there is nothing, and opens the loans of a row', async () => {
  signIn('branch_manager', ['irr.view'], { '/irr/report': REPORT, '/irr/detail': DETAIL })
  renderApp('/manage/irr')
  const nav = await screen.findByRole('navigation', { name: 'Main' })
  expect(within(nav).getByRole('link', { name: 'IRR report' })).toHaveAttribute('href', '/manage/irr')
  const row = (await screen.findByRole('button', { name: 'Loans of Guntur' })).closest('tr')!
  expect(within(row).getAllByText('–')).toHaveLength(3)  // no disbursements: no IRR, never 0%
  expect(within(row).queryByText(/0\.00/)).toBeNull()
  const total = screen.getByRole('button', { name: 'Loans of Company total' }).closest('tr')!
  expect(within(total).getByText('9.24')).toBeInTheDocument()
  for (const h of ['Today (TD)', 'Month to date (MTD)', 'Year to date (YTD)']) expect(screen.getByText(h)).toBeInTheDocument()
  expect(screen.getAllByText('Weighted average IRR (%)')).toHaveLength(3)
  expect(screen.getByText(/sum of \(disbursed amount × tenure in months × ROI\)/)).toBeInTheDocument()
  expect(screen.getByText(/1 disbursement of this year to date is left out/)).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Export as Excel' })).toBeInTheDocument()

  await userEvent.click(screen.getByRole('button', { name: 'Loans of Vijayawada' }))
  const dialog = await screen.findByRole('dialog')
  expect(await within(dialog).findByText('HLA')).toBeInTheDocument()
  expect(within(dialog).getByTestId('detail-totals')).toHaveTextContent('Weighted average IRR 9.12%')
  const req = calls.filter((c) => c.url === '/irr/detail').at(-1)!
  expect(req.cfg.params).toMatchObject({ branch_id: 'b1', product: 'HL', period: 'MTD', as_of: '2026-11-05' })
})

test('upload problems are a table of row, column, value found and problem, with a download', async () => {
  signIn('mis', ['irr.view', 'irr.manage'], { '/irr/uploads': [] })
  handlers.post = (url) => {
    if (url === '/irr/disbursements') {
      return { data: {
        dry_run: true, summary: { rows: 8, new: 6, replaced: 0, excluded: 0, exceptions: 1, errors: 1 },
        columns: { 'Disbursement date': 'Date of Disbursement' },
        errors: [{ row: 7, column: 'Date of Disbursement', value: '31/02/2026', message: 'Not a real date. Use DD-MM-YYYY, for example 05-11-2026' }],
      } }
    }
    if (url === '/events/ticket') return { data: { ticket: 'tkt' } }
    throw new Error(url)
  }
  renderApp('/admin/irr-data')
  const nav = await screen.findByRole('navigation', { name: 'Main' })
  expect(within(nav).getAllByRole('link').map((a) => a.textContent)).toEqual(
    expect.arrayContaining(['IRR report', 'Disbursement register', 'IRR exceptions', 'IRR settings']))
  const file = new File(['x'], 'register.csv', { type: 'text/csv' })
  await userEvent.upload(await screen.findByLabelText('Disbursement register file'), file)
  await userEvent.click(screen.getByRole('button', { name: 'Check first' }))
  const table = await screen.findByTestId('row-errors')
  expect(within(table).getAllByRole('columnheader').map((h) => h.textContent)).toEqual(['Row', 'Column', 'Value found', 'Problem'])
  const cells = within(table).getAllByRole('cell').map((c) => c.textContent)
  expect(cells).toEqual(['7', 'Date of Disbursement', '31/02/2026', 'Not a real date. Use DD-MM-YYYY, for example 05-11-2026'])
  expect(screen.getByRole('button', { name: 'Download errors' })).toBeInTheDocument()
  expect(screen.getByText('Check only: nothing was saved.')).toBeInTheDocument()
  expect(screen.getByText(/Disbursement date ← “Date of Disbursement”/)).toBeInTheDocument()
  await waitFor(() => expect(calls.find((c) => c.url === '/irr/disbursements')?.body.get('dry_run')).toBe('true'))
})
