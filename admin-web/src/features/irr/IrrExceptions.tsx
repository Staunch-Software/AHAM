import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ListChecks } from 'lucide-react'
import { useState } from 'react'
import { Button, Card, Dialog, EmptyState, ErrorBox, Field, Input, PageTitle, Pager, Segmented, Skeleton, Table, Td } from '../../components/ui'
import { api, errorMessage } from '../../services/api'
import { useAuth } from '../../services/auth'
import { ExportButtons, fmtDay, fmtNum } from './shared'

type Status = 'open' | 'corrected' | 'all'
interface Item { id: string; loan_account: string; disbursement_ref: string | null; disbursement_date: string; branch: string; region: string; product: string; product_class: string; amount: number; tenure_months: number | null; roi: number | null; problem: string | null; corrected_at: string | null; source_row: number | null }
interface Page { items: Item[]; total: number }

function CorrectDialog({ item, onClose }: { item: Item; onClose: () => void }) {
  const qc = useQueryClient()
  const [tenure, setTenure] = useState(item.tenure_months != null && item.tenure_months > 0 ? String(item.tenure_months) : '')
  const [roi, setRoi] = useState(item.roi != null && item.roi > 0 ? String(item.roi) : '')
  const bad = (v: string) => v.trim() !== '' && !(Number(v) > 0)
  const save = useMutation({
    mutationFn: () => api.patch(`/irr/exceptions/${item.id}`, {
      ...(tenure.trim() ? { tenure_months: Number(tenure) } : {}), ...(roi.trim() ? { roi: Number(roi) } : {}),
    }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['irr'] }); onClose() },
  })
  return (
    <Dialog title={`Correct ${item.loan_account}`} onClose={onClose}>
      <p className="mb-4 text-sm text-slate-600">
        Disbursed {fmtDay(item.disbursement_date)} at {item.branch}, ₹{fmtNum(item.amount)} ({item.product}). Problem: {item.problem ?? 'none (already corrected)'}.
        Once tenure and ROI are both above 0 the disbursement counts in the IRR. The change is recorded in the audit log; a later upload of the same row replaces it.
      </p>
      <ErrorBox error={save.error ? errorMessage(save.error) : null} />
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Tenure in months" error={bad(tenure) ? 'A number above 0, for example 240' : undefined}>
          <Input inputMode="decimal" value={tenure} onChange={(e) => setTenure(e.target.value)} placeholder="240" />
        </Field>
        <Field label="ROI (% a year)" error={bad(roi) ? 'A percentage above 0, for example 9.25' : undefined}>
          <Input inputMode="decimal" value={roi} onChange={(e) => setRoi(e.target.value)} placeholder="9.25" />
        </Field>
      </div>
      <div className="mt-5 flex justify-end gap-2">
        <Button variant="secondary" onClick={onClose}>Cancel</Button>
        <Button disabled={save.isPending || bad(tenure) || bad(roi) || (!tenure.trim() && !roi.trim())} onClick={() => save.mutate()}>Save correction</Button>
      </div>
    </Dialog>
  )
}

/** Disbursements left out of the IRR because tenure or ROI is missing, zero or negative (assumption 7). */
export default function IrrExceptions() {
  const { can } = useAuth()
  const [status, setStatus] = useState<Status>('open')
  const [page, setPage] = useState(1)
  const [editing, setEditing] = useState<Item | null>(null)
  const { data, error, isLoading } = useQuery({
    queryKey: ['irr', 'exceptions', status, page], placeholderData: keepPreviousData,
    queryFn: async () => (await api.get<Page>('/irr/exceptions', { params: { status, page, page_size: 50 } })).data,
  })
  return (
    <>
      <PageTitle subtitle="These disbursements are uploaded but left out of the IRR until their tenure or ROI is corrected here, or the row is uploaded again with the values filled in.">IRR exceptions</PageTitle>
      <div className="mb-4">
        <Segmented label="Show" value={status} onChange={(s) => { setStatus(s); setPage(1) }}
          options={[{ value: 'open', label: 'To correct' }, { value: 'corrected', label: 'Corrected' }, { value: 'all', label: 'All' }]} />
      </div>
      <ErrorBox error={error ? errorMessage(error) : null} />
      <Card flush title={data ? `${data.total} disbursement${data.total === 1 ? '' : 's'}` : undefined} actions={<ExportButtons url="/irr/exceptions" params={{ status }} name={`irr_exceptions_${status}`} />}>
        {isLoading ? <div className="space-y-2 p-5">{Array.from({ length: 4 }, (_, i) => <Skeleton key={i} className="h-10" />)}</div>
          : !data?.items.length ? <EmptyState icon={<ListChecks size={20} />} title={status === 'open' ? 'Nothing to correct: every uploaded disbursement has a tenure and ROI.' : 'Nothing here yet.'} />
            : (
              <Table head={['Loan account', 'Date', 'Branch', 'Product', 'Amount (₹)', 'Tenure (months)', 'ROI (%)', 'Problem', '']}>
                {data.items.map((i) => (
                  <tr key={i.id}>
                    <Td className="whitespace-nowrap font-medium text-slate-900">{i.loan_account}{i.disbursement_ref && <span className="ml-1 text-xs text-slate-500">#{i.disbursement_ref}</span>}</Td>
                    <Td className="tabular whitespace-nowrap">{fmtDay(i.disbursement_date)}</Td>
                    <Td className="whitespace-nowrap">{i.branch}<div className="text-xs text-slate-500">{i.region}</div></Td>
                    <Td>{i.product} <span className="text-xs text-slate-500">({i.product_class})</span></Td>
                    <Td className="tabular text-right">{fmtNum(i.amount)}</Td>
                    <Td className="tabular text-right">{fmtNum(i.tenure_months)}</Td>
                    <Td className="tabular text-right">{fmtNum(i.roi, 4)}</Td>
                    <Td className={i.problem ? 'text-amber-800' : 'text-emerald-700'}>{i.problem ?? `Corrected ${i.corrected_at ? new Date(i.corrected_at).toLocaleDateString() : ''}`}</Td>
                    <Td>{can('irr.manage') && <Button small variant="secondary" onClick={() => setEditing(i)}>Correct</Button>}</Td>
                  </tr>
                ))}
              </Table>
            )}
        {data && data.total > 50 && <Pager page={page} pageSize={50} total={data.total} onChange={setPage} />}
      </Card>
      {editing && <CorrectDialog item={editing} onClose={() => setEditing(null)} />}
    </>
  )
}
