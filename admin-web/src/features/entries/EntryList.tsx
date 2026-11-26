import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { Flag, GanttChartSquare, IdCard, Search, X } from 'lucide-react'
import { ReactNode, useMemo } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Card, EmptyState, ErrorBox, Input, PageTitle, Pager, RAG_LABEL, RagBadge, Select, Skeleton, StatusText, Table, Td } from '../../components/ui'
import { api, errorMessage } from '../../services/api'
import { allPages, type Cells } from '../../services/exporting'
import { useAuth } from '../../services/auth'
import { fmtParts } from '../../services/format'
import { useBranches, useMeta } from '../../services/meta'
import type { EntryRow, Page } from '../../types'

const KEYS = [
  'q',
  'branch_id',
  'region_id',
  'so_user_id',
  'category',
  'call_group',
  'rag',
  'status',
  'date_from',
  'date_to',
  'date_field',
  'customer_validated',
  'sankalp_success',
  'lead_outcome',
  'has_action',
] as const

export const entryParams = (p: URLSearchParams) => Object.fromEntries(KEYS.map((k) => [k, p.get(k) || undefined]).filter(([, v]) => v))

export function EntryFilters({ params, onChange, extra }: { params: URLSearchParams; onChange: (p: URLSearchParams) => void; extra?: ReactNode }) {
  const { data: meta } = useMeta()
  const { data: branches } = useBranches()
  const set = (k: string, v: string) => { const n = new URLSearchParams(params); v ? n.set(k, v) : n.delete(k); n.delete('page'); onChange(n) }

  const kpiFilterLabel = useMemo(() => {
    if (params.get('customer_validated') === 'true') return 'Customers validated'
    if (params.get('sankalp_success') === 'true') return 'Sankalp success'
    if (params.get('lead_outcome')) return `Logged in (${params.get('lead_outcome')})`
    if (params.get('call_group') === 'lead') return 'Lead / Prospect'
    if (params.get('call_group') === 'dsa_cp') return 'DSA / CP'
    if (params.get('has_action') === 'true') return 'Open SO / branch actions'
    if (params.get('status') === 'Allocate') return 'Awaiting first call (Allocate)'
    if (params.get('date_field') === 'count') return 'Dashboard period entries'
    return null
  }, [params])

  const clearKpi = () => {
    const n = new URLSearchParams(params)
    n.delete('customer_validated')
    n.delete('sankalp_success')
    n.delete('lead_outcome')
    n.delete('call_group')
    n.delete('has_action')
    n.delete('date_field')
    n.delete('date_from')
    n.delete('date_to')
    n.delete('status')
    n.delete('page')
    onChange(n)
  }

  return (
    <div className="mb-2.5 sm:mb-3 space-y-2.5 shrink-0">
      {kpiFilterLabel && (
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl bg-brand-50 border border-brand-200 px-3.5 py-2 text-xs text-brand-900 shadow-sm">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-semibold text-brand-800">Filtered from Dashboard:</span>
            <span className="rounded-md bg-white px-2 py-0.5 font-medium text-slate-800 border border-brand-200">
              {kpiFilterLabel}
            </span>
            {params.get('date_from') && params.get('date_to') && (
              <span className="rounded-md bg-white px-2 py-0.5 text-slate-600 border border-brand-200">
                Count date: {params.get('date_from')} to {params.get('date_to')}
              </span>
            )}
          </div>
          <button
            type="button"
            onClick={clearKpi}
            className="inline-flex items-center gap-1 font-semibold text-brand-700 hover:text-brand-950 underline"
          >
            <X size={13} aria-hidden="true" /> Clear dashboard filter
          </button>
        </div>
      )}

      <div className="grid gap-2 sm:gap-2.5 rounded-2xl border border-slate-200/80 bg-white p-3 sm:p-3.5 shadow-card sm:grid-cols-2 lg:grid-cols-4">
        <label className="relative sm:col-span-2">
          <span className="sr-only">Search</span>
          <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" aria-hidden="true" />
          <Input className="pl-9 !py-1.5 !text-sm" placeholder="Entry ID, name, mobile, SO or Emp ID" defaultValue={params.get('q') ?? ''}
            onKeyDown={(e) => e.key === 'Enter' && set('q', (e.target as HTMLInputElement).value.trim())}
            onBlur={(e) => e.target.value.trim() !== (params.get('q') ?? '') && set('q', e.target.value.trim())} />
        </label>
        <Select aria-label="Branch" className="!py-1.5 !text-sm" value={params.get('branch_id') ?? ''} onChange={(e) => set('branch_id', e.target.value)}>
          <option value="">All my branches</option>
          {branches?.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
        </Select>
        <Select aria-label="Category" className="!py-1.5 !text-sm" value={params.get('category') ?? ''} onChange={(e) => set('category', e.target.value)}>
          <option value="">All categories</option>
          {meta?.categories.map((c) => <option key={c.key} value={c.key}>{c.label}</option>)}
        </Select>
        <Select aria-label="RAG" className="!py-1.5 !text-sm" value={params.get('rag') ?? ''} onChange={(e) => set('rag', e.target.value)}>
          <option value="">Any RAG</option>
          {meta?.rags.map((r) => <option key={r} value={r}>{RAG_LABEL[r] ?? r}</option>)}
        </Select>
        <Select aria-label="Status" className="!py-1.5 !text-sm" value={params.get('status') ?? ''} onChange={(e) => set('status', e.target.value)}>
          <option value="">Any status</option>
          <option value="Pending">Waiting for the daily selection</option>
          <option value="Allocate">Waiting for the first call</option>
          {meta?.statuses.map((s) => <option key={s} value={s}>{s}</option>)}
        </Select>
        <label className="flex items-center gap-2 text-xs text-slate-500">From<Input type="date" className="!py-1.5 !text-sm" value={params.get('date_from') ?? ''} onChange={(e) => set('date_from', e.target.value)} /></label>
        <label className="flex items-center gap-2 text-xs text-slate-500">To<Input type="date" className="!py-1.5 !text-sm" value={params.get('date_to') ?? ''} onChange={(e) => set('date_to', e.target.value)} /></label>
        {extra}
      </div>
    </div>
  )
}

/** The columns of an entries export: one fact per column, in plain words. */
const ENTRY_EXPORT: [string, (r: EntryRow) => Cells[number]][] = [
  ['Entry ID', (r) => r.entry_code], ['Person met', (r) => r.person_name], ['Mobile number', (r) => r.phone],
  ['Category', (r) => r.category_label], ['CP sub-type', (r) => r.cp_subtype_label], ['Sales Officer', (r) => r.so_name],
  ['Emp ID', (r) => r.so_employee_code], ['Branch', (r) => r.branch_name], ['Region', (r) => r.region_name],
  ['Entry date', (r) => r.entry_date], ['Entered at (phone time)', (r) => r.submitted_at_device], ['Current status', (r) => r.current_status],
  ['RAG', (r) => RAG_LABEL[r.rag] ?? r.rag], ['Next action (SO / branch)', (r) => r.so_action], ['Next action date', (r) => r.so_action_date],
  ['Call-centre action', (r) => r.cc_action], ['Call-centre action date', (r) => r.cc_action_date], ['TCS ID (login)', (r) => r.tcs_id],
  ['Customer validated', (r) => (r.customer_validated ? 'Yes' : 'No')], ['Sankalp success', (r) => (r.sankalp_success ? 'Yes' : 'No')],
]

export function EntryTable({ rows, link, exportName, exportAll }: {
  rows: EntryRow[]; link: (r: EntryRow) => string; exportName?: string; exportAll?: () => Promise<EntryRow[]>
}) {
  return (
    <Table
      head={['Entry ID', 'Person met (mobile number)', 'Category', 'Sales Officer (Emp ID · branch)', 'Entered on (phone time)', 'Current status', 'RAG', 'Next action']}
      exportName={exportName}
      exportHeader={ENTRY_EXPORT.map(([h]) => h)}
      exportAll={async () => ((exportAll ? await exportAll() : rows).map((r) => ENTRY_EXPORT.map(([, f]) => f(r))))}
      maxHeight="max-h-[calc(100vh-23.5rem)]"
      containerClassName="flex-1 min-h-0"
    >
      {rows.map((r) => {
        const made = fmtParts(r.submitted_at_device)
        return (
          <tr key={r.id}>
            <Td className="whitespace-nowrap">
              <Link className="font-mono text-xs font-semibold text-brand-700 hover:underline" to={link(r)}>{r.entry_code}</Link>
              <div className="mt-0.5 flex gap-1.5 text-[11px]">
                {r.priority && <span className="inline-flex items-center gap-0.5 font-semibold text-roof-600"><Flag size={11} aria-hidden="true" />PRIORITY</span>}
                {r.tcs_id && <span className="inline-flex items-center gap-0.5 text-sky-700"><IdCard size={11} aria-hidden="true" />{r.tcs_id}</span>}
              </div>
            </Td>
            <Td><div className="font-medium text-slate-900">{r.person_name}</div><div className="tabular text-xs text-slate-500">Mobile: {r.phone}</div></Td>
            <Td>{r.category_label}{r.cp_subtype_label && <div className="text-xs text-slate-500">{r.cp_subtype_label}</div>}</Td>
            <Td><div>{r.so_name}</div><div className="text-xs text-slate-500">{r.so_employee_code} · {r.branch_name}</div></Td>
            <Td className="whitespace-nowrap">{made?.date}<div className="text-xs text-slate-500">{made?.time}{r.device_time_suspect && ' · check time'}</div></Td>
            <Td><StatusText value={r.current_status} /></Td>
            <Td><RagBadge value={r.rag} overridden={r.rag_overridden} /></Td>
            <Td className="text-xs">
              {r.so_action && <div><span className="font-medium text-slate-800">{r.so_action}</span>{r.so_action_date && ` · ${r.so_action_date}`}</div>}
              {r.cc_action && <div className="text-slate-500">Call centre: {r.cc_action}{r.cc_action_date && ` · ${r.cc_action_date}`}</div>}
              {!r.so_action && !r.cc_action && r.expired_action && <div className="text-roof-600">Expired: {r.expired_action}{r.expired_on && ` · ${r.expired_on}`}</div>}
              {!r.so_action && !r.cc_action && !r.expired_action && <span className="text-slate-400">—</span>}
            </Td>
          </tr>
        )
      })}
    </Table>
  )
}

export default function EntryList() {
  const { path } = useAuth()
  const [params, setParams] = useSearchParams()
  const page = Number(params.get('page') ?? 1)
  const { data, isLoading, error } = useQuery({
    queryKey: ['entries', Object.fromEntries(params)],
    queryFn: async () => (await api.get<Page<EntryRow>>('/entries', { params: { ...entryParams(params), page, page_size: 25 } })).data,
    placeholderData: keepPreviousData,
  })
  return (
    <div className="flex-1 flex flex-col min-h-0">
      <PageTitle subtitle="One entry per person met. The Entry ID is permanent; the time is the Submit press on the phone.">Entries</PageTitle>
      <EntryFilters params={params} onChange={setParams} />
      <ErrorBox error={error ? errorMessage(error) : null} />
      <Card flush className="flex-1 min-h-0 flex flex-col justify-between">
        {isLoading || !data ? <div className="space-y-2 p-5">{Array.from({ length: 6 }, (_, i) => <Skeleton key={i} className="h-10" />)}</div>
          : data.items.length === 0 ? <EmptyState icon={<GanttChartSquare size={20} />} title="No entries match these filters." />
            : <EntryTable rows={data.items} link={(r) => path(`entries/${r.id}`)} exportName="Entries" exportAll={() => allPages<EntryRow>('/entries', entryParams(params))} />}
        {data && data.total > 0 && <Pager page={page} pageSize={25} total={data.total} onChange={(p) => { const n = new URLSearchParams(params); n.set('page', String(p)); setParams(n) }} />}
      </Card>
    </div>
  )
}
