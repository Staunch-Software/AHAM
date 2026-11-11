import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowRightLeft, Copy, Play, Save, UserPlus } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Button, Card, EmptyState, ErrorBox, Input, Note, PageTitle, Select, Skeleton, StatCard, Table, Td } from '../../components/ui'
import { api, errorMessage } from '../../services/api'
import { useAuth } from '../../services/auth'
import { useCallers } from '../../services/meta'
import type { CallRow } from '../../types'

interface Days { day: string; items: { branch_id: string; branch: string; region: string | null; caller_id: string | null }[] }
interface Overview { callers: { id: string; name: string; active: boolean; open: number; attempts_today: number; first_try_overdue: number }[]; unassigned: number; first_try_overdue: number; items: CallRow[] }
interface Run { id: string; run_date: string; started_at: string; started_by: string; counts: { selection: Record<string, number>; allocated: Record<string, number>; unreturned: number } }

const isoToday = () => new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10)
const isoMinus = (d: string, n: number) => new Date(Date.parse(`${d}T00:00:00Z`) - n * 86400000).toISOString().slice(0, 10)
const clock = (iso: string) => new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

// The run's counts in the document's words (the API keys are fresh/retry/followup/priority and "Allocate").
const KINDS: [string, string][] = [['fresh', 'new'], ['retry', 'retries'], ['followup', 'follow-ups'], ['priority', 'PRIORITY']]
const decision = (k: string) => (k === 'Allocate' ? 'Selected for calling' : k)
const listed = (a: Record<string, number> = {}) => KINDS.filter(([k]) => a[k]).map(([k, label]) => `${a[k]} ${label}`).join(', ')
// A run again the same day only adds what came in since; one that found nothing is not worth showing.
const did = (c?: Run['counts'] | null) => !!c && (Object.keys(c.selection ?? {}).length > 0 || Object.keys(c.allocated ?? {}).length > 0 || c.unreturned > 0)

function RunCounts({ c }: { c: Run['counts'] }) {
  return (
    <div className="space-y-1 text-sm">
      {Object.entries(c.selection ?? {}).map(([k, v]) => <p key={k} className="flex justify-between"><span className="text-slate-600">{decision(k)}</span><strong>{v}</strong></p>)}
      <p className="flex justify-between gap-3 border-t border-slate-100 pt-1"><span className="text-slate-600">Put on lists</span><strong className="text-right">{listed(c.allocated) || 'none'}</strong></p>
      {c.unreturned ? <p className="flex justify-between"><span className="text-slate-600">Not called on their day, offered again</span><strong>{c.unreturned}</strong></p> : null}
    </div>
  )
}

