import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { Award, BadgeCheck, Clock, IdCard, ListChecks, Target, UserCheck, Users } from 'lucide-react'
import { useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Card, EmptyState, ErrorBox, ExportBar, Input, PageTitle, RAG_LABEL, Segmented, Skeleton, StatCard, Table, Td } from '../../components/ui'
import { tableCells } from '../../services/exporting'
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
  conversion: { since: string; from?: string; to?: string; regions: ConversionRow[]; total: Omit<ConversionRow, 'region'> }
}

interface ConversionRow { region: string | null; validated: number; logged_in: number; rejected: number; open: number }
const loginPct = (r: Omit<ConversionRow, 'region'>) => (r.validated ? `${((r.logged_in / r.validated) * 100).toFixed(1)}%` : '—')

/** What each column of the lead conversion table counts (the Takeoff master's rules). */
const CONVERSION_GUIDE: [string, string][] = [
  ['Validated leads', 'Lead-type entries (a Lead, a DSA/CP converted to a lead, or an entry carrying a lead action) that are customer-validated: a call validated them, or they are the Sankalp success. Repeat entries by the same SO are left out.'],
  ['Logged in', 'Of those, the ones that are the Sankalp success: the earliest logged-in entry for its TCS ID, with the login after the entry date. A second entry for the same customer does not count again.'],
  ['Rejected', 'Of those, the ones whose lead outcome is Rejected (a branch R1–R6 answer, or Rejected on the tracker).'],
  ['Open', 'Validated − Logged in − Rejected: still being worked by the branch or the call centre.'],
  ['Login %', 'Logged in ÷ Validated leads: how many confirmed leads became business.'],
]

export type Period = 'today' | 'week' | 'last_week' | 'month'
export const PERIODS: { value: Period; label: string }[] = [
  { value: 'today', label: 'Today' }, { value: 'week', label: 'This week' }, { value: 'last_week', label: 'Last week' }, { value: 'month', label: 'This month' },
]
const RAG_ORDER = ['GREEN', 'AMBER', 'RED', 'RNR', 'PENDING', 'NA']
const RAG_BAR: Record<string, string> = { GREEN: 'bg-emerald-500', AMBER: 'bg-amber-400', RED: 'bg-roof-500', RNR: 'bg-violet-400', PENDING: 'bg-sky-400', NA: 'bg-slate-300' }

