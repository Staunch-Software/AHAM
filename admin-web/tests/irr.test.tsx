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

const cell = (records: number, irr: number | null) => ({ records, irr, amount: 0 })
const REPORT = {
  as_of: '2026-11-05', product: 'HL', level: 'branch', decimals: 2, band: null, warnings: [],
  periods: { TD: { from: '2026-11-05', to: '2026-11-05' }, MTD: { from: '2026-11-01', to: '2026-11-05' }, YTD: { from: '2026-04-01', to: '2026-11-05' } },
  rows: [
    { branch_id: 'b1', region_id: 'r1', code: 'B1', label: 'Vijayawada', region: 'AP & TG', flags: [], periods: { TD: cell(2, 13.03), MTD: cell(2, 13.03), YTD: cell(3, 11.11) } },
    { branch_id: 'b2', region_id: 'r1', code: 'B2', label: 'Guntur', region: 'AP & TG', flags: [], periods: { TD: cell(0, null), MTD: cell(0, null), YTD: cell(0, null) } },
  ],
  total: { label: 'Company total', flags: [], periods: { TD: cell(2, 13.03), MTD: cell(3, 12.76), YTD: cell(4, 11.24) } },
  open_exceptions: { TD: 1, MTD: 1, YTD: 1 },
}
const DETAIL = {
  as_of: '2026-11-05', period: 'MTD', from: '2026-11-01', to: '2026-11-05', decimals: 2, total: 2, page: 1, page_size: 25,
  items: [{ id: 'd1', loan_account: 'HLA', disbursement_ref: '1', disbursement_date: '2026-11-05', branch: 'Vijayawada', branch_code: 'B1', region: 'AP & TG', product: 'Home Loan', product_class: 'HL', amount: 3000000, tenure_months: 240, roi: 9, weight: 720000000, weighted_roi: 6480000000 }],
  totals: { records: 2, amount: 3500000, tenure: 300, average_tenure: 150, denominator: 525000000, weighted_roi: 6840000000, irr: 13.03 },
}

test('the IRR report shows No. and IRR per period, a dash when there is nothing, and opens the loans of a row', async () => {
  signIn('branch_manager', ['irr.view'], { '/irr/report': REPORT, '/irr/detail': DETAIL })
  renderApp('/manage/irr')
  const nav = await screen.findByRole('navigation', { name: 'Main' })
  expect(within(nav).getByRole('link', { name: 'IRR report' })).toHaveAttribute('href', '/manage/irr')
  const row = (await screen.findByRole('button', { name: 'Loans of Guntur' })).closest('tr')!
  expect(within(row).getAllByText('–')).toHaveLength(3)  // no disbursements: no IRR, never 0%
  expect(within(row).queryByText(/0\.00/)).toBeNull()
  const total = screen.getByRole('button', { name: 'Loans of Company total' }).closest('tr')!
  expect(within(total).getByText('12.76')).toBeInTheDocument()
  expect(within(total).getByText('4')).toBeInTheDocument()  // No. counts disbursement rows
  expect(screen.getAllByText('Number of disbursements')).toHaveLength(3)
  for (const h of ['For the day (TD)', 'Month to date (MTD)', 'Year to date (YTD)']) expect(screen.getByText(h)).toBeInTheDocument()
  expect(screen.getAllByText('Weighted average IRR (%)')).toHaveLength(3)
  expect(screen.queryByRole('region', { name: 'How the IRR is worked out' })).toBeNull()  // closed by default
  await userEvent.click(screen.getByRole('button', { name: /Weighted average IRR of Home Loans/ }))
  const how = screen.getByRole('region', { name: 'How the IRR is worked out' })
  expect(how).toHaveTextContent('Weighted average IRR = Σ Transaction IRR ÷ (Σ disbursed amount × average tenure)')
  expect(how).toHaveTextContent("Transaction IRR = disbursed amount × that loan's tenure (months) × ROI")
  expect(how).toHaveTextContent('Average tenure = plain average of the tenures in the period')
  expect(screen.getByText(/1 disbursement of this year to date is left out/)).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Export as Excel' })).toBeInTheDocument()

  await userEvent.click(screen.getByRole('button', { name: 'Loans of Vijayawada' }))
  const dialog = await screen.findByRole('dialog')
  expect(await within(dialog).findByText('HLA')).toBeInTheDocument()
  const totals = within(dialog).getByTestId('detail-totals')
  expect(totals).toHaveTextContent('average tenure 150 months (300 ÷ 2)')
  expect(totals).toHaveTextContent('Weighted average IRR 13.03% = 6,84,00,00,000 ÷ 52,50,00,000')
  const req = calls.filter((c) => c.url === '/irr/detail').at(-1)!
  expect(req.cfg.params).toMatchObject({ branch_id: 'b1', product: 'HL', period: 'MTD', as_of: '2026-11-05' })
  // HL and NHL are never added together: the dialog switches product, it has no "both"
  await userEvent.click(within(dialog).getByRole('button', { name: 'NHL' }))
  await waitFor(() => expect(calls.filter((c) => c.url === '/irr/detail').at(-1)!.cfg.params).toMatchObject({ product: 'NHL' }))
})

