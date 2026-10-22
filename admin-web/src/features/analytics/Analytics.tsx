import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertCircle, CalendarRange, FileText, Gauge, Hourglass, Info, Users } from 'lucide-react'
import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Button, Card, EmptyState, ErrorBox, Field, Input, PageTitle, Segmented, Skeleton, StatCard, Table, Td } from '../../components/ui'
import { api, errorMessage } from '../../services/api'
import type { AgentMetrics, AnalyticsOverview, Metrics, PeriodMeta } from '../../types'

export const PERIODS = [['today', 'Today'], ['week', 'This week'], ['month', 'This month'], ['custom', 'Custom']] as const

export function periodParams(p: URLSearchParams) {
  const period = p.get('period') ?? 'month'
  return period === 'custom' ? { period, date_from: p.get('date_from') ?? '', date_to: p.get('date_to') ?? '' } : { period }
}

export function PeriodPicker({ params, onChange }: { params: URLSearchParams; onChange: (p: URLSearchParams) => void }) {
  const period = params.get('period') ?? 'month'
  const set = (k: string, v: string) => { const n = new URLSearchParams(params); v ? n.set(k, v) : n.delete(k); onChange(n) }
  return (
    <div className="mb-5 flex flex-wrap items-end gap-4" aria-label="Reporting period">
      <Segmented label="Period" value={period} onChange={(v) => set('period', v)} options={PERIODS.map(([value, label]) => ({ value, label }))} />
      {period === 'custom' && (
        <>
          <Field label="From"><Input type="date" value={params.get('date_from') ?? ''} onChange={(e) => set('date_from', e.target.value)} /></Field>
          <Field label="To"><Input type="date" value={params.get('date_to') ?? ''} onChange={(e) => set('date_to', e.target.value)} /></Field>
        </>
      )}
    </div>
  )
}

export const Trend = ({ pct }: { pct: number | null }) =>
  pct == null ? <span className="text-slate-400" title="No reports in the previous period to compare with">—</span>
    : <span className={`tabular font-medium ${pct >= 0 ? 'text-emerald-700' : 'text-roof-600'}`}>{pct >= 0 ? '▲' : '▼'} {Math.abs(pct)}%</span>

export function Achievement({ m, applies }: { m: Metrics; applies: boolean }) {
  if (!applies) return <span className="text-slate-400" title="Targets apply to week and month views">n/a</span>
  if (m.target == null) return <span className="text-slate-400">No target</span>
  const pct = m.achievement ?? 0
  return (
    <div className="min-w-28">
      <div className="tabular text-sm font-medium text-slate-800">{pct}%</div>
      <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-slate-100" role="progressbar" aria-valuenow={Math.min(100, pct)} aria-valuemin={0} aria-valuemax={100} aria-label="Target achievement">
        <div className={`h-full rounded-full ${pct >= 100 ? 'bg-emerald-500' : pct >= 75 ? 'bg-brand-600' : 'bg-gold-500'}`} style={{ width: `${Math.min(100, pct)}%` }} />
      </div>
    </div>
  )
}

