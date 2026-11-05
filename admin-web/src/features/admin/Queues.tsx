import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Clock, Shapes } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Button, Card, Dialog, EmptyState, ErrorBox, Field, Input, PageTitle, Pager, Select, Table, Td } from '../../components/ui'
import { api, errorMessage } from '../../services/api'
import { useAuth } from '../../services/auth'
import { fmtServer } from '../../services/format'
import { useMeta } from '../../services/meta'
import type { EntryRow, Page } from '../../types'

function CategoryDialog({ entry, onClose }: { entry: EntryRow; onClose: () => void }) {
  const qc = useQueryClient()
  const { data: meta } = useMeta()
  const subtypes = useQuery({ queryKey: ['cp-active'], queryFn: async () => (await api.get<{ id: string; label: string }[]>('/cp-subtypes/active')).data })
  const [category, setCategory] = useState(entry.category)
  const [sub, setSub] = useState('')
  const [note, setNote] = useState('')
  const m = useMutation({
    mutationFn: () => api.post(`/monitor/category-review/${entry.id}`, { category, cp_subtype_id: category === 'contact_point' ? sub : null, note: note || null }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['queues'] }); onClose() },
  })
  return (
    <Dialog title={`Category of ${entry.entry_code}`} onClose={onClose}>
      <p className="mb-4 text-sm text-slate-600">The branch says the category is wrong. Keep it, or set the right one (the calling group follows the category).</p>
      <ErrorBox error={m.error ? errorMessage(m.error) : null} />
      <div className="space-y-4">
        <Field label="Category"><Select value={category} onChange={(e) => setCategory(e.target.value)}>{meta?.categories.map((c) => <option key={c.key} value={c.key}>{c.label}</option>)}</Select></Field>
        {category === 'contact_point' && <Field label="CP sub-type"><Select value={sub} onChange={(e) => setSub(e.target.value)}><option value="">Choose…</option>{subtypes.data?.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}</Select></Field>}
        <Field label="Note"><Input value={note} onChange={(e) => setNote(e.target.value)} /></Field>
      </div>
      <div className="mt-5 flex justify-end gap-2"><Button variant="secondary" onClick={onClose}>Cancel</Button><Button disabled={m.isPending || (category === 'contact_point' && !sub)} onClick={() => m.mutate()}>{category === entry.category ? 'Keep category' : 'Change category'}</Button></div>
    </Dialog>
  )
}

/** The Sankalp monitor's queues: "category wrong" answers from branches, and entries whose phone clock looked wrong. */
export default function Queues() {
  const { path } = useAuth()
  const [editing, setEditing] = useState<EntryRow | null>(null)
  const [catPage, setCatPage] = useState(1)
  const [timePage, setTimePage] = useState(1)
  const cat = useQuery({ queryKey: ['queues', 'category', catPage], queryFn: async () => (await api.get<Page<EntryRow>>('/monitor/category-review', { params: { page: catPage, page_size: 100 } })).data })
  const time = useQuery({ queryKey: ['queues', 'time', timePage], queryFn: async () => (await api.get<Page<EntryRow>>('/monitor/time-flags', { params: { page: timePage, page_size: 100 } })).data })
  const link = (r: EntryRow) => <Link className="font-mono text-xs font-semibold text-brand-700 hover:underline" to={path(`entries/${r.id}`)}>{r.entry_code}</Link>
  return (
    <>
      <PageTitle subtitle="Wrong-SO corrections are made from the entry page (“Correct SO”).">Review queues</PageTitle>
      <ErrorBox error={[cat.error, time.error].map((e) => e && errorMessage(e)).find(Boolean) ?? null} />
      <Card title="Category wrong (branch code 2)" flush>
        {!cat.data?.items.length ? <EmptyState icon={<Shapes size={20} />} title="Nothing to review." /> : (
          <Table head={['Entry', 'Person', 'Category now', 'SO', '']}>
            {cat.data.items.map((r) => <tr key={r.id}><Td>{link(r)}</Td><Td>{r.person_name}</Td><Td>{r.category_label}</Td><Td>{r.so_name} · {r.branch_name}</Td><Td><Button small onClick={() => setEditing(r)}>Review</Button></Td></tr>)}
          </Table>
        )}
        {!!cat.data?.items.length && <Pager page={catPage} pageSize={100} total={cat.data.total} onChange={setCatPage} />}
      </Card>
      <Card title="Check the time" subtitle="The phone’s clock was ahead of the server, or had been set back since the phone last reached the server" className="mt-6" flush>
        {!time.data?.items.length ? <EmptyState icon={<Clock size={20} />} title="No entries with a suspicious time." /> : (
          <Table head={['Entry', 'SO', 'Phone time', 'Received']}>
            {time.data.items.map((r) => <tr key={r.id}><Td>{link(r)}</Td><Td>{r.so_name}</Td><Td>{fmtServer(r.submitted_at_device)}</Td><Td>{fmtServer(r.received_at_server)}</Td></tr>)}
          </Table>
        )}
        {!!time.data?.items.length && <Pager page={timePage} pageSize={100} total={time.data.total} onChange={setTimePage} />}
      </Card>
      {editing && <CategoryDialog entry={editing} onClose={() => setEditing(null)} />}
    </>
  )
}