export function RagBar({ rag, linkFor }: { rag: Record<string, number>; linkFor?: (rag: string) => string }) {
  const total = Object.values(rag).reduce((a, b) => a + b, 0)
  if (!total) return <p className="text-sm text-slate-500">No entries yet.</p>
  return (
    <div>
      <div className="flex h-3 w-full overflow-hidden rounded-full bg-slate-100" role="img" aria-label="RAG mix">
        {RAG_ORDER.filter((k) => rag[k]).map((k) => <div key={k} className={RAG_BAR[k]} style={{ width: `${(rag[k]! / total) * 100}%` }} />)}
      </div>
      <ul className="mt-3.5 grid grid-cols-3 gap-x-6 gap-y-2.5 text-xs">
        {RAG_ORDER.map((k) => {
          const item = (
            <span className="flex items-center justify-between rounded px-1.5 py-1 text-slate-600 transition hover:bg-slate-50 hover:text-slate-900">
              <span className="flex items-center gap-1.5 whitespace-nowrap">
                <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${RAG_BAR[k]}`} aria-hidden="true" />
                <span>{RAG_LABEL[k]}</span>
              </span>
              <span className="tabular font-semibold text-slate-800">{rag[k] ?? 0}</span>
            </span>
          )
          return (
            <li key={k}>
              {linkFor ? <Link to={linkFor(k)} className="hover:underline block">{item}</Link> : item}
            </li>
          )
        })}
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
  // the lead conversion's own range of entry dates (blank: from Takeoff start to today)
  const [convFrom, setConvFrom] = useState('')
  const [convTo, setConvTo] = useState('')
  const conversionTableRef = useRef<HTMLTableElement>(null)
  const branchesTableRef = useRef<HTMLTableElement>(null)
  const { data, isLoading, error } = useQuery({
    queryKey: ['dashboard', period, convFrom, convTo],
    queryFn: async () => (await api.get<Dash>('/dashboard', { params: { period, conv_from: convFrom || undefined, conv_to: convTo || undefined } })).data,
    placeholderData: keepPreviousData,
  })
  const scope = me?.branch_name ?? me?.cluster_name ?? me?.region_name ?? 'All regions'
  const t = data?.totals

  const entriesUrl = (extra: Record<string, string>) => {
    if (!data) return path('entries')
    const p = new URLSearchParams({
      date_from: data.period.from,
      date_to: data.period.to,
      date_field: 'count',
      ...extra,
    })
    return path(`entries?${p.toString()}`)
  }

  const conversionHead = ['Region', 'Validated leads', 'Logged in', 'Rejected', 'Open', 'Login %']
  const branchesHead = ['Branch', 'Region', 'Sales Officers', 'Entries', 'Lead / Prospect entries', 'Validated', 'Logged in', 'Green', 'Amber', 'Red']

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
            <StatCard
              label="Entries"
              value={t.entries}
              testId="kpi-entries"
              icon={<ListChecks size={20} />}
              hint={`${t.active_sos} Sales Officers`}
              linkTo={can('entries.read') ? entriesUrl({}) : undefined}
            />
            <StatCard
              label="Lead / Prospect"
              value={t.lead_prospect}
              icon={<Target size={20} />}
              tone="gold"
              hint={`${t.dsa_cp} DSA / CP`}
              linkTo={can('entries.read') ? entriesUrl({ call_group: 'lead' }) : undefined}
            />
            <StatCard
              label="Customers validated"
              value={t.validated}
              testId="kpi-validated"
              icon={<BadgeCheck size={20} />}
              tone="green"
              linkTo={can('entries.read') ? entriesUrl({ customer_validated: 'true' }) : undefined}
            />
            <StatCard
              label="Logged in"
              value={t.logged_in}
              icon={<IdCard size={20} />}
              tone="blue"
              hint={`${t.sankalp_success} Sankalp successes`}
              linkTo={can('entries.read') ? entriesUrl({ lead_outcome: 'Logged in' }) : undefined}
            />
            <StatCard
              label="Awaiting first call"
              value={t.awaiting_call}
              icon={<Clock size={20} />}
              hint="Selected, not yet called"
              linkTo={can('entries.read') ? entriesUrl({ status: 'Allocate' }) : undefined}
            />
            <StatCard
              label="Open SO / branch actions"
              value={t.open_so_actions}
              icon={<UserCheck size={20} />}
              tone="red"
              linkTo={can('entries.read') ? entriesUrl({ has_action: 'true' }) : undefined}
              hint="Filter entries with open actions"
            />
            <StatCard
              label="Sankalp success"
              value={t.sankalp_success}
              icon={<Award size={20} />}
              tone="gold"
              hint="Earliest entry per TCS ID"
              linkTo={can('entries.read') ? entriesUrl({ sankalp_success: 'true' }) : undefined}
            />
            <StatCard
              label="Active Sales Officers"
              value={t.active_sos}
              icon={<Users size={20} />}
              hint={`${data.period.from} to ${data.period.to}`}
              linkTo={can('team.read') ? path('team') : (can('entries.read') ? entriesUrl({}) : undefined)}
            />
          </div>

          <div className="mt-6 grid gap-6 lg:grid-cols-2">
            <Card title="Entries per day" subtitle="By count date (Sundays and holidays count on the next working day)"><Trend trend={data.trend} /></Card>
            <Card title="RAG" subtitle="Where the entries of this period stand now">
              <RagBar rag={data.rag} linkFor={can('entries.read') ? (k) => entriesUrl({ rag: k }) : undefined} />
            </Card>
          </div>

          <div className="mt-6 grid gap-6 lg:grid-cols-2">
            <Card title="By category">
              <ul className="space-y-2.5">
                {Object.entries(data.by_category).sort((a, b) => b[1] - a[1]).map(([k, v]) => (
                  <li key={k} className="flex items-center gap-3 text-sm">
                    {can('entries.read') ? (
                      <Link to={entriesUrl({ category: k })} className="w-36 shrink-0 text-slate-600 hover:text-brand-700 hover:underline truncate">
                        {k}
                      </Link>
                    ) : (
                      <span className="w-36 shrink-0 text-slate-600 truncate">{k}</span>
                    )}
                    <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-100">
                      <div className="h-full rounded-full bg-brand-600" style={{ width: `${(v / Math.max(1, t.entries)) * 100}%` }} />
                    </div>
                    <span className="tabular w-10 text-right font-semibold text-slate-800">{v}</span>
                  </li>
                ))}
                {!Object.keys(data.by_category).length && <li className="text-sm text-slate-500">No entries in this period.</li>}
              </ul>
            </Card>
            <Card title="By status" subtitle="Selection result until the first call, then the call status">
              <ul className="max-h-72 space-y-1.5 overflow-y-auto text-sm">
                {Object.entries(data.by_status).sort((a, b) => b[1] - a[1]).map(([k, v]) => (
                  <li key={k} className="flex justify-between gap-3 border-b border-slate-100 pb-1.5 hover:bg-slate-50 px-1 rounded transition">
                    {can('entries.read') ? (
                      <Link to={entriesUrl({ status: k })} className="text-slate-600 hover:text-brand-700 hover:underline flex-1 flex justify-between">
                        <span>{k}</span>
                        <span className="tabular font-semibold text-slate-800">{v}</span>
                      </Link>
                    ) : (
                      <>
                        <span className="text-slate-600">{k}</span>
                        <span className="tabular font-semibold text-slate-800">{v}</span>
                      </>
                    )}
                  </li>
                ))}
              </ul>
            </Card>
          </div>

          <Card title="Sankalp lead conversion" className="mt-6" flush
            subtitle={`Takeoff leads validated by the call centre, by region · entries made from ${data.conversion.from ?? data.conversion.since} to ${data.conversion.to ?? 'today'}, whatever the period above`}
            actions={<div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
              <span>Entries from</span>
              <Input type="date" aria-label="Lead conversion from" className="!w-auto !py-1 !text-xs" value={convFrom || data.conversion.from || ''} min={data.conversion.since} onChange={(e) => setConvFrom(e.target.value)} />
              <span>to</span>
              <Input type="date" aria-label="Lead conversion to" className="!w-auto !py-1 !text-xs" value={convTo || data.conversion.to || ''} onChange={(e) => setConvTo(e.target.value)} />
              {(convFrom || convTo) && <button type="button" className="font-semibold text-brand-700 hover:underline" onClick={() => { setConvFrom(''); setConvTo('') }}>All since Takeoff start</button>}
              {data.conversion.regions.length > 0 && (
                <ExportBar compact name="Lead conversion" header={conversionHead} rows={() => tableCells(conversionTableRef.current!, conversionHead.map(() => true))} />
              )}
            </div>}>
            {data.conversion.regions.length === 0 ? <EmptyState icon={<BadgeCheck size={20} />} title="No validated leads yet." /> : (
              <Table head={conversionHead} tableRef={conversionTableRef}>
                {data.conversion.regions.map((c) => (
                  <tr key={c.region ?? '—'}>
                    <Td className="font-medium text-slate-900">{c.region ?? '—'}</Td><Td className="tabular">{c.validated}</Td>
                    <Td className="tabular text-emerald-700">{c.logged_in}</Td><Td className="tabular text-roof-700">{c.rejected}</Td>
                    <Td className="tabular">{c.open}</Td><Td className="tabular font-semibold">{loginPct(c)}</Td>
                  </tr>
                ))}
                <tr className="bg-slate-50 font-semibold text-slate-900">
                  <Td>Total</Td><Td className="tabular">{data.conversion.total.validated}</Td>
                  <Td className="tabular text-emerald-700">{data.conversion.total.logged_in}</Td>
                  <Td className="tabular text-roof-700">{data.conversion.total.rejected}</Td>
                  <Td className="tabular">{data.conversion.total.open}</Td><Td className="tabular">{loginPct(data.conversion.total)}</Td>
                </tr>
              </Table>
            )}
            <details className="border-t border-slate-100 px-5 py-3 text-sm">
              <summary className="cursor-pointer font-medium text-brand-700">What the columns count</summary>
              <dl className="mt-3 space-y-2">
                {CONVERSION_GUIDE.map(([k, v]) => <div key={k}><dt className="font-semibold text-slate-800">{k}</dt><dd className="text-slate-600">{v}</dd></div>)}
              </dl>
            </details>
          </Card>

          <Card title="Branches" className="mt-6" flush
            actions={data.branches.length > 0 && (
              <ExportBar compact name="Branches" header={branchesHead} rows={() => tableCells(branchesTableRef.current!, branchesHead.map(() => true))} />
            )}>
            {data.branches.length === 0 ? <EmptyState icon={<ListChecks size={20} />} title="No entries in this period." /> : (
              <Table head={branchesHead} tableRef={branchesTableRef} maxHeight="max-h-[min(480px,60vh)]">
                {data.branches.map((b) => (
                  <tr key={b.branch_id} className="hover:bg-slate-50/80 transition">
                    <Td className="font-medium text-slate-900">
                      {can('entries.read') ? (
                        <Link to={entriesUrl({ branch_id: b.branch_id })} className="text-brand-700 hover:underline">
                          {b.branch}
                        </Link>
                      ) : (
                        b.branch
                      )}
                    </Td>
                    <Td>{b.region ?? '—'}</Td>
                    <Td className="tabular">{b.sos}</Td>
                    <Td className="tabular">{b.entries}</Td>
                    <Td className="tabular">{b.lead_prospect}</Td>
                    <Td className="tabular">{b.validated}</Td>
                    <Td className="tabular">{b.logged_in}</Td>
                    <Td className="tabular text-emerald-700">{b.green}</Td>
                    <Td className="tabular text-amber-700">{b.amber}</Td>
                    <Td className="tabular text-roof-700">{b.red}</Td>
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
