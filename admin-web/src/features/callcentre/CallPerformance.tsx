import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { BarChart3 } from 'lucide-react'
import { useState } from 'react'
import { Card, EmptyState, ErrorBox, PageTitle, Segmented, Skeleton, StatCard, Table, Td } from '../../components/ui'
import { api, errorMessage } from '../../services/api'
import { PERIODS, type Period } from '../dashboard/Dashboard'

interface Data { period: { from: string; to: string }; first_attempts: number; first_attempt_on_time: number; target_days: number; callers: { caller_id: string; name: string; attempts: number; connected: number; unanswered: number; validated: number; entries: number }[] }

export default function CallPerformance() {
  const [period, setPeriod] = useState<Period>('today')
  const { data, isLoading, error } = useQuery({ queryKey: ['calls', 'perf', period], queryFn: async () => (await api.get<Data>('/reports/callcentre', { params: { period } })).data, placeholderData: keepPreviousData })
  const pct = (a: number, b: number) => (b ? `${Math.round((a / b) * 100)}%` : '—')
  const totals = data?.callers.reduce((t, c) => ({ attempts: t.attempts + c.attempts, connected: t.connected + c.connected, validated: t.validated + c.validated }), { attempts: 0, connected: 0, validated: 0 })
  return (
    <>
      <PageTitle subtitle="Tries recorded in the period, by caller." actions={<Segmented label="Period" options={PERIODS} value={period} onChange={setPeriod} />}>Caller performance</PageTitle>
      <ErrorBox error={error ? errorMessage(error) : null} />
      {isLoading || !data || !totals ? <Skeleton className="h-40" /> : (
        <>
          <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard label="Tries" value={totals.attempts} />
            <StatCard label="Connected" value={totals.connected} tone="green" hint={pct(totals.connected, totals.attempts)} />
            <StatCard label="Validated" value={totals.validated} tone="gold" />
            <StatCard label="First try on time" value={pct(data.first_attempt_on_time, data.first_attempts)} tone="blue" hint={`Within ${data.target_days} day of the entry · ${data.first_attempts} first tries`} />
          </div>
          <Card flush>
            {!data.callers.length ? <EmptyState icon={<BarChart3 size={20} />} title="No tries in this period." /> : (
              <Table head={['Caller', 'Entries called', 'Calls made', 'Connected calls', 'Calls not answered', 'Entries validated', 'Connected (% of calls)']} exportName="Caller performance">
                {data.callers.map((c) => (
                  <tr key={c.caller_id}><Td className="font-medium">{c.name}</Td><Td className="tabular">{c.entries}</Td><Td className="tabular">{c.attempts}</Td>
                    <Td className="tabular">{c.connected}</Td><Td className="tabular">{c.unanswered}</Td><Td className="tabular">{c.validated}</Td><Td className="tabular">{pct(c.connected, c.attempts)}</Td></tr>
                ))}
              </Table>
            )}
          </Card>
        </>
      )}
    </>
  )
}
