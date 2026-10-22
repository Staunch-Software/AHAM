import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { Camera, ClipboardList, MapPin, MapPinOff } from 'lucide-react'
import { Link, useSearchParams } from 'react-router-dom'
import { Avatar, Badge, Card, EmptyState, ErrorBox, PageTitle, Pager, Segmented, Skeleton, Table, Td } from '../../components/ui'
import { api, errorMessage } from '../../services/api'
import { fmtParts } from '../../services/format'
import type { Page, SubmissionRow } from '../../types'
import { Filters, filterParams } from './Filters'

const TABS = [
  { value: '', label: 'All' },
  { value: 'pending', label: 'Pending review' },
  { value: 'rejected', label: 'Needs correction' },
  { value: 'approved', label: 'Approved' },
]

function When({ ts }: { ts: string }) {
  const p = fmtParts(ts)
  if (!p) return <span>—</span>
  return <span className="whitespace-nowrap"><span className="block text-slate-800">{p.date}</span><span className="tabular block text-xs text-slate-500">{p.time}</span></span>
}

export default function SubmissionList() {
  const [params, setParams] = useSearchParams()
  const page = Number(params.get('page') ?? 1)
  const { data, isLoading, error } = useQuery({
    queryKey: ['submissions', 'list', Object.fromEntries(params)],
    queryFn: async () => (await api.get<Page<SubmissionRow>>('/submissions', { params: { ...filterParams(params), page, page_size: 25 } })).data,
    placeholderData: keepPreviousData,
  })
  const setReview = (v: string) => {
    const n = new URLSearchParams(params)
    v ? n.set('review_status', v) : n.delete('review_status')
    n.delete('page')
    setParams(n)
  }
  return (
    <>
      <PageTitle subtitle="Every report from the field, newest first.">Submissions</PageTitle>
      <div className="mb-4"><Segmented label="Review status" options={TABS} value={params.get('review_status') ?? ''} onChange={setReview} /></div>
      <Filters params={params} onChange={setParams} hide={['review_status']} />
      <ErrorBox error={error ? errorMessage(error) : null} />
      {isLoading ? (
        <Card flush><div className="space-y-3 p-5" role="status" aria-label="Loading submissions">{Array.from({ length: 6 }, (_, i) => <Skeleton key={i} className="h-12" />)}</div></Card>
      ) : (
        <Card flush>
          <Table head={['Reference', 'Agent', 'Branch', 'Type of person', 'Submitted (device)', 'Received (server)', 'Photos', 'Location', 'Review']}>
            {data?.items.map((r) => (
              <tr key={r.id} className={r.is_latest ? '' : 'bg-slate-50/60 text-slate-500'}>
                <Td className="whitespace-nowrap">
                  <Link className="font-mono font-medium text-brand-700 hover:underline" to={`/submissions/${r.id}`}>{r.reference}</Link>
                  {r.revision > 1 && <div className="text-xs text-slate-500">Revision {r.revision}{r.is_latest ? '' : ' (superseded)'}</div>}
                </Td>
                <Td>
                  <div className="flex items-center gap-2.5">
                    <Avatar name={r.agent_name} size="sm" />
                    <div className="min-w-0"><div className="truncate font-medium text-slate-800">{r.agent_name}</div><div className="text-xs text-slate-500">{r.employee_code}</div></div>
                  </div>
                </Td>
                <Td className="whitespace-nowrap">{r.branch_name ?? '—'}</Td>
                <Td>
                  {r.person_types.length
                    ? <span className="flex flex-wrap gap-1">{r.person_types.map((t) => <span key={t} className="rounded-md bg-brand-50 px-2 py-0.5 text-xs font-medium text-brand-700">{t}</span>)}</span>
                    : '—'}
                </Td>
                <Td><When ts={r.submitted_at_device} /></Td>
                <Td><When ts={r.received_at_server} /></Td>
                <Td><span className="inline-flex items-center gap-1.5 text-slate-600"><Camera size={14} className="text-slate-400" aria-hidden="true" />{r.photo_count}</span></Td>
                <Td>
                  {r.has_location
                    ? <span className="inline-flex items-center gap-1 text-emerald-700"><MapPin size={14} aria-hidden="true" />Yes</span>
                    : <span className="inline-flex items-center gap-1 text-slate-400"><MapPinOff size={14} aria-hidden="true" />No</span>}
                </Td>
                <Td><Badge value={r.review_status} /></Td>
              </tr>
            ))}
          </Table>
          {data?.items.length === 0 && <EmptyState icon={<ClipboardList size={22} />} title="No submissions match these filters." hint="Try a wider date range, or clear the filters." />}
          {data && <Pager page={data.page} pageSize={data.page_size} total={data.total} onChange={(p) => { const n = new URLSearchParams(params); n.set('page', String(p)); setParams(n) }} />}
        </Card>
      )}
    </>
  )
}
