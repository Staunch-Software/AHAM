import { useQuery } from '@tanstack/react-query'
import { Clock, Flag, PhoneCall, PhoneForwarded, Repeat, Sparkles } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Card, cx, EmptyState, ErrorBox, ExportBar, PageTitle, RAG_LABEL, RagBadge, Select, Skeleton } from '../../components/ui'
import { api, errorMessage } from '../../services/api'
import { useAuth } from '../../services/auth'
import { useCallers, useMeta } from '../../services/meta'
import type { CallRow } from '../../types'

const GROUPS = [
  { kind: 'priority', title: 'PRIORITY', hint: 'Reopened by the branch or flagged by the master owner: call first', icon: Flag, tone: 'text-roof-600 bg-roof-50' },
  { kind: 'retry', title: 'Retries due', hint: 'Unanswered before, or a callback that is due today', icon: Repeat, tone: 'text-violet-700 bg-violet-50' },
  { kind: 'followup', title: 'Follow-ups', hint: 'Cases to take forward and follow-ups sent to the call centre', icon: PhoneForwarded, tone: 'text-gold-700 bg-gold-100' },
  { kind: 'fresh', title: 'New entries', hint: 'Selected in today’s run for your branches', icon: Sparkles, tone: 'text-brand-700 bg-brand-50' },
] as const

/** The caller's list for today, in the order to call it (6.2: PRIORITY first). */
export default function MyCalls() {
  const { me, path } = useAuth()
  const isMaster = me?.role === 'master_owner'
  const { data: callers } = useCallers(isMaster)
  const { data: meta } = useMeta()
  const lim = meta?.limits
  const [caller, setCaller] = useState('')
  const { data, isLoading, error } = useQuery({
    queryKey: ['calls', 'list', caller],
    queryFn: async () => (await api.get<{ today: string; items: CallRow[]; called_today?: CallRow[] }>('/calls/my-list', { params: { caller_id: caller || undefined } })).data,
    refetchInterval: 60_000,
  })
  const items = data?.items ?? []
  const calledToday = data?.called_today ?? []
  return (
    <>
      <PageTitle subtitle={data ? `${items.length} to call · ${data.today}.${lim ? ` Lead: ${lim.tries_per_day_lead} tries a day, up to ${lim.max_unanswered_lead} unanswered. DSA/CP: ${lim.tries_per_day_dsa} try, one day.` : ''}` : 'Today’s list'}
        actions={isMaster && (
          <Select aria-label="Caller" value={caller} onChange={(e) => setCaller(e.target.value)} className="w-auto">
            <option value="">My own list</option>{callers?.map((c) => <option key={c.id} value={c.id}>{c.full_name}</option>)}
          </Select>
        )}>
        My calls
      </PageTitle>
      <ErrorBox error={error ? errorMessage(error) : null} />
      {items.length + calledToday.length > 0 && (
        <ExportBar name="My calls" className="px-0"
          header={['List', 'Entry ID', 'Person met', 'Mobile number', 'Category', 'Sales Officer', 'Branch', 'Calls today', 'Unanswered so far', 'Current status', 'RAG', 'PRIORITY reason']}
          rows={() => [...items.map((r) => [GROUPS.find((g) => g.kind === r.kind)?.title ?? r.kind, r] as const), ...calledToday.map((r) => ['Called today, still not answered', r] as const)]
            .map(([list, r]) => [list, r.entry_code, r.person_name, r.phone, r.category_label, r.so_name, r.branch_name, r.tries_today, r.unanswered_count, r.current_status, RAG_LABEL[r.rag] ?? r.rag, r.priority_reason])} />
      )}
      {isLoading ? <div className="space-y-3">{Array.from({ length: 4 }, (_, i) => <Skeleton key={i} className="h-16" />)}</div>
        : items.length === 0 ? <Card><EmptyState icon={<PhoneCall size={20} />} title="Nothing to call right now." hint="New entries arrive with the daily run; retries and follow-ups come back on their date." /></Card>
          : (
            <div className="space-y-6">
              {GROUPS.map((g) => {
                const rows = items.filter((r) => r.kind === g.kind)
                if (!rows.length) return null
                return (
                  <section key={g.kind} aria-label={g.title}>
                    <header className="mb-2 flex items-center gap-2">
                      <span className={cx('grid h-7 w-7 place-items-center rounded-lg', g.tone)}><g.icon size={15} aria-hidden="true" /></span>
                      <h2 className="text-sm font-semibold text-brand-900">{g.title} <span className="text-slate-400">({rows.length})</span></h2>
                      <span className="hidden text-xs text-slate-500 sm:inline">· {g.hint}</span>
                    </header>
                    <ul className="divide-y divide-slate-100 overflow-hidden rounded-2xl border border-slate-200/80 bg-white shadow-card">
                      {rows.map((r) => (
                        <CallItem key={r.allocation_id} r={r} to={path(`calls/${r.id}`)} />
                      ))}
                    </ul>
                  </section>
                )
              })}
            </div>
          )}
      {calledToday.length > 0 && (
        <section aria-label="Called today" className="mt-8">
          <header className="mb-2 flex items-center gap-2">
            <span className="grid h-7 w-7 place-items-center rounded-lg bg-slate-100 text-slate-600"><PhoneCall size={15} aria-hidden="true" /></span>
            <h2 className="text-sm font-semibold text-brand-900">Called today, still not answered <span className="text-slate-400">({calledToday.length})</span></h2>
            <span className="hidden text-xs text-slate-500 sm:inline">· {lim ? `${lim.tries_per_day_lead} tries are planned a day; up to ${lim.max_slots_per_day} can be recorded, so one more try is possible today` : 'One more try is possible today'}</span>
          </header>
          <ul className="divide-y divide-slate-100 overflow-hidden rounded-2xl border border-slate-200/80 bg-white opacity-90 shadow-card">
            {calledToday.map((r) => <CallItem key={r.allocation_id} r={r} to={path(`calls/${r.id}`)} />)}
          </ul>
        </section>
      )}
    </>
  )
}