/** Sections 5-6: each morning one caller per branch, then the run selects new entries and fills the callers' lists. */
export default function DailyRun() {
  const qc = useQueryClient()
  const { path } = useAuth()
  const [day, setDay] = useState(isoToday())
  const { data: callers } = useCallers()
  const days = useQuery({ queryKey: ['caller-days', day], queryFn: async () => (await api.get<Days>('/calls/caller-days', { params: { day } })).data })
  const overview = useQuery({ queryKey: ['calls', 'overview'], queryFn: async () => (await api.get<Overview>('/calls/allocations', { params: { unassigned: true } })).data })
  const runs = useQuery({ queryKey: ['calls', 'runs'], queryFn: async () => (await api.get<Run[]>('/calls/runs')).data })
  const [pick, setPick] = useState<Record<string, string>>({})
  useEffect(() => { if (days.data) setPick(Object.fromEntries(days.data.items.map((i) => [i.branch_id, i.caller_id ?? '']))) }, [days.data])
  const refresh = () => ['caller-days', 'calls', 'entries', 'dashboard'].forEach((k) => qc.invalidateQueries({ queryKey: [k] }))
  // Saving a branch's caller after the run also hands that branch's waiting new entries to the new caller.
  const [moved, setMoved] = useState<number | null>(null)
  const saved = (r: { moved: number }) => { setMoved(r.moved); refresh() }
  const save = useMutation({ mutationFn: async () => (await api.put<{ moved: number }>('/calls/caller-days', { day, assignments: Object.entries(pick).map(([branch_id, caller_id]) => ({ branch_id, caller_id: caller_id || null })) })).data, onSuccess: saved })
  const copy = useMutation({ mutationFn: async () => (await api.post<{ moved: number }>('/calls/caller-days/copy', { from_day: isoMinus(day, 1), to_day: day })).data, onSuccess: saved })
  const run = useMutation({ mutationFn: async () => (await api.post('/calls/runs', { run_date: day })).data as Run['counts'] & { run_date: string }, onSuccess: refresh })
  const assign = useMutation({ mutationFn: ({ id, caller }: { id: string; caller: string }) => api.post(`/calls/allocations/${id}/assign`, { caller_id: caller }), onSuccess: refresh })
  // A caller is off: their whole open list (retries and PRIORITY calls too) goes to another caller for the day.
  const move = useMutation({ mutationFn: async ({ from, to }: { from: string; to: string }) => (await api.post<{ moved: number }>('/calls/allocations/move', { from_caller_id: from, to_caller_id: to })).data, onSuccess: refresh })
  const activeCallers = callers?.filter((c) => c.status === 'active') ?? []
  const setAll = (caller: string) => setPick(Object.fromEntries(Object.keys(pick).map((b) => [b, caller])))
  const dayRuns = (runs.data ?? []).filter((r) => r.run_date === day && did(r.counts))
  const ranNow = run.data?.run_date === day ? run.data : null
  return (
    <>
      <PageTitle subtitle="Entries are called from the day after they are made. Retries go back to the caller who first handled the entry."
        actions={<Input type="date" aria-label="Run date" value={day} max={isoToday()} onChange={(e) => { setDay(e.target.value); setMoved(null) }} className="w-auto" />}>
        Daily run & allocation
      </PageTitle>
      <ErrorBox error={[save.error, copy.error, run.error, assign.error, move.error].map((e) => e && errorMessage(e)).find(Boolean) ?? null} />

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
        <Card title="1 · Caller of the day per branch" subtitle="New entries of a branch go to its caller of the day"
          actions={<div className="flex gap-2">
            <Button variant="secondary" small disabled={copy.isPending} onClick={() => copy.mutate()}><Copy size={14} aria-hidden="true" />Copy yesterday</Button>
            <Button small disabled={save.isPending} onClick={() => save.mutate()}><Save size={14} aria-hidden="true" />Save</Button>
          </div>}>
          {days.isLoading ? <Skeleton className="h-40" /> : (
            <>
              {moved !== null && (
                <p className="mb-3 rounded-xl bg-emerald-50 px-3 py-2 text-sm text-emerald-800" role="status">
                  Saved.{moved ? ` ${moved} new ${moved === 1 ? 'entry' : 'entries'} not yet called went to the caller now set for ${moved === 1 ? 'its' : 'their'} branch. Retries stay with their first caller.` : ''}
                </p>
              )}
              <div className="mb-3 flex items-center gap-2 text-xs text-slate-500">Set all to
                <Select className="w-auto py-1 text-xs" value="" onChange={(e) => e.target.value && setAll(e.target.value)}><option value="">choose…</option>{activeCallers.map((c) => <option key={c.id} value={c.id}>{c.full_name}</option>)}</Select>
              </div>
              <div className="max-h-[420px] overflow-y-auto rounded-xl border border-slate-100">
                <table className="w-full text-sm">
                  <tbody className="divide-y divide-slate-100">
                    {days.data?.items.map((b) => (
                      <tr key={b.branch_id}>
                        <td className="px-3 py-2"><span className="font-medium text-slate-800">{b.branch}</span><span className="ml-2 text-xs text-slate-400">{b.region}</span></td>
                        <td className="w-48 px-3 py-1.5">
                          <Select aria-label={`Caller for ${b.branch}`} className="py-1.5" value={pick[b.branch_id] ?? ''} onChange={(e) => setPick({ ...pick, [b.branch_id]: e.target.value })}>
                            <option value="">No caller</option>{activeCallers.map((c) => <option key={c.id} value={c.id}>{c.full_name}</option>)}
                          </Select>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </Card>

        <div className="space-y-6">
          <Card title="2 · Run the selection" subtitle="Checks each new entry in order (no valid number, repeat, duplicate, being called, spoken to) and fills the lists">
            <Button variant="gold" className="w-full py-2.5" disabled={run.isPending} onClick={() => run.mutate()}><Play size={16} aria-hidden="true" />{run.isPending ? 'Running…' : `${dayRuns.length ? 'Run again' : 'Run'} for ${day}`}</Button>
            {ranNow && !did(ranNow) && (
              <p className="mt-4 rounded-xl bg-brand-50 px-3 py-2 text-sm text-brand-800" role="status">
                Nothing new to select{dayRuns.length ? `: ${day} was already run, below` : ` for ${day}`}. Running again only adds entries and calls that came in since.
              </p>
            )}
            {dayRuns.map((r) => (
              <div key={r.id} className="mt-4">
                <p className="mb-1 text-xs font-medium text-slate-500">Run at {clock(r.started_at)} by {r.started_by}</p>
                <RunCounts c={r.counts} />
              </div>
            ))}
            {!dayRuns.length && !ranNow && <p className="mt-3 text-xs text-slate-500">Not run yet for {day}.</p>}
            {overview.data?.unassigned ? <p className="mt-3 text-sm text-roof-600">{overview.data.unassigned} have no caller yet: set the branch’s caller and Save, or assign them below.</p> : null}
          </Card>
          <div className="grid grid-cols-3 gap-4">
            <StatCard label="Unassigned work" value={overview.data?.unassigned ?? '—'} tone="red" />
            <StatCard label="First try overdue" value={overview.data?.first_try_overdue ?? '—'} tone="gold" testId="kpi-overdue" hint="On a list, not called within the target" />
            <StatCard label="Tries today" value={overview.data?.callers.reduce((a, c) => a + c.attempts_today, 0) ?? '—'} tone="green" />
          </div>
        </div>
      </div>

      <Card title="Callers" subtitle="A caller who is off today: move their open list (retries and PRIORITY calls too) to another caller" className="mt-6" flush>
        {move.data && <p className="px-5 pt-3 text-sm text-emerald-700" role="status">{move.data.moved} moved.</p>}
        <Table head={['Caller', 'Still to call today', 'Not called within the target (overdue)', 'Calls made today', 'Move today’s list to', '']} exportName="Callers today">
          {overview.data?.callers.map((c) => (
            <tr key={c.id}><Td className="font-medium">{c.name}{!c.active && <span className="ml-2 text-xs text-slate-400">inactive</span>}</Td><Td className="tabular">{c.open}</Td>
              <Td className="tabular">{c.first_try_overdue || 0}</Td><Td className="tabular">{c.attempts_today}</Td>
              <Td>{c.open > 0 ? (
                <Select aria-label={`Move ${c.name}'s list`} className="w-44 py-1.5" value="" disabled={move.isPending}
                  onChange={(e) => e.target.value && move.mutate({ from: c.id, to: e.target.value })}>
                  <option value="">Choose…</option>{activeCallers.filter((x) => x.id !== c.id).map((x) => <option key={x.id} value={x.id}>{x.full_name}</option>)}
                </Select>) : <span className="inline-flex items-center gap-1 text-xs text-slate-400"><ArrowRightLeft size={12} aria-hidden="true" />nothing open</span>}</Td>
              <Td><Link className="text-xs font-semibold text-brand-700 hover:underline" to={`${path('calls')}`}>Lists</Link></Td></tr>
          ))}
        </Table>
      </Card>

      <Card title="Work with no caller" subtitle="The branch had no caller of the day" className="mt-6" flush>
        {!overview.data?.items.length ? <EmptyState icon={<UserPlus size={20} />} title="Everything is on a caller's list." /> : (
          <Table head={['Entry ID', 'Person met', 'Branch', 'List', 'Assign to caller']} exportName="Work with no caller">
            {overview.data.items.map((r) => (
              <tr key={r.allocation_id}>
                <Td><Link className="font-mono text-xs font-semibold text-brand-700 hover:underline" to={path(`entries/${r.id}`)}>{r.entry_code}</Link></Td>
                <Td>{r.person_name}</Td><Td>{r.branch_name}</Td><Td>{r.kind}</Td>
                <Td><Select aria-label={`Assign ${r.entry_code}`} className="w-44 py-1.5" value="" onChange={(e) => e.target.value && assign.mutate({ id: r.allocation_id, caller: e.target.value })}>
                  <option value="">Choose…</option>{activeCallers.map((c) => <option key={c.id} value={c.id}>{c.full_name}</option>)}</Select></Td>
              </tr>
            ))}
          </Table>
        )}
      </Card>

      <Card title="Recent runs" className="mt-6" flush>
        {runs.data?.some((r) => did(r.counts)) ? (
          <>
            <Table head={['Run date', 'Started at', 'Started by', 'Entries decided', 'Put on callers’ lists', 'Not done before, offered again']} exportName="Daily runs">
              {runs.data.filter((r) => did(r.counts)).map((r) => (
                <tr key={r.id}><Td>{r.run_date}</Td><Td>{new Date(r.started_at).toLocaleString()}</Td><Td>{r.started_by}</Td>
                  <Td className="text-xs">{Object.entries(r.counts.selection ?? {}).map(([k, v]) => `${v} ${decision(k)}`).join(' · ') || '—'}</Td>
                  <Td className="text-xs">{listed(r.counts.allocated) || '—'}</Td>
                  <Td className="tabular">{r.counts.unreturned ?? 0}</Td></tr>
              ))}
            </Table>
            <p className="px-5 py-3 text-xs text-slate-500">A run again the same day that found nothing new is not listed.</p>
          </>
        ) : <Note>No runs yet. Set the callers, then run the selection each morning (or set an automatic time in Settings).</Note>}
      </Card>
    </>
  )
}
