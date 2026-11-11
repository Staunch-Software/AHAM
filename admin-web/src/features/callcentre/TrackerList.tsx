import { useQuery } from '@tanstack/react-query'
import { ClipboardList } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Card, EmptyState, ErrorBox, Pager, PageTitle, RAG_LABEL, RagBadge, Segmented, Skeleton, Table, Td } from '../../components/ui'
import { api, errorMessage } from '../../services/api'
import { allPages } from '../../services/exporting'
import { useAuth } from '../../services/auth'
import type { Page } from '../../types'

interface Row { entry_id: string; entry_code: string; person_name: string; owner: string | null; action_type: string | null; followup_date: string | null; outcome: string | null; tcs_id: string | null; rag_override: string | null; notes: string | null; status: string | null; rag: string }
const OWNERS = [{ value: '', label: 'All' }, { value: 'branch', label: 'Branch' }, { value: 'call_centre', label: 'Call centre' }, { value: 'done', label: 'Done' }]

/** Section 13.3: the master owner's manual follow-up rows. Edit a row from the entry page. */
export default function TrackerList() {
  const { path } = useAuth()
  const [owner, setOwner] = useState('')
  const [page, setPage] = useState(1)
  const { data: res, isLoading, error } = useQuery({ queryKey: ['calls', 'tracker', owner, page], queryFn: async () => (await api.get<Page<Row>>('/calls/tracker', { params: { owner: owner || undefined, page, page_size: 100 } })).data })
  const data = res?.items
  return (
    <>
      <PageTitle subtitle="One row per entry. Open an entry and use “Follow-up tracker” to add or change its row." actions={<Segmented label="Owner" options={OWNERS} value={owner} onChange={(v) => { setOwner(v); setPage(1) }} />}>Follow-up tracker</PageTitle>
      <ErrorBox error={error ? errorMessage(error) : null} />
      <Card flush>
        {isLoading ? <Skeleton className="m-5 h-24" /> : !data?.length ? <EmptyState icon={<ClipboardList size={20} />} title="No tracker rows yet." /> : (
          <Table head={['Entry ID and customer', 'Who has it now', 'Action type', 'Follow-up date', 'Outcome', 'TCS ID (login)', 'RAG', 'Notes']} exportName="Follow-up tracker"
            exportAll={async () => (await allPages<Row>('/calls/tracker', { owner: owner || undefined })).map((r) => [`${r.entry_code} · ${r.person_name}`,
              r.owner?.replace('_', ' '), r.action_type, r.followup_date, r.outcome, r.tcs_id, RAG_LABEL[r.rag] ?? r.rag, r.notes])}>
            {data.map((r) => (
              <tr key={r.entry_id}>
                <Td><Link className="font-mono text-xs font-semibold text-brand-700 hover:underline" to={path(`entries/${r.entry_id}`)}>{r.entry_code}</Link><div className="text-xs text-slate-500">{r.person_name}</div></Td>
                <Td>{r.owner?.replace('_', ' ') ?? '—'}</Td><Td>{r.action_type ?? '—'}</Td><Td>{r.followup_date ?? '—'}</Td><Td>{r.outcome ?? '—'}</Td><Td>{r.tcs_id ?? '—'}</Td>
                <Td><RagBadge value={r.rag} overridden={!!r.rag_override} /></Td><Td className="max-w-xs truncate text-xs">{r.notes ?? ''}</Td>
              </tr>
            ))}
          </Table>
        )}
        {!!data?.length && <Pager page={page} pageSize={100} total={res?.total ?? 0} onChange={setPage} />}
      </Card>
    </>
  )
}