/** One entry on a calling list: who, the SO and branch, today's tries, status and RAG. */
function CallItem({ r, to }: { r: CallRow; to: string }) {
  return (
    <li>
      <Link to={to} className="flex flex-wrap items-center gap-x-6 gap-y-2 px-5 py-4 transition hover:bg-brand-50/40 focus:outline-none focus-visible:bg-brand-50">
        <div className="min-w-0 flex-1">
          <p className="font-medium text-slate-900">{r.person_name} <span className="tabular ml-2 text-sm font-normal text-slate-500">Mobile: {r.phone}</span></p>
          <p className="text-xs text-slate-500">{r.category_label}{r.cp_subtype_label && ` · ${r.cp_subtype_label}`} · {r.so_name} · {r.branch_name} · <span className="font-mono">{r.entry_code}</span></p>
          {(r.priority_reason || r.first_try_overdue) && (
            <p className="mt-1 flex flex-wrap gap-1.5 text-xs">
              {r.priority_reason && <span className="rounded-full bg-roof-50 px-2 py-0.5 font-medium text-roof-700" data-testid="priority-reason">{r.priority_reason}</span>}
              {r.first_try_overdue && <span className="inline-flex items-center gap-1 rounded-full bg-gold-100 px-2 py-0.5 font-medium text-gold-700"><Clock size={12} aria-hidden="true" />First try overdue</span>}
            </p>
          )}
        </div>
        <div className="text-right text-xs text-slate-500">
          <div>{r.tries_today} tried today · {r.unanswered_count} unanswered</div>
          <div>{r.current_status}</div>
        </div>
        <RagBadge value={r.rag} />
      </Link>
    </li>
  )
}
