import { useQuery } from '@tanstack/react-query'
import { ClipboardList } from 'lucide-react'
import { useState } from 'react'
import { Card, EmptyState, ErrorBox, Input, PageTitle, Pager, Segmented, Select, Skeleton, Table, Td } from '../../components/ui'
import { api, errorMessage } from '../../services/api'
import { useAuth } from '../../services/auth'
import { useMeta } from '../../services/meta'
import type { EntryRow, Page } from '../../types'
import { allPages } from '../../services/exporting'
import { EntryTable } from '../entries/EntryList'

const KINDS = [
  { value: '', label: 'All' }, { value: 'Correct customer number', label: 'Correct number' },
  { value: 'lead', label: 'Lead actions' }, { value: 'DSA/CP follow-up', label: 'DSA/CP follow-up' },
]
const VIEWS = [{ value: 'open', label: 'Open' }, { value: 'expired', label: 'Expired unworked' }]
const PAGE = 100

interface TotalsRow { id: string | null; label: string; region: string | null; counts: Record<string, number>; total: number }
interface Totals { columns: string[]; rows: TotalsRow[]; total: { counts: Record<string, number>; total: number } }
// The Takeoff master's two SO / branch action sheets, each with its "Totals by region"
const LISTS = [{ value: 'lead', label: 'Leads & prospects' }, { value: 'dsa', label: 'DSAs & contact points' }]
const BYS = [{ value: 'region', label: 'By region' }, { value: 'branch', label: 'By branch' }]

/** Open (or expired) actions counted per action, for either list, by region or by branch (narrowed to one region). */
function ActionTotals({ expired, dates }: { expired: boolean; dates: { date_from?: string; date_to?: string } }) {
  const [list, setList] = useState('lead')
  const [by, setBy] = useState('region')
  const [region, setRegion] = useState('')
  const { data, isLoading, error } = useQuery({
    queryKey: ['entries', 'actions', 'totals', expired, list, by, dates],
    queryFn: async () => (await api.get<Totals>('/branch/actions/totals', { params: { list, by, expired: expired || undefined, ...dates } })).data,
  })
  const regions = [...new Set((data?.rows ?? []).map((r) => r.region).filter((r): r is string => !!r))].sort()
  const rows = (data?.rows ?? []).filter((r) => by === 'region' || !region || r.region === region)
  const cols = data?.columns ?? []
  const sum = (a: string) => rows.reduce((n, r) => n + (r.counts[a] ?? 0), 0)
  const listLabel = LISTS.find((l) => l.value === list)!.label
  return (
    <Card flush className="mb-6" title={`${expired ? 'Expired actions' : 'Open actions'}: totals by ${by}`}
      subtitle={`${listLabel}. Counted where the lead is worked (the handling branch, else the SO's branch), the same entries as the list below.`}
      actions={<div className="flex flex-wrap items-center gap-2">
        <Segmented label="List" options={LISTS} value={list} onChange={setList} />
        <Segmented label="Group by" options={BYS} value={by} onChange={(v) => { setBy(v); setRegion('') }} />
        {by === 'branch' && (
          <Select aria-label="Region" className="w-48 py-1.5" value={region} onChange={(e) => setRegion(e.target.value)}>
            <option value="">All regions</option>{regions.map((r) => <option key={r} value={r}>{r}</option>)}
          </Select>
        )}
      </div>}>
      <ErrorBox error={error ? errorMessage(error) : null} />
      {isLoading ? <div className="p-5"><Skeleton className="h-40" /></div>
        : rows.length === 0 ? <EmptyState icon={<ClipboardList size={20} />} title="Nothing to count." />
          : (
            <Table head={[by === 'branch' ? 'Branch' : 'Region', ...(by === 'branch' ? ['Region'] : []), ...cols, 'Total']}
              exportName={`${expired ? 'Expired' : 'Open'} actions by ${by} - ${listLabel}${region ? ` - ${region}` : ''}`}>
              {rows.map((r) => (
                <tr key={r.id ?? r.label}>
                  <Td className="font-medium">{r.label}</Td>{by === 'branch' && <Td>{r.region ?? '–'}</Td>}
                  {cols.map((a) => <Td key={a} className="tabular text-right">{r.counts[a] ?? 0}</Td>)}
                  <Td className="tabular text-right font-semibold">{r.total}</Td>
                </tr>
              ))}
              <tr className="bg-slate-50 font-semibold">
                <Td>Total</Td>{by === 'branch' && <Td>{region || 'All regions'}</Td>}
                {cols.map((a) => <Td key={a} className="tabular text-right">{sum(a)}</Td>)}
                <Td className="tabular text-right">{rows.reduce((n, r) => n + r.total, 0)}</Td>
              </tr>
            </Table>
          )}
    </Card>
  )
}

