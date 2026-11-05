import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { BarChart3, Download } from 'lucide-react'
import { useState } from 'react'
import { Button, Card, cx, EmptyState, ErrorBox, Input, PageTitle, Select, Skeleton, StatCard, Table, Td } from '../../components/ui'
import { api, download, errorMessage } from '../../services/api'
import { useAuth } from '../../services/auth'
import { useBranches, useRegions } from '../../services/meta'

interface Row { so_user_id: string; emp_code: string; name: string; designation: string | null; branch: string | null; region: string | null; attendance: string | null; state: string; entries: number; lead_prospect: number; shortfall: number | 'AB' | null; lead_shortfall: number | null; met_target: boolean; met_lead_target: boolean }
interface Data { day: string; entry_target: number; lead_target: number; summary: Record<string, number>; items: Row[] }

const isoToday = () => new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10)

/** Section 4.5: 10 entries per present SO per day (all categories), 5 genuine Lead/Prospect; "AB" when absent. */
export default function Compliance() {
  const { can } = useAuth()
  const { data: branches } = useBranches()
  const { data: regions } = useRegions()
  const [day, setDay] = useState(isoToday())
  const [branch, setBranch] = useState('')
  const [region, setRegion] = useState('')
  const [q, setQ] = useState('')
  const [range, setRange] = useState({ from: isoToday(), to: isoToday() })
  const { data, isLoading, error } = useQuery({
    queryKey: ['compliance', day, branch, region, q],
    queryFn: async () => (await api.get<Data>('/compliance', { params: { day, branch_id: branch || undefined, region_id: region || undefined, q: q.trim() || undefined } })).data,
    placeholderData: keepPreviousData,
  })
  const s = data?.summary ?? {}
  const pct = (n?: number) => (s.expected ? `${Math.round(((n ?? 0) / s.expected) * 100)}%` : '—')
  const shownBranches = branches?.filter((b) => !region || b.region_id === region)
  return (
    <>
      <PageTitle subtitle="Entries counted on their count date. Joiners are N/A before their joining date; people who left are not listed after their exit date."
        actions={<>
          <Input type="date" aria-label="Day" value={day} onChange={(e) => setDay(e.target.value)} className="w-auto" />
          {(regions?.length ?? 0) > 1 && (
            <Select aria-label="Region" value={region} onChange={(e) => { setRegion(e.target.value); setBranch('') }} className="w-auto">
              <option value="">All regions</option>{regions?.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
            </Select>
          )}
          <Select aria-label="Branch" value={branch} onChange={(e) => setBranch(e.target.value)} className="w-auto">
            <option value="">All my branches</option>{shownBranches?.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
          </Select>
          <Input aria-label="Search Sales Officer" placeholder="Name or Emp ID" value={q} onChange={(e) => setQ(e.target.value)} className="w-44" />
        </>}>
        Daily compliance
      </PageTitle>
      <ErrorBox error={error ? errorMessage(error) : null} />
      {data && (
        <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard label="Sales Officers" value={s.sos ?? 0} hint={`${s.present ?? 0} present · ${s.absent ?? 0} absent · ${s['no attendance'] ?? 0} not marked`} />
          <StatCard label="Entries" value={s.entries ?? 0} tone="gold" hint={`Target ${data.entry_target} per present SO`} />
          <StatCard label="Met the target" value={s.met_target ?? 0} tone="green" testId="kpi-met" hint={`${pct(s.met_target)} of ${s.expected ?? 0} expected · ${data.entry_target}+ entries`} />
          <StatCard label="Met Lead/Prospect" value={s.met_lead_target ?? 0} tone="blue" testId="kpi-met-lead" hint={`${pct(s.met_lead_target)} · ${data.lead_target}+ genuine · ${s['N/A'] ?? 0} joiners N/A`} />
        </div>
      )}
      <Card flush>
        {isLoading || !data ? <div className="space-y-2 p-5">{Array.from({ length: 5 }, (_, i) => <Skeleton key={i} className="h-10" />)}</div>
          : data.items.length === 0 ? <EmptyState icon={<BarChart3 size={20} />} title="No Sales Officers in your scope." />
            : (
              <Table head={['Sales Officer', 'Branch', 'Attendance', 'Entries', `Shortfall (of ${data.entry_target})`, `Lead/Prospect (of ${data.lead_target})`]}>
                {data.items.map((r) => (
                  <tr key={r.so_user_id}>
                    <Td><div className="font-medium text-slate-900">{r.name}</div><div className="text-xs text-slate-500">{r.emp_code}{r.designation && ` · ${r.designation}`}</div></Td>
                    <Td>{r.branch ?? '—'}{r.region && <div className="text-xs text-slate-500">{r.region}</div>}</Td>
                    <Td>{r.state === 'N/A' ? 'Not joined yet' : r.attendance ?? <span className="text-slate-400">not marked</span>}</Td>
                    <Td className="tabular font-semibold">{r.entries}</Td>
                    <Td className={cx('tabular font-semibold', r.shortfall === 'AB' ? 'text-slate-500' : r.shortfall === 0 ? 'text-emerald-700' : 'text-roof-600')}>{r.shortfall ?? 'N/A'}</Td>
                    <Td className="tabular">{r.lead_prospect}{r.lead_shortfall ? <span className="ml-1 text-xs text-roof-600">(−{r.lead_shortfall})</span> : null}</Td>
                  </tr>
                ))}
              </Table>
            )}
      </Card>
      {can('compliance.export') && (
        <Card title="Export" subtitle="One row per Sales Officer per day, for publishing the daily compliance (the region and branch chosen above apply)" className="mt-6">
          <div className="flex flex-wrap items-end gap-3">
            <label className="text-xs text-slate-500">From<Input type="date" value={range.from} onChange={(e) => setRange({ ...range, from: e.target.value })} /></label>
            <label className="text-xs text-slate-500">To<Input type="date" value={range.to} onChange={(e) => setRange({ ...range, to: e.target.value })} /></label>
            <Button variant="secondary" onClick={() => download('/compliance/export.csv', { date_from: range.from, date_to: range.to, region_id: region || undefined, branch_id: branch || undefined }, `sankalp_compliance_${range.from}_${range.to}.csv`)}>
              <Download size={16} aria-hidden="true" />Download CSV
            </Button>
          </div>
        </Card>
      )}
    </>
  )
}
