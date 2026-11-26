import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowRightLeft, Copy, FileSpreadsheet, Play, Save, UserPlus, Wand2 } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Button, Card, cx, EmptyState, ErrorBox, ExportBar, Input, Note, PageTitle, Select, Skeleton, StatCard, Table, Td } from '../../components/ui'
import { api, download, errorMessage } from '../../services/api'
import { useAuth } from '../../services/auth'
import { tableCells } from '../../services/exporting'
import { useCallers } from '../../services/meta'
import type { CallRow } from '../../types'

interface Days { day: string; items: { branch_id: string; branch: string; region: string | null; caller_id: string | null; uncalled_count?: number }[] }
interface Overview { callers: { id: string; name: string; active: boolean; open: number; attempts_today: number; first_try_overdue: number }[]; unassigned: number; first_try_overdue: number; items: CallRow[] }
// Caller allocation by language, absence and the daily limit (GET /calls/day-plan): flags and suggestions only
interface Flag { code: 'no_caller' | 'inactive' | 'absent' | 'language' | 'over_limit'; message: string }
interface PlanBranch { branch_id: string; branch: string; caller_id: string | null; caller: string | null; waiting: number; flags: Flag[]; suggestion: { caller_id: string; caller: string; room: number } | null }
interface PlanCaller { id: string; name: string; absent: boolean; load: number; room: number; over: number }
interface PlanMove { kind: 'entries' | 'branch'; from_id: string; from: string; to_id: string; to: string; branch_id: string; branch: string; count: number; languages: string[] }
interface DayPlan { day: string; limit: number; branches: PlanBranch[]; callers: PlanCaller[]; moves: PlanMove[] }
interface Run { id: string; run_date: string; started_at: string; started_by: string; counts: { selection: Record<string, number>; allocated: Record<string, number>; unreturned: number } }

