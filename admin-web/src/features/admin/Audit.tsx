import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { ScrollText } from 'lucide-react'
import { useState } from 'react'
import { Avatar, Card, EmptyState, ErrorBox, PageTitle, Pager, Skeleton, Table, Td } from '../../components/ui'
import { api, errorMessage } from '../../services/api'
import { fmtServer } from '../../services/format'

interface Entry { id: string; actor: string | null; action: string; entity_type: string; entity_id: string | null; details: Record<string, unknown> | null; created_at: string }

/** "daily_entry_target: 10 → 12" for a setting change; "key: value" for anything else. */
const describe = (d: Record<string, unknown>) => Object.entries(d).map(([k, v]) => {
  const ov = v as { old?: unknown; new?: unknown } | null
  const show = (x: unknown) => (typeof x === 'object' && x !== null ? JSON.stringify(x) : String(x))
  return ov && typeof ov === 'object' && 'new' in ov ? `${k.replace(/_/g, ' ')}: ${show(ov.old)} → ${show(ov.new)}` : `${k.replace(/_/g, ' ')}: ${show(v)}`
})

export default function Audit() {
  const [page, setPage] = useState(1)
  const { data, isLoading, error } = useQuery({
    queryKey: ['audit', page],
    queryFn: async () => (await api.get<{ items: Entry[]; total: number; page: number; page_size: number }>('/audit-logs', { params: { page } })).data,
    placeholderData: keepPreviousData,
  })
  return (
    <>
      <PageTitle subtitle="Who changed what, newest first.">Audit log</PageTitle>
      <ErrorBox error={error ? errorMessage(error) : null} />
      {isLoading ? (
        <Card flush><div className="space-y-3 p-5" role="status" aria-label="Loading audit log">{Array.from({ length: 6 }, (_, i) => <Skeleton key={i} className="h-10" />)}</div></Card>
      ) : (
        <Card flush>
          <Table head={['When', 'Who', 'Action', 'Record', 'What changed']}>
            {data?.items.map((e) => (
              <tr key={e.id}>
                <Td className="whitespace-nowrap">{fmtServer(e.created_at)}</Td>
                <Td><span className="flex items-center gap-2"><Avatar name={e.actor ?? 'system'} size="sm" />{e.actor ?? 'system'}</span></Td>
                <Td><span className="rounded-md bg-slate-100 px-2 py-0.5 font-mono text-xs text-slate-700">{e.action}</span></Td>
                <Td className="font-mono text-xs text-slate-500">{e.entity_type} {e.entity_id?.slice(0, 8)}</Td>
                <Td className="text-xs text-slate-600">{e.details ? describe(e.details).map((l) => <div key={l}>{l}</div>) : ''}</Td>
              </tr>
            ))}
          </Table>
          {data?.items.length === 0 && <EmptyState icon={<ScrollText size={22} />} title="Nothing recorded yet." />}
          {data && <Pager page={data.page} pageSize={data.page_size} total={data.total} onChange={setPage} />}
        </Card>
      )}
    </>
  )
}
