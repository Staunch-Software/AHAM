import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, CalendarRange, Info, UserX } from 'lucide-react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { Avatar, Card, EmptyState, ErrorBox, PageTitle, Skeleton, Table, Td } from '../../components/ui'
import { api, errorMessage } from '../../services/api'
import { fmtServer } from '../../services/format'
import { Achievement, type AgentsPayload, PeriodPicker, PeriodRange, TargetEditor, Trend, listLink, numberLink, periodParams, rate } from './Analytics'

export default function BranchAgents() {
  const { id } = useParams()
  const [params, setParams] = useSearchParams()
  const q = periodParams(params)
  const ready = q.period !== 'custom' || (q.date_from && q.date_to)
  const { data, isLoading, error } = useQuery({
    queryKey: ['analytics', 'agents', id, q], enabled: !!ready,
    queryFn: async () => (await api.get<AgentsPayload>(`/analytics/branches/${id}/agents`, { params: q })).data,
  })
  return (
    <>
      <Link to={`/analytics?${params.toString()}`} className="mb-4 inline-flex items-center gap-1.5 text-sm font-medium text-slate-500 hover:text-brand-700"><ArrowLeft size={16} aria-hidden="true" />All branches</Link>
      <PageTitle subtitle="Reports and review outcomes for each agent in this branch.">{data ? `${data.branch.name}: agents` : 'Agents'}</PageTitle>
      <PeriodPicker params={params} onChange={setParams} />
      <ErrorBox error={error ? errorMessage(error) : null} />
      {!ready ? <EmptyState icon={<CalendarRange size={22} />} title="Choose a start and end date." />
        : isLoading || !data ? <div role="status" aria-label="Loading agents"><Skeleton className="h-72" /></div> : (
        <>
          <PeriodRange meta={data.period} />
          <Card flush>
            <Table head={['Agent', 'Reports', 'Target', 'Achievement', 'Pending', 'Needs correction', 'Rejection rate', 'Trend', 'Last report']}>
              {data.agents.map((a) => (
                <tr key={a.agent_id}>
                  <Td>
                    <div className="flex items-center gap-2.5">
                      <Avatar name={a.name} size="sm" />
                      <div><div className="font-medium text-slate-800">{a.name}</div><div className="text-xs text-slate-500">{a.employee_code}{a.status !== 'active' ? ' · inactive' : ''}</div></div>
                    </div>
                  </Td>
                  <Td><Link className={numberLink} to={listLink(data.period, { agent_id: a.agent_id })}>{a.reports}</Link></Td>
                  <Td><TargetEditor scope="agent" id={a.agent_id} meta={data.period} value={a.target} /></Td>
                  <Td><Achievement m={a} applies={data.period.targets_apply} /></Td>
                  <Td><Link className={numberLink} to={listLink(data.period, { agent_id: a.agent_id, review_status: 'pending' })}>{a.pending}</Link></Td>
                  <Td><Link className={numberLink} to={listLink(data.period, { agent_id: a.agent_id, review_status: 'rejected' })}>{a.needs_correction}</Link></Td>
                  <Td className="tabular">{rate(a.rejection_rate)}</Td>
                  <Td><Trend pct={a.trend_pct} /></Td>
                  <Td className="whitespace-nowrap">{a.last_report_at ? fmtServer(a.last_report_at) : 'Never'}</Td>
                </tr>
              ))}
            </Table>
            {data.agents.length === 0 && <EmptyState icon={<UserX size={22} />} title="No agents are assigned to this branch." />}
          </Card>
          <p className="mt-4 flex items-start gap-2.5 rounded-xl border border-gold-300/60 bg-gold-50 px-4 py-3 text-sm text-slate-700" data-testid="sync-note">
            <Info size={16} className="mt-0.5 shrink-0 text-gold-700" aria-hidden="true" /><span>{data.note}</span>
          </p>
        </>
      )}
    </>
  )
}