export function TargetEditor({ scope, id, meta, value }: { scope: 'branch' | 'agent'; id: string; meta: PeriodMeta; value: number | null }) {
  const qc = useQueryClient()
  const [editing, setEditing] = useState(false)
  const [text, setText] = useState('')
  const period = meta.key === 'week' ? 'weekly' : 'monthly'
  const save = useMutation({
    mutationFn: (target: number | null) => api.put('/analytics/targets', { scope, id, period, target }),
    onSuccess: () => { setEditing(false); qc.invalidateQueries({ queryKey: ['analytics'] }) },
  })
  if (!meta.targets_apply) return <span className="text-slate-400">n/a</span>
  if (!editing) {
    return (
      <span className="inline-flex items-center gap-2">
        <span className="tabular">{value ?? '—'}</span>
        <button type="button" className="rounded px-1.5 py-0.5 text-xs font-medium text-brand-700 hover:bg-brand-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500" onClick={() => { setText(value == null ? '' : String(value)); setEditing(true) }}>{value == null ? 'Set' : 'Edit'}</button>
      </span>
    )
  }
  const n = text.trim() === '' ? null : Number(text)
  const valid = n === null || (Number.isInteger(n) && n >= 0 && n <= 100000)
  return (
    <form className="flex items-center gap-1.5" onSubmit={(e) => { e.preventDefault(); if (valid) save.mutate(n) }}>
      <Input aria-label={`${meta.key === 'week' ? 'Weekly' : 'Monthly'} target`} className="w-20 py-1.5" inputMode="numeric" value={text} autoFocus onChange={(e) => setText(e.target.value)} />
      <Button type="submit" small disabled={!valid || save.isPending}>Save</Button>
      <Button type="button" variant="secondary" small onClick={() => setEditing(false)}>Cancel</Button>
    </form>
  )
}

export const rate = (v: number | null) => (v == null ? '—' : `${v}%`)

/** Link into the submissions list pre-filtered for a metric, so any number can be traced to the reports behind it. */
export function listLink(meta: PeriodMeta, extra: Record<string, string>) {
  const q = new URLSearchParams({ date_from: meta.from, date_to: meta.to, ...extra })
  return `/submissions?${q.toString()}`
}

export const numberLink = 'tabular font-medium text-brand-700 hover:underline'

export function PeriodRange({ meta }: { meta: PeriodMeta }) {
  return (
    <p className="mb-4 inline-flex items-center gap-2 rounded-full bg-white px-3 py-1 text-xs text-slate-600 shadow-sm ring-1 ring-slate-200" data-testid="period-range">
      <CalendarRange size={14} className="text-brand-600" aria-hidden="true" />{meta.from} to {meta.to} ({meta.timezone})
    </p>
  )
}

function AnalyticsSkeleton() {
  return (
    <div role="status" aria-label="Loading performance">
      <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-5">{Array.from({ length: 5 }, (_, i) => <Skeleton key={i} className="h-28" />)}</div>
      <Skeleton className="h-72" />
    </div>
  )
}

