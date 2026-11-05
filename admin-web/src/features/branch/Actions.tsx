import { useQuery } from '@tanstack/react-query'
import { ClipboardList } from 'lucide-react'
import { useState } from 'react'
import { Card, EmptyState, ErrorBox, PageTitle, Pager, Segmented, Skeleton } from '../../components/ui'
import { api, errorMessage } from '../../services/api'
import { useAuth } from '../../services/auth'
import { useMeta } from '../../services/meta'
import type { EntryRow, Page } from '../../types'
import { EntryTable } from '../entries/EntryList'

const KINDS = [
  { value: '', label: 'All' }, { value: 'Correct customer number', label: 'Correct number' },
  { value: 'lead', label: 'Lead actions' }, { value: 'DSA/CP follow-up', label: 'DSA/CP follow-up' },
]
const VIEWS = [{ value: 'open', label: 'Open' }, { value: 'expired', label: 'Expired unworked' }]
const PAGE = 100

/** 12.1: SO / branch actions in my scope, and (12.3) actions whose window ran out before anyone acted. */
export default function Actions() {
  const { path } = useAuth()
  const { data: meta } = useMeta()
  const [kind, setKind] = useState('')
  const [view, setView] = useState('open')
  const [page, setPage] = useState(1)
  const { data, isLoading, error } = useQuery({
    queryKey: ['entries', 'actions', view, kind, page],
    queryFn: async () => (await api.get<Page<EntryRow>>('/branch/actions', { params: { expired: view === 'expired' || undefined, action: kind || undefined, page, page_size: PAGE } })).data,
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
        </div>}>
        {view === 'expired' ? 'Expired actions' : 'Open actions'}
      </PageTitle>
      <ErrorBox error={error ? errorMessage(error) : null} />
      <Card flush>
        {isLoading ? <div className="space-y-2 p-5">{Array.from({ length: 4 }, (_, i) => <Skeleton key={i} className="h-10" />)}</div>
          : rows.length === 0 ? <EmptyState icon={<ClipboardList size={20} />} title={view === 'expired' ? 'Nothing expired.' : 'Nothing open.'} />
            : <>
              <EntryTable rows={rows} link={(r) => path(`entries/${r.id}`)} />
              <Pager page={page} pageSize={PAGE} total={data?.total ?? 0} onChange={setPage} />
            </>}
      </Card>
    </>
  )
}
