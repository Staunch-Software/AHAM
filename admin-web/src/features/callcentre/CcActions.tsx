import { useQuery } from '@tanstack/react-query'
import { Headphones } from 'lucide-react'
import { Card, EmptyState, ErrorBox, PageTitle, Pager, Skeleton } from '../../components/ui'
import { api, errorMessage } from '../../services/api'
import { useAuth } from '../../services/auth'
import { useState } from 'react'
import type { EntryRow, Page } from '../../types'
import { allPages } from '../../services/exporting'
import { EntryTable } from '../entries/EntryList'

/** 12.2: callbacks, cases to take forward and follow-ups, by date. Due ones go on the lists in the daily run. */
export default function CcActions() {
  const { path } = useAuth()
  const [page, setPage] = useState(1)
  const { data, isLoading, error } = useQuery({ queryKey: ['calls', 'cc-actions', page], queryFn: async () => (await api.get<Page<EntryRow>>('/calls/actions', { params: { page, page_size: 100 } })).data })
  return (
    <>
      <PageTitle subtitle="Each comes back on a caller’s list on its date, with the caller who first handled the entry.">Call-centre actions</PageTitle>
      <ErrorBox error={error ? errorMessage(error) : null} />
      <Card flush>
        {isLoading ? <Skeleton className="m-5 h-24" /> : !data?.items.length ? <EmptyState icon={<Headphones size={20} />} title="No open call-centre actions." />
          : <><EntryTable rows={data.items} link={(r) => path(`entries/${r.id}`)} exportName="Call-centre actions" exportAll={() => allPages<EntryRow>('/calls/actions')} /><Pager page={page} pageSize={100} total={data.total} onChange={setPage} /></>}
      </Card>
    </>
  )
}