export default function Analytics() {
  const [params, setParams] = useSearchParams()
  const q = periodParams(params)
  const ready = q.period !== 'custom' || (q.date_from && q.date_to)
  const { data, isLoading, error } = useQuery({
    queryKey: ['analytics', 'overview', q], enabled: !!ready,
    queryFn: async () => (await api.get<AnalyticsOverview>('/analytics/overview', { params: q })).data,
  })
  const keep = params.toString()
  return (
    <>
      <PageTitle subtitle="How each branch and agent is doing, from first submissions to review outcomes.">Branch and agent performance</PageTitle>
      <PeriodPicker params={params} onChange={setParams} />
      <ErrorBox error={error ? errorMessage(error) : null} />
      {!ready ? <EmptyState icon={<CalendarRange size={22} />} title="Choose a start and end date." hint="The numbers appear as soon as both dates are set." />
        : isLoading || !data ? <AnalyticsSkeleton /> : (
        <>
          <PeriodRange meta={data.period} />
          <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-5">
            <StatCard label="Reports submitted" value={data.totals.reports} icon={<FileText size={20} />} tone="navy" hint={<>vs previous period: <Trend pct={data.totals.trend_pct} /></>} />
            <StatCard label="Pending review" value={data.totals.pending} icon={<Hourglass size={20} />} tone="gold" />
            <StatCard label="Needs correction" value={data.totals.needs_correction} icon={<AlertCircle size={20} />} tone="red" />
            <StatCard label="Rejection rate" value={rate(data.totals.rejection_rate)} icon={<Gauge size={20} />} tone="blue" hint={`${data.totals.reviewed_decisions} decisions`} />
            <StatCard label="Active agents" value={`${data.totals.active_agents} / ${data.totals.assigned_agents}`} icon={<Users size={20} />} tone="green" hint="reported / assigned" />
          </div>

          <Card title="Branches" subtitle="Select a branch to see its agents." flush className="mb-6">
            <Table head={['Branch', 'Agents (active / assigned)', 'Reports', 'Target', 'Achievement', 'Pending', 'Needs correction', 'Rejection rate', 'Trend']}>
              {data.branches.map((b) => (
                <tr key={b.branch_id}>
                  <Td><Link className="font-semibold text-brand-700 hover:underline" to={`/analytics/branches/${b.branch_id}?${keep}`}>{b.name}</Link><div className="text-xs text-slate-400">{b.code}</div></Td>
                  <Td className="tabular">{b.active_agents} / {b.assigned_agents}</Td>
                  <Td><Link className={numberLink} to={listLink(data.period, { branch_id: b.branch_id })}>{b.reports}</Link></Td>
                  <Td><TargetEditor scope="branch" id={b.branch_id} meta={data.period} value={b.target} /></Td>
                  <Td><Achievement m={b} applies={data.period.targets_apply} /></Td>
                  <Td><Link className={numberLink} to={listLink(data.period, { branch_id: b.branch_id, review_status: 'pending' })}>{b.pending}</Link></Td>
                  <Td><Link className={numberLink} to={listLink(data.period, { branch_id: b.branch_id, review_status: 'rejected' })}>{b.needs_correction}</Link></Td>
                  <Td className="tabular">{rate(b.rejection_rate)}</Td>
                  <Td><Trend pct={b.trend_pct} /></Td>
                </tr>
              ))}
            </Table>
            {data.branches.length === 0 && <EmptyState title="No active branches yet." hint="Add branches under Organization." />}
            <details className="border-t border-slate-100 px-5 py-3 text-xs text-slate-500">
              <summary className="flex cursor-pointer items-center gap-1.5 font-medium text-slate-600"><Info size={14} aria-hidden="true" />How these numbers are calculated</summary>
              <ul className="mt-2 list-disc space-y-1 pl-5">
                <li><strong>Reports</strong>: reports first submitted in the period. A corrected resubmission is not counted again.</li>
                <li><strong>Pending / needs correction</strong>: the current state of those reports.</li>
                <li><strong>Rejection rate</strong> = rejections ÷ (approvals + rejections) among review decisions made in the period. Pending reports are not counted.</li>
                <li><strong>Achievement</strong> = reports ÷ target × 100, for week and month views when a target is set.</li>
                <li><strong>Trend</strong>: reports compared with the previous equivalent period.</li>
                <li>Reports still waiting to sync on an agent's phone are not counted yet.</li>
              </ul>
            </details>
          </Card>

          <Card title="Meetings by type of person" subtitle="Each meeting in a report counts once.">
            {data.person_types.length === 0 ? <p className="text-sm text-slate-500">No meetings with a type of person in this period.</p> : (
              <ul className="space-y-3" aria-label="Meetings by type of person">
                {data.person_types.map((t) => {
                  const max = Math.max(...data.person_types.map((x) => x.meetings))
                  return (
                    <li key={t.label} className="grid grid-cols-[9rem_minmax(0,1fr)_2.5rem] items-center gap-3 text-sm">
                      <span className="truncate text-slate-700">{t.label}</span>
                      <span className="h-2.5 overflow-hidden rounded-full bg-slate-100"><span className="block h-full rounded-full bg-gradient-to-r from-brand-600 to-brand-400" style={{ width: `${Math.max(4, (t.meetings / max) * 100)}%` }} /></span>
                      <span className="tabular text-right font-medium text-slate-800">{t.meetings}</span>
                    </li>
                  )
                })}
              </ul>
            )}
          </Card>
        </>
      )}
    </>
  )
}

export interface AgentsPayload { period: PeriodMeta; branch: { id: string; name: string }; agents: AgentMetrics[]; note: string }
