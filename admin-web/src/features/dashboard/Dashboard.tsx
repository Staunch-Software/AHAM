import { useQuery } from '@tanstack/react-query'
import { AlertCircle, ArrowRight, Building2, ClipboardList, FileText, Hourglass, Inbox, Users } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Avatar, Badge, Card, EmptyState, ErrorBox, PageTitle, Skeleton, StatCard } from '../../components/ui'
import { api, errorMessage } from '../../services/api'
import { useAuth } from '../../services/auth'
import { fillDays, fmtServer } from '../../services/format'
import type { Dashboard as D } from '../../types'

function greeting(name?: string) {
  const h = new Date().getHours()
  const part = h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening'
  const first = name?.split(/\s+/)[0]
  return first ? `${part}, ${first}` : part
}
const today = () => new Date().toLocaleDateString(undefined, { weekday: 'long', day: 'numeric', month: 'long' })
const shortDay = (iso: string) => new Date(`${iso}T00:00:00`).toLocaleDateString(undefined, { day: 'numeric', month: 'short' })

function DashboardSkeleton() {
  return (
    <div role="status" aria-label="Loading dashboard">
      <Skeleton className="mb-6 h-9 w-72" />
      <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-5">{Array.from({ length: 5 }, (_, i) => <Skeleton key={i} className="h-28" />)}</div>
      <Skeleton className="mb-6 h-56" />
      <Skeleton className="h-64" />
    </div>
  )
}

export default function Dashboard() {
  const { me } = useAuth()
  const { data, isLoading, error } = useQuery({ queryKey: ['dashboard'], queryFn: async () => (await api.get<D>('/dashboard')).data })
  if (isLoading) return <DashboardSkeleton />
  if (error || !data) return <ErrorBox error={errorMessage(error)} />
  const stats = [
    { label: 'Active agents', value: data.total_agents, icon: <Users size={20} />, tone: 'navy' },
    { label: 'Active branches', value: data.active_branches, icon: <Building2 size={20} />, tone: 'blue' },
    { label: 'Reports today', value: data.submissions_today, icon: <FileText size={20} />, tone: 'green' },
    { label: 'Pending review', value: data.pending_review, icon: <Hourglass size={20} />, tone: 'gold' },
    { label: 'Needs correction', value: data.needs_correction, icon: <AlertCircle size={20} />, tone: 'red' },
  ] as const
  const days = fillDays(data.trend)
  const max = Math.max(1, ...days.map((t) => t.count))
  const total = days.reduce((a, t) => a + t.count, 0)
  const peak = days.reduce((a, t) => (t.count > a.count ? t : a), days[0] ?? { date: '', count: 0 })
  return (
    <>
      <PageTitle subtitle={`${greeting(me?.full_name)} · ${today()}`}>Dashboard</PageTitle>

      {data.pending_review > 0 && (
        <Link to="/submissions?review_status=pending"
          className="mb-6 flex items-center justify-between gap-3 rounded-2xl border border-gold-300/60 bg-gradient-to-r from-gold-50 to-white px-5 py-4 shadow-card transition hover:border-gold-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500">
          <span className="flex items-center gap-3">
            <span className="grid h-10 w-10 place-items-center rounded-xl bg-gold-100 text-gold-700" aria-hidden="true"><ClipboardList size={20} /></span>
            <span>
              <span className="block text-sm font-semibold text-brand-900">{data.pending_review} {data.pending_review === 1 ? 'report is' : 'reports are'} waiting for your review</span>
              <span className="block text-xs text-slate-500">Approve them, or send them back to the agent with a reason.</span>
            </span>
          </span>
          <span className="flex shrink-0 items-center gap-1 text-sm font-medium text-brand-700">Open queue <ArrowRight size={16} aria-hidden="true" /></span>
        </Link>
      )}

      <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-5">
        {stats.map((s) => <StatCard key={s.label} label={s.label} value={s.value} icon={s.icon} tone={s.tone} testId={`stat-${s.label}`} />)}
      </div>

      {days.length > 0 && (
        <Card title="Submissions, last 14 days" subtitle={`${total} reports · busiest day ${shortDay(peak.date)} (${peak.count})`} className="mb-6">
          <div className="relative">
            <div className="pointer-events-none absolute inset-x-0 top-0 flex h-36 flex-col justify-between" aria-hidden="true">
              {[max, Math.round(max / 2), 0].map((v, i) => (
                <div key={i} className="flex items-center gap-2"><span className="tabular w-6 text-right text-[10px] text-slate-400">{v}</span><span className="h-px flex-1 bg-slate-100" /></div>
              ))}
            </div>
            <div className="flex h-36 items-end gap-1.5 pl-8" role="img" aria-label="Submissions per day">
              {days.map((t) => (
                <div key={t.date} title={`${shortDay(t.date)}: ${t.count}`} className="group relative flex h-full flex-1 items-end">
                  <div className={`w-full rounded-t-md transition-colors ${t === peak && t.count > 0 ? 'bg-gold-500' : t.count > 0 ? 'bg-brand-600 group-hover:bg-brand-500' : 'bg-slate-200'}`} style={{ height: t.count ? `${(t.count / max) * 100}%` : 3 }} />
                </div>
              ))}
            </div>
            <div className="mt-2 flex justify-between pl-8 text-[11px] text-slate-400" aria-hidden="true">
              <span>{shortDay(days[0]!.date)}</span><span>{shortDay(days[days.length - 1]!.date)}</span>
            </div>
          </div>
        </Card>
      )}

      <Card title="Recently submitted" subtitle="Newest reports from the field" flush actions={<Link to="/submissions" className="mr-5 text-sm font-medium text-brand-700 hover:underline">View all</Link>}>
        {data.recent.length === 0 ? (
          <EmptyState icon={<Inbox size={22} />} title="No submissions yet." hint="Reports appear here as soon as an agent's phone syncs them." />
        ) : (
          <ul className="divide-y divide-slate-100 border-t border-slate-100">
            {data.recent.map((r) => (
              <li key={r.id}>
                <Link to={`/submissions/${r.id}`} className="flex flex-wrap items-center gap-x-4 gap-y-1 px-5 py-3 transition hover:bg-brand-50/40 focus:outline-none focus-visible:bg-brand-50">
                  <Avatar name={r.agent_name} />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-medium text-brand-900"><span className="font-mono">{r.reference}</span> · {r.agent_name}</span>
                    <span className="block truncate text-xs text-slate-500">{r.branch_name ?? 'No branch'} · {fmtServer(r.accepted_at_server)}</span>
                  </span>
                  <Badge value={r.review_status} />
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </>
  )
}
