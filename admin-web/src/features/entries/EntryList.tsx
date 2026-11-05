import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { Flag, GanttChartSquare, IdCard, Search } from 'lucide-react'
import { ReactNode } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Card, EmptyState, ErrorBox, Input, PageTitle, Pager, RagBadge, Select, Skeleton, StatusText, Table, Td } from '../../components/ui'
import { api, errorMessage } from '../../services/api'
import { useAuth } from '../../services/auth'
import { fmtParts } from '../../services/format'
import { useBranches, useMeta } from '../../services/meta'
import type { EntryRow, Page } from '../../types'

const KEYS = ['q', 'branch_id', 'category', 'rag', 'status', 'date_from', 'date_to'] as const

export const entryParams = (p: URLSearchParams) => Object.fromEntries(KEYS.map((k) => [k, p.get(k) || undefined]).filter(([, v]) => v))

export function EntryFilters({ params, onChange, extra }: { params: URLSearchParams; onChange: (p: URLSearchParams) => void; extra?: ReactNode }) {
  const { data: meta } = useMeta()
  const { data: branches } = useBranches()
  const set = (k: string, v: string) => { const n = new URLSearchParams(params); v ? n.set(k, v) : n.delete(k); n.delete('page'); onChange(n) }
  return (
    <div className="mb-4 grid gap-3 rounded-2xl border border-slate-200/80 bg-white p-4 shadow-card sm:grid-cols-2 lg:grid-cols-4">
      <label className="relative sm:col-span-2">
        <span className="sr-only">Search</span>
        <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" aria-hidden="true" />
        <Input className="pl-9" placeholder="Entry ID, name, mobile, SO or Emp ID" defaultValue={params.get('q') ?? ''}
          onKeyDown={(e) => e.key === 'Enter' && set('q', (e.target as HTMLInputElement).value.trim())}
          onBlur={(e) => e.target.value.trim() !== (params.get('q') ?? '') && set('q', e.target.value.trim())} />
      </label>
      <Select aria-label="Branch" value={params.get('branch_id') ?? ''} onChange={(e) => set('branch_id', e.target.value)}>
        <option value="">All my branches</option>
        {branches?.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
      </Select>
      <Select aria-label="Category" value={params.get('category') ?? ''} onChange={(e) => set('category', e.target.value)}>
        <option value="">All categories</option>
        {meta?.categories.map((c) => <option key={c.key} value={c.key}>{c.label}</option>)}
      </Select>
      <Select aria-label="RAG" value={params.get('rag') ?? ''} onChange={(e) => set('rag', e.target.value)}>
        <option value="">Any RAG</option>
        {meta?.rags.map((r) => <option key={r} value={r}>{r}</option>)}
      </Select>
      <Select aria-label="Status" value={params.get('status') ?? ''} onChange={(e) => set('status', e.target.value)}>
        <option value="">Any status</option>
        <option value="Pending">Not yet selected</option>
        <option value="Allocate">Waiting for first call</option>
        {meta?.statuses.map((s) => <option key={s} value={s}>{s}</option>)}
      </Select>
      <label className="flex items-center gap-2 text-xs text-slate-500">From<Input type="date" value={params.get('date_from') ?? ''} onChange={(e) => set('date_from', e.target.value)} /></label>
      <label className="flex items-center gap-2 text-xs text-slate-500">To<Input type="date" value={params.get('date_to') ?? ''} onChange={(e) => set('date_to', e.target.value)} /></label>
      {extra}
    </div>
  )
}

export function EntryTable({ rows, link }: { rows: EntryRow[]; link: (r: EntryRow) => string }) {
  return (
    <Table head={['Entry', 'Person met', 'Category', 'Sales Officer', 'Made', 'Status', 'RAG', 'Next action']}>
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
            <Td><div className="font-medium text-slate-900">{r.person_name}</div><div className="tabular text-xs text-slate-500">{r.phone}</div></Td>
            <Td>{r.category_label}{r.cp_subtype_label && <div className="text-xs text-slate-500">{r.cp_subtype_label}</div>}</Td>
            <Td><div>{r.so_name}</div><div className="text-xs text-slate-500">{r.so_employee_code} · {r.branch_name}</div></Td>
            <Td className="whitespace-nowrap">{made?.date}<div className="text-xs text-slate-500">{made?.time}{r.device_time_suspect && ' · check time'}</div></Td>
            <Td><StatusText status={r.status} selection={r.selection_status} callGroup={r.call_group} />{r.lead_outcome && <div className="text-xs font-medium text-sky-700">{r.lead_outcome}</div>}</Td>
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
    <>
      <PageTitle subtitle="One entry per person met. The Entry ID is permanent; the time is the Submit press on the phone.">Entries</PageTitle>
      <EntryFilters params={params} onChange={setParams} />
      <ErrorBox error={error ? errorMessage(error) : null} />
      <Card flush>
        {isLoading || !data ? <div className="space-y-2 p-5">{Array.from({ length: 6 }, (_, i) => <Skeleton key={i} className="h-10" />)}</div>
          : data.items.length === 0 ? <EmptyState icon={<GanttChartSquare size={20} />} title="No entries match these filters." />
            : <EntryTable rows={data.items} link={(r) => path(`entries/${r.id}`)} />}
        {data && data.total > 0 && <Pager page={page} pageSize={25} total={data.total} onChange={(p) => { const n = new URLSearchParams(params); n.set('page', String(p)); setParams(n) }} />}
      </Card>
    </>
  )
}