/** 12.1: SO / branch actions in my scope, and (12.3) actions whose window ran out before anyone acted. */
export default function Actions() {
  const { path } = useAuth()
  const { data: meta } = useMeta()
  const [kind, setKind] = useState('')
  const [view, setView] = useState('open')
  const [page, setPage] = useState(1)
  // entries made in this range (blank: every entry); applies to the totals and the list
  const [from, setFrom] = useState('')
  const [to, setTo] = useState('')
  const dates = { date_from: from || undefined, date_to: to || undefined }
  const { data, isLoading, error } = useQuery({
    queryKey: ['entries', 'actions', view, kind, page, from, to],
    queryFn: async () => (await api.get<Page<EntryRow>>('/branch/actions', { params: { expired: view === 'expired' || undefined, action: kind || undefined, page, page_size: PAGE, ...dates } })).data,
  })
  const lim = meta?.limits
  const rows = data?.items ?? []
  return (
    <>
      <PageTitle subtitle={view === 'expired'
        ? 'Actions whose window ran out before anyone acted on them: kept here so they can be followed up.'
        : `What Sales Officers and branches need to do next, from the latest call.${lim ? ` "Correct number" stays open ${lim.correct_number_window_days} days from the entry; lead actions until login or rejection; others ${lim.action_window_days} days.` : ''}`}
        actions={<div className="flex flex-wrap gap-2">
          <Segmented label="View" options={VIEWS} value={view} onChange={(v) => { setView(v); setPage(1) }} />
          <Segmented label="Action" options={KINDS} value={kind} onChange={(v) => { setKind(v); setPage(1) }} />
          <div className="flex items-center gap-1.5 text-xs text-slate-500">
            <span>Entries from</span>
            <Input type="date" aria-label="Entries from" className="w-auto py-1 text-xs" value={from} max={to || undefined} onChange={(e) => { setFrom(e.target.value); setPage(1) }} />
            <span>to</span>
            <Input type="date" aria-label="Entries to" className="w-auto py-1 text-xs" value={to} min={from || undefined} onChange={(e) => { setTo(e.target.value); setPage(1) }} />
            {(from || to) && <button type="button" className="font-semibold text-brand-700 hover:underline" onClick={() => { setFrom(''); setTo(''); setPage(1) }}>All dates</button>}
          </div>
        </div>}>
        {view === 'expired' ? 'Expired actions' : 'Open actions'}
      </PageTitle>
      <ErrorBox error={error ? errorMessage(error) : null} />
      <ActionTotals expired={view === 'expired'} dates={dates} />
      <Card flush>
        {isLoading ? <div className="space-y-2 p-5">{Array.from({ length: 4 }, (_, i) => <Skeleton key={i} className="h-10" />)}</div>
          : rows.length === 0 ? <EmptyState icon={<ClipboardList size={20} />} title={view === 'expired' ? 'Nothing expired.' : 'Nothing open.'} />
            : <>
              <EntryTable rows={rows} link={(r) => path(`entries/${r.id}`)} exportName={view === 'expired' ? 'Expired actions' : 'Open actions'}
                exportAll={() => allPages<EntryRow>('/branch/actions', { expired: view === 'expired' || undefined, action: kind || undefined, ...dates })} />
              <Pager page={page} pageSize={PAGE} total={data?.total ?? 0} onChange={setPage} />
            </>}
      </Card>
    </>
  )
}