const CALLERS_HEAD = ['Caller', 'Still to call today', 'List / limit', 'Not called within the target (overdue)', 'Calls made today', 'Move today’s list to', '']
const RUNS_HEAD = ['Run date', 'Started at', 'Started by', 'Entries decided', 'Put on callers’ lists', 'Not done before, offered again']
const NO_CALLER_HEAD = ['Entry ID', 'Person met', 'Branch', 'List', 'Assign to caller']

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
  const callersTableRef = useRef<HTMLTableElement>(null)
  const runsTableRef = useRef<HTMLTableElement>(null)
  const noCallerTableRef = useRef<HTMLTableElement>(null)
  const { data: callers } = useCallers()
  const days = useQuery({ queryKey: ['caller-days', day], queryFn: async () => (await api.get<Days>('/calls/caller-days', { params: { day } })).data })
  const overview = useQuery({ queryKey: ['calls', 'overview'], queryFn: async () => (await api.get<Overview>('/calls/allocations', { params: { unassigned: true } })).data })
  const runs = useQuery({ queryKey: ['calls', 'runs'], queryFn: async () => (await api.get<Run[]>('/calls/runs')).data })
  const plan = useQuery({ queryKey: ['calls', 'day-plan', day], queryFn: async () => (await api.get<DayPlan>('/calls/day-plan', { params: { day } })).data })
  const planOf = Object.fromEntries((plan.data?.branches ?? []).map((b) => [b.branch_id, b]))
  const loadOf = Object.fromEntries((plan.data?.callers ?? []).map((c) => [c.id, c]))
  const [pick, setPick] = useState<Record<string, string>>({})
  useEffect(() => { if (days.data) setPick(Object.fromEntries(days.data.items.map((i) => [i.branch_id, i.caller_id ?? '']))) }, [days.data])
  const refresh = () => ['caller-days', 'calls', 'entries', 'dashboard'].forEach((k) => qc.invalidateQueries({ queryKey: [k] }))
  // Saving a branch's caller after the run also hands that branch's waiting new entries to the new caller.
  const [moved, setMoved] = useState<number | null>(null)
  const saved = (r: { moved: number }) => { setMoved(r.moved); refresh() }
  const save = useMutation({ mutationFn: async () => (await api.put<{ moved: number }>('/calls/caller-days', { day, assignments: Object.entries(pick).map(([branch_id, caller_id]) => ({ branch_id, caller_id: caller_id || null })) })).data, onSuccess: saved })
  const copy = useMutation({ mutationFn: async () => (await api.post<{ moved: number }>('/calls/caller-days/copy', { from_day: isoMinus(day, 1), to_day: day })).data, onSuccess: saved })
  const run = useMutation({ mutationFn: async () => (await api.post('/calls/runs', { run_date: day })).data as Run['counts'] & { run_date: string }, onSuccess: refresh })
  // by language, absence and room: the usual caller, else the present caller who speaks the language with most room
  const [autoNote, setAutoNote] = useState<{ assigned: number; no_caller: string[] } | null>(null)
  const auto = useMutation({ mutationFn: async () => (await api.post<{ moved: number; auto: { assigned: number; no_caller: string[] } }>('/calls/caller-days/auto', { day })).data,
    onSuccess: (r) => { setAutoNote(r.auto); saved(r) } })
  // one click: this branch's caller for the day (its waiting new entries follow), or N new entries to another caller
  const pickCaller = useMutation({ mutationFn: async ({ branch, caller }: { branch: string; caller: string }) => (await api.put<{ moved: number }>('/calls/caller-days', { day, assignments: [{ branch_id: branch, caller_id: caller }] })).data, onSuccess: saved })
  const applyMove = useMutation({
    mutationFn: async (m: PlanMove) => (m.kind === 'entries'
      ? (await api.post<{ moved: number }>('/calls/allocations/move', { from_caller_id: m.from_id, to_caller_id: m.to_id, branch_id: m.branch_id, count: m.count })).data
      : (await api.put<{ moved: number }>('/calls/caller-days', { day, assignments: [{ branch_id: m.branch_id, caller_id: m.to_id }] })).data),
    onSuccess: refresh })
  const assign = useMutation({ mutationFn: ({ id, caller }: { id: string; caller: string }) => api.post(`/calls/allocations/${id}/assign`, { caller_id: caller }), onSuccess: refresh })
  // A caller is off: their whole open list (retries and PRIORITY calls too) goes to another caller for the day.
  const move = useMutation({ mutationFn: async ({ from, to }: { from: string; to: string }) => (await api.post<{ moved: number }>('/calls/allocations/move', { from_caller_id: from, to_caller_id: to })).data, onSuccess: refresh })
  // the lists of the day as Excel, in the layout of the call sheets handed out today: one sheet per caller
  const sheet = useMutation({ mutationFn: (c?: { id: string; name: string }) => download('/calls/call-sheet.xlsx',
    c ? { day, caller_id: c.id } : { day }, `call_sheet_${c ? c.name.replace(/\W+/g, '_') : 'all_callers'}_${day}.xlsx`) })
  const activeCallers = callers?.filter((c) => c.status === 'active') ?? []
  const callerName = (id?: string | null) => callers?.find((c) => c.id === id)?.full_name ?? 'No caller'
  const setAll = (caller: string) => setPick(Object.fromEntries(Object.keys(pick).map((b) => [b, caller])))
  const dayRuns = (runs.data ?? []).filter((r) => r.run_date === day && did(r.counts))
  const ranNow = run.data?.run_date === day ? run.data : null
  return (
    <>
      <PageTitle
        subtitle="Entries are called from the day after they are made. Retries go back to the caller who first handled the entry."
        actions={
          <Input
            type="date"
            aria-label="Run date"
            value={day}
            max={isoToday()}
            onChange={(e) => {
              setDay(e.target.value)
              setMoved(null)
            }}
            className="!w-auto"
          />
        }
      >
        Daily run & allocation
      </PageTitle>
      <ErrorBox error={[save.error, copy.error, run.error, assign.error, move.error, sheet.error, auto.error, pickCaller.error, applyMove.error].map((e) => e && errorMessage(e)).find(Boolean) ?? null} />

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
        <Card
          title="1 · Caller of the day per branch"
          subtitle="New entries of a branch go to its caller of the day"
          className="h-full flex flex-col"
          actions={<div className="flex gap-2">
            <Button variant="secondary" small disabled={auto.isPending} onClick={() => auto.mutate()} title="Each branch's usual caller; for an absent one, the caller who speaks the language with the most room (Callers page)"><Wand2 size={14} aria-hidden="true" />Auto-assign</Button>
            <Button variant="secondary" small disabled={copy.isPending} onClick={() => copy.mutate()}><Copy size={14} aria-hidden="true" />Copy yesterday</Button>
            <Button small disabled={save.isPending} onClick={() => save.mutate()}><Save size={14} aria-hidden="true" />Save</Button>
          </div>}>
          {days.isLoading ? <Skeleton className="h-40" /> : (
            <div className="flex-1 flex flex-col min-h-0">
              {autoNote && (
                <p className="mb-3 rounded-xl bg-brand-50 px-3 py-2 text-sm text-brand-800 shrink-0" role="status">
                  Auto-assigned {autoNote.assigned} {autoNote.assigned === 1 ? 'branch' : 'branches'}.{autoNote.no_caller.length ? ` No present caller speaks the language of ${autoNote.no_caller.join(', ')}: set one on the Callers page.` : ''}
                </p>
              )}
              {moved !== null && (
                <p className="mb-3 rounded-xl bg-emerald-50 px-3 py-2 text-sm text-emerald-800 shrink-0" role="status">
                  Saved.{moved ? ` ${moved} new ${moved === 1 ? 'entry' : 'entries'} not yet called went to the caller now set for ${moved === 1 ? 'its' : 'their'} branch. Retries stay with their first caller.` : ''}
                </p>
              )}
              <div className="mb-3 flex items-center justify-between gap-2 text-xs text-slate-500 shrink-0 whitespace-nowrap">
                <div className="flex items-center gap-2 shrink-0">
                  <span>Set all to</span>
                  <Select className="w-32 shrink-0 py-1 text-xs" value="" onChange={(e) => e.target.value && setAll(e.target.value)}>
                    <option value="">choose…</option>{activeCallers.map((c) => <option key={c.id} value={c.id}>{c.full_name}</option>)}
                  </Select>
                </div>
                <div className="flex items-center gap-2.5 shrink-0">
                  {(days.data?.items.reduce((s, b) => s + (b.uncalled_count ?? 0), 0) ?? 0) > 0 ? (
                    <span className="inline-flex items-center gap-1.5 rounded-full bg-gold-50 px-2 py-0.5 text-[11px] font-semibold text-gold-900 border border-gold-200 shrink-0">
                      <span className="h-1.5 w-1.5 rounded-full bg-gold-500" />
                      {days.data?.items.reduce((s, b) => s + (b.uncalled_count ?? 0), 0)} not called yet
                    </span>
                  ) : (
                    <span className="text-xs text-slate-400 shrink-0">0 uncalled</span>
                  )}
                  <ExportBar
                    name={`Callers of the day ${day}`}
                    header={['Branch', 'Region', 'Uncalled entries', 'Caller of the day']}
                    className="p-0 gap-1.5 flex-nowrap shrink-0"
                    rows={() => (days.data?.items ?? []).map((b) => [b.branch, b.region ?? '', String(b.uncalled_count ?? 0), callerName(pick[b.branch_id])])}
                  />
                </div>
              </div>
              <div className="flex-1 min-h-0 max-h-[min(480px,52vh)] overflow-y-auto rounded-xl border border-slate-100 custom-scrollbar">
                <table className="w-full text-sm">
                  <tbody className="divide-y divide-slate-100">
                    {days.data?.items.map((b) => (
                      <tr key={b.branch_id} className="hover:bg-slate-50/60">
                        <td className="px-3 py-2">
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-slate-800">{b.branch}</span>
                            <span className="text-xs text-slate-400">{b.region}</span>
                          </div>
                          {(planOf[b.branch_id]?.flags ?? []).map((f) => (
                            <p key={f.code} className={cx('mt-0.5 text-[11px] font-medium', f.code === 'over_limit' ? 'text-gold-800' : 'text-roof-700')}>{f.message}</p>
                          ))}
                          {planOf[b.branch_id]?.suggestion && (
                            <button type="button" className="mt-0.5 text-[11px] font-semibold text-brand-700 hover:underline disabled:opacity-50" disabled={pickCaller.isPending}
                              onClick={() => pickCaller.mutate({ branch: b.branch_id, caller: planOf[b.branch_id]!.suggestion!.caller_id })}>
                              Use {planOf[b.branch_id]!.suggestion!.caller} (room for {planOf[b.branch_id]!.suggestion!.room})
                            </button>
                          )}
                        </td>
                        <td className="w-72 px-3 py-1.5 text-right">
                          <div className="flex items-center justify-end gap-2.5">
                            <div className="w-24 text-right shrink-0">
                              {(b.uncalled_count ?? 0) > 0 ? (
                                <span
                                  className="inline-flex items-center rounded-full bg-gold-50 px-2 py-0.5 text-[11px] font-semibold text-gold-800 border border-gold-200/80 whitespace-nowrap"
                                  title={`${b.uncalled_count} uncalled entries waiting in ${b.branch}`}
                                >
                                  {b.uncalled_count} uncalled
                                </span>
                              ) : (
                                <span className="text-xs text-slate-300 font-normal tabular whitespace-nowrap">
                                  0 uncalled
                                </span>
                              )}
                            </div>
                            <Select
                              aria-label={`Caller for ${b.branch}`}
                              className="w-48 shrink-0 py-1.5 text-xs"
                              value={pick[b.branch_id] ?? ''}
                              onChange={(e) => setPick({ ...pick, [b.branch_id]: e.target.value })}
                            >
                              <option value="">No caller</option>{activeCallers.map((c) => <option key={c.id} value={c.id}>{c.full_name}</option>)}
                            </Select>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </Card>

        <div className="flex flex-col h-full justify-between gap-4">
          <Card
            title="2 · Run the selection"
            subtitle="Checks each new entry in order (no valid number, repeat, duplicate, being called, spoken to) and fills the lists"
            className="flex-1 flex flex-col"
          >
            <div className="flex-1 flex flex-col justify-between min-h-0">
              <div className="space-y-3">
                <Button variant="gold" className="w-full py-2.5" disabled={run.isPending} onClick={() => run.mutate()}>
                  <Play size={16} aria-hidden="true" />{run.isPending ? 'Running…' : `${dayRuns.length ? 'Run again' : 'Run'} for ${day}`}
                </Button>
                {ranNow && !did(ranNow) && (
                  <p className="rounded-xl bg-brand-50 px-3 py-2 text-sm text-brand-800" role="status">
                    Nothing new to select{dayRuns.length ? `: ${day} was already run, below` : ` for ${day}`}. Running again only adds entries and calls that came in since.
                  </p>
                )}
                {dayRuns.map((r) => (
                  <div key={r.id} className="rounded-xl border border-slate-100 bg-slate-50/50 p-3">
                    <p className="mb-1 text-xs font-medium text-slate-500">Run at {clock(r.started_at)} by {r.started_by}</p>
                    <RunCounts c={r.counts} />
                  </div>
                ))}
                {!dayRuns.length && !ranNow && (
                  <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-200/80 bg-slate-50/40 py-6 text-center">
                    <p className="text-xs font-medium text-slate-500">Not run yet for {day}</p>
                    <p className="mt-1 text-[11px] text-slate-400">Click &ldquo;Run for {day}&rdquo; to allocate entries to callers.</p>
                  </div>
                )}
              </div>
              {overview.data?.unassigned ? (
                <p className="mt-4 rounded-xl bg-roof-50 border border-roof-200/70 px-3 py-2 text-xs font-medium text-roof-700">
                  {overview.data.unassigned} have no caller yet: set the branch’s caller and Save, or assign them below.
                </p>
              ) : null}
            </div>
          </Card>
          <div className="grid grid-cols-3 gap-3 shrink-0">
            <StatCard label="Unassigned work" value={overview.data?.unassigned ?? '—'} tone="red" />
            <StatCard label="First try overdue" value={overview.data?.first_try_overdue ?? '—'} tone="gold" testId="kpi-overdue" hint="On a list, not called within the target" />
            <StatCard label="Tries today" value={overview.data?.callers.reduce((a, c) => a + c.attempts_today, 0) ?? '—'} tone="green" />
          </div>
        </div>
      </div>

      <Card title="Callers" subtitle={`A caller who is off today: move their open list (retries and PRIORITY calls too) to another caller. Call sheet: that caller's list for ${day} in Excel, as the hand-made call sheets, with the tries, answers and lead card recorded so far.`} className="mt-6" flush
        actions={<>
          <Button small variant="secondary" disabled={sheet.isPending} onClick={() => sheet.mutate(undefined)}><FileSpreadsheet size={14} aria-hidden="true" />All call sheets (Excel)</Button>
          <ExportBar compact name="Callers today" header={CALLERS_HEAD.filter((h) => h !== '')} rows={() => tableCells(callersTableRef.current!, CALLERS_HEAD.map((h) => h !== ''))} />
        </>}>
        {move.data && <p className="px-5 pt-3 text-sm text-emerald-700" role="status">{move.data.moved} moved.</p>}
        {applyMove.data && <p className="px-5 pt-3 text-sm text-emerald-700" role="status">{applyMove.data.moved} moved.</p>}
        {(plan.data?.moves ?? []).length > 0 && (
          <div className="mx-5 mt-3 space-y-1.5 rounded-xl border border-gold-200 bg-gold-50/60 px-3 py-2" data-testid="limit-moves">
            <p className="text-xs font-semibold text-gold-900">Over the daily limit of {plan.data!.limit}</p>
            {plan.data!.moves.map((m) => (
              <p key={`${m.from_id}-${m.branch_id}`} className="flex flex-wrap items-center justify-between gap-2 text-sm text-slate-700">
                <span>{m.from} has {loadOf[m.from_id]?.load ?? '—'} today. {m.to} speaks {m.languages.join(' / ') || 'the language'} and has room: {m.kind === 'entries' ? `${m.count} of ${m.branch}'s new entries` : `${m.branch} for the day (${m.count} new)`}.</span>
                <Button small variant="secondary" disabled={applyMove.isPending} onClick={() => applyMove.mutate(m)}>
                  {m.kind === 'entries' ? `Move ${m.count}` : `Give ${m.branch} to ${m.to}`}
                </Button>
              </p>
            ))}
          </div>
        )}
        <Table head={CALLERS_HEAD} exportName="Callers today" hideExportBar tableRef={callersTableRef}>
          {overview.data?.callers.map((c) => (
            <tr key={c.id}><Td className="font-medium">{c.name}{!c.active && <span className="ml-2 text-xs text-slate-400">inactive</span>}{loadOf[c.id]?.absent && <span className="ml-2 rounded-full bg-roof-50 px-2 py-0.5 text-[11px] font-semibold text-roof-700">absent today</span>}</Td><Td className="tabular">{c.open}</Td>
              <Td className={cx('tabular', (loadOf[c.id]?.over ?? 0) > 0 && 'font-semibold text-roof-700')}>{loadOf[c.id] ? `${loadOf[c.id]!.load} / ${plan.data!.limit}` : '—'}</Td>
              <Td className="tabular">{c.first_try_overdue || 0}</Td><Td className="tabular">{c.attempts_today}</Td>
              <Td>{c.open > 0 ? (
                <Select aria-label={`Move ${c.name}'s list`} className="w-44 py-1.5" value="" disabled={move.isPending}
                  onChange={(e) => e.target.value && move.mutate({ from: c.id, to: e.target.value })}>
                  <option value="">Choose…</option>{activeCallers.filter((x) => x.id !== c.id).map((x) => <option key={x.id} value={x.id}>{x.full_name}</option>)}
                </Select>) : <span className="inline-flex items-center gap-1 text-xs text-slate-400"><ArrowRightLeft size={12} aria-hidden="true" />nothing open</span>}</Td>
              <Td className="whitespace-nowrap"><Link className="text-xs font-semibold text-brand-700 hover:underline" to={`${path('calls')}`}>Lists</Link>
                <button type="button" className="ml-3 text-xs font-semibold text-brand-700 hover:underline disabled:opacity-50" disabled={sheet.isPending}
                  aria-label={`Call sheet of ${c.name}`} onClick={() => sheet.mutate({ id: c.id, name: c.name })}>Call sheet</button></Td></tr>
          ))}
        </Table>
      </Card>

      <Card title="Work with no caller" subtitle="The branch had no caller of the day" className="mt-6" flush
        actions={!!overview.data?.items.length && (
          <ExportBar compact name="Work with no caller" header={NO_CALLER_HEAD} rows={() => tableCells(noCallerTableRef.current!, NO_CALLER_HEAD.map(() => true))} />
        )}>
        {!overview.data?.items.length ? <EmptyState icon={<UserPlus size={20} />} title="Everything is on a caller's list." /> : (
          <Table head={NO_CALLER_HEAD} hideExportBar tableRef={noCallerTableRef}>
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

      <Card title="Recent runs" className="mt-6" flush
        actions={runs.data?.some((r) => did(r.counts)) && (
          <ExportBar compact name="Daily runs" header={RUNS_HEAD} rows={() => tableCells(runsTableRef.current!, RUNS_HEAD.map(() => true))} />
        )}>
        {runs.data?.some((r) => did(r.counts)) ? (
          <>
            <Table head={RUNS_HEAD} exportName="Daily runs" hideExportBar tableRef={runsTableRef}>
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
