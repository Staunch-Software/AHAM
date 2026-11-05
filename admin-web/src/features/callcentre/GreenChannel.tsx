import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ShieldCheck } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Button, Card, EmptyState, ErrorBox, Note, PageTitle, Skeleton, Table, Td } from '../../components/ui'
import { api, errorMessage } from '../../services/api'
import { useAuth } from '../../services/auth'
import { rupeesInWords } from '../../services/format'
import { useMeta } from '../../services/meta'

interface Row { answer_id: string; entry_id: string; entry_code: string; person_name: string; code: string; meaning: string; by: string; responded_on: string; loan_requirement: number | null }

/** 12.4: a branch R2/R3 on a green-channel lead (small construction or purchase loan) waits for head office. */
export default function GreenChannel() {
  const qc = useQueryClient()
  const { path } = useAuth()
  const lim = useMeta().data?.limits
  const { data, isLoading, error } = useQuery({ queryKey: ['calls', 'green'], queryFn: async () => (await api.get<Row[]>('/calls/green-channel')).data })
  const decide = useMutation({
    mutationFn: ({ id, accept }: { id: string; accept: boolean }) => api.post(`/calls/green-channel/${id}`, { accept_reject: accept }),
    onSuccess: () => ['calls', 'entries', 'entry'].forEach((k) => qc.invalidateQueries({ queryKey: [k] })),
  })
  return (
    <>
      <PageTitle subtitle={lim ? `Self construction or improvement up to ₹${rupeesInWords(lim.green_channel_construction_limit)}, purchase or plot + construction up to ₹${rupeesInWords(lim.green_channel_purchase_limit)}, on the call centre’s loan requirement.` : 'Small construction and purchase loans, on the call centre’s loan requirement.'}>Green channel</PageTitle>
      <Note>The rule: an eligibility (R2) or credit-score (R3) reject is <strong>not accepted</strong> for these leads. The lead goes back to the branch to log in, and credit decides.</Note>
      <ErrorBox error={[error, decide.error].map((e) => e && errorMessage(e)).find(Boolean) ?? null} />
      <Card flush>
        {isLoading ? <Skeleton className="m-5 h-24" /> : !data?.length ? <EmptyState icon={<ShieldCheck size={20} />} title="Nothing waiting for a check." /> : (
          <Table head={['Lead', 'Branch answer', 'Loan requirement', 'By', '']}>
            {data.map((r) => (
              <tr key={r.answer_id}>
                <Td><Link className="font-mono text-xs font-semibold text-brand-700 hover:underline" to={path(`entries/${r.entry_id}`)}>{r.entry_code}</Link><div className="text-xs text-slate-500">{r.person_name}</div></Td>
                <Td>{r.code} · {r.meaning}</Td><Td className="tabular">{r.loan_requirement != null ? `₹${r.loan_requirement.toLocaleString('en-IN')}` : '—'}</Td>
                <Td>{r.by}<div className="text-xs text-slate-500">{r.responded_on}</div></Td>
                <Td className="whitespace-nowrap">
                  <Button small disabled={decide.isPending} onClick={() => decide.mutate({ id: r.answer_id, accept: false })}>Back to branch</Button>{' '}
                  <Button small variant="secondary" disabled={decide.isPending} onClick={() => decide.mutate({ id: r.answer_id, accept: true })}>Accept reject</Button>
                </Td>
              </tr>
            ))}
          </Table>
        )}
      </Card>
    </>
  )
}
