import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { Award, BadgeCheck, Clock, IdCard, ListChecks, Target, UserCheck, Users } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Card, EmptyState, ErrorBox, PageTitle, RAG_LABEL, Segmented, Skeleton, StatCard, Table, Td } from '../../components/ui'
import { api, errorMessage } from '../../services/api'
import { useAuth } from '../../services/auth'

interface Dash {
  period: { from: string; to: string }
  totals: Record<'entries' | 'lead_prospect' | 'dsa_cp' | 'validated' | 'logged_in' | 'sankalp_success' | 'awaiting_call' | 'open_so_actions' | 'active_sos', number>
  rag: Record<string, number>
  by_category: Record<string, number>
  by_status: Record<string, number>
  trend: { day: string; entries: number }[]
  branches: { branch_id: string; branch: string; region: string | null; entries: number; lead_prospect: number; validated: number; logged_in: number; red: number; amber: number; green: number; sos: number }[]
}

export type Period = 'today' | 'week' | 'last_week' | 'month'
export const PERIODS: { value: Period; label: string }[] = [
  { value: 'today', label: 'Today' }, { value: 'week', label: 'This week' }, { value: 'last_week', label: 'Last week' }, { value: 'month', label: 'This month' },
]
const RAG_ORDER = ['GREEN', 'AMBER', 'RED', 'RNR', 'PENDING', 'NA']
const RAG_BAR: Record<string, string> = { GREEN: 'bg-emerald-500', AMBER: 'bg-amber-400', RED: 'bg-roof-500', RNR: 'bg-violet-400', PENDING: 'bg-sky-400', NA: 'bg-slate-300' }

