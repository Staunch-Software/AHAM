import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, test, vi } from 'vitest'
import { currentSlot, dsaLogic, hasLoanType, leadLogic } from '../src/services/classify'
import { calls, FakeEventSource, handlers, installApiMock, renderApp } from './helpers'

beforeEach(() => {
  FakeEventSource.instances = []
  vi.stubGlobal('EventSource', FakeEventSource)
})

function entry(over: Record<string, unknown> = {}) {
  return {
    id: 'e1', entry_code: 'AHFL90001-20261020-100000', emp_code: 'AHFL90001', so_user_id: 's1', so_name: 'Ravi Kumar', so_employee_code: 'AHFL90001',
    branch_id: 'b1', branch_name: 'Vijayawada', region_name: 'AP & TG', category: 'lead', category_label: 'Lead', cp_subtype_label: null, call_group: 'lead',
    person_name: 'Suresh', phone: '9876543210', submitted_at_device: '2026-10-20T04:30:00Z', received_at_server: '2026-10-20T04:31:00Z',
    entry_date: '2026-10-20', count_date: '2026-10-20', device_time_suspect: false, selection_status: 'Allocate', status: null, rag: 'PENDING',
    rag_overridden: false, priority: false, so_action: null, so_action_date: null, so_action_until: null, cc_action: null, cc_action_date: null,
    lead_outcome: null, tcs_id: null, customer_validated: false, sankalp_success: false, photo_count: 0, has_location: true, place_name: null,
    description: 'Wants a loan for a plot', keka_photo_time: null, phone_raw: '9876543210', device_tz_offset_min: 330, spoke: null,
    location: { latitude: 16.5, longitude: 80.6, accuracy_m: 10, fix_at_device: null, status: 'obtained', place_name: 'Benz Circle', place_status: 'done' },
    original_so_user_id: 's1', call_cycle: 1, unanswered_count: 0, callback_date: null, validated_on: null, first_validation: false, login_date: null,
    login_source: null, category_review: null, photos: [], history: [], first_caller: null, on_list_of: [], attempts: [], lead_card: null,
    branch_answers: [], tracker: null, same_number: [], ...over,
  }
}

test('classification preview follows section 8 in order', () => {
  expect(leadLogic({})).toBe('Amber – answers missing')
  expect(leadLogic({ loan_need: 'LAP', documents: 'File already logged with Aham' })).toBe('Not counted – LAP')
  expect(leadLogic({ loan_need: 'Home purchase', relationship: 'Yes – the same officer', name_check: 'Different person' })).toBe('Amber – knows SO')
  expect(leadLogic({ loan_need: 'Home purchase', name_check: 'Different person – same family', visit: 'No' })).toBe('Validated – different person')
  expect(dsaLogic({ dsa_rag: 'Green' })).toBe('DSA/CP – Green')
  expect(dsaLogic({})).toBe('DSA/CP – no RAG')
  expect(dsaLogic({ needs_home_loan: 'Yes', loan_need: 'Home purchase', visit: 'No' })).toBe('Validated – converted from DSA/CP')
  expect(hasLoanType({ loan_need: 'Not looking for a loan' })).toBe(false)
  expect(currentSlot(['09-10', '12-01', '01-02'], new Date(2026, 9, 20, 13, 5))).toBe('01-02')
  expect(currentSlot(['09-10', '12-01'], new Date(2026, 9, 20, 12, 30))).toBe('12-01')
  expect(currentSlot(['09-10'], new Date(2026, 9, 20, 22, 0))).toBe('09-10')
})

test('the caller records a connected call with the lead questions and sees the status it will produce', async () => {
  installApiMock('caller', { '/entries/e1': entry() })
  handlers.post = (url, body) => {
    if (url === '/events/ticket') return { data: { ticket: 't' } }
    if (url === '/calls/entries/e1/attempts') return { data: { row_status: 'Validated – visit not confirmed', rag: 'GREEN', ...body } }
    throw new Error(url)
  }
  renderApp('/callcentre/calls/e1')
  expect(await screen.findByRole('link', { name: /98765 43210/ })).toHaveAttribute('href', 'tel:9876543210')
  await userEvent.click(screen.getByRole('button', { name: 'Connected' }))
  const visit = screen.getByRole('group', { name: 'Visit: did the SO meet you?' })
  await userEvent.click(within(visit).getByRole('button', { name: 'No' }))
  expect(screen.getByTestId('status-preview')).toHaveTextContent('Amber – answers missing')
  await userEvent.click(within(screen.getByRole('group', { name: 'Loan need' })).getByRole('button', { name: 'Home purchase' }))
  expect(screen.getByTestId('status-preview')).toHaveTextContent('Validated – visit not confirmed')
  await userEvent.click(screen.getByRole('button', { name: 'Save try' }))
  await screen.findByRole('status')
  const post = calls.find((c) => c.url === '/calls/entries/e1/attempts')!
  expect(post.body.outcome).toBe('Connected')
  expect(post.body.answers).toEqual({ visit: 'No', loan_need: 'Home purchase' })
  expect(post.body.slot).toMatch(/^\d\d-\d\d$/)
})