test('the report shows one period, or a date range, and the loans of the range with their weight (BRD 3.1, 9)', async () => {
  signIn('mis', ['irr.view', 'irr.manage'], { '/irr/report': REPORT, '/irr/detail': DETAIL, '/irr/uploads': [] })
  const RANGE = {
    ...REPORT, as_of: '2026-11-05', periods: { RANGE: { from: '2026-11-01', to: '2026-11-05', label: '01-11-2026 to 05-11-2026' } },
    rows: REPORT.rows.map((r) => ({ ...r, periods: { RANGE: r.periods.MTD } })), total: { ...REPORT.total, periods: { RANGE: cell(3, 12.76) } },
    open_exceptions: { RANGE: 1 },
  }
  const MTD = { ...REPORT, periods: { MTD: REPORT.periods.MTD }, rows: REPORT.rows.map((r) => ({ ...r, periods: { MTD: r.periods.MTD } })),
    total: { ...REPORT.total, periods: { MTD: REPORT.total.periods.MTD } }, open_exceptions: { MTD: 1 } }
  const base = handlers.get
  handlers.get = (url, cfg) => {
    const p = (cfg?.params ?? {}) as Record<string, unknown>
    if (url === '/irr/report' && p.date_from) return { data: RANGE }
    if (url === '/irr/report' && p.periods === 'MTD') return { data: MTD }
    return base(url, cfg)
  }
  renderApp('/admin/irr')
  await userEvent.click(await screen.findByRole('button', { name: 'Show' }))
  await userEvent.click(await screen.findByRole('option', { name: 'MTD' }))
  await waitFor(() => expect(calls.filter((c) => c.url === '/irr/report').at(-1)!.cfg.params).toMatchObject({ periods: 'MTD' }))
  expect(await screen.findByText('Home Loan (HL): Month to date (MTD)')).toBeInTheDocument()
  expect(screen.queryByText('For the day (TD)')).toBeNull()
  expect(screen.getByText(/1 disbursement of this month to date is left out/)).toBeInTheDocument()

  await userEvent.click(screen.getByRole('button', { name: 'Show' }))
  await userEvent.click(await screen.findByRole('option', { name: 'Date range' }))
  // the range starts on the 1st of the as-of month and ends on the as-of date; the as-of date is not used
  await waitFor(() => expect(calls.filter((c) => c.url === '/irr/report').at(-1)!.cfg.params).toMatchObject({ date_from: '2026-11-01', date_to: '2026-11-05' }))
  expect(calls.filter((c) => c.url === '/irr/report').at(-1)!.cfg.params.as_of).toBeUndefined()
  expect(await screen.findByText('01-11-2026 to 05-11-2026')).toBeInTheDocument()
  expect(screen.queryByLabelText('As of date')).toBeNull()
  expect(screen.getByLabelText('Disbursed from')).toHaveValue('2026-11-01')

  await userEvent.click(screen.getByRole('button', { name: 'Loans of Vijayawada' }))
  const dialog = await screen.findByRole('dialog')
  expect(await within(dialog).findByText('HLA')).toBeInTheDocument()
  const req = calls.filter((c) => c.url === '/irr/detail').at(-1)!
  expect(req.cfg.params).toMatchObject({ branch_id: 'b1', date_from: '2026-11-01', date_to: '2026-11-05' })
  expect(req.cfg.params.period).toBeUndefined()
  expect(within(dialog).queryByRole('group', { name: 'Period' })).toBeNull()
  expect(within(dialog).getByText('Weight (amount × tenure)')).toBeInTheDocument()
  expect(within(dialog).getByText('72,00,00,000')).toBeInTheDocument()  // 30,00,000 × 240
})

test('upload problems are a table of row, column, value found and problem, with a download', async () => {
  const batch = { id: 'u1', filename: 'oct.csv', uploaded_by: 'Indira N', created_at: '2026-11-05T10:00:00Z', rows_total: 8, rows_error: 0,
    summary: { rows: 8, new: 8, replaced: 0, excluded: 0, exceptions: 0, errors: 0 }, errors: [] }
  signIn('mis', ['irr.view', 'irr.manage'], { '/irr/uploads': [batch] })
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
  // every table on a screen can be exported, the upload history too (its export sits in the card's own header, beside the title)
  const history = (await screen.findByText('Upload history')).closest('section')!
  expect(within(history).getByText('oct.csv')).toBeInTheDocument()
  expect(within(history).getByText('Export:')).toBeInTheDocument()
  const file = new File(['x'], 'register.csv', { type: 'text/csv' })
  await userEvent.upload(await screen.findByLabelText('Disbursement register file'), file)
  await userEvent.click(screen.getByRole('button', { name: 'Check first' }))
  const table = await screen.findByTestId('row-errors')
  expect(within(table).getAllByRole('columnheader').map((h) => h.textContent)).toEqual(['Row', 'Column', 'Value found', 'Problem'])
  const cells = within(table).getAllByRole('cell').map((c) => c.textContent)
  expect(cells).toEqual(['7', 'Date of Disbursement', '31/02/2026', 'Not a real date. Use DD-MM-YYYY, for example 05-11-2026'])
  expect(within(table).getByText('Export:')).toBeInTheDocument()  // CSV and Excel, like every table
  expect(screen.getByText('Check only: nothing was saved.')).toBeInTheDocument()
  expect(screen.getByText(/Disbursement date ← “Date of Disbursement”/)).toBeInTheDocument()
  await waitFor(() => expect(calls.find((c) => c.url === '/irr/disbursements')?.body.get('dry_run')).toBe('true'))
})