export function RagBar({ rag }: { rag: Record<string, number> }) {
  const total = Object.values(rag).reduce((a, b) => a + b, 0)
  if (!total) return <p className="text-sm text-slate-500">No entries yet.</p>
  return (
    <div>
      <div className="flex h-3 w-full overflow-hidden rounded-full bg-slate-100" role="img" aria-label="RAG mix">
        {RAG_ORDER.filter((k) => rag[k]).map((k) => <div key={k} className={RAG_BAR[k]} style={{ width: `${(rag[k]! / total) * 100}%` }} />)}
      </div>
      <ul className="mt-3 grid grid-cols-3 gap-2 text-xs sm:grid-cols-6">
        {RAG_ORDER.map((k) => (
          <li key={k} className="flex items-center gap-1.5 text-slate-600">
            <span className={`h-2.5 w-2.5 rounded-full ${RAG_BAR[k]}`} aria-hidden="true" />{RAG_LABEL[k]}
            <span className="tabular ml-auto font-semibold text-slate-800">{rag[k] ?? 0}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

function Trend({ trend }: { trend: Dash['trend'] }) {
  const max = Math.max(1, ...trend.map((t) => t.entries))
  if (!trend.length) return <p className="text-sm text-slate-500">No entries in this period.</p>
  return (
    <div className="flex h-36 items-end gap-1.5" role="img" aria-label="Entries per day">
      {trend.map((t) => (
        <div key={t.day} className="group flex h-full max-w-16 flex-1 flex-col items-center justify-end gap-1" title={`${t.day}: ${t.entries}`}>
          <span className="tabular text-[10px] font-semibold text-slate-600">{t.entries}</span>
          <div className="flex w-full flex-1 items-end">
            <div className="w-full rounded-t-md bg-gradient-to-t from-brand-700 to-brand-500" style={{ height: `${(t.entries / max) * 100}%`, minHeight: 4 }} />
          </div>
          <span className="text-[10px] text-slate-400">{t.day.slice(5)}</span>
        </div>
      ))}
    </div>
  )
}

export default function Dashboard() {
  const { me, can, path } = useAuth()
  const [period, setPeriod] = useState<Period>('today')
  const { data, isLoading, error } = useQuery({
    queryKey: ['dashboard', period],
    queryFn: async () => (await api.get<Dash>('/dashboard', { params: { period } })).data,
    placeholderData: keepPreviousData,
  })
  const scope = me?.branch_name ?? me?.cluster_name ?? me?.region_name ?? 'All regions'
  const t = data?.totals
  return (
    <>
      <PageTitle subtitle={<>Entries counted on their count date · <strong className="text-slate-700">{scope}</strong></>}
        actions={<Segmented label="Period" options={PERIODS} value={period} onChange={setPeriod} />}>
        Dashboard
      </PageTitle>
      <ErrorBox error={error ? errorMessage(error) : null} />
      {isLoading || !t || !data ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">{Array.from({ length: 8 }, (_, i) => <Skeleton key={i} className="h-28" />)}</div>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard label="Entries" value={t.entries} testId="kpi-entries" icon={<ListChecks size={20} />} hint={`${t.active_sos} Sales Officers`} />
            <StatCard label="Lead / Prospect" value={t.lead_prospect} icon={<Target size={20} />} tone="gold" hint={`${t.dsa_cp} DSA / CP`} />
            <StatCard label="Customers validated" value={t.validated} testId="kpi-validated" icon={<BadgeCheck size={20} />} tone="green" />
            <StatCard label="Logged in" value={t.logged_in} icon={<IdCard size={20} />} tone="blue" hint={`${t.sankalp_success} Sankalp successes`} />
            <StatCard label="Awaiting first call" value={t.awaiting_call} icon={<Clock size={20} />} hint="Selected, not yet called" />
            <StatCard label="Open SO / branch actions" value={t.open_so_actions} icon={<UserCheck size={20} />} tone="red"
              to={can('entries.read') ? <Link to={path('actions')} className="mt-2 inline-block text-xs font-semibold text-brand-700 hover:underline">See actions</Link> : undefined} />
            <StatCard label="Sankalp success" value={t.sankalp_success} icon={<Award size={20} />} tone="gold" hint="Earliest entry per TCS ID" />
            <StatCard label="Active Sales Officers" value={t.active_sos} icon={<Users size={20} />} hint={`${data.period.from} to ${data.period.to}`} />
          </div>

          <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]">
            <Card title="Entries per day" subtitle="By count date (Sundays and holidays count on the next working day)"><Trend trend={data.trend} /></Card>
            <Card title="RAG" subtitle="Where the entries of this period stand now"><RagBar rag={data.rag} /></Card>
          </div>

          <div className="mt-6 grid gap-6 lg:grid-cols-2">
            <Card title="By category">
              <ul className="space-y-2.5">
                {Object.entries(data.by_category).sort((a, b) => b[1] - a[1]).map(([k, v]) => (
                  <li key={k} className="flex items-center gap-3 text-sm">
                    <span className="w-36 shrink-0 text-slate-600">{k}</span>
                    <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-brand-600" style={{ width: `${(v / Math.max(1, t.entries)) * 100}%` }} /></div>
                    <span className="tabular w-10 text-right font-semibold text-slate-800">{v}</span>
                  </li>
                ))}
                {!Object.keys(data.by_category).length && <li className="text-sm text-slate-500">No entries in this period.</li>}
              </ul>
            </Card>
            <Card title="By status" subtitle="Selection result until the first call, then the call status">
              <ul className="max-h-72 space-y-1.5 overflow-y-auto text-sm">
                {Object.entries(data.by_status).sort((a, b) => b[1] - a[1]).map(([k, v]) => (
                  <li key={k} className="flex justify-between gap-3 border-b border-slate-100 pb-1.5"><span className="text-slate-600">{k}</span><span className="tabular font-semibold text-slate-800">{v}</span></li>
                ))}
              </ul>
            </Card>
          </div>

          <Card title="Branches" className="mt-6" flush>
            {data.branches.length === 0 ? <EmptyState icon={<ListChecks size={20} />} title="No entries in this period." /> : (
              <Table head={['Branch', 'Region', 'Sales Officers', 'Entries', 'Lead / Prospect entries', 'Validated', 'Logged in', 'Green', 'Amber', 'Red']} exportName="Branches">
                {data.branches.map((b) => (
                  <tr key={b.branch_id}>
                    <Td className="font-medium text-slate-900">{b.branch}</Td><Td>{b.region ?? '—'}</Td><Td className="tabular">{b.sos}</Td>
                    <Td className="tabular">{b.entries}</Td><Td className="tabular">{b.lead_prospect}</Td><Td className="tabular">{b.validated}</Td>
                    <Td className="tabular">{b.logged_in}</Td><Td className="tabular text-emerald-700">{b.green}</Td>
                    <Td className="tabular text-amber-700">{b.amber}</Td><Td className="tabular text-roof-700">{b.red}</Td>
                  </tr>
                ))}
              </Table>
            )}
          </Card>
        </>
      )}
    </>
  )
}