test('a DSA/CP call asks the RAG and switches to the lead questions when he needs a loan', async () => {
  installApiMock('caller', { '/entries/e1': entry({ call_group: 'dsa_cp', category: 'contact_point', category_label: 'Contact Point', cp_subtype_label: 'Other Hardware Shop' }) })
  renderApp('/callcentre/calls/e1')
  await userEvent.click(await screen.findByRole('button', { name: 'Connected' }))
  expect(screen.queryByRole('group', { name: 'Loan need' })).toBeNull()
  await userEvent.click(within(screen.getByRole('group', { name: 'RAG given by caller' })).getByRole('button', { name: 'Amber' }))
  expect(screen.getByTestId('status-preview')).toHaveTextContent('DSA/CP – Amber')
  await userEvent.click(within(screen.getByRole('group', { name: 'Needs a home loan himself?' })).getByRole('button', { name: 'Yes' }))
  expect(screen.getByRole('group', { name: 'Loan need' })).toBeInTheDocument()
})

test('a callback needs its date before it can be saved', async () => {
  installApiMock('caller', { '/entries/e1': entry() })
  renderApp('/callcentre/calls/e1')
  await userEvent.click(await screen.findByRole('button', { name: 'Callback requested' }))
  expect(screen.getByRole('button', { name: 'Save try' })).toBeDisabled()
  expect(screen.getByLabelText('Call back on (working day)')).toBeInTheDocument()
})

test('the lead card appears once a loan type is known and refuses a lead ID without the loan requirement', async () => {
  const attempts = [{ id: 'a1', call_date: '2026-10-21', slot: '10-11', outcome: 'Connected', cycle: 1, next_date: null, answers: { loan_need: 'Home purchase' }, row_status: 'Validated', caller: 'Divya', at: '' }]
  installApiMock('caller', { '/entries/e1': entry({ attempts, status: 'Validated' }) })
  handlers.put = (url, body) => ({ data: body })
  renderApp('/callcentre/calls/e1')
  await userEvent.type(await screen.findByLabelText('TCS lead ID (when the lead is generated)'), 'TCS-1')
  expect(screen.getByText('Compulsory once a lead ID is entered')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Save lead card' })).toBeDisabled()
  await userEvent.type(screen.getByLabelText(/Loan requirement/), '45,00,000')
  await userEvent.click(screen.getByRole('button', { name: 'Save lead card' }))
  await waitFor(() => expect(calls.find((c) => c.url === '/calls/entries/e1/lead-card')?.body).toMatchObject({ lead_id: 'TCS-1', loan_requirement: 4500000 }))
})

test('the BM answers a lead with a code and the date the code asks for', async () => {
  const lead = { ...entry({ status: 'Validated', so_action: 'Follow up lead', rag: 'GREEN' }), branch_answer: null }
  installApiMock('branch_manager', { '/branch/leads': { today: '2026-10-21', items: [lead] }, '/branch/missed-dates': [] })
  handlers.post = (url, body) => {
    if (url === '/events/ticket') return { data: { ticket: 't' } }
    if (url === '/branch/leads/e1/answer') return { data: body }
    throw new Error(url)
  }
  renderApp('/manage/leads')
  await userEvent.click(await screen.findByRole('button', { name: 'Answer' }))
  const dialog = screen.getByRole('dialog')
  await userEvent.selectOptions(within(dialog).getByLabelText('Code'), 'A1')
  const save = within(dialog).getByRole('button', { name: 'Save answer' })
  expect(save).toBeDisabled()  // A1 asks for the login date
  await userEvent.type(within(dialog).getByLabelText('Login date'), '2026-10-30')
  await userEvent.click(save)
  await waitFor(() => expect(calls.find((c) => c.url === '/branch/leads/e1/answer')?.body).toEqual({ code: 'A1', answer_date: '2026-10-30', note: null }))
})

test('entries list shows status and RAG for the scope', async () => {
  installApiMock('branch_manager', { '/entries': { items: [entry({ status: 'In retry', rag: 'RNR', so_action: null })], total: 1, page: 1, page_size: 25 } })
  renderApp('/manage/entries')
  expect(await screen.findByText('AHFL90001-20261020-100000')).toBeInTheDocument()
  const row = screen.getByText('AHFL90001-20261020-100000').closest('tr')!
  expect(within(row).getByText('In retry')).toBeInTheDocument()
  expect(within(row).getByText('RNR')).toBeInTheDocument()
})

test('uploads check a file first without saving it', async () => {
  installApiMock('admin', { '/imports': [] })
  handlers.post = (url, body) => {
    if (url === '/events/ticket') return { data: { ticket: 't' } }
    if (url === '/imports/roster') return { data: { dry_run: body.get('dry_run') === 'true', summary: { created: 2 }, errors: [] } }
    throw new Error(url)
  }
  renderApp('/admin/uploads')
  const file = new File(['Emp ID,Name\nA1,X\n'], 'roster.csv', { type: 'text/csv' })
  await userEvent.upload(await screen.findByLabelText('Employee roster (FOS Spoke) file'), file)
  await userEvent.click(screen.getAllByRole('button', { name: 'Check first' })[0]!)
  expect(await screen.findByText('Check only: nothing was saved.')).toBeInTheDocument()
  expect((calls.find((c) => c.url === '/imports/roster')!.body as FormData).get('dry_run')).toBe('true')
})
