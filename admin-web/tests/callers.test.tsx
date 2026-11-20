// Caller allocation by language, absence and the daily limit: the Callers page and the Daily run's flags and moves.
import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, test, vi } from 'vitest'
import { calls, FakeEventSource, handlers, installApiMock, renderApp } from './helpers'

beforeEach(() => {
  FakeEventSource.instances = []
  vi.stubGlobal('EventSource', FakeEventSource)
})

const today = new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10)
const ok = () => ({ data: { moved: 0 } })

test('the Callers page sets languages and marks a caller absent for the day', async () => {
  installApiMock('master_owner', {
    '/calls/callers': {
      day: today, limit: 100, languages: ['Telugu', 'Tamil', 'Kannada'],
      callers: [
        { id: 'jaya', name: 'Jaya', employee_code: 'CC-JAYA', active: true, absent: false, languages: ['Telugu'], usual_branches: ['Anakapalli', 'Nellore'], today_branches: [], load: 120, room: -20, calls_made: 3 },
        { id: 'divya', name: 'Divya S', employee_code: 'AHFL90061', active: true, absent: false, languages: [], usual_branches: [], today_branches: [], load: 0, room: 100, calls_made: 0 },
      ],
      branches: [{ branch_id: 'b1', branch: 'Anakapalli', region: 'AP & TG', languages: ['Telugu'], usual_caller_id: 'jaya', usual_caller: 'Jaya' }],
    },
  })
  handlers.put = ok
  handlers.patch = ok
  renderApp('/callcentre/callers')
  const row = (await screen.findByText('CC-JAYA')).closest('tr')!
  expect(within(row).getByText('Anakapalli, Nellore')).toBeInTheDocument()
  expect(within(row).getByText('120 / 100 (over by 20)')).toBeInTheDocument()
  expect(screen.getByText('Set languages: not used by auto-assign')).toBeInTheDocument()  // Divya has none
  // Jaya also speaks Tamil
  await userEvent.click(within(within(row).getByRole('group', { name: 'Languages of Jaya' })).getByRole('button', { name: 'Tamil' }))
  await waitFor(() => expect(calls.find((c) => c.method === 'patch' && c.url === '/calls/callers/jaya')?.body).toEqual({ languages: ['Telugu', 'Tamil'] }))
  // Jaya is absent today
  await userEvent.click(within(row).getByRole('button', { name: `Jaya absent on ${today}` }))
  await waitFor(() => expect(calls.find((c) => c.method === 'put' && c.url === '/calls/callers/jaya/absence')?.body).toEqual({ day: today, absent: true }))
  // a branch's languages
  await userEvent.click(within(screen.getByRole('group', { name: 'Languages of Anakapalli' })).getByRole('button', { name: 'Kannada' }))
  await waitFor(() => expect(calls.find((c) => c.method === 'put' && c.url === '/calls/branches/b1')?.body).toEqual({ languages: ['Telugu', 'Kannada'] }))
})

test('the Daily run flags an absent caller and an over-limit caller, and applies a suggestion in one click', async () => {
  installApiMock('master_owner', {
    '/calls/caller-days': { day: today, items: [{ branch_id: 'b1', branch: 'Anakapalli', region: 'AP & TG', caller_id: 'jaya', uncalled_count: 25 },
      { branch_id: 'b2', branch: 'Vijayawada', region: 'AP & TG', caller_id: 'raji', uncalled_count: 0 }] },
    '/calls/allocations': { callers: [{ id: 'raji', name: 'Raji', active: true, open: 140, attempts_today: 0, first_try_overdue: 0 }], unassigned: 0, first_try_overdue: 0, items: [] },
    '/calls/runs': [],
    '/calls/day-plan': {
      day: today, limit: 100,
      branches: [
        { branch_id: 'b1', branch: 'Anakapalli', caller_id: 'jaya', caller: 'Jaya', waiting: 25, flags: [{ code: 'absent', message: 'Jaya is absent today – change the caller' }], suggestion: { caller_id: 'sita', caller: 'Sita', room: 60 } },
        { branch_id: 'b2', branch: 'Vijayawada', caller_id: 'raji', caller: 'Raji', waiting: 0, flags: [{ code: 'over_limit', message: 'Raji is over the limit by 40' }], suggestion: null },
      ],
      callers: [{ id: 'raji', name: 'Raji', absent: false, load: 140, room: -40, over: 40 }, { id: 'jaya', name: 'Jaya', absent: true, load: 0, room: 100, over: 0 }],
      moves: [{ kind: 'entries', from_id: 'raji', from: 'Raji', to_id: 'sita', to: 'Sita', branch_id: 'b2', branch: 'Vijayawada', count: 40, languages: ['Telugu'] }],
    },
  })
  const post = handlers.post
  handlers.post = (url, body) => (url === '/calls/allocations/move' ? { data: { moved: 40 } }
    : url === '/calls/caller-days/auto' ? { data: { day: today, items: [], moved: 0, auto: { assigned: 2, no_caller: [] } } } : post(url, body))
  handlers.put = () => ({ data: { day: today, items: [], moved: 25 } })
  renderApp('/callcentre/run')
  expect(await screen.findByText('Jaya is absent today – change the caller')).toBeInTheDocument()
  expect(screen.getByText('Raji is over the limit by 40')).toBeInTheDocument()
  await userEvent.click(screen.getByRole('button', { name: 'Use Sita (room for 60)' }))
  await waitFor(() => expect(calls.filter((c) => c.method === 'put' && c.url === '/calls/caller-days').at(-1)?.body)
    .toEqual({ day: today, assignments: [{ branch_id: 'b1', caller_id: 'sita' }] }))
  const moves = screen.getByTestId('limit-moves')
  expect(moves).toHaveTextContent("Raji has 140 today. Sita speaks Telugu and has room: 40 of Vijayawada's new entries.")
  await userEvent.click(within(moves).getByRole('button', { name: 'Move 40' }))
  await waitFor(() => expect(calls.find((c) => c.url === '/calls/allocations/move')?.body)
    .toEqual({ from_caller_id: 'raji', to_caller_id: 'sita', branch_id: 'b2', count: 40 }))
  await userEvent.click(screen.getByRole('button', { name: 'Auto-assign' }))
  expect(await screen.findByText('Auto-assigned 2 branches.')).toBeInTheDocument()
})
