import { useQuery } from '@tanstack/react-query'
import { CalendarClock, ListChecks, TriangleAlert } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Button, Card, cx, EmptyState, ErrorBox, Note, PageTitle, RagBadge, Skeleton, Table, Td } from '../../components/ui'
import { api, errorMessage } from '../../services/api'
import { useAuth } from '../../services/auth'
import type { EntryRow } from '../../types'
import { AnswerDialog } from './AnswerDialog'

interface Lead extends EntryRow { handling_branch_name?: string | null; branch_answer: { code: string; meaning: string; answer_date: string | null; responded_on: string; green_channel: string | null; missed: boolean } | null }

/** 12: validated leads waiting for the branch. One code and one date per lead (12.4). */
export default function BranchLeads() {
  const { me, path } = useAuth()
  const [answering, setAnswering] = useState<Lead | null>(null)
  const { data, isLoading, error } = useQuery({ queryKey: ['branch-leads'], queryFn: async () => (await api.get<{ today: string; items: Lead[] }>('/branch/leads')).data })
  const missed = useQuery({ queryKey: ['missed-dates'], queryFn: async () => (await api.get<{ branch: string; missed: number }[]>('/branch/missed-dates')).data })
  return (
    <>
      <PageTitle subtitle={me?.role === 'region_manager' ? 'Leads of the branches in your region that have no Branch Manager.' : 'Validated leads of your branch: answer each with a code and a date.'}>
        Leads to answer
      </PageTitle>
      {missed.data && missed.data.length > 0 && (
        <Note tone="gold"><TriangleAlert size={14} className="mr-1.5 inline" aria-hidden="true" />Missed dates: {missed.data.map((m) => `${m.branch} ${m.missed}`).join(' · ')}. A missed date is a promised login, follow-up or visit date that has passed.</Note>
      )}
      <ErrorBox error={error ? errorMessage(error) : null} />
      <Card flush>
        {isLoading || !data ? <div className="space-y-2 p-5">{Array.from({ length: 4 }, (_, i) => <Skeleton key={i} className="h-12" />)}</div>
          : data.items.length === 0 ? <EmptyState icon={<ListChecks size={20} />} title="No leads are waiting for your branch." hint="Validated leads appear here after the call centre speaks to the customer." />
            : (
              <Table head={['Entry ID (current status)', 'Customer (mobile number)', 'Sales Officer', 'Next action and date', 'Branch’s last answer', 'RAG', '']} exportName="Leads to answer">
                {data.items.map((l) => (
                  <tr key={l.id}>
                    <Td className="whitespace-nowrap"><Link className="font-mono text-xs font-semibold text-brand-700 hover:underline" to={path(`entries/${l.id}`)}>{l.entry_code}</Link><div className="text-xs text-slate-500">{l.current_status}</div></Td>
                    <Td><div className="font-medium text-slate-900">{l.person_name}</div><div className="tabular text-xs text-slate-500">Mobile: {l.phone}</div></Td>
                    <Td>{l.so_name}<div className="text-xs text-slate-500">{l.branch_name}</div>{l.handling_branch_name && <div className="text-xs font-medium text-gold-700">Handled by {l.handling_branch_name}</div>}</Td>
                    <Td className="text-sm">
                      {l.so_action ? <><span className="font-medium">{l.so_action}</span>{l.so_action_date && <div className="flex items-center gap-1 text-xs text-slate-500"><CalendarClock size={12} aria-hidden="true" />{l.so_action_date}</div>}</>
                        : l.cc_action && <span className="text-xs text-slate-500">With the call centre: {l.cc_action} {l.cc_action_date}</span>}
                    </Td>
                    <Td className="text-xs">
                      {l.branch_answer ? (
                        <span className={cx(l.branch_answer.missed && 'font-semibold text-roof-600')}>
                          {l.branch_answer.code} · {l.branch_answer.meaning}{l.branch_answer.answer_date && ` · ${l.branch_answer.answer_date}`}
                          {l.branch_answer.missed && ' (date passed)'}{l.branch_answer.green_channel === 'pending' && ' · green-channel check pending'}
                        </span>
                      ) : <span className="text-slate-400">Not answered yet</span>}
                    </Td>
                    <Td><RagBadge value={l.rag} /></Td>
                    <Td><Button small onClick={() => setAnswering(l)}>Answer</Button></Td>
                  </tr>
                ))}
              </Table>
            )}
      </Card>
      {answering && <AnswerDialog entryId={answering.id} entryCode={answering.entry_code} onClose={() => setAnswering(null)} />}
    </>
  )
}
